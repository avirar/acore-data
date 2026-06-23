"""
Terrain tool for acore-data.

Provides query access to map/vmap/mmap terrain data: height queries,
area/liquid lookups, tile listings, navmesh stats, and coordinate conversions.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.terrain import coords
from core.terrain.pathfinder import Pathfinder
from core.terrain.tile_manager import TileManager
from core.terrain.map_reader import (
    LIQUID_TYPE_NO_WATER,
    LIQUID_TYPE_WATER,
    LIQUID_TYPE_OCEAN,
    LIQUID_TYPE_MAGMA,
    LIQUID_TYPE_SLIME,
    LIQUID_STATUS_NO_WATER,
    LIQUID_STATUS_ABOVE_WATER,
    LIQUID_STATUS_WATER_WALK,
    LIQUID_STATUS_IN_WATER,
    LIQUID_STATUS_UNDER_WATER,
    INVALID_HEIGHT,
    MapReader,
)
from core.terrain.vmap_reader import VMapReader
from core.terrain.mmap_reader import MMapReader


# Liquid type/flag name maps
LIQUID_TYPE_NAMES = {
    LIQUID_TYPE_NO_WATER: "NO_WATER",
    LIQUID_TYPE_WATER: "WATER",
    LIQUID_TYPE_OCEAN: "OCEAN",
    LIQUID_TYPE_MAGMA: "MAGMA",
    LIQUID_TYPE_SLIME: "SLIME",
}

LIQUID_STATUS_NAMES = {
    LIQUID_STATUS_NO_WATER: "NO_WATER",
    LIQUID_STATUS_ABOVE_WATER: "ABOVE_WATER",
    LIQUID_STATUS_WATER_WALK: "WATER_WALK",
    LIQUID_STATUS_IN_WATER: "IN_WATER",
    LIQUID_STATUS_UNDER_WATER: "UNDER_WATER",
}


def _resolve_map_id(server, map_id_or_name) -> int:
    """Resolve map ID from numeric ID or name."""
    if isinstance(map_id_or_name, (int, float)):
        return int(map_id_or_name)

    # Try parsing as numeric string first
    try:
        return int(float(str(map_id_or_name)))
    except (ValueError, TypeError):
        pass

    name = str(map_id_or_name).lower()
    try:
        dbcmgr = server._load_dbc("Map")
        for row in dbcmgr.rows:
            # name[0] is at index 5
            row_name = row[5] if len(row) > 5 else ""
            if row_name and row_name.lower() == name:
                return row[0]  # MapID at index 0
    except Exception:
        pass

    # Try all language variants
    try:
        dbcmgr = server._load_dbc("Map")
        for row in dbcmgr.rows:
            for i in range(5, 21):  # name[0] through name[15]
                if i < len(row) and row[i] and row[i].lower() == name:
                    return row[0]
    except Exception:
        pass

    raise ValueError(f"Unknown map: {map_id_or_name}")


def _check_coord(args: dict, required: List[str]) -> None:
    """Check required coordinate args are present."""
    for key in required:
        if key not in args or args[key] is None:
            raise ValueError(f"Missing required parameter: {key}")


def _cmd_list_maps(server) -> dict:
    """List maps with file counts for maps/vmaps/mmaps."""
    paths = coords.get_data_paths()

    # Count .map files per map ID
    map_counts: Dict[int, int] = {}
    if paths["maps"].exists():
        for f in paths["maps"].iterdir():
            if f.suffix == ".map" and len(f.stem) >= 5:
                mid = int(f.stem[:3])
                map_counts[mid] = map_counts.get(mid, 0) + 1

    # Count .vmtile files per map ID
    vmap_counts: Dict[int, int] = {}
    if paths["vmaps"].exists():
        for f in paths["vmaps"].iterdir():
            if f.suffix == ".vmtile" and len(f.stem) >= 4:
                mid = int(f.stem[:3])
                vmap_counts[mid] = vmap_counts.get(mid, 0) + 1

    # Count .mmtile files per map ID
    mmap_counts: Dict[int, int] = {}
    if paths["mmaps"].exists():
        for f in paths["mmaps"].iterdir():
            if f.suffix == ".mmtile" and len(f.stem) >= 5:
                mid = int(f.stem[:3])
                mmap_counts[mid] = mmap_counts.get(mid, 0) + 1

    # Get map names from DBC
    map_names: Dict[int, str] = {}
    try:
        dbcmgr = server._load_dbc("Map")
        for row in dbcmgr.rows:
            mid = row[0]
            name = row[5] if len(row) > 5 else ""
            map_names[mid] = name
    except Exception:
        pass

    # Build result
    all_ids = sorted(set(list(map_counts.keys()) + list(vmap_counts.keys()) + list(mmap_counts.keys())))

    result = []
    for mid in all_ids:
        entry = {
            "map_id": mid,
            "name": map_names.get(mid, ""),
            "map_files": map_counts.get(mid, 0),
            "vmap_files": vmap_counts.get(mid, 0),
            "mmap_files": mmap_counts.get(mid, 0),
        }
        result.append(entry)

    return {"result": result, "count": len(result)}


def _cmd_list_tiles(server, data_type: str, map_id: int) -> dict:
    """List tiles for a map."""
    paths = coords.get_data_paths()

    if data_type == "maps":
        if not paths["maps"].exists():
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


def _cmd_height(server, map_id: int, x: float, y: float) -> dict:
    """Get terrain height at world coordinates."""
    paths = coords.get_data_paths()
    reader = MapReader(paths["maps"])

    height = reader.get_height(map_id, x, y)

    # Get tile info
    tile_x, tile_y = coords.world_to_map_tile(x, y)
    tile = reader.get_tile(map_id, tile_x, tile_y)

    result = {
        "map_id": map_id,
        "position": {"x": x, "y": y},
        "tile": {"x": tile_x, "y": tile_y},
    }

    if height != INVALID_HEIGHT:
        result["height"] = round(height, 4)
    else:
        result["height"] = None
        result["error"] = "No terrain data available for this location"

    if tile and tile.height:
        result["tile_info"] = {
            "height_type": tile.height.height_type,
            "grid_height": round(tile.height.grid_height, 4),
            "grid_max_height": round(tile.height.grid_max_height, 4),
        }

    return result


def _cmd_liquid(server, map_id: int, x: float, y: float, z: float) -> dict:
    """Get liquid data at world coordinates."""
    paths = coords.get_data_paths()
    reader = MapReader(paths["maps"])

    liquid = reader.get_liquid(map_id, x, y, z)

    tile_x, tile_y = coords.world_to_map_tile(x, y)

    result = {
        "map_id": map_id,
        "position": {"x": x, "y": y, "z": z},
        "tile": {"x": tile_x, "y": tile_y},
        "liquid_type": liquid["type"],
        "liquid_type_name": LIQUID_TYPE_NAMES.get(liquid["type"], f"UNKNOWN({liquid['type']})"),
        "status": liquid["status"],
        "status_name": LIQUID_STATUS_NAMES.get(liquid["status"], f"UNKNOWN({liquid['status']})"),
    }

    if liquid["level"] != INVALID_HEIGHT:
        result["liquid_level"] = round(liquid["level"], 4)
    if liquid["depth_level"] != INVALID_HEIGHT:
        result["depth_level"] = round(liquid["depth_level"], 4)
    if liquid["flags"]:
        result["liquid_flags"] = liquid["flags"]

    return result


def _cmd_area(server, map_id: int, x: float, y: float) -> dict:
    """Get area ID at world coordinates."""
    paths = coords.get_data_paths()
    reader = MapReader(paths["maps"])

    area_id = reader.get_area(map_id, x, y)
    tile_x, tile_y = coords.world_to_map_tile(x, y)

    return {
        "map_id": map_id,
        "position": {"x": x, "y": y},
        "tile": {"x": tile_x, "y": tile_y},
        "area_id": area_id,
    }


def _cmd_coord(server, x: float, y: float) -> dict:
    """Convert world coordinates to grid/tile coordinates."""
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


def _cmd_tile_info(server, map_id: int, tile_x: int, tile_y: int, data_type: str) -> dict:
    """Get info for a specific tile (mmap or vmap)."""
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

    elif data_type == "vmaps":
        vreader = VMapReader(paths["vmaps"])
        info = vreader.get_tile_info(map_id, tile_x, tile_y)
        if not info:
            return {"error": f"VMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}

        return {
            "map_id": map_id,
            "tile": {"x": tile_x, "y": tile_y},
            "is_tiled": info.is_tiled,
            "model_count": info.model_count,
            "gobject_count": info.gobject_count,
            "spawn_count": info.spawn_count,
            "file_size": info.file_size,
            "has_bih_tree": info.has_bih_tree,
        }

    else:
        raise ValueError(f"Invalid data_type: {data_type}. Use 'mmaps' or 'vmaps'.")


def _cmd_vmap_info(server, map_id: int, tile_x: Optional[int] = None,
                   tile_y: Optional[int] = None) -> dict:
    """Get vmap info for a map (tree or specific tile)."""
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
            "model_count": info.model_count,
            "gobject_count": info.gobject_count,
            "spawn_count": info.spawn_count,
            "file_size": info.file_size,
            "has_bih_tree": info.has_bih_tree,
        }
    else:
        info = vreader.get_tree_info(map_id)
        if not info:
            return {"error": f"VMap tree not found for map {map_id}"}

        tiles = vreader.list_tiles(map_id)
        return {
            "map_id": map_id,
            "tree": {
                "model_count": info.model_count,
                "gobject_count": info.gobject_count,
                "spawn_count": info.spawn_count,
                "file_size": info.file_size,
                "has_bih_tree": info.has_bih_tree,
            },
            "tile_count": len(tiles),
            "tiles": tiles[:20],  # First 20 tiles
        }


def _cmd_tile_stats(server, map_id: int, tile_x: int, tile_y: int) -> dict:
    """Get navmesh stats for an mmap tile."""
    paths = coords.get_data_paths()
    mreader = MMapReader(paths["mmaps"])
    stats = mreader.get_tile_stats(map_id, tile_x, tile_y)
    if not stats:
        return {"error": f"MMap tile not found: map {map_id}, tile ({tile_x}, {tile_y})"}
    return stats


def _cmd_map_info(server, map_id: int) -> dict:
    """Get main mmap navmesh info for a map."""
    paths = coords.get_data_paths()
    mreader = MMapReader(paths["mmaps"])
    return mreader.get_main_info(map_id)


def _cmd_pathfind(server, map_id: int, x1: float, y1: float, z1: float,
                   x2: float, y2: float, z2: float,
                   flying: bool = False) -> dict:
    """Find path between two points on the navmesh."""
    paths = coords.get_data_paths()
    tm = TileManager(map_id, paths["mmaps"])
    pf = Pathfinder(tm)
    result = pf.find_path((x1, y1, z1), (x2, y2, z2), flying=flying)

    return {
        "map_id": map_id,
        "found": result.found,
        "distance": round(result.distance, 2),
        "raw_path_length": len(result.raw_path),
        "smooth_path_length": len(result.smooth_path),
        "raw_path": [
            {"poly": s.poly_idx, "tile": (s.tx, s.ty),
             "position": {"x": round(s.position[0], 2),
                          "y": round(s.position[1], 2),
                          "z": round(s.position[2], 2)}}
            for s in result.raw_path
        ],
        "smooth_path": [
            {"x": round(p.x, 2), "y": round(p.y, 2), "z": round(p.z, 2),
             "is_offmesh": p.is_offmesh}
            for p in result.smooth_path
        ],
        "error": result.error,
    }


def terrain_tools(server) -> dict:
    """Dispatch terrain tool subcommands."""
    args = server.args
    subcommand = args.get("subcommand", "")
    data_type = args.get("data_type", "maps")

    if subcommand == "list_maps":
        return _cmd_list_maps(server)

    elif subcommand == "list_tiles":
        _check_coord(args, ["mapId"])
        return _cmd_list_tiles(server, data_type, _resolve_map_id(server, args["mapId"]))

    elif subcommand == "height":
        _check_coord(args, ["mapId", "x", "y"])
        return _cmd_height(server, _resolve_map_id(server, args["mapId"]),
                           float(args["x"]), float(args["y"]))

    elif subcommand == "liquid":
        _check_coord(args, ["mapId", "x", "y", "z"])
        return _cmd_liquid(server, _resolve_map_id(server, args["mapId"]),
                           float(args["x"]), float(args["y"]), float(args["z"]))

    elif subcommand == "area":
        _check_coord(args, ["mapId", "x", "y"])
        return _cmd_area(server, _resolve_map_id(server, args["mapId"]),
                         float(args["x"]), float(args["y"]))

    elif subcommand == "coord":
        _check_coord(args, ["x", "y"])
        return _cmd_coord(server, float(args["x"]), float(args["y"]))

    elif subcommand == "tile_info":
        _check_coord(args, ["mapId", "tileX", "tileY"])
        return _cmd_tile_info(server, _resolve_map_id(server, args["mapId"]),
                              int(args["tileX"]), int(args["tileY"]), data_type)

    elif subcommand == "vmap_info":
        _check_coord(args, ["mapId"])
        tx = args.get("tileX")
        ty = args.get("tileY")
        return _cmd_vmap_info(server, _resolve_map_id(server, args["mapId"]),
                              int(tx) if tx is not None else None,
                              int(ty) if ty is not None else None)

    elif subcommand == "tile_stats":
        _check_coord(args, ["mapId", "tileX", "tileY"])
        return _cmd_tile_stats(server, _resolve_map_id(server, args["mapId"]),
                               int(args["tileX"]), int(args["tileY"]))

    elif subcommand == "map_info":
        _check_coord(args, ["mapId"])
        return _cmd_map_info(server, _resolve_map_id(server, args["mapId"]))

    elif subcommand == "pathfind":
        _check_coord(args, ["mapId", "x1", "y1", "z1", "x2", "y2", "z2"])
        return _cmd_pathfind(
            server,
            _resolve_map_id(server, args["mapId"]),
            float(args["x1"]), float(args["y1"]), float(args["z1"]),
            float(args["x2"]), float(args["y2"]), float(args["z2"]),
            bool(args.get("flying", False)),
        )

    else:
        valid = [
            "list_maps", "list_tiles", "height", "liquid", "area",
            "coord", "tile_info", "vmap_info", "tile_stats", "map_info",
            "pathfind",
        ]
        return {
            "error": f"Unknown subcommand: {subcommand}",
            "valid_subcommands": valid,
        }


def get_schema() -> dict:
    """Tool schema for MCP."""
    return {
        "name": "terrain",
        "description": (
            "Query map/vmap/mmap terrain data. Subcommands: "
            "list_maps (list maps with file counts), "
            "list_tiles (list tiles for a map), "
            "height (terrain height at coords), "
            "liquid (liquid data at coords), "
            "area (area ID at coords), "
            "coord (world to grid/tile conversion), "
            "tile_info (mmap/vmap tile header info), "
            "vmap_info (vmap model info), "
            "tile_stats (navmesh stats), "
            "map_info (main mmap navmesh params), "
            "pathfind (find path between two points)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subcommand": {
                    "type": "string",
                    "enum": [
                        "list_maps", "list_tiles", "height", "liquid", "area",
                        "coord", "tile_info", "vmap_info", "tile_stats", "map_info",
                        "pathfind",
                    ],
                    "description": "Terrain subcommand to execute.",
                },
                "mapId": {
                    "type": ["number", "string"],
                    "description": (
                        "Map ID (numeric) or map name (string, e.g. 'Eastern Kingdoms')."
                    ),
                },
                "x": {
                    "type": "number",
                    "description": "World X coordinate.",
                },
                "y": {
                    "type": "number",
                    "description": "World Y coordinate.",
                },
                "z": {
                    "type": "number",
                    "description": "World Z coordinate (required for 'liquid' subcommand).",
                },
                "tileX": {
                    "type": "number",
                    "description": "Tile X coordinate (0-63).",
                },
                "tileY": {
                    "type": "number",
                    "description": "Tile Y coordinate (0-63).",
                },
                "data_type": {
                    "type": "string",
                    "enum": ["maps", "vmaps", "mmaps"],
                    "description": (
                        "Data type for list_tiles/tile_info. Default: 'maps'."
                    ),
                },
                "x1": {
                    "type": "number",
                    "description": "Start X coordinate (for pathfind).",
                },
                "y1": {
                    "type": "number",
                    "description": "Start Y coordinate (for pathfind).",
                },
                "z1": {
                    "type": "number",
                    "description": "Start Z coordinate (for pathfind).",
                },
                "x2": {
                    "type": "number",
                    "description": "End X coordinate (for pathfind).",
                },
                "y2": {
                    "type": "number",
                    "description": "End Y coordinate (for pathfind).",
                },
                "z2": {
                    "type": "number",
                    "description": "End Z coordinate (for pathfind).",
                },
                "flying": {
                    "type": "boolean",
                    "description": "Ignore height constraints (for pathfind).",
                },
            },
            "required": ["subcommand"],
        },
    }
