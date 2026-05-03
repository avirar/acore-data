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

    # Set up per-request memoization cache to avoid duplicate ref lookups
    from .resolvers.ref_utils import set_ref_cache, clear_ref_cache
    req_cache = {}
    set_ref_cache(req_cache)

    try:
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

        # Generic resolution for all other tables
        return _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)
    finally:
        clear_ref_cache()


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

    # Pre-warm per-request cache with batch SQL lookups
    if "sql" in allowed:
        from collections import defaultdict as dd
        sql_groups = dd(set)
        for r in resolvable:
            if r["resolve_category"] != "sql":
                continue
            for row in rows:
                raw_value = _get_row_value(row, r["sql_col"], r["field_name"])
                if raw_value is not None and raw_value != 0:
                    sql_groups[(r["lookup_name"], r["ref_col"])].add(raw_value)
        # Batch resolve and inject into cache
        for (table, id_col), id_set in sql_groups.items():
            from .resolvers.ref_utils import batch_resolve_sql as brs, _active_cache
            batch = brs(server, table, list(id_set), id_col)
            if _active_cache is not None:
                for rid, name in batch.items():
                    _active_cache[f"sql:{table}:{rid}:{id_col}"] = name

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
