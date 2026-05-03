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
  - Conditions table -> polymorphic source/value resolution with enum translation
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

    # Special case: conditions table uses polymorphic resolution
    if sql_table == "conditions":
        return _resolve_condition_fields(server, reg_entry, rows, resolve_filter, resolve_max)

    # Special case: smart_scripts triple-polymorphic resolution
    if sql_table == "smart_scripts":
        return _resolve_smart_script_fields(server, reg_entry, rows, resolve_filter, resolve_max)

    # Special case: achievement_criteria_data polymorphic resolution
    if sql_table == "achievement_criteria_data":
        return _resolve_achievement_criteria_fields(server, reg_entry, rows, resolve_filter, resolve_max)

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


# Enum name maps for condition table polymorphic fields
_SOURCE_TYPE_NAMES = {
    0: "NONE", 1: "CREATURE_LOOT", 2: "DISENCHANT_LOOT", 3: "FISHING_LOOT",
    4: "GAMEOBJECT_LOOT", 5: "ITEM_LOOT", 6: "MAIL_LOOT", 7: "MILLING_LOOT",
    8: "PICKPOCKETING_LOOT", 9: "PROSPECTING_LOOT", 10: "REFERENCE_LOOT",
    11: "SKINNING_LOOT", 12: "SPELL_LOOT", 13: "SPELL_IMPLICIT_TARGET",
    14: "GOSSIP_MENU", 15: "GOSSIP_MENU_OPTION", 16: "CREATURE_TEMPLATE_VEHICLE",
    17: "SPELL", 18: "SPELL_CLICK_EVENT", 19: "QUEST_AVAILABLE",
    20: "GOSSIP_HELLO", 21: "VEHICLE_SPELL", 22: "SMART_EVENT",
    23: "NPC_VENDOR", 24: "SPELL_PROC", 25: "TERRAIN_SWAP", 26: "PHASE",
    27: "GRAVEYARD", 28: "PLAYER_LOOT", 29: "CREATURE_RESPAWN",
    30: "OBJECT_VISIBILITY",
}

_CONDITION_TYPE_NAMES = {
    0: "NONE", 1: "AURA", 2: "ITEM", 3: "ITEM_EQUIPPED", 4: "ZONEID",
    5: "REPUTATION_RANK", 6: "TEAM", 7: "SKILL", 8: "QUESTREWARDED",
    9: "QUESTTAKEN", 10: "DRUNKENSTATE", 11: "WORLD_STATE",
    12: "ACTIVE_EVENT", 13: "INSTANCE_INFO", 14: "QUEST_NONE",
    15: "CLASS", 16: "RACE", 17: "ACHIEVEMENT", 18: "TITLE",
    19: "SPAWNMASK", 20: "GENDER", 21: "UNIT_STATE", 22: "MAPID",
    23: "AREAID", 24: "CREATURE_TYPE", 25: "SPELL_LEARNED", 26: "PHASEMASK",
    27: "LEVEL", 28: "QUEST_COMPLETE", 29: "NEAR_CREATURE",
    30: "NEAR_GAMEOBJECT", 31: "OBJECT_ENTRY_GUID", 32: "TYPE_MASK",
    33: "RELATION_TO", 34: "REACTION_TO", 35: "DISTANCE_TO", 36: "ALIVE",
    37: "HP_VAL", 38: "HP_PCT", 39: "REALM_ACHIEVEMENT", 40: "IN_WATER",
    42: "STAND_STATE", 43: "DAILY_QUEST_DONE", 44: "CHARMED", 45: "PET_TYPE",
    46: "TAXI", 47: "QUESTSTATE", 48: "QUEST_OBJ_PROGRESS",
    49: "DIFFICULTY_ID", 101: "QUEST_SATISFY_EXCLUSIVE",
    102: "HAS_AURA_TYPE", 103: "WORLD_SCRIPT", 104: "AI_DATA",
    105: "PLAYER_QUEUED_RANDOM_DUNGEON",
}

_COMPARISON_TYPES = {0: ">=", 1: "<=", 2: "==", 3: "!="}


