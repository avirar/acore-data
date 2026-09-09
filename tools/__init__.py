"""
Tool modules for acore-data MCP server.

Eight tools: query, lookup, list, spawns, dbversion, travel, sql, terrain
"""
import os

from tools import query as query_tool
from tools import lookup as lookup_tool
from tools import list as list_tool
from tools import spawns as spawns_tool
from tools import dbversion as dbversion_tool
from tools import travel as travel_tool
from tools import sql as sql_tool
from tools import terrain as terrain_tool


# SQL tool mode: full (default), readonly, disabled
_SQL_MODE = os.environ.get("ACORE_SQL_TOOL_MODE", "full").lower()


def get_sql_mode() -> str:
    """Get current SQL tool mode."""
    return _SQL_MODE


def get_tool_schemas() -> list:
    """Get all tool schemas for MCP."""
    schemas = [
        query_tool.get_schema(),
        lookup_tool.get_schema(),
        list_tool.get_schema(),
        spawns_tool.get_schema(),
        dbversion_tool.get_schema(),
        travel_tool.get_schema(),
        terrain_tool.get_schema(),
    ]

    # Only include sql tool if not disabled
    if _SQL_MODE != "disabled":
        schemas.append(sql_tool.get_schema())

    return schemas
