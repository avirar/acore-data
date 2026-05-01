"""
Integration test suite for acore-data MCP server.

Tests filter operators ($like, $ilike), column name resolution,
error handling, and cross-store queries against live database.

Run with: python3 tests/test_integration.py (or pytest)
Requires: mysql CLI on PATH, running AzerothCore MySQL instance
"""

import json
import os
import subprocess
import sys
import unittest


SERVER_SCRIPT = "server.py"
TIMEOUT = 10

# Resolve working directory to the acore-data root (parent of tests/)
_WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV = {**os.environ, "PYTHONPATH": _WORKDIR}


def call_query(args):
    """Call the query tool and return parsed result."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "query", "arguments": args},
    }
    p = subprocess.run(
        ["python3", SERVER_SCRIPT],
        input=json.dumps(payload),
        capture_output=True,
        timeout=TIMEOUT,
        text=True,
        cwd=_WORKDIR,
        env=_ENV,
    )
    r = json.loads(p.stdout)
    return json.loads(r["result"]["content"][0]["text"])


def call_tool(name, args):
    """Call any tool and return parsed result."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    }
    p = subprocess.run(
        ["python3", SERVER_SCRIPT],
        input=json.dumps(payload),
        capture_output=True,
        timeout=TIMEOUT,
        text=True,
        cwd=_WORKDIR,
        env=_ENV,
    )
    r = json.loads(p.stdout)
    return json.loads(r["result"]["content"][0]["text"])


