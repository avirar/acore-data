"""
Annotation module for acore-data.

Handles record annotation with field metadata, source tracking,
filter parsing, and error formatting.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


def _resolve_field_name_to_index(
    field_name: str, fields_meta: Dict
) -> List[int]:
    """Resolve field name (C++ struct or SQL column) to list of index numbers.
    
    Handles array elements like 'name', 'name[3]', etc.
    Returns empty list if not found.
    """
    resolved = []
    name_lower = field_name.lower()

    for idx_str, info in fields_meta.items():
        c_name = info.get("name", "").lower()
        sql_col = info.get("sql_column", "").lower()
        idx = int(idx_str)

        # Direct match
        if c_name == name_lower or sql_col == name_lower:
            resolved.append(idx)
            continue

        # Prefix match for arrays (e.g., 'name' matches 'name[3]')
        array_prefix = c_name.split("[")[0] if "[" in c_name else c_name
        if field_name == array_prefix and name_lower.startswith(array_prefix):
            resolved.append(idx)

    return resolved


def _parse_filter_value(value: Any) -> Tuple[str, str]:
    """Parse filter value into (operator, escaped_value).
    
    Supports:
      - Exact match: value -> (=, 'value')
      - $like: {'$like': '%term%'} -> (LIKE, '%term%')
      - $ilike: {'$ilike': '%term%'} -> (INSTR for case-insensitive)
    
    Returns:
        Tuple of (operator_sql, escaped_value)
    """
    if isinstance(value, dict):
        if "$like" in value:
            return "LIKE", _escape_like_pattern(value["$like"])
        elif "$ilike" in value:
            # MySQL doesn't have ILIKE; use LIKE BINARY for case-sensitive
            # or LOWER() + LIKE for case-insensitive
            return "LIKE_CI", _escape_like_pattern(value["$ilike"])
    
    if isinstance(value, str):
        return "=", f"'{value}'"
    
    return "=", str(value)


def _escape_like_pattern(pattern: str) -> str:
    """Escape special characters in LIKE pattern and wrap with quotes.

    Preserves user-provided % and _ wildcards. Only escapes backslashes."""
    escaped = pattern.replace("\\", "\\\\")
    return f"'{escaped}'"


def _dbc_filter_to_sql_where(
    filter_dict: Dict[int, Any], reg_entry: Optional[Dict]
) -> List[str]:
    """Convert DBC filter dict to SQL WHERE clauses with parameterized escaping.
    
    Args:
        filter_dict: Dictionary of field_index -> value
        reg_entry: Registry entry for SQL column mapping
    
    Returns:
        List of WHERE clause strings
    """
    where_clauses = []
    fields_meta = reg_entry.get("fields", {}) if reg_entry else {}

    for idx, value in filter_dict.items():
        field_info = fields_meta.get(str(idx), {})
        sql_col = field_info.get("sql_column", f"field_{idx}")

        operator, escaped_value = _parse_filter_value(value)

        if operator == "LIKE":
            where_clauses.append(f"{sql_col} LIKE {escaped_value}")
        elif operator == "LIKE_CI":
            # Case-insensitive LIKE in MySQL
            where_clauses.append(f"LOWER({sql_col}) LIKE LOWER({escaped_value})")
        else:
            where_clauses.append(f"{sql_col} {operator} {escaped_value}")

    return where_clauses


def _annotate_single_record(
    record: Dict[int, Any],
    fields_meta: Dict[str, Dict],
    sql_values: Optional[Dict] = None,
    field_filter: Optional[List] = None,
    compact: bool = True
) -> List[Dict[str, Any]]:
    """Annotate single record with source tracking.
    
    Args:
        record: DBC record dict {index: value}
        fields_meta: Registry field mapping {index: field_info}
        sql_values: Optional SQL overlay values for source comparison
        field_filter: List of field indices/names to include (None = all)
        compact: If True, strip null values and skip unused fields
        
    Returns:
        List of annotated field dicts
    """
    if not isinstance(record, dict):
        return []

    # Build index set for field_filter if provided
    filter_indices = None
    if field_filter and isinstance(field_filter, list):
        filter_indices = set()
        for f in field_filter:
            if isinstance(f, int):
                filter_indices.add(f)
            elif isinstance(f, str):
                resolved = _resolve_field_name_to_index(f, fields_meta)
                if resolved:
                    filter_indices.update(resolved)

    pk_col = None
    if "0" in fields_meta:
        pk_col = fields_meta["0"].get("sql_column", "ID")

    this_sql_values = None
    if sql_values and isinstance(sql_values, dict):
        this_sql_values = sql_values
    elif sql_values and isinstance(sql_values, list) and len(sql_values) == 1:
        if pk_col and record.get(0):
            for s in sql_values:
                if s.get(pk_col) == record.get(0):
                    this_sql_values = s
                    break

    annotated = []
    for idx, value in sorted(record.items()):
        try:
            idx_int = int(idx)
        except (ValueError, TypeError):
            continue

        # Apply field filter if provided
        if filter_indices is not None and idx_int not in filter_indices:
            continue

        # Skip null values in compact mode
        if compact and value is None:
            continue

        field_info = fields_meta.get(str(idx_int), {})

        sql_col = field_info.get("sql_column", "")
        db_value = value
        sql_value = None
        source = "dbc"

        if this_sql_values and sql_col:
            sql_value = this_sql_values.get(sql_col)
            if sql_value is not None:
                if db_value == sql_value:
                    source = "merged"
                else:
                    source = "dbc"

        entry: Dict[str, Any] = {
            "index": idx_int,
            "name": field_info.get("name", f"Field{idx_int}"),
            "value": db_value,
            "type": field_info.get("type", "unknown"),
            "source": source
        }

        if sql_col:
            entry["sql_column"] = sql_col

        if source == "dbc" and sql_value is not None and sql_value != db_value:
            entry["sql_override"] = sql_value
            entry["source_note"] = "DBC value; SQL has different value"

        annotated.append(entry)

    return annotated


def _annotate_dbc_result(
    result: Any,
    reg_entry: Optional[Dict],
    db_result: Optional[List] = None,
    fields: Optional[List] = None,
    compact: bool = True
) -> Dict[str, Any]:
    """Annote DBC query results with field names, types, and source tracking.
    
    Args:
        result: Query result (dict for single record, list for multiple)
        reg_entry: Registry entry with field metadata
        db_result: Optional SQL overlay results
        fields: List of field indices/names to include (None = all)
        compact: If True, strip nulls, omit raw, unwrap single records
        
    Returns:
        For compact=True, single record: {"result": [field1, field2, ...]}
        For compact=True, multi record: {"result": [[row1_fields], [row2_fields]]}
    """
    if not reg_entry:
        if compact:
            return {"result": result} if isinstance(result, list) else {"result": result}
        return {
            "annotated": result if isinstance(result, list) else [result],
            "raw": result
        }

    fields_meta = reg_entry.get("fields", {})
    sql_values = None
    if db_result and isinstance(db_result, list) and len(db_result) > 0:
        if isinstance(result, dict):
            sql_values = db_result[0]

    if isinstance(result, dict):
        # Single record - flat annotate
        annotated = _annotate_single_record(
            result, fields_meta, sql_values, fields, compact
        )
        if not annotated:
            return {
                "result": {},
                "metadata": {"empty_reason": "No matching fields", "compact": compact}
            }
        # Remove raw section - pure duplication burning LLM context
        return {"result": annotated}

    elif isinstance(result, list):
        if not result:
            return {
                "result": {},
                "metadata": {"empty_reason": "No records found", "compact": compact}
            }

        annotated_rows = []
        for record in result:
            row_ann = _annotate_single_record(
                record, fields_meta, sql_values, fields, compact
            )
            annotated_rows.append(row_ann)

        if compact:
            return {"result": annotated_rows}
        
        return {"annotated": annotated_rows, "raw": result, "result": annotated_rows}

    return {"result": result}


def _build_schema_error(
    store_name: str,
    error_msg: str,
    reg_entry: Optional[Dict],
    filter_used: Optional[Dict] = None
) -> Dict[str, Any]:
    """Build consistent schema error response with suggestions.
    
    Returns: {"error": message, "isError": True, "suggestion": optional hint}
    """
    result: Dict[str, Any] = {
        "error": error_msg,
        "isError": True
    }

    # Add field suggestions if available
    if reg_entry and filter_used:
        fields = reg_entry.get("fields", {})
        all_field_names = []
        for idx_str, info in fields.items():
            all_field_names.append(info.get("name", ""))
            all_field_names.append(info.get("sql_column", ""))

        if filter_used:
            bad_key = next(iter(filter_used.keys()))
            bad_lower = str(bad_key).lower()
            suggestions = [
                n for n in all_field_names
                if bad_lower in n.lower() or n.lower() in bad_lower
            ]
            if not suggestions and len(bad_lower) >= 3:
                suggestions = [
                    n for n in all_field_names if n.lower().startswith(bad_lower[:3])
                ]

            if suggestions:
                result["suggestion"] = f"Available fields: {', '.join(suggestions[:8])}"

    return result


def _convert_filter_for_dbc(
    registry,
    filter_data: Dict,
    reg_entry: Dict,
    dbc_name: str
) -> Tuple[Dict[int, Any], List[str], Optional[Dict[int, List[int]]]]:
    """Convert filter dict with field names to DBC-compatible numeric indices.

    When a filter key matches the bare SQL column name of an indexed field family
    (e.g., 'EffectMiscValue' matching EffectMiscValue[0/1/2]), all slots are OR'd.
    Single-index and bracket-notation keys match only their specific slot.

    Args:
        registry: Registry instance for _resolve_filter_key
        filter_data: Filter dictionary {name or index: value}
        reg_entry: Registry entry
        dbc_name: DBC name

    Returns:
        Tuple of (converted_filter, notes, or_groups)
        - converted_filter: {int_index: value} for AND matching
        - notes: list of informational strings
        - or_groups: None if no OR groups; else {primary_idx: [list_of_all_matching_indices]}
          where the primary index is used in converted_filter but post-filtering should
          also match records where any sibling index equals the value.
    """
    if not filter_data:
        return {}, [], None

    converted = {}
    notes = []
    or_groups: Dict[int, List[int]] = {}

    for key, value in filter_data.items():
        idx, resolved_name, note = registry._resolve_filter_key(
            key, reg_entry, dbc_name, set()
        )
        converted[idx] = value
        if note:
            notes.append(f"  {note}")

        # Check for multi-slot OR expansion
        or_primary, or_siblings = registry._find_sibling_indices(key, dbc_name)
        if or_siblings:
            or_groups[idx] = [idx] + or_siblings

    return converted, notes, or_groups if or_groups else None
