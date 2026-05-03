"""
SQL tool for acore-data.

Port of execute_sql with renamed parameter (sql -> query).
Preserves all smart routing, typo suggestions, and multi-DB support.
"""

import sys
import re
from typing import Dict, Any, List, Optional


def sql_tools(server):
    """
    Execute raw SQL query with smart database routing.

    Args:
        server: Server instance with database module

    Returns:
        {"result": [...], "count": N} or {"error": "...", "isError": True}

    Features:
      - Smart multi-database routing (acore_world, acore_characters, acore_auth)
      - Typo suggestions for tables and columns
      - Safety: blocks DROP, TRUNCATE, ALTER, GRANT, REVOKE
      - Configurable via ACORE_SQL_TOOL_MODE=full|readonly|disabled
    """
    query = server.args.get("query", "").strip()

    if not query:
        return {"error": "query is required", "isError": True}

    if not server.database.db_available:
        return {
            "error": (
                f"Database not available "
                f"({server.database.db_user}@{server.database.db_host}:{server.database.db_port}/{server.database.db_name})."
                " Check DB credentials in MCP server environment config."
            ),
            "isError": True,
        }

    query_upper = query.upper().strip()

    # Readonly mode: only allow SELECT statements
    from tools import get_sql_mode
    if get_sql_mode() == "readonly" and not query_upper.startswith("SELECT"):
        return {
            "error": f"Readonly mode: '{query_upper.split()[0]}' is not allowed. Set ACORE_SQL_TOOL_MODE=full for write access.",
            "isError": True,
        }

    # Safety: block destructive statements
    for forbidden in ["DROP ", "TRUNCATE ", "ALTER ", "GRANT ", "REVOKE "]:
        if query_upper.startswith(forbidden):
            return {
                "error": f"Forbidden statement type: {forbidden.strip()}",
                "isError": True,
            }

    # Smart routing: extract tables and determine correct database
    tables = server.database._extract_tables_from_sql(query)
    target_db = server.database.db_name

    if tables:
        primary_table = tables[0]
        resolved_db = server.database._resolve_table_database(
            primary_table, server.database.db_name
        )
        if resolved_db:
            target_db = resolved_db
            print(
                f"Routing query to {target_db} for table '{primary_table}'",
                file=sys.stderr,
            )

    rows, error = server.database._query_database(query, db_name=target_db)

    if error:
        # Check for wrong database and try all databases
        if "Unknown table" in error or "doesn't exist" in error:
            for db in server.database._db_priority_order:
                if db == target_db:
                    continue
                rows, error = server.database._query_database(query, db_name=db)
                if not error and rows is not None:
                    print(f"Retried successfully in {db}", file=sys.stderr)
                    # Update cache
                    for table in tables:
                        tbl_lower = table.lower()
                        if tbl_lower in server.database._table_to_db_cache:
                            dbs = server.database._table_to_db_cache[tbl_lower]
                            if db not in dbs:
                                dbs.insert(0, db)
                        else:
                            server.database._table_to_db_cache[tbl_lower] = [db]

                    # Hint for empty loot_template results
                    if not rows:
                        table_match = re.search(r'FROM\s+`?(\w+)`?', query, re.IGNORECASE)
                        if table_match:
                            tbl = table_match.group(1)
                            if (
                                "loot_template" in tbl.lower()
                                and re.search(
                                    r"\bITEM\s*=|ITEM\s+=\s*\d+", query, re.IGNORECASE
                                )
                            ):
                                hint = (
                                    "No results. For quest items,"
                                    " try gameobject_questitem or creature_questitem tables.\n"
                                    f"Example: SELECT * FROM gameobject_questitem WHERE ItemId = <item_id>\n"
                                    "Use lookup(query='gameobject_questitem') to see schema."
                                )
                                return {"result": [], "count": 0, "hint": hint}

                    return {"result": rows or [], "count": len(rows or [])}

            # Build error with suggestions
            msg = f"Database query failed: {error}"
            table_match = re.search(
                r"Table '(\w+)\.(\w+)' doesn't exist", error
            )
            if not table_match:
                table_match = re.search(r"Unknown table '([^']+)'", error)

            if table_match:
                bad_table = (
                    table_match.group(2)
                    if table_match.lastindex >= 2
                    else table_match.group(1)
                )

                # Check if the table name matches a DBC-backed store
                resolved = server.registry._resolve_entry(bad_table)
                if resolved:
                    struct_name, entry = resolved
                    if entry.get("category") == "dbc_backed":
                        dbc_name = entry.get("dbc_name", bad_table)
                        sql_overlay = entry.get("sql_table", "")
                        hint = (
                            f"\n\n'{bad_table}' is a DBC binary file, not a SQL table.\n"
                            f"Use acore_data_query(name='{dbc_name}') to query this data."
                        )
                        if sql_overlay:
                            hint += f"\nSQL overlay table (partial/extended data): '{sql_overlay}'."
                        msg = hint
                        msg += f"\n\nExample: acore_data_query(name='{dbc_name}', id=118)"
                        msg += f"\nUse lookup(query='{bad_table}') for full field list."
                        return {"error": msg, "isError": True}

                suggestions = server.database._suggest_similar_tables(bad_table)

                if suggestions:
                    suggestion_info = []
                    for s in suggestions[:5]:
                        db_list = server.database._table_to_db_cache.get(s, [])
                        db_str = ", ".join(db_list) if db_list else "unknown"
                        suggestion_info.append(f"{s} ({db_str})")
                    msg += f"\n\nDid you mean: {', '.join(suggestion_info)}?"

                msg += f"\n\nUse lookup(query='{bad_table}') to verify table and get schema."
                msg += f"\nNote: Searched databases: {', '.join(server.database._db_priority_order)}"

            elif "Unknown column" in error:
                msg = f"Database query failed: {error}"
                col_match = re.search(
                    r"Unknown column '([^']+)' in '([^']*)'", error
                )
                if not col_match:
                    col_match = re.search(r"Unknown column '([^']+)'", error)

                if col_match:
                    bad_col = col_match.group(1)
                    from_match = re.search(
                        r'\bFROM\s+`?(\w+)`?', query, re.IGNORECASE
                    )
                    table_hint = (
                        from_match.group(1)
                        if from_match and from_match.group(1).upper() not in ("SELECT", "DUAL")
                        else None
                    )

                    if table_hint:
                        suggestion = server.database._suggest_column(table_hint, bad_col)
                        if suggestion:
                            msg += f"\n{suggestion}"

            return {"error": msg, "isError": True}

        return {"error": f"Database error: {error}", "isError": True}

    # Empty result hints
    if not rows:
        table_match = re.search(r'FROM\s+`?(\w+)`?', query, re.IGNORECASE)
        if table_match:
            tbl = table_match.group(1)
            if (
                "loot_template" in tbl.lower()
                and re.search(r"\bITEM\s*=|ITEM\s+=\s*\d+", query, re.IGNORECASE)
            ):
                hint = (
                    "No results. For quest items,"
                    " try gameobject_questitem or creature_questitem tables.\n"
                    "Use lookup(query='gameobject_questitem') to see schema."
                )
                return {"result": [], "count": 0, "hint": hint}

    return {"result": rows or [], "count": len(rows or [])}


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "sql",
        "description": (
            "Execute raw SQL query with smart database routing."
            " Automatically routes to correct database (acore_world, acore_characters, acore_auth)."
            " Provides typo suggestions for tables and columns."
            " Blocks destructive statements (DROP, TRUNCATE, ALTER, GRANT, REVOKE)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute (SELECT, INSERT, UPDATE, DELETE only)"
                }
            },
            "required": ["query"]
        }
    }
