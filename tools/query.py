"""
Query tool for acore-data.

Merged from query_game_data + query_dbc.
Unified entry point for ALL data: DBC binary, SQL tables, overlays, auxiliary.

Parameters renamed: dbc_name -> name
"""

import difflib
import re
import sys
from typing import Dict, Any, List, Optional, Tuple

from core.annotation import (
    _annotate_dbc_result as _annotate_dbc_impl,
    _build_schema_error as _build_schema_error_impl,
    _convert_filter_for_dbc as _convert_filter_for_dbc_impl,
    _dbc_filter_to_sql_where,
    _escape_like_pattern,
)
from core.type_resolver import resolve_type_fields


def _resolve_sql_column(
    reg_entry: Dict, key: str, sql_table: str
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a filter key to the actual SQL column name.

    Checks registry field definitions for both C++ struct field names
    and SQL column names with case-insensitive matching. Falls back
    to fuzzy matching suggestions.

    Returns:
        (resolved_sql_col, suggestion_or_error) -- if resolved_sql_col is None,
        the suggestion string contains available field hints.
    """
    fields = reg_entry.get("fields", {})
    key_lower = str(key).lower()

    # Exact match (case-insensitive) on sql_column first
    for idx_str, info in fields.items():
        sql_col = info.get("sql_column", "")
        if sql_col and sql_col.lower() == key_lower:
            return sql_col, None

        # Also match against the field key itself (registry may use sql_column as key)
        if str(idx_str).lower() == key_lower and sql_col:
            return sql_col, None

    # Match on C++ struct name -> resolve to SQL column
    for idx_str, info in fields.items():
        c_name = info.get("name", "")
        if c_name and c_name.lower() == key_lower:
            sql_col = info.get("sql_column", c_name)
            return sql_col or c_name, None

    # Fuzzy match — build deduplicated list of (display_name, lower_name)
    seen = set()
    all_names = []
    for idx_str, info in fields.items():
        for n in [info.get("sql_column", ""), info.get("name", ""), str(idx_str)]:
            if n:
                n_lower = n.lower()
                if n_lower not in seen:
                    seen.add(n_lower)
                    all_names.append((n, n_lower))

    suggestions_lower = difflib.get_close_matches(key_lower, [n[1] for n in all_names], n=5, cutoff=0.4)
    # Map back to original casing
    suggestion_map = {n[1]: n[0] for n in all_names}
    if not suggestions_lower and len(key_lower) >= 3:
        start_matches = [(n[0], n[1]) for n in all_names if n[1].startswith(key_lower[:3])][:5]
        suggestions_lower = [s[1] for s in start_matches]

    if suggestions_lower:
        display = [suggestion_map.get(s, s) for s in suggestions_lower[:5]]
        return None, f"Did you mean: {', '.join(display)}? "
    display_all = [n[0] for n in all_names[:10]]
    return None, f"Available fields ({min(len(all_names), 10)}): {', '.join(display_all)} "


def _build_sql_filter_clause(
    col_name: str, val: Any
) -> Tuple[Optional[str], bool]:
    """Build a single SQL WHERE clause from a column name and value.

    Handles $like / $ilike dict operators and exact match values.

    Returns:
        (clause_string, is_error) -- clause_string is None on error.
    """
    if isinstance(val, dict):
        if "$like" in val:
            pattern = _escape_like_pattern(val["$like"])
            return f"{col_name} LIKE {pattern}", False
        elif "$ilike" in val:
            pattern = _escape_like_pattern(val["$ilike"])
            # MySQL case-insensitive: use LOWER() wrapper
            return f"LOWER({col_name}) LIKE LOWER({pattern})", False
        return None, True

    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f"{col_name} = '{escaped}'", False

    # Numeric / boolean values
    return f"{col_name} = {val}", False


def query_tools(server):
    """
    Query any datastore.
    
    Args:
        server: Server instance with all modules
        
    Returns:
        {"result": [...], "metadata": {...}} or {"error": "...", "isError": True}
        
    Supported data:
      - DBC binary files (Spell, Item, SkillLine)
      - SQL ObjectMgr tables (quest_template, creature_template)
      - SQL Manager tables (smart_scripts, spell_proc_event)
      - Auxiliary tables (gameobject_questitem, loot templates)
      
    Features:
      - ID lookup (O(1) with index)
      - Named field filters
      - $like / $ilike pattern matching
      - Field selection by name or index
      - Compact mode strips nulls
      - Single-record unwrapping for ID lookups
    """
    name = server.args.get("name")
    if not name:
        return {"error": "name is required", "isError": True}

    resolved = server.registry._resolve_entry(name)
    
    if resolved:
        struct_name, entry = resolved
        category = entry.get("category", "")

        if category == "dbc_backed":
            return _query_dbc(server, args=server.args, reg_entry=entry)
        elif category in ("sql_objectmgr", "sql_manager", "sql_auxiliary"):
            return _query_sql(server, args=server.args, reg_entry=entry)

    # Fallback: fuzzy matching
    suggestions = server.registry._suggest_similar_store(
        name, server.database._all_tables_cache
    )
    if suggestions:
        formatted = [f"{n} ({c})" for n, c, _ in suggestions[:5]]
        return {
            "error": f"Store '{name}' not found.",
            "suggestion": f"Did you mean: {', '.join(formatted)}?",
            "isError": True,
        }

    # Last resort: try as raw DBC
    return _query_dbc(server, args=server.args, reg_entry=None)


def _query_dbc(
    server, args: Dict[str, Any], reg_entry: Optional[Dict]
) -> Dict[str, Any]:
    """Query DBC-backed store with optional SQL overlay."""
    name = args.get("name")
    id_value = args.get("id")
    row_index = args.get("row_index")
    filter_data = args.get("filter")
    fields_param = args.get("fields")
    limit = args.get("limit", 100)
    compact = args.get("compact", True)
    info_mode = args.get("info", False)

    dbc_load_name = reg_entry.get('dbc_name', name) if reg_entry else name

    # Info mode - return DBC metadata
    if info_mode:
        try:
            reader = server._load_dbc(dbc_load_name)
            info = reader.get_info()
            return {
                "result": {
                    "file": info["file"],
                    "record_count": info["record_count"],
                    "field_count": info["field_count"],
                    "record_size": info["record_size"],
                }
            }
        except Exception as e:
            return {"error": f"DBC error: {e}", "isError": True}

    # Convert named filter to numeric indices
    dbc_filter = {}
    filter_notes = []
    if filter_data and reg_entry:
        try:
            dbc_name_for_filter = reg_entry.get('dbc_name', name) if reg_entry else name
            dbc_filter, filter_notes = _convert_filter_for_dbc_impl(
                server.registry, filter_data, reg_entry, dbc_name_for_filter
            )
        except ValueError as e:
            return _build_schema_error_impl(name, str(e), reg_entry, filter_data)

    # Query DBC
    dbc_result = None
    dbc_error = None

    try:
        reader = server._load_dbc(dbc_load_name)

        if id_value is not None:
            record = reader.get_record_by_id(id_value)
            dbc_result = [record] if record else []
        elif row_index is not None:
            record = reader.get_record(int(row_index))
            dbc_result = [record] if record else []
        elif dbc_filter:
            dbc_result = reader.query(filter_dict=dbc_filter)
            if limit and len(dbc_result) > limit:
                dbc_result = dbc_result[:limit]
        else:
            # Return all records (limited)
            dbc_result = []
            for i in range(min(limit, reader.record_count)):
                record = reader.get_record(i)
                if record:
                    dbc_result.append(record)
                else:
                    break

    except Exception as e:
        dbc_error = str(e)

    # Query SQL overlay
    sql_table = reg_entry.get("sql_table", "") if reg_entry else ""
    db_result = None
    db_error = None

    if sql_table and server.database.db_available:
        db_result, db_error = _query_sql_overlay(
            server, sql_table, id_value, dbc_filter, limit, reg_entry
        )

    # Merge results
    merged = _merge_dbc_sql(
        server, dbc_result, db_result, reg_entry, fields_param, compact, id_value is not None
    )

    if merged.get("error"):
        return merged

    metadata = {
        "source": merged.pop("source", "unknown"),
        "dbc_exists": dbc_result is not None,
        "db_table": sql_table,
        "db_exists": db_result is not None,
        "field_annotations": True,
    }

    if reg_entry:
        metadata["c_struct"] = reg_entry.get("c_struct", "")
        metadata["sql_table"] = sql_table
        metadata["store_variable"] = reg_entry.get("store_variable", "")
        refs = _extract_field_references(reg_entry)
        if refs:
            metadata["field_references"] = refs
        if reg_entry.get("referenced_by"):
            metadata["referenced_by"] = reg_entry["referenced_by"]

    if filter_notes:
        metadata["filter_notes"] = filter_notes

    return {"result": merged.get("result", []), "metadata": metadata}


def _query_sql(
    server, args: Dict[str, Any], reg_entry: Dict
) -> Dict[str, Any]:
    """Query SQL-only store."""
    name = args.get("name")
    id_value = args.get("id")
    filter_data = args.get("filter")
    limit = args.get("limit", 100)
    resolve_filter = args.get("resolve", False)
    resolve_max = args.get("resolve_max", 10)

    sql_table = reg_entry.get("sql_table", "")
    if not sql_table:
        return {
            "error": f"No SQL table for {reg_entry.get('c_struct', 'unknown')}",
            "isError": True,
        }

    if not server.database.db_available:
        return {
            "error": (
                f"Database not available "
                f"({server.database.db_user}@{server.database.db_host}:{server.database.db_port}/{server.database.db_name})"
            ),
            "isError": True,
        }

    # Smart routing
    target_db = server.database._resolve_table_database(sql_table, server.database.db_name)
    if target_db:
        print(
            f"Routing query to {target_db} for table '{sql_table}'", file=sys.stderr
        )

    # Build SQL
    sql = f"SELECT * FROM {sql_table}"
    where_clauses = []

    if id_value is not None:
        pk_col = server.database._find_primary_key(reg_entry, sql_table)
        where_clauses.append(f"{pk_col} = {id_value}")

    if filter_data:
        for col, val in filter_data.items():
            resolved_col, err_msg = _resolve_sql_column(reg_entry, col, sql_table)
            if resolved_col is None:
                return {
                    "error": f"Unknown field '{col}' for table '{sql_table}'. {err_msg}",
                    "isError": True,
                }
            clause, is_err = _build_sql_filter_clause(resolved_col, val)
            if is_err:
                return {
                    "error": f"Unsupported filter operator for '{col}'",
                    "isError": True,
                }
            where_clauses.append(clause)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += f" LIMIT {limit}"

    rows, error = server.database._query_database(sql, db_name=target_db)

    if error:
        error_msg = f"Database error: {error}"
        col_match = re.search(r"Unknown column '([^']+)'", error)
        if col_match:
            bad_col = col_match.group(1)
            suggestion = server.database._suggest_column(sql_table, bad_col)
            if suggestion:
                error_msg += f"\n{suggestion}"
        return {"error": error_msg, "isError": True}

    # Resolve type-specific fields (e.g. gameobject data[0-19] meanings)
    resolved = resolve_type_fields(server, sql_table, rows or [], resolve_filter, resolve_max)

    metadata = {
        "source": "database",
        "category": reg_entry.get("category", ""),
        "sql_table": sql_table,
        "c_struct": reg_entry.get("c_struct", ""),
        "store_variable": reg_entry.get("store_variable", ""),
        "primary_key": server.database._find_primary_key(reg_entry, sql_table),
    }

    # Add cross-reference hints
    refs = _extract_field_references(reg_entry)
    if refs:
        metadata["field_references"] = refs
    if reg_entry.get("referenced_by"):
        metadata["referenced_by"] = reg_entry["referenced_by"]

    if rows:
        metadata["columns"] = list(rows[0].keys())
    elif server.database.db_available:
        schema = server.database._get_table_schema(sql_table)
        if schema:
            metadata["columns"] = [c["COLUMN_NAME"] for c in schema]

    mgr = reg_entry.get("manager_singleton", "")
    if mgr:
        metadata["manager_singleton"] = mgr

    if resolved:
        metadata["$resolved_fields"] = resolved
        metadata["type_resolved"] = True

    return {"result": rows or [], "count": len(rows or []), "metadata": metadata}


def _query_sql_overlay(
    server, sql_table: str, id_value: Optional[int], dbc_filter: Dict, limit: int, reg_entry: Optional[Dict] = None
) -> tuple:
    """Query SQL overlay for DBC-backed store."""
    sql = f"SELECT * FROM {sql_table}"
    where_clauses = []

    if id_value is not None:
        pk_col = "ID"
        if len(dbc_filter) == 0:
            where_clauses.append(f"{pk_col} = {id_value}")

    if dbc_filter:
        where_clauses.extend(
            _dbc_filter_to_sql_where(dbc_filter, reg_entry)
        )

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += f" LIMIT {limit}"

    return server.database._query_database(sql)


def _merge_dbc_sql(
    server,
    dbc_result: List,
    db_result: Optional[List],
    reg_entry: Optional[Dict],
    fields_param: Optional[List],
    compact: bool,
    single_record: bool
) -> Dict[str, Any]:
    """Merge DBC and SQL results with annotation."""
    if db_result and not dbc_result:
        return {"result": db_result, "source": "database"}

    if dbc_result and not db_result:
        annotated = _annotate_dbc_result(
            dbc_result, reg_entry, fields_param, compact, single_record
        )
        return {"result": annotated, "source": "dbc"}

    if dbc_result and db_result:
        annotated = _annotate_dbc_result(
            dbc_result, reg_entry, db_result, fields_param, compact, single_record
        )
        return {"result": annotated, "source": "hybrid"}

    return {"error": "No data found", "isError": True}


def _annotate_dbc_result(
    result: List,
    reg_entry: Optional[Dict],
    db_result: Optional[List] = None,
    fields_param: Optional[List] = None,
    compact: bool = True,
    single_record: bool = False
) -> Any:
    """Annotate DBC results. Wrap/unwrap based on single_record flag."""
    if not result:
        return []

    # Convert fields_param=False to None for annotation
    actual_fields = fields_param if fields_param is not False else None

    # For single record lookups, unwrap to flat list
    if single_record and len(result) == 1:
        annotated = _annotate_dbc_impl(
            result[0], reg_entry, db_result, actual_fields, compact
        )
        return annotated.get("result", []) if isinstance(annotated, dict) else annotated

    # Multi-record: return nested lists
    return _annotate_dbc_impl(result, reg_entry, db_result, actual_fields, compact).get(
        "result", []
    )


def _extract_field_references(reg_entry: Optional[Dict]) -> Optional[Dict[str, List]]:
    """Extract field-level references from registry entry for metadata hints."""
    if not reg_entry or "fields" not in reg_entry:
        return None

    refs = {}
    for field_key, field_info in reg_entry["fields"].items():
        if field_info.get("references"):
            field_name = field_info.get("name", field_key)
            refs[field_name] = field_info["references"]

    return refs if refs else None


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "query",
        "description": (
            "Query any datastore. Merged from query_game_data + query_dbc."
            " Supports DBC binary files, SQL tables, overlays, and auxiliary stores."
            " Use id= for O(1) lookup, filter={...} for named field queries,"
            " fields=[...] for column selection, compact=true (default) to strip nulls."
            " Use resolve=true to get type-aware field resolution for tables like gameobject_template."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Datastore name: DBC file (Spell), SQL table (quest_template),"
                        " or struct (SpellEntry). Use lookup(query='<name>') to find valid names."
                    )
                },
                "id": {
                    "type": "number",
                    "description": "Primary key ID for O(1) lookup. Mutually exclusive with filter."
                },
                "filter": {
                    "type": "object",
                    "description": (
                        "Filter by field names or indices."
                        " Supports $like and $ilike patterns."
                        ' Example: {"name": "Polymorph"} or {"0": 118}'
                    ),
                    "additionalProperties": True
                },
                "fields": {
                    "type": "array",
                    "items": {"type": ["number", "string"]},
                    "description": (
                        "Select specific fields by index [38, 39] or name ['BaseLevel', 'SpellLevel']."
                        " None = all fields."
                    )
                },
                "limit": {
                    "type": "number",
                    "description": "Max records to return (default: 100)"
                },
                "compact": {
                    "type": "boolean",
                    "description": "Strip null fields (default: true)"
                },
                "resolve": {
                    "oneOf": [
                        {"type": "boolean"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": (
                        "Resolve type-specific data fields. Use true to resolve all references, "
                        "or ['dbc', 'sql', 'loot'] to pick specific types. For gameobject_template, "
                        "this annotates data[0-19] with their actual meaning (lootId, lockId, spellId, etc.)"
                    )
                },
                "resolve_max": {
                    "type": "number",
                    "description": (
                        "Max items to return per loot table resolution (default: 10). "
                        "Use 0 for no limit."
                    )
                }
            },
            "required": ["name"]
        }
    }

