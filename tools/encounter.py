"""encounter tool: instance/map encounter rollup.

One call answers "what is in this map/instance?":
  - instance metadata (if the map is an instance: script, allow_mount)
  - top creatures by spawn count with level ranges and loot item names
  - top game objects (doors/switches/chests - what the bot must interact with)
  - travel graph stats for the map (mod-playerbots, if installed)

Read-only, acore_world based (playerbots part optional) - works on any
azerothcore-wotlk install; loot comes from the AzerothCore
creature_loot_template / gameobject_loot_template tables.
"""

from typing import Any, Dict, List, Optional

_MAX_CREATURES = 20
_MAX_GAMEOBJECTS = 10
_MAX_LOOT_ITEMS = 5


def _q(server, sql: str, params: Optional[List[Any]] = None,
       db: str = "acore_world"):
    rows, err = server.database._query_database(sql, db_name=db, params=params)
    if err:
        return None, err
    return (rows or []), None


def _item_names(server, entries: List[int], max_items: int) -> List[Dict[str, Any]]:
    if not entries:
        return []
    ph = ",".join(["%s"] * len(entries))
    rows, err = _q(
        server,
        f"SELECT entry, name, Quality FROM item_template WHERE entry IN ({ph})",
        entries,
    )
    if err:
        return []
    out = []
    for r in rows[:max_items]:
        out.append({"item": int(r["entry"]), "name": r["name"],
                    "quality": int(r["Quality"] or 0)})
    return out


def _loot_items(server, entry: int) -> List[Dict[str, Any]]:
    """Item names from a creature's loot template (deduped, capped)."""
    rows, err = _q(
        server,
        "SELECT DISTINCT Item FROM creature_loot_template WHERE Entry = %s "
        "ORDER BY Item LIMIT 25",
        [entry],
    )
    if err:
        return []
    items = [int(r["Item"]) for r in rows if int(r["Item"] or 0) > 0]
    return _item_names(server, items[:_MAX_LOOT_ITEMS], _MAX_LOOT_ITEMS)