def _resolve_condition_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve conditions table with polymorphic field interpretation.

    Translates SourceTypeOrReferenceId and ConditionTypeOrReference to enum names,
    resolves SourceEntry based on source type (spell/quest/item/creature),
    resolves ConditionValue1 based on condition type (aura spell, quest, item, etc.).
    """
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    resolved = {}
    for row in rows:
        pk = _get_row_pk(row)

        source_type = row.get("SourceTypeOrReferenceId", 0) or 0
        condition_type = row.get("ConditionTypeOrReference", 0) or 0
        source_entry = row.get("SourceEntry", 0) or 0
        source_group = row.get("SourceGroup", 0) or 0
        cond_value1 = row.get("ConditionValue1", 0) or 0
        cond_value2 = row.get("ConditionValue2", 0) or 0
        cond_value3 = row.get("ConditionValue3", 0) or 0

        entry_resolved = {
            "source_type_name": _SOURCE_TYPE_NAMES.get(source_type, f"UNKNOWN({source_type})"),
            "condition_type_name": _CONDITION_TYPE_NAMES.get(condition_type, f"UNKNOWN({condition_type})"),
        }

        # Handle reference templates (negative values)
        if source_type < 0:
            entry_resolved["source_type_name"] = f"REFERENCE_TEMPLATE({abs(source_type)})"
            entry_resolved["raw_source_type"] = source_type

        if condition_type < 0:
            entry_resolved["condition_type_name"] = f"REFERENCE_TO_CONDITION({abs(condition_type)})"
            entry_resolved["raw_condition_type"] = condition_type
            condition_type = 0  # Don't attempt value resolution for references

        # --- Resolve SourceEntry based on SourceType ---
        if source_entry and "sql" in allowed:
            resolved_source = _resolve_condition_source(server, source_type, source_entry, source_group)
            if resolved_source:
                entry_resolved["source_entry"] = resolved_source

        # --- Resolve ConditionValue1-3 based on ConditionType ---
        if cond_value1 and "sql" in allowed:
            resolved_values = _resolve_condition_values(server, condition_type, cond_value1, cond_value2, cond_value3)
            if resolved_values:
                entry_resolved["condition_values"] = resolved_values

        # --- Effect bitmask annotation for SPELL_IMPLICIT_TARGET ---
        if source_type == 13 and source_group:
            effects = []
            if source_group & 1:
                effects.append("effect0")
            if source_group & 2:
                effects.append("effect1")
            if source_group & 4:
                effects.append("effect2")
            entry_resolved["source_group"] = f"effect_mask[{','.join(effects)}]"

        if pk and entry_resolved.get("source_entry") or entry_resolved.get("condition_values"):
            resolved[pk] = entry_resolved

    return resolved


def _resolve_condition_source(server, source_type: int, source_entry: int, source_group: int) -> Optional[Dict]:
    """Resolve SourceEntry based on SourceTypeOrReferenceId."""
    # Spell sources — resolve via Spell DBC first, fall back to SQL quest_template (some spell-like IDs are quests)
    if source_type in (13, 17, 24):
        name = _resolve_dbc_ref(server, "Spell", source_entry) or _resolve_sql_ref(server, "quest_template", source_entry, "ID")
        return {"type": "spell", "id": source_entry, "name": name}

    if source_type in (18, 21):
        spell_name = _resolve_dbc_ref(server, "Spell", source_entry) or _resolve_sql_ref(server, "quest_template", source_entry, "ID")
        creature_name = _resolve_sql_ref(server, "creature_template", source_group, "entry")
        return {
            "spell": {"type": "spell", "id": source_entry, "name": spell_name},
            "trigger_by": {"type": "creature", "id": source_group, "name": creature_name},
        }

    # Quest sources
    if source_type == 19:
        name = _resolve_sql_ref(server, "quest_template", source_entry, "ID")
        return {"type": "quest", "id": source_entry, "name": name}

    # Gossip/menu sources
    if source_type in (14, 15):
        # Try gossip_menu_option table
        name = _resolve_sql_ref(server, "gossip_menu_option", source_entry, "menu_id")
        return {"type": "gossip", "id": source_entry, "name": name}

    if source_type == 20:
        creature_name = _resolve_sql_ref(server, "creature_template", source_entry, "entry")
        return {"type": "creature_gossip", "id": source_entry, "name": creature_name}

    # Creature template vehicle / respawn
    if source_type in (16, 29):
        name = _resolve_sql_ref(server, "creature_template", source_entry, "entry")
        return {"type": "creature", "id": source_entry, "name": name}

    return None


def _resolve_condition_values(
    server, condition_type: int, value1: int, value2: int, value3: int
) -> Optional[Dict]:
    """Resolve ConditionValue1-3 based on ConditionTypeOrReference."""
    result = {}

    # --- Spell references in conditions ---
    if condition_type == 1:  # AURA
        name = _resolve_dbc_ref(server, "Spell", value1) or _resolve_sql_ref(server, "quest_template", value1, "ID")
        result["spell"] = {"type": "aura_spell", "id": value1, "name": name}
        if value2:
            result["effect_index"] = int(value2)

    elif condition_type == 25:  # SPELL_LEARNED
        name = _resolve_dbc_ref(server, "Spell", value1) or _resolve_sql_ref(server, "quest_template", value1, "ID")
        result["spell"] = {"type": "learned_spell", "id": value1, "name": name}

    # --- Quest references in conditions ---
    elif condition_type in (8, 9, 14, 28, 43):  # QUESTREWARDED, QUESTTAKEN, QUEST_NONE, QUEST_COMPLETE, DAILY_QUEST_DONE
        quest_names = {8: "rewarded", 9: "taken", 14: "quest_none", 28: "completed", 43: "daily_done"}
        name = _resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": quest_names[condition_type], "id": value1, "name": name}

    elif condition_type == 47:  # QUESTSTATE
        name = _resolve_sql_ref(server, "quest_template", value1, "ID")
        states = []
        if value2 & 1: states.append("not_taken")
        if value2 & 2: states.append("completed")
        if value2 & 8: states.append("in_progress")
        if value2 & 32: states.append("failed")
        if value2 & 64: states.append("rewarded")
        result["quest"] = {"type": "state", "id": value1, "name": name}
        if states:
            result["states"] = states

    elif condition_type == 48:  # QUEST_OBJ_PROGRESS
        name = _resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": "objective", "id": value1, "name": name}
        if value2:
            result["objective_index"] = int(value2)
        if value3:
            result["progress_required"] = int(value3)

    elif condition_type == 101:  # QUEST_SATISFY_EXCLUSIVE
        name = _resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": "exclusive", "id": value1, "name": name}

    # --- Item references in conditions ---
    elif condition_type == 2:  # ITEM
        name = _resolve_sql_ref(server, "item_template", value1, "entry")
        result["item"] = {"type": "has_item", "id": value1, "name": name}
        if value2:
            result["count_required"] = int(value2)

    elif condition_type == 3:  # ITEM_EQUIPPED
        name = _resolve_sql_ref(server, "item_template", value1, "entry")
        result["item"] = {"type": "equipped_item", "id": value1, "name": name}

    # --- Creature references in conditions ---
    elif condition_type == 29:  # NEAR_CREATURE
        name = _resolve_sql_ref(server, "creature_template", value1, "entry")
        result["creature"] = {"type": "nearby_creature", "id": value1, "name": name}
        if value2:
            result["max_distance"] = int(value2)

    elif condition_type == 30:  # NEAR_GAMEOBJECT
        name = _resolve_sql_ref(server, "gameobject_template", value1, "entry")
        result["gameobject"] = {"type": "nearby_go", "id": value1, "name": name}
        if value2:
            result["max_distance"] = int(value2)

    # --- OBJECT_ENTRY_GUID (complex TypeID-based resolution) ---
    elif condition_type == 31:  # OBJECT_ENTRY_GUID
        type_id = int(value1)
        type_names = {0: "ITEM", 1: "CREATURE", 2: "GAMEOBJECT", 3: "DYNAMIC_OBJECT",
                      5: "GAMEOBJECT", 6: "PLAYER", 7: "VEHICLE"}
        result["type_id"] = {"raw": type_id, "name": type_names.get(type_id, f"TYPE({type_id})")}
        if value2 and type_id in (1,):
            name = _resolve_sql_ref(server, "creature_template", value2, "entry")
            result["target_entity"] = {"type": "creature", "id": value2, "name": name}
        elif value2 and type_id in (0,):
            name = _resolve_sql_ref(server, "item_template", value2, "entry")
            result["target_entity"] = {"type": "item", "id": value2, "name": name}
        elif value2:
            result["target_entity"] = {"id": value2, "type_id": type_id}

    # --- Level comparison ---
    elif condition_type == 27:  # LEVEL
        result["level"] = int(value1)
        if value2:
            result["comparison"] = _COMPARISON_TYPES.get(int(value2), f"RAW({value2})")

    # --- HP comparisons ---
    elif condition_type == 37:  # HP_VAL
        result["hp_value"] = int(value1)
        if value2:
            result["comparison"] = _COMPARISON_TYPES.get(int(value2), f"RAW({value2})")
    elif condition_type == 38:  # HP_PCT
        result["hp_percent"] = int(value1)
        if value2:
            result["comparison"] = _COMPARISON_TYPES.get(int(value2), f"RAW({value2})")

    # --- Distance to target ---
    elif condition_type == 35:  # DISTANCE_TO
        result["distance"] = int(value2)
        if value1:
            result["target_slot"] = int(value1)
        if value3:
            result["comparison"] = _COMPARISON_TYPES.get(int(value3), f"RAW({value3})")

    return result if result else None


# SAI event_type enum names (SmartEvent)
_SAI_EVENT_NAMES = {
    0: "UPDATE_IC", 1: "UPDATE_OOC", 2: "HEALTH_PCT", 3: "MANA_PCT",
    4: "AGGRO", 5: "KILL", 6: "DEATH", 7: "EVADE", 8: "SPELLHIT",
    9: "RANGE", 10: "OOC_LOS", 11: "RESPAWN", 12: "TARGET_HEALTH_PCT",
    13: "VICTIM_CASTING", 14: "FRIENDLY_HEALTH", 15: "FRIENDLY_IS_CC",
    16: "FRIENDLY_MISSING_BUFF", 17: "SUMMONED_UNIT", 18: "TARGET_MANA_PCT",
    19: "ACCEPTED_QUEST", 20: "REWARD_QUEST", 21: "REACHED_HOME",
    22: "RECEIVE_EMOTE", 23: "HAS_AURA", 24: "TARGET_BUFFED",
    25: "RESET", 26: "IC_LOS", 27: "PASSENGER_BOARDED",
    28: "PASSENGER_REMOVED", 29: "CHARMED", 30: "CHARMED_TARGET",
    31: "SPELLHIT_TARGET", 32: "DAMAGED", 33: "DAMAGED_TARGET",
    34: "MOVEMENTINFORM", 35: "SUMMON_DESPAWNED", 36: "CORPSE_REMOVED",
    37: "AI_INIT", 38: "DATA_SET", 39: "ESCORT_START", 40: "ESCORT_REACHED",
    41: "TRANSPORT_ADDPLAYER", 42: "TRANSPORT_ADDCREATURE", 43: "TRANSPORT_REMOVE_PLAYER",
    44: "TRANSPORT_RELOCATE", 45: "INSTANCE_PLAYER_ENTER",
    46: "AREATRIGGER_ONTRIGGER",
    47: "QUEST_ACCEPTED", 48: "QUEST_OBJ_COMPLETION", 49: "QUEST_COMPLETION",
    50: "QUEST_REWARDED", 51: "QUEST_FAIL",
    52: "TEXT_OVER", 53: "RECEIVE_HEAL",
    54: "JUST_SUMMONED", 55: "ESCORT_PAUSED", 56: "ESCORT_RESUMED",
    57: "ESCORT_STOPPED", 58: "ESCORT_ENDED", 59: "TIMED_EVENT_TRIGGERED",
    60: "UPDATE", 61: "LINK", 62: "GOSSIP_SELECT", 63: "JUST_CREATED",
    64: "GOSSIP_HELLO", 65: "FOLLOW_COMPLETED", 66: "EVENT_PHASE_CHANGE",
    67: "IS_BEHIND_TARGET", 68: "GAME_EVENT_START", 69: "GAME_EVENT_END",
    70: "GO_STATE_CHANGED", 71: "GO_EVENT_INFORM", 72: "ACTION_DONE",
    73: "ON_SPELLCLICK", 74: "FRIENDLY_HEALTH_PCT",
    75: "DISTANCE_CREATURE", 76: "DISTANCE_GAMEOBJECT",
    77: "COUNTER_SET", 82: "SUMMONED_UNIT_DIES",
    101: "NEAR_PLAYERS", 102: "NEAR_PLAYERS_NEGATION",
    103: "NEAR_UNIT", 104: "NEAR_UNIT_NEGATION",
    105: "AREA_CASTING", 106: "AREA_RANGE", 107: "SUMMONED_UNIT_EVADE",
    108: "WAYPOINT_REACHED", 109: "WAYPOINT_ENDED",
    110: "IS_IN_MELEE_RANGE",
}

# SAI action_type enum names (SmartAction) — covering all known values
_SAI_ACTION_NAMES = {
    0: "NONE", 1: "TALK", 2: "SET_FACTION", 3: "MORPH_TO_ENTRY_OR_MODEL",
    4: "SOUND", 5: "PLAY_EMOTE", 6: "FAIL_QUEST", 7: "OFFER_QUEST",
    8: "SET_REACT_STATE", 9: "ACTIVATE_GOBJECT", 10: "RANDOM_EMOTE",
    11: "CAST", 12: "SUMMON_CREATURE", 13: "THREAT_SINGLE_PCT",
    14: "THREAT_ALL_PCT", 15: "CALL_AREAEXPLOREDOREVENTHAPPENS",
    17: "SET_EMOTE_STATE", 18: "SET_UNIT_FLAG", 19: "REMOVE_UNIT_FLAG",
    20: "AUTO_ATTACK", 21: "ALLOW_COMBAT_MOVEMENT", 22: "SET_EVENT_PHASE",
    23: "INC_EVENT_PHASE", 24: "EVADE", 25: "FLEE_FOR_ASSIST",
    26: "CALL_GROUPEVENTHAPPENS", 27: "COMBAT_STOP",
    28: "REMOVEAURASFROMSPELL", 29: "FOLLOW", 30: "RANDOM_PHASE",
    31: "RANDOM_PHASE_RANGE", 32: "RESET_GOBJECT",
    33: "CALL_KILLEDMONSTER", 34: "SET_INST_DATA", 35: "SET_INST_DATA64",
    36: "UPDATE_TEMPLATE", 37: "DIE", 38: "SET_IN_COMBAT_WITH_ZONE",
    39: "CALL_FOR_HELP", 40: "SET_SHEATH", 41: "FORCE_DESPAWN",
    42: "SET_INVINCIBILITY_HP_LEVEL", 43: "MOUNT_TO_ENTRY_OR_MODEL",
    44: "SET_INGAME_PHASE_MASK", 45: "SET_DATA", 46: "MOVE_FORWARD",
    47: "SET_VISIBILITY", 48: "SET_ACTIVE", 49: "ATTACK_START",
    50: "SUMMON_GO", 51: "KILL_UNIT", 52: "ACTIVATE_TAXI",
    53: "ESCORT_START", 54: "ESCORT_PAUSE", 55: "ESCORT_STOP",
    56: "ADD_ITEM", 57: "REMOVE_ITEM", 58: "INSTALL_AI_TEMPLATE",
    59: "SET_RUN", 60: "SET_FLY", 61: "SET_SWIM", 62: "TELEPORT",
    63: "SET_COUNTER", 64: "STORE_TARGET_LIST", 65: "ESCORT_RESUME",
    66: "SET_ORIENTATION", 67: "CREATE_TIMED_EVENT", 68: "PLAYMOVIE",
    69: "MOVE_TO_POS", 70: "RESPAWN_TARGET", 71: "EQUIP",
    72: "CLOSE_GOSSIP", 73: "TRIGGER_TIMED_EVENT", 74: "REMOVE_TIMED_EVENT",
    75: "ADD_AURA", 76: "OVERRIDE_SCRIPT_BASE_OBJECT",
    77: "RESET_SCRIPT_BASE_OBJECT", 78: "CALL_SCRIPT_RESET",
    79: "SET_RANGED_MOVEMENT", 80: "CALL_TIMED_ACTIONLIST",
    81: "SET_NPC_FLAG", 82: "ADD_NPC_FLAG", 83: "REMOVE_NPC_FLAG",
    84: "SIMPLE_TALK", 85: "SELF_CAST", 86: "CROSS_CAST",
    87: "CALL_RANDOM_TIMED_ACTIONLIST", 88: "CALL_RANDOM_RANGE_TIMED_ACTIONLIST",
    89: "RANDOM_MOVE", 90: "SET_UNIT_FIELD_BYTES_1", 91: "REMOVE_UNIT_FIELD_BYTES_1",
    92: "INTERRUPT_SPELL", 93: "SEND_GO_CUSTOM_ANIM", 94: "SET_DYNAMIC_FLAG",
    95: "ADD_DYNAMIC_FLAG", 96: "REMOVE_DYNAMIC_FLAG", 97: "JUMP_TO_POS",
    98: "SEND_GOSSIP_MENU", 99: "GO_SET_LOOT_STATE",
    100: "SEND_TARGET_TO_TARGET", 101: "SET_HOME_POS", 102: "SET_HEALTH_REGEN",
    103: "SET_ROOT", 104: "SET_GO_FLAG", 105: "ADD_GO_FLAG",
    106: "REMOVE_GO_FLAG", 107: "SUMMON_CREATURE_GROUP",
    108: "SET_POWER", 109: "ADD_POWER", 110: "REMOVE_POWER",
    111: "GAME_EVENT_STOP", 112: "GAME_EVENT_START",
    113: "START_CLOSEST_WAYPOINT", 114: "RISE_UP", 115: "RANDOM_SOUND",
    116: "SET_CORPSE_DELAY", 117: "DISABLE_EVADE", 118: "GO_SET_GO_STATE",
    121: "SET_SIGHT_DIST", 122: "FLEE", 123: "ADD_THREAT",
    124: "LOAD_EQUIPMENT", 125: "TRIGGER_RANDOM_TIMED_EVENT",
    126: "REMOVE_ALL_GAMEOBJECTS", 131: "SPAWN_SPAWNGROUP",
    132: "DESPAWN_SPAWNGROUP", 134: "INVOKER_CAST",
    135: "PLAY_CINEMATIC", 136: "SET_MOVEMENT_SPEED", 142: "SET_HEALTH_PCT",
    201: "MOVE_TO_POS_TARGET", 203: "EXIT_VEHICLE",
    204: "SET_UNIT_MOVEMENT_FLAGS", 205: "SET_COMBAT_DISTANCE",
    206: "DISMOUNT", 207: "SET_HOVER", 208: "ADD_IMMUNITY",
    209: "REMOVE_IMMUNITY", 210: "FALL", 211: "SET_EVENT_FLAG_RESET",
    212: "STOP_MOTION", 213: "NO_ENVIRONMENT_UPDATE",
    214: "ZONE_UNDER_ATTACK", 215: "LOAD_GRID", 216: "MUSIC",
    217: "RANDOM_MUSIC", 218: "CUSTOM_CAST", 219: "CONE_SUMMON",
    220: "PLAYER_TALK", 221: "VORTEX_SUMMON", 222: "CU_ENCOUNTER_START",
    223: "DO_ACTION", 224: "ATTACK_STOP", 225: "SET_GUID",
    226: "SCRIPTED_SPAWN", 227: "SET_SCALE", 228: "SUMMON_RADIAL",
    229: "PLAY_SPELL_VISUAL", 230: "FOLLOW_GROUP",
    231: "ORIENTATION_TARGET", 232: "WAYPOINT_START",
    233: "WAYPOINT_DATA_RANDOM", 234: "MOVEMENT_STOP",
    235: "MOVEMENT_PAUSE", 236: "MOVEMENT_RESUME",
    237: "WORLD_SCRIPT", 238: "DISABLE_REWARD", 239: "SET_ANIM_TIER",
    240: "SET_GOSSIP_MENU", 241: "SUMMON_GAMEOBJECT_GROUP",
}

# SAI target_type enum names (SmartTarget)
_SAI_TARGET_NAMES = {
    0: "NONE", 1: "SELF", 2: "VICTIM",
    3: "HOSTILE_SECOND_AGGRO", 4: "HOSTILE_LAST_AGGRO",
    5: "HOSTILE_RANDOM", 6: "HOSTILE_RANDOM_NOT_TOP",
    7: "ACTION_INVOKER", 8: "POSITION",
    9: "CREATURE_RANGE", 10: "CREATURE_GUID", 11: "CREATURE_DISTANCE",
    12: "STORED", 13: "GAMEOBJECT_RANGE", 14: "GAMEOBJECT_GUID",
    15: "GAMEOBJECT_DISTANCE", 16: "INVOKER_PARTY",
    17: "PLAYER_RANGE", 18: "PLAYER_DISTANCE",
    19: "CLOSEST_CREATURE", 20: "CLOSEST_GAMEOBJECT",
    21: "CLOSEST_PLAYER", 22: "ACTION_INVOKER_VEHICLE",
    23: "OWNER_OR_SUMMONER", 24: "THREAT_LIST",
    25: "CLOSEST_ENEMY", 26: "CLOSEST_FRIENDLY",
    27: "LOOT_RECIPIENTS", 28: "FARTHEST",
    29: "VEHICLE_PASSENGER",
    201: "PLAYER_WITH_AURA", 202: "RANDOM_POINT",
    203: "ROLE_SELECTION", 204: "SUMMONED_CREATURES",
    205: "INSTANCE_STORAGE", 206: "FORMATION",
}

# SAI source_type enum names
_SAI_SOURCE_TYPE_NAMES = {
    0: "CREATURE", 1: "GAMEOBJECT", 2: "AREATRIGGER", 9: "TIMED_ACTIONLIST",
}

# TextEmotes enum (SharedDefines.h) — used by RECEIVE_EMOTE event_type 22
_TEXT_EMOTE_NAMES = {
    1: "AGREE", 2: "AMAZE", 3: "ANGRY", 4: "APOLOGIZE", 5: "APPLAUD",
    6: "BASHFUL", 7: "BECKON", 8: "BEG", 9: "BITE", 10: "BLEED",
    11: "BLINK", 12: "BLUSH", 13: "BONK", 14: "BORED", 15: "BOUNCE",
    16: "BRB", 17: "BOW", 18: "BURP", 19: "BYE", 20: "CACKLE",
    21: "CHEER", 22: "CHICKEN", 23: "CHUCKLE", 24: "CLAP", 25: "CONFUSED",
    26: "CONGRATULATE", 27: "COUGH", 28: "COWER", 29: "CRACK", 30: "CRINGE",
    31: "CRY", 32: "CURIOUS", 33: "CURTSEY", 34: "DANCE", 35: "DRINK",
    36: "DROOL", 37: "EAT", 38: "EYE", 39: "FART", 40: "FIDGET",
    41: "FLEX", 42: "FROWN", 43: "GASP", 44: "GAZE", 45: "GIGGLE",
    46: "GLARE", 47: "GLOAT", 48: "GREET", 49: "GRIN", 50: "GROAN",
    51: "GROVEL", 52: "GUFFAW", 53: "HAIL", 54: "HAPPY", 55: "HELLO",
    56: "HUG", 57: "HUNGRY", 58: "KISS", 59: "KNEEL", 60: "LAUGH",
    61: "LAYDOWN", 62: "MESSAGE", 63: "MOAN", 64: "MOON", 65: "MOURN",
    66: "NO", 67: "NOD", 68: "NOSEPICK", 69: "PANIC", 70: "PEER",
    71: "PLEAD", 72: "POINT", 73: "POKE", 74: "PRAY", 75: "ROAR",
    76: "ROFL", 77: "RUDE", 78: "SALUTE", 79: "SCRATCH", 80: "SEXY",
    81: "SHAKE", 82: "SHOUT", 83: "SHRUG", 84: "SHY", 85: "SIGH",
    86: "SIT", 87: "SLEEP", 88: "SNARL", 89: "SPIT", 90: "STARE",
    91: "SURPRISED", 92: "SURRENDER", 93: "TALK", 94: "TALKEX", 95: "TALKQ",
    96: "TAP", 97: "THANK", 98: "THREATEN", 99: "TIRED", 100: "VICTORY",
    101: "WAVE", 102: "WELCOME", 103: "WHINE", 104: "WHISTLE", 105: "WORK",
    106: "YAWN", 107: "BOGGLE", 108: "CALM", 109: "COLD", 110: "COMFORT",
    111: "CUDDLE", 112: "DUCK", 113: "INSULT", 114: "INTRODUCE", 115: "JK",
    116: "LICK", 117: "LISTEN", 118: "LOST", 119: "MOCK", 120: "PONDER",
    121: "POUNCE", 122: "PRAISE", 123: "PURR", 124: "PUZZLE", 125: "RAISE",
    126: "READY", 127: "SHIMMY", 128: "SHIVER", 129: "SHOO", 130: "SLAP",
    131: "SMIRK", 132: "SNIFF", 133: "SNUB", 134: "SOOTHE", 135: "STINK",
    136: "TAUNT", 137: "TEASE", 138: "THIRSTY", 139: "VETO", 140: "SNICKER",
    141: "STAND", 142: "TICKLE", 143: "VIOLIN", 163: "SMILE", 183: "RASP",
    203: "PITY", 204: "GROWL",
}

# Emote animation enum (SharedDefines.h) — used by PLAY_EMOTE/SET_EMOTE_STATE action_type 5,17
_ANIM_EMOTE_NAMES = {
    0: "NONE", 1: "TALK", 2: "BOW", 3: "WAVE", 4: "CHEER",
    5: "EXCLAMATION", 6: "QUESTION", 7: "EAT", 10: "DANCE_STATE",
    11: "LAUGH", 12: "SLEEP_STATE", 13: "SIT_STATE", 14: "RUDE",
    15: "ROAR", 16: "KNEEL", 17: "KISS", 18: "CRY", 19: "CHICKEN",
    20: "BEG", 21: "APPLAUD", 22: "SHOUT", 23: "FLEX", 24: "SHY",
    25: "POINT", 26: "STAND_STATE", 27: "READY_UNARMED_STATE", 28: "WORK_SHEATHED_STATE",
    29: "POINT_STATE", 30: "NONE_STATE", 33: "WOUND", 34: "WOUND_CRITICAL",
    35: "ATTACK_UNARMED", 36: "ATTACK1H", 37: "ATTACK2HTIGHT", 38: "ATTACK2H_LOOSE",
    39: "PARRY_UNARMED", 43: "PARRY_SHIELD", 44: "READY_UNARMED_ONESHOT", 45: "READY1H",
    48: "READY_BOW", 50: "SPELL_PRECAST", 51: "SPELL_CAST", 53: "BATTLE_ROAR",
    54: "SPECIALATTACK1H", 60: "KICK", 61: "ATTACK_THROWN", 64: "STUN_STATE",
    65: "DEAD_STATE", 66: "SALUTE", 68: "KNEEL_STATE", 69: "USE_STANDING_STATE",
    70: "WAVE_NO_SHEATHE", 71: "CHEER_NO_SHEATHE", 92: "EAT_NO_SHEATHE",
    93: "STUN_NO_SHEATHE_STATE", 94: "DANCE", 113: "SALUTE_NO_SHEATH",
    133: "USE_STANDING_NO_SHEATHE_STATE", 153: "LAUGH_NO_SHEATHE",
    173: "WORK_STATE", 193: "SPELL_PRECAST_STATE", 213: "READY_RIFLE",
    214: "READY_RIFLE_STATE", 233: "WORK_MINING_STATE", 234: "WORK_CHOPWOOD_STATE",
    253: "APPLAUD_STATE", 254: "LIFTOFF", 273: "YES", 274: "NO",
    275: "TRAIN", 293: "LAND", 313: "AT_EASE_STATE", 333: "READY1H_STATE",
    353: "SPELL_KNEEL_START_STATE", 373: "SUBMERGED_STATE", 374: "SUBMERGE",
    375: "READY2H_STATE", 376: "READY_BOW_STATE", 377: "MOUNT_SPECIAL",
    378: "TALK_STATE", 379: "FISHING_STATE", 380: "FISHING", 381: "LOOT",
    382: "WHIRLWIND_STATE", 383: "DROWNED_STATE", 384: "HOLD_BOW_STATE",
    385: "HOLD_RIFLE_STATE", 386: "HOLD_THROWN_STATE", 387: "DROWN",
    388: "STOMP", 389: "ATTACK_OFF", 390: "ATTACK_OFF_PIERCE",
    391: "ROAR_STATE", 392: "LAUGH_STATE", 393: "CREATURE_SPECIAL",
    394: "JUMPLANDRUN", 395: "JUMPEND", 396: "TALK_NO_SHEATHE",
    397: "POINT_NO_SHEATHE", 398: "CANNIBALIZE_STATE", 399: "JUMPSTART",
    400: "DANCESPECIAL_STATE", 401: "DANCESPECIAL", 402: "CUSTOM_SPELL_01",
    403: "CUSTOM_SPELL_02", 404: "CUSTOM_SPELL_03", 405: "CUSTOM_SPELL_04",
}

# AchievementCriteriaData type enum names (AchievementCriteriaDataType)
_AC_TYPE_NAMES = {
    0: "TYPE_NONE",
    1: "TYPE_T_CREATURE",
    2: "TYPE_T_PLAYER_CLASS_RACE",
    3: "TYPE_T_PLAYER_LESS_HEALTH",
    4: "TYPE_T_PLAYER_DEAD",
    5: "TYPE_S_AURA",
    6: "TYPE_S_AREA",
    7: "TYPE_T_AURA",
    8: "TYPE_VALUE",
    9: "TYPE_T_LEVEL",
    10: "TYPE_T_GENDER",
    11: "TYPE_SCRIPT",
    12: "TYPE_MAP_DIFFICULTY",
    13: "TYPE_MAP_PLAYER_COUNT",
    14: "TYPE_T_TEAM",
    15: "TYPE_S_DRUNK",
    16: "TYPE_HOLIDAY",
    17: "TYPE_BG_LOSS_TEAM_SCORE",
    18: "TYPE_INSTANCE_SCRIPT",
    19: "TYPE_S_EQUIPED_ITEM",
    20: "TYPE_MAP_ID",
    21: "TYPE_S_PLAYER_CLASS_RACE",
    22: "TYPE_NTH_BIRTHDAY",
    23: "TYPE_S_KNOWN_TITLE",
    24: "TYPE_BG_WIN_TEAM_SCORE",
    25: "TYPE_S_ITEM_QUALITY",
}

# Race enum for value2 resolution in TYPE_T_PLAYER_CLASS_RACE, TYPE_S_PLAYER_CLASS_RACE
_AC_RACE_NAMES = {
    1: "Human", 2: "Orc", 3: "Dwarf", 4: "NightElf", 5: "Undead", 6: "Tauren",
    7: "Gnome", 8: "Troll", 10: "BloodElf", 11: "Draenei",
}

# Comparison type for TYPE_VALUE (value2)
_AC_COMP_TYPES = {0: ">=", 1: "<=", 2: "==", 3: "!=", 4: "bitand"}

# Drunk state enum (for TYPE_S_DRUNK)
_AC_DRUNK_STATES = {0: "normal", 1: "slightly_tipsy", 2: "very_drunk", 3: "drunk"}


def _resolve_achievement_criteria_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve achievement_criteria_data polymorphic fields.

    Translates type to enum name (e.g., TYPE_T_CREATURE).
    Resolves value1 based on type (creature/spell/area/map references).
    Resolves value2 where applicable (race, effect_index, comp_type).
    """
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    resolved = {}
    for row in rows:
        criteria_id = row.get("criteria_id") or _get_row_pk(row)
        type_val = row.get("type", 0) or 0
        value1 = row.get("value1", 0) or 0
        value2 = row.get("value2", 0) or 0

        entry_resolved = {
            "type_name": _AC_TYPE_NAMES.get(type_val, f"UNKNOWN({type_val})"),
        }

        # Resolve value1 based on type
        if value1:
            if type_val == 1 and "sql" in allowed:
                cn = _resolve_sql_ref(server, "creature_template", value1, "entry")
                entry_resolved["value1"] = {"meaning": "creature_entry", "raw": value1, "resolved_to": cn}

            elif type_val in (5, 7) and "dbc" in allowed:
                sn = _resolve_dbc_ref(server, "Spell", value1)
                entry_resolved["value1"] = {"meaning": "spell_id", "raw": value1, "resolved_to": sn}
                if value2:
                    entry_resolved["value2"] = {"meaning": "effect_index", "raw": value2}

            elif type_val == 6 and "dbc" in allowed:
                an = _resolve_dbc_ref(server, "AreaTable", value1)
                entry_resolved["value1"] = {"meaning": "area_id", "raw": value1, "resolved_to": an}

            elif type_val == 20 and "dbc" in allowed:
                mn = _resolve_dbc_ref(server, "Map", value1)
                entry_resolved["value1"] = {"meaning": "map_id", "raw": value1, "resolved_to": mn}

            elif type_val == 16 and "dbc" in allowed:
                hn = _resolve_dbc_ref(server, "Holiday", value1)
                entry_resolved["value1"] = {"meaning": "holiday_id", "raw": value1, "resolved_to": hn}

            else:
                entry_resolved["value1"] = {"raw": value1}

        # Resolve value2 for specific types
        if value2 and type_val in (2, 21):
            race_name = _AC_RACE_NAMES.get(value2)
            entry_resolved["value2"] = {
                "meaning": "race_id",
                "raw": value2,
                "name": race_name or f"Race({value2})",
            }

        if type_val == 8 and value2:
            comp = _AC_COMP_TYPES.get(value2)
            entry_resolved["value2"] = {
                "meaning": "comparison_type",
                "raw": value2,
                "name": comp or f"COMP({value2})",
            }

        if type_val == 15 and value2:
            drunk = _AC_DRUNK_STATES.get(value2)
            entry_resolved["value2"] = {
                "meaning": "drunk_state",
                "raw": value2,
                "name": drunk or f"DRUNK({value2})",
            }

        if type_val == 10 and value2:
            entry_resolved["value2"] = {"meaning": "gender", "raw": value2, "name": ["male", "female", "neutral"][value2 - 1] if 1 <= value2 <= 3 else f"Gender({value2})"}

        if type_val == 14 and value2:
            entry_resolved["value2"] = {"meaning": "team_id", "raw": value2, "name": {"469": "Alliance", "67": "Horde"}.get(str(value2), f"Team({value2})")}

        if type_val == 12 and value2:
            entry_resolved["value2"] = {"meaning": "difficulty", "raw": value2}

        if entry_resolved.get("value1") or entry_resolved.get("value2") or criteria_id:
            resolved[str(criteria_id)] = entry_resolved

    return resolved


