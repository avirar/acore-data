"""
Binary parser for AzerothCore .map terrain files.

Parses the MAPS v9 format: area IDs, height maps (float/uint16/uint8),
liquid type/flags/levels, and hole data. Provides bilinear interpolation
for height queries at arbitrary world coordinates.
"""

import struct
from pathlib import Path
from typing import Dict, NamedTuple, Optional, Tuple

from core.terrain.coords import (
    GRID_SIZE,
    MAP_TILE_VERTS_V9,
    world_to_map_tile,
)


# Magic constants
MAP_MAGIC = b"MAPS"
MAP_VERSION = 9
AREA_MAGIC = b"AREA"
HEIGHT_MAGIC = b"MHGT"
LIQUID_MAGIC = b"MLIQ"

# Header flags
MAP_AREA_NO_AREA = 0x0001
MAP_HEIGHT_NO_HEIGHT = 0x0001
MAP_HEIGHT_AS_INT16 = 0x0002
MAP_HEIGHT_AS_INT8 = 0x0004
MAP_HEIGHT_HAS_FLIGHT_BOUNDS = 0x0008
MAP_LIQUID_NO_TYPE = 0x0001
MAP_LIQUID_NO_HEIGHT = 0x0002

# Liquid types
LIQUID_TYPE_NO_WATER = 0x00
LIQUID_TYPE_WATER = 0x01
LIQUID_TYPE_OCEAN = 0x02
LIQUID_TYPE_MAGMA = 0x04
LIQUID_TYPE_SLIME = 0x08

# Liquid status flags
LIQUID_STATUS_NO_WATER = 0x00
LIQUID_STATUS_ABOVE_WATER = 0x01
LIQUID_STATUS_WATER_WALK = 0x02
LIQUID_STATUS_IN_WATER = 0x04
LIQUID_STATUS_UNDER_WATER = 0x08

INVALID_HEIGHT = -100000.0


class MapFileHeader(NamedTuple):
    """Parsed .map file header."""
    magic: bytes
    version: int
    build: int
    area_offset: int
    area_size: int
    height_offset: int
    height_size: int
    liquid_offset: int
    liquid_size: int
    holes_offset: int
    holes_size: int


class AreaData(NamedTuple):
    """Parsed area data for a map tile."""
    grid_area: int
    area_map: list  # 16x16 array of uint16 area IDs


class HeightData(NamedTuple):
    """Parsed height data for a map tile."""
    grid_height: float
    grid_max_height: float
    height_type: str  # "float", "uint16", "uint8", "flat"
    heights: list  # 129x129 or 128x128 array
    multiplier: float  # for uint16/uint8 types


class LiquidData(NamedTuple):
    """Parsed liquid data for a map tile."""
    liquid_level: float
    liquid_width: int
    liquid_height: int
    liquid_off_x: int
    liquid_off_y: int
    liquid_types: list  # 16x16 array of liquid type IDs
    liquid_flags: list  # 16x16 array of liquid flag bytes
    liquid_map: list  # variable-size liquid height map


