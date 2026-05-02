# Polymorphic Resolver Implementation Plan

## Overview

Several AzerothCore database tables have **polymorphic fields** — columns whose meaning
changes depending on a "type" discriminator column. Without type-conditional resolution,
these fields are opaque integers to AI agents. This document describes the plan for
adding resolvers for the remaining polymorphic tables, following the patterns established
by `gameobject_template` and `conditions` resolvers in `core/type_resolver.py`.

## Status

| Task | Status | Commit | Lines Added |
|------|--------|--------|-------------|
| 1. smart_scripts resolver | DONE | `9418931` | +354 resolver, +80 test, +26 registry |
| 2. achievement_criteria_data resolver | DONE | `9418931` | +130 resolver, +40 enum map, +35 test |
| 3. item_template annotations | DONE | pending | +4 grouped field notes, +1 Armor note (rest done prior) |
| 4. Spell DBC annotations | DONE | pending | +51 Effect* field notes |

## Existing Patterns (Updated)

Five resolvers exist in `core/type_resolver.py` (1504 lines total):

| Resolver | Lines | Pattern | Table | Tests |
|----------|-------|---------|-------|-------|
| `_resolve_gameobject_fields()` | ~80 | type_field_mappings from registry | gameobject_template | 0 |
| `_resolve_quest_fields()` | ~120 | Enriched resolution (starters, enders, POIs, chain) | quest_template | 5 |
| `_resolve_condition_fields()` | ~250 | Polymorphic: 2 independent type axes, enum maps | conditions | 6 |
| `_resolve_smart_script_fields()` | ~350 | Triple-polymorphic: event/action/target axes | smart_scripts | 10 |
| `_resolve_achievement_criteria_fields()` | ~130 | Simple polymorphic: type→value1/value2 | achievement_criteria_data | 5 |

**Dispatcher routing** in `resolve_type_fields()` at `core/type_resolver.py:137-160`:
```python
if sql_table == "gameobject_template": ...
if sql_table == "quest_template": ...
if sql_table == "conditions": ...
if sql_table == "smart_scripts": ...
if sql_table == "achievement_criteria_data": ...
# Generic fallback for all others
```

**Helper functions** available for reuse:
- `_resolve_sql_ref(server, table, id, id_col)` → `Optional[str]` — resolves SQL FK to name
- `_resolve_dbc_ref(server, dbc_name, id, id_col)` → `Optional[str]` — resolves DBC FK to name
- `_resolve_loot_ref(server, table, loot_id, id_col, max)` → `Optional[Dict]` — loot expansion

**Test pattern** in `tests/test_integration.py` (767 lines, 56 tests):
- Each resolver gets a `TestXxxResolution` class
- Tests use `call_query()` helper with `resolve=True`
- Resolved data is in `result["metadata"]["$resolved_fields"]`

---

## Task 1: smart_scripts — Triple-Polymorphic Resolver **DONE**

### Completed Implementation (commit `9418931`)

**What was built:** Full triple-polymorphic resolver with 79 event enum names, 183 action enum names, 42 target enum names. Covers ~90% of row space by resolving the most impactful event/action/target types.

**Key differences from plan:**
- EmoteId DBC is `Emotes` (not `GossipMenuStatus`) — fixed during implementation
- Events 41-51 (TRANSPORT_*, QUEST_ACCEPTED/COMPLETION/REWARDED/FAIL, INSTANCE_PLAYER_ENTER) added from source code discovery
- KILL event param resolver added for creature entry resolution
- Registry needed 26 new SQL column mappings (event_type, action_type, target_type, all params, coords) — original registry only had 12 fields with wrong C++ names

**Tests:** 10 tests covering CAST spell, SUMMON_CREATURE entry, TALK creature_text, SUMMON_GO entry, UPDATE_IC/LINK enum translation, CLOSEST_CREATURE target, OFFER_QUEST quest, negative guid annotation, multi-row filter

### Background

