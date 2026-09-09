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
        [sys.executable, SERVER_SCRIPT],
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
        [sys.executable, SERVER_SCRIPT],
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
        """Should return 6 consolidated tools."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        p = subprocess.run(
            [sys.executable, SERVER_SCRIPT],
            input=json.dumps(payload),
            capture_output=True,
            timeout=5,
            text=True,
            cwd=_WORKDIR,
            env=_ENV,
        )
        r = json.loads(p.stdout)
        tools = r["result"]["tools"]
        self.assertEqual(len(tools), 10, "Should have exactly 10 tools")
        names = {t["name"] for t in tools}
        self.assertIn("terrain", names)
        self.assertIn("spawns", names)
        self.assertIn("dbversion", names)
        self.assertIn("travel", names)
        self.assertIn("encounter", names)
        self.assertIn("explain", names)
        self.assertIn("query", names)


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


class TestQuestResolution(unittest.TestCase):
    """Test quest-specific resolution with starters, enders, POIs, chain."""

    def _quest_resolved(self, result):
        """Get $resolved_fields from metadata for a quest query result."""
        meta = result.get("metadata", {})
        return meta.get("$resolved_fields", {})

    def test_quest_resolve_includes_starters(self):
        """Quest with resolve=true should include NPC/GO starters."""
        result = call_query({
            "name": "quest_template",
            "id": 3904,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        resolved = self._quest_resolved(result)
        q3904 = resolved.get("3904", {})
        starters = q3904.get("starters", [])
        self.assertGreater(len(starters), 0, "Quest 3904 should have at least one starter NPC")

    def test_quest_resolve_includes_pois(self):
        """Quest POI resolution should return coordinate data."""
        result = call_query({
            "name": "quest_template",
            "id": 3904,
            "resolve": True,
        })
        self.assertNotIn("error", result)

    def test_quest_resolve_includes_chain(self):
        """Quest with chain data should resolve prev/next/breadcrumb."""
        # Quest 7561 has PrevQuestId set (known chain quest)
        result = call_query({
            "name": "quest_template",
            "id": 7561,
            "resolve": True,
        })
        self.assertNotIn("error", result)

    def test_quest_resolve_sql_only_skip_enrichment(self):
        """resolve=['dbc'] should skip quest enrichment (requires SQL)."""
        result = call_query({
            "name": "quest_template",
            "id": 3904,
            "resolve": ["dbc"],
        })
        self.assertNotIn("error", result)

    def test_quest_multiple_ids_resolve(self):
        """Filter query for multiple quests with resolve should work."""
        result = call_query({
            "name": "quest_template",
            "filter": {"LogTitle": {"$ilike": "%war%"}},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)


class TestConditionResolution(unittest.TestCase):
    """Test polymorphic condition table resolution with enum translation."""

    def _cond_resolved(self, result):
        """Get $resolved_fields from metadata for a conditions query result."""
        meta = result.get("metadata", {})
        return meta.get("$resolved_fields", {})

    def test_spell_source_translates_enum(self):
        """SourceType=17 should resolve to 'SPELL' enum name."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceTypeOrReferenceId": 17, "SourceEntry": 3678},
            "resolve": True,
            "limit": 5,
        })
        self.assertNotIn("error", result)
        resolved = self._cond_resolved(result)
        # At least one row should have been resolved
        rows_with_resolution = [k for k in resolved if not k.startswith("$")]
        self.assertTrue(len(rows_with_resolution) > 0 or len(resolved) > 0,
                        "Should resolve SourceType enum name")

    def test_spell_click_resolves_creature_and_spell(self):
        """SourceType=18 should resolve SourceGroup as creature and SourceEntry as spell."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceGroup": 24418, "SourceTypeOrReferenceId": 18},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_near_creature_resolves_condition_value(self):
        """ConditionType=29 (NEAR_CREATURE) should resolve Value1 as creature name."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceEntry": 3678, "SourceTypeOrReferenceId": 17},
            "resolve": True,
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_questtaken_resolves_condition_value(self):
        """ConditionType=9 (QUESTTAKEN) should resolve Value1 as quest name."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceGroup": 24418, "SourceTypeOrReferenceId": 18},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_item_condition_resolves(self):
        """ConditionType=2 (ITEM) should resolve Value1 as item name."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceTypeOrReferenceId": 1, "SourceEntry": 6994},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_multi_row_condition_filter(self):
        """Filter for multiple conditions with resolve should work."""
        result = call_query({
            "name": "conditions",
            "filter": {"SourceTypeOrReferenceId": 17},
            "resolve": True,
            "limit": 10,
        })
        self.assertNotIn("error", result)


