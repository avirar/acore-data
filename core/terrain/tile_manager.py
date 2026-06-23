"""MMap tile manager with caching and on-demand cross-tile link resolution."""

from __future__ import annotations

import glob as glob_mod
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.terrain.coords import (
    GRID_SIZE as TILE_SIZE,
    mmap_tile_filename,
)
from core.terrain.detour_parser import DetourParser, DetourTileData


def world_to_tile(wx: float, wy: float) -> Tuple[int, int]:
    """World coords to mmap tile coords.

    From MapBuilder::getTileBounds:
    bmax[0] = (32 - tileX) * GRID_SIZE  (world X)
    bmax[2] = (32 - tileY) * GRID_SIZE  (world Y)
    Thus: tileX = 32 - world_x / GRID_SIZE, tileY = 32 - world_y / GRID_SIZE
    """
    tx = int(32 - wx / TILE_SIZE)
    ty = int(32 - wy / TILE_SIZE)
    return (max(0, min(63, tx)), max(0, min(63, ty)))


def get_tile_filename(map_id: int, tx: int, ty: int) -> str:
    """Generate tile filename."""
    return mmap_tile_filename(map_id, tx, ty)


@dataclass
class LoadedTile:
    """Wrapper around a parsed Detour tile with metadata."""

    tile: DetourTileData
    tx: int
    ty: int
    map_id: int
    external_links: Dict[int, List[Tuple[int, int, int]]] = field(default_factory=dict)