def encounter_tools(server) -> Dict[str, Any]:
    args = server.args or {}

    map_id = args.get("map")
    if not isinstance(map_id, int) or isinstance(map_id, bool):
        return {"error": "'map' is required and must be a map id (number).",
                "isError": True}
    max_creatures = args.get("limit", _MAX_CREATURES)
    if not isinstance(max_creatures, int) or isinstance(max_creatures, bool) \
            or not 1 <= max_creatures <= 100:
        return {"error": "'limit' must be an integer between 1 and 100.",
                "isError": True}

    # ---- map name (DBC-first, same pattern as spawns) --------------------
    map_name = None
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
            rec = reader.get_record_by_id(map_id)
            if rec:
                v = rec.get(name_idx)
                if isinstance(v, str) and v.strip():
                    map_name = v.strip()
    except Exception:
        pass

    # ---- instance metadata ------------------------------------------------
    instance = None
    it_rows, _ = _q(
        server,
        "SELECT map, parent, script, allowMount FROM instance_template "
        "WHERE map = %s",
        [map_id],
    )
    if it_rows:
        it = it_rows[0]
        instance = {
            "map": map_id,
            "script": it.get("script") or None,
            "allow_mount": int(it.get("allowMount") or 0),
            "parent_instance": int(it.get("parent") or 0) or None,
        }

    # ---- top creatures -----------------------------------------------------
    c_rows, c_err = _q(
        server,
        "SELECT c.id, COUNT(*) AS spawns FROM creature c "
        "WHERE c.map = %s GROUP BY c.id ORDER BY spawns DESC, c.id LIMIT %s",
        [map_id, max_creatures],
    )
    if c_err:
        return {"error": f"could not read creature table: {c_err[:200]}",
                "isError": True}
    if not c_rows:
        return {
            "map": map_id,
            "map_name": map_name,
            "is_instance": False,
            "creatures": [],
            "gameobjects": [],
            "error": None,
            "metadata": {
                "note": f"No creatures spawn on map {map_id} - check the map id "
                        "(use list/search on the Map datastore)."
            },
        }

    entries = [int(r["id"]) for r in c_rows]
    ph = ",".join(["%s"] * len(entries))
    t_rows, _ = _q(
        server,
        f"SELECT entry, name, subname, minlevel, maxlevel, `rank` "
        f"FROM creature_template WHERE entry IN ({ph})",
        entries,
    )
    templates = {int(r["entry"]): r for r in t_rows}

    creatures = []
    for r in c_rows:
        e = int(r["id"])
        t = templates.get(e)
        c: Dict[str, Any] = {
            "entry": e,
            "name": t["name"] if t else f"(template {e} not found)",
            "minlevel": int(t["minlevel"]) if t and t.get("minlevel") is not None else None,
            "maxlevel": int(t["maxlevel"]) if t and t.get("maxlevel") is not None else None,
            "spawn_count": int(r["spawns"]),
        }
        if t and t.get("subname"):
            c["subname"] = t["subname"]
        if t and t.get("rank"):
            c["rank"] = int(t["rank"])  # 0=normal, 1=rare, 2=elite, 3=worldboss
        creatures.append(c)

    # loot for the top 5 only (keeps the call fast + the payload lean)
    for c in creatures[:5]:
        if c["entry"] in templates:
            loot = _loot_items(server, c["entry"])
            if loot:
                c["loot"] = loot

    # ---- top game objects ---------------------------------------------------
    g_rows, _ = _q(
        server,
        "SELECT g.id, COUNT(*) AS count FROM gameobject g "
        "WHERE g.map = %s GROUP BY g.id ORDER BY count DESC, g.id LIMIT %s",
        [map_id, _MAX_GAMEOBJECTS],
    )
    gameobjects = []
    if g_rows:
        g_entries = [int(r["id"]) for r in g_rows]
        gph = ",".join(["%s"] * len(g_entries))
        gt_rows, _ = _q(
            server,
            f"SELECT entry, name, type FROM gameobject_template "
            f"WHERE entry IN ({gph})",
            g_entries,
        )
        gt = {int(r["entry"]): r for r in gt_rows}
        for r in g_rows:
            e = int(r["id"])
            t = gt.get(e)
            gameobjects.append({
                "entry": e,
                "name": t["name"] if t else f"(go {e} not found)",
                "type": int(t["type"]) if t and t.get("type") is not None else None,
                "count": int(r["count"]),
            })

    # ---- travel graph (optional) --------------------------------------------
    travel = None
    try:
        t_rows, t_err = _q(
            server,
            "SELECT COUNT(DISTINCT id) AS nodes FROM playerbots_travelnode "
            "WHERE map_id = %s",
            [map_id],
            db="acore_playerbots",
        )
        if t_err is None and t_rows:
            nodes = int(t_rows[0]["nodes"] or 0)
            p_rows, _ = _q(
                server,
                "SELECT COUNT(*) AS pts FROM playerbots_travelnode_path "
                "WHERE map_id = %s",
                [map_id],
                db="acore_playerbots",
            )
            travel = {
                "nodes": nodes,
                "path_points": int(p_rows[0]["pts"] or 0) if p_rows else 0,
            }
            if nodes == 0:
                travel["note"] = "no travel graph generated for this map"
    except Exception:
        pass  # mod DB absent - travel simply omitted

    return {
        "map": map_id,
        "map_name": map_name,
        "is_instance": instance is not None,
        **({"instance": instance} if instance else {}),
        "creature_count": len(creatures),
        "creatures": creatures,
        "gameobjects": gameobjects,
        **({"travel": travel} if travel else {}),
        "metadata": {
            "note": (
                f"Top {min(max_creatures, len(creatures))} creatures by spawn count "
                "(loot shown for top 5). rank: 0=normal 1=rare 2=elite 3=worldboss. "
                "Game objects are capped at 10. Use query/resolve for per-creature "
                "spell details."
            ),
            "sql_tables": ["creature", "creature_template", "creature_loot_template",
                           "item_template", "gameobject", "gameobject_template",
                           "instance_template"],
            "sql_database": "acore_world",
        },
    }


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "encounter",
        "description": (
            "Map/instance encounter rollup: top creatures by spawn count with "
            "level ranges, rank and (top 5) loot item names, top game objects "
            "(doors/switches/chests), instance metadata (script, allow_mount) "
            "when the map is an instance, and the mod-playerbots travel graph "
            "size when installed. Read-only, acore_world based - works on any "
            "azerothcore-wotlk install."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "map": {
                    "type": "number",
                    "description": "Map id (required)."
                },
                "limit": {
                    "type": "number",
                    "description": "Max creatures to list (default 20, max 100)."
                },
            },
            "required": ["map"],
        },
    }
