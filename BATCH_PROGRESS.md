# Batch Resolution Progress

## Phases

- [x] Phase 0-7 (completed previously)
- [ ] Phase 8A: Persistent TTL cache in ref_utils.py
- [ ] Phase 8B: Batch resolve_loot_ref item lookups
- [ ] Phase 8C: Pre-warm smart_scripts cache
- [ ] Phase 8D: Pre-warm _resolve_generic + remaining resolvers

## Test Results

| Phase | Status | Tests | Commit |
|---|---|---|---|
| 8A TTL Cache | pending | - | - |
| 8B Batch Loot | pending | - | - |
| 8C Smart Scripts | pending | - | - |
| 8D Remaining | pending | - | - |

## Performance Target

| Resolver (rows) | Before | After |
|---|---|---|
| smart_scripts (20) | ~200 queries | ~10 batch |
| conditions (20) | ~80 queries | ~8 batch |
| creature_template (20, generic) | ~100 queries | ~5 batch |
| gameobject_template (10) | ~50 queries | ~5 batch |
| Subsequent requests (any) | same | ~0 (TTL cache) |
