"""
Batch reference cache for resolver modules.

Provides a context manager that collects individual ref lookups across rows,
then flushes them as batch IN(...) queries. Dramatically reduces SQL round-trips.

Usage:
    with RefCache(server) as cache:
        name1 = cache.sql("creature_template", 123, "entry")
        name2 = cache.sql("creature_template", 456, "entry")
        spell1 = cache.dbc("Spell", 789)
    # After 'with' block, batch queries are executed automatically
"""
from typing import Any, Dict, List, Optional, Set, Tuple


class RefCache:
    """Caches reference lookups and flushes as batch queries on context exit."""

    def __init__(self, server):
        self._server = server
        # sql_batch: (table, id_col) -> set of IDs
        self._sql_batch: Dict[Tuple[str, str], Set[int]] = {}
        # dbc_batch: (dbc_name, id_col) -> set of IDs
        self._dbc_batch: Dict[Tuple[str, str], Set[int]] = {}
        # Result caches
        self._sql_cache: Dict[Tuple[str, str, int], Optional[str]] = {}
        self._dbc_cache: Dict[Tuple[str, str, int], Optional[str]] = {}
        self._flushed = False

    def sql(self, table: str, ref_id: int, id_col: str = "ID") -> Optional[str]:
        """Queue a SQL reference lookup (resolved on flush)."""
        cache_key = (table, id_col, ref_id)
        if cache_key in self._sql_cache:
            return self._sql_cache[cache_key]
        batch_key = (table, id_col)
        if batch_key not in self._sql_batch:
            self._sql_batch[batch_key] = set()
        self._sql_batch[batch_key].add(ref_id)
        # Don't resolve yet — wait for batch flush
        return None

    def dbc(self, dbc_name: str, ref_id: int, id_col: str = "ID") -> Optional[str]:
        """Queue a DBC reference lookup (resolved on flush)."""
        cache_key = (dbc_name, id_col, ref_id)
        if cache_key in self._dbc_cache:
            return self._dbc_cache[cache_key]
        batch_key = (dbc_name, id_col)
        if batch_key not in self._dbc_batch:
            self._dbc_batch[batch_key] = set()
        self._dbc_batch[batch_key].add(ref_id)
        return None

    def _flush(self):
        """Execute batch queries and populate result caches."""
        if self._flushed:
            return
        self._flushed = True

        # Flush SQL batch queries
        for (table, id_col), ids in self._sql_batch.items():
            if not ids:
                continue
            placeholders = ", ".join(["%s"] * len(ids))
            sql = f"SELECT {id_col}, name FROM {table} WHERE {id_col} IN ({placeholders})"
            try:
                rows, _ = self._server.database._query_database(sql, params=tuple(sorted(ids)))
                for row in rows:
                    rid = row.get(id_col)
                    name = row.get("name", "")
                    cache_key = (table, id_col, rid)
                    self._sql_cache[cache_key] = f"{table} [{name}]" if name else f"{table} [{rid}]"
                # Mark any IDs not found
                found_ids = {row.get(id_col) for row in rows}
                for rid in ids:
                    if rid not in found_ids and (table, id_col, rid) not in self._sql_cache:
                        self._sql_cache[(table, id_col, rid)] = f"{table} [{rid}] (not found)"
            except Exception:
                # On failure, fall back to individual lookups via direct query
                for rid in ids:
                    try:
                        rows2, _ = self._server.database._query_database(
                            f"SELECT * FROM {table} WHERE {id_col} = %s LIMIT 1",
                            params=(rid,),
                        )
                        cache_key = (table, id_col, rid)
                        if rows2:
                            row = rows2[0]
                            name = next((row[col] for col in ["name", "LogTitle", "entry", "ID"] if col in row and row[col]), None)
                            self._sql_cache[cache_key] = f"{table} [{name}]" if name else f"{table} [{rid}]"
                        else:
                            self._sql_cache[cache_key] = f"{table} [{rid}] (not found)"
                    except Exception:
                        self._sql_cache[(table, id_col, rid)] = None

        # Flush DBC batch lookups
        for (dbc_name, id_col), ids in self._dbc_batch.items():
            if not ids:
                continue
            try:
                reader = self._server._load_dbc(dbc_name)
                for ref_id in ids:
                    cache_key = (dbc_name, id_col, ref_id)
                    record = reader.get_record_by_id(ref_id)
                    if record:
                        for idx, value in record.items():
                            if isinstance(value, str) and value:
                                self._dbc_cache[cache_key] = f"{dbc_name} [{value}]"
                                break
                        else:
                            self._dbc_cache[cache_key] = f"{dbc_name} [{ref_id}]"
                    else:
                        self._dbc_cache[cache_key] = f"{dbc_name} [{ref_id}] (not found)"
            except Exception:
                for ref_id in ids:
                    self._dbc_cache[(dbc_name, id_col, ref_id)] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._flush()
        return False

    def resolve_sql(self, table: str, ref_id: int, id_col: str = "ID") -> Optional[str]:
        """Get cached SQL result (called after flush)."""
        return self._sql_cache.get((table, id_col, ref_id))

    def resolve_dbc(self, dbc_name: str, ref_id: int, id_col: str = "ID") -> Optional[str]:
        """Get cached DBC result (called after flush)."""
        return self._dbc_cache.get((dbc_name, id_col, ref_id))
