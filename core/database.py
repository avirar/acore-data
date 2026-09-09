"""
Database module for acore-data.

Handles multi-database connections, table discovery, smart routing,
and SQL query execution. Uses pymysql for connection management.
Falls back to subprocess mysql CLI if pymysql is unavailable.
"""

import os
import sys
import json
import subprocess
import re
import difflib
from typing import Dict, Any, List, Optional, Tuple, Union, Set, Pattern
from pathlib import Path

try:
    import pymysql
    from decimal import Decimal as _DecimalType
    _USE_PYMYSQL = True
except ImportError:
    pymysql = None  # type: ignore[assignment]
    _USE_PYMYSQL = False
    print("Warning: pymysql not installed. Falling back to subprocess mysql CLI.", file=sys.stderr)

# Valid MySQL identifier pattern: letters, digits, underscores only.
# Enforced for table/column names which cannot use %s parameterization.
_SAFE_IDENTIFIER_RE: Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def _is_safe_identifier(name: str) -> bool:
    """Check that a table or column name contains only safe MySQL identifier chars."""
    return bool(_SAFE_IDENTIFIER_RE.match(name))


class Database:
    """Multi-database handler for AzerothCore."""

    def __init__(
        self,
        db_host: str = "",
        db_port: str = "3306",
        db_user: str = "",
        db_password: str = "",
        db_name: str = "acore_world"
    ):
        """Initialize database connection params."""
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.db_available = False

        # Table discovery cache
        self._all_tables_cache: Set[str] = set()
        self._db_tables_cache: Dict[str, Set[str]] = {}
        self._table_to_db_cache: Dict[str, List[str]] = {}
        self._schema_cache: Dict[Tuple[str, str], Optional[List[Dict]]] = {}
        self._pk_cache: Dict[str, str] = {}

        # Connection cache (pymysql)
        self._connections: Dict[str, Any] = {}

        # Database priority order for routing
        self._db_priority_order = [
            "acore_world", "acore_characters", "acore_auth", "acore_playerbots"
        ]

    def _auto_detect_db_config(self) -> None:
        """Auto-detect database config from worldserver.conf."""
        for conf_path in [
            Path("/root/azerothcore-wotlk/env/dist/etc/worldserver.conf"),
            Path.home() / "azerothcore-wotlk/env/dist/etc/worldserver.conf"
        ]:
            if not conf_path.exists():
                continue
            try:
                text = conf_path.read_text()
                m = re.search(
                    r'^WorldDatabaseInfo\s*=\s*"([^"]+)"', text, re.MULTILINE
                )
                if m:
                    parts = m.group(1).split(";")
                    if len(parts) >= 5:
                        self.db_host = parts[0]
                        self.db_port = parts[1]
                        self.db_user = parts[2]
                        self.db_password = parts[3]
                        self.db_name = parts[4]
                        print(f"Auto-detected DB config from {conf_path}", file=sys.stderr)
                        return
            except Exception:
                continue

        self.db_host = self.db_host or "localhost"
        self.db_user = self.db_user or "root"
        self.db_password = self.db_password or ""

    def _get_connection(self, db_name: str):
        """Get (or create) a pymysql connection for the given database."""
        if db_name not in self._connections:
            try:
                conn = pymysql.connect(
                    host=self.db_host,
                    port=int(self.db_port),
                    user=self.db_user,
                    password=self.db_password,
                    database=db_name,
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=10,
                    charset="utf8mb4",
                    autocommit=True,
                )
                self._connections[db_name] = conn
            except pymysql.err.OperationalError:
                # Connection failed — might be wrong credentials or down
                raise
        return self._connections[db_name]

    def _is_connection_alive(self, db_name: str) -> bool:
        """Check if a cached connection is still alive."""
        try:
            conn = self._connections.get(db_name)
            if conn is None:
                return False
            conn.ping(reconnect=False)
            return True
        except Exception:
            # Dead — remove so _get_connection retries
            self._connections.pop(db_name, None)
            return False

    def _check_db_connection(self) -> None:
        """Check if database connection is available."""
        rows, error = self._query_database("SELECT 1 AS test")
        if error:
            print(
                f"Warning: Database connection failed: {error}", file=sys.stderr
            )
            print(
                f"  DB config: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}",
                file=sys.stderr,
            )
            print(
                "  SQL queries will fail. Set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME env vars.",
                file=sys.stderr,
            )
            self.db_available = False
        else:
            self.db_available = True
            print(
                f"Database connected: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}",
                file=sys.stderr,
            )

    def _discover_all_tables(self) -> None:
        """Discover all tables across all AzerothCore databases."""
        if not self.db_available:
            print("Skipping table discovery (database unavailable)", file=sys.stderr)
            return

        databases = ["acore_world", "acore_characters", "acore_auth", "acore_playerbots"]
        total_tables = 0

        for db in databases:
            rows, error = self._query_database("SHOW TABLES", db_name=db)
            if error:
                print(f"  {db}: unavailable ({error[:50]}...)", file=sys.stderr)
                continue

            tables = set()
            for row in rows:
                table = list(row.values())[0].lower()
                tables.add(table)
                self._all_tables_cache.add(table)

                if table not in self._table_to_db_cache:
                    self._table_to_db_cache[table] = []
                self._table_to_db_cache[table].append(db)

            self._db_tables_cache[db] = tables
            total_tables += len(tables)
            print(f"  {db}: {len(tables)} tables", file=sys.stderr)

        # Sort databases by priority for overlapping tables
        for table in self._table_to_db_cache:
            dbs = self._table_to_db_cache[table]
            if len(dbs) > 1:
                self._table_to_db_cache[table] = sorted(
                    dbs,
                    key=lambda x: (
                        self._db_priority_order.index(x)
                        if x in self._db_priority_order
                        else 999
                    ),
                )

        print(
            f"Discovered {total_tables} tables across {len(self._db_tables_cache)} databases",
            file=sys.stderr,
        )

    def _resolve_table_database(
        self, table_name: str, current_db: Optional[str] = None
    ) -> Optional[str]:
        """Resolve table name to correct database using cache and priority order."""
        table_lower = table_name.lower()

        if table_lower in self._table_to_db_cache:
            candidates = self._table_to_db_cache[table_lower]
            if current_db and current_db in candidates:
                return current_db

            for db in self._db_priority_order:
                if db in candidates:
                    return db
            return candidates[0] if candidates else None

        if (
            current_db
            and self._db_tables_cache.get(current_db, set())
            and table_lower in self._db_tables_cache[current_db]
        ):
            return current_db

        return None

    def _normalize_value(self, val) -> Any:
        """Normalize pymysql value types to match previous subprocess behavior."""
        if isinstance(val, _DecimalType):
            # Convert Decimal to int (if whole) or float
            if val == val.to_integral_value():
                return int(val)
            return float(val)
        return val

    def _query_database(
        self, sql: str, db_name: Optional[str] = None, params: Optional[Tuple] = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Execute SQL query and return results with headers.

        Uses pymysql connections (persistent per database) when available,
        falls back to subprocess mysql CLI as a last resort.

        Args:
            sql: SQL query string with %s placeholders for parameterized values
            db_name: Target database name
            params: Optional tuple of values for %s placeholders
        """
        db = db_name or self.db_name

        if _USE_PYMYSQL:
            try:
                if not self._is_connection_alive(db):
                    self._connections.pop(db, None)

                conn = self._get_connection(db)
                cur = conn.cursor()
                try:
                    if params:
                        cur.execute(sql, params)
                    else:
                        cur.execute(sql)
                    rows = cur.fetchall()
                finally:
                    cur.close()

                result = []
                for row in rows:
                    result.append({k: self._normalize_value(v) for k, v in row.items()})
                return result, None

            except Exception as e:
                self._connections.pop(db, None)
                return None, str(e)

        # Fallback: subprocess mysql CLI (when pymysql is not available)
        try:
            # Interpolate %s placeholders so parameterized queries work without pymysql.
            # Values are escaped before interpolation to avoid quoting breakage.
            if params:
                values = list(params)
                lit = []
                for v in values:
                    if v is None:
                        lit.append("NULL")
                    elif isinstance(v, bool):
                        lit.append("1" if v else "0")
                    elif isinstance(v, (int, float)):
                        lit.append(repr(v))
                    else:
                        escaped = str(v).replace("\\", "\\\\").replace("'", "\\'")
                        lit.append(f"'{escaped}'")
                idx = [0]

                def _sub(_m):
                    val = lit[idx[0]]
                    idx[0] += 1
                    return val

                sql = re.sub(r"%s", _sub, sql)

            cli_env = {**os.environ, "MYSQL_PWD": self.db_password}
            cmd = [
                "mysql",
                "-h",
                self.db_host,
                "-P",
                self.db_port,
                "-u",
                self.db_user,
                "-D",
                db,
                "-e",
                sql,
                "--batch",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15, env=cli_env
            )

            if result.returncode != 0:
                return None, result.stderr.strip()

            output = result.stdout.strip()
            if not output:
                return [], None

            lines = output.split("\n")
            if len(lines) < 2:
                return [], None

            # First line is headers
            columns = [c.strip() for c in lines[0].split("\t")]

            # Remaining lines are data
            rows = []
            for line in lines[1:]:
                if not line:
                    continue
                values = line.split("\t")
                row = {}
                for i, val in enumerate(values):
                    col_name = columns[i] if i < len(columns) else str(i)
                    # Convert numeric values
                    try:
                        row[col_name] = int(val)
                    except ValueError:
                        try:
                            row[col_name] = float(val)
                        except ValueError:
                            row[col_name] = val
                rows.append(row)

            return rows, None

        except subprocess.TimeoutExpired:
            return None, "Database query timed out"
        except Exception as e:
            return None, str(e)

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query."""
        tables = []

        # FROM clause
        from_match = re.search(r"\bFROM\s+(\w+)", sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1).lower())

        # JOIN clauses
        join_matches = re.findall(r"\bJOIN\s+(\w+)", sql, re.IGNORECASE)
        tables.extend(t.lower() for t in join_matches)

        return tables

    def _suggest_similar_tables(self, table_name: str) -> List[str]:
        """Suggest similar table names using prefix/suffix/substring matching."""
        table_lower = table_name.lower()
        suggestions = set()

        exact_matches = difflib.get_close_matches(
            table_lower, self._all_tables_cache, n=5, cutoff=0.6
        )
        for t in exact_matches:
            suggestions.add(t)

        words = table_lower.replace("_", " ").split()
        for word in words:
            if len(word) >= 3:
                prefix_matches = [
                    t for t in self._all_tables_cache if t.startswith(word)
                ]
                suffix_matches = [
                    t for t in self._all_tables_cache if t.endswith(word)
                ]
                substr_matches = [
                    t
                    for t in self._all_tables_cache
                    if word in t.replace("_", " ")
                ]
                suggestions.update(prefix_matches[:5])
                suggestions.update(suffix_matches[:5])
                suggestions.update(substr_matches[:5])

        sorted_suggestions = sorted(
            suggestions,
            key=lambda x: difflib.SequenceMatcher(None, table_lower, x).ratio(),
            reverse=True,
        )

        return list(sorted(set(sorted_suggestions[:5])))

    def _get_table_schema(self, table_name: str, db_name: Optional[str] = None) -> Optional[List[Dict]]:
        """Get column info from INFORMATION_SCHEMA, cached per (db, table)."""
        if not self.db_available:
            return None

        db = db_name or self._resolve_table_database(table_name, self.db_name) or self.db_name
        cache_key = (db, table_name)

        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        self._schema_cache[cache_key] = None

        pk_rows, _ = self._query_database(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "AND CONSTRAINT_NAME = 'PRIMARY'",
            params=(db, table_name),
        )
        pk_col = pk_rows[0]["COLUMN_NAME"] if pk_rows else None

        rows, _ = self._query_database(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            params=(db, table_name),
        )

        if rows:
            for r in rows:
                r["is_primary_key"] = (
                    (r["COLUMN_NAME"] == pk_col)
                    if pk_col
                    else (r.get("COLUMN_KEY") == "PRI")
                )
            self._schema_cache[cache_key] = rows[:50]

        return self._schema_cache[cache_key]

    def _suggest_column(self, table_name: str, bad_col: str, db_name: Optional[str] = None) -> Optional[str]:
        """Find similar column names when a query fails on Unknown column."""
        schema = self._get_table_schema(table_name, db_name)
        if not schema:
            return None

        columns = [c["COLUMN_NAME"] for c in schema]
        bad_lower = bad_col.lower()

        suggestions = [c for c in columns if c.lower() == bad_lower]
        if not suggestions:
            suggestions = [
                c for c in columns if bad_lower in c.lower() or c.lower() in bad_lower
            ]
        if not suggestions:
            suggestions = [c for c in columns if c.lower().startswith(bad_lower[:3])]

        if suggestions:
            return f"Column '{bad_col}' not found in '{table_name}'. " f"Similar columns: {', '.join(suggestions[:8])}."
        return f"Column '{bad_col}' not found in '{table_name}'. " f"Available columns: {', '.join(columns[:30])}"

    def _find_primary_key(self, reg_entry: Dict, sql_table: str, db_name: Optional[str] = None) -> str:
        """Try to determine the primary key column name from registry fields."""
        fields = reg_entry.get("fields", {})
        if "0" in fields:
            f = fields["0"]
            col = f.get("sql_column", "") or f.get("name", "")
            if col:
                return col

        if sql_table not in self._pk_cache:
            schema = self._get_table_schema(sql_table, db_name)
            if schema:
                for c in schema:
                    if c.get("is_primary_key"):
                        self._pk_cache[sql_table] = c["COLUMN_NAME"]
                        break
                else:
                    self._pk_cache[sql_table] = schema[0]["COLUMN_NAME"] if schema else "entry"
            else:
                self._pk_cache[sql_table] = "entry"

        return self._pk_cache.get(sql_table, "entry")
