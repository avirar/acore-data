"""Scripting facade for acore-data.

Lets local Python scripts do bulk datastore work without MCP round-trips or
hand-rolled DBC loading. Run scripts with the repo venv (has pymysql):

    .venv/bin/python3 my_script.py

Example - map every character talent spell back to its talent tab:

    from core.api import open_store
    talents = open_store("Talent")
    spell_to_tab = {}
    for row in talents.find_iter():          # flat {field: value}
        for i in range(5):
            s = row.get(f"RankID[{i}]", 0)
            if s:
                spell_to_tab[s] = row["TalentTab"]

SQL (any configured database, smart-routed by table name when `db` is None):

    from core.api import sql
    rows = sql("SELECT id, name FROM quest_template WHERE RequiredItemId1 = %s", params=(12472,))
"""

import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.database import Database
from core.dbc import WDBCReader
from core.formats import FormatParser
from core.registry import Registry

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DBC_PATH = os.environ.get(
    "ACORE_DBC_PATH", os.environ.get("DBC_PATH", "/root/azerothcore-wotlk/env/dist/bin/dbc")
)
DEFAULT_FORMAT_FILE = os.environ.get(
    "ACORE_FORMAT_FILE",
    os.environ.get("DBC_FORMAT_FILE", "/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h"),
)

_registry: Optional[Registry] = None
_format_parser: Optional[FormatParser] = None
_database: Optional[Database] = None
_dbc_cache: Dict[str, WDBCReader] = {}


def registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry(str(_ROOT / "datastore_registry.json"))
    return _registry


def _formats() -> FormatParser:
    global _format_parser
    if _format_parser is None:
        _format_parser = FormatParser(DEFAULT_FORMAT_FILE)
        _format_parser.parse()
    return _format_parser


def _db() -> Database:
    global _database
    if _database is None:
        database = Database(
            db_host=os.environ.get("DB_HOST", ""),
            db_port=os.environ.get("DB_PORT", "3306"),
            db_user=os.environ.get("DB_USER", ""),
            db_password=os.environ.get("DB_PASSWORD", ""),
            db_name=os.environ.get("DB_NAME", "acore_world"),
        )
        if not database.db_host or not database.db_user:
            database._auto_detect_db_config()
        database._discover_all_tables()
        database._check_db_connection()
        _database = database
    return _database


def resolve(name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Resolve a datastore name (struct, table, DBC file, store variable)."""
    return registry()._resolve_entry(name)


class Store:
    """A loaded DBC store with name-resolved fields.

    Rows are flat ``{field_name: value}`` dicts, matching the MCP query tool.
    """

    def __init__(self, name: str, entry: Dict[str, Any], reader: WDBCReader):
        self.struct_name = name
        self.entry = entry
        self.reader = reader
        self._name_by_idx: Dict[int, str] = {
            int(k): v.get("name", k)
            for k, v in entry.get("fields", {}).items()
            if isinstance(v, dict)
        }
        self._idx_by_name: Dict[str, int] = {n: i for i, n in self._name_by_idx.items()}

    @property
    def record_count(self) -> int:
        return self.reader.record_count

    def field_names(self) -> Dict[str, int]:
        """Name -> field index for every annotated field."""
        return dict(self._idx_by_name)

    def index(self, field: Any) -> int:
        """Field index from a name (case-insensitive) or an explicit index."""
        if isinstance(field, int):
            return field
        idx = self._idx_by_name.get(field)
        if idx is None:
            lower = {n.lower(): i for n, i in self._idx_by_name.items()}
            idx = lower.get(str(field).lower())
        if idx is None:
            raise KeyError(f"{self.struct_name}: unknown field '{field}'")
        return idx

    def row(self, record: Dict[int, Any], compact: bool = True) -> Dict[str, Any]:
        """Flat dict for one record (drops null/zero when ``compact``)."""
        out: Dict[str, Any] = {}
        for idx, value in record.items():
            if compact and value in (None, 0, "", 0.0):
                continue
            out[self._name_by_idx.get(idx, str(idx))] = value
        return out

    def all(self, compact: bool = True) -> Iterator[Dict[str, Any]]:
        for record in self.reader.records:
            yield self.row(record, compact=compact)

    def by_id(self, id_value: int, compact: bool = True) -> Optional[Dict[str, Any]]:
        record = self.reader.get_record_by_id(id_value)
        return self.row(record, compact=compact) if record else None

    def find_iter(self, compact: bool = True, **filters: Any) -> Iterator[Dict[str, Any]]:
        """Iterate records matching ``field_name=value`` (exact)."""
        wanted = {self.index(k): v for k, v in filters.items()}
        for record in self.reader.records:
            if all(record.get(i) == v for i, v in wanted.items()):
                yield self.row(record, compact=compact)

    def find(self, compact: bool = True, limit: int = 0, **filters: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in self.find_iter(compact=compact, **filters):
            out.append(row)
            if limit and len(out) >= limit:
                break
        return out


def open_store(name: str) -> Store:
    """Load a DBC-backed datastore by any resolvable name."""
    resolved = resolve(name)
    if not resolved:
        raise KeyError(f"unknown datastore '{name}'")
    struct_name, entry = resolved
    if entry.get("category") != "dbc_backed":
        raise ValueError(f"'{struct_name}' is not DBC-backed (category={entry.get('category')})")
    dbc_name = entry.get("dbc_name") or struct_name
    if dbc_name not in _dbc_cache:
        fmt = _formats().get_format(dbc_name)
        if not fmt:
            raise ValueError(f"no DBC format string for '{dbc_name}'")
        reader = WDBCReader(str(Path(DEFAULT_DBC_PATH) / f"{dbc_name}.dbc"), fmt)
        reader.read()
        _dbc_cache[dbc_name] = reader
    return Store(struct_name, entry, _dbc_cache[dbc_name])


def sql(query: str, db: Optional[str] = None, params: tuple = ()) -> List[Dict[str, Any]]:
    """Run a SQL query, returning rows as dicts.

    ``db`` defaults to smart routing by table name (see Database._resolve_table_database).
    """
    rows, err = _db()._query_database(query, db_name=db, params=params)
    if err:
        raise RuntimeError(f"sql: {err}")
    return rows or []
