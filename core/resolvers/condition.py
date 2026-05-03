"""Resolve conditions table with polymorphic field interpretation.

Translates SourceTypeOrReferenceId and ConditionTypeOrReference to enum names,
resolves SourceEntry based on source type (spell/quest/item/creature),
resolves ConditionValue1 based on condition type (aura spell, quest, item, etc.).
Pre-warms per-request cache with batch SQL lookups before row iteration.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..enums import (
    _SOURCE_TYPE_NAMES, _CONDITION_TYPE_NAMES, _TYPEID_NAMES, _TYPEMASK_NAMES,
    _CLASS_NAMES, _RACE_NAMES, _GENDER_NAMES,
)
from .ref_utils import resolve_dbc_ref, resolve_sql_ref

# Comparison type enum lookup (from ConditionMgr.h)
_COMP_TYPES = {0: ">=", 1: "<=", 2: "==", 3: "!="}

# ErrorType enum for spell cast failure feedback (ConditionMgr.h / SpellMgr.cpp)
_ERROR_TYPE_NAMES = {
    0: "SPELL_CAST_OK",
    1: "SPELL_FAILED_UNKNOWN",
    2: "SPELL_FAILED_NO_CHARGES",
    3: "SPELL_FAILED_NOT_MOUNTED",
    4: "SPELL_FAILED_NOT_IN_Arena",
    5: "SPELL_FAILED_EQUIPPED_ITEM",
    6: "SPELL_FAILED_EQUIPPED_ITEM_CLASS",
    7: "SPELL_FAILED_DOESNTOWN_REAGENT",
    8: "SPELL_FAILED_NOT_DEAD",
    9: "SPELL_FAILED_NOT_SLEEPING",
    10: "SPELL_FAILED_POSSESSSED",
    11: "SPELL_FAILED_NOT_ALIVE",
    12: "SPELL_FAILED_HOSTILE",
    13: "SPELL_FAILED_FRIENDLY",
    14: "SPELL_FAILED_NO_POWER",
    15: "SPELL_FAILED_TARGETAURAFILTER",
    16: "SPELL_FAILED_IMMUNE",
    17: "SPELL_FAILED_RESISTED",
    18: "SPELL_FAILED_LEVEL",
    19: "SPELL_FAILED_MIN_REPUTATION",
    20: "SPELL_FAILED_NO_TARGETS",
    21: "SPELL_FAILED_DISPEL_TYPE",
    22: "SPELL_FAILED_TOO_FAR_BEHIND",
    23: "SPELL_FAILED_FACING_TARGET",
    24: "SPELL_FAILED_DISTANCE",
    25: "SPELL_FAILED_NOT_STANDING",
    26: "SPELL_FAILED_MOD_CAST_OUT_OF_COMBAT",
    27: "SPELL_FAILED_HEALTH",
}


def _get_row_pk(row: Dict) -> str:
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def _collect_condition_ids(rows):
    """Collect all SQL IDs across rows grouped by (table, id_col)."""
    ids = defaultdict(set)
    for row in rows:
        source_type = row.get("SourceTypeOrReferenceId", 0) or 0
        condition_type = row.get("ConditionTypeOrReference", 0) or 0
        source_entry = row.get("SourceEntry", 0) or 0
        source_group = row.get("SourceGroup", 0) or 0
        value1 = row.get("ConditionValue1", 0) or 0
        value2 = row.get("ConditionValue2", 0) or 0

        # Source entry SQL refs (DBC fallbacks also collect quest_template)
        if source_type in (13, 17, 24) and source_entry:
            ids[("quest_template", "ID")].add(source_entry)
        if source_type in (18, 21):
            if source_entry:
                ids[("quest_template", "ID")].add(source_entry)
            if source_group:
                ids[("creature_template", "entry")].add(source_group)
        if source_type == 19 and source_entry:
            ids[("quest_template", "ID")].add(source_entry)
        if source_type in (14, 15) and source_entry:
            ids[("gossip_menu_option", "menu_id")].add(source_entry)
        if source_type == 20 and source_entry:
            ids[("creature_template", "entry")].add(source_entry)
        if source_type in (16, 29) and source_entry:
            ids[("creature_template", "entry")].add(source_entry)

        # Condition value SQL refs
        if condition_type in (1, 25) and value1:
            ids[("quest_template", "ID")].add(value1)
        if condition_type in (8, 9, 14, 28, 43) and value1:
            ids[("quest_template", "ID")].add(value1)
        if condition_type in (47, 48, 101) and value1:
            ids[("quest_template", "ID")].add(value1)
        if condition_type in (2, 3) and value1:
            ids[("item_template", "entry")].add(value1)
        if condition_type == 29 and value1:
            ids[("creature_template", "entry")].add(value1)
        if condition_type == 30 and value1:
            ids[("gameobject_template", "entry")].add(value1)
        if condition_type == 31 and value2:
            type_id = int(value1)
            if type_id in (3, 4):  # UNIT or PLAYER
                ids[("creature_template", "entry")].add(value2)
            elif type_id == 1:  # ITEM
                ids[("item_template", "entry")].add(value2)
            elif type_id in (5, 6):  # GAMEOBJECT or DYNAMICOBJECT
                ids[("gameobject_template", "entry")].add(value2)

    return dict(ids)


def _prewarm_condition_cache(server, collected_ids):
    """Batch-resolve collected condition IDs into per-request cache."""
    from .ref_utils import batch_resolve_sql as brs, _active_cache
    for (table, id_col), id_set in collected_ids.items():
        if not id_set:
            continue
        batch = brs(server, table, list(id_set), id_col)
        if _active_cache is not None:
            for rid, name in batch.items():
                _active_cache[f"sql:{table}:{rid}:{id_col}"] = name


def resolve_condition_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve conditions table with polymorphic field interpretation."""
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    # Pre-warm cache with batch SQL lookups to avoid N+1 pattern
    if "sql" in allowed:
        collected = _collect_condition_ids(rows)
        if collected:
            _prewarm_condition_cache(server, collected)

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

        # Also resolve types that don't need SQL but still have meaningful output (ALIVE, CLASS, RACE, GENDER)
        elif not cond_value1 and condition_type in (36, 15, 16, 20):
            resolved_values = _resolve_condition_values(server, condition_type, cond_value1, cond_value2, cond_value3)
            if resolved_values:
                entry_resolved["condition_values"] = resolved_values

        # --- NegativeCondition annotation (inverts the condition logic) ---
        neg_cond = row.get("NegativeCondition", 0) or 0
        if neg_cond:
            entry_resolved["negative_condition"] = True
            existing_type = entry_resolved.get("condition_type_name", "")
            entry_resolved["condition_type_name"] = f"NOT_{existing_type}"

        # --- ErrorType/ErrorTextId annotation (spell cast failure feedback) ---
        error_type = row.get("ErrorType", 0) or 0
        if error_type:
            entry_resolved["error_type"] = {
                "raw": error_type,
                "name": _ERROR_TYPE_NAMES.get(error_type, f"SPELL_FAILED({error_type})"),
            }
        error_text_id = row.get("ErrorTextId", 0) or 0
        if error_text_id:
            entry_resolved["error_text_lang_id"] = error_text_id

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

        if pk and (entry_resolved.get("source_entry") or entry_resolved.get("condition_values")):
            resolved[pk] = entry_resolved

    return resolved


