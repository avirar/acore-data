"""Resolve gameobject_template type-specific fields.

Uses type_field_mappings from the registry to resolve data[0-19] columns
based on gameobject type (Door, Button, Questgiver, Chest, etc.).
"""
from typing import Any, Dict, List

from ..enums import GO_TYPE_NAMES


def _resolve_gameobject_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve gameobject_template type-specific fields from registry."""
    # Import core helpers (to avoid circular imports)
    from ..type_resolver import (
        _resolve_dbc_ref,
        _resolve_loot_ref,
        _resolve_sql_ref,
    )

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

    return resolved if resolved else {}


# Register with resolver dispatch
from . import register_resolver
register_resolver("gameobject_template", _resolve_gameobject_fields)
