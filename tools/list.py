"""
List tool for acore-data.

Merged from list_stores + list_dbcs.
Lists available datastores with optional search and category filtering.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path


def list_tools(server):
    """
    List available datastores.
    
    Args:
        server: Server instance with registry and format_parser
        
    Returns:
        {"result": [...], "count": N}
        
    Merged capabilities:
      - All categories (dbc_backed, sql_objectmgr, sql_manager, sql_auxiliary)
      - DBC-only info (format, field_count, record_size, sql_overlay)
      - Search filtering
    """
    search = server.args.get("search", "").lower()
    category = server.args.get("category", "all")
    limit = int(server.args.get("limit", 50) or 50)

    entries = server.registry.registry.get("entries", {})
    result_list = []

    for struct_name, entry in entries.items():
        # Category filter
        if category != "all" and entry.get("category", "") != category:
            continue

        # Search filter
        search_fields = [
            struct_name,
            entry.get("sql_table", ""),
            entry.get("dbc_file", ""),
            entry.get("dbc_name", ""),
            entry.get("store_variable", ""),
        ]
        if search and not any(search in f.lower() for f in search_fields if f):
            continue

        item = {
            "struct": struct_name,
            "category": entry.get("category", ""),
            "sql_table": entry.get("sql_table", ""),
            "dbc_file": entry.get("dbc_file", ""),
        }

        # Add DBC-specific info for dbc_backed
        if entry.get("category") == "dbc_backed":
            dbc_name = entry.get("dbc_name", "")
            format_string = server.format_parser.get_format(dbc_name)
            
            item["dbc_name"] = dbc_name
            item["field_count"] = len(format_string) if format_string else 0
        
        # SQL-only stores
        elif entry.get("category") in ("sql_objectmgr", "sql_manager", "sql_auxiliary"):
            sql_table = entry.get("sql_table", "")
            if sql_table:
                item["columns"] = (
                    len(entry.get("fields", {}))
                    if entry.get("fields")
                    else None
                )
            if entry.get("manager_singleton"):
                item["manager"] = entry.get("manager_singleton", "")

        result_list.append(item)

    # Sort by struct name
    result_list.sort(key=lambda x: x["struct"].lower())

    total = len(result_list)
    shown = result_list[:limit]
    result: Dict[str, Any] = {"result": shown, "count": len(shown)}
    if total > len(shown):
        result["metadata"] = {
            "total": total,
            "note": (
                f"Showing first {limit} of {total}. Refine with search= or category=."
            ),
        }
    return result


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "list",
        "description": (
            "List available datastores by struct/table/DBC name. Each entry carries struct,"
            " category, sql_table, dbc_file and field_count. Defaults to the first 50 matches"
            "(alphabetical) - refine with search= when total is reported in metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": (
                        "Optional search term to filter by struct name, table, or DBC file"
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": "Max entries to return (default 50; total is reported in metadata when truncated)"
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "dbc_backed", "sql_objectmgr", "sql_manager", "sql_auxiliary"],
                    "description": (
                        "Filter by category. Default: 'all' (all categories)"
                    )
                }
            },
            "required": []
        }
    }
