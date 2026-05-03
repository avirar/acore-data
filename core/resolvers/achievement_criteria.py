"""Resolve achievement_criteria_data polymorphic fields.

Translates type to enum name (e.g., TYPE_T_CREATURE).
Resolves value1 based on type (creature/spell/area/map references).
Resolves value2 where applicable (race, effect_index, comp_type).
Pre-warms per-request cache with batch SQL lookups before row iteration.
"""
from collections import defaultdict
from typing import Any, Dict, List

from ..enums import _AC_TYPE_NAMES, _AC_RACE_NAMES, _AC_COMP_TYPES, _AC_DRUNK_STATES
from .ref_utils import resolve_dbc_ref, resolve_sql_ref


def _get_row_pk(row: Dict) -> str:
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def _collect_ac_ids(rows):
    """Collect all SQL IDs across rows grouped by (table, id_col)."""
    ids = defaultdict(set)
    for row in rows:
        type_val = row.get("type", 0) or 0
        value1 = row.get("value1", 0) or 0

        if type_val == 1 and value1:
            ids[("creature_template", "entry")].add(value1)

    return {k: v for k, v in ids.items() if v}


def _prewarm_ac_cache(server, collected_ids):
    """Batch-resolve collected achievement criteria IDs into per-request cache."""
    from .ref_utils import batch_resolve_sql as brs, _active_cache
    for (table, id_col), id_set in collected_ids.items():
        if not id_set:
            continue
        batch = brs(server, table, list(id_set), id_col)
        if _active_cache is not None:
            for rid, name in batch.items():
                _active_cache[f"sql:{table}:{rid}:{id_col}"] = name


def resolve_achievement_criteria(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve achievement_criteria_data polymorphic fields."""
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    # Pre-warm cache with batch SQL lookups to avoid N+1 pattern
    collected = _collect_ac_ids(rows)
    if collected:
        _prewarm_ac_cache(server, collected)

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
                cn = resolve_sql_ref(server, "creature_template", value1, "entry")
                entry_resolved["value1"] = {"meaning": "creature_entry", "raw": value1, "resolved_to": cn}

            elif type_val in (5, 7) and "dbc" in allowed:
                sn = resolve_dbc_ref(server, "Spell", value1)
                entry_resolved["value1"] = {"meaning": "spell_id", "raw": value1, "resolved_to": sn}
                if value2:
                    entry_resolved["value2"] = {"meaning": "effect_index", "raw": value2}

            elif type_val == 6 and "dbc" in allowed:
                an = resolve_dbc_ref(server, "AreaTable", value1)
                entry_resolved["value1"] = {"meaning": "area_id", "raw": value1, "resolved_to": an}

            elif type_val == 20 and "dbc" in allowed:
                mn = resolve_dbc_ref(server, "Map", value1)
                entry_resolved["value1"] = {"meaning": "map_id", "raw": value1, "resolved_to": mn}

            elif type_val == 16 and "dbc" in allowed:
                hn = resolve_dbc_ref(server, "Holiday", value1)
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