class MapTile:
    """Parsed .map tile with area, height, and liquid data."""

    def __init__(self, map_id: int, tile_x: int, tile_y: int):
        self.map_id = map_id
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.area: Optional[AreaData] = None
        self.height: Optional[HeightData] = None
        self.liquid: Optional[LiquidData] = None

    def get_height(self, local_x: float, local_y: float) -> float:
        """Get interpolated height at local tile coordinates (0-1 range)."""
        if not self.height:
            return INVALID_HEIGHT

        if self.height.height_type == "flat":
            return self.height.grid_height

        size = len(self.height.heights)
        if size == 0:
            return INVALID_HEIGHT

        # 129x129 grid means 128 cells, each cell has 4 vertices
        # local coords 0-1 map to grid indices 0-(size-1)
        grid_size = size - 1  # 128 for v9

        # Convert local coords to grid position
        fx = local_x * grid_size
        fy = local_y * grid_size

        # Clamp to valid range
        fx = max(0.0, min(grid_size, fx))
        fy = max(0.0, min(grid_size, fy))

        # Bilinear interpolation
        ix = int(fx)
        iy = int(fy)
        dx = fx - ix
        dy = fy - iy

        ix_next = min(ix + 1, grid_size)
        iy_next = min(iy + 1, grid_size)

        h00 = self.height.heights[iy][ix]
        h10 = self.height.heights[iy][ix_next]
        h01 = self.height.heights[iy_next][ix]
        h11 = self.height.heights[iy_next][ix_next]

        if self.height.height_type in ("uint16", "uint8"):
            h00 = self.height.grid_height + h00 * self.height.multiplier
            h10 = self.height.grid_height + h10 * self.height.multiplier
            h01 = self.height.grid_height + h01 * self.height.multiplier
            h11 = self.height.grid_height + h11 * self.height.multiplier

        # Bilinear interpolate
        h_top = h00 * (1 - dx) + h10 * dx
        h_bot = h01 * (1 - dx) + h11 * dx
        return h_top * (1 - dy) + h_bot * dy

    def get_area(self, local_x: float, local_y: float) -> int:
        """Get area ID at local tile coordinates."""
        if not self.area or not self.area.area_map:
            return self.area.grid_area if self.area else 0

        grid_size = 16
        fx = local_x * grid_size
        fy = local_y * grid_size

        ix = max(0, min(15, int(fx)))
        iy = max(0, min(15, int(fy)))

        return self.area.area_map[iy][ix]

    def get_liquid_status(self, local_x: float, local_y: float,
                          world_z: float) -> dict:
        """Get liquid status at local tile coordinates.

        Returns dict with: type, level, flags, status, depth_level
        """
        if not self.liquid:
            return {
                "type": LIQUID_TYPE_NO_WATER,
                "level": INVALID_HEIGHT,
                "flags": 0,
                "status": LIQUID_STATUS_NO_WATER,
                "depth_level": INVALID_HEIGHT,
            }

        grid_size = 16
        fx = local_x * grid_size
        fy = local_y * grid_size

        ix = max(0, min(15, int(fx)))
        iy = max(0, min(15, int(fy)))

        liquid_type = self.liquid.liquid_types[iy][ix] if self.liquid.liquid_types else LIQUID_TYPE_NO_WATER
        liquid_flag = self.liquid.liquid_flags[iy][ix] if self.liquid.liquid_flags else 0

        if liquid_type == LIQUID_TYPE_NO_WATER:
            return {
                "type": LIQUID_TYPE_NO_WATER,
                "level": INVALID_HEIGHT,
                "flags": 0,
                "status": LIQUID_STATUS_NO_WATER,
                "depth_level": INVALID_HEIGHT,
            }

        # Calculate liquid level
        if self.liquid.liquid_map and len(self.liquid.liquid_map) > 0:
            # Interpolate from liquid height map
            off_x = self.liquid.liquid_off_x
            off_y = self.liquid.liquid_off_y
            width = self.liquid.liquid_width
            height = self.liquid.liquid_height

            map_x = (ix - off_x) * width
            map_y = (iy - off_y) * height

            if (0 <= map_x < len(self.liquid.liquid_map) and
                    0 <= map_y < len(self.liquid.liquid_map[0])):
                liquid_level = self.liquid.liquid_level + self.liquid.liquid_map[map_x][map_y]
            else:
                liquid_level = self.liquid.liquid_level
        else:
            liquid_level = self.liquid.liquid_level

        # Determine status based on Z position relative to liquid level
        status = LIQUID_STATUS_NO_WATER
        depth_level = INVALID_HEIGHT

        if world_z > liquid_level:
            status = LIQUID_STATUS_ABOVE_WATER
        elif world_z == liquid_level:
            status = LIQUID_STATUS_WATER_WALK
            depth_level = liquid_level
        else:
            status = LIQUID_STATUS_IN_WATER | LIQUID_STATUS_UNDER_WATER
            depth_level = liquid_level

        return {
            "type": liquid_type,
            "level": liquid_level,
            "flags": liquid_flag,
            "status": status,
            "depth_level": depth_level,
        }


