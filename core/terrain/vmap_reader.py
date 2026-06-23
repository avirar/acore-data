"""
Binary parser for AzerothCore .vmap files (VMAP_4.8 format).

Parses .vmtree and .vmtile files to extract model spawn information,
BIH tree metadata, and game object model counts.
"""

import struct
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from core.terrain.coords import vmap_tile_filename, vmap_tree_filename


VMAP_MAGIC = b"VMAP_4.8"
RAW_VMAP_MAGIC = b"VMAP048"


class ModelSpawn(NamedTuple):
    """A model spawn entry from a vmap file."""
    id: int
    name: str
    pos_x: float
    pos_y: float
    pos_z: float
    rotation_0: float
    rotation_1: float
    rotation_2: float
    rotation_3: float
    rotation_4: float
    rotation_5: float
    rotation_6: float
    rotation_7: float
    rotation_8: float
    scale: float
    bounding_radius: float
    bounding_center_x: float
    bounding_center_y: float
    bounding_center_z: float
    bounding_min_x: float
    bounding_min_y: float
    bounding_min_z: float
    bounding_max_x: float
    bounding_max_y: float
    bounding_max_z: float


class VMapTileInfo(NamedTuple):
    """Metadata about a vmap tile."""
    map_id: int
    tile_x: int
    tile_y: int
    is_tiled: bool
    model_count: int
    gobject_count: int
    spawn_count: int
    file_size: int
    has_bih_tree: bool


class VMapReader:
    """Reads and parses .vmap files."""

    def __init__(self, vmaps_path: Path):
        self.vmaps_path = vmaps_path
        self._cache: Dict[Tuple[int, int, int], VMapTileInfo] = {}

    def get_tile_info(self, map_id: int, tile_x: int, tile_y: int) -> Optional[VMapTileInfo]:
        """Get info for a specific vmap tile."""
        cache_key = (map_id, tile_x, tile_y)
        if cache_key in self._cache:
            return self._cache[cache_key]

        tile_path = self.vmaps_path / vmap_tile_filename(map_id, tile_x, tile_y)
        if not tile_path.exists():
            return None

        info = self._parse_vmtile(tile_path, map_id, tile_x, tile_y)
        if info:
            self._cache[cache_key] = info
        return info

    def get_tree_info(self, map_id: int) -> Optional[VMapTileInfo]:
        """Get info for the main vmtree file of a map."""
        tree_path = self.vmaps_path / vmap_tree_filename(map_id)
        if not tree_path.exists():
            return None

        return self._parse_vmtree(tree_path, map_id)

    def list_tiles(self, map_id: int) -> List[str]:
        """List all vmap tiles for a map."""
        if not self.vmaps_path.exists():
            return []

        prefix = f"{map_id:03d}_"
        tiles = []
        for f in sorted(self.vmaps_path.iterdir()):
            if f.name.startswith(prefix) and f.suffix == ".vmtile":
                tiles.append(f.name)
        return tiles

    def _parse_vmtile(self, path: Path, map_id: int, tile_x: int, tile_y: int) -> Optional[VMapTileInfo]:
        """Parse a .vmtile file header."""
        return self._parse_vmap_file(path, map_id, tile_x, tile_y, is_tiled=True)

    def _parse_vmtree(self, path: Path, map_id: int) -> Optional[VMapTileInfo]:
        """Parse a .vmtree file header."""
        return self._parse_vmap_file(path, map_id, 0, 0, is_tiled=False)

    def _parse_vmap_file(self, path: Path, map_id: int, tile_x: int, tile_y: int,
                         is_tiled: bool) -> Optional[VMapTileInfo]:
        """Parse vmap file header and extract metadata."""
        with open(path, "rb") as f:
            # Read magic (8 bytes)
            magic = f.read(8)
            if magic != VMAP_MAGIC:
                return None

            # Read tiled flag (1 byte)
            tiled_byte = f.read(1)
            if len(tiled_byte) < 1:
                return None
            _tiled = tiled_byte[0] != 0

            file_size = path.stat().st_size

            # Scan for chunks: NODE (BIH tree) and GOBJ (game objects)
            has_bih = False
            gobject_count = 0
            model_count = 0
            spawn_count = 0

            f.seek(0)
            data = f.read()

            # Find NODE chunk
            node_pos = data.find(b"NODE", 9)
            if node_pos >= 0:
                has_bih = True
                # NODE chunk: "NODE"(4) + nodeCount(4) + ...
                if node_pos + 8 <= len(data):
                    node_count = struct.unpack_from("<I", data, node_pos + 4)[0]
                    model_count = node_count

            # Find GOBJ chunk
            gobj_pos = data.find(b"GOBJ", 9)
            if gobj_pos >= 0:
                # GOBJ chunk: "GOBJ"(4) + modelCount(4) + models...
                if gobj_pos + 8 <= len(data):
                    gobject_count = struct.unpack_from("<I", data, gobj_pos + 4)[0]

            # Count spawn entries by scanning for "SPAW" chunks
            pos = 9  # after magic + tiled byte
            while pos < len(data) - 8:
                chunk = data[pos:pos + 4]
                if chunk == b"SPAW":
                    spawn_count += 1
                    pos += 4
                    if pos < len(data) - 4:
                        spawn_size = struct.unpack_from("<I", data, pos)[0]
                        pos += 4 + spawn_size
                elif chunk == b"NODE" or chunk == b"GOBJ":
                    # Skip these chunks
                    pos += 4
                    if pos < len(data) - 4:
                        chunk_size = struct.unpack_from("<I", data, pos)[0]
                        pos += 4 + chunk_size
                else:
                    pos += 1

            return VMapTileInfo(
                map_id=map_id,
                tile_x=tile_x,
                tile_y=tile_y,
                is_tiled=is_tiled,
                model_count=model_count,
                gobject_count=gobject_count,
                spawn_count=spawn_count,
                file_size=file_size,
                has_bih_tree=has_bih,
            )