def _resolve_condition_source(server, source_type: int, source_entry: int, source_group: int) -> Optional[Dict]:
    """Resolve SourceEntry based on SourceTypeOrReferenceId."""
    # Spell sources — resolve via Spell DBC first, fall back to SQL quest_template (some spell-like IDs are quests)
    if source_type in (13, 17, 24):
        name = resolve_dbc_ref(server, "Spell", source_entry) or resolve_sql_ref(server, "quest_template", source_entry, "ID")
        return {"type": "spell", "id": source_entry, "name": name}

    if source_type in (18, 21):
        spell_name = resolve_dbc_ref(server, "Spell", source_entry) or resolve_sql_ref(server, "quest_template", source_entry, "ID")
        creature_name = resolve_sql_ref(server, "creature_template", source_group, "entry")
        return {
            "spell": {"type": "spell", "id": source_entry, "name": spell_name},
            "trigger_by": {"type": "creature", "id": source_group, "name": creature_name},
        }

    # Quest sources
    if source_type == 19:
        name = resolve_sql_ref(server, "quest_template", source_entry, "ID")
        return {"type": "quest", "id": source_entry, "name": name}

    # Gossip/menu sources
    if source_type in (14, 15):
        name = resolve_sql_ref(server, "gossip_menu_option", source_entry, "menu_id")
        return {"type": "gossip", "id": source_entry, "name": name}

    if source_type == 20:
        creature_name = resolve_sql_ref(server, "creature_template", source_entry, "entry")
        return {"type": "creature_gossip", "id": source_entry, "name": creature_name}

    # Creature template vehicle / respawn
    if source_type in (16, 29):
        name = resolve_sql_ref(server, "creature_template", source_entry, "entry")
        return {"type": "creature", "id": source_entry, "name": name}

    return None


