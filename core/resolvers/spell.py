"""Resolve Spell entries with enriched condition data from the conditions table.

For each spell row (from Spell DBC or SQL query), automatically includes:
- Cast conditions from conditions table where SourceTypeOrReferenceId IN (13,17,18,21,24)
  and SourceEntry = <spell_id>

Delegates condition value/source resolution to condition.py's shared functions
to maintain a single source of truth for all ~50 condition types.
"""
from typing import Any, Dict, List

from ..enums import _SOURCE_TYPE_NAMES

# Spell-related SourceTypeOrReferenceId values from conditions table
_SPELL_SOURCE_TYPES = (13, 17, 18, 21, 24)


def _get_spell_id(row: Dict) -> int:
    """Get spell ID from row (case-insensitive lookup)."""
    for key in ["ID", "Id", "id", "SpellId", "spellid"]:
        if key in row and row[key]:
            return int(row[key])
    for k, v in row.items():
        if k.lower() in ("id", "spellid") and v:
            return int(v)
    return 0


def collect_spell_condition_ids(rows: List[Dict[str, Any]]) -> list:
    """Collect all spell IDs that may have conditions."""
    spell_ids = []
    for row in rows:
        sid = _get_spell_id(row)
        if sid:
            spell_ids.append(sid)
    return spell_ids


def _fetch_spell_conditions(server, spell_ids: list) -> Dict[int, list]:
    """Fetch all conditions for given spell IDs.

    Uses inline integer values (safe from SQL injection since IDs are ints).
    This works correctly with both pymysql and CLI fallback modes.
    """
    if not spell_ids:
        return {}

    ids_str = ",".join(str(int(sid)) for sid in spell_ids)
    stypes = ",".join(str(s) for s in _SPELL_SOURCE_TYPES)

    try:
        rows, _ = server.database._query_database(
            f"SELECT SourceTypeOrReferenceId, SourceGroup, SourceEntry, SourceId, "
            f"ElseGroup, ConditionTypeOrReference, ConditionTarget, "
            f"ConditionValue1, ConditionValue2, ConditionValue3, "
            f"NegativeCondition, ErrorType, ErrorTextId, Comment "
            f"FROM conditions "
            f"WHERE SourceTypeOrReferenceId IN ({stypes}) AND SourceEntry IN ({ids_str}) "
            f"LIMIT 500",
        )
    except Exception:
        return {}

    result = {}
    for row in (rows or []):
        sid = row.get("SourceEntry", 0)
        if sid:
            result.setdefault(sid, []).append(row)
    return result


def _format_condition_row(server, cond: Dict) -> Dict:
    """Format a single condition row using shared resolution from condition.py."""
    from ..enums import _CONDITION_TYPE_NAMES
    from .condition import (
        _ERROR_TYPE_NAMES,
        _resolve_condition_source,
        _resolve_condition_values,
    )

    source_type = cond.get("SourceTypeOrReferenceId", 0) or 0
    condition_type = cond.get("ConditionTypeOrReference", 0) or 0
    value1 = cond.get("ConditionValue1", 0) or 0
    value2 = cond.get("ConditionValue2", 0) or 0
    value3 = cond.get("ConditionValue3", 0) or 0
    source_entry = cond.get("SourceEntry", 0) or 0
    source_group = cond.get("SourceGroup", 0) or 0
    neg_cond = cond.get("NegativeCondition", 0) or 0
    error_type = cond.get("ErrorType", 0) or 0
    else_group = cond.get("ElseGroup", 0) or 0

    entry = {
        "source": _SOURCE_TYPE_NAMES.get(source_type, f"UNKNOWN({source_type})"),
        "type": _CONDITION_TYPE_NAMES.get(condition_type, f"UNKNOWN({condition_type})"),
        "raw_values": {"v1": value1, "v2": value2, "v3": value3},
    }

    if else_group:
        entry["else_group"] = int(else_group)

    if neg_cond:
        entry["negative_condition"] = True
        entry["type"] = f"NOT_{entry['type']}"

    # Effect bitmask for SPELL_IMPLICIT_TARGET (source_type=13)
    if source_type == 13 and source_group:
        effects = []
        if source_group & 1:
            effects.append("effect0")
        if source_group & 2:
            effects.append("effect1")
        if source_group & 4:
            effects.append("effect2")
        entry["effects"] = f"mask[{','.join(effects)}]"

    # Delegate source resolution to shared condition functions
    if source_entry:
        resolved_source = _resolve_condition_source(
            server, source_type, source_entry, source_group
        )
        if resolved_source:
            entry["source_entry"] = resolved_source

    # Delegate value resolution to shared condition functions
    resolved_values = _resolve_condition_values(
        server, condition_type, value1, value2, value3
    )
    if resolved_values:
        entry["values"] = resolved_values

    # Error type annotation
    if error_type and error_type != 0:
        entry["error"] = _ERROR_TYPE_NAMES.get(error_type, f"SPELL_FAILED({error_type})")

    return entry


def resolve_spell_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve spell entries with enriched condition data."""
    from ..type_resolver import _resolve_generic
    base_resolved = _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)

    if not rows:
        return base_resolved

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return base_resolved

    if "sql" not in allowed:
        return base_resolved

    spell_ids = collect_spell_condition_ids(rows)
    conditions_by_spell = _fetch_spell_conditions(server, spell_ids)

    # Pre-warm cache with batch lookups for all condition value references
    if conditions_by_spell:
        from .condition import _collect_condition_ids, _prewarm_condition_cache
        all_conds = [c for conds in conditions_by_spell.values() for c in conds]
        collected = _collect_condition_ids(all_conds)
        if collected:
            _prewarm_condition_cache(server, collected)

    resolved = {}
    for row in rows:
        sid = _get_spell_id(row)
        if not sid:
            continue

        entry_resolved = base_resolved.get(sid, {})
        conds = conditions_by_spell.get(sid, [])

        enriched = {}
        if conds:
            limit = resolve_max if resolve_max else len(conds)
            formatted = [_format_condition_row(server, c) for c in conds[:limit]]
            enriched["conditions"] = {
                "count": len(conds),
                "requirements": formatted,
            }
            if resolve_max and len(conds) > resolve_max:
                enriched["conditions"]["warning"] = (
                    f"Spell has {len(conds)} conditions, showing first {resolve_max}. "
                    f"Use resolve_max=0 to show all."
                )

        merged = {**entry_resolved, **enriched}
        if merged:
            resolved[sid] = merged

    return resolved
