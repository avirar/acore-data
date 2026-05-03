"""
Shared reference resolution utilities for resolver modules.

Provides functions to resolve DBC references, SQL references, and loot templates
by ID. Used by all table-specific resolver modules. Includes optional per-request
memoization and persistent TTL cache to avoid duplicate lookups across requests.
"""
import time
from typing import Any, Dict, Optional, Tuple

# Module-level cache for per-request memoization. Set via set_ref_cache() before
# a batch of resolve calls, then cleared via clear_ref_cache() afterward.
_active_cache: Optional[Dict[str, str]] = None

# Persistent TTL cache that survives across requests.
_PERSISTENT_CACHE: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes
_CACHE_MAX = 2000


def _get_persistent(key: str) -> Optional[str]:
    """Get a value from the persistent TTL cache."""
    if key in _PERSISTENT_CACHE:
        value, expiry = _PERSISTENT_CACHE[key]
        if time.time() < expiry:
            return value
        del _PERSISTENT_CACHE[key]
    return None


def _set_persistent(key: str, value: str) -> None:
    """Store a value in the persistent TTL cache."""
    if len(_PERSISTENT_CACHE) >= _CACHE_MAX:
        now = time.time()
        expired = [k for k, (_, exp) in _PERSISTENT_CACHE.items() if now >= exp]
        for k in expired:
            del _PERSISTENT_CACHE[k]
        if len(_PERSISTENT_CACHE) >= _CACHE_MAX:
            keys = list(_PERSISTENT_CACHE.keys())[:_CACHE_MAX // 4]
            for k in keys:
                del _PERSISTENT_CACHE[k]
    _PERSISTENT_CACHE[key] = (value, time.time() + _CACHE_TTL)


def invalidate_persistent_cache() -> None:
    """Clear the persistent TTL cache. Useful for manual cache invalidation."""
    _PERSISTENT_CACHE.clear()


def set_ref_cache(cache: Dict[str, str]) -> None:
    """Set the active cache dict for per-request memoization."""
    global _active_cache
    _active_cache = cache


def clear_ref_cache() -> None:
    """Clear the active cache reference after a resolve operation completes."""
    global _active_cache
    _active_cache = None


def _cache_key_sql(table: str, ref_id: int, id_col: str) -> str:
    return f"sql:{table}:{ref_id}:{id_col}"


def _cache_key_dbc(dbc_name: str, ref_id: int, id_col: str) -> str:
    return f"dbc:{dbc_name}:{ref_id}:{id_col}"


def resolve_dbc_ref(
    server,
    dbc_name: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve a DBC reference by ID to its name/title."""
    key = _cache_key_dbc(dbc_name, ref_id, id_col)

    # Check persistent cache first
    cached = _get_persistent(key)
    if cached is not None:
        return cached

    # Check per-request cache
    if _active_cache is not None and key in _active_cache:
        return _active_cache[key]

    try:
        reader = server._load_dbc(dbc_name)

        record = reader.get_record_by_id(ref_id)
        if not record:
            result = f"{dbc_name} [{ref_id}] (not found)"
        else:
            for idx, value in record.items():
                if isinstance(value, str) and value:
                    result = f"{dbc_name} [{value}]"
                    break
            else:
                result = f"{dbc_name} [{ref_id}]"
    except Exception:
        return None

    # Store in both caches
    _set_persistent(key, result)
    if _active_cache is not None:
        _active_cache[key] = result

    return result


def resolve_sql_ref(
    server,
    table: str,
    ref_id: int,
    id_col: str = "ID",
) -> Optional[str]:
    """Resolve an SQL reference by ID to its key identifying field."""
    key = _cache_key_sql(table, ref_id, id_col)

    # Check persistent cache first
    cached = _get_persistent(key)
    if cached is not None:
        return cached

    # Check per-request cache
    if _active_cache is not None and key in _active_cache:
        return _active_cache[key]

    try:
        rows, _ = server.database._query_database(
            f"SELECT * FROM {table} WHERE {id_col} = %s LIMIT 1",
            params=(ref_id,),
        )

        if rows:
            row = rows[0]
            for col in ["name", "LogTitle", "entry", "ID"]:
                if col in row and row[col]:
                    result = f"{table} [{row[col]}]"
                    break
            else:
                result = f"{table} [{ref_id}]"
        else:
            result = f"{table} [{ref_id}] (not found)"
    except Exception:
        return None

    # Store in both caches
    _set_persistent(key, result)
    if _active_cache is not None:
        _active_cache[key] = result

    return result


def batch_resolve_sql(
    server,
    table: str,
    ids: list,
    id_col: str = "ID",
) -> Dict[int, str]:
    """Resolve multiple SQL references in a single query.

    Returns dict mapping {id: "table [name]"} for each found ID,
    and {id: "table [id] (not found)"} for IDs not found.
    """
    if not ids:
        return {}

    placeholder = "%s"
    placeholders = ", ".join([placeholder] * len(ids))

    query = f"SELECT {id_col}, name, LogTitle, entry FROM {table} WHERE {id_col} IN ({placeholders})"

    try:
        rows, _ = server.database._query_database(query, params=tuple(ids))
    except Exception:
        return {}

    found = {}
    for row in (rows or []):
        row_id = row.get(id_col)
        if row_id is None:
            continue
        name_val = None
        for col in ["name", "LogTitle", "entry"]:
            if col in row and row[col]:
                name_val = row[col]
                break
        found[row_id] = f"{table} [{name_val}]" if name_val else f"{table} [{row_id}]"

    for rid in ids:
        if rid not in found:
            found[rid] = f"{table} [{rid}] (not found)"

    return found


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