**52,392 rows** in the database. The most complex polymorphic table: three independent
type axes, each reinterpreting 6 param fields.

### Table Schema

```
entryorguid     INT SIGNED      PRI  (entry > 0 or guid < 0)
source_type     TINYINT UNSIGNED PRI  (0=creature, 1=gameobject, 2=areatrigger, 9=timed_actionlist)
id              SMALLINT UNSIGNED PRI  (incremental row ID)
link            SMALLINT UNSIGNED PRI  (linked event ID)
event_type      TINYINT UNSIGNED      POLYMORPHIC AXIS 1
event_phase_mask SMALLINT UNSIGNED
event_chance    TINYINT UNSIGNED
event_flags     SMALLINT UNSIGNED
event_param1-6  INT UNSIGNED          MEANING CHANGES BY event_type
action_type     TINYINT UNSIGNED      POLYMORPHIC AXIS 2
action_param1-6 INT UNSIGNED          MEANING CHANGES BY action_type
target_type     TINYINT UNSIGNED      POLYMORPHIC AXIS 3
target_param1-4 INT UNSIGNED          MEANING CHANGES BY target_type
target_x/y/z/o  FLOAT                 POSITIONAL (some target_types)
comment         TEXT
```

### Axis 1: event_type (66 active values)

Top values by row count: 0=UPDATE_IC(22k), 61=LINK(7k), 1=UPDATE_OOC(2.4k),
2=HEALTH_PCT(2.4k), 4=AGGRO(1.9k), 38=DATA_SET(1.7k), 9=RANGE(1.5k),
11=RESPAWN(1.4k)

Key param patterns:
- **Timer events** (0,1,9,12,60,74): param1=InitialMin, param2=InitialMax, param3=RepeatMin, param4=RepeatMax
- **Spell events** (8,23,24,31): param1=SpellID, param2=Stacks/School, param3-4=Cooldown
- **Health/Mana** (2,3,12,14): param1=Min%, param2=Max%, param3-4=Repeat
- **Kill/Summon** (5,17,35,82): param1=CreatureID(0=all), param2-4=Cooldown
- **Quest events** (19,20): param1=QuestID(0=any), param2-3=Cooldown
- **Escort events** (39-40,55-58): param1=PointID, param2=pathId
- **Gossip** (62): param1=MenuID, param2=OptionID

**References to resolve:**
- event_type=8 SPELLHIT: param1 → Spell DBC
- event_type=11 RESPAWN: param2 → MapEntry DBC, param3 → AreaTable DBC
- event_type=17 SUMMONED_UNIT: param1 → creature_template
- event_type=19/20 QUEST: param1 → quest_template
- event_type=22 EMOTE: param1 → Emotes DBC
- event_type=23/24 AURA: param1 → Spell DBC
- event_type=62 GOSSIP: param1 → gossip_menu, param2 → gossip_menu_option
- event_type=68/69 GAME_EVENT: param1 → game_event table
- event_type=75 DISTANCE_CREATURE: param1 → creature guid, param2 → creature_template
- event_type=76 DISTANCE_GAMEOBJECT: param1 → gameobject guid, param2 → gameobject_template

### Axis 2: action_type (~183 values)

Top values: 11=CAST(17.5k), 1=TALK(6.7k), 80=STORE_VARIABLE(2.3k),
45=SET_DATA(1.8k), 12=SUMMON_CREATURE(1.8k), 41=FORCE_DESPAWN(1.7k)

Key param patterns:
- **CAST** (11): param1=SpellID, param2=castFlags, param3=triggeredFlags, param4=limitTargets
- **TALK** (1): param1=creature_text.GroupID, param2=duration
- **SUMMON_CREATURE** (12): param1=creature_template.entry, param2=SummonType, param3=duration
- **SUMMON_GO** (50): param1=gameobject_template.entry, param2=despawnTime
- **QUEST actions** (6,7,15,26,33): param1=quest_template.id or creature_template.entry
- **MORPH/MOUNT** (3,43): param1=creature_template.entry
- **EMOTE** (5,10,17): param1=EmoteId
- **FACTION** (2): param1=FactionID
- **SOUND** (4): param1=SoundId
- **ESCORT** (53-55): param2=waypoints.entry, param3=canRepeat, param4=quest_template.id

