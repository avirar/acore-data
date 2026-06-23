"""
Terrain data access module for acore-data.
"""

from core.terrain.coords import (
    GRID_SIZE,
    MAX_GRIDS,
    MAP_SIZE,
    GridCoord,
    TileCoord,
    get_data_paths,
    is_valid_gridcoord,
    is_valid_world_coord,
    local_tile_to_world,
    map_tile_filename,
    mmap_main_filename,
    mmap_tile_filename,
    world_to_gridcoord,
    world_to_local_tile,
    world_to_map_tile,
    world_to_mmap_tile,
    world_to_vmap_tile,
)

__all__ = [
    "GRID_SIZE",
    "MAX_GRIDS",
    "MAP_SIZE",
    "GridCoord",
    "TileCoord",
    "get_data_paths",
    "is_valid_gridcoord",
    "is_valid_world_coord",
    "local_tile_to_world",
    "map_tile_filename",
    "mmap_main_filename",
    "mmap_tile_filename",
    "world_to_gridcoord",
    "world_to_local_tile",
    "world_to_map_tile",
    "world_to_mmap_tile",
    "world_to_vmap_tile",
]