def _resolve_smart_script_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve smart_scripts triple-polymorphic fields.

    Translates event_type, action_type, target_type to enum names.
    Resolves event_param1-6 based on event_type (spell/quest/creature refs).
    Resolves action_param1-6 based on action_type (spell/creature/GO/quest refs).
    Resolves target_param1-4 based on target_type (creature/GO entry refs).
    Resolves entryorguid based on source_type.
    """
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    resolved = {}
    for row in rows:
        entryorguid = row.get("entryorguid", 0) or 0
        source_type = row.get("source_type", 0) or 0
        event_type = row.get("event_type", 0) or 0
        action_type = row.get("action_type", 0) or 0
        target_type = row.get("target_type", 0) or 0

        entry_resolved = {}

        # --- Entry/guid resolution based on source_type ---
        if entryorguid and "sql" in allowed:
            entry_label = _resolve_sai_entry(server, source_type, entryorguid)
            if entry_label:
                entry_resolved["entryorguid"] = {
                    "raw": entryorguid,
                    "source_type_name": _SAI_SOURCE_TYPE_NAMES.get(source_type, f"UNKNOWN({source_type})"),
                    "resolved_to": entry_label,
                }

        # --- Enum name translation for all three axes ---
        event_name = _SAI_EVENT_NAMES.get(event_type)
        action_name = _SAI_ACTION_NAMES.get(action_type)
        target_name = _SAI_TARGET_NAMES.get(target_type)

        if event_name:
            entry_resolved["event_type"] = {"raw": event_type, "name": event_name}
        if action_name:
            entry_resolved["action_type"] = {"raw": action_type, "name": action_name}
        if target_name:
            entry_resolved["target_type"] = {"raw": target_type, "name": target_name}

        # --- Event param resolution (by event_type) ---
        if "sql" in allowed or "dbc" in allowed:
            ep1 = row.get("event_param1", 0) or 0
            ep2 = row.get("event_param2", 0) or 0
            ep3 = row.get("event_param3", 0) or 0

            # Spell events: param1=SpellID
            if event_type in (8, 23, 24, 31) and ep1:
                spell_name = _resolve_dbc_ref(server, "Spell", ep1)
                entry_resolved["event_param1"] = {"meaning": "SpellId", "raw": ep1, "resolved_to": spell_name}

            # Quest events: param1=QuestID
            if event_type in (19, 20) and ep1:
                quest_name = _resolve_sql_ref(server, "quest_template", ep1, "ID")
                entry_resolved["event_param1"] = {"meaning": "QuestId", "raw": ep1, "resolved_to": quest_name}

            # Respawn event: param2=MapId (type=1), param3=ZoneId (type=2)
            if event_type == 11:
                resp_parts = {}
                if ep2 and ep1 == 1:
                    map_name = _resolve_dbc_ref(server, "Map", ep2)
                    resp_parts["map_id"] = {"raw": ep2, "resolved_to": map_name}
                if ep3 and ep1 == 2:
                    area_name = _resolve_dbc_ref(server, "AreaTable", ep3)
                    resp_parts["zone_id"] = {"raw": ep3, "resolved_to": area_name}
                if resp_parts:
                    entry_resolved["event_params_respawn"] = resp_parts

            # Kill event: param1=CreatureId (0=all), param2-4=Cooldown
            if event_type == 5 and ep1:
                cn = _resolve_sql_ref(server, "creature_template", ep1, "entry")
                entry_resolved["event_param1"] = {"meaning": "CreatureId (0=all)", "raw": ep1, "resolved_to": cn}

            # Summoned/summon-despawned unit: param1=CreatureId
            if event_type in (17, 35, 82) and ep1:
                crit_name = _resolve_sql_ref(server, "creature_template", ep1, "entry")
                entry_resolved["event_param1"] = {"meaning": "CreatureId", "raw": ep1, "resolved_to": crit_name}

            # Gossip select: param1=MenuID, param2=OptionID
            if event_type == 62 and ep1:
                gossip_parts = {}
                gossip_parts["menu_id"] = {"raw": ep1}
                try:
                    gname = _resolve_sql_ref(server, "gossip_menu", ep1, "entry")
                    gossip_parts["menu_id"]["resolved_to"] = gname
                except Exception:
                    pass
                if ep2:
                    gossip_parts["option_id"] = {"raw": ep2}
                entry_resolved["event_params_gossip"] = gossip_parts

            # RECEIVE_EMOTE: param1=TextEmotes enum ID (chat-text emotes, NOT animation)
            if event_type == 22 and ep1:
                text_emote = _TEXT_EMOTE_NAMES.get(ep1, f"unknown_text_emote({ep1})")
                entry_resolved["event_param1"] = {"meaning": "TextEmotes", "raw": ep1, "resolved_to": text_emote}

            # Game event: param1=eventEntry
            if event_type in (68, 69) and ep1:
                try:
                    ge = _resolve_sql_ref(server, "game_event", ep1, "eventEntry")
                    entry_resolved["event_param1"] = {"meaning": "game_event.eventEntry", "raw": ep1, "resolved_to": ge}
                except Exception:
                    entry_resolved["event_param1"] = {"meaning": "game_event.eventEntry", "raw": ep1}

            # Distance creature/GO: param2=entry
            if event_type == 75 and ep2:
                cn = _resolve_sql_ref(server, "creature_template", ep2, "entry")
                entry_resolved["event_param2"] = {"meaning": "creature_template.entry", "raw": ep2, "resolved_to": cn}
            if event_type == 76 and ep2:
                gn = _resolve_sql_ref(server, "gameobject_template", ep2, "entry")
                entry_resolved["event_param2"] = {"meaning": "gameobject_template.entry", "raw": ep2, "resolved_to": gn}

            # Victim casting: param3=SpellId
            if event_type == 13 and (ep3 or 0):
                s = ep3 or 0
                if s:
                    sn = _resolve_dbc_ref(server, "Spell", s)
                    entry_resolved["event_param3"] = {"meaning": "SpellId", "raw": s, "resolved_to": sn}

            # Friendly missing buff: param1=SpellId
            if event_type == 16 and ep1:
                sn = _resolve_dbc_ref(server, "Spell", ep1)
                entry_resolved["event_param1"] = {"meaning": "SpellId", "raw": ep1, "resolved_to": sn}

        # --- Action param resolution (by action_type) ---
        if "sql" in allowed or "dbc" in allowed:
            ap1 = row.get("action_param1", 0) or 0
            ap2 = row.get("action_param2", 0) or 0
            ap3 = row.get("action_param3", 0) or 0
            ap4 = row.get("action_param4", 0) or 0

            # CAST: param1=SpellId
            if action_type == 11 and ap1:
                spell_name = _resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": spell_name}

            # SUMMON_CREATURE: param1=creature_template.entry
            if action_type == 12 and ap1:
                cn = _resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # QUEST actions: param1=quest_id
            if action_type in (6, 7, 15, 26) and ap1:
                qn = _resolve_sql_ref(server, "quest_template", ap1, "ID")
                entry_resolved["action_param1"] = {"meaning": "QuestId", "raw": ap1, "resolved_to": qn}

            # CALL_KILLEDMONSTER: param1=creature_template.entry
            if action_type == 33 and ap1:
                cn = _resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "RequiredNpcOrGo (creature)", "raw": ap1, "resolved_to": cn}

            # MORPH/MOUNT: param1=creature_template.entry
            if action_type in (3, 43) and ap1:
                cn = _resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # UPDATE_TEMPLATE: param1=creature_template.entry
            if action_type == 36 and ap1:
                cn = _resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # FOLLOW: param3=creature_template.entry
            if action_type == 29 and ap3:
                cn = _resolve_sql_ref(server, "creature_template", ap3, "entry")
                entry_resolved["action_param3"] = {"meaning": "End_creature_entry", "raw": ap3, "resolved_to": cn}

            # SUMMON_GO: param1=gameobject_template.entry
            if action_type == 50 and ap1:
                gn = _resolve_sql_ref(server, "gameobject_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "gameobject_entry", "raw": ap1, "resolved_to": gn}

            # TALK/SIMPLE_TALK: param1=creature_text.GroupID
            if action_type in (1, 84) and ap1:
                try:
                    cn = _resolve_sql_ref(server, "creature_text", ap1, "GroupID")
                    entry_resolved["action_param1"] = {"meaning": "creature_text.GroupID", "raw": ap1, "resolved_to": cn}
                except Exception:
                    pass

            # SOUND/MUSIC: param1=SoundEntriesDLC_ID
            if action_type in (4, 216) and ap1:
                sn = _resolve_dbc_ref(server, "SoundEntries", ap1)
                entry_resolved["action_param1"] = {"meaning": "SoundId", "raw": ap1, "resolved_to": sn}

            # PLAY_EMOTE/SET_EMOTE_STATE: param1=Emote animation enum ID (SharedDefines.h)
            if action_type in (5, 17) and ap1:
                anim_emote = _ANIM_EMOTE_NAMES.get(ap1, f"unknown_anim_emote({ap1})")
                entry_resolved["action_param1"] = {"meaning": "Emote", "raw": ap1, "resolved_to": anim_emote}

            # ACTIVATE_TAXI: param1=TaxiNodes
            if action_type == 52 and ap1:
                tn = _resolve_dbc_ref(server, "TaxiNodes", ap1)
                entry_resolved["action_param1"] = {"meaning": "TaxiNodeID", "raw": ap1, "resolved_to": tn}

            # ESCORT_START: param2=waypoints.entry, param4=quest_template.id
            if action_type == 53:
                escort_parts = {}
                if ap2:
                    try:
                        wn = _resolve_sql_ref(server, "waypoints", ap2, "entry")
                        escort_parts["waypoints_entry"] = {"raw": ap2, "resolved_to": wn}
                    except Exception:
                        escort_parts["waypoints_entry"] = {"raw": ap2}
                if ap4:
                    qn = _resolve_sql_ref(server, "quest_template", ap4, "ID")
                    escort_parts["quest_id"] = {"raw": ap4, "resolved_to": qn}
                if escort_parts:
                    entry_resolved["action_params_escorts"] = escort_parts

            # ADD_ITEM/REMOVE_ITEM: param1=item_template.entry
            if action_type in (56, 57) and ap1:
                iname = _resolve_sql_ref(server, "item_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "item_entry", "raw": ap1, "resolved_to": iname}

            # SELF_CAST/CROSS_CAST/INVOKER_CAST: param1=SpellId
            if action_type in (85, 86, 134) and ap1:
                sn = _resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": sn}

            # ADD_AURA/REMOVEAURASFROMSPELL: param1=SpellId
            if action_type in (75, 28) and ap1:
                sn = _resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": sn}

            # INTERRUPT_SPELL: param2=SpellId
            if action_type == 92 and ap2:
                sn = _resolve_dbc_ref(server, "Spell", ap2)
                entry_resolved["action_param2"] = {"meaning": "SpellId", "raw": ap2, "resolved_to": sn}

            # SEND_GOSSIP_MENU: param1=gossip_menu.entry, param2=text_id
            if action_type == 98 and ap1:
                gossip_parts = {}
                gn = _resolve_sql_ref(server, "gossip_menu", ap1, "entry")
                gossip_parts["menu_id"] = {"raw": ap1, "resolved_to": gn}
                if ap2:
                    try:
                        tn = _resolve_sql_ref(server, "npc_text", ap2, "ID")
                        gossip_parts["text_id"] = {"raw": ap2, "resolved_to": tn}
                    except Exception:
                        try:
                            tn = _resolve_sql_ref(server, "creature_text", ap2, "GroupID")
                            gossip_parts["text_id"] = {"raw": ap2, "resolved_to": tn}
                        except Exception:
                            gossip_parts["text_id"] = {"raw": ap2}
                entry_resolved["action_params_gossip"] = gossip_parts

            # GAME_EVENT_START/STOP: param1=eventEntry
            if action_type in (111, 112) and ap1:
                try:
                    ge = _resolve_sql_ref(server, "game_event", ap1, "eventEntry")
                    entry_resolved["action_param1"] = {"meaning": "game_event.eventEntry", "raw": ap1, "resolved_to": ge}
                except Exception:
                    entry_resolved["action_param1"] = {"meaning": "game_event.eventEntry", "raw": ap1}

            # SET_GOSSIP_MENU: param1=gossipMenuId
            if action_type == 240 and ap1:
                gn = _resolve_sql_ref(server, "gossip_menu", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "gossip_menu.entry", "raw": ap1, "resolved_to": gn}

            # TELEPORT: param1=MapId, target_x/y/z/o destination coordinates
            if action_type == 62:
                teleport_info = {}
                if ap1:
                    map_name = _resolve_dbc_ref(server, "Map", ap1)
                    teleport_info["map_id"] = {"raw": ap1, "resolved_to": map_name}
                entry_resolved["teleport_info"] = teleport_info

        # --- Target param resolution (by target_type) ---
        if "sql" in allowed:
            tp1 = row.get("target_param1", 0) or 0

            # Creature by entry (range/distance/closest)
            if target_type in (9, 11, 19) and tp1:
                cn = _resolve_sql_ref(server, "creature_template", tp1, "entry")
                entry_resolved["target_param1"] = {"meaning": "creature_entry", "raw": tp1, "resolved_to": cn}

            # Creature by guid
            if target_type == 10 and tp1:
                abs_guid = abs(tp1)
                cn = _resolve_sql_ref(server, "creature_template", (row.get("target_param2", 0) or 0), "entry")
                entry_resolved["target_param1"] = {"meaning": "creature_guid", "raw": tp1, "resolved_to": f"guid:{abs_guid}" + (f", template: {cn}" if cn else "")}

            # GO by entry (range/distance/closest)
            if target_type in (13, 15, 20) and tp1:
                gn = _resolve_sql_ref(server, "gameobject_template", tp1, "entry")
                entry_resolved["target_param1"] = {"meaning": "gameobject_entry", "raw": tp1, "resolved_to": gn}

            # GO by guid
            if target_type == 14 and tp1:
                abs_guid = abs(tp1)
                entry_resolved["target_param1"] = {"meaning": "gameobject_guid", "raw": tp1, "resolved_to": f"guid:{abs_guid}"}

            # Player with aura: param1=spellID
            if target_type == 201 and tp1:
                sn = _resolve_dbc_ref(server, "Spell", tp1)
                entry_resolved["target_param1"] = {"meaning": "SpellId (aura)", "raw": tp1, "resolved_to": sn}

        # --- Position coordinates annotation ---
        tx = row.get("target_x")
        ty = row.get("target_y")
        tz = row.get("target_z")
        if target_type == 8 and any(v is not None and v != 0 for v in [tx, ty, tz]):
            entry_resolved["position"] = {
                "type_name": "POSITION",
                "x": tx,
                "y": ty,
                "z": tz,
                "orientation": row.get("target_o"),
            }

        # TELEPORT destination coordinates (action_type 62 uses target_x/y/z/o as dest)
        if action_type == 62 and any(v is not None and v != 0 for v in [tx, ty, tz]):
            entry_resolved["teleport_destination"] = {
                "map_id": ap1,
                "x": tx,
                "y": ty,
                "z": tz,
                "orientation": row.get("target_o"),
            }

        # Skip empty entries — only include if we resolved something meaningful
        if entry_resolved:
            pk = str(abs(entryorguid)) + "_" + str(row.get("source_type", 0)) + "_" + str(row.get("id", 0))
            resolved[pk] = entry_resolved

    return resolved


def _resolve_sai_entry(server, source_type: int, entryorguid: int) -> Optional[str]:
    """Resolve entryorguid based on source_type and sign."""
    if entryorguid == 0:
        return None

    pos = abs(entryorguid)
    if source_type == 0:  # Creature
        if entryorguid > 0:
            name = _resolve_sql_ref(server, "creature_template", pos, "entry")
            return f"creature (entry={pos}) -> {name}" if name else f"creature (entry={pos})"
        else:
            return f"creature (guid={entryorguid})"
    elif source_type == 1:  # Gameobject
        if entryorguid > 0:
            name = _resolve_sql_ref(server, "gameobject_template", pos, "entry")
            return f"gameobject (entry={pos}) -> {name}" if name else f"gameobject (entry={pos})"
        else:
            return f"gameobject (guid={entryorguid})"
    elif source_type == 2:  # Areatrigger
        try:
            name = _resolve_sql_ref(server, "areatrigger_scripts", pos, "entry")
            return f"areatrigger (entry={pos}) -> {name}" if name else f"areatrigger (entry={pos})"
        except Exception:
            return f"areatrigger (entry={pos})"
    elif source_type == 9:  # TimedActionList
        return f"timed_actionlist (entry={entryorguid})"

    return None


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
        rows, _ = server.database._query_database(
            f"SELECT * FROM {table} WHERE {id_col} = %s LIMIT 1",
            params=(ref_id,),
        )

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
        items, _ = server.database._query_database(
            f"SELECT Item, Chance, MinCount, MaxCount FROM {table} WHERE {id_col} = %s",
            params=(loot_id,),
        )

        if not items:
            return {"resolved_to": f"{table} [{loot_id}]", "warning": "Empty loot template"}

        total_items = len(items)
        display_items = []

        for item_row in items[:resolve_max]:
            item_id = item_row.get("Item", 0)
            if not item_id:
                continue

            # Resolve item name
            item_rows, _ = server.database._query_database(
                "SELECT entry, name FROM item_template WHERE entry = %s LIMIT 1",
                params=(item_id,),
            )
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