**References to resolve:**
- action_type=1 TALK: param1 → creature_text table
- action_type=3 MORPH: param1 → creature_template
- action_type=4 SOUND: param1 → SoundEntries DBC
- action_type=5 PLAY_EMOTE: param1 → Emotes DBC
- action_type=6 FAIL_QUEST / 7 OFFER_QUEST / 15 CALL_AREA / 26 CALL_GROUP: param1 → quest_template
- action_type=11 CAST: param1 → Spell DBC
- action_type=12 SUMMON_CREATURE: param1 → creature_template
- action_type=29 FOLLOW: param3 → creature_template
- action_type=33 CALL_KILLEDMONSTER: param1 → creature_template
- action_type=36 UPDATE_TEMPLATE: param1 → creature_template
- action_type=43 MOUNT: param1 → creature_template
- action_type=50 SUMMON_GO: param1 → gameobject_template
- action_type=52 ACTIVATE_TAXI: param1 → TaxiNodes DBC
- action_type=53 ESCORT_START: param2=waypoints.entry, param4=quest_template.id

### Axis 3: target_type (~42 values)

Top values: 1=SELF(28k), 2=VICTIM(7.8k), 7=ACTION_INVOKER(3.7k),
8=POSITION(2.8k), 19=CLOSEST_CREATURE(2.3k)

Key param patterns:
- **Position-based** (8): target_x/y/z/o used
- **Creature-by-entry** (9,11,19): param1=creature_template.entry, param2=distance
- **Creature-by-guid** (10): param1=creature.guid
- **GO-by-entry** (13,15,20): param1=gameobject_template.entry, param2=distance
- **GO-by-guid** (14): param1=gameobject.guid
- **Player range** (17,18,21): param1=distance, param2=maxCount

**References to resolve:**
- target_type=9/11/19: param1 → creature_template
- target_type=10: param1 → creature (guid lookup)
- target_type=13/15/20: param1 → gameobject_template
- target_type=14: param1 → gameobject (guid lookup)

### Implementation Plan

#### File: `generators/patch_smart_scripts_registry.py`

Create the registry patch script. Replace the existing `SmartScriptHolder` entry with
rich annotations:

1. **Add enum name maps** as Python dicts in the resolver (not in registry — too large):
   - `_SAI_EVENT_TYPE_NAMES` (~66 entries)
   - `_SAI_ACTION_TYPE_NAMES` (~183 entries)
   - `_SAI_TARGET_TYPE_NAMES` (~42 entries)

2. **Add registry field notes** for the polymorphic columns:
   - `event_type`: "Polymorphic axis 1. See SmartEvent enum in SmartScriptMgr.h. Meaning of event_param1-6 depends on this value."
   - `event_param1-6`: "Meaning depends on event_type. Timer events: min/max/repeat. Spell events: SpellID/School/Cooldown. Quest events: QuestID/Cooldown."
   - `action_type`: "Polymorphic axis 2. See SmartAction enum in SmartScriptMgr.h."
   - `action_param1-6`: "Meaning depends on action_type. CAST: SpellID/flags. TALK: GroupID/duration. SUMMON: CreatureID/SummonType/duration."
   - `target_type`: "Polymorphic axis 3. See SmartTarget enum in SmartScriptMgr.h."
   - `target_param1-4`: "Meaning depends on target_type. Creature/GO targets: entry. Position targets: unused (use x/y/z)."

3. **Add source_type notes** with entryorguid resolution semantics:
   - source_type=0 → entryorguid references creature_template (positive) or creature.guid (negative)
   - source_type=1 → entryorguid references gameobject_template (positive) or gameobject.guid (negative)
   - source_type=2 → entryorguid references areatrigger_scripts.entry

