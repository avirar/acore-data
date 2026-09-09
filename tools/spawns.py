"""spawns tool: creature spawn analysis for creature_template entries.

Answers "where does creature N spawn?" / "does template X have any world
spawn?" in one call: total spawn count, per-map breakdown (with map names),
and sample positions. Read-only; uses creature + creature_template + map
(acore_world). No mod required - works on any azerothcore-wotlk install.
"""

from typing import Any, Dict


def _map_rows_to_dicts(rows):
    return rows or []


def _map_names(server, map_ids) -> Dict[int, str]:
    """Resolve map ids to names: DBC Map (universal) then SQL `map` table
    fallback (builds that ship one). Never fails - missing names stay None."""
    names: Dict[int, str] = {}
    try:
        reader = server._load_dbc("Map")
        entry = server.registry.registry.get("entries", {}).get("MapEntry") or {}
        name_idx = None
        for k, f in (entry.get("fields") or {}).items():
            if f.get("name") in ("name[0]", "Name"):
                try:
                    name_idx = int(k)
                except (TypeError, ValueError):
                    pass
                break
        if name_idx is not None:
            for mid in map_ids:
                rec = reader.get_record_by_id(mid)
                if rec:
                    v = rec.get(name_idx)
                    if isinstance(v, str) and v.strip():
                        names[mid] = v.strip()
    except Exception:
        pass
    missing = [m for m in map_ids if m not in names]
    if missing:
        try:
            ph = ",".join(["%s"] * len(missing))
            rows, _ = server.database._query_database(
                f"SELECT map, name FROM map WHERE map IN ({ph})", params=missing
            )
            for r in _map_rows_to_dicts(rows):
                names.setdefault(int(r["map"]), r["name"])
        except Exception:
            pass
    return names


def spawns_tools(server) -> Dict[str, Any]:
    args = server.args
    entry = args.get("entry")
    map_id = args.get("map")
    limit = args.get("limit", 3)

    if isinstance(entry, bool) or not isinstance(entry, int) or entry <= 0:
        return {
            "error": "entry must be a positive integer (creature_template entry).",
            "isError": True,
        }
    if map_id is not None and (isinstance(map_id, bool) or not isinstance(map_id, int)):
        return {
            "error": "map must be an integer map ID.",
            "isError": True,
        }
    if limit is None:
        limit = 3
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        limit = 3
    limit = min(limit, 20)

    db = server.database
    if not db.db_available:
        return {"error": "Database not available.", "isError": True}

    where = "WHERE id = %s"
    params = [entry]
    if map_id is not None:
        where += " AND map = %s"
        params.append(map_id)

    # template name (absent -> the entry is not a known creature_template)
    trows, terr = db._query_database(
        "SELECT name FROM creature_template WHERE entry = %s", params=(entry,)
    )
    if terr:
        return {"error": f"creature_template lookup failed: {terr}", "isError": True}
    name = trows[0]["name"] if trows else None

    # per-map spawn counts
    mrows, merr = db._query_database(
        f"SELECT map, COUNT(*) AS c FROM creature {where} GROUP BY map ORDER BY c DESC",
        params=params,
    )
    if merr:
        return {"error": f"creature query failed: {merr}", "isError": True}
    per_map = _map_rows_to_dicts(mrows)
    total = sum(int(r["c"]) for r in per_map)

    # map names for the breakdown (top 8 only)
    shown = per_map[:8]
    maps_out = []
    if shown:
        ids = [int(r["map"]) for r in shown]
        names = _map_names(server, ids)
        for r in shown:
            maps_out.append(
                {
                    "map": int(r["map"]),
                    "map_name": names.get(int(r["map"])),
                    "count": int(r["c"]),
                }
            )

    # sample positions (deterministic: first rows by PK order)
    srows, serr = db._query_database(
        f"SELECT map, position_x, position_y, position_z, zoneId, areaId "
        f"FROM creature {where} LIMIT %s",
        params=params + [limit],
    )
    if serr:
        return {"error": f"sample positions query failed: {serr}", "isError": True}
    samples = [
        {
            "map": int(r["map"]),
            "x": round(float(r["position_x"]), 2),
            "y": round(float(r["position_y"]), 2),
            "z": round(float(r["position_z"]), 2),
            "zoneId": r.get("zoneId"),
            "areaId": r.get("areaId"),
        }
        for r in _map_rows_to_dicts(srows)
    ]

    result = {
        "entry": entry,
        "name": name,
        "template_exists": name is not None,
        "total_spawns": total,
        "has_world_spawn": total > 0,
        "map_count": len(per_map),
        "maps": maps_out,
        "samples": samples,
        "metadata": {
            "sql_table": "creature",
            "sql_database": "acore_world",
            "note": (
                "Read-only spawn analysis. `maps` is capped at 8 entries; "
                "`map_count` is the exact number of distinct maps."
            ),
        },
    }

    if total == 0 and name is None:
        result["error"] = (
            f"Entry {entry} is neither a creature_template nor has any world "
            "spawns. Check the entry id (query creature_template for names)."
        )
        result["isError"] = True

    return result


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "spawns",
        "description": (
            "Creature spawn analysis for a creature_template entry (creature id): "
            "total world spawns, per-map breakdown with map names, and sample "
            "positions. Answers 'where does creature N spawn?' and 'does template "
            "X have any world spawn?' (has_world_spawn). Read-only; uses the "
            "creature, creature_template and map tables (acore_world)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry": {
                    "type": "number",
                    "description": "creature_template entry (the creature id).",
                },
                "map": {
                    "type": "number",
                    "description": "Restrict the analysis to a single map ID.",
                },
                "limit": {
                    "type": "number",
                    "description": "Number of sample positions to return (default 3, max 20).",
                },
            },
            "required": ["entry"],
        },
    }