def _resolve_condition_values(
    server, condition_type: int, value1: int, value2: int, value3: int
) -> Optional[Dict]:
    """Resolve ConditionValue1-3 based on ConditionTypeOrReference."""
    result = {}

    # --- Spell references in conditions ---
    if condition_type == 1:  # AURA
        name = resolve_dbc_ref(server, "Spell", value1) or resolve_sql_ref(server, "quest_template", value1, "ID")
        result["spell"] = {"type": "aura_spell", "id": value1, "name": name}
        if value2:
            result["effect_index"] = int(value2)

    elif condition_type == 25:  # SPELL_LEARNED
        name = resolve_dbc_ref(server, "Spell", value1) or resolve_sql_ref(server, "quest_template", value1, "ID")
        result["spell"] = {"type": "learned_spell", "id": value1, "name": name}

    # --- Quest references in conditions ---
    elif condition_type in (8, 9, 14, 28, 43):  # QUESTREWARDED, QUESTTAKEN, QUEST_NONE, QUEST_COMPLETE, DAILY_QUEST_DONE
        quest_names = {8: "rewarded", 9: "taken", 14: "quest_none", 28: "completed", 43: "daily_done"}
        name = resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": quest_names[condition_type], "id": value1, "name": name}

    elif condition_type == 47:  # QUESTSTATE
        name = resolve_sql_ref(server, "quest_template", value1, "ID")
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
        name = resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": "objective", "id": value1, "name": name}
        if value2:
            result["objective_index"] = int(value2)
        if value3:
            result["progress_required"] = int(value3)

    elif condition_type == 101:  # QUEST_SATISFY_EXCLUSIVE
        name = resolve_sql_ref(server, "quest_template", value1, "ID")
        result["quest"] = {"type": "exclusive", "id": value1, "name": name}

    # --- Item references in conditions ---
    elif condition_type == 2:  # ITEM
        name = resolve_sql_ref(server, "item_template", value1, "entry")
        result["item"] = {"type": "has_item", "id": value1, "name": name}
        if value2:
            result["count_required"] = int(value2)

    elif condition_type == 3:  # ITEM_EQUIPPED
        name = resolve_sql_ref(server, "item_template", value1, "entry")
        result["item"] = {"type": "equipped_item", "id": value1, "name": name}

    # --- Creature references in conditions ---
    elif condition_type == 29:  # NEAR_CREATURE
        name = resolve_sql_ref(server, "creature_template", value1, "entry")
        result["creature"] = {"type": "nearby_creature", "id": value1, "name": name}
        if value2:
            result["max_distance"] = int(value2)

    elif condition_type == 30:  # NEAR_GAMEOBJECT
        name = resolve_sql_ref(server, "gameobject_template", value1, "entry")
        result["gameobject"] = {"type": "nearby_go", "id": value1, "name": name}
        if value2:
            result["max_distance"] = int(value2)

    # --- OBJECT_ENTRY_GUID (complex TypeID-based resolution) ---
    elif condition_type == 31:  # OBJECT_ENTRY_GUID
        type_id = int(value1)
        result["type_id"] = {"raw": type_id, "name": _TYPEID_NAMES.get(type_id, f"TYPE({type_id})")}
        if value2 and type_id in (3, 4):  # UNIT or PLAYER
            name = resolve_sql_ref(server, "creature_template", value2, "entry")
            result["target_entity"] = {"type": "creature", "id": value2, "name": name}
        elif value2 and type_id == 1:  # ITEM
            name = resolve_sql_ref(server, "item_template", value2, "entry")
            result["target_entity"] = {"type": "item", "id": value2, "name": name}
        elif value2 and type_id in (5, 6):  # GAMEOBJECT or DYNAMICOBJECT
            name = resolve_sql_ref(server, "gameobject_template", value2, "entry")
            result["target_entity"] = {"type": "gameobject", "id": value2, "name": name}
        elif value2:
            result["target_entity"] = {"id": value2, "type_id": type_id}

    # Type mask check (object's TypeMask must match)
    elif condition_type == 32:  # TYPE_MASK
        result["type_mask"] = {
            "raw": int(value1),
            "name": _TYPEMASK_NAMES.get(int(value1), f"MASK(0x{value1:X})"),
            "bitmask": f"0x{value1:04X}",
        }

    # --- Level comparison ---
    elif condition_type == 27:  # LEVEL
        result["level"] = int(value1)
        if value2:
            result["comparison"] = _COMP_TYPES.get(int(value2), f"RAW({value2})")

    # --- Enum-only conditions (no SQL ref needed) ---
    elif condition_type == 15:  # CLASS
        result["class_id"] = {"raw": int(value1), "name": _CLASS_NAMES.get(int(value1), f"CLASS({value1})")}
    elif condition_type == 16:  # RACE
        result["race_id"] = {"raw": int(value1), "name": _RACE_NAMES.get(int(value1), f"RACE({value1})")}
    elif condition_type == 20:  # GENDER
        result["gender"] = {"raw": int(value1), "name": _GENDER_NAMES.get(int(value1), f"GENDER({value1})")}
    elif condition_type == 24:  # CREATURE_TYPE
        result["creature_type_id"] = int(value1)
    elif condition_type in (22, 23):  # MAPID / AREAID
        dbc_name = "Map" if condition_type == 22 else "AreaTable"
        name = resolve_dbc_ref(server, dbc_name, value1)
        field = "map_id" if condition_type == 22 else "area_id"
        result[field] = {"raw": int(value1), "name": name}
    elif condition_type in (26, 19):  # PHASEMASK / SPAWNMASK
        mask_name = "phase_mask" if condition_type == 26 else "spawn_mask"
        result[mask_name] = {"raw": int(value1), "bitmask": f"0x{value1:08X}"}

    # --- HP comparisons ---
    elif condition_type == 37:  # HP_VAL
        result["hp_value"] = int(value1)
        if value2:
            result["comparison"] = _COMP_TYPES.get(int(value2), f"RAW({value2})")
    elif condition_type == 38:  # HP_PCT
        result["hp_percent"] = int(value1)
        if value2:
            result["comparison"] = _COMP_TYPES.get(int(value2), f"RAW({value2})")

    # --- Distance to target ---
    elif condition_type == 35:  # DISTANCE_TO
        result["distance"] = int(value2)
        if value1:
            result["target_slot"] = int(value1)
        if value3:
            result["comparison"] = _COMP_TYPES.get(int(value3), f"RAW({value3})")

    # --- ALIVE status check (NegativeCondition=1 means must be dead) ---
    elif condition_type == 36:
        result["status"] = "alive" if not value1 else "dead"

    return result if result else None
