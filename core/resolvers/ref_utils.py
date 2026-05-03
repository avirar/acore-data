"""
Shared reference resolution utilities for resolver modules.

Provides functions to resolve DBC references, SQL references, and loot templates
by ID. Used by all table-specific resolver modules.
"""
from typing import Any, Dict, Optional


def resolve_dbc_ref(
    server,
    dbc_name: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve a DBC reference by ID to its name/title."""
    try:
        reader = server._load_dbc(dbc_name)

        record = reader.get_record_by_id(ref_id)
        if not record:
            return f"{dbc_name} [{ref_id}] (not found)"

        # Try to find a name/title string field
        for idx, value in record.items():
            if isinstance(value, str) and value:
                return f"{dbc_name} [{value}]"

        # No string name found - return ID-based reference
        return f"{dbc_name} [{ref_id}]"
    except Exception:
        return None


def resolve_sql_ref(
    server,
    table: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve an SQL reference by ID to its key identifying field."""
    try:
        rows, _ = server.database._query_database(
            f"SELECT * FROM {table} WHERE {id_col} = %s LIMIT 1",
            params=(ref_id,),
        )

        if rows:
            row = rows[0]
            # Find a meaningful identifier from the result
            for col in ["name", "LogTitle", "entry", "ID"]:
                if col in row and row[col]:
                    return f"{table} [{row[col]}]"
            return f"{table} [{ref_id}]"

        return f"{table} [{ref_id}] (not found)"
    except Exception:
        return None


def resolve_loot_ref(
    server,
    table: str,
    loot_id: int,
    id_col: str = "Entry",
    resolve_max: int = 10,
) -> Optional[Dict[str, Any]]:
    """Resolve a loot template reference to item list."""
    try:
        items, _ = server.database._query_database(
            f"SELECT Item, Chance, MinCount, MaxCount FROM {table} WHERE {id_col} = %s",
            params=(loot_id,),
        )

        if not items:
            return {"resolved_to": f"{table} [{loot_id}]", "warning": "Empty loot template"}

        total_items = len(items)
        display_items = []

        for item_row in items[:resolve_max]:
            item_id = item_row.get("Item", 0)
            if not item_id:
                continue

            # Resolve item name
            item_rows, _ = server.database._query_database(
                "SELECT entry, name FROM item_template WHERE entry = %s LIMIT 1",
                params=(item_id,),
            )
            item_name = ""
            if item_rows:
                item_name = item_rows[0].get("name", "")

            display_items.append({
                "Item": item_id,
                "name": item_name,
                "Chance": item_row.get("Chance", 100),
                "MinCount": item_row.get("MinCount", 1),
                "MaxCount": item_row.get("MaxCount", 1),
            })

        result = {
            "resolved_to": f"{table} [{loot_id}]",
            "items": display_items,
        }

        if resolve_max and total_items > resolve_max:
            result["warning"] = (
                f"Loot template has {total_items} items, showing first {resolve_max}. "
                f"Use resolve_max=0 to show all."
            )

        return result
    except Exception:
        return None