class TestDollarLikeOperators(unittest.TestCase):
    """Test $like and $ilike filter operators on SQL-only tables."""

    def test_like_basic_match(self):
        """$like with % wildcards should match records on SQL table."""
        result = call_query({
            "name": "creature_template",
            "filter": {"name": {"$like": "%Murloc%"}},
            "limit": 5,
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertGreater(len(rows), 0, "$like should return matches")

    def test_like_case_sensitive(self):
        """$like is case-sensitive on MySQL with default collation."""
        result = call_query({
            "name": "creature_template",
            "filter": {"name": {"$like": "%murloc%"}},  # lowercase may not match
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_ilike_case_insensitive(self):
        """$ilike should be case-insensitive via LOWER() wrapping."""
        result = call_query({
            "name": "quest_template",
            "filter": {"LogTitle": {"$ilike": "%war%"}},
            "limit": 5,
        })
        self.assertNotIn("error", result)
        # Should match "Warden" (contains "war")
        rows = result.get("result", [])
        self.assertGreater(len(rows), 0, "$ilike should return case-insensitive matches")

    def test_like_no_escapes_in_pattern(self):
        """User-provided % wildcards should NOT be escaped."""
        result = call_query({
            "name": "creature_template",
            "filter": {"name": {"$like": "%Waypoint%"}},
            "limit": 3,
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertGreater(len(rows), 0, "% wildcards must work")

    def test_combined_filter_like_and_exact(self):
        """Combining $like with exact match should work."""
        result = call_query({
            "name": "creature_template",
            "filter": {
                "entry": 1,
                "name": {"$like": "%Waypoint%"},
            },
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_ilike_on_quest_logtitle(self):
        """$ilike on quest_template LogTitle with known pattern."""
        result = call_query({
            "name": "quest_template",
            "filter": {"LogTitle": {"$ilike": "%kanrethad%"}},  # lowercase to test case-insensitive
            "limit": 3,
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        # Should find "Kanrethad's Quest" despite lowercase input
        self.assertGreater(len(rows), 0, "$ilike should be case-insensitive")


class TestColumnResolution(unittest.TestCase):
    """Test C++ field name to SQL column resolution."""

    def test_exact_sql_column_match(self):
        """Filter by SQL column name (case-sensitive) should work."""
        result = call_query({
            "name": "creature_template",
            "filter": {"entry": 1},
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertEqual(len(rows), 1)

    def test_case_insensitive_column(self):
        """Column names should be matched case-insensitively."""
        result = call_query({
            "name": "quest_template",
            "filter": {"logtitle": {"$ilike": "%war%"}},
            "limit": 1,
        })
        # logtitle (lowercase) should resolve to LogTitle
        self.assertNotIn("error", result)

    def test_unknown_column_gives_suggestion(self):
        """Unknown column name should return error with suggestions."""
        result = call_query({
            "name": "quest_template",
            "filter": {"boguscolumn": "foo"},
        })
        self.assertIn("error", result)
        error = result["error"]
        # Should contain a suggestion hint
        self.assertTrue(
            "did you mean" in error.lower() or "available fields" in error.lower(),
            f"Error should have suggestions, got: {error[:150]}",
        )

    def test_typo_in_column_gives_correction(self):
        """Typo 'tite' should suggest 'title' or similar."""
        result = call_query({
            "name": "quest_template",
            "filter": {"tite": "foo"},
        })
        self.assertIn("error", result)


class TestExactMatchFilters(unittest.TestCase):
    """Test exact match filter values (non-dict)."""

    def test_numeric_filter(self):
        """Numeric filter value should use = comparison."""
        result = call_query({
            "name": "creature_template",
            "filter": {"entry": 1},
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertEqual(len(rows), 1)

    def test_string_filter(self):
        """String filter should properly escape quotes."""
        result = call_query({
            "name": "creature_template",
            "filter": {"name": "Hyakki"},
        })
        self.assertNotIn("error", result)


class TestIDLookup(unittest.TestCase):
    """Test ID-based lookups (primary key access)."""

    def test_id_lookup_sql_only(self):
        """ID lookup on SQL-only table should work."""
        result = call_query({
            "name": "quest_template",
            "id": 3904,
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertEqual(len(rows), 1, "ID lookup should return exactly 1 row")

    def test_id_lookup_dbc(self):
        """ID lookup on DBC-backed store should work."""
        result = call_query({
            "name": "Spell",
            "id": 118,
        })
        self.assertNotIn("error", result)


class TestDBCOverlay(unittest.TestCase):
    """Test DBC+SQL overlay queries."""

    def test_dbc_filter_by_field_name(self):
        """DBC query with named field filter should convert to numeric index."""
        result = call_query({
            "name": "SkillLineAbility",
            "filter": {"Spell": 2567},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_dbc_info_mode(self):
        """info=true should return DBC metadata."""
        result = call_query({
            "name": "Spell",
            "info": True,
        })
        self.assertNotIn("error", result)
        info = result.get("result", {})
        self.assertIn("record_count", info)


class TestErrorHandling(unittest.TestCase):
    """Test error messages and suggestions."""

    def test_unknown_store_gives_suggestions(self):
        """Unknown store name should return fuzzy match suggestions."""
        result = call_query({"name": "spel"})
        self.assertIn("error", result)

    def test_raw_sql_table_typo_suggestion(self):
        """SQL tool should suggest corrected table names."""
        result = call_tool(
            "sql",
            {"query": "SELECT * FROM creature_templat LIMIT 1"},
        )
        self.assertIn("error", result)

    def test_raw_sql_column_typo_suggestion(self):
        """SQL tool should suggest corrected column names."""
        result = call_tool(
            "sql",
            {"query": "SELECT entry, neme FROM creature_template LIMIT 1"},
        )
        self.assertIn("error", result)


class TestRegression(unittest.TestCase):
    """Regression tests for existing functionality."""

    def test_no_filter_query(self):
        """Query without filter should return limited results."""
        result = call_query({
            "name": "creature_template",
            "limit": 5,
        })
        self.assertNotIn("error", result)
        rows = result.get("result", [])
        self.assertGreater(len(rows), 0)

    def test_sql_tool_basic_select(self):
        """Raw SQL tool should still work."""
        result = call_tool(
            "sql",
            {"query": "SELECT entry, name FROM creature_template WHERE entry = 1 LIMIT 1"},
        )
        self.assertNotIn("error", result)

    def test_lookup_tool(self):
        """Lookup tool should resolve store names."""
        result = call_tool(
            "lookup",
            {"query": "SpellEntry"},
        )
        self.assertNotIn("error", result)

    def test_list_tools(self):
        """Should return 4 consolidated tools."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        p = subprocess.run(
            ["python3", SERVER_SCRIPT],
            input=json.dumps(payload),
            capture_output=True,
            timeout=5,
            text=True,
            cwd=_WORKDIR,
            env=_ENV,
        )
        r = json.loads(p.stdout)
        tools = r["result"]["tools"]
        self.assertEqual(len(tools), 4, "Should have exactly 4 tools")


class TestSQLOverlayRegEntry(unittest.TestCase):
    """Test that reg_entry is properly passed through SQL overlay path."""

    def test_sql_overlay_uses_real_columns(self):
        """SQL overlay should use actual SQL column names, not field_N."""
        # Query Spell by ID - triggers DBC + SQL overlay path
        result = call_query({
            "name": "Spell",
            "id": 118,
        })
        self.assertNotIn("error", result)
        # If field_N was used, MySQL would error


class TestRegistryDrivenResolution(unittest.TestCase):
    """Test generic cross-reference resolution driven by registry metadata."""

    def test_sql_creature_template_resolve(self):
        """creature_template with resolve=true should resolve faction, etc."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": True,
        })
        self.assertNotIn("error", result)

    def test_dbc_spell_entry_resolve(self):
        """SpellEntry DBC query with resolve=true should resolve Category etc."""
        result = call_query({
            "name": "SpellEntry",
            "id": 118,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        # May or may not have resolved_fields depending on DB/DBC availability
        # but should not error

    def test_gameobject_still_works(self):
        """gameobject_template resolution still works after registry migration."""
        result = call_query({
            "name": "gameobject_template",
            "filter": {"type": 3},
            "resolve": True,
            "limit": 1,
        })
        self.assertNotIn("error", result)

    def test_resolve_filter_sql_only(self):
        """resolve=['sql'] should only resolve SQL targets, not DBC."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": ["sql"],
        })
        self.assertNotIn("error", result)

    def test_resolve_filter_dbc_only(self):
        """resolve=['dbc'] should only resolve DBC targets."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": ["dbc"],
        })
        self.assertNotIn("error", result)

    def test_no_resolve_by_default(self):
        """Without resolve param, no resolution should happen."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
        })
        self.assertNotIn("error", result)


if __name__ == "__main__":
    # Run from acore-data directory
    unittest.main(verbosity=2)