#### File: `core/type_resolver.py`

Add `_resolve_smart_script_fields()` (~300-400 lines):

1. **Entry resolution**: Resolve `entryorguid` based on `source_type`:
   - source_type=0, positive → creature_template name
   - source_type=0, negative → creature guid lookup
   - source_type=1, positive → gameobject_template name
   - source_type=2 → areatrigger_scripts

2. **Enum name translation**: Translate all three type axes:
   - event_type → enum name (e.g., 0 → "UPDATE_IC", 61 → "LINK")
   - action_type → enum name (e.g., 11 → "CAST", 1 → "TALK")
   - target_type → enum name (e.g., 1 → "SELF", 2 → "VICTIM")

3. **Event param resolution**: Resolve event_param1-6 based on event_type.
   Only resolve the most impactful event types (cover ~90% of rows):
   - Types 8,23,24,31 (spell events): param1 → Spell DBC
   - Types 19,20 (quest events): param1 → quest_template
   - Type 11 (respawn): param2 → Map DBC, param3 → Area DBC
   - Types 17,35,82 (summon events): param1 → creature_template
   - Type 62 (gossip): param1 → gossip_menu
   - Type 22 (emote): param1 → Emotes DBC
   - Types 75,76 (distance): param2 → creature/GO template

4. **Action param resolution**: Resolve action_param1-6 based on action_type.
   Only resolve the most impactful action types (cover ~90% of rows):
   - Type 11 (CAST): param1 → Spell DBC
   - Type 12 (SUMMON_CREATURE): param1 → creature_template
   - Types 6,7,15,26,33 (quest/kill): param1 → quest/creature template
   - Type 50 (SUMMON_GO): param1 → gameobject_template
   - Type 1 (TALK): param1 → creature_text
   - Types 3,43 (morph/mount): param1 → creature_template
   - Type 4 (SOUND): param1 → SoundEntries DBC

5. **Target param resolution**: Resolve target_param1-4 based on target_type:
   - Types 9,11,19 (creature range/distance/closest): param1 → creature_template
   - Types 13,15,20 (GO range/distance/closest): param1 → gameobject_template

6. **Dispatcher**: Add routing at `resolve_type_fields()`:
   ```python
   if sql_table == "smart_scripts":
       return _resolve_smart_script_fields(server, reg_entry, rows, resolve_filter, resolve_max)
   ```

#### File: `tests/test_integration.py`

Add `TestSmartScriptResolution` class with 8-10 tests:

1. Test CAST action resolves param1 as Spell DBC name
2. Test SUMMON_CREATURE action resolves param1 as creature name
3. Test UPDATE_IC event translates event_type enum name
4. Test TALK action resolves param1 as creature_text group
5. Test target_type=CLOSEST_CREATURE resolves param1 as creature
6. Test source_type=0 resolves entryorguid as creature_template
7. Test multi-row filter query with resolve
8. Test LINK event (event_type=61) gets enum translation
9. Test QUEST_OFFER action resolves param1 as quest name
10. Test SUMMON_GO action resolves param1 as gameobject name

### Wiki Reference

Full param mapping tables at `~/acore-wiki/docs/smart_scripts.md` (619 lines):
- event_type table: lines 156-236 (66 event types with param1-6 meanings)
- action_type table: lines 239-410 (183 action types with param1-6 meanings)
- target_type table: lines 425-462 (42 target types with param1-4 meanings)
- Cast flags: lines 490-500
- Triggered flags: lines 503-526
- Summon types: lines 540-549

### C++ Source Reference

- Enums: `/root/azerothcore-wotlk/src/server/game/AI/SmartScripts/SmartScriptMgr.h`
  - SmartEvent enum: lines 97-202
  - SmartAction enum: lines 540-731
  - SmartTarget enum: lines 1549-1593
- Loading: `SmartScriptMgr.cpp` lines 716+
- Execution: `SmartScript.cpp` (5537 lines)

### Estimated Scope

