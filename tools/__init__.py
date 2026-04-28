"""
Tool modules for acore-data MCP server.

Four tools: query, lookup, list, sql
"""

from tools import query as query_tool
from tools import lookup as lookup_tool
from tools import list as list_tool
from tools import sql as sql_tool


def get_tool_schemas() -> list:
    """Get all tool schemas for MCP."""
    return [
        query_tool.get_schema(),
        lookup_tool.get_schema(),
        list_tool.get_schema(),
        sql_tool.get_schema(),
    ]
