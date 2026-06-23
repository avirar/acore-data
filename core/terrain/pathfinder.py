"""A* pathfinding on Detour navigation mesh with lazy tile loading.

Matches AzerothCore's PathGenerator behavior:
- A* search across tiles with on-demand loading
- Smooth path via corridor steering (funnel algorithm)
- Off-mesh connection support
"""

from __future__ import annotations

import heapq
import math
from typing import Dict, List, Set, Tuple

from core.terrain.detour_parser import DetourParser
from core.terrain.tile_manager import LoadedTile, TileManager


# AzerothCore constants
MAX_PATH_LENGTH = 74
SMOOTH_PATH_STEP_SIZE = 4.0
SMOOTH_PATH_SLOP = 0.3
FAR_FROM_POLY = 50.0


class PathStep:
    """A single step in the raw A* path."""
    __slots__ = ("poly_idx", "tx", "ty", "position")

    def __init__(self, poly_idx: int, tx: int, ty: int, position: Tuple[float, float, float]):
        self.poly_idx = poly_idx
        self.tx = tx
        self.ty = ty
        self.position = position


class SmoothPoint:
    """A point on the smoothed path."""
    __slots__ = ("x", "y", "z", "is_offmesh")

    def __init__(self, x: float, y: float, z: float, is_offmesh: bool = False):
        self.x = x
        self.y = y
        self.z = z
        self.is_offmesh = is_offmesh


class PathResult:
    """Result of a pathfinding query."""
    __slots__ = ("found", "raw_path", "smooth_path", "distance", "error")

    def __init__(self, found: bool, raw_path: List[PathStep],
                 smooth_path: List[SmoothPoint], distance: float, error: str = ""):
        self.found = found
        self.raw_path = raw_path
        self.smooth_path = smooth_path
        self.distance = distance
        self.error = error


class _OpenEntry:
    """A* open-list entry."""
    __slots__ = ("g", "f", "poly", "tx", "ty", "edge_idx")

    def __init__(self, g: float, f: float, poly: int, tx: int, ty: int, edge_idx: int = -1):
        self.g = g
        self.f = f
        self.poly = poly
        self.tx = tx
        self.ty = ty
        self.edge_idx = edge_idx

    def __lt__(self, other: _OpenEntry) -> bool:
        return self.f < other.f