- Registry patch: ~80 lines
- Resolver function: ~350 lines
- Enum maps: ~120 lines
- Tests: ~80 lines
- **Total: ~630 lines**

---

## Task 2: achievement_criteria_data — Simple Polymorphic Resolver **DONE**

### Background

**2,816 rows** in the database. Simple 2-field polymorphism driven by `type` column.

### Table Schema

```
criteria_id  MEDIUMINT        PRI  (→ AchievementCriteria DBC)
type         TINYINT UNSIGNED PRI  POLYMORPHIC AXIS (0-24)
value1       MEDIUMINT UNSIGNED    MEANING CHANGES BY type
value2       MEDIUMINT UNSIGNED    MEANING CHANGES BY type
ScriptName   char(64)
```

### Type Values (24 types)

| Type | Name | value1 | value2 | Row Count |
|------|------|--------|--------|-----------|
| 0 | TYPE_NONE | unused | unused | — |
| 1 | TYPE_T_CREATURE | creature_template.entry | unused | 83 |
| 2 | TYPE_T_PLAYER_CLASS_RACE | class ID | race ID | 55 |
| 3 | TYPE_T_PLAYER_LESS_HEALTH | health pct | unused | 1 |
| 4 | TYPE_T_PLAYER_DEAD | faction | unused | 1 |
| 5 | TYPE_S_AURA | spell_id | effect_index | 38 |
| 6 | TYPE_S_AREA | AreaTable ID | unused | 95 |
| 7 | TYPE_T_AURA | spell_id | effect_index | 35 |
| 8 | TYPE_VALUE | comparison value | comp_type(0-4) | 14 |
| 9 | TYPE_T_LEVEL | min level | unused | 15 |
| 10 | TYPE_T_GENDER | gender(0/1) | unused | 10 |
| 11 | TYPE_SCRIPT | script ID | unused | 271 |
| 12 | TYPE_MAP_DIFFICULTY | difficulty(0-3) | unused | 1,327 |
| 13 | TYPE_MAP_PLAYER_COUNT | player count | unused | — |
| 14 | TYPE_T_TEAM | team(469/67) | unused | 10 |
| 15 | TYPE_S_DRUNK | drunk state(0-3) | unused | 6 |
| 16 | TYPE_HOLIDAY | Holiday DBC ID | unused | 41 |
| 17 | TYPE_BG_LOSS_TEAM_SCORE | min score | max score | — |
| 18 | TYPE_INSTANCE_SCRIPT | script ID | unused | 188 |
| 19 | TYPE_S_EQUIPED_ITEM | item level | item quality | 32 |
| 20 | TYPE_MAP_ID | map_id | unused | 51 |
| 21 | TYPE_S_PLAYER_CLASS_RACE | class ID | race ID | 20 |
| 22 | TYPE_NTH_BIRTHDAY | birthday number | unused | 2 |
| 23 | TYPE_S_KNOWN_TITLE | title ID | unused | 58 |

### References to Resolve

| type | value1 target | value2 target |
|------|--------------|--------------|
| 1 | creature_template (entry) | — |
| 5,7 | Spell DBC | — |
| 6 | AreaTable DBC | — |
| 20 | Map DBC | — |
| 16 | Holiday DBC | — |

### Implementation Plan

#### File: `generators/patch_achievement_criteria_registry.py`

Add notes to the existing `AchievementCriteriaData` registry entry:
- `type` field: inline enum table with all 24 type values and value1/value2 semantics
- `value1`: "Meaning depends on type. T_CREATURE(1)=creature_entry, S_AURA(5)/T_AURA(7)=spell_id, S_AREA(6)=area_id, MAP_ID(20)=map_id, etc."
- `value2`: "Meaning depends on type. T_PLAYER_CLASS_RACE(2)=race_id, S_AURA(5)/T_AURA(7)=effect_index, VALUE(8)=comp_type, etc."

#### File: `core/type_resolver.py`

Add `_resolve_achievement_criteria_fields()` (~100 lines):

