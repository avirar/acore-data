"""
Core modules for acore-data MCP server.

Modules:
  - dbc: WDBC file reader with ID index
  - formats: DBCfmt.h parser
  - registry: Datastore metadata and name resolution
  - database: Multi-database connection and routing
  - annotation: Record annotation and error formatting
"""

from core.dbc import WDBCReader
from core.formats import FormatParser
from core.registry import Registry
from core.database import Database
from core.annotation import (
    _annotate_dbc_result,
    _annotate_single_record,
    _build_schema_error,
    _dbc_filter_to_sql_where,
)
