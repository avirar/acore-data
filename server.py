#!/usr/bin/env python3
"""
acore-data MCP Server

Unified data query tool for AzerothCore World of Warcraft server.
Provides access to all game datastores: DBC binary files, SQL tables, and overlays.

Version: 1.0.0
"""

import difflib
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import core modules
from core.formats import FormatParser
from core.registry import Registry
from core.database import Database
from core.dbc import WDBCReader

# Import tools
from tools import get_tool_schemas


class AcoreDataServer:
    """MCP server for querying AzerothCore datastores."""

    def __init__(self):
        # Environment variables with fallbacks
        self.dbc_path = Path(
            os.environ.get("ACORE_DBC_PATH", os.environ.get("DBC_PATH", "/root/azerothcore-wotlk/env/dist/bin/dbc"))
        )
        self.format_file = os.environ.get(
            "ACORE_FORMAT_FILE",
            os.environ.get("DBC_FORMAT_FILE", "/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h"),
        )

        # Database config
        db_host = os.environ.get("DB_HOST", "")
        db_port = os.environ.get("DB_PORT", "3306")
        db_user = os.environ.get("DB_USER", "")
        db_password = os.environ.get("DB_PASSWORD", "")
        db_name = os.environ.get("DB_NAME", "acore_world")

        # Initialize core modules
        self.format_parser = FormatParser(self.format_file)
        self.format_parser.parse()

        registry_path = Path(__file__).parent / "datastore_registry.json"
        self.registry = Registry(str(registry_path))
        self.registry._field_name_cache = self.registry._build_field_name_cache()

        self.database = Database(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
        )

        if not self.database.db_host or not self.database.db_user:
            self.database._auto_detect_db_config()

        # Terrain data paths
        data_base = Path(os.environ.get(
            "ACORE_DATA_PATH",
            os.environ.get("DATA_PATH", "/root/azerothcore-wotlk/env/dist/bin"),
        ))
        self.maps_path = data_base / "maps"
        self.vmaps_path = data_base / "vmaps"
        self.mmaps_path = data_base / "mmaps"

        # Cache for DBC readers
        self.dbc_cache: Dict[str, WDBCReader] = {}

        # Initialize database connection and discovery
        self.database._check_db_connection()
        self.database._discover_all_tables()

    def _load_dbc(self, dbc_name: str) -> WDBCReader:
        """Load DBC file with caching."""
        if dbc_name in self.dbc_cache:
            return self.dbc_cache[dbc_name]

        format_string = self.format_parser.get_format(dbc_name)
        if not format_string:
            raise ValueError(f"No format found for DBC: {dbc_name}")

        # Try exact path first, then case-insensitive search
        dbc_file = self.dbc_path / f"{dbc_name}.dbc"
        if not dbc_file.exists():
            dbc_name_lower = dbc_name.lower()
            for f in self.dbc_path.glob("*.dbc"):
                if f.stem.lower() == dbc_name_lower:
                    dbc_file = f
                    break

        if not dbc_file.exists():
            raise FileNotFoundError(f"DBC file not found: {dbc_name}.dbc")

        reader = WDBCReader(str(dbc_file), format_string)
        reader.read()
        self.dbc_cache[dbc_name] = reader
        return reader

    def _list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return get_tool_schemas()

    def _validate_arguments(self, name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Reject unknown argument keys with suggestions (prevents silent no-ops)."""
        try:
            schema = next(s for s in self._list_tools() if s.get("name") == name)
        except StopIteration:
            return None
        known = set(schema.get("inputSchema", {}).get("properties", {}).keys())
        if not known:
            return None
        unknown = [k for k in arguments if k not in known]
        if not unknown:
            return None
        u = str(unknown[0])
        sugg = difflib.get_close_matches(u.lower(), [k.lower() for k in known], n=3, cutoff=0.4)
        msg = f"Unknown argument '{u}' for tool '{name}'."
        if len(unknown) > 1:
            msg += f" Unknown arguments: {', '.join(map(str, unknown))}."
        if sugg:
            msg += f" Did you mean: {', '.join(sugg)}?"
        else:
            msg += f" Valid arguments: {', '.join(sorted(known))}."
        return {"error": msg, "isError": True}

    def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool call to appropriate handler."""
        self.args = arguments

        invalid = self._validate_arguments(name, arguments)
        if invalid:
            return invalid

        if name == "query":
            from tools import query as query_tool
            return query_tool.query_tools(self)

        elif name == "lookup":
            from tools import lookup as lookup_tool
            return lookup_tool.lookup_tools(self)

        elif name == "list":
            from tools import list as list_tool
            return list_tool.list_tools(self)

        elif name == "sql":
            from tools import sql as sql_tool
            return sql_tool.sql_tools(self)

        elif name == "encounter":
            from tools import encounter as encounter_tool
            return encounter_tool.encounter_tools(self)

        elif name == "travel":
            from tools import travel as travel_tool
            return travel_tool.travel_tools(self)

        elif name == "dbversion":
            from tools import dbversion as dbversion_tool
            return dbversion_tool.dbversion_tools(self)

        elif name == "spawns":
            from tools import spawns as spawns_tool
            return spawns_tool.spawns_tools(self)

        elif name == "terrain":
            from tools import terrain as terrain_tool
            return terrain_tool.terrain_tools(self)

        else:
            return {
                "error": f"Unknown tool: {name}",
                "isError": True,
            }

    def run(self):
        """Main MCP server loop."""
        print("acore-data MCP server starting...", file=sys.stderr)
        print(f"  DBC path: {self.dbc_path}", file=sys.stderr)
        print(f"  Format file: {self.format_file}", file=sys.stderr)
        print(f"  Maps path: {self.maps_path}", file=sys.stderr)
        print(f"  VMaps path: {self.vmaps_path}", file=sys.stderr)
        print(f"  MMaps path: {self.mmaps_path}", file=sys.stderr)
        print(f"  Tools: query, lookup, list, spawns, dbversion, encounter, travel, terrain, sql", file=sys.stderr)

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())

                # Notifications carry no id and expect no response
                if request.get("method", "").startswith("notifications/"):
                    continue

                if request.get("method") == "initialize":
                    client_params = request.get("params", {}) or {}
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": client_params.get(
                                "protocolVersion", "2024-11-05"
                            ),
                            "serverInfo": {
                                "name": "acore-data",
                                "version": "1.0.0",
                            },
                            "capabilities": {"tools": {}},
                        },
                    }

                elif request.get("method") == "tools/list":
                    tools = self._list_tools()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {"tools": tools},
                    }

                elif request.get("method") == "tools/call":
                    params = request.get("params", {})
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})

                    result = self._call_tool(tool_name, tool_args)
                    call_result = {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                    if isinstance(result, dict) and result.get("isError"):
                        call_result["isError"] = True
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": call_result,
                    }

                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {request.get('method')}",
                        },
                    }

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                sys.stdout.write(
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": str(e)},
                    }) + "\n"
                )
                sys.stdout.flush()

            except KeyboardInterrupt:
                break

            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if "request" in locals() else None,
                    "error": {"code": -32000, "message": str(e)},
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def main():
    """Entry point."""
    server = AcoreDataServer()
    server.run()


if __name__ == "__main__":
    main()
