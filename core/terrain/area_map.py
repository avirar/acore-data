"""
Obstacle-aware SVG area-map renderer for the terrain tool.

DB-free by design: navmesh geometry, labeled points, path polylines and LOS
rays go in, one SVG string comes out. The tool layer (tools/terrain.py)
gathers points from SQL and paths/LOS from the server-parity primitives; this
module never touches the database.

Frame convention (derived from the WoW world axes): +X = north, +Y = west.
The map is drawn north-up / east-right like the in-game world map:
    screen_x = (maxy - y) * scale      (east = -Y is right)
    screen_y = (maxx - x) * scale      (south = -X is down)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from xml.sax.saxutils import escape

HEIGHT_LEVELS = 16
MAX_SVG_AXIS = 6000.0            # px hard cap per canvas axis
DEFAULT_MAX_SPAN = 3000.0        # yards per axis before refusing
DEFAULT_MAX_POLYS = 40000        # polys before refusing (suggest outline)
DEFAULT_Z_BAND = 25.0            # yards around `z` for multi-floor filtering

# kind -> (fill, stroke, radius px)
POINT_STYLE = {
    "creature": ("#e53e3e", "#742a2a", 3.0),
    "gameobject": ("#3182ce", "#2a4d7f", 3.0),
    "trigger": ("#a0aec0", "#4a5568", 1.8),
}
POINT_LABEL_ORDER = ("creature", "gameobject", "trigger")

PATH_COLOR = "#6b46c1"
LOS_VISIBLE_COLOR = "#38a169"
LOS_BLOCKED_COLOR = "#c05621"

_PAD_L, _PAD_T, _PAD_R, _PAD_B = 54.0, 46.0, 20.0, 48.0
_LEGEND_W = 150.0     # dedicated right-hand column: never overlaps the frame
_LEGEND_H = 26 + HEIGHT_LEVELS * 8 + 18 + 16 * 6
_FONT_TITLE, _FONT_SUB, _FONT_LABEL, _FONT_TICK = 14, 11, 11, 10


class AreaMapError(ValueError):
    """Raised for caller-fixable area_map problems (bounds, caps)."""


class Bounds(NamedTuple):
    minx: float
    miny: float
    maxx: float
    maxy: float

    @property
    def span_x(self) -> float:
        return self.maxx - self.minx

    @property
    def span_y(self) -> float:
        return self.maxy - self.miny


def _fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _hsl_hex(h: float, s: float, l: float) -> str:
    """h in degrees, s/l in [0,1] -> #rrggbb."""
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    hp = (h % 360.0) / 60.0
    x = c * (1.0 - abs(hp % 2.0 - 1.0))
    r1, g1, b1 = (
        (c, x, 0.0) if hp < 1 else
        (x, c, 0.0) if hp < 2 else
        (0.0, c, x) if hp < 3 else
        (0.0, x, c) if hp < 4 else
        (x, 0.0, c) if hp < 5 else
        (c, 0.0, x)
    )
    m = l - c / 2.0
    return "#{:02x}{:02x}{:02x}".format(
        int(round((r1 + m) * 255)), int(round((g1 + m) * 255)),
        int(round((b1 + m) * 255)),
    )


def height_color(t: float) -> str:
    """Color ramp for normalized height t in [0,1]: blue (low) -> red (high)."""
    t = min(1.0, max(0.0, t))
    return _hsl_hex(220.0 - 220.0 * t, 0.52, 0.62)


def height_level(z: float, zmin: float, zmax: float) -> int:
    if zmax <= zmin:
        return 0
    t = (z - zmin) / (zmax - zmin)
    level = int(t * (HEIGHT_LEVELS - 1) + 1e-9)
    return min(HEIGHT_LEVELS - 1, max(0, level))


# ---------------------------------------------------------------------------
# mesh collection
# ---------------------------------------------------------------------------