class Pathfinder:
    """A* pathfinder on Detour navmesh with cross-tile support."""

    def __init__(self, tile_manager: TileManager, agent_radius: float = 0.5):
        self._tm = tile_manager
        self._parser = DetourParser()
        self._radius = agent_radius

    def find_path(
        self,
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        flying: bool = False,
    ) -> PathResult:
        """Find path from start to end.

        Coordinates are in world space (x, y, z).
        AC transforms to Detour space as (world_y, world_z, world_x).
        """
        sx, sy, sz = start
        ex, ey, ez = end

        # World -> Detour: (world_y, world_z, world_x)
        dsx, dsy, dsz = sy, sz, sx
        dex, dey, dez = ey, ez, ex

        # Find and load start tile
        start_tile = self._tm.find_tile_at(sx, sy)
        if start_tile is None:
            return PathResult(False, [], [], 0.0, "No mmap tile at start position")
        stx, sty = start_tile
        start_lt = self._tm.ensure_tile(stx, sty)
        if start_lt is None:
            return PathResult(False, [], [], 0.0, "Failed to load start tile")

        self._parser._tile = start_lt.tile  # pylint: disable=protected-access
        start_poly, _ = self._parser.find_nearest_poly(
            (dsx, dsy, dsz), max_dist=FAR_FROM_POLY
        )
        if start_poly < 0:
            return PathResult(False, [], [], 0.0, "No reachable polygon at start")

        # Find and load end tile
        end_tile = self._tm.find_tile_at(ex, ey)
        if end_tile is None:
            return PathResult(False, [], [], 0.0, "No mmap tile at end position")
        etx, ety = end_tile
        end_lt = self._tm.ensure_tile(etx, ety)
        if end_lt is None:
            return PathResult(False, [], [], 0.0, "Failed to load end tile")

        self._parser._tile = end_lt.tile  # pylint: disable=protected-access
        end_poly, _ = self._parser.find_nearest_poly(
            (dex, dey, dez), max_dist=FAR_FROM_POLY
        )
        if end_poly < 0:
            return PathResult(False, [], [], 0.0, "No reachable polygon at end")

        # Same tile, same poly?
        if stx == etx and sty == ety and start_poly == end_poly:
            dist = math.sqrt((sx - ex) ** 2 + (sy - ey) ** 2 + (sz - ez) ** 2)
            sp = [SmoothPoint(sx, sy, sz), SmoothPoint(ex, ey, ez)]
            return PathResult(True, [], sp, dist)

        # Run A*
        raw = self._astar(
            start_poly, stx, sty,
            end_poly, etx, ety,
            (dsx, dsy, dsz), (dex, dey, dez),
        )

        if not raw:
            return PathResult(False, [], [], 0.0, "Path not found (A* failed)")

        # Smooth path in world space (portals are world-space)
        smooth = self._smooth_path(raw, start, end)
        dist = self._path_distance(smooth)
        return PathResult(True, raw, smooth, dist)

    def _astar(
        self,
        start_poly: int, stx: int, sty: int,
        end_poly: int, etx: int, ety: int,
        start_pos: Tuple[float, float, float],
        end_pos: Tuple[float, float, float],
    ) -> List[PathStep]:
        """A* search with on-demand tile loading."""
        open_list: List[_OpenEntry] = []
        heapq.heappush(open_list, _OpenEntry(0.0, 0.0, start_poly, stx, sty))

        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int, int]] = {}
        g_score: Dict[Tuple[int, int, int], float] = {
            (start_poly, stx, sty): 0.0
        }

        iterations = 0
        max_iterations = 200000

        while open_list and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_list)
            state = (current.poly, current.tx, current.ty)

            if current.poly == end_poly and current.tx == etx and current.ty == ety:
                return self._reconstruct_path(came_from, state)

            tile = self._tm.get_tile(current.tx, current.ty)
            if tile is None:
                continue

            self._parser._tile = tile.tile  # pylint: disable=protected-access
            neighbors = self._get_neighbors(current.poly, current.tx, current.ty, tile)

            for nei_poly, nei_tx, nei_ty, edge_idx in neighbors:
                nei_state = (nei_poly, nei_tx, nei_ty)

                nei_tile = self._tm.get_tile(nei_tx, nei_ty)
                if nei_tile is None:
                    nei_tile = self._tm.ensure_tile(nei_tx, nei_ty)
                    if nei_tile is None:
                        continue

                if nei_poly >= len(nei_tile.tile.polygons):
                    continue
                if nei_tile.tile.polygons[nei_poly].is_offmesh:
                    continue

                step_cost = self._step_cost(
                    current.poly, current.tx, current.ty,
                    nei_poly, nei_tx, nei_ty,
                )
                tentative_g = g_score[state] + step_cost

                if tentative_g >= g_score.get(nei_state, float("inf")):
                    continue

                g_score[nei_state] = tentative_g
                h = self._heuristic(nei_poly, nei_tx, nei_ty, end_pos)
                f = tentative_g + h

                came_from[nei_state] = (current.poly, current.tx, current.ty, edge_idx)
                heapq.heappush(
                    open_list,
                    _OpenEntry(tentative_g, f, nei_poly, nei_tx, nei_ty, edge_idx),
                )

        return []

    def _get_neighbors(
        self, poly_idx: int, tx: int, ty: int, lt: LoadedTile
    ) -> List[Tuple[int, int, int, int]]:
        """Get neighboring polygons with on-demand cross-tile resolution.

        AC MMap tiles mark external edges with DT_EXT_LINK (0x8000) | direction,
        not 0xFFFF. Direction: 0=+X, 2=+Z, 4=-X, 6=-Z.
        """
        neighbors: List[Tuple[int, int, int, int]] = []
        tile = lt.tile
        poly = tile.polygons[poly_idx]
        DT_EXT_LINK = 0x8000

        # Detour tile neighbor directions -> (delta_tx, delta_ty)
        # 0=+X, 2=+Z, 4=-X, 6=-Z
        dir_delta = {
            0: (1, 0),
            2: (0, -1),
            4: (-1, 0),
            6: (0, 1),
        }

        for vi in range(poly.vert_count):
            nei_idx = poly.neis[vi]
            if nei_idx & DT_EXT_LINK:
                # External edge - resolve cross-tile link
                direction = nei_idx & 0xFF
                delta = dir_delta.get(direction, (0, 0))
                ntx, nty = tx + delta[0], ty + delta[1]

                # Get edge midpoint for polygon lookup
                vx1 = poly.verts[vi]
                vx2 = poly.verts[(vi + 1) % poly.vert_count]
                v1 = tile.vertices[vx1]
                v2 = tile.vertices[vx2]
                mx = (v1[0] + v2[0]) / 2.0
                my = (v1[1] + v2[1]) / 2.0
                mz = (v1[2] + v2[2]) / 2.0

                resolved = self._resolve_ext_link(
                    ntx, nty, mx, my, mz
                )
                for ext_poly, ext_tx, ext_ty in resolved:
                    neighbors.append((ext_poly, ext_tx, ext_ty, vi))
            elif nei_idx == 0xFFFF:
                # Legacy external edge marker
                cached = self._tm.get_external_links(poly_idx, tx, ty)
                if cached:
                    for ext_poly, ext_tx, ext_ty in cached:
                        neighbors.append((ext_poly, ext_tx, ext_ty, vi))
                else:
                    resolved = self._tm.resolve_external_edge(
                        poly_idx, tx, ty, vi
                    )
                    for ext_poly, ext_tx, ext_ty in resolved:
                        neighbors.append((ext_poly, ext_tx, ext_ty, vi))
            else:
                neighbors.append((nei_idx, tx, ty, vi))

        return neighbors

    def _resolve_ext_link(
        self,
        ntx: int, nty: int,
        mx: float, my: float, mz: float,
    ) -> List[Tuple[int, int, int]]:
        """Resolve an external link to a neighbor polygon.

        Returns list of (neighbor_poly_idx, neighbor_tx, neighbor_ty).
        """
        if ntx < 0 or ntx > 63 or nty < 0 or nty > 63:
            return []

        neighbor_lt = self._tm.get_tile(ntx, nty)
        if neighbor_lt is None:
            neighbor_lt = self._tm.ensure_tile(ntx, nty)
            if neighbor_lt is None:
                return []

        # Clamp query point to neighbor tile bounds
        nb = neighbor_lt.tile
        cx = max(nb.bmin[0], min(nb.bmax[0], mx))
        cy = max(nb.bmin[1], min(nb.bmax[1], my))
        cz = max(nb.bmin[2], min(nb.bmax[2], mz))

        nei_poly = self._tm._find_polygon_at(nb, cx, cz, cy)
        if nei_poly is not None:
            return [(nei_poly, ntx, nty)]

        # Fallback: try with neighbor tile's typical surface height
        if nb.vertices:
            avg_y = sum(v[1] for v in nb.vertices) / len(nb.vertices)
            nei_poly = self._tm._find_polygon_at(nb, cx, cz, avg_y)
            if nei_poly is not None:
                return [(nei_poly, ntx, nty)]

        return []

    def _step_cost(
        self,
        p1: int, tx1: int, ty1: int,
        p2: int, tx2: int, ty2: int,
    ) -> float:
        """Cost to move from one polygon to another."""
        t1 = self._tm.get_tile(tx1, ty1)
        t2 = self._tm.get_tile(tx2, ty2)
        if t1 is None or t2 is None:
            return float("inf")

        c1 = t1.tile.get_poly_center(p1)
        c2 = t2.tile.get_poly_center(p2)
        return math.sqrt(
            (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2
        )

    def _heuristic(
        self, poly_idx: int, tx: int, ty: int,
        end_pos: Tuple[float, float, float],
    ) -> float:
        """Euclidean heuristic on world x,y plane."""
        tile = self._tm.get_tile(tx, ty)
        if tile is None:
            return 0.0
        c = tile.tile.get_poly_center(poly_idx)
        return math.sqrt(
            (c[0] - end_pos[0]) ** 2 + (c[2] - end_pos[2]) ** 2
        )

    def _reconstruct_path(
        self,
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int, int]],
        end_state: Tuple[int, int, int],
    ) -> List[PathStep]:
        """Reconstruct path from came_from map."""
        path: List[PathStep] = []
        state = end_state
        visited: Set[Tuple[int, int, int]] = set()

        while state is not None:
            if state in visited:
                break
            visited.add(state)

            poly_idx, tx, ty = state
            tile = self._tm.get_tile(tx, ty)
            if tile is None:
                break

            center = tile.tile.get_poly_center(poly_idx)
            # Detour (y,z,x) -> world (x,y,z): world_x=Detour_z, world_y=Detour_x, world_z=Detour_y
            world_center = (center[2], center[0], center[1])
            path.append(PathStep(poly_idx, tx, ty, world_center))

            parent = came_from.get(state)
            state = parent[:3] if parent else None

        path.reverse()
        return path[:MAX_PATH_LENGTH]

    def _smooth_path(
        self,
        raw: List[PathStep],
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
    ) -> List[SmoothPoint]:
        """Simplify raw path using funnel algorithm on polygon edge portals."""
        if not raw:
            return [SmoothPoint(*start), SmoothPoint(*end)]

        # Build left/right portals from polygon edge vertices
        portals = self._build_edge_portals(raw)
        if not portals:
            return [SmoothPoint(*start), SmoothPoint(*end)]

        smoothed: List[SmoothPoint] = [SmoothPoint(*start)]

        tail = start
        tail_idx = 0
        left_idx = 0
        right_idx = 0
        is_left_cw = True

        for i in range(1, len(portals)):
            pl = portals[left_idx][0]
            pr = portals[right_idx][1]

            if not self._is_left_of(tail, tail_idx, pl, pr, is_left_cw):
                left_idx = i - 1
                is_left_cw = not self._is_left_of(
                    tail, tail_idx,
                    portals[left_idx][0], portals[right_idx][1],
                    is_left_cw,
                )
            elif self._is_left_of(tail, tail_idx, pr, pl, not is_left_cw):
                right_idx = i - 1
                is_left_cw = not self._is_left_of(
                    tail, tail_idx,
                    portals[left_idx][0], portals[right_idx][1],
                    is_left_cw,
                )
            else:
                apex = portals[left_idx][0] if left_idx < right_idx else portals[right_idx][1]
                smoothed.append(SmoothPoint(*apex))
                tail = apex
                tail_idx = left_idx if left_idx < right_idx else right_idx
                left_idx = i
                right_idx = i
                is_left_cw = True

        # Final point: use last portal midpoint
        last_pl, last_pr = portals[-1]
        apex = ((last_pl[0] + last_pr[0]) / 2,
                (last_pl[1] + last_pr[1]) / 2,
                (last_pl[2] + last_pr[2]) / 2)
        smoothed.append(SmoothPoint(*apex))
        smoothed.append(SmoothPoint(*end))

        return smoothed

        tail = start
        tail_idx = 0
        left_idx = 0
        right_idx = 0
        is_left_cw = True

        for i in range(1, len(portals)):
            portal_left = portals[left_idx]
            portal_right = portals[right_idx]

            if not self._is_left_of(tail, tail_idx, portal_left, portal_right, is_left_cw):
                left_idx = i - 1
                is_left_cw = not self._is_left_of(
                    tail, tail_idx,
                    portals[left_idx], portals[right_idx],
                    is_left_cw,
                )
            elif self._is_left_of(tail, tail_idx, portal_right, portal_left, not is_left_cw):
                right_idx = i - 1
                is_left_cw = not self._is_left_of(
                    tail, tail_idx,
                    portals[left_idx], portals[right_idx],
                    is_left_cw,
                )
            else:
                apex = portals[left_idx] if left_idx < right_idx else portals[right_idx]
                smoothed.append(SmoothPoint(*apex))
                tail = apex
                tail_idx = left_idx if left_idx < right_idx else right_idx
                left_idx = i
                right_idx = i
                is_left_cw = True

        smoothed.append(SmoothPoint(*end))
        return smoothed

    def _build_portals(
        self, raw: List[PathStep]
    ) -> List[Tuple[float, float, float]]:
        """Build portal points from raw path for funnel algorithm."""
        return [step.position for step in raw]

    def _build_edge_portals(
        self, raw: List[PathStep]
    ) -> List[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
        """Build left/right edge portals for funnel algorithm.

        For each consecutive pair of polygons, the shared edge defines
        the portal. Returns list of ((left_vertex), (right_vertex)).
        """
        portals: List[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = []

        for i in range(len(raw) - 1):
            step = raw[i]
            next_step = raw[i + 1]

            tile = self._tm.get_tile(step.tx, step.ty)
            if tile is None:
                continue

            poly = tile.tile.polygons[step.poly_idx]

            # Find the edge that connects to the next polygon
            found = False
            for vi in range(poly.vert_count):
                nei = poly.neis[vi]
                DT_EXT_LINK = 0x8000
                if nei & DT_EXT_LINK:
                    # Cross-tile edge - use edge midpoint
                    vx1 = poly.verts[vi]
                    vx2 = poly.verts[(vi + 1) % poly.vert_count]
                    if vx1 < len(tile.tile.vertices) and vx2 < len(tile.tile.vertices):
                        v1 = tile.tile.vertices[vx1]
                        v2 = tile.tile.vertices[vx2]
                        # Transform from Detour to world
                        w1 = (v1[2], v1[0], v1[1])
                        w2 = (v2[2], v2[0], v2[1])
                        portals.append((w1, w2))
                        found = True
                        break
                elif next_step.tx == step.tx and next_step.ty == step.ty:
                    if nei == next_step.poly_idx:
                        # Internal edge - get the two vertices
                        vx1 = poly.verts[vi]
                        vx2 = poly.verts[(vi + 1) % poly.vert_count]
                        if vx1 < len(tile.tile.vertices) and vx2 < len(tile.tile.vertices):
                            v1 = tile.tile.vertices[vx1]
                            v2 = tile.tile.vertices[vx2]
                            w1 = (v1[2], v1[0], v1[1])
                            w2 = (v2[2], v2[0], v2[1])
                            portals.append((w1, w2))
                            found = True
                            break

            if not found:
                # Fallback: use polygon centers as degenerate portal
                portals.append((step.position, next_step.position))

        return portals

    def _is_left_of(
        self,
        tail: Tuple[float, float, float],
        tail_idx: int,
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
        is_left_cw: bool,
    ) -> bool:
        """Check if tail is left of the line from a to b (2D cross product)."""
        cross = (b[0] - a[0]) * (tail[2] - a[2]) - (b[2] - a[2]) * (tail[0] - a[0])
        return cross >= 0 if is_left_cw else cross <= 0

    def _path_distance(self, smooth: List[SmoothPoint]) -> float:
        """Calculate total path distance."""
        total = 0.0
        for i in range(1, len(smooth)):
            dx = smooth[i].x - smooth[i - 1].x
            dy = smooth[i].y - smooth[i - 1].y
            dz = smooth[i].z - smooth[i - 1].z
            total += math.sqrt(dx * dx + dy * dy + dz * dz)
        return total