1. Enum name translation: type → TYPE_T_CREATURE, TYPE_S_AURA, etc.
2. Resolve value1 based on type:
   - type=1 → creature_template
   - type=5,7 → Spell DBC
   - type=6 → AreaTable DBC
   - type=20 → Map DBC
   - type=16 → Holiday DBC
3. Resolve value2 where applicable:
   - type=2,21 → race description
   - type=5,7 → effect index annotation
   - type=8 → comparison type name

4. **Dispatcher**: Add routing:
   ```python
   if sql_table == "achievement_criteria_data":
       return _resolve_achievement_criteria_fields(server, reg_entry, rows, resolve_filter, resolve_max)
   ```

#### File: `tests/test_integration.py`

Add `TestAchievementCriteriaResolution` class with 4-5 tests:

1. Test TYPE_T_CREATURE resolves value1 as creature name
2. Test TYPE_S_AURA resolves value1 as spell name
3. Test TYPE_MAP_DIFFICULTY translates type enum name
4. Test multi-row filter query with resolve
5. Test TYPE_MAP_ID resolves value1 as map name

### Wiki Reference

`~/acore-wiki/docs/achievement_criteria_data.md` (204 lines) — complete type→value1/value2 mapping.

### Estimated Scope

- Registry patch: ~50 lines
- Resolver function: ~100 lines
- Tests: ~50 lines
- **Total: ~200 lines**

---

## Task 3: item_template — Class/Subclass Relevance Annotations **DONE**

### Completed Implementation

**What was done:** Patched class/subclass relevance notes for ItemTemplate fields in `datastore_registry.json`. Most flat-field annotations (class, subclass, ContainerSlots, FoodType, delay, ammo_type, block, GemProperties, socketBonus) were added in prior session. Final session completed 4 grouped-field annotations and Armor field.

**Generator:** `generators/patch_polymorphic_annotations.py` — single script handles both Task 3 and Task 4 patches.

**Patched fields (4):**
- `stat_type1..10`: Added class=2/4 relevance + ItemModType enum values
- `dmg_min/max/type1..2`: Added class=2(Weapon) relevance + SpellSchool values
- `socketColor_1..3`: Added class=2/4 relevance + SocketColors.dbc reference
- `Armor`: Added class=4(Armor) relevance note

### Background

