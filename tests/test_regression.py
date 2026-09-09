"""
Regression tests for the flat-output / strict-error / protocol rework
(branch fix/mcp-ergonomics).

Run with: python3 tests/test_regression.py (or pytest)
Requires: running AzerothCore MySQL instance + DBC files (same as test_integration.py)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

SERVER_SCRIPT = "server.py"
TIMEOUT = 120

_WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV = {**os.environ, "PYTHONPATH": _WORKDIR}


def _raw(*payloads):
    """Send raw JSON-RPC lines, return list of raw stdout lines."""
    p = subprocess.run(
        [sys.executable, SERVER_SCRIPT],
        input="".join(json.dumps(x) + "\n" for x in payloads),
        capture_output=True,
        timeout=TIMEOUT,
        text=True,
        cwd=_WORKDIR,
        env=_ENV,
    )
    return [line for line in p.stdout.splitlines() if line.strip()]


def call_tool(name, args):
    """Call any tool and return parsed result."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    }
    lines = _raw(payload)
    for line in lines:
        m = json.loads(line)
        if m.get("id") == 1:
            r = m.get("result", {})
            if r.get("isError"):
                return {"error": json.loads(r["content"][0]["text"]).get("error"),
                        "isError": True}
            return json.loads(r["content"][0]["text"])
    raise AssertionError(f"No response for {name}")


class TestResultShape(unittest.TestCase):
    """Flat rows, single-object id lookups, list filters."""

    def test_id_lookup_returns_single_object(self):
        r = call_tool("query", {"name": "Spell", "id": 118})
        self.assertNotIn("error", r)
        self.assertIsInstance(r["result"], dict, "id lookup must return one object")
        self.assertEqual(r["result"].get("Id"), 118)

    def test_filter_returns_list_of_flat_objects(self):
        r = call_tool("query", {
            "name": "quest_template",
            "filter": {"LogTitle": {"$ilike": "%murloc%"}},
            "limit": 5,
        })
        self.assertNotIn("error", r)
        self.assertIsInstance(r["result"], list)
        self.assertGreater(len(r["result"]), 0)
        for row in r["result"]:
            self.assertIsInstance(row, dict)
            self.assertIn("LogTitle", row)

    def test_id_not_found_is_specific_error_not_empty(self):
        r = call_tool("query", {"name": "Spell", "id": 999999999})
        self.assertTrue(r.get("isError"), "missing id must be an error, not empty")
        self.assertIn("999999999", r.get("error", ""))

    def test_id_filter_mismatch_is_specific_error(self):
        r = call_tool("query", {
            "name": "Spell", "id": 118, "filter": {"BaseLevel": 99},
        })
        self.assertTrue(r.get("isError"))
        self.assertIn("118", r.get("error", ""))

    def test_annotate_restores_legacy_shape(self):
        r = call_tool("query", {"name": "Spell", "id": 118, "annotate": True})
        self.assertNotIn("error", r)
        self.assertIsInstance(r["result"], list, "annotate mode returns field arrays")
        first = r["result"][0]
        self.assertIn("index", first)
        self.assertIn("sql_column", first)


class TestStrictValidation(unittest.TestCase):
    """Unknown args/fields produce errors with suggestions."""

    def test_unknown_argument_suggests_fields(self):
        r = call_tool("query", {"name": "Spell", "id": 118, "field": [38]})
        self.assertTrue(r.get("isError"))
        self.assertIn("field", r.get("error", ""))
        self.assertIn("fields", r.get("error", ""))

    def test_unknown_field_name_errors_with_suggestions(self):
        r = call_tool("query", {
            "name": "quest_template", "id": 46, "fields": ["LogTtl"],
        })
        self.assertTrue(r.get("isError"))
        self.assertIn("Did you mean", r.get("error", ""))


class TestErrorSurfacing(unittest.TestCase):
    """No-data must report which source(s) were consulted."""

    def test_no_data_lists_sources(self):
        r = call_tool("query", {"name": "Map", "filter": {"name": "DoesNotExistXYZ"}})
        self.assertTrue(r.get("isError"))
        err = r.get("error", "")
        self.assertIn("No data found", err)
        self.assertIn("DBC", err)
        self.assertIn("SQL overlay", err)


