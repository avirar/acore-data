"""Port of AzerothCore's PathGenerator (server path semantics).

Matches ``PathGenerator::CalculatePath`` with modes:
  - ``smooth``   -> FindSmoothPath (the ``.mmap path`` default)
  - ``straight`` -> findStraightPath corner points (``.mmap path true``)
  - ``raycast``  -> navmesh raycast (``.mmap path ray``)

All caps (poly count, point count) default to unlimited; the server's own
limits (74, or 148 in playerbots builds) can be supplied explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from core.terrain.detour.filter import DetourFilter, player_filter
from core.terrain.detour.mathutil import v_dist_sqr, v_lerp, v_mad, v_dist
from core.terrain.detour.navmesh import NavMesh
from core.terrain.detour.query import (
    DT_FAILURE,
    DT_STRAIGHTPATH_END,
    DT_STRAIGHTPATH_OFFMESH_CONNECTION,
    DT_SUCCESS,
    NavMeshQuery,
)

SMOOTH_PATH_STEP_SIZE = 4.0
SMOOTH_PATH_SLOP = 0.3
FLT_MAX = 3.4028234663852886e38
DT_SLOPE_TOO_STEEP = 1 << 8
INVALID_POLYREF = 0

PATHFIND_BLANK = 0x00
PATHFIND_NORMAL = 0x01
PATHFIND_SHORTCUT = 0x02
PATHFIND_INCOMPLETE = 0x04
PATHFIND_NOPATH = 0x08
PATHFIND_NOT_USING_PATH = 0x10
PATHFIND_SHORT = 0x20
PATHFIND_FARFROMPOLY_START = 0x40
PATHFIND_FARFROMPOLY_END = 0x80

PATH_TYPE_NAMES = {
    PATHFIND_BLANK: "BLANK",
    PATHFIND_NORMAL: "NORMAL",
    PATHFIND_SHORTCUT: "SHORTCUT",
    PATHFIND_INCOMPLETE: "INCOMPLETE",
    PATHFIND_NOPATH: "NOPATH",
    PATHFIND_NOT_USING_PATH: "NOT_USING_PATH",
    PATHFIND_SHORT: "SHORT",
    PATHFIND_FARFROMPOLY_START: "FARFROMPOLY_START",
    PATHFIND_FARFROMPOLY_END: "FARFROMPOLY_END",
}

MAP_LIQUID_NO_WATER = 0x00
MAP_LIQUID_ABOVE_WATER = 0x01
MAP_LIQUID_WATER_WALK = 0x02
MAP_LIQUID_IN_WATER = 0x04
MAP_LIQUID_UNDER_WATER = 0x08
MAP_LIQUID_STATUS_SWIMMING = MAP_LIQUID_IN_WATER | MAP_LIQUID_UNDER_WATER
MAP_LIQUID_STATUS_IN_CONTACT = MAP_LIQUID_STATUS_SWIMMING | MAP_LIQUID_WATER_WALK

MAP_BLADES_EDGE_ARENA = 562


@dataclass
class UnitProfile:
    """Subset of WorldObject/Unit state used by PathGenerator."""
    can_swim: bool = True
    can_fly: bool = False
    is_falling: bool = False
    in_water: bool = False
    collision_height: float = 2.03128
    hover_height: float = 0.0


class PathResult:
    __slots__ = ("found", "path_type", "path_points", "poly_refs",
                 "start_position", "end_position", "actual_end_position",
                 "distance", "max_nodes_exceeded")

    def __init__(self) -> None:
        self.found = False
        self.path_type = PATHFIND_BLANK
        self.path_points: List[Tuple[float, float, float]] = []
        self.poly_refs: List[int] = []
        self.start_position = (0.0, 0.0, 0.0)
        self.end_position = (0.0, 0.0, 0.0)
        self.actual_end_position = (0.0, 0.0, 0.0)
        self.distance = 0.0
        self.max_nodes_exceeded = False

    @property
    def path_type_names(self) -> List[str]:
        return [name for flag, name in PATH_TYPE_NAMES.items()
                if flag and flag != PATHFIND_BLANK and (self.path_type & flag)]


def _detour_point(p):
    """World (x, y, z) -> Detour (y, z, x)."""
    return (p[1], p[2], p[0])


def _world_point(p):
    """Detour (x, y, z) -> world (z, x, y)."""
    return (p[2], p[0], p[1])


def _in_range_yzx(v1, v2, r: float, h: float) -> bool:
    dx = v2[0] - v1[0]
    dy = v2[1] - v1[1]
    dz = v2[2] - v1[2]
    return (dx * dx + dz * dz) < r * r and abs(dy) < h


def _in_range(p1, p2, r: float, h: float) -> bool:
    d = (p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2])
    return (d[0] * d[0] + d[1] * d[1]) < r * r and abs(d[2]) < h


class PathGenerator:
    def __init__(self, navmesh: NavMesh, filt: Optional[DetourFilter] = None,
                 profile: Optional[UnitProfile] = None,
                 normalizer: Optional[Callable[[float, float, float], float]] = None,
                 liquid: Optional[Callable[[float, float, float], int]] = None,
                 max_nodes: Optional[int] = None):
        self.nav = navmesh
        self.profile = profile or UnitProfile()
        self.filter = filt or player_filter()
        self.normalizer = normalizer
        self.liquid = liquid
        self.query = NavMeshQuery(navmesh, self.filter, max_nodes=max_nodes)

        self._use_straight_path = False
        self._use_raycast = False
        self._force_destination = False
        self._slope_check = False
        self._max_polys: Optional[int] = None
        self._max_points: Optional[int] = None

        self._path_poly_refs: List[int] = []
        self._poly_length = 0
        self._path_points: List[Tuple[float, float, float]] = []
        self._type = PATHFIND_BLANK
        self._start_position = (0.0, 0.0, 0.0)
        self._end_position = (0.0, 0.0, 0.0)
        self._actual_end_position = (0.0, 0.0, 0.0)
        self._max_nodes_exceeded = False

    # ---- option setters ----

    def set_use_straight_path(self, value: bool) -> None:
        self._use_straight_path = value

    def set_use_raycast(self, value: bool) -> None:
        self._use_raycast = value

    def set_slope_check(self, value: bool) -> None:
        self._slope_check = value

    def set_max_polys(self, value: Optional[int]) -> None:
        self._max_polys = value

    def set_max_points(self, value: Optional[int]) -> None:
        self._max_points = value

    def set_path_length_limit(self, distance: float) -> None:
        limit = int(distance / SMOOTH_PATH_STEP_SIZE)
        if self._max_points is None:
            self._max_points = limit
        else:
            self._max_points = min(self._max_points, limit)

    # ---- result getters ----

    @property
    def path_type(self) -> int:
        return self._type

    @property
    def path_points(self):
        return self._path_points

    @property
    def start_position(self):
        return self._start_position

    @property
    def end_position(self):
        return self._end_position

    @property
    def actual_end_position(self):
        return self._actual_end_position

    @property
    def poly_refs(self):
        return self._path_poly_refs

    # ---- main entry ----

    def calculate_path(self, x: float, y: float, z: float,
                       dest_x: float, dest_y: float, dest_z: float,
                       force_dest: bool = False) -> bool:
        if not _valid_map_coord(dest_x, dest_y, dest_z) or \
                not _valid_map_coord(x, y, z):
            return False

        self._max_nodes_exceeded = False
        self._end_position = (dest_x, dest_y, dest_z)
        self._actual_end_position = self._end_position
        self._start_position = (x, y, z)
        self._force_destination = force_dest

        if not self.nav.has_navmesh or \
                not self._have_tile(self._start_position) or \
                not self._have_tile(self._end_position):
            self._build_shortcut()
            self._type = PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH
            return True

        self._build_poly_path(self._start_position, self._end_position)
        return True

    # ---- internal ----

    def _valid(self, x, y, z) -> bool:
        return _valid_map_coord(x, y, z)

    def _have_tile(self, p) -> bool:
        point = _detour_point(p)
        tx, ty = self.nav.calc_tile_loc(point)
        if tx < 0 or ty < 0:
            return False
        if (tx, ty) in self.nav.tiles:
            return True
        return self.nav.tile_file(tx, ty) is not None

    def _get_path_poly_by_position(self, poly_path: Sequence[int], point):
        if not poly_path:
            return INVALID_POLYREF, FLT_MAX
        nearest = INVALID_POLYREF
        min_dist = FLT_MAX
        for ref in poly_path:
            closest, _pos_over = self.nav.closest_point_on_poly(ref, point)
            if closest is None:
                continue
            d = v_dist_sqr(point, closest)
            if d < min_dist:
                min_dist = d
                nearest = ref
            if min_dist < 1.0:
                break
        if min_dist < 3.0:
            return nearest, math.sqrt(min_dist)
        return INVALID_POLYREF, math.sqrt(min_dist)

    def _get_poly_by_location(self, point):
        ref, dist = self._get_path_poly_by_position(self._path_poly_refs, point)
        if ref != INVALID_POLYREF:
            return ref, dist

        ref, closest = self.query.find_nearest_poly(point, (3.0, 5.0, 3.0))
        if ref:
            return ref, v_dist(point, closest)
        ref, closest = self.query.find_nearest_poly(point, (3.0, 50.0, 3.0))
        if ref:
            return ref, v_dist(point, closest)
        return INVALID_POLYREF, FLT_MAX

    def _build_poly_path(self, start_pos, end_pos) -> None:
        start_point = _detour_point(start_pos)
        end_point = _detour_point(end_pos)

        start_poly, dist_start = self._get_poly_by_location(start_point)
        end_poly, dist_end = self._get_poly_by_location(end_point)

        self._type = PATHFIND_NORMAL

        if start_poly == INVALID_POLYREF or end_poly == INVALID_POLYREF:
            self._build_shortcut()
            water_path = self._is_water_path(self._path_points)
            if self.profile.can_fly or (water_path and self.profile.can_swim):
                self._type = PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH
                return
            if not self._use_raycast:
                self._type = PATHFIND_NOPATH
                return

        start_far = dist_start > 7.0
        end_far = dist_end > 7.0

        if start_far or end_far:
            build_shortcut = False
            water_path = False
            if self.liquid is not None:
                ls = self._liquid_status(start_pos[0], start_pos[1], start_pos[2])
                le = self._liquid_status(end_pos[0], end_pos[1], end_pos[2])
                start_under_end_in = (ls == MAP_LIQUID_UNDER_WATER and
                                      (le & MAP_LIQUID_STATUS_IN_CONTACT) != 0)
                start_in_end_under = ((ls & MAP_LIQUID_STATUS_IN_CONTACT) != 0 and
                                      le == MAP_LIQUID_UNDER_WATER)
                water_path = start_under_end_in or start_in_end_under

            is_water = self.profile.can_swim and water_path
            if is_water or self.profile.can_fly or \
                    (self.profile.is_falling and end_pos[2] < start_pos[2]):
                build_shortcut = True

            if build_shortcut:
                self._build_shortcut()
                self._type = PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH
                self._add_far_from_poly_flags(start_far, end_far)
                return
            closest = self.nav.closest_point_on_poly(end_poly, end_point)
            if closest is not None:
                end_point = closest
                self._actual_end_position = _world_point(end_point)
            self._type = PATHFIND_INCOMPLETE
            self._add_far_from_poly_flags(start_far, end_far)

        if start_poly == end_poly and not self._use_raycast:
            self._path_poly_refs = [start_poly]
            self._poly_length = 1
            if start_far or end_far:
                self._type = PATHFIND_INCOMPLETE
                self._add_far_from_poly_flags(start_far, end_far)
            else:
                self._type = PATHFIND_NORMAL
            self._build_point_path(start_point, end_point)
            return

        self._clear()
        if self._use_raycast:
            status, hit, _normal, path = self.query.raycast(
                start_poly, start_point, end_point,
                max_path=self._max_polys if self._max_polys else (1 << 30),
            )
            self._path_poly_refs = list(path)
            self._poly_length = len(path)
            if not path or (status & DT_FAILURE):
                self._build_shortcut()
                self._type = PATHFIND_NOPATH
                self._add_far_from_poly_flags(start_far, end_far)
                return
            if hit != FLT_MAX:
                hit *= 0.99
                hit_pos = v_lerp(start_point, end_point, hit)
                height = self.nav.get_poly_height(path[-1], hit_pos)
                if height is None:
                    hit_pos = self.nav.closest_point_on_poly_boundary(path[-1], hit_pos)
                else:
                    hit_pos = (hit_pos[0], height, hit_pos[2])
                self._path_points = [start_pos, _world_point(hit_pos)]
                self._normalize_path()
                self._type = PATHFIND_INCOMPLETE
                self._add_far_from_poly_flags(start_far, False)
                return
            height = self.nav.get_poly_height(path[-1], end_point)
            if height is None:
                end_point = self.nav.closest_point_on_poly_boundary(path[-1], end_point)
            else:
                end_point = (end_point[0], height, end_point[2])
            self._path_points = [start_pos, _world_point(end_point)]
            self._normalize_path()
            if start_far or end_far:
                self._type = PATHFIND_INCOMPLETE
                self._add_far_from_poly_flags(start_far, end_far)
            else:
                self._type = PATHFIND_NORMAL
            return

        status, path = self.query.find_path(
            start_poly, end_poly, start_point, end_point,
            max_path=self._max_polys if self._max_polys else (1 << 30),
        )
        self._path_poly_refs = list(path)
        self._poly_length = len(path)
        if not path or (status & DT_FAILURE):
            self._build_shortcut()
            self._type = PATHFIND_NOPATH
            return
        if status & 0x800000:  # DT_OUT_OF_NODES
            self._max_nodes_exceeded = True

        if path[-1] == end_poly and not (self._type & PATHFIND_INCOMPLETE):
            self._type = PATHFIND_NORMAL
        else:
            self._type = PATHFIND_INCOMPLETE

        self._add_far_from_poly_flags(start_far, end_far)
        self._build_point_path(start_point, end_point)

    def _build_point_path(self, start_point, end_point) -> None:
        max_points = self._max_points if self._max_points is not None else (1 << 30)
        points: List[Tuple[float, float, float]] = []
        status = DT_FAILURE

        if self._use_raycast:
            self._build_shortcut()
            self._type = PATHFIND_NOPATH
            return
        if self._use_straight_path:
            status, points, _flags, _refs = self.query.find_straight_path(
                start_point, end_point, self._path_poly_refs, max_points=max_points
            )
        else:
            status, points = self._find_smooth_path(
                start_point, end_point, self._path_poly_refs, max_points
            )

        if self._poly_length == 1 and len(points) == 1 and not (status & DT_SLOPE_TOO_STEEP):
            points = [points[0], end_point]
        elif len(points) < 2 or (status & DT_FAILURE):
            if points and (status & DT_SLOPE_TOO_STEEP):
                self._path_points = [_world_point(p) for p in points]
                self._normalize_path()
                self._actual_end_position = self._path_points[-1]
                self._type = self._type | PATHFIND_INCOMPLETE
                return
            self._build_shortcut()
            self._type = self._type | PATHFIND_NOPATH
            return
        elif len(points) >= max_points:
            self._build_shortcut()
            self._type = self._type | PATHFIND_SHORT
            return

        self._path_points = [_world_point(p) for p in points]
        self._normalize_path()
        self._actual_end_position = self._path_points[-1]

        if self._force_destination and (
                not (self._type & PATHFIND_NORMAL)
                or not _in_range(self._end_position, self._actual_end_position, 1.0, 1.0)):
            if v_dist_sqr(self._actual_end_position, self._end_position) < \
                    0.3 * v_dist_sqr(self._start_position, self._end_position):
                self._actual_end_position = self._end_position
                self._path_points[-1] = self._end_position
            else:
                self._actual_end_position = self._end_position
                self._build_shortcut()
            self._type = PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH

    # ---- smooth path ----

    def _get_steer_target(self, start_pos, end_pos, min_target_dist, path):
        status, points, flags, refs = self.query.find_straight_path(
            start_pos, end_pos, path, max_points=3
        )
        if not points:
            return None
        ns = 0
        while ns < len(points):
            if (flags[ns] & DT_STRAIGHTPATH_OFFMESH_CONNECTION) or \
                    not _in_range_yzx(points[ns], start_pos, min_target_dist, 1000.0):
                break
            ns += 1
        if ns >= len(points):
            return None
        steer = list(points[ns])
        steer[1] = start_pos[1]  # keep Z value
        return tuple(steer), flags[ns], refs[ns]

    def _fixup_corridor(self, path: List[int], visited: List[int]) -> List[int]:
        furthest_path = -1
        furthest_visited = -1
        for i in range(len(path) - 1, -1, -1):
            found = False
            for j in range(len(visited) - 1, -1, -1):
                if path[i] == visited[j]:
                    furthest_path = i
                    furthest_visited = j
                    found = True
            if found:
                break
        if furthest_path == -1 or furthest_visited == -1:
            return path
        req = len(visited) - furthest_visited
        orig = furthest_path + 1 if furthest_path + 1 < len(path) else len(path)
        size = len(path) - orig if len(path) > orig else 0
        new_path = [0] * (req + size)
        for i in range(req):
            new_path[i] = visited[len(visited) - 1 - i]
        if size:
            new_path[req:req + size] = path[orig:orig + size]
        return new_path

    def _find_smooth_path(self, start_pos, end_pos, poly_path, max_size):
        polys = list(poly_path)
        npolys = len(polys)
        if not npolys:
            return DT_FAILURE, []

        if npolys > 1:
            iter_pos = self.nav.closest_point_on_poly_boundary(polys[0], start_pos)
            target_pos = self.nav.closest_point_on_poly_boundary(polys[-1], end_pos)
            if iter_pos is None or target_pos is None:
                return DT_FAILURE, []
        else:
            iter_pos = start_pos
            target_pos = end_pos

        smooth: List[Tuple[float, float, float]] = [iter_pos]

        while npolys and len(smooth) < max_size:
            steer = self._get_steer_target(iter_pos, target_pos, SMOOTH_PATH_SLOP, polys)
            if steer is None:
                break
            steer_pos, steer_flag, steer_ref = steer
            end_of_path = bool(steer_flag & DT_STRAIGHTPATH_END)
            off_mesh = bool(steer_flag & DT_STRAIGHTPATH_OFFMESH_CONNECTION)

            delta = (steer_pos[0] - iter_pos[0],
                     steer_pos[1] - iter_pos[1],
                     steer_pos[2] - iter_pos[2])
            length = math.sqrt(delta[0] ** 2 + delta[1] ** 2 + delta[2] ** 2)
            if (end_of_path or off_mesh) and length < SMOOTH_PATH_STEP_SIZE:
                factor = 1.0
            else:
                factor = SMOOTH_PATH_STEP_SIZE / length if length > 0 else 0.0
            move_tgt = v_mad(iter_pos, delta, factor)

            status, result, visited = self.query.move_along_surface(
                polys[0], iter_pos, move_tgt, max_visited=16
            )
            if status & DT_FAILURE:
                return DT_FAILURE, []
            polys = self._fixup_corridor(polys, visited)
            npolys = len(polys)
            height = self.nav.get_poly_height(polys[0], result)
            if height is not None:
                result = (result[0], height, result[2])
            result = (result[0], result[1] + 0.5, result[2])
            iter_pos = result

            if end_of_path and _in_range_yzx(iter_pos, steer_pos, SMOOTH_PATH_SLOP, 1.0):
                iter_pos = target_pos
                if len(smooth) < max_size:
                    smooth.append(iter_pos)
                break
            if off_mesh and _in_range_yzx(iter_pos, steer_pos, SMOOTH_PATH_SLOP, 1.0):
                prev_ref = 0
                poly_ref = polys[0] if polys else 0
                npos = 0
                while npos < npolys and poly_ref != steer_ref:
                    prev_ref = poly_ref
                    poly_ref = polys[npos]
                    npos += 1
                polys = polys[npos:]
                npolys = len(polys)
                ends = self.query.get_off_mesh_connection_poly_end_points(
                    prev_ref, poly_ref
                )
                if ends is not None:
                    connection_start, connection_end = ends
                    if len(smooth) < max_size:
                        smooth.append(connection_start)
                    iter_pos = connection_end
                    if polys:
                        height = self.nav.get_poly_height(polys[0], iter_pos)
                        if height is None:
                            return DT_FAILURE, []
                        iter_pos = (iter_pos[0], height + 0.5, iter_pos[2])

            if len(smooth) < max_size:
                smooth.append(iter_pos)

        if len(smooth) < max_size:
            return DT_SUCCESS, smooth
        return DT_FAILURE, smooth

    # ---- helpers ----

    def _build_shortcut(self) -> None:
        self._clear()
        self._path_points = [self._start_position, self._actual_end_position]
        self._normalize_path()
        self._type = PATHFIND_SHORTCUT

    def _clear(self) -> None:
        self._poly_length = 0
        self._path_points = []

    def _add_far_from_poly_flags(self, start_far: bool, end_far: bool) -> None:
        if start_far:
            self._type |= PATHFIND_FARFROMPOLY_START
        if end_far:
            self._type |= PATHFIND_FARFROMPOLY_END

    def _normalize_path(self) -> None:
        if self.normalizer is None:
            return
        normalized = []
        for point in self._path_points:
            z = self.normalizer(point[0], point[1], point[2])
            normalized.append((point[0], point[1], z))
        self._path_points = normalized

    def _liquid_status(self, x, y, z) -> int:
        liquid = self.liquid(x, y, z)
        status = getattr(liquid, "status", liquid)
        return int(status)

    def _get_nav_terrain(self, x, y, z):
        from core.terrain.detour.filter import (
            NAV_GROUND, NAV_MAGMA, NAV_WATER,
        )
        if self.liquid is None:
            return NAV_GROUND
        status = self._liquid_status(x, y, z)
        if status == MAP_LIQUID_NO_WATER:
            return NAV_GROUND
        return NAV_WATER

    def _is_water_path(self, points) -> bool:
        from core.terrain.detour.filter import NAV_MAGMA, NAV_WATER
        for p in points:
            terrain = self._get_nav_terrain(p[0], p[1], p[2])
            if terrain not in (NAV_MAGMA, NAV_WATER):
                return False
        return True

    @property
    def path_length(self) -> float:
        if not self._path_points:
            return 0.0
        total = v_dist(self._path_points[0], self._start_position)
        for i in range(1, len(self._path_points)):
            total += v_dist(self._path_points[i], self._path_points[i - 1])
        return total


def _valid_map_coord(x: float, y: float, z: float) -> bool:
    limit = 17066.0  # MAP_HALFSIZE - 0.5
    for c in (x, y, z):
        if not math.isfinite(c) or abs(c) > limit:
            return False
    return True