**46,096 rows**. `item_template` is NOT sharply polymorphic like gameobject_template
(data fields don't completely change meaning), but many fields are only relevant for
certain `class`/`subclass` combinations, making them noise for AI agents.

This task is **annotations-only** — no resolver needed. Just add notes to the registry
explaining which fields matter for which class/subclass.

### Class Values (17)

| class | Name | Relevant Fields |
|-------|------|----------------|
| 0 | Consumable | FoodType, spellid_1-5, spelltrigger_1-5, spellcharges_1-5 |
| 1 | Container | ContainerSlots |
| 2 | Weapon | dmg_min1-2, dmg_max1-2, dmg_type1-2, delay, ammo_type, stat_type1-10 |
| 3 | Gem | GemProperties, socketBonus |
| 4 | Armor | armor, block, stat_type1-10, socketColor_1-3, socketBonus |
| 5 | Reagent | — (minimal fields) |
| 6 | Projectile | ammo_type |
| 7 | Trade Goods | — |
| 8 | Generic | — |
| 9 | Recipe | spellid_1-5 (learning spells) |
| 10 | Money | — |
| 11 | Quiver | ContainerSlots |
| 12 | Quest | startquest |
| 13 | Key | — |
| 14 | Permanent | — |
| 15 | Miscellaneous | — |
| 16 | Glyph | GemProperties (spell category) |

### Implementation Plan

#### File: `generators/patch_item_template_registry.py`

Add notes to existing `ItemTemplate` registry entry fields:
- `class`: "Item class determines which fields are relevant. 0=Consumable(FoodType,spells), 1=Container(ContainerSlots), 2=Weapon(dmg,stats), 3=Gem(GemProperties), 4=Armor(armor,block,stats,sockets), 6=Projectile(ammo_type), 9=Recipe(spellid=learning), 12=Quest(startquest), 16=Glyph."
- `subclass`: "Subclass meaning depends on class. Weapon(2): 0=1H_Axe,1=2H_Axe,...,13=Fist,14=Misc,15=Dagger,16=Thrown,17=Spear,18=Crossbow,19=Wand,20=Fishing. Armor(4): 0=Misc,1=Cloth,2=Leather,3=Mail,4=Plate,5=Buckler,6=Shield,7=Libram,8=Idol,9=Totem,10=Sigil."
- `stat_type1-10`: "Only relevant for class=2(Weapon) and class=4(Armor). Value references ItemModType enum."
- `dmg_min/max/type1-2`: "Only relevant for class=2(Weapon)."
- `ContainerSlots`: "Only relevant for class=1(Container) and class=11(Quiver)."
- `FoodType`: "Only relevant for class=0(Consumable) subclass 5(Food&Drink)."
- `GemProperties`: "Only relevant for class=3(Gem) and class=16(Glyph)."
- `socketColor_1-3`, `socketBonus`: "Only for equipment with sockets (class 2,4 with socketColor>0)."

#### No resolver needed — annotations-only task.

### Wiki Reference

`~/acore-wiki/docs/item_template.md` (1,164 lines) — complete class/subclass/field relevance.

### Estimated Scope

- Registry patch: ~80 lines
- **Total: ~80 lines** (no resolver, no tests needed)

---

## Task 4: Spell DBC — Effect/Aura Polymorphic Annotations **DONE**

### Completed Implementation

**What was done:** Added comprehensive polymorphic annotations for all Effect* fields across 3 effect slots in `SpellEntry` registry entry (51 fields patched). Previous attempt failed because field names use bracket notation (`Effect[0]`) not underscore (`Effect_1`). Script fixed to match actual registry keys.

**Key fix:** Registry SpellEntry uses string-indexed numeric keys ("71", "72", etc.) referencing DBC column indices, not named fields like ItemTemplate. Field names are `Effect[0]`, `EffectBasePoints[0]`, etc. with 3 slots (0,1,2).

**Generator:** `generators/patch_polymorphic_annotations.py` — Task4_patches dict with 51 entries covering all Effect* indices (71-124 plus RealPointsPerLevel 77-79).

**Patched field groups (17 families x 3 slots + extras):**
- Effect[0-2]: SpellEffect enum (164 values) — explains polymorphism driver
- EffectBasePoints[0-2]: Value meaning by Effect type
- EffectApplyAuraName[0-2]: SPELL_AURA enum (317 values) — nested polymorphism
- EffectMiscValue[0-2]: Most polymorphic field — depends on both Effect + Aura
- EffectImplicitTargetA/B[0-2]: Targeting enums
- EffectTriggerSpell[0-2]: Triggered spell ID references
- EffectDieSides, RealPointsPerLevel, Mechanic, RadiusIndex, Amplitude, ValueMultiplier, ChainTarget, ItemType, MiscValueB, PointsPerComboPoint, SpellClassMask

### Background

~70,000-100,000 spells in the DBC. The deepest polymorphism in the system:
Effect[1-3] determines field meanings, and when Effect=APPLY_AURA(6), ApplyAuraName
creates a **nested** second level of polymorphism.

This task is **annotations-only** — DBC resolution is architecturally different from
SQL resolution and would require changes to the DBC query path. Add notes to help
agents understand the field relationships.

### Polymorphic Fields Per Effect Slot (3 slots: 0, 1, 2)

Each spell has 3 effect slots. For each slot `N`:
- `Effect[N]` (SPELL_EFFECT enum, 164 values) determines meaning of:
  - `EffectBasePoints[N]`, `EffectDieSides[N]`
  - `EffectImplicitTargetA[N]`, `EffectImplicitTargetB[N]`
  - `EffectApplyAuraName[N]` (when Effect=6, creates nested polymorphism with 317 SPELL_AURA values)
  - `EffectMiscValue[N]`, `EffectMiscValueB[N]`
  - `EffectRadiusIndex[N]`
  - `EffectTriggerSpell[N]`
  - `EffectSpellClassMask[A/B/C][N]`
  - `EffectAmplitude[N]`, `EffectMultipleValue[N]`

### Nested Level: When Effect=APPLY_AURA(6)

`EffectApplyAuraName[N]` (317 SPELL_AURA values) further reinterprets:
- `EffectMiscValue[N]` — e.g., SPELL_AURA_MOD_RESISTANCE(22)=schoolMask, SPELL_AURA_TRANSFORM(56)=creatureID
- `EffectBasePoints[N]` — amount/value
- `EffectMiscValueB[N]` — secondary parameter

### Implementation Plan

#### File: `generators/patch_spell_registry.py`

Add notes to the existing `SpellEntry` registry entry fields:
- `Effect_1/2/3`: "Spell effect type (SPELL_EFFECT enum, 164 values). Determines meaning of all Effect* fields for this slot. Common: 2=SCHOOL_DAMAGE, 6=APPLY_AURA, 28=SUMMON, 36=LEARN_SPELL, 51=TRANS_DOOR, 76=SUMMON_GAMEOBJECT."
- `EffectApplyAuraName_1/2/3`: "Only relevant when Effect=6(APPLY_AURA). SPELL_AURA enum with 317 values. Further reinterprets MiscValue and BasePoints."
- `EffectMiscValue_1/2/3`: "Meaning depends on Effect type. APPLY_AURA: depends on aura name (creatureID, schoolMask, skillID, etc.). SUMMON: creature_entry. LEARN_SPELL: spellID."
- `EffectTriggerSpell_1/2/3`: "Spell ID triggered by this effect. Relevant for TRIGGER_SPELL(38), LEARN_SPELL(36), etc."
- `EffectImplicitTargetA/B_1/2/3`: "Targets enum (Targets.h). 1=self, 6=hostile, 8=area, 15=location, 25=player, 40=gameobject."

#### No resolver needed — annotations-only task.

### Wiki Reference

- `~/acore-wiki/docs/spell-effects-reference.md` (556 lines) — Effect types with MiscValue mappings
- `~/acore-wiki/docs/spell-aura-reference.md` (488 lines) — Aura types with MiscValue mappings

### C++ Source Reference

- SpellEffects enum: `/root/azerothcore-wotlk/src/server/shared/SharedDefines.h` lines 765-932
- SpellAuraDefines enum: `/root/azerothcore-wotlk/src/server/game/Spells/Auras/SpellAuraDefines.h` (~1600 lines)

### Estimated Scope

- Registry patch: ~60 lines
- **Total: ~60 lines** (annotations only)

---

## Implementation Order

| Order | Task | Scope | Impact |
|-------|------|-------|--------|
| 1 | smart_scripts resolver | ~630 lines | EXTREME — 52k rows, 291 type interpretations |
| 2 | achievement_criteria_data resolver | ~200 lines | HIGH — 2.8k rows, simple 2-field polymorphism |
| 3 | item_template annotations | ~80 lines | HIGH — 46k rows, class/subclass relevance |
| 4 | Spell DBC annotations | ~60 lines | EXTREME complexity but annotations-only |

### Commit Strategy

- Task 1: Single commit with detailed message (resolver + registry + tests)
- Task 2: Single commit (quick win)
- Tasks 3+4: Can be combined into one commit (both annotations-only)

### Testing Requirements

After each task:
1. Run `python3 -m pytest tests/test_integration.py -v` — all tests must pass
2. Run `python3 -m py_compile core/type_resolver.py` — syntax check
3. Verify resolver output with manual query against real DB

### Environment

```
DB_HOST=127.0.0.1 DB_USER=acore DB_PASSWORD=acore DB_NAME=acore_world
MCP server config: opencode.jsonc
Test runner: pytest
```
