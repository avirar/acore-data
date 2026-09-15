"""
Boot smoke tests: server.py must start and speak MCP JSON-RPC even with
NO AzerothCore install and NO database present (degraded SQL-only /
asset-less mode). This is the "stranger clones the repo" path, which is
exactly what CI verifies (CI runners have no install).

Run with: python3 tests/test_smoke.py (or pytest)
Works on both a clean machine and a full install.
"""

import json
import os
import subprocess
import sys
import unittest

SERVER_SCRIPT = "server.py"
TIMEOUT = 60

_WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV = {**os.environ, "PYTHONPATH": _WORKDIR}

EXPECTED_TOOLS = {
    "query", "lookup", "list", "spawns", "dbversion", "encounter",
    "travel", "explain", "config", "enums", "terrain", "sql",
}


def _raw(*payloads):
    """Send raw JSON-RPC lines to a fresh server, return stdout lines."""
    p = subprocess.run(
        [sys.executable, SERVER_SCRIPT],
        input="".join(json.dumps(x) + "\n" for x in payloads),
        capture_output=True,
        timeout=TIMEOUT,
        text=True,
        cwd=_WORKDIR,
        env=_ENV,
    )
    lines = [line for line in p.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(
            "server.py produced no stdout "
            f"(rc={p.returncode}); stderr tail:\n{p.stderr[-4000:]}"
        )
    return lines


class TestServerBoot(unittest.TestCase):
    """Server boots and answers basic MCP without any install present."""

    def test_initialize_echoes_protocol_version(self):
        lines = _raw({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        })
        m = json.loads(lines[0])
        self.assertEqual(m["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(m["result"]["serverInfo"]["name"], "acore-data")

    def test_tools_list_returns_full_toolset(self):
        lines = _raw({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                      "params": {}})
        m = json.loads(lines[0])
        names = {t["name"] for t in m["result"]["tools"]}
        self.assertEqual(names, EXPECTED_TOOLS)

    def test_tool_error_sets_mcp_iserror(self):
        """A failing tool call degrades to an MCP-level isError, not a crash."""
        lines = _raw({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "query",
                       "arguments": {"name": "NoSuchStoreXYZ"}},
        })
        m = json.loads(lines[0])
        self.assertTrue(m["result"].get("isError"))


def main():
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
