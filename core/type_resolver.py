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

# Import enum dicts extracted to core/enums.py
from .enums import (
    GO_TYPE_NAMES,
    _SOURCE_TYPE_NAMES,
    _CONDITION_TYPE_NAMES,
    _SAI_EVENT_NAMES,
    _SAI_ACTION_NAMES,
    _SAI_TARGET_NAMES,
    _SAI_SOURCE_TYPE_NAMES,
    _TEXT_EMOTE_NAMES,
    _ANIM_EMOTE_NAMES,
    _AC_TYPE_NAMES,
    _AC_RACE_NAMES,
    _AC_COMP_TYPES,
    _AC_DRUNK_STATES,
)

# Import shared ref utilities from resolvers module
from .resolvers.ref_utils import resolve_dbc_ref, resolve_sql_ref, resolve_loot_ref

# Backwards-compatible aliases for remaining inline resolvers
_resolve_dbc_ref = resolve_dbc_ref
_resolve_sql_ref = resolve_sql_ref
_resolve_loot_ref = resolve_loot_ref


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

    # Check resolver registry first (for modularized resolvers that don't need registry entry)
    from .resolvers import get_resolver
    registered = get_resolver(sql_table)
    if registered:
        reg_entry = _find_registry_entry(server, sql_table)
        if reg_entry and "type_field_mappings" in reg_entry:
            return registered(server, reg_entry, rows, resolve_filter, resolve_max)
        # Some resolvers (smart_scripts, quest_template) have hardcoded logic without registry
        return registered(server, reg_entry or {}, rows, resolve_filter, resolve_max)

    reg_entry = _find_registry_entry(server, sql_table)
    if not reg_entry:
        return {}

    # Special case: conditions table uses polymorphic resolution
    if sql_table == "conditions":
        return _resolve_condition_fields(server, reg_entry, rows, resolve_filter, resolve_max)

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
