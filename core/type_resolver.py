"""
Type resolver for acore-data.

Registry-driven resolution engine. Reads cross-reference metadata from
datastore_registry.json to resolve fields for ANY table with registered
references. No hardcoded mappings needed.

Currently resolves:
  - DBC lookups (dbc_backed / dbc_entry references) -> names/labels
  - SQL lookups (sql_objectmgr / sql_manager / etc.) -> names/labels
  - Loot templates (external references) -> item lists
  - Quest template resolution -> starters, enders, POIs, chain info
"""

from typing import Dict, Any, List, Optional


GO_TYPE_NAMES = {
    0: "DOOR",
    1: "BUTTON",
    2: "QUESTGIVER",
    3: "CHEST",
    4: "BINDER",
    5: "GENERIC",
    6: "TRAP",
    7: "CHAIR",
    8: "SPELL_FOCUS",
    9: "TEXT",
    10: "GOOBER",
    11: "TRANSPORT",
    12: "AREADAMAGE",
    13: "CAMERA",
    14: "MAP_OBJECT",
    15: "MO_TRANSPORT",
    16: "DUEL_ARBITER",
    17: "FISHINGNODE",
    18: "SUMMONING_RITUAL",
    19: "MAILBOX",
    20: "AUCTIONHOUSE",
    21: "GUARDPOST",
    22: "SPELLCASTER",
    23: "MEETINGSTONE",
    24: "FLAGSTAND",
    25: "FISHINGHOLE",
    26: "FLAGDROP",
    27: "MINI_GAME",
    28: "LOTTERY_KIOSK",
    29: "CAPTURE_POINT",
    30: "AURA_GENERATOR",
    31: "DUNGEON_DIFFICULTY",
    32: "BARBER_CHAIR",
    33: "DESTRUCTIBLE_BUILDING",
    34: "GUILD_BANK",
    35: "TRAPDOOR",
}


def _classify_target(ref_type: str, target_entry: Optional[Dict]) -> str:
    """Classify a target into dbc/sql/loot resolution category."""
    if ref_type in ("dbc_backed", "dbc_entry"):
        return "dbc"
    if target_entry:
        cat = target_entry.get("category", "")
        name_lower = (target_entry.get("sql_table", target_entry.get("dbc_name", "")) or "").lower()
        if "loot" in name_lower and "template" in name_lower:
            return "loot"
        if cat.startswith("sql_"):
            return "sql"
        if cat == "dbc_backed":
            return "dbc"
    if ref_type == "external":
        return "loot"
    return "sql"


def _get_row_value(row: Dict, sql_col: str, field_name: str):
    """Get value from row by column name (case-insensitive)."""
    for key in [sql_col, field_name]:
        if key and key in row:
            return row[key]
    key_lower = (sql_col or field_name or "").lower()
    for k, v in row.items():
        if k.lower() == key_lower:
            return v
    return None


def _get_row_pk(row: Dict):
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def _find_registry_entry(server, table_name: str) -> Optional[Dict]:
    """Find registry entry by SQL table name, DBC name, or struct name."""
    resolved = server.registry._resolve_entry(table_name)
    if resolved:
        return resolved[1]
    entries = server.registry.registry.get("entries", {})
    table_lower = table_name.lower()
    for name, entry in entries.items():
        if (entry.get("sql_table", "") or "").lower() == table_lower:
            return entry
        if (entry.get("dbc_name", "") or "").lower() == table_lower:
            return entry
    return None


