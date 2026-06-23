"""
Pure Python Detour navmesh tile binary parser.

Parses the raw binary data produced by dtCreateNavMeshData (after the
MmapTileHeader).  Layout (all sections 4-byte aligned via dtAlign4):

  1. dtMeshHeader          (100 bytes)
  2. Vertices              float[3] × vertCount
  3. Polygons (dtPoly)     32 bytes × polyCount
  4. Links (dtLink)        16 bytes × maxLinkCount  (zeroed on disk, built on load)
  5. Detail meshes         12 bytes × detailMeshCount
  6. Detail vertices       float[3] × detailVertCount
  7. Detail triangles      uchar[4] × detailTriCount
  8. BV tree (dtBVNode)    12 bytes × bvNodeCount
  9. Off-mesh connections  68 bytes × offMeshConCount

Coordinate convention: Detour Z-up  (y=AC_x, z=AC_y, x=AC_z).
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---- Detour constants ----
DT_NAVMESH_MAGIC = 0x444E4156  # "DNAV" little-endian
DT_NAVMESH_VERSION = 7
DT_VERTS_PER_POLYGON = 6
DT_NULL_LINK = 0xFFFFFFFF
DT_POLYTYPE_GROUND = 0x00
DT_POLYTYPE_OFFMESH_CONNECTION = 0x01
DT_POLYFLAGS_WALK = 0x0001
DT_POLYFLAGS_SWIM = 0x0002
DT_POLYFLAGS_FLY = 0x0004
DT_OFFMESH_CON_BIDIR = 0x0002


def _align4(n: int) -> int:
    return (n + 3) & ~3


# ---- Data classes ----

@dataclass
class DetourPoly:
    first_link: int = DT_NULL_LINK
    verts: List[int] = field(default_factory=list)       # vertex indices
    neis: List[int] = field(default_factory=list)        # neighbour polyRefs
    flags: int = 0
    vert_count: int = 0
    area: int = 0
    ptype: int = 0

    @property
    def is_offmesh(self) -> bool:
        return self.ptype == DT_POLYTYPE_OFFMESH_CONNECTION


@dataclass
class DetourBVNode:
    bmin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bmax: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    i: int = 0


@dataclass
class DetourTileData:
    # Header
    x: int = 0
    y: int = 0
    layer: int = 0
    bmin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bmax: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    walkable_height: float = 0.0
    walkable_radius: float = 0.0
    walkable_climb: float = 0.0
    bv_quant_factor: float = 0.0

    # Geometry
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    polygons: List[DetourPoly] = field(default_factory=list)
    bv_nodes: List[DetourBVNode] = field(default_factory=list)

    # Detail mesh
    detail_meshes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    detail_verts: List[Tuple[float, float, float]] = field(default_factory=list)
    detail_tris: List[Tuple[int, int, int, int]] = field(default_factory=list)

    # Off-mesh connections
    off_mesh_cons: List[Tuple[float, ...]] = field(default_factory=list)

    def get_poly_vertices(self, idx: int) -> List[Tuple[float, float, float]]:
        p = self.polygons[idx]
        return [self.vertices[i] for i in p.verts if i < len(self.vertices)]

    def get_poly_center(self, idx: int) -> Tuple[float, float, float]:
        vs = self.get_poly_vertices(idx)
        if not vs:
            return (0.0, 0.0, 0.0)
        return (sum(v[0] for v in vs) / len(vs),
                sum(v[1] for v in vs) / len(vs),
                sum(v[2] for v in vs) / len(vs))


# ---- Parser ----

class DetourParser:
    """Parse raw Detour tile binary data (after MmapTileHeader)."""

    def __init__(self) -> None:
        self._tile: Optional[DetourTileData] = None

    # ---- public ----

    def parse(self, data: bytes) -> DetourTileData:
        if len(data) < 100:
            raise ValueError(f"Too short for dtMeshHeader: {len(data)}")

        tile = DetourTileData()

        # 1. dtMeshHeader  (all int/float, 100 bytes)
        h = struct.unpack_from("<15i10f", data, 0)
        # fields: magic, version, x, y, layer, userId,
        #         polyCount, vertCount, maxLinkCount, detailMeshCount,
        #         detailVertCount, detailTriCount, bvNodeCount, offMeshConCount,
        #         offMeshBase, walkableH, walkableR, walkableClimb,
        #         bmin[3], bmax[3], bvQuantFactor

        magic = h[0]
        if magic != DT_NAVMESH_MAGIC:
            raise ValueError(f"Bad magic 0x{magic:08X}")
        if h[1] != DT_NAVMESH_VERSION:
            raise ValueError(f"Bad version {h[1]}")

        tile.x, tile.y, tile.layer = h[2], h[3], h[4]
        poly_count, vert_count, max_link_count = h[6], h[7], h[8]
        detail_mesh_count = h[9]
        detail_vert_count, detail_tri_count = h[10], h[11]
        bv_node_count, off_mesh_con_count = h[12], h[13]
        off_mesh_base = h[14]
        tile.walkable_height = h[15]
        tile.walkable_radius = h[16]
        tile.walkable_climb = h[17]
        tile.bmin = (h[18], h[19], h[20])
        tile.bmax = (h[21], h[22], h[23])
        tile.bv_quant_factor = h[24]

        # Section offsets (cumulative, 4-byte aligned)
        off = _align4(100)                       # header

        # 2. Vertices
        verts_size = _align4(vert_count * 3 * 4)
        for i in range(vert_count):
            v = struct.unpack_from("<fff", data, off + i * 12)
            tile.vertices.append(v)
        off += verts_size

        # 3. Polygons  (dtPoly = 32 bytes each)
        poly_size = _align4(32)
        for i in range(poly_count):
            base = off + i * poly_size
            first_link = struct.unpack_from("<I", data, base)[0]
            verts_raw = struct.unpack_from("<6H", data, base + 4)
            neis_raw = struct.unpack_from("<6H", data, base + 16)
            flags = struct.unpack_from("<H", data, base + 28)[0]
            vert_cnt = data[base + 30]
            area_type = data[base + 31]
            area = area_type & 0x3F
            ptype = (area_type >> 6) & 0x03

            poly = DetourPoly()
            poly.first_link = first_link
            poly.verts = list(verts_raw[:vert_cnt])
            poly.neis = list(neis_raw)
            poly.flags = flags
            poly.vert_count = vert_cnt
            poly.area = area
            poly.ptype = ptype
            tile.polygons.append(poly)
        off += poly_count * poly_size

        # 4. Links — zeroed on disk, skip
        links_size = _align4(max_link_count * 16)
        off += links_size

        # 5. Detail meshes  (dtPolyDetail = 12 bytes)
        dm_size = _align4(12)
        for i in range(detail_mesh_count):
            base = off + i * dm_size
            vert_base, tri_base = struct.unpack_from("<II", data, base)
            vert_cnt, tri_cnt = struct.unpack_from("<BB", data, base + 8)
            tile.detail_meshes.append((vert_base, tri_base, vert_cnt, tri_cnt))
        off += detail_mesh_count * dm_size

        # 6. Detail vertices
        dv_size = _align4(detail_vert_count * 3 * 4)
        for i in range(detail_vert_count):
            tile.detail_verts.append(struct.unpack_from("<fff", data, off + i * 12))
        off += dv_size

        # 7. Detail triangles  (4 uchar each)
        for i in range(detail_tri_count):
            t = struct.unpack_from("<4B", data, off + i * 4)
            tile.detail_tris.append(t)
        off += _align4(detail_tri_count * 4)

        # 8. BV tree  (dtBVNode = 16 bytes; quantised coords relative to bmin)
        # dtBVNode: bmin[3] (unsigned short) + bmax[3] (unsigned short) + i (int)
        if bv_node_count > 0:
            qf = tile.bv_quant_factor
            for i in range(bv_node_count):
                base = off + i * 16
                bmin_raw = struct.unpack_from("<3H", data, base)
                bmax_raw = struct.unpack_from("<3H", data, base + 6)
                node_i = struct.unpack_from("<i", data, base + 12)[0]
                # De-quantize and convert to global coords (add tile bmin)
                tile.bv_nodes.append(DetourBVNode(
                    bmin=tuple(tile.bmin[j] + v / qf for j, v in enumerate(bmin_raw)),
                    bmax=tuple(tile.bmin[j] + v / qf for j, v in enumerate(bmax_raw)),
                    i=node_i,
                ))
            off += _align4(bv_node_count * 16)

        # 9. Off-mesh connections  (68 bytes each)
        for i in range(off_mesh_con_count):
            base = off + i * 68
            pos = struct.unpack_from("<6f", data, base)
            rad = struct.unpack_from("<f", data, base + 24)[0]
            side = struct.unpack_from("<f", data, base + 28)[0]
            poly = struct.unpack_from("<H", data, base + 32)[0]
            flags = data[base + 34]
            dir_ = data[base + 35]
            area_from = data[base + 36]
            area_to = data[base + 37]
            tile.off_mesh_cons.append((*pos, rad, side, poly, flags, dir_, area_from, area_to))
            off += _align4(68)

        self._tile = tile
        return tile

    # ---- queries ----

    def find_nearest_poly(self, point: Tuple[float, float, float],
                          max_dist: float = 50.0,
                          filter_flags: int = 0xFFFF) -> Tuple[int, float]:
        """Linear BV-tree nearest-polygon search (matches Detour query).

        Detour traverses the BV tree linearly: leaf nodes have i>=0
        (polygon index), internal nodes have i<0 and are skipped.

        Returns (poly_index, dist_sq) or (-1, inf).
        """
        if not self._tile or not self._tile.bv_nodes:
            return (-1, float("inf"))

        tile = self._tile
        best_idx, best_d2 = -1, max_dist * max_dist

        for node in tile.bv_nodes:
            if node.i < 0:
                continue  # internal node, skip
            d2 = _dist_pt_aabb_sq(point, node.bmin, node.bmax)
            if d2 > best_d2:
                continue
            pi = node.i
            if pi >= len(tile.polygons):
                continue
            p = tile.polygons[pi]
            if p.is_offmesh or not (p.flags & filter_flags):
                continue
            d2 = _dist_pt_poly_sq(point, tile, pi)
            if d2 < best_d2:
                best_d2 = d2
                best_idx = pi

        return (best_idx, best_d2)

    def get_poly_neighbors(self, poly_idx: int) -> List[Tuple[int, int, int]]:
        """Return [(neighbor_poly_idx, edge_start_vert, edge_end_vert), ...]."""
        if not self._tile or poly_idx >= len(self._tile.polygons):
            return []
        poly = self._tile.polygons[poly_idx]
        result: List[Tuple[int, int, int]] = []
        n = poly.vert_count
        for i in range(n):
            ref = poly.neis[i]
            if ref == DT_NULL_LINK or ref == 0:
                continue
            neighbour = ref & 0xFFFF
            if neighbour < len(self._tile.polygons):
                result.append((neighbour, i, (i + 1) % n))
        return result

    def get_poly_height(self, poly_idx: int, x: float, z: float) -> Optional[float]:
        """Height on polygon plane at (x, z)."""
        if not self._tile or poly_idx >= len(self._tile.polygons):
            return None
        vs = self._tile.get_poly_vertices(poly_idx)
        if len(vs) < 3:
            return None
        v0, v1, v2 = vs[0], vs[1], vs[2]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        if abs(ny) < 1e-6:
            return None
        d = -(nx * v0[0] + ny * v0[1] + nz * v0[2])
        return -(nx * x + d + nz * z) / ny


# ---- helpers ----

def _dist_pt_aabb_sq(p: Tuple[float, float, float],
                     mn: Tuple[float, float, float],
                     mx: Tuple[float, float, float]) -> float:
    d = 0.0
    for i in range(3):
        if p[i] < mn[i]:
            d += (mn[i] - p[i]) ** 2
        elif p[i] > mx[i]:
            d += (p[i] - mx[i]) ** 2
    return d


def _dist_pt_poly_sq(p: Tuple[float, float, float],
                     tile: DetourTileData,
                     pi: int) -> float:
    vs = tile.get_poly_vertices(pi)
    if len(vs) < 3:
        return float("inf")
    v0, v1, v2 = vs[0], vs[1], vs[2]
    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    nx = e1[1] * e2[2] - e1[2] * e2[1]
    ny = e1[2] * e2[0] - e1[0] * e2[2]
    nz = e1[0] * e2[1] - e1[1] * e2[0]
    lsq = nx * nx + ny * ny + nz * nz
    if lsq < 1e-12:
        return float("inf")
    t = (nx * p[0] + ny * p[1] + nz * p[2] +
         (-(nx * v0[0] + ny * v0[1] + nz * v0[2]))) / lsq
    px, py, pz = p[0] + t * nx, p[1] + t * ny, p[2] + t * nz
    if _pt_in_poly_2d(px, py, pz, vs):
        return t * t * lsq
    # closest edge
    best = float("inf")
    n = len(vs)
    for i in range(n):
            d = _dist_pt_seg_sq(p, vs[i], vs[(i + 1) % n])
            if d < best:
                best = d
    return best


def _pt_in_poly_2d(px: float, py: float, pz: float,
                   vs: List[Tuple[float, float, float]]) -> bool:
    n = len(vs)
    inside = False
    j = n - 1
    for i in range(n):
        yi, zi = vs[i][1], vs[i][2]
        yj, zj = vs[j][1], vs[j][2]
        if ((zi > pz) != (zj > pz)) and (py < (yj - yi) * (pz - zi) / (zj - zi) + yi):
            inside = not inside
        j = i
    return inside


def _dist_pt_seg_sq(p: Tuple[float, float, float],
                    a: Tuple[float, float, float],
                    b: Tuple[float, float, float]) -> float:
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    lsq = dx * dx + dy * dy + dz * dz
    if lsq < 1e-12:
        return sum((p[i] - a[i]) ** 2 for i in range(3))
    t = max(0.0, min(1.0, sum((p[i] - a[i]) * (b[i] - a[i]) for i in range(3)) / lsq))
    return sum((p[i] - (a[i] + t * (b[i] - a[i]))) ** 2 for i in range(3))