class TestListTool(unittest.TestCase):
    """Default limit + total metadata."""

    def test_default_limit_50_with_total(self):
        r = call_tool("list", {})
        self.assertLessEqual(len(r.get("result", [])), 50)
        self.assertEqual(r.get("count"), len(r["result"]))
        self.assertGreaterEqual(r.get("metadata", {}).get("total", 0), 400)

    def test_explicit_limit_respected(self):
        r = call_tool("list", {"limit": 3})
        self.assertEqual(len(r["result"]), 3)
        # truncation note must still report the full total
        self.assertGreaterEqual(r.get("metadata", {}).get("total", 0), 400)

    def test_no_format_string_noise(self):
        r = call_tool("list", {"search": "SpellEntry"})
        for item in r["result"]:
            self.assertNotIn("format", item)
            self.assertNotIn("record_size", item)


class TestLinks(unittest.TestCase):
    """links=true one-hop relation map."""

    def test_quest_links_includes_required_item(self):
        r = call_tool("query", {"name": "quest_template", "id": 46, "links": True})
        self.assertNotIn("error", r)
        links = r.get("metadata", {}).get("links")
        self.assertTrue(links, "metadata.links expected for quest 46")
        flat = json.dumps(links)
        self.assertIn("780", flat)
        self.assertIn("Torn Murloc Fin", flat)

    def test_links_off_by_default(self):
        r = call_tool("query", {"name": "quest_template", "id": 46})
        self.assertNotIn("links", r.get("metadata", {}))