class TileManager:
    """Manages loaded MMap tiles with on-demand loading and cross-tile link resolution."""

    def __init__(self, map_id: int, mmap_dir: str):
        self._map_id = map_id
        self._mmap_dir = mmap_dir
        self._parser = DetourParser()
        self._loaded: Dict[Tuple[int, int], LoadedTile] = {}
        self._available: Set[Tuple[int, int]] = self._discover_tiles()
        self._tile_bboxes: Dict[Tuple[int, int], Tuple[float, float, float, float]] = {}

    @property
    def map_id(self) -> int:
        return self._map_id

    def _discover_tiles(self) -> Set[Tuple[int, int]]:
        """Scan disk for available .mmtile files for this map."""
        tiles: Set[Tuple[int, int]] = set()
        pattern = str(Path(self._mmap_dir) / f"{self._map_id:03d}*.mmtile")
        for fpath in glob_mod.glob(pattern):
            fname = os.path.basename(fpath)
            base = fname.replace(".mmtile", "")
            if len(base) >= 7:
                tx = int(base[3:5])
                ty = int(base[5:7])
                tiles.add((tx, ty))
        return tiles

    def _tile_path(self, tx: int, ty: int) -> str:
        return os.path.join(self._mmap_dir, get_tile_filename(self._map_id, tx, ty))

    def _load_raw_tile(self, tx: int, ty: int) -> Optional[LoadedTile]:
        """Load and parse a single tile from disk."""
        path = self._tile_path(tx, ty)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            data = f.read()
        detour_data = data[56:]
        tile = self._parser.parse(detour_data)
        if tile is None:
            return None
        lt = LoadedTile(
            tile=tile,
            tx=tx,
            ty=ty,
            map_id=self._map_id,
        )
        self._tile_bboxes[(tx, ty)] = (
            tile.bmin[0], tile.bmax[0], tile.bmin[2], tile.bmax[2]
        )
        return lt

    def get_tile(self, tx: int, ty: int) -> Optional[LoadedTile]:
        return self._loaded.get((tx, ty))

    def ensure_tile(self, tx: int, ty: int) -> Optional[LoadedTile]:
        """Load a tile if not already loaded, and build cross-tile links."""
        if (tx, ty) in self._loaded:
            return self._loaded[(tx, ty)]
        if (tx, ty) not in self._available:
            return None
        lt = self._load_raw_tile(tx, ty)
        if lt is None:
            return None
        self._loaded[(tx, ty)] = lt
        self._build_links_for_tile(lt, tx, ty)
        return lt

    def find_tile_at(self, wx: float, wy: float) -> Optional[Tuple[int, int]]:
        """Find the tile containing world coordinates (x, y)."""
        tx, ty = world_to_tile(wx, wy)
        if (tx, ty) in self._available:
            return (tx, ty)
        # Spiral search outward
        for radius in range(1, 10):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue  # Only check the ring at this radius
                    candidate = (tx + dx, ty + dy)
                    if candidate in self._available:
                        return candidate
        return None

    def get_all_loaded(self) -> List[LoadedTile]:
        return list(self._loaded.values())

    def resolve_external_edge(
        self, poly_idx: int, tx: int, ty: int, vert_idx: int
    ) -> List[Tuple[int, int, int]]:
        """Resolve an external edge (nei_idx == 0xFFFF) to neighbor polygons.

        Returns list of (neighbor_poly_idx, neighbor_tx, neighbor_ty).
        Loads neighbor tile on-demand.
        """
        lt = self._loaded.get((tx, ty))
        if lt is None:
            return []

        tile = lt.tile
        poly = tile.polygons[poly_idx]
        vx1 = poly.verts[vert_idx]
        vx2 = poly.verts[(vert_idx + 1) % poly.vert_count]
        if vx1 >= len(tile.vertices) or vx2 >= len(tile.vertices):
            return []

        v1 = tile.vertices[vx1]
        v2 = tile.vertices[vx2]
        mx = (v1[0] + v2[0]) / 2.0
        my = (v1[1] + v2[1]) / 2.0
        mz = (v1[2] + v2[2]) / 2.0

        neighbor_tile = self._find_tile_at_detour(mx, mz, (tx, ty))
        if neighbor_tile is None:
            return []

        ntx, nty = neighbor_tile
        neighbor = self._loaded.get((ntx, nty))
        if neighbor is None:
            neighbor = self.ensure_tile(ntx, nty)
            if neighbor is None:
                return []

        results: List[Tuple[int, int, int]] = []
        neighbor_poly = self._find_polygon_at(neighbor.tile, mx, mz, my)
        if neighbor_poly is not None:
            results.append((neighbor_poly, ntx, nty))

        # Cache in external_links for future lookups
        lt.external_links.setdefault(poly_idx, []).extend(results)
        return results

    def get_external_links(
        self, poly_idx: int, tx: int, ty: int
    ) -> List[Tuple[int, int, int]]:
        """Get external links for a polygon (cached)."""
        lt = self._loaded.get((tx, ty))
        if lt is None:
            return []
        return lt.external_links.get(poly_idx, [])

    def _build_links_for_tile(self, lt: LoadedTile, tx: int, ty: int) -> None:
        """Build cross-tile links for a single tile against all loaded neighbors."""
        tile = lt.tile
        if not tile.polygons:
            return

        for pi, poly in enumerate(tile.polygons):
            if poly.is_offmesh:
                continue

            for vi in range(poly.vert_count):
                nei_idx = poly.neis[vi]
                if nei_idx != 0xFFFF:
                    continue

                vx1 = poly.verts[vi]
                vx2 = poly.verts[(vi + 1) % poly.vert_count]
                if vx1 >= len(tile.vertices) or vx2 >= len(tile.vertices):
                    continue

                v1 = tile.vertices[vx1]
                v2 = tile.vertices[vx2]
                mx = (v1[0] + v2[0]) / 2.0
                my = (v1[1] + v2[1]) / 2.0
                mz = (v1[2] + v2[2]) / 2.0

                neighbor_tile = self._find_tile_at_detour(mx, mz, (tx, ty))
                if neighbor_tile is None:
                    continue

                ntx, nty = neighbor_tile
                neighbor = self._loaded.get((ntx, nty))
                if neighbor is None:
                    continue

                neighbor_poly = self._find_polygon_at(neighbor.tile, mx, mz, my)
                if neighbor_poly is not None:
                    lt.external_links.setdefault(pi, []).append(
                        (neighbor_poly, ntx, nty)
                    )

    def _find_tile_at_detour(
        self, x: float, z: float, exclude: Tuple[int, int]
    ) -> Optional[Tuple[int, int]]:
        """Find loaded tile containing (x, z) in Detour space, excluding self."""
        eps = 1.0
        for (ktx, kty), bbox in self._tile_bboxes.items():
            if (ktx, kty) == exclude:
                continue
            if bbox[0] <= x + eps and bbox[1] >= x - eps and \
               bbox[2] <= z + eps and bbox[3] >= z - eps:
                return (ktx, kty)

        # Not in loaded tiles — try to find on disk
        if (x, z) != (x, z):  # NaN check
            return None

        candidate = self._detour_to_tile(x, z)
        if candidate != exclude and candidate in self._available:
            return candidate

        return None

    def _detour_to_tile(self, x: float, z: float) -> Tuple[int, int]:
        """Convert Detour coords to tile coords.

        AC transforms: Detour = (world_y, world_z, world_x).
        So Detour_X = world_Y, Detour_Z = world_X.
        tileX = 32 - world_x / GRID = 32 - Detour_Z / GRID
        tileY = 32 - world_y / GRID = 32 - Detour_X / GRID
        """
        tx = int(32 - z / TILE_SIZE)
        ty = int(32 - x / TILE_SIZE)
        return (max(0, min(63, tx)), max(0, min(63, ty)))

    def _find_polygon_at(
        self, tile: DetourTileData, x: float, z: float, y: float = 0.0
    ) -> Optional[int]:
        """Find polygon containing point (x, y, z) using BV tree."""
        parser = DetourParser()
        parser._tile = tile  # pylint: disable=protected-access
        idx, _ = parser.find_nearest_poly((x, y, z), max_dist=50.0)
        return idx if idx >= 0 else None
