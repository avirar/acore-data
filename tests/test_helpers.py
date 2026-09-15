"""
Unit tests for filter clause builder and column resolver helpers.

These tests don't require a live database connection.
Run with: python3 tests/test_helpers.py (or pytest)
"""

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.query import _build_sql_filter_clause, _resolve_sql_column, _escape_like_pattern


class TestEscapeLikePattern(unittest.TestCase):
    """Test LIKE pattern escaping."""

    def test_preserves_percent_wildcards(self):
        """User-provided % wildcards should be preserved."""
        result = _escape_like_pattern("%term%")
        self.assertIn("term", result)
        # Should NOT escape %
        self.assertNotIn("\\%", result)

    def test_preserves_underscore_wildcard(self):
        """User-provided _ wildcard should be preserved."""
        result = _escape_like_pattern("_test_")
        self.assertNotIn("\\_", result)

    def test_escapes_backslash(self):
        """Backslashes should be escaped to prevent injection."""
        result = _escape_like_pattern("a\\b")
        # Single backslash becomes double
        self.assertIn("\\\\", result)

    def test_wraps_with_quotes(self):
        """Pattern should be wrapped in single quotes."""
        result = _escape_like_pattern("test")
        self.assertTrue(result.startswith("'"))
        self.assertTrue(result.endswith("'"))


class TestBuildSqlFilterClause(unittest.TestCase):
    """Test SQL WHERE clause building."""

    def test_like_operator(self):
        """"$like should produce LIKE clause with %s placeholder."""
        fragment, param, err = _build_sql_filter_clause("name", {"$like": "%term%"})
        self.assertFalse(err)
        self.assertIn("LIKE", fragment)
        self.assertIn("%s", fragment)
        self.assertIn("name", fragment)
        self.assertEqual(param, "%term%")

    def test_ilike_operator(self):
        """"$ilike should produce LOWER() wrapped LIKE with %s placeholder."""
        fragment, param, err = _build_sql_filter_clause("name", {"$ilike": "%TERM%"})
        self.assertFalse(err)
        self.assertIn("LOWER(", fragment)
        self.assertIn("LIKE", fragment)
        self.assertIn("%s", fragment)
        self.assertEqual(param, "%term%")

    def test_string_exact_match(self):
        """Plain string should produce equality with %s placeholder."""
        fragment, param, err = _build_sql_filter_clause("name", "O'Brien")
        self.assertFalse(err)
        self.assertIn("=", fragment)
        self.assertIn("%s", fragment)
        self.assertEqual(param, "O'Brien")

    def test_numeric_exact_match(self):
        """Integer should produce equality with %s placeholder."""
        fragment, param, err = _build_sql_filter_clause("entry", 42)
        self.assertFalse(err)
        self.assertIn("= %s", fragment)
        self.assertEqual(param, 42)

    def test_unknown_dict_operator_fails(self):
        """Unknown dict operators should return error."""
        fragment, param, err = _build_sql_filter_clause("name", {"$unknown": "x"})
        self.assertTrue(err)