class MapReader:
    """Reads and caches .map terrain files."""

    def __init__(self, maps_path: Path):
        self.maps_path = maps_path
        self._cache: Dict[Tuple[int, int, int], MapTile] = {}

    def _get_tile_path(self, map_id: int, tile_x: int, tile_y: int) -> Path:
        from core.terrain.coords import map_tile_filename
        return self.maps_path / map_tile_filename(map_id, tile_x, tile_y)

    def get_tile(self, map_id: int, tile_x: int, tile_y: int) -> Optional[MapTile]:
        """Get or load a map tile. Returns None if file doesn't exist."""
        cache_key = (map_id, tile_x, tile_y)
        if cache_key in self._cache:
            return self._cache[cache_key]

        tile_path = self._get_tile_path(map_id, tile_x, tile_y)
        if not tile_path.exists():
            return None

        tile = MapTile(map_id, tile_x, tile_y)
        try:
            self._parse_file(tile_path, tile)
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse {tile_path.name}: {e}"
            ) from e

        self._cache[cache_key] = tile
        return tile

    def get_height(self, map_id: int, world_x: float, world_y: float) -> float:
        """Get terrain height at world coordinates."""
        tile_x, tile_y = world_to_map_tile(world_x, world_y)
        tile = self.get_tile(map_id, tile_x, tile_y)
        if not tile:
            return INVALID_HEIGHT

        from core.terrain.coords import world_to_local_tile
        local_x, local_y = world_to_local_tile(world_x, world_y, tile_x, tile_y)
        return tile.get_height(local_x, local_y)

    def get_area(self, map_id: int, world_x: float, world_y: float) -> int:
        """Get area ID at world coordinates."""
        tile_x, tile_y = world_to_map_tile(world_x, world_y)
        tile = self.get_tile(map_id, tile_x, tile_y)
        if not tile:
            return 0

        from core.terrain.coords import world_to_local_tile
        local_x, local_y = world_to_local_tile(world_x, world_y, tile_x, tile_y)
        return tile.get_area(local_x, local_y)

    def get_liquid(self, map_id: int, world_x: float, world_y: float,
                   world_z: float) -> dict:
        """Get liquid data at world coordinates."""
        tile_x, tile_y = world_to_map_tile(world_x, world_y)
        tile = self.get_tile(map_id, tile_x, tile_y)
        if not tile:
            return {
                "type": LIQUID_TYPE_NO_WATER,
                "level": INVALID_HEIGHT,
                "flags": 0,
                "status": LIQUID_STATUS_NO_WATER,
                "depth_level": INVALID_HEIGHT,
            }

        from core.terrain.coords import world_to_local_tile
        local_x, local_y = world_to_local_tile(world_x, world_y, tile_x, tile_y)
        return tile.get_liquid_status(local_x, local_y, world_z)

    def _parse_file(self, path: Path, tile: MapTile) -> None:
        """Parse a .map binary file."""
        with open(path, "rb") as f:
            data = f.read()

        # Parse file header (40 bytes)
        if len(data) < 40:
            raise ValueError("File too small for map header")

        magic = data[0:4]
        if magic != MAP_MAGIC:
            raise ValueError(f"Invalid map magic: {magic!r}, expected {MAP_MAGIC!r}")

        version, build = struct.unpack_from("<II", data, 4)
        if version != MAP_VERSION:
            raise ValueError(f"Unsupported map version: {version}")

        (area_offset, area_size, height_offset, height_size,
         liquid_offset, liquid_size, holes_offset, holes_size
         ) = struct.unpack_from("<IIIIIIII", data, 12)

        # Parse area data
        if area_offset > 0 and area_size > 0:
            tile.area = self._parse_area(data, area_offset, area_size)

        # Parse height data
        if height_offset > 0 and height_size > 0:
            tile.height = self._parse_height(data, height_offset, height_size)

        # Parse liquid data
        if liquid_offset > 0 and liquid_size > 0:
            tile.liquid = self._parse_liquid(data, liquid_offset, liquid_size)

    def _parse_area(self, data: bytes, offset: int, size: int) -> AreaData:
        """Parse area section: AREA magic + header + 16x16 grid."""
        magic = data[offset:offset + 4]
        if magic != AREA_MAGIC:
            raise ValueError(f"Invalid area magic: {magic!r}")

        # map_areaHeader: fourcc(4) + flags(2) + gridArea(2) = 8 bytes
        flags, grid_area = struct.unpack_from("<Hh", data, offset + 4)

        if flags & MAP_AREA_NO_AREA:
            return AreaData(grid_area=grid_area, area_map=[])

        # 16x16 uint16 area IDs
        area_start = offset + 8
        area_map = []
        for row in range(16):
            row_data = []
            for col in range(16):
                val = struct.unpack_from("<H", data, area_start + (row * 16 + col) * 2)[0]
                row_data.append(val)
            area_map.append(row_data)

        return AreaData(grid_area=grid_area, area_map=area_map)

    def _parse_height(self, data: bytes, offset: int, size: int) -> HeightData:
        """Parse height section: MHT magic + header + height grid."""
        magic = data[offset:offset + 4]
        if magic != HEIGHT_MAGIC:
            raise ValueError(f"Invalid height magic: {magic!r}")

        # map_heightHeader: fourcc(4) + flags(4) + gridHeight(4) + gridMaxHeight(4) = 16 bytes
        flags, grid_height, grid_max_height = struct.unpack_from(
            "<Iff", data, offset + 4
        )

        if flags & MAP_HEIGHT_NO_HEIGHT:
            return HeightData(
                grid_height=grid_height,
                grid_max_height=grid_max_height,
                height_type="flat",
                heights=[],
                multiplier=1.0,
            )

        height_start = offset + 16

        if flags & MAP_HEIGHT_AS_INT8:
            # 129x129 uint8 heights
            multiplier = (grid_max_height - grid_height) / 255.0
            heights = []
            idx = height_start
            for row in range(MAP_TILE_VERTS_V9):
                row_data = list(struct.unpack_from(
                    f"<{MAP_TILE_VERTS_V9}B", data, idx
                ))
                heights.append(row_data)
                idx += MAP_TILE_VERTS_V9
            return HeightData(
                grid_height=grid_height,
                grid_max_height=grid_max_height,
                height_type="uint8",
                heights=heights,
                multiplier=multiplier,
            )

        if flags & MAP_HEIGHT_AS_INT16:
            # 129x129 uint16 heights
            multiplier = (grid_max_height - grid_height) / 65535.0
            heights = []
            idx = height_start
            for row in range(MAP_TILE_VERTS_V9):
                row_data = list(struct.unpack_from(
                    f"<{MAP_TILE_VERTS_V9}H", data, idx
                ))
                heights.append(row_data)
                idx += MAP_TILE_VERTS_V9 * 2
            return HeightData(
                grid_height=grid_height,
                grid_max_height=grid_max_height,
                height_type="uint16",
                heights=heights,
                multiplier=multiplier,
            )

        # Float heights (129x129)
        heights = []
        idx = height_start
        for row in range(MAP_TILE_VERTS_V9):
            row_data = list(struct.unpack_from(
                f"<{MAP_TILE_VERTS_V9}f", data, idx
            ))
            heights.append(row_data)
            idx += MAP_TILE_VERTS_V9 * 4
        return HeightData(
            grid_height=grid_height,
            grid_max_height=grid_max_height,
            height_type="float",
            heights=heights,
            multiplier=1.0,
        )

    def _parse_liquid(self, data: bytes, offset: int, size: int) -> LiquidData:
        """Parse liquid section: MLIQ magic + header + liquid grids."""
        magic = data[offset:offset + 4]
        if magic != LIQUID_MAGIC:
            raise ValueError(f"Invalid liquid magic: {magic!r}")

        # map_liquidHeader: fourcc(4) + flags(1) + liquidFlags(1) + liquidType(2) +
        #                    offsetX(1) + offsetY(1) + width(1) + height(1) + liquidLevel(4) = 16 bytes
        (flags, liquid_flag, liquid_type, off_x, off_y,
         width, height, liquid_level
         ) = struct.unpack_from("<BBhBBBBf", data, offset + 4)

        pos = offset + 16
        end = offset + size

        # Parse liquid type entries (16x16 uint16)
        liquid_types = []
        if not (flags & MAP_LIQUID_NO_TYPE):
            for row in range(16):
                row_data = list(struct.unpack_from(
                    "<16H", data, pos
                ))
                liquid_types.append(row_data)
                pos += 16 * 2

        # Parse liquid flags (16x16 uint8) - only present when NO_HEIGHT is NOT set
        liquid_flags = []
        if not (flags & MAP_LIQUID_NO_HEIGHT) and pos + 256 <= end:
            for row in range(16):
                row_data = list(struct.unpack_from(
                    "<16B", data, pos
                ))
                liquid_flags.append(row_data)
                pos += 16

        # Parse liquid height map (width*16*height*16 floats)
        liquid_map = []
        if not (flags & MAP_LIQUID_NO_HEIGHT) and width > 0 and height > 0:
            for row in range(height):
                row_data = []
                for col in range(width):
                    cell_count = 16
                    if pos + cell_count * 4 > end:
                        break
                    cell_data = list(struct.unpack_from(
                        f"<{cell_count}f", data, pos
                    ))
                    row_data.append(cell_data)
                    pos += cell_count * 4
                liquid_map.append(row_data)
                liquid_map.append(row_data)

        return LiquidData(
            liquid_level=liquid_level,
            liquid_width=width,
            liquid_height=height,
            liquid_off_x=off_x,
            liquid_off_y=off_y,
            liquid_types=liquid_types,
            liquid_flags=liquid_flags,
            liquid_map=liquid_map,
        )
