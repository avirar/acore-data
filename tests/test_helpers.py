"""
Unit tests for filter clause builder and column resolver helpers.

These tests don't require a live database connection.
Run with: python3 tests/test_helpers.py (or pytest)
"""

import unittest
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
