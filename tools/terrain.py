"""
Terrain tool for acore-data.

Server-parity queries against the client terrain data: ADT (.map) heights
and liquids, WMO/M2 vmap raycasts (floors, line of sight, hit positions),
area/zone resolution, and uncapped Detour pathfinding equivalent to the
``.mmap path`` GM command.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.enums import GO_TYPE_NAMES
from core.paths import safe_is_dir
from core.terrain import coords
from core.terrain.detour import (
    DetourFilter,
    NavMesh,
    creature_filter,
    player_filter,
)
from core.terrain.map_reader import (
    LIQUID_TYPE_NO_WATER,
    LIQUID_TYPE_WATER,
    LIQUID_TYPE_OCEAN,
    LIQUID_TYPE_MAGMA,
    LIQUID_TYPE_SLIME,
    INVALID_HEIGHT,
    MapReader,
)
from core.terrain.map_resolver import (
    DEFAULT_COLLISION_HEIGHT,
    MAX_HEIGHT,
    MapResolver,
)
from core.terrain.mmap_reader import MMapReader
from core.terrain.path_generator import (
    PATH_TYPE_NAMES,
    PATHFIND_INCOMPLETE,
    PATHFIND_NOPATH,
    PATHFIND_NORMAL,
    PATHFIND_NOT_USING_PATH,
    PathGenerator,
    UnitProfile,
)
from core.terrain.vmap_reader import VMapReader


# Liquid type/flag name maps
LIQUID_TYPE_NAMES = {
    LIQUID_TYPE_NO_WATER: "NO_WATER",
    LIQUID_TYPE_WATER: "WATER",
    LIQUID_TYPE_OCEAN: "OCEAN",
    LIQUID_TYPE_MAGMA: "MAGMA",
    LIQUID_TYPE_SLIME: "SLIME",
}

LIQUID_STATUS_NAMES = {
    0x00: "NO_WATER",
    0x01: "ABOVE_WATER",
    0x02: "WATER_WALK",
    0x04: "IN_WATER",
    0x08: "UNDER_WATER",
    0x05: "IN_WATER|ABOVE_WATER",
    0x09: "UNDER_WATER|ABOVE_WATER",
    0x06: "IN_WATER|WATER_WALK",
    0x0A: "UNDER_WATER|WATER_WALK",
    0x07: "IN_WATER|WATER_WALK|ABOVE_WATER",
    0x0B: "UNDER_WATER|WATER_WALK|ABOVE_WATER",
    0x0C: "IN_WATER|UNDER_WATER",
    0x0D: "+ABOVE_WATER",
    0x0E: "+WATER_WALK",
    0x0F: "ALL",
}

_RESOLVER_CACHE: Dict[int, MapResolver] = {}
_NAVMESH_CACHE: Dict[int, NavMesh] = {}


def _resolve_map_id(server, map_id_or_name) -> int:
    """Resolve map ID from numeric ID or name."""
    if isinstance(map_id_or_name, (int, float)):
        return int(map_id_or_name)

    try:
        return int(float(str(map_id_or_name)))
    except (ValueError, TypeError):
        pass

    name = str(map_id_or_name).lower()
    try:
        dbcmgr = server._load_dbc("Map")
        for row in dbcmgr.records:
            row_name = row.get(5) or ""
            if row_name and row_name.lower() == name:
                return row[0]
            for i in range(5, 21):
                variant = row.get(i)
                if variant and variant.lower() == name:
                    return row[0]
    except Exception:
        pass

    raise ValueError(f"Unknown map: {map_id_or_name}")


def _get_resolver(server, map_id: int) -> MapResolver:
    resolver = _RESOLVER_CACHE.get(map_id)
    if resolver is None:
        resolver = MapResolver(map_id, dbc_lookup=server._load_dbc)
        _RESOLVER_CACHE[map_id] = resolver
    return resolver


def _get_navmesh(map_id: int) -> NavMesh:
    nav = _NAVMESH_CACHE.get(map_id)
    if nav is None:
        nav = NavMesh(map_id, coords.get_data_paths()["mmaps"])
        _NAVMESH_CACHE[map_id] = nav
    return nav


def _check_coord(args: dict, required: List[str]) -> None:
    for key in required:
        if key not in args or args[key] is None:
            raise ValueError(f"Missing required parameter: {key}")


def _round_point(p, nd: int = 2) -> dict:
    return {"x": round(p[0], nd), "y": round(p[1], nd), "z": round(p[2], nd)}


def _cell_coords(x: float, y: float) -> dict:
    """Port of Acore::ComputeCellCoord + Cell grid/cell accessors."""
    cell_size = coords.GRID_SIZE / 8.0
    cx = max(0, int(256 - x / cell_size))
    cy = max(0, int(256 - y / cell_size))
    return {
        "cell_x": cx % 8, "cell_y": cy % 8,
        "grid_x": cx // 8, "grid_y": cy // 8,
    }


def _liquid_payload(liquid, resolver: MapResolver) -> dict:
    out = {
        "entry": int(liquid.entry),
        "flags": int(liquid.flags),
        "status": int(liquid.status),
        "status_name": LIQUID_STATUS_NAMES.get(liquid.status, f"UNKNOWN({liquid.status})"),
    }
    if liquid.level != INVALID_HEIGHT:
        out["level"] = round(liquid.level, 3)
    if liquid.depth_level != INVALID_HEIGHT:
        out["depth_level"] = round(liquid.depth_level, 3)
    return out


# ---------------------------------------------------------------------------
# listing / metadata
# ---------------------------------------------------------------------------

def _cmd_list_maps(server) -> dict:
    """List maps with file counts for maps/vmaps/mmaps."""
    paths = coords.get_data_paths()
    map_counts: Dict[int, int] = {}
    vmap_counts: Dict[int, int] = {}
    mmap_counts: Dict[int, int] = {}

    if safe_is_dir(paths["maps"]):
        for f in paths["maps"].iterdir():
            if f.suffix == ".map" and f.name[:3].isdigit():
                mid = int(f.name[:3])
                map_counts[mid] = map_counts.get(mid, 0) + 1
    if safe_is_dir(paths["vmaps"]):
        for f in paths["vmaps"].iterdir():
            if f.suffix == ".vmtile" and f.name[:3].isdigit():
                mid = int(f.name[:3])
                vmap_counts[mid] = vmap_counts.get(mid, 0) + 1
    if safe_is_dir(paths["mmaps"]):
        for f in paths["mmaps"].iterdir():
            if f.suffix == ".mmtile" and f.name[:3].isdigit():
                mid = int(f.name[:3])
                mmap_counts[mid] = mmap_counts.get(mid, 0) + 1

    map_names: Dict[int, str] = {}
    try:
        dbcmgr = server._load_dbc("Map")
        for row in dbcmgr.records:
            map_names[row.get(0)] = row.get(5) or ""
    except Exception:
        pass

    result = []
    all_ids = sorted(set(list(map_counts) + list(vmap_counts) + list(mmap_counts)))
    for mid in all_ids:
        result.append({
            "map_id": mid,
            "name": map_names.get(mid, ""),
            "map_files": map_counts.get(mid, 0),
            "vmap_files": vmap_counts.get(mid, 0),
            "mmap_files": mmap_counts.get(mid, 0),
        })
    return {"result": result, "count": len(result)}


def _cmd_list_tiles(server, data_type: str, map_id: int) -> dict:
    paths = coords.get_data_paths()
    if data_type == "maps":
        if not safe_is_dir(paths["maps"]):
            return {"result": [], "count": 0}
        prefix = f"{map_id:03d}"
        tiles = sorted(
            f.name for f in paths["maps"].iterdir()
            if f.name.startswith(prefix) and f.suffix == ".map"
        )
    elif data_type == "vmaps":
        vreader = VMapReader(paths["vmaps"])
        tiles = vreader.list_tiles(map_id)
    elif data_type == "mmaps":
        mreader = MMapReader(paths["mmaps"])
        tiles = mreader.list_tiles(map_id)
    else:
        raise ValueError(f"Invalid data_type: {data_type}. Use 'maps', 'vmaps', or 'mmaps'.")
    return {"result": tiles, "count": len(tiles), "map_id": map_id}


# ---------------------------------------------------------------------------
# heights / liquids / areas
# ---------------------------------------------------------------------------

def _cmd_height(server, map_id: int, x: float, y: float,
                z: Optional[float] = None) -> dict:
    """ADT terrain height and vmap-aware floor height."""
    resolver = _get_resolver(server, map_id)
    tile_x, tile_y = coords.world_to_map_tile(x, y)

    terrain = resolver.get_grid_height(x, y)
    result = {
        "map_id": map_id,
        "position": {"x": x, "y": y},
        "tile": {"x": tile_x, "y": tile_y},
        "terrain_height": round(terrain, 4) if terrain != INVALID_HEIGHT else None,
        "height": round(terrain, 4) if terrain != INVALID_HEIGHT else None,
        "height_type": resolver.get_height_type(x, y),
    }
    if terrain == INVALID_HEIGHT:
        result["error"] = "No terrain data available for this location"

    if z is not None:
        floor = resolver.get_floor_height(x, y, z)
        result["floor_height"] = round(floor, 4) if floor > INVALID_HEIGHT else None
        tree = resolver._tree()
        vmap_height = tree.get_height(x, y, z, 50.0) if tree else None
        if vmap_height is not None and vmap_height != float("inf"):
            result["vmap_height"] = round(vmap_height, 4)
            result["source"] = "vmap"
        else:
            result["vmap_height"] = None
            result["source"] = "terrain" if terrain != INVALID_HEIGHT else "none"
    return result


def _cmd_liquid(server, map_id: int, x: float, y: float, z: float,
                collision_height: float = DEFAULT_COLLISION_HEIGHT) -> dict:
    resolver = _get_resolver(server, map_id)
    liquid = resolver.get_liquid_data(x, y, z, collision_height)
    tile_x, tile_y = coords.world_to_map_tile(x, y)
    result = {
        "map_id": map_id,
        "position": {"x": x, "y": y, "z": z},
        "tile": {"x": tile_x, "y": tile_y},
        "liquid_type": liquid.entry,
        "liquid_flags": liquid.flags,
        "status": liquid.status,
        "status_name": LIQUID_STATUS_NAMES.get(liquid.status, f"UNKNOWN({liquid.status})"),
    }
    if liquid.level != INVALID_HEIGHT:
        result["liquid_level"] = round(liquid.level, 4)
    if liquid.depth_level != INVALID_HEIGHT:
        result["depth_level"] = round(liquid.depth_level, 4)
    return result


def _cmd_area(server, map_id: int, x: float, y: float,
              z: Optional[float] = None) -> dict:
    resolver = _get_resolver(server, map_id)
    tile_x, tile_y = coords.world_to_map_tile(x, y)
    if z is None:
        z = resolver.get_ground_height(x, y)
        if z <= INVALID_HEIGHT:
            z = MAX_HEIGHT
    zone_id, area_id = resolver.get_zone_and_area_id(x, y, z)
    return {
        "map_id": map_id,
        "position": {"x": x, "y": y, "z": z},
        "tile": {"x": tile_x, "y": tile_y},
        "area_id": area_id,
        "area_name": resolver.area_name(area_id),
        "zone_id": zone_id,
        "zone_name": resolver.area_name(zone_id),
    }


def _cmd_position(server, map_id: int, x: float, y: float, z: float,
                  orientation: Optional[float] = None,
                  collision_height: float = DEFAULT_COLLISION_HEIGHT,
                  include_mmap: bool = True) -> dict:
    """`.gps`-equivalent position digest."""
    resolver = _get_resolver(server, map_id)
    status = resolver.get_full_terrain_status(x, y, z, collision_height)
    zone_id, area_id = resolver.get_zone_and_area_id(x, y, z)
    zone_x, zone_y = resolver.map2zone_coordinates(x, y, zone_id)

    grid = coords.world_to_gridcoord(x, y)
    cell = _cell_coords(x, y)

    terrain_z = resolver.get_ground_height(x, y)
    floor_z = resolver.get_floor_height(x, y, z, collision_height)

    vmap_block = None
    vmap_data = resolver.get_vmap_data(x, y, z)
    if vmap_data is not None:
        vmap_block = {"floor_z": round(vmap_data.floor_z, 3)}
        if vmap_data.area is not None:
            vmap_block["wmo"] = {
                "root_id": vmap_data.area.root_id,
                "adt_id": vmap_data.area.adt_id,
                "group_id": vmap_data.area.group_id,
                "mogp_flags": vmap_data.area.mogp_flags,
                "unique_id": vmap_data.area.unique_id,
                "indoors_flag": bool(vmap_data.area.mogp_flags & 0x2000),
                "outdoors_flag": bool(vmap_data.area.mogp_flags & 0x8),
            }
        if vmap_data.liquid is not None:
            vmap_block["liquid"] = {
                "type": vmap_data.liquid[0],
                "level": round(vmap_data.liquid[1], 3),
            }

    result: Dict[str, Any] = {
        "map_id": map_id,
        "map_name": resolver.map_name(),
        "zone": {"id": zone_id, "name": resolver.area_name(zone_id)},
        "area": {"id": area_id, "name": resolver.area_name(area_id)},
        "position": {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)},
        "grid": {"x": grid.x, "y": grid.y},
        "cell": {"grid_x": cell["grid_x"], "grid_y": cell["grid_y"],
                 "cell_x": cell["cell_x"], "cell_y": cell["cell_y"]},
        "zone_coords": {"x": round(zone_x, 2), "y": round(zone_y, 2)},
        "terrain_z": round(terrain_z, 4) if terrain_z > INVALID_HEIGHT else None,
        "floor_z": round(floor_z, 4) if floor_z > INVALID_HEIGHT else None,
        "outdoors": status.outdoors,
        "liquid": _liquid_payload(status.liquid, resolver),
        "have": {
            "map": resolver.get_grid_height(x, y) != INVALID_HEIGHT,
            "vmap": resolver._tree() is not None,
            "mmap": _get_navmesh(map_id).has_navmesh,
        },
        "vmap": vmap_block,
        "metadata": {
            "collision_height": collision_height,
            "note": "static collision only - dynamic game objects/transports "
                    "are not reproducible offline",
        },
    }
    if orientation is not None:
        result["orientation"] = round(orientation, 4)

    if include_mmap:
        nav = _get_navmesh(map_id)
        if nav.has_navmesh:
            point = (y, z, x)  # detour
            ref, closest = nav.find_nearest_poly(point, (3.0, 5.0, 3.0), player_filter())
            if ref:
                tile, poly = nav.poly(ref)
                poly_height = nav.get_poly_height(ref, point)
                dist = ((point[0] - closest[0]) ** 2 + (point[1] - closest[1]) ** 2 +
                        (point[2] - closest[2]) ** 2) ** 0.5 if closest else None
                result["mmap"] = {
                    "found": True,
                    "tile": {"x": tile.tx, "y": tile.ty},
                    "poly": poly.index,
                    "flags": poly.flags,
                    "area": poly.area,
                    "distance": round(dist, 3) if dist is not None else None,
                    "height": round(poly_height, 3) if poly_height is not None else None,
                }
            else:
                result["mmap"] = {"found": False}
        else:
            result["mmap"] = {"found": False, "error": "no mmap data for this map"}
    return result


# ---------------------------------------------------------------------------
# vmap queries
# ---------------------------------------------------------------------------

def _cmd_los(server, map_id: int, x1: float, y1: float, z1: float,
             x2: float, y2: float, z2: float,
             ignore_m2: bool = False) -> dict:
    resolver = _get_resolver(server, map_id)
    visible = resolver.line_of_sight(x1, y1, z1, x2, y2, z2, ignore_m2)
    return {
        "map_id": map_id,
        "from": {"x": x1, "y": y1, "z": z1},
        "to": {"x": x2, "y": y2, "z": z2},
        "visible": visible,
        "blocked": not visible,
        "ignore_m2": ignore_m2,
        "note": "static geometric LOS (vmap only; dynamic objects excluded)",
    }


def _cmd_raycast(server, map_id: int, x1: float, y1: float, z1: float,
                 x2: float, y2: float, z2: float,
                 modify_dist: float = 0.0) -> dict:
    resolver = _get_resolver(server, map_id)
    hit, hx, hy, hz = resolver.get_object_hit_pos(
        x1, y1, z1, x2, y2, z2, modify_dist
    )
    return {
        "map_id": map_id,
        "from": {"x": x1, "y": y1, "z": z1},
        "to": {"x": x2, "y": y2, "z": z2},
        "hit": hit,
        "position": {"x": round(hx, 4), "y": round(hy, 4), "z": round(hz, 4)},
        "modify_dist": modify_dist,
    }


# ---------------------------------------------------------------------------
# area map (SVG export)
# ---------------------------------------------------------------------------

_TRIGGER_PATTERNS = ("world trigger", "invisible stalker", "trigger")
_GO_DECOR_TYPES = {5, 7}  # GENERIC / CHAIR benches & seats: clutter, not walls
_CREATURE_RANK_NAMES = {0: "normal", 1: "elite", 2: "rare elite",
                        3: "world boss", 4: "rare"}


def _coords_sub(x: float, y: float, z: float) -> str:
    return f"{x:.1f}, {y:.1f}, {z:.1f}"


def _area_map_query(server, sql: str, params: list):
    rows, err = server.database._query_database(sql, db_name="acore_world",
                                                params=params)
    if err:
        return None, err
    return (rows or []), None


def _is_trigger_name(name: str) -> bool:
    n = (name or "").lower()
    return any(p in n for p in _TRIGGER_PATTERNS)


def _parse_endpoint(value, what: str) -> tuple:
    if (isinstance(value, (list, tuple)) and len(value) == 3 and
            all(isinstance(v, (int, float)) for v in value)):
        return tuple(float(v) for v in value)
    raise ValueError(f"{what} must be [x, y, z] numbers, got: {value!r}")


def _map_name(server, map_id: int) -> str:
    try:
        return _get_resolver(server, map_id).map_name()
    except Exception:
        return str(map_id)


def _cmd_area_map(server, map_id: int, args: dict) -> dict:
    """Render an obstacle-aware SVG map of a region: navmesh mesh, labeled
    spawn points, navmesh paths and LOS rays."""
    import hashlib
    import tempfile
    from core.terrain.area_map import (
        AreaMapError,
        Bounds,
        DEFAULT_MAX_POLYS,
        DEFAULT_MAX_SPAN,
        DEFAULT_Z_BAND,
        collect_mesh,
        render_svg,
    )

    nav = _get_navmesh(map_id)
    if not nav.has_navmesh:
        return {"error": f"No navmesh data for map {map_id}", "isError": True}

    warnings: List[str] = []
    z = float(args["z"]) if args.get("z") is not None else None
    z_band = float(args.get("z_band", DEFAULT_Z_BAND))

    # ---- bounds -----------------------------------------------------------
    max_span = float(args.get("max_span", DEFAULT_MAX_SPAN))
    pad = float(args.get("padding", 25.0))
    bounds: Optional[Bounds] = None
    if all(args.get(k) is not None for k in ("x1", "y1", "x2", "y2")):
        bounds = Bounds(
            min(float(args["x1"]), float(args["x2"])),
            min(float(args["y1"]), float(args["y2"])),
            max(float(args["x1"]), float(args["x2"])),
            max(float(args["y1"]), float(args["y2"])),
        )
    elif args.get("centerX") is not None and args.get("centerY") is not None:
        size = float(args.get("size", 200.0))
        if size <= 0:
            raise ValueError("size must be > 0")
        cx, cy = float(args["centerX"]), float(args["centerY"])
        bounds = Bounds(cx - size / 2.0, cy - size / 2.0,
                        cx + size / 2.0, cy + size / 2.0)

    sql_failed = False
    if bounds is None:
        spans = []
        for table in ("creature", "gameobject"):
            rows, err = _area_map_query(
                server,
                f"SELECT MIN(position_x) AS minx, MAX(position_x) AS maxx, "
                f"MIN(position_y) AS miny, MAX(position_y) AS maxy "
                f"FROM {table} WHERE map = %s",
                [map_id],
            )
            if err:
                sql_failed = True
                continue
            row = rows[0] if rows else None
            if row and row.get("minx") is not None:
                spans.append((float(row["minx"]), float(row["miny"]),
                              float(row["maxx"]), float(row["maxy"])))
        if not spans:
            if sql_failed:
                return {"error": "SQL unavailable and no explicit bounds given; "
                                "pass x1/y1/x2/y2 or centerX/centerY/size",
                        "isError": True}
            return {"error": f"No spawns found on map {map_id} to auto-fit "
                             f"bounds; pass x1/y1/x2/y2 or "
                             f"centerX/centerY/size",
                    "isError": True}
        bounds = Bounds(min(s[0] for s in spans) - pad,
                        min(s[1] for s in spans) - pad,
                        max(s[2] for s in spans) + pad,
                        max(s[3] for s in spans) + pad)
    if bounds.span_x > max_span or bounds.span_y > max_span:
        return {"error": f"area_map: bounds span {bounds.span_x:.0f}x"
                         f"{bounds.span_y:.0f}yd exceeds max_span="
                         f"{max_span:.0f}; shrink the region or raise max_span",
                "isError": True}

    # ---- points from SQL (degrade to mesh-only when the DB is down) --------
    points_mode = str(args.get("points_mode", "named")).lower()
    if points_mode not in ("named", "all", "none"):
        raise ValueError("points_mode must be 'named', 'all' or 'none'")
    go_mode = str(args.get("gameobjects", "key")).lower()
    if go_mode not in ("key", "all", "none"):
        raise ValueError("gameobjects must be 'key', 'all' or 'none'")
    show_triggers = bool(args.get("triggers", True))

    points: List[Dict[str, Any]] = []
    counts = {"creatures": 0, "gameobjects": 0, "triggers": 0}
    bbox_sql = ("position_x BETWEEN %s AND %s AND position_y BETWEEN %s AND %s")
    bbox_params = [bounds.minx, bounds.maxx, bounds.miny, bounds.maxy]

    if points_mode != "none":
        rows, err = _area_map_query(
            server,
            "SELECT c.id AS entry, ct.name, ct.`rank` AS cr_rank, "
            "ct.minlevel, ct.maxlevel, "
            "c.position_x AS x, c.position_y AS y, c.position_z AS z "
            "FROM creature c JOIN creature_template ct ON c.id = ct.entry "
            f"WHERE c.map = %s AND {bbox_sql}",
            [map_id] + bbox_params,
        )
        if err:
            warnings.append(f"SQL unavailable, creature points omitted: {err}")
            sql_failed = True
        else:
            for row in rows:
                pz = float(row["z"])
                if z is not None and abs(pz - z) > z_band:
                    continue
                name = row.get("name") or f"creature {row['entry']}"
                if _is_trigger_name(name):
                    if show_triggers:
                        points.append({
                            "x": float(row["x"]), "y": float(row["y"]), "z": pz,
                            "label": f"{name} ({row['entry']})",
                            "sub": _coords_sub(float(row["x"]),
                                               float(row["y"]), pz),
                            "kind": "trigger"})
                        counts["triggers"] += 1
                    continue
                if points_mode == "named" and not int(row.get("cr_rank") or 0):
                    continue
                rank = int(row.get("cr_rank") or 0)
                minl = int(row.get("minlevel") or 0)
                maxl = int(row.get("maxlevel") or 0)
                lvl = (f"L{minl}-{maxl}" if minl and minl != maxl
                       else f"L{maxl}")
                points.append({
                    "x": float(row["x"]), "y": float(row["y"]), "z": pz,
                    "label": f"{name} ({row['entry']})",
                    "sub": f"{_CREATURE_RANK_NAMES.get(rank, str(rank))}, "
                           f"{lvl} · {_coords_sub(float(row['x']), float(row['y']), pz)}",
                    "kind": "creature"})
                counts["creatures"] += 1

    if go_mode != "none":
        type_filter = f"AND gt.type NOT IN ({','.join(str(t) for t in sorted(_GO_DECOR_TYPES))})" \
            if go_mode == "key" else ""
        rows, err = _area_map_query(
            server,
            "SELECT g.id AS entry, gt.name, gt.type AS got_type, "
            "g.position_x AS x, g.position_y AS y, g.position_z AS z "
            "FROM gameobject g JOIN gameobject_template gt ON g.id = gt.entry "
            f"WHERE g.map = %s AND {bbox_sql} {type_filter}",
            [map_id] + bbox_params,
        )
        if err:
            warnings.append(f"SQL unavailable, gameobject points omitted: {err}")
            sql_failed = True
        else:
            for row in rows:
                pz = float(row["z"])
                if z is not None and abs(pz - z) > z_band:
                    continue
                name = row.get("name") or f"gameobject {row['entry']}"
                go_type = int(row.get("got_type") or 0)
                sub = (f"{GO_TYPE_NAMES.get(go_type, f'type{go_type}').lower()}"
                       f" · {_coords_sub(float(row['x']), float(row['y']), pz)}")
                points.append({
                    "x": float(row["x"]), "y": float(row["y"]), "z": pz,
                    "label": f"{name} ({row['entry']})",
                    "sub": sub,
                    "kind": "gameobject"})
                counts["gameobjects"] += 1

    # ---- paths + LOS rays ---------------------------------------------------
    paths: List[Dict[str, Any]] = []
    for i, spec in enumerate(args.get("paths") or []):
        if not isinstance(spec, dict):
            raise ValueError(f"paths[{i}] must be an object with from/to")
        fx, fy, fz = _parse_endpoint(spec.get("from"), f"paths[{i}].from")
        tx, ty, tz = _parse_endpoint(spec.get("to"), f"paths[{i}].to")
        mode = str(spec.get("mode") or "smooth").lower()
        label = spec.get("label") or f"path {i + 1}"
        try:
            pf = _cmd_pathfind(server, map_id, fx, fy, fz, tx, ty, tz,
                               {"mode": mode, "limit": 4000})
        except (ValueError, IndexError) as e:
            warnings.append(f"{label}: pathfind failed: {e}")
            continue
        if pf.get("error"):
            warnings.append(f"{label}: {pf['error']}")
            continue
        paths.append({
            "label": label,
            "ok": bool(pf.get("found")),
            "distance": pf.get("distance"),
            "points": [(p["x"], p["y"], p["z"]) for p in pf.get("points", [])],
        })

    rays: List[Dict[str, Any]] = []
    for i, spec in enumerate(args.get("rays") or []):
        if not isinstance(spec, dict):
            raise ValueError(f"rays[{i}] must be an object with from/to")
        fx, fy, fz = _parse_endpoint(spec.get("from"), f"rays[{i}].from")
        tx, ty, tz = _parse_endpoint(spec.get("to"), f"rays[{i}].to")
        los = _cmd_los(server, map_id, fx, fy, fz, tx, ty, tz)
        rays.append({"x1": fx, "y1": fy, "z1": fz,
                     "x2": tx, "y2": ty, "z2": tz,
                     "visible": bool(los.get("visible")),
                     "label": spec.get("label") or f"ray {i + 1}"})

    # ---- render + write ------------------------------------------------------
    try:
        mesh = collect_mesh(nav, bounds,
                            max_polys=int(args.get("max_polys",
                                                   DEFAULT_MAX_POLYS)),
                            z=z, z_band=z_band)
        svg = render_svg(
            map_id, _map_name(server, map_id), bounds, mesh, points,
            paths, rays,
            mesh_style=str(args.get("mesh_style", "height")).lower(),
            scale=float(args.get("scale", 4.0)),
            grid=float(args.get("grid", 50.0)),
            labels=bool(args.get("labels", True)),
            label_limit=int(args.get("label_limit", 60)),
        )
    except AreaMapError as e:
        return {"error": str(e), "isError": True}

    out = args.get("out")
    if not out:
        out_dir = Path(tempfile.gettempdir()) / "acore-area-maps"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = hashlib.sha1(
            f"{map_id}:{bounds.minx}:{bounds.miny}:{bounds.maxx}:"
            f"{bounds.maxy}".encode()
        ).hexdigest()[:10]
        out = str(out_dir / f"{map_id:03d}_{slug}.svg")
    Path(out).write_text(svg, encoding="utf-8")

    counts["paths"] = len(paths)
    counts["rays"] = len(rays)
    counts["polys_drawn"] = len(mesh["polys"])
    counts["polys_total"] = mesh["poly_total"]
    counts["offmesh"] = len(mesh["offmesh"])
    counts["tiles"] = mesh["tile_count"]

    payload: Dict[str, Any] = {
        "map_id": map_id,
        "map_name": _map_name(server, map_id),
        "bounds": {"x1": bounds.minx, "y1": bounds.miny,
                   "x2": bounds.maxx, "y2": bounds.maxy},
        "out": str(out),
        "bytes": len(svg.encode("utf-8")),
        "counts": counts,
        "warnings": warnings,
        "metadata": {
            "note": "static collision only - dynamic game objects/transports "
                    "are not in the offline navmesh",
            **({"z_filter": {"z": z, "band": z_band}} if z is not None else {}),
        },
    }
    if args.get("inline"):
        payload["svg"] = svg
    return payload


# ---------------------------------------------------------------------------
# pathfinding
# ---------------------------------------------------------------------------

def _cmd_pathfind(server, map_id: int, x1: float, y1: float, z1: float,
                  x2: float, y2: float, z2: float, args: dict) -> dict:
    nav = _get_navmesh(map_id)
    if not nav.has_navmesh:
        return {"error": f"No navmesh data for map {map_id}", "isError": True}

    mode = str(args.get("mode") or "smooth").lower()
    if mode not in ("smooth", "straight", "raycast"):
        raise ValueError(f"Invalid mode: {mode}. Use 'smooth', 'straight' or 'raycast'.")

    unit = str(args.get("unit") or "player").lower()
    if args.get("flying"):
        unit = "flying"
    if unit not in ("player", "creature", "flying"):
        raise ValueError(f"Invalid unit: {unit}. Use 'player', 'creature' or 'flying'.")

    normalize = args.get("normalize", True)
    max_nodes = args.get("max_nodes")
    max_polys = args.get("max_polys")
    max_points = args.get("max_points")
    limit = int(args.get("limit", 2000))

    if unit == "flying":
        points = [(x1, y1, z1), (x2, y2, z2)]
        distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2) ** 0.5
        payload = _path_payload(map_id, "flying", PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH,
                                points, [], (x1, y1, z1), (x2, y2, z2),
                                (x2, y2, z2), distance, limit)
        payload["metadata"]["note"] = "flying/shortcut: navmesh not used"
        return payload

    resolver = _get_resolver(server, map_id)
    profile = UnitProfile(
        can_swim=True,
        can_fly=False,
        collision_height=float(args.get("collision_height", DEFAULT_COLLISION_HEIGHT)),
    )
    filt: DetourFilter
    if unit == "creature":
        filt = creature_filter(can_walk=True, can_swim=True)
    else:
        filt = player_filter(headless=bool(args.get("headless", False)))

    normalizer = None
    if normalize:
        profile_dict = {
            "can_swim": True,
            "can_fly": False,
            "hover_height": 0.0,
            "collision_height": profile.collision_height,
            "collision_width": profile.collision_height,
        }
        normalizer = lambda px, py, pz: resolver.update_allowed_position_z(
            px, py, pz, profile_dict
        )

    liquid = lambda px, py, pz: resolver.get_liquid_data(
        px, py, pz, profile.collision_height
    )

    pg = PathGenerator(
        nav, filt=filt, profile=profile, normalizer=normalizer,
        liquid=liquid, max_nodes=max_nodes,
    )
    pg.set_max_polys(max_polys)
    pg.set_max_points(max_points)
    if mode == "straight":
        pg.set_use_straight_path(True)
    elif mode == "raycast":
        pg.set_use_raycast(True)

    ok = pg.calculate_path(x1, y1, z1, x2, y2, z2)
    if not ok:
        return {"error": "Invalid map coordinates", "isError": True}

    payload = _path_payload(
        map_id, mode, pg.path_type, pg.path_points, pg.poly_refs,
        pg.start_position, pg.end_position, pg.actual_end_position,
        pg.path_length, limit,
    )
    payload["max_nodes_exceeded"] = pg._max_nodes_exceeded
    return payload


def _path_payload(map_id: int, mode: str, path_type: int, points, poly_refs,
                  start, end, actual_end, distance: float, limit: int) -> dict:
    names = [name for flag, name in PATH_TYPE_NAMES.items()
             if flag and (path_type & flag)]
    shown = points[:limit] if limit > 0 else points
    result = {
        "map_id": map_id,
        "mode": mode,
        "found": not (path_type & PATHFIND_NOPATH),
        "path_type": path_type,
        "path_type_names": names,
        "partial": bool(path_type & PATHFIND_INCOMPLETE),
        "start": _round_point(start),
        "end": _round_point(end),
        "actual_end": _round_point(actual_end),
        "distance": round(distance, 2),
        "point_count": len(points),
        "poly_count": len(poly_refs),
        "points": [_round_point(p) for p in shown],
        "metadata": {
            "note": "smooth mode matches the server's '.mmap path' output "
                    "(4-yard steps on the navmesh surface)",
        },
    }
    if len(points) > len(shown):
        result["points_truncated"] = True
    return result


# ---------------------------------------------------------------------------
# tiles / navmesh metadata
# ---------------------------------------------------------------------------

def _cmd_tile_info(server, map_id: int, tile_x: int, tile_y: int,
                   data_type: str) -> dict:
    paths = coords.get_data_paths()
    if data_type == "mmaps":
        mreader = MMapReader(paths["mmaps"])
        info = mreader.get_tile_info(map_id, tile_x, tile_y)
        if not info:
            return {"error": f"MMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}
        result = {
            "map_id": map_id,
            "tile": {"x": tile_x, "y": tile_y},
            "file_size": info.file_size,
        }
        if info.mmap_header:
            mh = info.mmap_header
            result["mmap_header"] = {
                "version": mh.mmap_version,
                "dt_version": mh.dt_version,
                "size": mh.size,
                "uses_liquids": mh.uses_liquids,
            }
            rc = mh.recast_config
            result["recast_config"] = {
                "walkable_slope_angle": rc.walkable_slope_angle,
                "walkable_radius": rc.walkable_radius,
                "walkable_height": rc.walkable_height,
                "walkable_climb": rc.walkable_climb,
                "cell_size_horizontal": rc.cell_size_horizontal,
                "cell_size_vertical": rc.cell_size_vertical,
                "max_simplification_error": rc.max_simplification_error,
                "vertex_per_tile_edge": rc.vertex_per_tile_edge,
            }
        if info.detour_header:
            dh = info.detour_header
            result["detour_header"] = {
                "version": dh.version,
                "tile_position": {"x": dh.x, "y": dh.y, "layer": dh.layer},
                "user_id": dh.user_id,
                "poly_count": dh.poly_count,
                "vert_count": dh.vert_count,
                "detail_mesh_count": dh.detail_mesh_count,
                "detail_vert_count": dh.detail_vert_count,
                "detail_tri_count": dh.detail_tri_count,
                "bv_node_count": dh.bv_node_count,
                "off_mesh_con_count": dh.off_mesh_con_count,
                "bounds": {
                    "min": {"x": dh.bmin[0], "y": dh.bmin[1], "z": dh.bmin[2]},
                    "max": {"x": dh.bmax[0], "y": dh.bmax[1], "z": dh.bmax[2]},
                },
            }
        return result

    if data_type == "vmaps":
        vreader = VMapReader(paths["vmaps"])
        info = vreader.get_tile_info(map_id, tile_x, tile_y)
        if not info:
            return {"error": f"VMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}
        return {
            "map_id": map_id,
            "tile": {"x": tile_x, "y": tile_y},
            "is_tiled": info.is_tiled,
            "spawn_count": info.spawn_count,
            "model_count": info.model_count,
            "wmo_spawns": info.wmo_spawns,
            "gobject_count": info.gobject_count,
            "file_size": info.file_size,
            "has_bih_tree": info.has_bih_tree,
        }
    raise ValueError(f"Invalid data_type: {data_type}. Use 'mmaps' or 'vmaps'.")


def _cmd_vmap_info(server, map_id: int, tile_x: Optional[int] = None,
                   tile_y: Optional[int] = None) -> dict:
    paths = coords.get_data_paths()
    vreader = VMapReader(paths["vmaps"])

    if tile_x is not None and tile_y is not None:
        info = vreader.get_tile_info(map_id, tile_x, tile_y)
        if not info:
            return {"error": f"VMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}
        return {
            "map_id": map_id,
            "tile": {"x": tile_x, "y": tile_y},
            "is_tiled": info.is_tiled,
            "spawn_count": info.spawn_count,
            "model_count": info.model_count,
            "wmo_spawns": info.wmo_spawns,
            "gobject_count": info.gobject_count,
            "file_size": info.file_size,
            "has_bih_tree": info.has_bih_tree,
            "models": list(info.models),
        }

    info = vreader.get_tree_info(map_id)
    if not info:
        return {"error": f"VMap tree not found for map {map_id}"}
    tiles = vreader.list_tiles(map_id)
    return {
        "map_id": map_id,
        "tree": {
            "is_tiled": info.is_tiled,
            "model_count": info.model_count,
            "gobject_count": info.gobject_count,
            "file_size": info.file_size,
            "has_bih_tree": info.has_bih_tree,
        },
        "tile_count": len(tiles),
        "tiles": tiles[:20],
    }


def _cmd_tile_stats(server, map_id: int, tile_x: int, tile_y: int) -> dict:
    paths = coords.get_data_paths()
    mreader = MMapReader(paths["mmaps"])
    stats = mreader.get_tile_stats(map_id, tile_x, tile_y)
    if not stats:
        return {"error": f"MMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}
    return stats


def _cmd_map_info(server, map_id: int) -> dict:
    paths = coords.get_data_paths()
    mreader = MMapReader(paths["mmaps"])
    return mreader.get_main_info(map_id)


def _cmd_coord(server, x: float, y: float) -> dict:
    grid = coords.world_to_gridcoord(x, y)
    map_tile = coords.world_to_map_tile(x, y)
    vmap_tile = coords.world_to_vmap_tile(x, y)
    mmap_tile = coords.world_to_mmap_tile(x, y)
    return {
        "world": {"x": x, "y": y},
        "grid": {"x": grid.x, "y": grid.y},
        "map_tile": {"x": map_tile[0], "y": map_tile[1]},
        "vmap_tile": {"x": vmap_tile[0], "y": vmap_tile[1]},
        "mmap_tile": {"x": mmap_tile[0], "y": mmap_tile[1]},
        "valid": coords.is_valid_world_coord(x, y),
    }


# ---------------------------------------------------------------------------
# dispatch / schema
# ---------------------------------------------------------------------------

def terrain_tools(server) -> dict:
    args = server.args
    subcommand = args.get("subcommand", "")
    data_type = args.get("data_type", "maps")

    if subcommand == "list_maps":
        return _cmd_list_maps(server)
    if subcommand == "list_tiles":
        _check_coord(args, ["mapId"])
        return _cmd_list_tiles(server, data_type, _resolve_map_id(server, args["mapId"]))
    if subcommand == "height":
        _check_coord(args, ["mapId", "x", "y"])
        return _cmd_height(server, _resolve_map_id(server, args["mapId"]),
                           float(args["x"]), float(args["y"]),
                           float(args["z"]) if args.get("z") is not None else None)
    if subcommand == "position":
        _check_coord(args, ["mapId", "x", "y", "z"])
        return _cmd_position(
            server, _resolve_map_id(server, args["mapId"]),
            float(args["x"]), float(args["y"]), float(args["z"]),
            float(args["orientation"]) if args.get("orientation") is not None else None,
            float(args.get("collision_height", DEFAULT_COLLISION_HEIGHT)),
            bool(args.get("include_mmap", True)),
        )
    if subcommand == "liquid":
        _check_coord(args, ["mapId", "x", "y", "z"])
        return _cmd_liquid(
            server, _resolve_map_id(server, args["mapId"]),
            float(args["x"]), float(args["y"]), float(args["z"]),
            float(args.get("collision_height", DEFAULT_COLLISION_HEIGHT)),
        )
    if subcommand == "area":
        _check_coord(args, ["mapId", "x", "y"])
        return _cmd_area(server, _resolve_map_id(server, args["mapId"]),
                         float(args["x"]), float(args["y"]),
                         float(args["z"]) if args.get("z") is not None else None)
    if subcommand == "coord":
        _check_coord(args, ["x", "y"])
        return _cmd_coord(server, float(args["x"]), float(args["y"]))
    if subcommand == "tile_info":
        _check_coord(args, ["mapId", "tileX", "tileY"])
        return _cmd_tile_info(server, _resolve_map_id(server, args["mapId"]),
                              int(args["tileX"]), int(args["tileY"]), data_type)
    if subcommand == "vmap_info":
        _check_coord(args, ["mapId"])
        tx = args.get("tileX")
        ty = args.get("tileY")
        return _cmd_vmap_info(server, _resolve_map_id(server, args["mapId"]),
                              int(tx) if tx is not None else None,
                              int(ty) if ty is not None else None)
    if subcommand == "tile_stats":
        _check_coord(args, ["mapId", "tileX", "tileY"])
        return _cmd_tile_stats(server, _resolve_map_id(server, args["mapId"]),
                               int(args["tileX"]), int(args["tileY"]))
    if subcommand == "map_info":
        _check_coord(args, ["mapId"])
        return _cmd_map_info(server, _resolve_map_id(server, args["mapId"]))
    if subcommand == "pathfind":
        _check_coord(args, ["mapId", "x1", "y1", "z1", "x2", "y2", "z2"])
        return _cmd_pathfind(
            server, _resolve_map_id(server, args["mapId"]),
            float(args["x1"]), float(args["y1"]), float(args["z1"]),
            float(args["x2"]), float(args["y2"]), float(args["z2"]),
            args,
        )
    if subcommand == "los":
        _check_coord(args, ["mapId", "x1", "y1", "z1", "x2", "y2", "z2"])
        return _cmd_los(
            server, _resolve_map_id(server, args["mapId"]),
            float(args["x1"]), float(args["y1"]), float(args["z1"]),
            float(args["x2"]), float(args["y2"]), float(args["z2"]),
            bool(args.get("ignore_m2", False)),
        )
    if subcommand == "raycast":
        _check_coord(args, ["mapId", "x1", "y1", "z1", "x2", "y2", "z2"])
        return _cmd_raycast(
            server, _resolve_map_id(server, args["mapId"]),
            float(args["x1"]), float(args["y1"]), float(args["z1"]),
            float(args["x2"]), float(args["y2"]), float(args["z2"]),
            float(args.get("modify_dist", 0.0)),
        )
    if subcommand == "area_map":
        _check_coord(args, ["mapId"])
        return _cmd_area_map(server, _resolve_map_id(server, args["mapId"]), args)

    valid = [
        "list_maps", "list_tiles", "height", "position", "liquid", "area",
        "coord", "tile_info", "vmap_info", "tile_stats", "map_info",
        "pathfind", "los", "raycast", "area_map",
    ]
    return {"error": f"Unknown subcommand: {subcommand}", "valid_subcommands": valid}


def get_schema() -> dict:
    """Tool schema for MCP."""
    return {
        "name": "terrain",
        "description": (
            "Query map/vmap/mmap terrain data the way the server does. "
            "Subcommands: list_maps, list_tiles, height (ADT + vmap floor), "
            "position (.gps-equivalent: terrain/floor Z, area/zone, liquid, "
            "indoors/outdoors, nearest navmesh poly), liquid, area, coord, "
            "tile_info, vmap_info, tile_stats, map_info, "
            "pathfind (server '.mmap path' semantics; modes smooth|straight|"
            "raycast, uncapped by default), los, raycast, "
            "area_map (obstacle-aware SVG map of a region: navmesh mesh, "
            "labeled creature/gameobject/trigger points, path polylines, "
            "LOS rays)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subcommand": {
                    "type": "string",
                    "enum": [
                        "list_maps", "list_tiles", "height", "position", "liquid",
                        "area", "coord", "tile_info", "vmap_info", "tile_stats",
                        "map_info", "pathfind", "los", "raycast", "area_map",
                    ],
                    "description": "Terrain subcommand to execute.",
                },
                "mapId": {
                    "type": ["number", "string"],
                    "description": "Map ID (numeric) or map name (string).",
                },
                "x": {"type": "number", "description": "World X coordinate."},
                "y": {"type": "number", "description": "World Y coordinate."},
                "z": {
                    "type": "number",
                    "description": "World Z coordinate (required for position/liquid).",
                },
                "orientation": {
                    "type": "number",
                    "description": "Optional orientation (radians) echoed in position output.",
                },
                "tileX": {"type": "number", "description": "Tile X coordinate (0-63)."},
                "tileY": {"type": "number", "description": "Tile Y coordinate (0-63)."},
                "data_type": {
                    "type": "string",
                    "enum": ["maps", "vmaps", "mmaps"],
                    "description": "Data type for list_tiles/tile_info. Default: 'maps'.",
                },
                "x1": {"type": "number", "description": "Start X (pathfind/los/raycast)."},
                "y1": {"type": "number", "description": "Start Y (pathfind/los/raycast)."},
                "z1": {"type": "number", "description": "Start Z (pathfind/los/raycast)."},
                "x2": {"type": "number", "description": "End X (pathfind/los/raycast)."},
                "y2": {"type": "number", "description": "End Y (pathfind/los/raycast)."},
                "z2": {"type": "number", "description": "End Z (pathfind/los/raycast)."},
                "mode": {
                    "type": "string",
                    "enum": ["smooth", "straight", "raycast"],
                    "description": "Pathfind mode: smooth (default, '.mmap path'), "
                                   "straight ('.mmap path true'), raycast ('.mmap path ray').",
                },
                "unit": {
                    "type": "string",
                    "enum": ["player", "creature", "flying"],
                    "description": "Movement profile for navmesh filters (default player).",
                },
                "normalize": {
                    "type": "boolean",
                    "description": "Clamp path points to the server's allowed floor "
                                   "(default true, requires vmaps).",
                },
                "flying": {
                    "type": "boolean",
                    "description": "Legacy alias for unit='flying' (returns a 2-point shortcut).",
                },
                "headless": {
                    "type": "boolean",
                    "description": "Use the stricter playerbots filter "
                                   "(no steep slopes, avoid water).",
                },
                "collision_height": {
                    "type": "number",
                    "description": "Unit collision height for Z offset/normalization "
                                   "(default 2.03128).",
                },
                "max_nodes": {
                    "type": "number",
                    "description": "A* search node cap (default unlimited; server uses 1024).",
                },
                "max_polys": {
                    "type": "number",
                    "description": "Poly path cap (default unlimited; server uses 74/148).",
                },
                "max_points": {
                    "type": "number",
                    "description": "Point path cap (default unlimited; server uses 74/148).",
                },
                "limit": {
                    "type": "number",
                    "description": "Max path points returned in the response (default 2000).",
                },
                "ignore_m2": {
                    "type": "boolean",
                    "description": "LOS only: ignore M2 doodad collision.",
                },
                "modify_dist": {
                    "type": "number",
                    "description": "Raycast only: distance offset applied to the hit point.",
                },
                "include_mmap": {
                    "type": "boolean",
                    "description": "Position only: include nearest navmesh poly info (default true).",
                },
                "centerX": {
                    "type": "number",
                    "description": "area_map only: bounds center X (with centerY/size).",
                },
                "centerY": {
                    "type": "number",
                    "description": "area_map only: bounds center Y (with centerX/size).",
                },
                "size": {
                    "type": "number",
                    "description": "area_map only: square bounds side in yards (default 200).",
                },
                "padding": {
                    "type": "number",
                    "description": "area_map only: yards added around auto-fitted bounds (default 25).",
                },
                "z": {
                    "type": "number",
                    "description": "area_map only: filter mesh/points to one dungeon floor "
                                   "(polys within z +- z_band); recommended in multi-floor "
                                   "instances.",
                },
                "z_band": {
                    "type": "number",
                    "description": "area_map only: half-height of the z filter band "
                                   "(default 25 yards).",
                },
                "points_mode": {
                    "type": "string",
                    "enum": ["named", "all", "none"],
                    "description": "area_map only: creature points; 'named' = rank > 0 "
                                   "plus triggers (default), 'all', 'none'.",
                },
                "gameobjects": {
                    "type": "string",
                    "enum": ["key", "all", "none"],
                    "description": "area_map only: GO points; 'key' excludes decor types "
                                   "GENERIC/CHAIR (default), 'all', 'none'.",
                },
                "triggers": {
                    "type": "boolean",
                    "description": "area_map only: include World Trigger / Invisible Stalker "
                                   "spawn points (default true).",
                },
                "labels": {
                    "type": "boolean",
                    "description": "area_map only: draw name labels (default true).",
                },
                "label_limit": {
                    "type": "number",
                    "description": "area_map only: max labeled points, in creature > "
                                   "gameobject > trigger order (default 60).",
                },
                "mesh_style": {
                    "type": "string",
                    "enum": ["height", "outline", "wire"],
                    "description": "area_map only: 'height' = fills colored by floor Z "
                                   "(default), 'outline' = white fills, 'wire' = no fills.",
                },
                "scale": {
                    "type": "number",
                    "description": "area_map only: SVG pixels per yard (default 4, "
                                   "shrunk to fit the 6000px canvas cap).",
                },
                "grid": {
                    "type": "number",
                    "description": "area_map only: grid/tick spacing in yards (default 50, "
                                   "0 disables).",
                },
                "out": {
                    "type": "string",
                    "description": "area_map only: SVG output path (default "
                                   "<tempdir>/acore-area-maps/<map>_<hash>.svg).",
                },
                "inline": {
                    "type": "boolean",
                    "description": "area_map only: also return the SVG string in the "
                                   "response (default false).",
                },
                "max_span": {
                    "type": "number",
                    "description": "area_map only: max bounds span per axis in yards "
                                   "(default 3000).",
                },
                "max_polys": {
                    "type": "number",
                    "description": "area_map only: max navmesh polys to draw (default "
                                   "40000).",
                },
                "paths": {
                    "type": "array",
                    "description": "area_map only: navmesh path polylines to draw.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {
                                "type": "array", "items": {"type": "number"},
                                "minItems": 3, "maxItems": 3,
                                "description": "[x, y, z] start.",
                            },
                            "to": {
                                "type": "array", "items": {"type": "number"},
                                "minItems": 3, "maxItems": 3,
                                "description": "[x, y, z] end.",
                            },
                            "mode": {
                                "type": "string",
                                "description": "pathfind mode (default smooth).",
                            },
                            "label": {"type": "string"},
                        },
                        "required": ["from", "to"],
                    },
                },
                "rays": {
                    "type": "array",
                    "description": "area_map only: LOS rays to draw (green = clear, "
                                   "orange = blocked).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {
                                "type": "array", "items": {"type": "number"},
                                "minItems": 3, "maxItems": 3,
                                "description": "[x, y, z] start.",
                            },
                            "to": {
                                "type": "array", "items": {"type": "number"},
                                "minItems": 3, "maxItems": 3,
                                "description": "[x, y, z] end.",
                            },
                            "label": {"type": "string"},
                        },
                        "required": ["from", "to"],
                    },
                },
            },
            "required": ["subcommand"],
        },
    }
