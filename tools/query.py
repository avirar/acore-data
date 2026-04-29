"""
Query tool for acore-data.

Merged from query_game_data + query_dbc.
Unified entry point for ALL data: DBC binary, SQL tables, overlays, auxiliary.

Parameters renamed: dbc_name -> name
"""

import sys
from typing import Dict, Any, List, Optional


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
            dbc_filter, filter_notes = _convert_filter_for_dbc(
                server.registry, filter_data, reg_entry, dbc_name_for_filter
            )
        except ValueError as e:
            return _build_schema_error(name, str(e), reg_entry, filter_data)

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
            server, sql_table, id_value, dbc_filter, limit
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
            if isinstance(val, str):
                # Escape single quotes
                escaped_val = val.replace("'", "''")
                where_clauses.append(f"{col} = '{escaped_val}'")
            else:
                where_clauses.append(f"{col} = {val}")

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

    metadata = {
        "source": "database",
        "category": reg_entry.get("category", ""),
        "sql_table": sql_table,
        "c_struct": reg_entry.get("c_struct", ""),
        "store_variable": reg_entry.get("store_variable", ""),
        "primary_key": server.database._find_primary_key(reg_entry, sql_table),
    }

    if rows:
        metadata["columns"] = list(rows[0].keys())
    elif server.database.db_available:
        schema = server.database._get_table_schema(sql_table)
        if schema:
            metadata["columns"] = [c["COLUMN_NAME"] for c in schema]

    mgr = reg_entry.get("manager_singleton", "")
    if mgr:
        metadata["manager_singleton"] = mgr

    return {"result": rows or [], "count": len(rows or []), "metadata": metadata}


def _query_sql_overlay(
    server, sql_table: str, id_value: Optional[int], dbc_filter: Dict, limit: int
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
            _dbc_filter_to_sql_where_server(server, dbc_filter, None)
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


def _convert_filter_for_dbc(
    registry, filter_data: Dict, reg_entry: Dict, dbc_name: str
) -> tuple:
    """Convert filter dict with field names to DBC-compatible numeric indices."""
    if not filter_data:
        return {}, []

    converted = {}
    notes = []

    for key, value in filter_data.items():
        idx, resolved_name, note = registry._resolve_filter_key(
            key, reg_entry, dbc_name, set()
        )
        converted[idx] = value
        if note:
            notes.append(f"  {note}")

    return converted, notes


def _dbc_filter_to_sql_where_server(
    server, filter_dict: Dict[int, Any], reg_entry: Optional[Dict]
) -> List[str]:
    """Convert DBC filter to SQL WHERE clauses."""
    from core.annotation import _dbc_filter_to_sql_where
    return _dbc_filter_to_sql_where(filter_dict, reg_entry)


def _annotate_dbc_result(
    result: List,
    reg_entry: Optional[Dict],
    db_result: Optional[List] = None,
    fields_param: Optional[List] = None,
    compact: bool = True,
    single_record: bool = False
) -> Any:
    """Annotate DBC results. Wrap/unwrap based on single_record flag."""
    from core.annotation import _annotate_dbc_result as annotate_func

    if not result:
        return []

    # Convert fields_param=False to None for annotation
    actual_fields = fields_param if fields_param is not False else None
    
    # For single record lookups, unwrap to flat list
    if single_record and len(result) == 1:
        annotated = annotate_func(
            result[0], reg_entry, db_result, actual_fields, compact
        )
        return annotated.get("result", []) if isinstance(annotated, dict) else annotated

    # Multi-record: return nested lists
    return annotate_func(result, reg_entry, db_result, actual_fields, compact).get(
        "result", []
    )


def _build_schema_error(
    store_name: str, error_msg: str, reg_entry: Optional[Dict], filter_used: Optional[Dict]
) -> Dict[str, Any]:
    """Build consistent schema error."""
    from core.annotation import _build_schema_error as build_err
    return build_err(store_name, error_msg, reg_entry, filter_used)


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "query",
        "description": (
            "Query any datastore. Merged from query_game_data + query_dbc."
            " Supports DBC binary files, SQL tables, overlays, and auxiliary stores."
            " Use id= for O(1) lookup, filter={...} for named field queries,"
            " fields=[...] for column selection, compact=true (default) to strip nulls."
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
                }
            },
            "required": ["name"]
        }
    }


# Import re for regex usage
import re