def resolve_type_fields(
    server,
    sql_table: str,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve cross-reference fields for any table with registry metadata.

    Args:
        server: Server instance with database module
        sql_table: SQL table name or DBC name to resolve
        rows: Query results to resolve fields for
        resolve_filter: What to resolve - True (all), list of types, or False
        resolve_max: Max items to return for loot tables (0 = no limit)

    Returns:
        Dict with resolved field data for each row
    """
    if not rows or not resolve_filter:
        return {}

    reg_entry = _find_registry_entry(server, sql_table)
    if not reg_entry:
        return {}

    # Special case: gameobject_template uses type-conditional resolution
    if sql_table == "gameobject_template" and "type_field_mappings" in reg_entry:
        return _resolve_gameobject_fields(server, reg_entry, rows, resolve_filter, resolve_max)

    # Special case: quest_template resolves starters, enders, POIs, chain
    if sql_table == "quest_template":
        return _resolve_quest_fields(server, reg_entry, rows, resolve_filter, resolve_max)

    # Generic resolution for all other tables
    return _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)


def _resolve_generic(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve fields using registry cross-reference metadata.

    Works for any table that has fields with 'references' in the registry.
    Handles DBC lookups, SQL lookups, and loot template expansion.
    """
    fields = reg_entry.get("fields", {})
    registry = server.registry.registry.get("entries", {})

    # Build list of resolvable fields from registry metadata
    resolvable = []
    for fid, finfo in fields.items():
        if not isinstance(finfo, dict):
            continue
        target = finfo.get("references")
        if not target or target == "self_ref":
            continue
        if isinstance(target, list):  # Complex multi-ref (e.g. gameobject data[])
            continue

        ref_type = finfo.get("reference_type", "")
        ref_col = finfo.get("reference_column", "ID")
        sql_col = finfo.get("sql_column", finfo.get("name", ""))
        field_name = finfo.get("name", fid)

        target_entry = registry.get(target)
        resolve_category = _classify_target(ref_type, target_entry)

        # Determine the lookup name for the target
        if resolve_category == "dbc" and target_entry:
            lookup_name = target_entry.get("dbc_name", target.replace("Entry", ""))
        elif resolve_category == "sql" and target_entry:
            lookup_name = target_entry.get("sql_table", target)
        elif resolve_category == "loot" and target_entry:
            lookup_name = target_entry.get("sql_table", target)
        else:
            lookup_name = target

        resolvable.append({
            "field_id": fid,
            "field_name": field_name,
            "sql_col": sql_col,
            "target": target,
            "ref_type": ref_type,
            "ref_col": ref_col,
            "resolve_category": resolve_category,
            "lookup_name": lookup_name,
        })

    if not resolvable:
        return {}

    # Determine allowed resolve types
    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    resolved = {}
    for row in rows:
        pk = _get_row_pk(row)
        row_resolved = {}

        for r in resolvable:
            raw_value = _get_row_value(row, r["sql_col"], r["field_name"])
            if raw_value is None or raw_value == 0:
                continue

            entry_resolved = {
                "meaning": r["field_name"],
                "raw": raw_value,
            }

            if r["resolve_category"] == "dbc" and "dbc" in allowed:
                resolved_val = _resolve_dbc_ref(server, r["lookup_name"], raw_value, r["ref_col"])
                if resolved_val:
                    entry_resolved["resolved_to"] = resolved_val

            elif r["resolve_category"] == "sql" and "sql" in allowed:
                resolved_val = _resolve_sql_ref(server, r["lookup_name"], raw_value, r["ref_col"])
                if resolved_val:
                    entry_resolved["resolved_to"] = resolved_val

            elif r["resolve_category"] == "loot" and "loot" in allowed:
                loot_items = _resolve_loot_ref(server, r["lookup_name"], raw_value, r["ref_col"], resolve_max)
                if loot_items:
                    entry_resolved.update(loot_items)

            if "resolved_to" in entry_resolved or "items" in entry_resolved:
                row_resolved[r["sql_col"]] = entry_resolved

        if row_resolved:
            resolved[pk] = row_resolved

    return resolved


def _resolve_quest_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve quest_template with enriched cross-reference data.

    For each quest row, automatically includes:
    - Starters: NPCs/GOs that offer this quest (creature_queststarter, gameobject_queststarter)
    - Ender:   NPCs/GOs that accept this quest (creature_questender, gameobject_questender)
    - POIs:    Point-of-interest coordinates from quest_poi + quest_poi_points
    - Chain:   prevQuestID, nextQuestID, breadcrumbForQuestId from quest_template_addon

    On top of the generic field resolution (faction, spell, item refs).
    """
    # First get generic resolution for base fields
    base_resolved = _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)

    if not rows:
        return base_resolved

    # Determine allowed resolve types
    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return base_resolved

    if "sql" not in allowed:
        # Quest enrichment requires SQL lookups; skip if not allowed
        return base_resolved

    # Resolve starters, enders, POIs, chain for each quest
    resolved = {}
    for row in rows:
        quest_id = _get_row_pk(row)
        entry_resolved = base_resolved.get(quest_id, {})

        starters = []
        enders = []
        pois = []
        chain = {}

        # --- Quest Starters (NPCs) ---
        try:
            sql = f"SELECT id, quest FROM creature_queststarter WHERE quest = {int(quest_id)} LIMIT 20"
            rows_data, _ = server.database._query_database(sql)
            for r in rows_data:
                npc_id = r.get("id", 0)
                if npc_id:
                    name = _resolve_sql_ref(server, "creature_template", npc_id, "entry")
                    starters.append({"type": "npc", "id": npc_id, "name": name})
        except Exception:
            pass

        # --- Quest Starters (GOs) ---
        try:
            sql = f"SELECT id, quest FROM gameobject_queststarter WHERE quest = {int(quest_id)} LIMIT 20"
            rows_data, _ = server.database._query_database(sql)
            for r in rows_data:
                go_id = r.get("id", 0)
                if go_id:
                    name = _resolve_sql_ref(server, "gameobject_template", go_id, "entry")
                    starters.append({"type": "go", "id": go_id, "name": name})
        except Exception:
            pass

        # --- Quest Enders (NPCs) ---
        try:
            sql = f"SELECT id, quest FROM creature_questender WHERE quest = {int(quest_id)} LIMIT 20"
            rows_data, _ = server.database._query_database(sql)
            for r in rows_data:
                npc_id = r.get("id", 0)
                if npc_id:
                    name = _resolve_sql_ref(server, "creature_template", npc_id, "entry")
                    enders.append({"type": "npc", "id": npc_id, "name": name})
        except Exception:
            pass

        # --- Quest Enders (GOs) ---
        try:
            sql = f"SELECT id, quest FROM gameobject_questender WHERE quest = {int(quest_id)} LIMIT 20"
            rows_data, _ = server.database._query_database(sql)
            for r in rows_data:
                go_id = r.get("id", 0)
                if go_id:
                    name = _resolve_sql_ref(server, "gameobject_template", go_id, "entry")
                    enders.append({"type": "go", "id": go_id, "name": name})
        except Exception:
            pass

        # --- Quest POIs ---
        try:
            sql_poi = f"""
                SELECT qp.id, qp.questID, qp.MapID, qp.ObjectiveIndex, qp.Flags,
                       qp.Idx1, qp.Idx2, qp.Icon, qpp.SurveyLongitude, qpp.SurveyLatitude
                FROM quest_poi qp
                LEFT JOIN quest_poi_points qpp ON qp.id = qpp.ID AND qp.questID = qpp.QuestId
                WHERE qp.questID = {int(quest_id)}
                LIMIT 20
            """
            poi_rows, _ = server.database._query_database(sql_poi)
            for p in poi_rows:
                pois.append({
                    "ObjectiveIndex": p.get("ObjectiveIndex", -1),
                    "turn_in_point": p.get("ObjectiveIndex", -1) == -1,
                    "MapID": p.get("MapID"),
                    "longitude": p.get("SurveyLongitude"),
                    "latitude": p.get("SurveyLatitude"),
                    "icon": p.get("Icon"),
                })
        except Exception:
            pass

        # --- Quest Chain ---
        try:
            sql_chain = f"""
                SELECT PrevQuestId, NextQuestId, BreadcrumbForQuestId
                FROM quest_template_addon WHERE ID = {int(quest_id)} LIMIT 1
            """
            chain_rows, _ = server.database._query_database(sql_chain)
            if chain_rows:
                cr = chain_rows[0]
                prev_id = cr.get("PrevQuestId", 0) or 0
                next_id = cr.get("NextQuestId", 0) or 0
                breadcrumb_id = cr.get("BreadcrumbForQuestId", 0) or 0

                if prev_id:
                    prev_name = _resolve_sql_ref(server, "quest_template", prev_id, "ID")
                    chain["prev_quest"] = {"id": prev_id, "name": prev_name}
                if next_id:
                    next_name = _resolve_sql_ref(server, "quest_template", next_id, "ID")
                    chain["next_quest"] = {"id": next_id, "name": next_name}
                if breadcrumb_id:
                    bc_name = _resolve_sql_ref(server, "quest_template", breadcrumb_id, "ID")
                    chain["breadcrumb_for"] = {"id": breadcrumb_id, "name": bc_name}
        except Exception:
            pass

        # Merge enriched data into resolved entry
        enriched = {}
        if starters:
            enriched["starters"] = starters
        if enders:
            enriched["enders"] = enders
        if pois:
            enriched["pois"] = pois
        if chain:
            enriched["chain"] = chain

        # Merge with base resolution
        merged = {**entry_resolved, **enriched}
        if merged:
            resolved[quest_id] = merged

    return resolved


def _resolve_gameobject_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve gameobject_template type-specific fields from registry."""
    type_mappings = reg_entry.get("type_field_mappings", {})
    if not type_mappings:
        return {}

    resolved = {}
    for row in rows:
        entry_value = row.get("entry")
        go_type = row.get("type", 0)

        type_name = GO_TYPE_NAMES.get(go_type, f"UNKNOWN({go_type})")
        field_map = type_mappings.get(str(go_type), {})

        if not field_map:
            continue

        row_resolved = {"type_name": type_name}

        if isinstance(resolve_filter, list):
            allowed_refs = set(resolve_filter)
        elif resolve_filter is True:
            allowed_refs = {"dbc", "sql", "loot"}
        else:
            continue

        for data_col, field_info in field_map.items():
            raw_value = row.get(data_col)
            if raw_value is None:
                for key in row:
                    if key.lower() == data_col.lower():
                        raw_value = row[key]
                        break
            if raw_value is None or raw_value == 0:
                continue

            ref_type = field_info.get("resolve_type", "")
            if not ref_type:
                continue

            entry_resolved = {
                "meaning": field_info["name"],
                "raw": raw_value,
            }

            if ref_type == "dbc" and "dbc" in allowed_refs:
                dbc_name = field_info.get("target", "")
                id_col = field_info.get("id_col", "ID")
                resolved_value = _resolve_dbc_ref(server, dbc_name, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "sql" and "sql" in allowed_refs:
                table = field_info.get("target", "")
                id_col = field_info.get("id_col", "entry") or "entry"
                resolved_value = _resolve_sql_ref(server, table, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "loot" and "loot" in allowed_refs:
                table = field_info.get("target", "gameobject_loot_template")
                id_col = field_info.get("id_col", "Entry")
                loot_items = _resolve_loot_ref(server, table, raw_value, id_col, resolve_max)
                if loot_items is not None:
                    entry_resolved.update(loot_items)

            row_resolved[data_col] = entry_resolved

        resolved[entry_value] = row_resolved

    return resolved


def _resolve_dbc_ref(
    server,
    dbc_name: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve a DBC reference by ID to its name/title."""
    try:
        reader = server._load_dbc(dbc_name)

        record = reader.get_record_by_id(ref_id)
        if not record:
            return f"{dbc_name} [{ref_id}] (not found)"

        # Try to find a name/title string field
        for idx, value in record.items():
            if isinstance(value, str) and value:
                return f"{dbc_name} [{value}]"

        # No string name found - return ID-based reference
        return f"{dbc_name} [{ref_id}]"
    except Exception:
        return None


def _resolve_sql_ref(
    server,
    table: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve an SQL reference by ID to its key identifying field."""
    try:
        sql = f"SELECT * FROM {table} WHERE {id_col} = {ref_id} LIMIT 1"
        rows, _ = server.database._query_database(sql)

        if rows:
            row = rows[0]
            # Find a meaningful identifier from the result
            for col in ["name", "LogTitle", "entry", "ID"]:
                if col in row and row[col]:
                    return f"{table} [{row[col]}]"
            return f"{table} [{ref_id}]"

        return f"{table} [{ref_id}] (not found)"
    except Exception:
        return None


def _resolve_loot_ref(
    server,
    table: str,
    loot_id: int,
    id_col: str = "Entry",
    resolve_max: int = 10,
) -> Optional[Dict[str, Any]]:
    """Resolve a loot template reference to item list."""
    try:
        sql = f"SELECT Item, Chance, MinCount, MaxCount FROM {table} WHERE {id_col} = {loot_id}"
        items, _ = server.database._query_database(sql)

        if not items:
            return {"resolved_to": f"{table} [{loot_id}]", "warning": "Empty loot template"}

        total_items = len(items)
        display_items = []

        for item_row in items[:resolve_max]:
            item_id = item_row.get("Item", 0)
            if not item_id:
                continue

            # Resolve item name
            sql_item = f"SELECT entry, name FROM item_template WHERE entry = {item_id} LIMIT 1"
            item_rows, _ = server.database._query_database(sql_item)
            item_name = ""
            if item_rows:
                item_name = item_rows[0].get("name", "")

            display_items.append({
                "Item": item_id,
                "name": item_name,
                "Chance": item_row.get("Chance", 100),
                "MinCount": item_row.get("MinCount", 1),
                "MaxCount": item_row.get("MaxCount", 1),
            })

        result = {
            "resolved_to": f"{table} [{loot_id}]",
            "items": display_items,
        }

        if resolve_max and total_items > resolve_max:
            result["warning"] = (
                f"Loot template has {total_items} items, showing first {resolve_max}. "
                f"Use resolve_max=0 to show all."
            )

        return result

    except Exception:
        return None
