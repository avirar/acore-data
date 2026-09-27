#!/usr/bin/env python3
"""Export a server-parity path (``.mmap path`` equivalent) as a JSON path pack.

Standalone wrapper around ``core.terrain`` for external viewers such as Noggit.
No database access; requires the client data (mmaps/maps/vmaps) and the DBC
files/format definitions configured via the usual ``ACORE_*``/``*_PATH``
environment variables.

Run:
  .venv/bin/python3 scripts/path_export.py --map 0 \
      --start -9464 64 55 --end -8832 628 100 --output /tmp/path.json

Output (``format: acore-path/1``):
  map, mode, unit, path_type(_names), found, partial,
  start/end/actual_end, distance, smooth_path, poly_path, counts.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

WORKDIR = Path(__file__).resolve().parent.parent
if str(WORKDIR) not in sys.path:
    sys.path.insert(0, str(WORKDIR))

from core.dbc import WDBCReader
from core.formats import FormatParser
from core.paths import safe_exists, safe_is_dir, safe_is_file
from core.terrain import coords
from core.terrain.detour import NavMesh, creature_filter, player_filter
from core.terrain.map_resolver import DEFAULT_COLLISION_HEIGHT, MapResolver
from core.terrain.path_generator import (
    PATH_TYPE_NAMES,
    PATHFIND_BLANK,
    PATHFIND_INCOMPLETE,
    PATHFIND_NOPATH,
    PATHFIND_NORMAL,
    PATHFIND_NOT_USING_PATH,
    PathGenerator,
    UnitProfile,
)

FORMAT_ID = "acore-path/1"
MODES = ("smooth", "straight", "raycast")
UNITS = ("player", "creature", "flying")

DEFAULT_DBC_PATH = "/root/azerothcore-wotlk/env/dist/bin/dbc"
DEFAULT_FORMAT_FILE = "/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h"


class DbcProvider:
    """Minimal cached DBC lookup for MapResolver (no server/database needed)."""

    def __init__(self, dbc_path: str, format_file: str):
        self.dbc_path = Path(dbc_path)
        self.format_file = Path(format_file)
        self._cache: Dict[str, WDBCReader] = {}
        self._parser: Optional[FormatParser] = None
        if safe_is_dir(self.dbc_path) and safe_is_file(self.format_file):
            self._parser = FormatParser(str(self.format_file))
            self._parser.parse()

    @property
    def available(self) -> bool:
        return self._parser is not None

    def load(self, name: str) -> WDBCReader:
        if name in self._cache:
            return self._cache[name]
        if self._parser is None:
            raise FileNotFoundError(
                f"DBC data unavailable (path: {self.dbc_path}, format: {self.format_file})"
            )
        format_string = self._parser.get_format(name)
        if not format_string:
            raise KeyError(f"No DBC format for {name}")
        dbc_file = self.dbc_path / f"{name}.dbc"
        if not safe_exists(dbc_file):
            for candidate in self.dbc_path.glob("*.dbc"):
                if candidate.stem.lower() == name.lower():
                    dbc_file = candidate
                    break
        if not safe_exists(dbc_file):
            raise FileNotFoundError(f"DBC file not found: {name}.dbc")
        reader = WDBCReader(str(dbc_file), format_string)
        reader.read()
        self._cache[name] = reader
        return reader


def resolve_map_id(provider: DbcProvider, value: Any) -> int:
    text = str(value)
    try:
        return int(text)
    except ValueError:
        pass
    if not provider.available:
        raise ValueError(
            f"Unknown map: {value} (DBC data unavailable for name lookup)"
        )
    name = text.lower()
    for row in provider.load("Map").records:
        row_name = row.get(5) or ""
        if row_name and str(row_name).lower() == name:
            return int(row[0])
        for i in range(5, 21):
            variant = row.get(i)
            if variant and str(variant).lower() == name:
                return int(row[0])
    raise ValueError(f"Unknown map: {value}")


def round_point(point: Sequence[float], nd: int = 4) -> Dict[str, float]:
    return {
        "x": round(float(point[0]), nd),
        "y": round(float(point[1]), nd),
        "z": round(float(point[2]), nd),
    }


def poly_centers(nav: NavMesh, refs: Sequence[int]) -> List[Tuple[float, float, float]]:
    """Detour poly refs -> world-space polygon centers (off-mesh skipped)."""
    centers: List[Tuple[float, float, float]] = []
    for ref in refs:
        tile, poly = nav.poly(ref)
        if tile is None or poly is None or poly.is_offmesh or not poly.verts:
            continue
        verts = [tile.data.vertices[i] for i in poly.verts]
        cx = sum(v[0] for v in verts) / len(verts)
        cy = sum(v[1] for v in verts) / len(verts)
        cz = sum(v[2] for v in verts) / len(verts)
        centers.append((cz, cx, cy))
    return centers


class _PathResult:
    """PathGenerator-shaped value object (used for the flying shortcut)."""

    def __init__(self, path_type: int, points, poly_refs, start, end,
                 actual_end, distance: float) -> None:
        self.path_type = path_type
        self.path_points = points
        self.poly_refs = poly_refs
        self.start_position = start
        self.end_position = end
        self.actual_end_position = actual_end
        self.path_length = distance


def build_payload(map_id: int, mode: str, unit: str, pg, nav: Optional[NavMesh],
                  limit: int = 0, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    type_names = [
        name for flag, name in PATH_TYPE_NAMES.items()
        if flag and flag != PATHFIND_BLANK and (pg.path_type & flag)
    ]
    points = list(pg.path_points)
    shown = points if limit <= 0 else points[:limit]
    poly_refs = list(pg.poly_refs)
    payload: Dict[str, Any] = {
        "format": FORMAT_ID,
        "map": map_id,
        "mode": mode,
        "unit": unit,
        "found": not (pg.path_type & PATHFIND_NOPATH),
        "partial": bool(pg.path_type & PATHFIND_INCOMPLETE),
        "path_type": int(pg.path_type),
        "path_type_names": type_names,
        "start": round_point(pg.start_position),
        "end": round_point(pg.end_position),
        "actual_end": round_point(pg.actual_end_position),
        "distance": round(float(pg.path_length), 2),
        "point_count": len(points),
        "poly_count": len(poly_refs),
        "smooth_path": [round_point(p) for p in shown],
        "poly_path": [round_point(p) for p in poly_centers(nav, poly_refs)]
                     if nav is not None else [],
    }
    if limit > 0 and len(points) > limit:
        payload["points_truncated"] = True
    if extra:
        payload.update(extra)
    return payload


def _flying_payload(map_id: int, unit: str, start, end, limit: int) -> Dict[str, Any]:
    distance = math.dist(start, end)
    result = _PathResult(
        PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH,
        [tuple(start), tuple(end)], [], tuple(start), tuple(end), tuple(end), distance,
    )
    return build_payload(
        map_id, "flying", unit, result, None, limit,
        extra={"metadata": {"note": "flying/shortcut: navmesh not used"}},
    )


def generate(args: argparse.Namespace) -> Dict[str, Any]:
    provider = DbcProvider(args.dbc_path, args.format_file)
    map_id = resolve_map_id(provider, args.map)
    start = tuple(float(v) for v in args.start)
    end = tuple(float(v) for v in args.end)

    if args.unit == "flying":
        return _flying_payload(map_id, args.unit, start, end, args.limit)

    mmaps_dir = coords.get_data_paths()["mmaps"]
    if not safe_is_dir(mmaps_dir):
        raise FileNotFoundError(
            f"MMap data not found: {mmaps_dir} (set ACORE_DATA_PATH or DATA_PATH)"
        )
    nav = NavMesh(map_id, mmaps_dir)
    if not nav.has_navmesh:
        raise FileNotFoundError(f"No navmesh data for map {map_id}")

    resolver = MapResolver(map_id, dbc_lookup=provider.load)
    profile = UnitProfile(
        can_swim=True,
        can_fly=False,
        collision_height=args.collision_height,
    )
    filt = creature_filter(can_walk=True, can_swim=True) if args.unit == "creature" \
        else player_filter(headless=False)

    normalizer = None
    if args.normalize:
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
        liquid=liquid, max_nodes=args.max_nodes,
    )
    pg.set_max_polys(args.max_polys)
    pg.set_max_points(args.max_points)
    if args.mode == "straight":
        pg.set_use_straight_path(True)
    elif args.mode == "raycast":
        pg.set_use_raycast(True)

    if not pg.calculate_path(start[0], start[1], start[2], end[0], end[1], end[2]):
        raise ValueError("Invalid map coordinates")

    payload = build_payload(map_id, args.mode, args.unit, pg, nav, args.limit)
    payload["max_nodes_exceeded"] = bool(pg._max_nodes_exceeded)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a server-parity path as an acore-path/1 JSON pack.",
    )
    parser.add_argument("--map", required=True,
                        help="Map id or DBC map name (e.g. 0 or 'Eastern Kingdoms')")
    parser.add_argument("--start", nargs=3, type=float, required=True,
                        metavar=("X", "Y", "Z"), help="Start coordinates (world)")
    parser.add_argument("--end", nargs=3, type=float, required=True,
                        metavar=("X", "Y", "Z"), help="End coordinates (world)")
    parser.add_argument("--mode", choices=MODES, default="smooth",
                        help="smooth = '.mmap path', straight = 'path true', "
                             "raycast = 'path ray'")
    parser.add_argument("--unit", choices=UNITS, default="player")
    parser.add_argument("--normalize", action=argparse.BooleanOptionalAction,
                        default=True,
                        help="Apply UpdateAllowedPositionZ (player-like profile)")
    parser.add_argument("--collision-height", type=float,
                        default=DEFAULT_COLLISION_HEIGHT)
    parser.add_argument("--max-nodes", type=int, default=None,
                        help="A* node cap (server uses 1024; default uncapped)")
    parser.add_argument("--max-polys", type=int, default=None,
                        help="Corridor poly cap (server uses 74/148)")
    parser.add_argument("--max-points", type=int, default=None,
                        help="Path point cap")
    parser.add_argument("--limit", type=int, default=0,
                        help="Truncate exported smooth_path points (0 = all)")
    parser.add_argument("--output", help="Write JSON to this file (default stdout)")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    parser.add_argument("--dbc-path",
                        default=os.environ.get(
                            "ACORE_DBC_PATH", os.environ.get("DBC_PATH", DEFAULT_DBC_PATH)))
    parser.add_argument("--format-file",
                        default=os.environ.get(
                            "ACORE_FORMAT_FILE",
                            os.environ.get("DBC_FORMAT_FILE", DEFAULT_FORMAT_FILE)))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = generate(args)
    except Exception as exc:
        json.dump({"error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 1

    text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
    )
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
