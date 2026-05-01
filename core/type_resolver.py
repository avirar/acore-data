"""
Type resolver for acore-data.

Provides type-aware field resolution for tables with type-specific data fields.
Currently supports: gameobject_template, creature_template, item_template.

Each table type has a mapping that defines which data fields reference other
datastores and how to resolve those references.
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


GAMEOBJECT_FIELD_MAP = {
    # GAMEOBJECT_TYPE_DOOR (0)
    0: {
        "data1": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_BUTTON (1)
    1: {
        "data1": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data3": {"name": "linkedTrap", "references": "sql", "table": "gameobject_template"},
    },
    # GAMEOBJECT_TYPE_QUESTGIVER (2)
    2: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data3": {"name": "gossipID", "references": "sql", "table": "gossip_menu_option", "id_col": "menu_id"},
    },
    # GAMEOBJECT_TYPE_CHEST (3)
    3: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data1": {"name": "lootId", "references": "loot", "table": "gameobject_loot_template", "id_col": "Entry"},
        "data6": {"name": "eventId", "references": "sql", "table": "event_scripts"},
        "data7": {"name": "linkedTrapId", "references": "sql", "table": "gameobject_template"},
        "data8": {"name": "questId", "references": "sql", "table": "quest_template", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_GENERIC (5)
    5: {
        "data5": {"name": "questId", "references": "sql", "table": "quest_template", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_TRAP (6)
    6: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data3": {"name": "spellId", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_SPELL_FOCUS (8)
    8: {
        "data0": {"name": "focusId", "references": "dbc", "dbc_name": "SpellFocusObject", "id_col": "ID"},
        "data4": {"name": "questID", "references": "sql", "table": "quest_template", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_TEXT (9)
    9: {
        "data0": {"name": "pageID", "references": "sql", "table": "page_text", "id_col": "entry"},
    },
    # GAMEOBJECT_TYPE_GOOBER (10)
    10: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data1": {"name": "questId", "references": "sql", "table": "quest_template", "id_col": "ID"},
        "data2": {"name": "eventId", "references": "sql", "table": "event_scripts"},
        "data10": {"name": "spellId", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data12": {"name": "linkedTrapId", "references": "sql", "table": "gameobject_template"},
        "data19": {"name": "gossipID", "references": "sql", "table": "gossip_menu_option", "id_col": "menu_id"},
    },
    # GAMEOBJECT_TYPE_AREADAMAGE (12)
    12: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_CAMERA (13)
    13: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data1": {"name": "cinematicId", "references": "dbc", "dbc_name": "CinematicCamera", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_MO_TRANSPORT (15)
    15: {
        "data0": {"name": "taxiPathId", "references": "dbc", "dbc_name": "TaxiPath", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_SUMMONING_RITUAL (18)
    18: {
        "data1": {"name": "spellId", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data2": {"name": "animSpell", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data4": {"name": "casterTargetSpell", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_SPELLCASTER (22)
    22: {
        "data0": {"name": "spellId", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_FLAGSTAND (24)
    24: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data1": {"name": "pickupSpell", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data3": {"name": "returnAura", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data4": {"name": "returnSpell", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_FISHINGHOLE (25)
    25: {
        "data1": {"name": "lootId", "references": "loot", "table": "gameobject_loot_template", "id_col": "Entry"},
        "data4": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_FLAGDROP (26)
    26: {
        "data0": {"name": "lockId", "references": "dbc", "dbc_name": "Lock", "id_col": "ID"},
        "data2": {"name": "pickupSpell", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_AURA_GENERATOR (30)
    30: {
        "data2": {"name": "auraID1", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
        "data4": {"name": "auraID2", "references": "dbc", "dbc_name": "Spell", "id_col": "ID"},
    },
    # GAMEOBJECT_TYPE_DUNGEON_DIFFICULTY (31)
    31: {
        "data0": {"name": "mapID", "references": "dbc", "dbc_name": "Map", "id_col": "ID"},
    },
}


def resolve_type_fields(
    server,
    sql_table: str,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve type-specific data fields for supported tables.

    Args:
        server: Server instance with database module
        sql_table: SQL table name (gameobject_template, etc.)
        rows: Query results to resolve fields for
        resolve_filter: What to resolve - True (all), list of types, or False
        resolve_max: Max items to return for loot tables (0 = no limit)

    Returns:
        Dict with resolved field data for each row
    """
    if not rows or not resolve_filter:
        return {}

    resolvers = {
        "gameobject_template": _resolve_gameobject_fields,
    }

    resolver = resolvers.get(sql_table)
    if not resolver:
        return {}

    return resolver(server, sql_table, rows, resolve_filter, resolve_max)


def _resolve_gameobject_fields(
    server,
    sql_table: str,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve gameobject_template type-specific fields."""
    resolved = {}

    for row in rows:
        entry_value = row.get("entry")
        go_type = row.get("type", 0)

        type_name = GO_TYPE_NAMES.get(go_type, f"UNKNOWN({go_type})")
        field_map = GAMEOBJECT_FIELD_MAP.get(go_type, {})

        if not field_map:
            continue

        row_resolved = {"type_name": type_name}

        # Determine which references to resolve based on filter
        if isinstance(resolve_filter, list):
            allowed_refs = set(resolve_filter)
        elif resolve_filter is True:
            allowed_refs = {"dbc", "sql", "loot"}
        else:
            continue

        for data_col, field_info in field_map.items():
            # Case-insensitive column lookup (SQL has Data0, map uses data0)
            raw_value = row.get(data_col)
            if raw_value is None:
                for key in row:
                    if key.lower() == data_col.lower():
                        raw_value = row[key]
                        break
            if raw_value is None or raw_value == 0:
                continue

            ref_type = field_info.get("references", "")

            # Skip non-resolvable fields (boolean flags, etc.)
            if not ref_type:
                continue

            entry_resolved = {
                "meaning": field_info["name"],
                "raw": raw_value,
            }

            if ref_type == "dbc" and "dbc" in allowed_refs:
                dbc_name = field_info.get("dbc_name", "")
                id_col = field_info.get("id_col", "ID")
                resolved_value = _resolve_dbc_ref(server, dbc_name, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "sql" and "sql" in allowed_refs:
                table = field_info.get("table", "")
                id_col = field_info.get("id_col", "ID") or field_info.get("id_col", "entry")
                resolved_value = _resolve_sql_ref(server, table, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "loot" and "loot" in allowed_refs:
                table = field_info.get("table", "gameobject_loot_template")
                id_col = field_info.get("id_col", "Entry")
                loot_items = _resolve_loot_ref(server, table, raw_value, id_col, resolve_max)
                if loot_items is not None:
                    entry_resolved.update(loot_items)

            row_resolved[data_col] = entry_resolved

        # Use entry as key for single rows, or index-based for multiple
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
