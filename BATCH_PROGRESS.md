# Batch Resolution Progress

## Phases

- [x] Phase 0-7 (completed previously)
- [x] Phase 8A: Persistent TTL cache in ref_utils.py — `2700b1c`
- [x] Phase 8B: Batch resolve_loot_ref item lookups — `06289ca`
- [x] Phase 8C: Pre-warm smart_scripts cache — `1d6552c`
- [x] Phase 8D: Pre-warm _resolve_generic + remaining resolvers — `b51d459`
- [x] Cleanup: guard `if "sql" in allowed`, remove dead batch_cache.py, update this file (uncommitted)
- [x] Phase 9E: Spell -> Conditions cross-reference resolver with pre-warming (uncommitted)

## Test Results

| Phase | Status | Tests | Commit |
|---|---|---|---|
| 8A TTL Cache | done | +5 unit tests | 2700b1c |
| 8B Batch Loot | done | 90 pass | 06289ca |
| 8C Smart Scripts | done | 90 pass | 1d6552c |
| 8D Remaining | done | 90 pass | b51d459 |
| **9E Spell Conditions** | **done** | **+5 pass (75 total)** | **_pending_** |

## Performance Target

| Resolver (rows) | Before | After |
|---|---|---|
| smart_scripts (20) | ~200 queries | ~10 batch |
| conditions (20) | ~80 queries | ~8 batch |
| creature_template (20, generic) | ~100 queries | ~5 batch |
| gameobject_template (10) | ~50 queries | ~5 batch |
| Spell (48649, 191 conds) | ~200 queries | ~6 batch (creature/item/quest/etc.) |
| Subsequent requests (any) | same | ~0 (TTL cache) |
