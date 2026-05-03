"""Resolve gameobject_template type-specific fields.

Uses type_field_mappings from the registry to resolve data[0-19] columns
based on gameobject type (Door, Button, Questgiver, Chest, etc.). Pre-warms
per-request cache with batch SQL lookups before row iteration.
"""
from collections import defaultdict
from typing import Any, Dict, List

from ..enums import GO_TYPE_NAMES
from .ref_utils import resolve_dbc_ref, resolve_loot_ref, resolve_sql_ref, _active_cache


def resolve_gameobject_fields(
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

    if isinstance(resolve_filter, list):
        allowed_refs = set(resolve_filter)
    elif resolve_filter is True:
        allowed_refs = {"dbc", "sql", "loot"}
    else:
        return {}

    # Pre-warm cache: collect all SQL IDs across rows from type_field_mappings
    if "sql" in allowed_refs:
        sql_groups = defaultdict(set)
        for row in rows:
            go_type = row.get("type", 0)
            field_map = type_mappings.get(str(go_type), {})
            if not field_map:
                continue
            for data_col, field_info in field_map.items():
                ref_type = field_info.get("resolve_type", "")
                if ref_type != "sql":
                    continue
                raw_value = row.get(data_col)
                if raw_value is None:
                    for key in row:
                        if key.lower() == data_col.lower():
                            raw_value = row[key]
                            break
                if raw_value is not None and raw_value != 0:
                    table = field_info.get("target", "")
                    id_col = field_info.get("id_col", "entry") or "entry"
                    sql_groups[(table, id_col)].add(raw_value)
        # Batch resolve and inject into cache
        for (table, id_col), id_set in sql_groups.items():
            from .ref_utils import batch_resolve_sql as brs
            batch = brs(server, table, list(id_set), id_col)
            if _active_cache is not None:
                for rid, name in batch.items():
                    _active_cache[f"sql:{table}:{rid}:{id_col}"] = name

    resolved = {}
    for row in rows:
        entry_value = row.get("entry")
        go_type = row.get("type", 0)

        type_name = GO_TYPE_NAMES.get(go_type, f"UNKNOWN({go_type})")
        field_map = type_mappings.get(str(go_type), {})

        if not field_map:
            continue

        row_resolved = {"type_name": type_name}

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
                resolved_value = resolve_dbc_ref(server, dbc_name, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "sql" and "sql" in allowed_refs:
                table = field_info.get("target", "")
                id_col = field_info.get("id_col", "entry") or "entry"
                resolved_value = resolve_sql_ref(server, table, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value

            elif ref_type == "loot" and "loot" in allowed_refs:
                table = field_info.get("target", "gameobject_loot_template")
                id_col = field_info.get("id_col", "Entry")
                loot_items = resolve_loot_ref(server, table, raw_value, id_col, resolve_max)
                if loot_items is not None:
                    entry_resolved.update(loot_items)

            row_resolved[data_col] = entry_resolved

        resolved[entry_value] = row_resolved

    return resolved if resolved else {}