class TestProtocol(unittest.TestCase):
    """JSON-RPC/MCP transport behavior."""

    def test_single_line_responses(self):
        lines = _raw(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        self.assertEqual(len(lines), 2, "exactly one line per response")
        for line in lines:
            m = json.loads(line)  # each line must be complete JSON
            self.assertIn("id", m)

    def test_notifications_get_no_response(self):
        lines = _raw(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        self.assertEqual(len(lines), 2)
        ids = {json.loads(l)["id"] for l in lines}
        self.assertEqual(ids, {1, 2})

    def test_protocol_version_echo(self):
        lines = _raw(
            {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            },
        )
        m = json.loads(lines[0])
        self.assertEqual(m["result"]["protocolVersion"], "2025-03-26")

    def test_mcp_is_error_flag(self):
        lines = _raw(
            {
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "query", "arguments": {"name": "NoSuchStoreXYZ"}},
            },
        )
        m = json.loads(lines[0])
        self.assertTrue(m["result"].get("isError", False),
                        "tool failures must set MCP-level isError")


class TestRegistryAudit(unittest.TestCase):
    """Static sanity checks on datastore_registry.json."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_WORKDIR, "datastore_registry.json"), "r") as f:
            cls.registry = json.load(f)["entries"]

    def test_spell_effect_indices_match_dbc_structure(self):
        # Authoritative layout from DBCStructure.h:
        #   EffectMiscValue  110-112
        #   EffectMiscValueB 113-115
        #   EffectTriggerSpell 116-118
        # (the old registry had 115/116 swapped; index 116 is EffectTriggerSpell[0])
        f = self.registry["SpellEntry"]["fields"]
        self.assertEqual(f["115"]["name"], "EffectMiscValueB[2]")
        self.assertEqual(f["115"]["sql_column"], "EffectMiscValueB")
        self.assertEqual(f["116"]["name"], "EffectTriggerSpell[0]")
        self.assertEqual(f["116"]["sql_column"], "EffectTriggerSpell")

    def test_map_entry_sql_database(self):
        self.assertEqual(self.registry["MapEntry"]["sql_database"], "acore_world")

    _TYPE_NAME = re.compile(
        r"^(std::[A-Za-z0-9_:]*|u?int(8|16|32|64)(_t)?|float|double|bool|string|"
        r"time_t|ObjectGuid|Difficulty|G3D::[A-Za-z0-9_]+|char|void)$"
    )

    def test_no_duplicate_field_names_per_entry(self):
        """Real field-identifier collisions (e.g. the old Spell idx 115/116
        EffectTriggerSpell[0] duplicate) are a registry bug. Type-string
        placeholder entries are a known separate defect and are exempted."""
        problems = []
        for name, entry in self.registry.items():
            seen = {}
            for idx, info in (entry.get("fields") or {}).items():
                fname = info.get("name", "")
                if not fname or self._TYPE_NAME.match(fname):
                    continue
                seen[fname] = seen.get(fname, 0) + 1
            for fname, n in seen.items():
                if n > 1:
                    problems.append(f"{name}: {fname} x{n}")
        self.assertFalse(problems, "; ".join(problems[:5]))


class TestRegistryHygiene(unittest.TestCase):
    """Live-but-unregistered tables found by the coverage audit (feat/registry-hygiene).

    - playerbots_bis_gear is OPTIONAL (mod-playerbots only): it must be
      registered, flagged in reference_notes, and must NOT be a structural
      audit failure when absent from the install.
    - SQL update-management tables + RBAC tables are registered so agents can
      query DB state / GM permissions.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_WORKDIR, "datastore_registry.json"), "r") as f:
            reg = json.load(f)
            cls.registry = reg["entries"]
            cls.indices = reg["indices"]

    def test_bis_gear_registered_as_optional(self):
        e = self.registry["PlayerbotsBisGear"]
        self.assertEqual(e["sql_table"], "playerbots_bis_gear")
        self.assertEqual(e["sql_database"], "acore_playerbots")
        self.assertEqual(e["category"], "sql_auxiliary")
        notes = (e.get("reference_notes") or "").lower()
        self.assertIn("optional", notes)
        # item_id FK is annotated (cross-DB join to item_template is the point)
        item_field = next(f for f in e["fields"].values() if f["sql_column"] == "item_id")
        self.assertTrue(item_field.get("references"), "item_id should reference item_template")

    def test_update_management_tables_registered(self):
        for name, tbl, db in [
            ("Updates", "updates", "acore_world"),
            ("UpdatesInclude", "updates_include", "acore_world"),
            ("Version", "version", "acore_world"),
        ]:
            self.assertIn(name, self.registry, name)
            self.assertEqual(self.registry[name]["sql_table"], tbl)
            self.assertEqual(self.registry[name]["sql_database"], db)

    def test_rbac_tables_registered(self):
        for name in [
            "RbacPermissions",
            "RbacAccountPermissions",
            "RbacDefaultPermissions",
            "RbacLinkedPermissions",
        ]:
            self.assertIn(name, self.registry, name)
            self.assertEqual(self.registry[name]["sql_database"], "acore_auth")

    def test_indices_contain_new_entries(self):
        for name in ["PlayerbotsBisGear", "Updates", "Version", "RbacPermissions"]:
            tbl = self.registry[name]["sql_table"]
            self.assertEqual(self.indices["by_struct_name"].get(name), name)
            self.assertEqual(self.indices["by_sql_table"].get(tbl), name)

    def test_total_entries_consistent(self):
        with open(os.path.join(_WORKDIR, "datastore_registry.json"), "r") as f:
            reg = json.load(f)
        self.assertEqual(reg["_meta"]["total_entries"], len(reg["entries"]))


class TestFormatParser(unittest.TestCase):
    """DBCfmt parser robustness."""

    def _parse(self, text):
        sys.path.insert(0, _WORKDIR)
        from core.formats import FormatParser
        tf = tempfile.NamedTemporaryFile("w", suffix=".h", delete=False)
        tf.write(text)
        tf.close()
        try:
            return FormatParser(tf.name).parse()
        finally:
            os.unlink(tf.name)

    def test_multiline_concatenated_literals(self):
        h = (
            'char constexpr Wrapfmt[] =\n'
            '    "niii"\n'
            '    "xxss" "x";\n'
            "const char Constanfmt[] = \"nixxx\";\n"
        )
        fmts = self._parse(h)
        self.assertEqual(fmts.get("Wrap"), "niiixxssx")
        self.assertEqual(fmts.get("Constan"), "nixxx")


if __name__ == "__main__":
    unittest.main(verbosity=2)