def collect_mesh(nav: Any, bounds: Bounds,
                 max_polys: int = DEFAULT_MAX_POLYS,
                 z: Optional[float] = None,
                 z_band: float = DEFAULT_Z_BAND) -> Dict[str, Any]:
    """Gather navmesh polygons intersecting the bounds (world XY).

    Detour vertices are (worldY, worldZ, worldX); they are remapped to world
    (x, y, z) here so the renderer works purely in world axes. When `z` is
    given, only polys whose average height falls within z +- z_band are kept
    (instances stack floors in XY).
    """
    if nav._file_index is None:
        nav._file_index = nav._build_file_index()

    polys: List[Tuple[List[Tuple[float, float, float]], float]] = []
    offmesh: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    zmin: Optional[float] = None
    zmax: Optional[float] = None
    tile_count = 0
    poly_total = 0

    for key in sorted(nav._file_index):
        tile = nav.ensure_tile(*key)
        if tile is None:
            continue
        tile_count += 1
        verts = tile.data.vertices
        for poly in tile.data.polygons:
            poly_total += 1
            if poly.is_offmesh:
                continue
            pv = [verts[i] for i in poly.verts if i < len(verts)]
            if len(pv) < 3:
                continue
            wpts = [(v[2], v[0], v[1]) for v in pv]
            xs = [p[0] for p in wpts]
            ys = [p[1] for p in wpts]
            if (max(xs) < bounds.minx or min(xs) > bounds.maxx or
                    max(ys) < bounds.miny or min(ys) > bounds.maxy):
                continue
            avgz = sum(p[2] for p in wpts) / len(wpts)
            if z is not None and abs(avgz - z) > z_band:
                continue
            polys.append((wpts, avgz))
            zmin = avgz if zmin is None else min(zmin, avgz)
            zmax = avgz if zmax is None else max(zmax, avgz)
        for con in tile.data.off_mesh_cons:
            s, e = con.start, con.end
            spt = (s[2], s[0])
            ept = (e[2], e[0])
            if (max(spt[0], ept[0]) < bounds.minx or
                    min(spt[0], ept[0]) > bounds.maxx or
                    max(spt[1], ept[1]) < bounds.miny or
                    min(spt[1], ept[1]) > bounds.maxy):
                continue
            if z is not None:
                con_z = (s[1] + e[1]) / 2.0
                if abs(con_z - z) > z_band:
                    continue
            offmesh.append((spt, ept))

    if len(polys) > max_polys:
        raise AreaMapError(
            f"area_map: {len(polys)} navmesh polys exceed max_polys="
            f"{max_polys}; shrink the bounds or pass mesh_style='outline'"
        )
    return {
        "polys": polys,
        "offmesh": offmesh,
        "zmin": zmin if zmin is not None else 0.0,
        "zmax": zmax if zmax is not None else 0.0,
        "tile_count": tile_count,
        "poly_total": poly_total,
    }


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

def _poly_path_d(polys: Sequence[Tuple[List[Tuple[float, float, float]], float]],
                 sx, sy) -> str:
    parts = []
    for wpts, _ in polys:
        coords = ["M", _fmt(sx(wpts[0][1])), _fmt(sy(wpts[0][0]))]
        for p in wpts[1:]:
            coords += ["L", _fmt(sx(p[1])), _fmt(sy(p[0]))]
        coords.append("Z")
        parts.append(" ".join(coords))
    return " ".join(parts)