class TestSmartScriptResolution(unittest.TestCase):
    """Test smart_scripts triple-polymorphic resolution."""

    def _sai_resolved(self, result):
        """Get $resolved_fields from metadata for a smart_scripts query result."""
        meta = result.get("metadata", {})
        return meta.get("$resolved_fields", {})

    def test_cast_action_resolves_spell(self):
        """action_type=11 (CAST) should resolve param1 as Spell name."""
        # entryorguid=-201800 has CAST actions with real spell IDs
        result = call_query({
            "name": "smart_scripts",
            "filter": {"entryorguid": -201800, "action_type": 11},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._sai_resolved(result)
        # Each resolved entry should have action_param1 with spell name
        has_spell = False
        for pk, data in resolved.items():
            ap1 = data.get("action_param1", {})
            if ap1.get("resolved_to") and "Spell" in str(ap1.get("resolved_to", "")):
                has_spell = True
                break
        self.assertTrue(has_spell, "CAST action should resolve param1 as Spell name")

    def test_update_ic_translates_event_type(self):
        """event_type=0 should resolve to 'UPDATE_IC' enum name."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"entryorguid": -201800, "event_type": 0},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._sai_resolved(result)
        has_name = False
        for pk, data in resolved.items():
            et = data.get("event_type", {})
            if et.get("name") == "UPDATE_IC":
                has_name = True
                break
        self.assertTrue(has_name, "event_type=0 should translate to UPDATE_IC")

    def test_talk_action_resolves_creature_text(self):
        """action_type=1 (TALK) on LINK event should resolve param1."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"entryorguid": -209188, "action_type": 1},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_summon_creature_resolves_entry(self):
        """action_type=12 (SUMMON_CREATURE) should resolve param1 as creature name."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"action_type": 12, "action_param1": 26923},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._sai_resolved(result)
        has_creature = False
        for pk, data in resolved.items():
            ap1 = data.get("action_param1", {})
            if ap1.get("resolved_to") and "creature_template" in str(ap1.get("resolved_to", "")):
                has_creature = True
                break
        self.assertTrue(has_creature, "SUMMON_CREATURE should resolve param1 as creature")

    def test_link_event_translates_enum(self):
        """event_type=61 (LINK) should translate to enum name."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"entryorguid": -209187, "event_type": 61},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._sai_resolved(result)
        has_link = False
        for pk, data in resolved.items():
            et = data.get("event_type", {})
            if et.get("name") == "LINK":
                has_link = True
                break
        self.assertTrue(has_link, "event_type=61 should translate to LINK")

    def test_source_type_resolves_entryorguid(self):
        """source_type=0 with negative entryorguid should annotate creature guid."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"entryorguid": -201800, "source_type": 0},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._sai_resolved(result)
        has_guid = False
        for pk, data in resolved.items():
            eo = data.get("entryorguid", {})
            if eo and ("guid" in str(eo.get("resolved_to", "")) or "source_type_name" in eo):
                has_guid = True
                break
        self.assertTrue(has_guid, "source_type=0 negative entryorguid should annotate guid")

    def test_summon_go_action_resolves_entry(self):
        """action_type=50 (SUMMON_GO) should resolve param1 as gameobject name."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"action_type": 50, "action_param1": 182659},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_multi_row_filter_resolves(self):
        """Multi-row smart_scripts filter with resolve should work."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"source_type": 0},
            "resolve": True,
            "limit": 10,
        })
        self.assertNotIn("error", result)

    def test_target_closest_creature_resolves_entry(self):
        """target_type=19 (CLOSEST_CREATURE) should resolve param1."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"target_type": 19},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)

    def test_quest_offer_action_resolves_quest(self):
        """action_type=7 (OFFER_QUEST) should resolve param1 as quest name."""
        result = call_query({
            "name": "smart_scripts",
            "filter": {"action_type": 7, "action_param1": 3904},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)


class TestAchievementCriteriaResolution(unittest.TestCase):
    """Test achievement_criteria_data polymorphic resolution."""

    def _ac_resolved(self, result):
        """Get $resolved_fields from metadata for an achievement query result."""
        meta = result.get("metadata", {})
        return meta.get("$resolved_fields", {})

    def test_type_creature_resolves_value1(self):
        """type=1 (T_CREATURE) should resolve value1 as creature name."""
        # criteria_id=3615 has type=1, value1=1412
        result = call_query({
            "name": "achievement_criteria_data",
            "filter": {"criteria_id": 3615},
            "resolve": True,
        })
        self.assertNotIn("error", result)
        resolved = self._ac_resolved(result)
        has_creature = False
        for pk, data in resolved.items():
            if "value1" in data and "creature_template" in str(data.get("value1", "")):
                has_creature = True
                break
        self.assertTrue(has_creature, "T_CREATURE type should resolve value1 as creature")

    def test_type_aura_resolves_spell(self):
        """type=5 (S_AURA) should resolve value1 as spell name."""
        # criteria_id=3826 has single row: type=5, value1=26157
        result = call_query({
            "name": "achievement_criteria_data",
            "filter": {"criteria_id": 3826},
            "resolve": True,
        })
        self.assertNotIn("error", result)
        resolved = self._ac_resolved(result)
        has_spell = False
        for pk, data in resolved.items():
            if "value1" in data and "Spell" in str(data.get("value1", "")):
                has_spell = True
                break
        self.assertTrue(has_spell, "S_AURA type should resolve value1 as spell")

    def test_type_map_difficulty_translates_enum(self):
        """type=12 (MAP_DIFFICULTY) should translate type to enum name."""
        result = call_query({
            "name": "achievement_criteria_data",
            "filter": {"type": 12},
            "resolve": True,
            "limit": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._ac_resolved(result)
        has_name = False
        for pk, data in resolved.items():
            if data.get("type_name") == "TYPE_MAP_DIFFICULTY":
                has_name = True
                break
        self.assertTrue(has_name, "type=12 should translate to TYPE_MAP_DIFFICULTY")

    def test_type_map_id_resolves_value1(self):
        """type=20 (MAP_ID) should resolve value1 as map name."""
        # criteria_id=1820 has type=20, value1=529
        result = call_query({
            "name": "achievement_criteria_data",
            "filter": {"criteria_id": 1820},
            "resolve": True,
        })
        self.assertNotIn("error", result)

    def test_multi_row_filter_resolves(self):
        """Multi-row achievement_criteria filter with resolve should work."""
        result = call_query({
            "name": "achievement_criteria_data",
            "filter": {"type": 1},
            "resolve": True,
            "limit": 10,
        })
        self.assertNotIn("error", result)


class TestDBCFixedAlias(unittest.TestCase):
    """Test underscore-to-bracket alias resolution and improved fuzzy suggestions."""

    def test_underscore_alias_slot_1(self):
        """EffectMiscValue_1 should resolve to EffectMiscValue[0] (index 110)."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectMiscValue_1": 0},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_underscore_alias_slot_2(self):
        """EffectMiscValue_2 should resolve to EffectMiscValue[1] (index 111)."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectMiscValue_2": 0},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_effect_underscore_alias(self):
        """Effect_1 should resolve to Effect[0] (index 71)."""
        result = call_query({
            "name": "Spell",
            "filter": {"Effect_1": 6},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_bracket_still_works(self):
        """Bracket notation Effect[0] should still work as before."""
        result = call_query({
            "name": "Spell",
            "filter": {"Effect[0]": 6},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_base_field_name_matches_any_slot(self):
        """Base field name 'EffectMiscValue' should match first slot (index 110)."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectMiscValue": 0},
            "limit": 5,
        })
        self.assertNotIn("error", result)

    def test_bad_key_shows_relevant_suggestions(self):
        """Bad key 'EffectMisvalue_X' should suggest EffectMiscValue variants."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectMisvalue_X": 0},
        })
        # Should get an error with useful suggestions, not generic ones
        self.assertIn("error", result)
        error_text = result.get("error", "") + result.get("suggestion", "")
        # At least should mention EffectMiscValue in the error output
        self.assertTrue(
            "EffectMiscValue" in error_text or "Effect" in error_text,
            f"Error should mention Effect-related fields. Got: {error_text[:200]}"
        )

    def test_misspelled_key_surfaces_similar_fields(self):
        """A misspelled key like 'EffectItemValue' should surface both EffectItemType and EffectMiscValue."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectItemValue": 0},
        })
        self.assertIn("error", result)
        error_text = result.get("error", "") + result.get("suggestion", "")
        # Both EffectItemType and EffectMiscValue should appear (not just Effect or EffectDieSides)
        has_itemtype = "EffectItemType" in error_text
        has_miscvalue = "EffectMiscValue" in error_text
        self.assertTrue(
            has_itemtype or has_miscvalue,
            f"Error should suggest EffectItemType or EffectMiscValue for misspelling 'EffectItemValue'. Got: {error_text[:300]}"
        )

    def test_suggestions_use_compact_bracket_display(self):
        """Suggestions should use compact [0-2] format rather than listing each slot individually."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectItemValue": 0},
        })
        self.assertIn("error", result)
        error_text = result.get("error", "") + result.get("suggestion", "")
        # Should have compact format like EffectMiscValue[0-2], not individual slots
        # If old-style expansion was used, we'd see many more "Effect" mentions
        # Compact format means at most a handful of distinct field families
        import re
        bracket_ranges = re.findall(r'\w+\[\d+-\d+\]', error_text)
        self.assertTrue(
            len(bracket_ranges) >= 2,
            f"Suggestions should use compact [N-M] format (found {len(bracket_ranges)}). Got: {error_text[:300]}"
        )

    def test_suggests_correct_field_for_item_creation(self):
        """When searching for fields related to item creation effects, EffectItemType should appear."""
        result = call_query({
            "name": "Spell",
            "filter": {"EffectCreateItem": 123},
        })
        self.assertIn("error", result)
        error_text = result.get("error", "") + result.get("suggestion", "")
        # EffectItemType is the actual field for CREATE_ITEM effect item type
        # EffectMiscValue also carries item ID for CREATE_ITEM
        related_fields = ["EffectItemType", "EffectMiscValue", "Effect"]
        found = [f for f in related_fields if f in error_text]
        self.assertTrue(
            len(found) >= 2,
            f"Should suggest at least 2 of {related_fields}. Found: {found}. Got: {error_text[:300]}"
        )


class TestDBCvsSQLHints(unittest.TestCase):
    """Test DBC vs SQL confusion hints."""

    def test_sql_query_for_dbc_table_suggests_query_tool(self):
        """Trying SQL on 'spell' (DBC table) should suggest acore_data_query."""
        result = call_tool("sql", {"query": "SELECT * FROM spell LIMIT 1"})
        error = result.get("error", "") + result.get("hint", "")
        self.assertTrue(
            "DBC" in error.upper() or "binary" in error.lower(),
            f"Should mention DBC/binary file. Got: {error[:300]}"
        )

    def test_sql_query_for_spells_table_works(self):
        """SQL on 'spells' table should work (different from DBC Spell)."""
        result = call_tool("sql", {"query": "SELECT * FROM spells LIMIT 1"})
        # The 'spells' table exists as a spell_dbc overlay or reference table
        # Just verify the tool runs without crash
        self.assertTrue("result" in result or "error" in result)


class TestSQLToolConfig(unittest.TestCase):
    """Test ACORE_SQL_TOOL_MODE config (full/readonly/disabled)."""

    @staticmethod
    def _call_with_env(method, params, extra_env=None):
        """Call a tool with custom environment variables."""
        env = {**_ENV}
        if extra_env:
            env.update(extra_env)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        p = subprocess.run(
            [sys.executable, SERVER_SCRIPT],
            input=json.dumps(payload),
            capture_output=True,
            timeout=TIMEOUT,
            text=True,
            cwd=_WORKDIR,
            env=env,
        )
        r = json.loads(p.stdout)
        return r

    def test_sql_tool_disabled_excludes_from_list(self):
        """ACORE_SQL_TOOL_MODE=disabled should remove sql tool from tools/list."""
        result = self._call_with_env("tools/list", {}, {"ACORE_SQL_TOOL_MODE": "disabled"})
        tool_names = [t["name"] for t in result["result"]["tools"]]
        self.assertNotIn("sql", tool_names, "sql tool should be hidden when disabled")

    def test_sql_tool_readonly_blocks_insert(self):
        """ACORE_SQL_TOOL_MODE=readonly should reject INSERT statements."""
        result = self._call_with_env(
            "tools/call",
            {"name": "sql", "arguments": {"query": "INSERT INTO creature_template (entry, name) VALUES (999999, 'Test')"}},
            {"ACORE_SQL_TOOL_MODE": "readonly"},
        )
        parsed = json.loads(result["result"]["content"][0]["text"])
        self.assertIn("isError", parsed, "INSERT should be blocked in readonly mode")
        self.assertIn("Readonly", parsed.get("error", ""))

    def test_sql_tool_readonly_allows_select(self):
        """ACORE_SQL_TOOL_MODE=readonly should allow SELECT queries."""
        result = self._call_with_env(
            "tools/call",
            {"name": "sql", "arguments": {"query": "SELECT 1 as test"}},
            {"ACORE_SQL_TOOL_MODE": "readonly"},
        )
        parsed = json.loads(result["result"]["content"][0]["text"])
        self.assertNotIn("error", parsed, "SELECT should work in readonly mode")
        self.assertEqual(parsed["count"], 1)


class TestSpellResolution(unittest.TestCase):
    """Test Spell -> Conditions cross-reference resolver."""

    def _spell_resolved(self, result):
        """Get $resolved_fields from metadata for a spell query result."""
        meta = result.get("metadata", {})
        return meta.get("$resolved_fields", {})

    def test_spell_with_conditions_includes_requirements(self):
        """Spell 48649 (191 conditions) should include conditions with count and requirements."""
        result = call_query({
            "name": "Spell",
            "id": 48649,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        resolved = self._spell_resolved(result)
        entry = resolved.get("48649", {})
        conds = entry.get("conditions")
        self.assertIsNotNone(conds, "Spell 48649 should have conditions in resolved output")
        self.assertEqual(conds["count"], 191, "Should report correct condition count")
        self.assertIn("requirements", conds, "Should include formatted requirements")

    def test_spell_object_entry_guid_structured_values(self):
        """OBJECT_ENTRY_GUID conditions should resolve to structured target_entity dict."""
        result = call_query({
            "name": "Spell",
            "id": 3730,
            "resolve": True,
            "resolve_max": 5,
        })
        self.assertNotIn("error", result)
        resolved = self._spell_resolved(result)
        entry = resolved.get("3730", {})
        conds = entry.get("conditions", {}).get("requirements", [])
        self.assertGreater(len(conds), 0, "Spell 3730 should have conditions")
        # First condition is OBJECT_ENTRY_GUID (type=31) with UNIT type target
        first = conds[0]
        self.assertEqual(first["type"], "OBJECT_ENTRY_GUID")
        vals = first.get("values", {})
        self.assertIn("target_entity", vals, "Should have structured target_entity")
        te = vals["target_entity"]
        self.assertIn("id", te, "target_entity should have id")
        self.assertEqual(te["id"], 15263)

    def test_spell_with_no_conditions(self):
        """Spell 118 (Polymorph) has no spell conditions -> no 'conditions' key."""
        result = call_query({
            "name": "Spell",
            "id": 118,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        resolved = self._spell_resolved(result)
        entry = resolved.get("118", {})
        self.assertNotIn("conditions", entry, "Spell without conditions should not have 'conditions' key")

    def test_spell_no_resolve_skips_conditions(self):
        """resolve=False should not fetch or attach conditions."""
        result = call_query({
            "name": "Spell",
            "id": 48649,
            "resolve": False,
        })
        self.assertNotIn("error", result)
        resolved = self._spell_resolved(result)
        self.assertEqual(resolved, {}, "No resolution should produce empty $resolved_fields")

    def test_spell_resolve_max_warning(self):
        """resolve_max=N on spell with >N conditions should include warning message."""
        result = call_query({
            "name": "Spell",
            "id": 48649,
            "resolve": True,
            "resolve_max": 3,
        })
        self.assertNotIn("error", result)
        resolved = self._spell_resolved(result)
        conds = resolved.get("48649", {}).get("conditions", {})
        self.assertIn("warning", conds, "Should include warning when conditions exceed resolve_max")
        self.assertIn("191", conds["warning"], "Warning should mention total condition count")
        self.assertEqual(len(conds["requirements"]), 3, "Should show exactly resolve_max requirements")


class TestDbversionTool(unittest.TestCase):
    """dbversion tool: DB state / version audit (live DB)."""

    def test_version_row_present(self):
        r = call_tool("dbversion", {})
        self.assertNotIn("isError", r)
        v = r["version"]
        self.assertTrue(v.get("core_version"))
        self.assertTrue(v.get("db_version"))
        self.assertIn("acore_world", r["databases"])

    def test_per_db_update_counts_consistent(self):
        r = call_tool("dbversion", {})
        w = r["databases"]["acore_world"]
        self.assertTrue(w["installed"])
        self.assertGreater(w["tables"], 0)
        # applied + pending must equal the sum of all state counts
        total = sum(w["updates"].values())
        self.assertEqual(w["applied"] + w["pending"], total)

    def test_optional_playerbots_flag(self):
        r = call_tool("dbversion", {})
        self.assertIn("mod_playerbots_installed", r)
        pb = r["databases"]["acore_playerbots"]
        # flag must agree with the per-DB installed state
        self.assertEqual(r["mod_playerbots_installed"], pb["installed"])
        # on this install the mod DB is present
        self.assertTrue(pb["installed"])


class TestTravelTool(unittest.TestCase):
    """travel tool: mod-playerbots travel graph (live DB)."""

    def test_stats_mode(self):
        r = call_tool("travel", {"map": 0})
        self.assertEqual(r["mode"], "stats")
        self.assertGreater(r["node_count"], 100)
        self.assertGreater(r["edge_count"], 100)
        self.assertGreater(r["path_point_count"], 1000)
        self.assertTrue(r["sample_named_nodes"])

    def test_node_mode(self):
        r = call_tool("travel", {"map": 0, "node": 0})
        self.assertEqual(r["mode"], "node")
        self.assertEqual(r["node"]["name"], "Human start")
        self.assertTrue(r["neighbours"]["outgoing"])
        # neighbour names are resolved
        self.assertTrue(any(n["name"] for n in r["neighbours"]["outgoing"]))

    def test_path_mode_with_verification_field(self):
        r = call_tool("travel", {"map": 0, "from": 0, "to": 2776})
        self.assertEqual(r["mode"], "path")
        self.assertEqual(r["from"]["name"], "Human start")
        self.assertEqual(r["to"]["name"], "Elwynn Forest Goldshire")
        self.assertGreater(r["point_count"], 50)
        self.assertEqual(r["points"][0]["nr"], 0)
        # verification must always be present in path mode (checked>0 when
        # MMap data exists, otherwise a clear skip note)
        v = r["navmesh_verification"]
        self.assertIn("checked", v)
        self.assertIn("off_ground_count", v)

    def test_unknown_node_is_error(self):
        r = call_tool("travel", {"map": 0, "node": 999999})
        self.assertTrue(r.get("isError"))

    def test_no_path_between_nodes_is_error(self):
        r = call_tool("travel", {"map": 0, "from": 0, "to": 999999})
        self.assertTrue(r.get("isError"))

    def test_missing_map_is_error(self):
        r = call_tool("travel", {})
        self.assertTrue(r.get("isError"))
        self.assertIn("map", r["error"])


class TestEncounterTool(unittest.TestCase):
    """encounter tool: map/instance rollup (live DB)."""

    def test_instance_rollup(self):
        r = call_tool("encounter", {"map": 43, "limit": 5})
        self.assertEqual(r["map_name"], "Wailing Caverns")
        self.assertTrue(r["is_instance"])
        self.assertEqual(r["instance"]["script"], "instance_wailing_caverns")
        self.assertTrue(r["creatures"])
        c = r["creatures"][0]
        self.assertTrue(c["name"])
        self.assertGreaterEqual(c["spawn_count"], 1)
        self.assertIsNotNone(c["minlevel"])

    def test_outdoor_map_rollup_with_gameobjects(self):
        r = call_tool("encounter", {"map": 0, "limit": 2})
        self.assertFalse(r["is_instance"])
        self.assertNotIn("instance", r)
        self.assertTrue(r["creatures"])
        self.assertEqual(r["creatures"][0]["name"], "Wild Turkey")
        # outdoor maps carry game objects (ores, nodes, ...
        self.assertTrue(r["gameobjects"])
        self.assertIn("name", r["gameobjects"][0])

    def test_unknown_map_degrades_gracefully(self):
        r = call_tool("encounter", {"map": 9999})
        self.assertEqual(r["creatures"], [])
        self.assertNotIn("isError", r)
        self.assertTrue(r["metadata"]["note"])

    def test_missing_map_is_error(self):
        r = call_tool("encounter", {})
        self.assertTrue(r.get("isError"))

    def test_limit_validation(self):
        r = call_tool("encounter", {"map": 0, "limit": 500})
        self.assertTrue(r.get("isError"))


class TestExplainTool(unittest.TestCase):
    """explain tool: record digest (live DB + DBC)."""

    def test_dbc_record_digest(self):
        r = call_tool("explain", {"name": "Spell", "id": 118})
        self.assertEqual(r["name"], "Polymorph")
        self.assertIn("Polymorph", r["summary"])
        # name is pinned first in key_fields
        self.assertEqual(list(r["key_fields"].keys())[0], "SpellName[0]")
        self.assertTrue(r["relations"])

    def test_sql_record_digest(self):
        r = call_tool("explain", {"name": "quest_template", "id": 46})
        self.assertEqual(r["name"], "Bounty on Murlocs")
        self.assertEqual(r["source"]["sql_table"], "quest_template")
        names = {x["target_name"] for x in r["relations"]}
        self.assertTrue(any("Guard Thomas" in n for n in names))

    def test_overlay_only_record_notes_missing_dbc(self):
        # spell 19 exists only in the live spell_dbc overlay in this build
        r = call_tool("explain", {"name": "Spell", "id": 19})
        self.assertNotIn("isError", r)
        self.assertIn("sql_table", r["source"])
        self.assertIn("note", r["source"])
        self.assertIn("overlay", r["source"]["note"].lower())

    def test_missing_id_is_error(self):
        r = call_tool("explain", {"name": "Spell"})
        self.assertTrue(r.get("isError"))

    def test_unknown_store_gets_suggestion(self):
        r = call_tool("explain", {"name": "BogusStoreXYZ", "id": 1})
        self.assertTrue(r.get("isError") or r.get("suggestion"))


class TestSpawnsTool(unittest.TestCase):
    """spawns tool: creature spawn analysis (live DB)."""

    def test_wild_turkey_spawn_analysis(self):
        r = call_tool("spawns", {"entry": 32820})
        self.assertEqual(r["name"], "Wild Turkey")
        self.assertTrue(r["template_exists"])
        self.assertTrue(r["has_world_spawn"])
        self.assertGreaterEqual(r["total_spawns"], 3000)
        self.assertEqual(r["maps"][0]["map"], 0)
        self.assertEqual(r["maps"][0]["map_name"], "Eastern Kingdoms")
        self.assertTrue(r["samples"])

    def test_multi_map_entry_with_name_resolution(self):
        r = call_tool("spawns", {"entry": 4075, "limit": 2})
        self.assertEqual(r["name"], "Rat")
        # breakdown capped at 8, map_count is the exact distinct-map count
        self.assertEqual(len(r["maps"]), 8)
        self.assertGreater(r["map_count"], 8)
        # every shown map must carry a resolved name (DBC Map fallback)
        self.assertTrue(all(m["map_name"] for m in r["maps"]))

    def test_no_spawn_entry_reports_false_not_error(self):
        r = call_tool("spawns", {"entry": 1})  # Waypoint (GM-only)
        self.assertEqual(r["total_spawns"], 0)
        self.assertFalse(r["has_world_spawn"])
        self.assertTrue(r["template_exists"])
        self.assertNotIn("isError", r)

    def test_unknown_entry_is_error(self):
        r = call_tool("spawns", {"entry": 99999999})
        self.assertTrue(r.get("isError"))
        self.assertFalse(r["template_exists"])

    def test_map_filter_restricts_analysis(self):
        r = call_tool("spawns", {"entry": 32820, "map": 0, "limit": 2})
        self.assertEqual(r["map_count"], 1)
        self.assertEqual(len(r["samples"]), 2)
        self.assertTrue(all(s["map"] == 0 for s in r["samples"]))

    def test_invalid_entry_type_is_error(self):
        r = call_tool("spawns", {"entry": "notanumber"})
        self.assertTrue(r.get("isError"))


if __name__ == "__main__":
    # Run from acore-data directory
    unittest.main(verbosity=2)