class TestResolveSqlColumn(unittest.TestCase):
    """Test column name resolution with registry entries."""

    def _make_reg_entry(self, fields):
        """Helper to create a mock registry entry."""
        return {
            "fields": {
                str(i): info for i, info in enumerate(fields)
            }
        }

    def test_exact_sql_column_match(self):
        """Exact match on sql_column should resolve."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "entry"},
            {"name": "CreatureName", "sql_column": "name"},
        ])
        col, err = _resolve_sql_column(reg, "entry", "creature_template")
        self.assertEqual(col, "entry")

    def test_case_insensitive_match(self):
        """Column lookup should be case-insensitive."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "Entry"},
        ])
        col, err = _resolve_sql_column(reg, "entry", "creature_template")
        self.assertEqual(col, "Entry")

    def test_cpp_name_to_sql_column(self):
        """C++ field name should resolve to SQL column."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "entry"},
        ])
        col, err = _resolve_sql_column(reg, "CreatureID", "creature_template")
        self.assertEqual(col, "entry")

    def test_case_insensitive_cpp_name(self):
        """C++ field name lookup should be case-insensitive."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "entry"},
        ])
        col, err = _resolve_sql_column(reg, "creatureid", "creature_template")
        self.assertEqual(col, "entry")

    def test_unknown_field_gives_suggestion(self):
        """Unknown field should return None with suggestion."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "entry"},
            {"name": "CreatureName", "sql_column": "name"},
        ])
        col, err = _resolve_sql_column(reg, "bogus", "creature_template")
        self.assertIsNone(col)
        self.assertIsNotNone(err)
        # Suggestion should mention actual fields
        self.assertTrue(
            "entry" in err.lower() or "name" in err.lower(),
            f"Suggestion missing field names: {err}",
        )

    def test_typo_gives_fuzzy_suggestion(self):
        """Near-miss should give fuzzy suggestion."""
        reg = self._make_reg_entry([
            {"name": "CreatureID", "sql_column": "entry"},
        ])
        col, err = _resolve_sql_column(reg, "entr", "creature_template")
        # Could match via fuzzy or prefix
        if col is not None:
            self.assertEqual(col, "entry")
        else:
            self.assertIn("entry", err.lower())


class TestTTLCache(unittest.TestCase):
    """Test persistent TTL cache behavior."""

    def setUp(self):
        from core.resolvers.ref_utils import invalidate_persistent_cache
        invalidate_persistent_cache()

    def test_set_and_get(self):
        from core.resolvers.ref_utils import _set_persistent, _get_persistent
        _set_persistent("sql:creature_template:123:entry", "creature_template [Rabbit]")
        result = _get_persistent("sql:creature_template:123:entry")
        self.assertEqual(result, "creature_template [Rabbit]")

    def test_key_not_found(self):
        from core.resolvers.ref_utils import _get_persistent
        self.assertIsNone(_get_persistent("nonexistent:key"))

    def test_expiry(self):
        import time
        from core.resolvers.ref_utils import _set_persistent, _get_persistent
        # Manually set an expired entry
        from core.resolvers.ref_utils import _PERSISTENT_CACHE
        _PERSISTENT_CACHE["expired:key"] = ("old_value", time.time() - 1)
        self.assertIsNone(_get_persistent("expired:key"))

    def test_invalidate_clears_all(self):
        from core.resolvers.ref_utils import _set_persistent, _get_persistent, invalidate_persistent_cache
        _set_persistent("k1", "v1")
        _set_persistent("k2", "v2")
        invalidate_persistent_cache()
        self.assertIsNone(_get_persistent("k1"))
        self.assertIsNone(_get_persistent("k2"))

    def test_max_size_eviction(self):
        from core.resolvers.ref_utils import _set_persistent, _get_persistent, _CACHE_MAX, _PERSISTENT_CACHE
        # Fill cache with expired entries to trigger eviction path
        import time
        for i in range(_CACHE_MAX + 100):
            _PERSISTENT_CACHE[f"old-{i}"] = (f"v{i}", time.time() - 60)
        # Set fresh key should evict expired entries first
        _set_persistent("fresh", "value")
        self.assertEqual(_get_persistent("fresh"), "value")


class TestEnumIndex(unittest.TestCase):
    """core.enum_index: C++ enum definition parsing."""

    def test_parse_value(self):
        from core.enum_index import _parse_value
        self.assertEqual(_parse_value("17"), 17)
        self.assertEqual(_parse_value("0x00200000"), 2097152)
        self.assertEqual(_parse_value("0b101"), 5)
        self.assertIsNone(_parse_value("(1 << 0)"))
        self.assertIsNone(_parse_value("A | B"))

    def test_extract_named_and_auto_enums(self):
        from core.enum_index import _extract_enums_from_text
        text = """
        // comment
        enum Foo {
            FOO_A,
            FOO_B = 5,        // explicit
            FOO_C,            // auto: 6
            FOO_D = (1 << 3), // expression: skipped
            FOO_E = 0x10      // hex
        };
        enum class Bar : uint32 {
            BAR_X = 0,
        };
        enum {
            ANON = 1
        };
        """
        idx = {}
        _extract_enums_from_text(text, "test.h", idx)
        self.assertIn("Foo", idx)
        self.assertEqual(idx["Foo"]["members"][0], "FOO_A")
        self.assertEqual(idx["Foo"]["members"][5], "FOO_B")
        self.assertEqual(idx["Foo"]["members"][6], "FOO_C")
        self.assertNotIn(8, idx["Foo"]["members"])   # expression skipped
        self.assertEqual(idx["Foo"]["members"][16], "FOO_E")
        self.assertIn("Bar", idx)
        self.assertEqual(idx["Bar"]["members"][0], "BAR_X")

    def test_find_enums_by_value(self):
        from core.enum_index import find_enums_by_value
        idx = {"A": {"file": "x", "members": {17: "A_X"}},
               "B": {"file": "y", "members": {5: "B_Y"}}}
        self.assertEqual(find_enums_by_value(idx, 17), {"A": "A_X"})


class TestExplainHelpers(unittest.TestCase):
    """explain tool: pure helpers (no DB)."""

    def test_nontrivial(self):
        from tools.explain import _nontrivial
        self.assertFalse(_nontrivial(None))
        self.assertFalse(_nontrivial(0))
        self.assertFalse(_nontrivial(""))
        self.assertFalse(_nontrivial("  "))
        self.assertFalse(_nontrivial(False))
        self.assertFalse(_nontrivial([]))
        self.assertTrue(_nontrivial(1))
        self.assertTrue(_nontrivial("x"))
        self.assertTrue(_nontrivial([1]))

    def test_flatten_links_caps_and_shapes(self):
        from tools.explain import _flatten_links
        self.assertEqual(_flatten_links(None), [])
        self.assertEqual(_flatten_links("not a list"), [])
        big = [{"links": [{"field": f"f{i}", "value": i,
                           "target": "t", "target_name": f"n{i}"} for i in range(50)]}]
        out = _flatten_links(big)
        self.assertEqual(len(out), 15)
        self.assertEqual(out[0]["target_name"], "n0")

    def test_dbc_overrides_diffs_and_reports_absent_dbc(self):
        from tools.explain import _dbc_overrides

        class _Reader:
            def get_record_by_id(self, i):
                return {0: 100, 1: 5} if i == 100 else None

        class _RegEntry:
            pass

        class _Registry:
            def _resolve_entry(self, name):
                return ("FakeEntry", {
                    "dbc_file": "Fake.dbc",
                    "fields": {
                        "0": {"name": "Id", "type": "uint32"},
                        "1": {"name": "Value", "type": "uint32"},
                        "2": {"name": "Other", "type": "uint32"},
                    },
                })

        class _Server:
            registry = _Registry()

            def _load_dbc(self, name):
                self.loaded = name
                return _Reader()

        s = _Server()
        row = {"ID": 100, "Value": 9, "Other": 0}
        overrides, exists = _dbc_overrides(s, "Fake", 100, row)
        self.assertTrue(exists)
        self.assertEqual(overrides, {"Value": 9})  # case-insensitive match
        self.assertEqual(s.loaded, "Fake")  # .dbc stripped

        overrides, exists = _dbc_overrides(s, "Fake", 99999, row)
        self.assertFalse(exists)
        self.assertEqual(overrides, {})


class TestProjectOverlayFields(unittest.TestCase):
    """tools.query._project_overlay_fields: DBC+SQL overlay merge projection.

    Live spell_dbc-style rows use WotLK SQL column style (ID,
    Name_Lang_enUS) while users select C field names (Id, spellname).
    """

    ROW = {
        "ID": 4051,
        "BaseLevel": 30,
        "Name_Lang_enUS": "Explosive Sheep Passive",
        "Name_Lang_deDE": None,
        "NameSubtext_Lang_enUS": "Sub",
        "EffectTriggerSpell_1": 123,
    }

    def _entry(self):
        return {
            "fields": {
                "0": {"name": "Id", "type": "uint32", "sql_column": "Id"},
                "7": {"name": "BaseLevel", "type": "uint32", "sql_column": "BaseLevel"},
                "136": {"name": "SpellName[0]", "type": "std::array<char const*,16>",
                        "sql_column": "SpellName"},
                "137": {"name": "SpellName[1]", "type": "std::array<char const*,16>",
                        "sql_column": "SpellName"},
                "152": {"name": "NameSubtext[0]", "type": "std::array<char const*,16>",
                        "sql_column": "NameSubtext"},
                "116": {"name": "EffectTriggerSpell[0]", "type": "uint32",
                        "sql_column": "EffectTriggerSpell"},
            }
        }

    def test_case_insensitive_pk(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], ["Id"], self._entry())
        self.assertEqual(rows, [{"Id": 4051}])

    def test_locale_family_enus(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], ["spellname"], self._entry())
        self.assertEqual(rows, [{"Id": 4051, "SpellName": "Explosive Sheep Passive"}])

    def test_locale_family_slot1(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], ["spellname[1]"], self._entry())
        self.assertEqual(rows, [{"Id": 4051, "SpellName": None}])

    def test_matching_locale_base(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], ["NameSubtext"], self._entry())
        self.assertEqual(rows, [{"Id": 4051, "NameSubtext": "Sub"}])

    def test_slot_suffixed_column(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], ["EffectTriggerSpell"], self._entry())
        self.assertEqual(rows, [{"Id": 4051, "EffectTriggerSpell": 123}])

    def test_missing_column_errors_with_sample(self):
        from tools.query import _project_overlay_fields
        out = _project_overlay_fields([dict(self.ROW)], ["NonexistentField"], self._entry())
        self.assertIsInstance(out, dict)
        self.assertTrue(out.get("isError"))
        self.assertIn("NonexistentField", out["error"])
        self.assertIn("ID", out["error"])

    def test_no_fields_returns_rows(self):
        from tools.query import _project_overlay_fields
        rows = _project_overlay_fields([dict(self.ROW)], None, self._entry())
        self.assertEqual(rows, [dict(self.ROW)])


class TestPerDbCreds(unittest.TestCase):
    """core.database: per-database credential overrides (DB_AUTH_*/DB_CHAR_*).

    Shared-DB topologies: explicit DB_* base config disables worldserver.conf
    auto-detection, but DB_AUTH_*/DB_CHAR_* env vars still route individual
    databases to a different MySQL host/credential set.
    """

    def _db(self, env=None):
        from core.database import Database
        with unittest.mock.patch.dict(
            os.environ, env or {}, clear=False
        ):
            db = Database(
                db_host="127.0.0.1",
                db_port="3306",
                db_user="acore",
                db_password="acore",
                db_name="acore_world",
            )
        # Env vars are read once in __init__; the instance is stable after.
        return db

    def test_no_env_overrides(self):
        db = self._db()
        creds = db._creds_for("acore_auth")
        self.assertEqual(creds["host"], "127.0.0.1")
        self.assertEqual(creds["user"], "acore")
        self.assertEqual(creds["name"], "acore_auth")

    def test_env_override_wins_over_conf_override(self):
        db = self._db(env={
            "DB_AUTH_HOST": "10.0.0.5",
            "DB_AUTH_USER": "remote",
            "DB_AUTH_PASSWORD": "secret",
        })
        # Simulate worldserver.conf auto-detection having found a third host.
        db._db_creds["acore_auth"] = {
            "host": "10.9.9.9", "port": "3307", "user": "confuser",
            "password": "confpass", "name": "acore_auth",
        }
        creds = db._creds_for("acore_auth")
        self.assertEqual(creds["host"], "10.0.0.5")
        self.assertEqual(creds["user"], "remote")
        self.assertEqual(creds["password"], "secret")
        # Unset keys merge over the conf layer, not the base.
        self.assertEqual(creds["port"], "3307")
        self.assertEqual(creds["name"], "acore_auth")

    def test_partial_env_merge_over_base(self):
        db = self._db(env={"DB_AUTH_PORT": "3307"})
        creds = db._creds_for("acore_auth")
        self.assertEqual(creds["port"], "3307")
        self.assertEqual(creds["host"], "127.0.0.1")
        self.assertEqual(creds["user"], "acore")
        self.assertEqual(creds["password"], "acore")

    def test_char_env_override(self):
        db = self._db(env={
            "DB_CHAR_HOST": "10.0.0.6",
            "DB_CHAR_NAME": "chars_realm2",
        })
        creds = db._creds_for("acore_characters")
        self.assertEqual(creds["host"], "10.0.0.6")
        self.assertEqual(creds["name"], "chars_realm2")

    def test_other_databases_untouched(self):
        db = self._db(env={"DB_AUTH_HOST": "10.0.0.5"})
        for name in ("acore_world", "acore_playerbots"):
            creds = db._creds_for(name)
            self.assertEqual(creds["host"], "127.0.0.1")
            self.assertEqual(creds["user"], "acore")

    def test_no_env_vars_means_no_overrides(self):
        from core.database import Database
        env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("DB_AUTH_", "DB_CHAR_"))
        }
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            db = Database(db_host="h", db_user="u")
        self.assertEqual(db._env_db_creds, {})

    def test_auto_detect_fallback_warns(self):
        """No worldserver.conf + no env vars -> explicit stderr warning,
        not a silent root@localhost fallback."""
        import contextlib
        import io
        import core.database as D

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            db = D.Database()
            db._auto_detect_db_config(candidates=[])

        out = buf.getvalue()
        self.assertIn("falling back to root@localhost", out)
        self.assertEqual(db.db_host, "localhost")
        self.assertEqual(db.db_user, "root")

    def test_worldserver_conf_env_override(self):
        """ACORE_WORLDSERVER_CONF points at a non-default conf location."""
        import core.database as D

        conf = (
            'LoginDatabaseInfo = "authhost;3306;authuser;authpass;acore_auth"\n'
            'WorldDatabaseInfo = "worldhost;3307;worlduser;worldpass;acore_world"\n'
            'CharacterDatabaseInfo = "worldhost;3307;worlduser;worldpass;acore_characters"\n'
        )
        with tempfile.TemporaryDirectory() as td:
            conf_path = Path(td) / "worldserver.conf"
            conf_path.write_text(conf)
            with unittest.mock.patch.dict(
                os.environ, {"ACORE_WORLDSERVER_CONF": str(conf_path)}
            ):
                db = D.Database()
                db._auto_detect_db_config()

        self.assertEqual(db.db_host, "worldhost")
        self.assertEqual(db.db_port, "3307")
        self.assertEqual(db.db_user, "worlduser")
        # differing Login line becomes a per-DB override
        self.assertEqual(db._db_creds["acore_auth"]["host"], "authhost")
        # identical Character line does NOT override
        self.assertNotIn("acore_characters", db._db_creds)

    def test_worldserver_conf_env_override_empty_ignored(self):
        import core.database as D

        env = {
            k: v for k, v in os.environ.items()
            if k != "ACORE_WORLDSERVER_CONF"
        }
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            db = D.Database(db_host="h", db_user="u")
        # no crash, and no empty-string candidate consulted
        self.assertEqual(db.db_host, "h")

    @unittest.skipIf(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        "root bypasses mode-000 permissions",
    )
    def test_safe_path_helpers_tolerate_inaccessible_parent(self):
        """pathlib exists()/is_dir() RAISE PermissionError under an
        inaccessible parent dir (e.g. /root on CI runners); the safe_*
        helpers must report 'absent' instead."""
        import core.paths as P

        with tempfile.TemporaryDirectory() as td:
            locked = Path(td) / "locked"
            (locked / "dbc").mkdir(parents=True)
            (locked / "dbc" / "x.dbc").write_text("x")
            locked.chmod(0o000)
            try:
                self.assertFalse(P.safe_is_dir(locked / "dbc"))
                self.assertFalse(P.safe_is_file(locked / "dbc" / "x.dbc"))
                self.assertFalse(P.safe_exists(locked))
            finally:
                locked.chmod(0o755)


if __name__ == "__main__":
    unittest.main(verbosity=2)