def render_svg(map_id: int, map_name: str, bounds: Bounds, mesh: Dict[str, Any],
               points: Sequence[Dict[str, Any]],
               paths: Sequence[Dict[str, Any]],
               rays: Sequence[Dict[str, Any]], *,
               mesh_style: str = "height",
               scale: float = 2.0,
               grid: float = 50.0,
               labels: bool = True,
               label_limit: int = 60) -> str:
    """Render one SVG string. All inputs are already tool-layer validated."""
    if mesh_style not in ("height", "outline", "wire"):
        raise AreaMapError(f"Invalid mesh_style: {mesh_style}")
    if scale <= 0:
        raise AreaMapError("scale must be > 0")
    if bounds.span_x <= 0 or bounds.span_y <= 0:
        raise AreaMapError("bounds have zero span")

    content_w = bounds.span_y * scale   # horizontal axis = world Y
    content_h = bounds.span_x * scale   # vertical axis = world X
    shrink = min(1.0, MAX_SVG_AXIS / max(1.0, content_w),
                 MAX_SVG_AXIS / max(1.0, content_h))
    scale *= shrink
    content_w = bounds.span_y * scale
    content_h = bounds.span_x * scale
    legend_x = _PAD_L + content_w + 24.0
    width = legend_x + _LEGEND_W
    height = _PAD_T + max(content_h, _LEGEND_H) + _PAD_B

    def sx(y: float) -> float:
        return _PAD_L + (bounds.maxy - y) * scale

    def sy(x: float) -> float:
        return _PAD_T + (bounds.maxx - x) * scale

    polys = mesh["polys"]
    zmin, zmax = mesh["zmin"], mesh["zmax"]

    out: List[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(width)}" '
        f'height="{_fmt(height)}" viewBox="0 0 {_fmt(width)} {_fmt(height)}" '
        'font-family="Helvetica,Arial,sans-serif">'
    )
    out.append(
        f"<title>{escape(map_name)} (map {map_id}) area map "
        f"X {_fmt(bounds.minx)}..{_fmt(bounds.maxx)} "
        f"Y {_fmt(bounds.miny)}..{_fmt(bounds.maxy)}</title>"
    )
    out.append(
        f'<rect x="0" y="0" width="{_fmt(width)}" height="{_fmt(height)}" '
        'fill="#f7fafc"/>'
    )

    # --- mesh fills, bucketed by height level -----------------------------
    buckets: Dict[int, List] = {}
    for poly in polys:
        buckets.setdefault(height_level(poly[1], zmin, zmax), []).append(poly)
    if mesh_style == "height":
        for level in sorted(buckets):
            t = level / (HEIGHT_LEVELS - 1) if HEIGHT_LEVELS > 1 else 0.5
            color = height_color(t)
            d = _poly_path_d(buckets[level], sx, sy)
            out.append(
                f'<path d="{d}" fill="{color}" fill-opacity="0.88" '
                f'stroke="{color}" stroke-opacity="0.35" stroke-width="0.5"/>'
            )
    elif mesh_style == "outline":
        d = _poly_path_d(polys, sx, sy)
        out.append(f'<path d="{d}" fill="#ffffff" fill-opacity="0.9" '
                   'stroke="none"/>')

    # shared edge outline pass for readability
    if mesh_style != "wire" and polys:
        d = _poly_path_d(polys, sx, sy)
        out.append(f'<path d="{d}" fill="none" stroke="#1a202c" '
                   'stroke-opacity="0.22" stroke-width="0.4"/>')

    # off-mesh connections (jumps/teleports): dotted violet
    for spt, ept in mesh.get("offmesh", []):
        out.append(
            f'<line x1="{_fmt(sx(spt[1]))}" y1="{_fmt(sy(spt[0]))}" '
            f'x2="{_fmt(sx(ept[1]))}" y2="{_fmt(sy(ept[0]))}" '
            'stroke="#805ad5" stroke-width="1" stroke-dasharray="2,3" '
            'stroke-opacity="0.8"/>'
        )

    # --- grid + ticks ------------------------------------------------------
    grid = float(grid) if grid and grid > 0 else 0.0
    if grid:
        gx0 = math.ceil(bounds.miny / grid) * grid
        gy0 = math.ceil(bounds.minx / grid) * grid
        yv = gx0
        while yv <= bounds.maxy + 1e-6:
            px = sx(yv)
            out.append(
                f'<line x1="{_fmt(px)}" y1="{_fmt(_PAD_T)}" '
                f'x2="{_fmt(px)}" y2="{_fmt(_PAD_T + content_h)}" '
                'stroke="#cbd5e0" stroke-width="0.5" stroke-opacity="0.7"/>'
            )
            out.append(
                f'<text x="{_fmt(px)}" y="{_fmt(_PAD_T + content_h + 14)}" '
                'font-size="10" fill="#4a5568" text-anchor="middle">'
                f"{_fmt(yv)}</text>"
            )
            yv += grid
        xv = gy0
        while xv <= bounds.maxx + 1e-6:
            py = sy(xv)
            out.append(
                f'<line x1="{_fmt(_PAD_L)}" y1="{_fmt(py)}" '
                f'x2="{_fmt(_PAD_L + content_w)}" y2="{_fmt(py)}" '
                'stroke="#cbd5e0" stroke-width="0.5" stroke-opacity="0.7"/>'
            )
            out.append(
                f'<text x="{_fmt(_PAD_L - 5)}" y="{_fmt(py + 3)}" '
                'font-size="10" fill="#4a5568" text-anchor="end">'
                f"{_fmt(xv)}</text>"
            )
            xv += grid

    # frame
    out.append(
        f'<rect x="{_fmt(_PAD_L)}" y="{_fmt(_PAD_T)}" '
        f'width="{_fmt(content_w)}" height="{_fmt(content_h)}" '
        'fill="none" stroke="#2d3748" stroke-width="1"/>'
    )

    # north arrow (+X = north), anchored to the frame's top-right corner
    nx, ny = _PAD_L + content_w - 20.0, _PAD_T + 22.0
    out.append(
        f'<line x1="{_fmt(nx)}" y1="{_fmt(ny + 12)}" x2="{_fmt(nx)}" '
        f'y2="{_fmt(ny - 6)}" stroke="#2d3748" stroke-width="1.2"/>'
        f'<polygon points="{_fmt(nx)},{_fmt(ny - 12)} '
        f'{_fmt(nx - 3.5)},{_fmt(ny - 4)} {_fmt(nx + 3.5)},{_fmt(ny - 4)}" '
        'fill="#2d3748"/>'
        f'<text x="{_fmt(nx)}" y="{_fmt(ny + 24)}" font-size="10" '
        'fill="#2d3748" text-anchor="middle">N</text>'
    )

    # --- LOS rays -----------------------------------------------------------
    for ray in rays:
        color = LOS_VISIBLE_COLOR if ray["visible"] else LOS_BLOCKED_COLOR
        out.append(
            f'<line x1="{_fmt(sx(ray["y1"]))}" y1="{_fmt(sy(ray["x1"]))}" '
            f'x2="{_fmt(sx(ray["y2"]))}" y2="{_fmt(sy(ray["x2"]))}" '
            f'stroke="{color}" stroke-width="1.2" stroke-opacity="0.85"/>'
        )

    # --- path polylines -----------------------------------------------------
    for path in paths:
        pts = path["points"]
        if len(pts) < 2:
            continue
        coords = [f"{_fmt(sx(p[1]))},{_fmt(sy(p[0]))}" for p in pts]
        out.append(
            f'<polyline points="{" ".join(coords)}" fill="none" '
            f'stroke="{PATH_COLOR}" stroke-width="1.8" stroke-opacity="0.9"/>'
        )
        px, py = sx(pts[-1][1]), sy(pts[-1][0])
        out.append(
            f'<circle cx="{_fmt(px)}" cy="{_fmt(py)}" r="2.4" fill="{PATH_COLOR}"/>'
        )

    # --- points + labels ----------------------------------------------------
    budget = max(0, int(label_limit)) if labels else 0
    order = {k: i for i, k in enumerate(POINT_LABEL_ORDER)}
    by_budget = sorted(range(len(points)),
                       key=lambda i: (order.get(points[i]["kind"], 99), i))
    label_flags = [False] * len(points)
    for i in by_budget[:budget]:
        label_flags[i] = True
    for pi, p in enumerate(points):
        if not (bounds.minx <= p["x"] <= bounds.maxx and
                bounds.miny <= p["y"] <= bounds.maxy):
            continue
        fill, stroke, r = POINT_STYLE.get(p["kind"], POINT_STYLE["trigger"])
        cx, cy = sx(p["y"]), sy(p["x"])
        out.append(
            f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="0.6"/>'
        )
        if label_flags[pi] and p.get("label"):
            out.append(
                f'<text x="{_fmt(cx + r + 2)}" y="{_fmt(cy - 3)}" '
                f'font-size="{_FONT_LABEL}" fill="#1a202c" stroke="#ffffff" '
                'stroke-width="2.5" paint-order="stroke" '
                f'fill-opacity="0.95">{escape(str(p["label"]))}</text>'
            )
            if p.get("sub"):
                out.append(
                    f'<text x="{_fmt(cx + r + 2)}" y="{_fmt(cy + 9)}" '
                    f'font-size="9" fill="#4a5568" stroke="#ffffff" '
                    'stroke-width="2" paint-order="stroke">'
                    f'{escape(str(p["sub"]))}</text>'
                )

    # --- legend (dedicated column right of the frame) -----------------------
    lx = legend_x
    ly = _PAD_T + 8.0
    out.append(
        f'<rect x="{_fmt(lx - 8)}" y="{_fmt(ly - 14)}" width="142" '
        f'height="{_fmt(_LEGEND_H + 20)}" fill="#ffffff" '
        'fill-opacity="0.85" stroke="#cbd5e0" stroke-width="0.5"/>'
    )
    out.append(
        f'<text x="{_fmt(lx)}" y="{_fmt(ly)}" font-size="10" fill="#2d3748">'
        "floor height</text>"
    )
    bar_y = ly + 6.0
    for level in range(HEIGHT_LEVELS):
        t = level / (HEIGHT_LEVELS - 1) if HEIGHT_LEVELS > 1 else 0.5
        yy = bar_y + (HEIGHT_LEVELS - 1 - level) * 8.0
        out.append(
            f'<rect x="{_fmt(lx)}" y="{_fmt(yy)}" width="18" height="8" '
            f'fill="{height_color(t)}"/>'
        )
    out.append(
        f'<text x="{_fmt(lx + 24)}" y="{_fmt(bar_y + 7)}" font-size="10" '
        f'fill="#4a5568">{_fmt(zmax)}</text>'
    )
    out.append(
        f'<text x="{_fmt(lx + 24)}" y="{_fmt(bar_y + HEIGHT_LEVELS * 8)}" '
        f'font-size="10" fill="#4a5568">{_fmt(zmin)}</text>'
    )
    ly2 = bar_y + HEIGHT_LEVELS * 8.0 + 18.0
    legend_rows = [
        (POINT_STYLE["creature"], "creature"),
        (POINT_STYLE["gameobject"], "gameobject"),
        (POINT_STYLE["trigger"], "trigger"),
    ]
    for style, text in legend_rows:
        fill, stroke, r = style
        out.append(
            f'<circle cx="{_fmt(lx + 5)}" cy="{_fmt(ly2 - 3)}" r="{_fmt(r)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="0.6"/>'
            f'<text x="{_fmt(lx + 16)}" y="{_fmt(ly2)}" font-size="10" '
            f'fill="#2d3748">{escape(text)}</text>'
        )
        ly2 += 16.0
    out.append(
        f'<line x1="{_fmt(lx)}" y1="{_fmt(ly2 - 4)}" x2="{_fmt(lx + 14)}" '
        f'y2="{_fmt(ly2 - 4)}" stroke="{PATH_COLOR}" stroke-width="1.8"/>'
        f'<text x="{_fmt(lx + 16)}" y="{_fmt(ly2)}" font-size="10" '
        f'fill="#2d3748">navmesh path</text>'
    )
    ly2 += 16.0
    out.append(
        f'<line x1="{_fmt(lx)}" y1="{_fmt(ly2 - 4)}" x2="{_fmt(lx + 14)}" '
        f'y2="{_fmt(ly2 - 4)}" stroke="{LOS_VISIBLE_COLOR}" '
        'stroke-width="1.2"/>'
        f'<text x="{_fmt(lx + 16)}" y="{_fmt(ly2)}" font-size="10" '
        f'fill="#2d3748">LOS clear</text>'
    )
    ly2 += 16.0
    out.append(
        f'<line x1="{_fmt(lx)}" y1="{_fmt(ly2 - 4)}" x2="{_fmt(lx + 14)}" '
        f'y2="{_fmt(ly2 - 4)}" stroke="{LOS_BLOCKED_COLOR}" '
        'stroke-width="1.2"/>'
        f'<text x="{_fmt(lx + 16)}" y="{_fmt(ly2)}" font-size="10" '
        f'fill="#2d3748">LOS blocked</text>'
    )

    # --- title / captions ----------------------------------------------------
    out.append(
        f'<text x="10" y="18" font-size="{_FONT_TITLE}" font-weight="bold" '
        f'fill="#1a202c">{escape(map_name)} (map {map_id}) - area map</text>'
    )
    out.append(
        f'<text x="10" y="33" font-size="{_FONT_SUB}" fill="#4a5568">'
        f'X {_fmt(bounds.minx)}..{_fmt(bounds.maxx)} (north = +X) '
        f'Y {_fmt(bounds.miny)}..{_fmt(bounds.maxy)} (west = +Y) '
        f'{len(polys)} polys, {len(points)} points</text>'
    )

    out.append("</svg>")
    return "".join(out)


__all__ = [
    "AreaMapError",
    "Bounds",
    "DEFAULT_MAX_POLYS",
    "DEFAULT_MAX_SPAN",
    "DEFAULT_Z_BAND",
    "HEIGHT_LEVELS",
    "collect_mesh",
    "height_color",
    "height_level",
    "render_svg",
]
