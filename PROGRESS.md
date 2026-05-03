# acore-data Tool Improvements - Progress Tracker

## Context
Improving the acore-data MCP tools based on analysis of the "A Little Slime Goes a Long Way" quest flow investigation.
The goal is to reduce round trips and improve readability of query results.

## Previous Milestones
- **Milestone 1**: P0 + P1 + P3 complete (quest + item resolution, enums, compact DBC, class decoding)

## Current Work: Milestone 2 — Four Bug Fixes

### Issue 1: Compact Mode Not Compact Enough (SQL Results)
- [x] Add `_compact_sql_rows()` helper to `core/annotation.py`
- [x] Pass `compact` arg through `_query_sql()` in `tools/query.py`
- [x] Apply compaction before returning SQL results
- **VERIFIED**: SQL results now strip zero/null columns (31 columns → ~15 non-trivial)

### Issue 2: Item Class Resolution Wrong
- [x] Suppress generic `class` field resolution in `core/resolvers/item.py`
- **VERIFIED**: "class" field removed from resolved output, "item_type" shows correct ITEM_CLASS_NAMES

### Issue 3: SQL Tool Error Handling
- [x] Move "Unknown column" handler to top-level `elif` in `tools/sql.py`
- [x] Fix `cur.execute(sql, params or ())` → conditional in `core/database.py`
- **VERIFIED**: Column suggestions shown for bad column; LIKE '%ooze%' now works (5 results)

### Issue 6: Inconsistent "Not Found" in Resolved Fields
- [x] Fix `reference_column: "ID"` → `"entry"` for ItemTemplate refs in `datastore_registry.json`
- [x] Add fallback PK column detection in `core/resolvers/ref_utils.py`
- **VERIFIED**: SrcItemId now resolves to "item_template [Package of Empty Ooze Containers]"

## Files Changed
| File | Issues | Status |
|------|--------|--------|
| `core/annotation.py` | 1 | ✅ Done |
| `tools/query.py` | 1 | ✅ Done |
| `core/resolvers/item.py` | 2 | ✅ Done |
| `tools/sql.py` | 3 | ✅ Done |
| `core/database.py` | 3 | ✅ Done |
| `datastore_registry.json` | 6 | ✅ Done |
| `core/resolvers/ref_utils.py` | 6 | ✅ Done |

## Testing
- [x] All 95 tests pass
- [x] Manual verification: Issue 1 (compact), Issue 2 (item class), Issue 3 (SQL errors), Issue 6 (not found)

## Commits
- (none yet) — **Ready for first commit**

## Handover Notes
- All changes are in `/root/acore-data/`
- Python MCP server, run via `/root/acore-data/.venv/bin/python3 /root/acore-data/server.py`
- Key architecture: `server.py` → `tools/*.py` → `core/type_resolver.py` → `core/resolvers/*.py`
- Registry metadata in `datastore_registry.json`
- MCP config at `/root/.config/opencode/opencode.jsonc`
