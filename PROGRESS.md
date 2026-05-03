# acore-data Tool Improvements - Progress Tracker

## Context
Improving the acore-data MCP tools based on analysis of the "A Little Slime Goes a Long Way" quest flow investigation.
The goal is to reduce round trips and improve readability of query results.

## Task List

### P0 - Critical
- [x] **Quest resolver: Resolve item references** ✅
  - Resolve `RequiredItemId1..6` to item names
  - Resolve `StartItem` to item name
  - Resolve `RewardItem1..4` to item names
  - Resolve `RewardChoiceItemID1..6` to item names
  - File: `core/resolvers/quest.py`

- [x] **Item resolver: Resolve spell fields** ✅
  - Resolve `spellid_1..5` to spell names
  - Include spell conditions for each spell
  - File: `core/resolvers/item.py`

### P1 - Important
- [x] **Spell effect/target type enums** ✅
  - Add `SPELL_EFFECT_NAMES` dict
  - Add `SPELL_TARGET_NAMES` dict (ImplicitTargetA/B)
  - Add `ITEM_CLASS_NAMES`, `ITEM_SUBCLASS_*` dicts
  - File: `core/enums.py`

- [x] **Compact DBC annotation output** ✅
  - Strip zero/null fields from DBC annotation results
  - File: `core/annotation.py`

### P2 - Nice to have
- [ ] **resolve_depth parameter**
  - Allow multi-hop resolution (e.g., quest → item → spell)
  - Files: `tools/query.py`, `core/type_resolver.py`

- [ ] **Multi-conditional reference handling**
  - Handle fields like QuestSortID that have conditional references
  - Files: `core/type_resolver.py` or specialized resolvers

### P3 - Polish
- [x] **Item class/subclass enum decoding** ✅
  - Add ITEM_CLASS_NAMES, ITEM_SUBCLASS_NAMES dicts
  - Resolve in item resolver
  - File: `core/enums.py`, `core/resolvers/item.py`

## Milestones
- **Milestone 1**: P0 + P1 + P3 complete ✅ (quest + item resolution, enums, compact DBC, class decoding)
- **Milestone 2**: P2 complete (resolve_depth, multi-conditional refs) - pending

## Testing
- Test with quest 4512/4513 (A Little Slime Goes a Long Way)
- Test with item 11912/11914 (Package/Empty Ooze Jars)
- Test with SpellEntry 15698/15699 (Filling Empty Jar spells)
- Verify existing tests still pass

## Handover Notes
- All changes are in `/root/acore-data/`
- The project is a Python MCP server
- Key architecture: `server.py` → `tools/*.py` → `core/type_resolver.py` → `core/resolvers/*.py`
- Registry metadata in `datastore_registry.json`
