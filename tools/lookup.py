"""
Lookup tool for acore-data.

Merged from lookup_datastore + describe_fields.
Returns complete schema or summary metadata for any datastore.
"""

from typing import Dict, Any, List, Optional


def lookup_tools(server):
    """
    Lookup datastore schema/metadata.
    
    Args:
        server: Server instance with registry and database
        
    Returns:
        For detail="schema" (default): full field list + all metadata
        For detail="summary": compact output (10 sample fields only)
        
    Resolution:
      - struct names (SpellEntry, CreatureEntry)
      - SQL table names (quest_template, smart_scripts)
      - DBC file names (Spell, Item)
      - Store variables (sSpellStore)
    """
    query = server.args.get("query", "").strip()
    detail = server.args.get("detail", "schema")

    if not query:
        return {"error": "query is required", "isError": True}

    # Resolve name to entry
    resolved = server.registry._resolve_entry(query)
    
    if not resolved:
        # Try fuzzy search
        entries = server.registry.registry.get("entries", {})
        matches = []
        q_lower = query.lower()
        
        for struct_name, entry in entries.items():
            if (
                q_lower in struct_name.lower()
                or q_lower in entry.get("sql_table", "").lower()
                or q_lower in entry.get("dbc_file", "").lower()
                or q_lower in entry.get("dbc_name", "").lower()
            ):
                matches.append(struct_name)

        if not matches:
            return {
                "result": {
                    "matches": [],
                    "message": f"No datastore found matching '{query}'"
                }
            }

        # Return multiple matches
        results = []
        for struct_name in matches[:10]:
            entry = entries[struct_name]
            result_item = _build_lookup_result(
                server, struct_name, entry, detail
            )
            results.append(result_item)
        
        return {"result": {"matches": results, "count": len(results)}}

    # Exact match
    struct_name, entry = resolved
    result_item = _build_lookup_result(server, struct_name, entry, detail)
    
    return {"result": {"matches": [result_item], "count": 1, "exact": True}}


def _build_lookup_result(
    server, struct_name: str, entry: Dict, detail: str
) -> Dict[str, Any]:
    """Build lookup result based on detail level."""
    category = entry.get("category", "")
    sql_table = entry.get("sql_table", "")

    result: Dict[str, Any] = {
        "c_struct": struct_name,
        "category": category,
        "sql_table": sql_table,
        "sql_database": entry.get("sql_database", "db_world"),
        "store_variable": entry.get("store_variable", ""),
        "header_file": entry.get("header_file", ""),
        "field_count": len(entry.get("fields", {})),
        "hints": _build_hints(category, entry),
    }

    # Add cross-references at entry level if present
    if entry.get("referenced_by"):
        result["referenced_by"] = entry["referenced_by"]

    # DBC-backed specific
    if category == "dbc_backed":
        result["dbc_file"] = entry.get("dbc_file", "")
        result["dbc_name"] = entry.get("dbc_name", "")
        result["format_variable"] = entry.get("format_variable", "")
        result["store_type"] = entry.get("store_type", "")

    # SQL ObjectMgr specific
    elif category == "sql_objectmgr":
        result["loader_function"] = entry.get("loader_function", "")
        result["container_type"] = entry.get("container_type", "")

    # SQL Manager specific
    elif category in ("sql_manager", "sql_auxiliary"):
        result["manager_singleton"] = entry.get("manager_singleton", "")
        result["manager_class"] = entry.get("manager_class", "")
        result["container_type"] = entry.get("container_type", "")

    # Field details based on detail level
    fields = entry.get("fields", {})
    
    if detail == "schema":
        # Full field list with all metadata
        all_fields = []
        def _sort_key(item):
            try:
                return int(item[0])
            except (ValueError, TypeError):
                return 999999  # String keys (SQL fields) sort after numeric

        for idx_str, info in sorted(fields.items(), key=_sort_key):
            field_entry = {
                "index": int(idx_str) if idx_str.isdigit() else idx_str,
                "name": info.get("name", ""),
                "type": info.get("type", ""),
                "sql_column": info.get("sql_column", ""),
                "is_primary_key": (idx_str == "0"),
            }
            if info.get("notes"):
                field_entry["notes"] = info.get("notes", "")
            if info.get("references"):
                field_entry["references"] = info["references"]
            all_fields.append(field_entry)
        result["fields"] = all_fields

    else:  # detail == "summary"
        # Sample of first 10 fields (human-friendly)
        sample = list(fields.items())[:10]
        result["fields_sample"] = [
            {"key": k, "name": v.get("name", ""), "type": v.get("type", "")}
            for k, v in sample
        ]

    # Add live SQL columns from database if available
    if sql_table and server.database.db_available:
        schema = server.database._get_table_schema(sql_table)
        if schema:
            result["sql_columns"] = [
                {
                    "name": c["COLUMN_NAME"],
                    "type": c["DATA_TYPE"],
                    "is_primary_key": c.get("is_primary_key", False),
                }
                for c in schema
            ]

    return result


def _build_hints(category: str, entry: Dict) -> Dict[str, str]:
    """Build access hints based on category."""
    store_var = entry.get("store_variable", "")
    sql_table = entry.get("sql_table", "")
    struct_name = entry.get("c_struct", "Entry")

    if category == "dbc_backed":
        dbc_file = entry.get("dbc_file", "")
        return {
            "loading": f"Loaded from {dbc_file} via DBCStorage, with SQL overlay from {sql_table}",
            "access_pattern": f"{store_var}.LookupEntry(id) -> {{struct_name}} const*",
        }
    elif category == "sql_objectmgr":
        loader = entry.get("loader_function", "ObjectMgr::Load*()")
        return {
            "loading": f"Loaded via {loader} from SQL table {sql_table}",
            "access_pattern": f"sObjectMgr->Get{struct_name}(id)",
        }
    elif category in ("sql_manager", "sql_auxiliary"):
        singleton = entry.get("manager_singleton", "")
        mgr_class = entry.get("manager_class", "")
        return {
            "loading": f"Loaded by {mgr_class} ({singleton}) from SQL table {sql_table}",
            "access_pattern": (
                f"{singleton}->Get{struct_name}()"
                if singleton
                else "Direct SQL query"
            ),
        }

    return {"access_pattern": "Unknown"}


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "lookup",
        "description": (
            "Get schema/metadata for a datastore. Merges lookup_datastore + describe_fields."
            " Resolves by struct name, SQL table, DBC file, or store variable."
            " Use detail='schema' for complete field list (default) or detail='summary' for compact output."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Name to lookup: struct name (SpellEntry), SQL table (quest_template),"
                        " DBC file (Spell), or store variable (sSpellStore)"
                    )
                },
                "detail": {
                    "type": "string",
                    "enum": ["schema", "summary"],
                    "description": (
                        "Detail level: 'schema' (default) = all fields with full metadata,"
                        " 'summary' = 10 sample fields for human reading"
                    )
                }
            },
            "required": ["query"]
        }
    }
