# SQL Datastores (Other Managers)

This document lists all datastores loaded by manager singletons other than `ObjectMgr`. For architecture details, see [README.md](README.md).

## Table of Contents

- [1. SpellMgr (sSpellMgr)](#1-spellmgr-sspellmgr)
- [2. LootStore (13 Global Objects)](#2-lootstore-13-global-objects)
- [3. SmartAIMgr (sSmartScriptMgr)](#3-smartaimgr-ssmartscriptmgr)
- [4. ConditionMgr (sConditionMgr)](#4-conditionmgr-sconditionmgr)
- [5. GameEventMgr (sGameEventMgr)](#5-gameeventmgr-sgameeventmgr)
- [6. PoolMgr (sPoolMgr)](#6-poolmgr-spoolmgr)
- [7. WaypointMgr (sWaypointMgr)](#7-waypointmgr-swaypointmgr)
- [8. AchievementGlobalMgr (sAchievementMgr)](#8-achievementglobalmgr-sachievementmgr)
- [9. LFGMgr (sLFGMgr)](#9-lfgmgr-slfgmgr)
- [10. BattlegroundMgr (sBattlegroundMgr)](#10-battlegroundmgr-sbattlegroundmgr)
- [11. DisableMgr (sDisableMgr)](#11-disablemgr-sdisablemgr)
- [12. FormationMgr (sFormationMgr)](#12-formationmgr-sformationmgr)
- [13. CreatureTextMgr (sCreatureTextMgr)](#13-creaturetextmgr-screaturetextmgr)
- [14. WardenCheckMgr (sWardenCheckMgr)](#14-wardencheckmgr-swardencheckmgr)
- [15. ServerMailMgr (sServerMailMgr)](#15-servermailmgr-sservermailmgr)
- [16. TransportMgr (sTransportMgr)](#16-transportmgr-stransportmgr)
- [17. WeatherMgr (namespace)](#17-weathermgr-namespace)
- [18. OutdoorPvPMgr (sOutdoorPvPMgr)](#18-outdoorpvpmgr-soutdoorpvpmgr)
- [19. ItemEnchantmentMgr (standalone)](#19-itemenchantmentmgr-standalone)
- [20. ArenaSeasonMgr (sArenaSeasonMgr)](#20-arenaseasonmgr-sarenaseasonmgr)
- [21. AutobroadcastMgr (sAutobroadcastMgr)](#21-autobroadcastmgr-sautobroadcastmgr)
- [22. MotdMgr (sMotdMgr)](#22-motdmgr-smotdmgr)

---

## 1. SpellMgr (sSpellMgr)

**Accessor:** `sSpellMgr`
**Class:** `SpellMgr`
**Header:** `src/server/game/Spells/SpellMgr.h`
**Source:** `src/server/game/Spells/SpellMgr.cpp`

### Stores

#### SpellProcEntry -- `spell_proc_event`

| Field | C++ Type |
|-------|----------|
| SchoolMask | `uint32` |
| SpellFamilyName | `uint32` |
| SpellFamilyMask | `flag96` |
| ProcFlags | `uint32` |
| SpellTypeMask | `uint32` |
| SpellPhaseMask | `uint32` |
| HitMask | `uint32` |
| AttributesMask | `uint32` |
| DisableEffectsMask | `uint32` |
| ProcsPerMinute | `float` |
| Chance | `float` |
| Cooldown | `Milliseconds` |
| Charges | `uint32` |

**Container:** `std::unordered_map<uint32, SpellProcEntry>` (`SpellProcMap`)

#### SpellEnchantProcEntry -- `spell_enchant_proc_data`

| Field | C++ Type |
|-------|----------|
| customChance | `uint32` |
| PPMChance | `float` |
| procEx | `uint32` |
| attributeMask | `uint32` |

**Container:** `std::unordered_map<uint32, SpellEnchantProcEntry>` (`SpellEnchantProcEventMap`)

#### SpellBonusEntry -- `spell_bonus_data`

| Field | C++ Type |
|-------|----------|
| direct_damage | `float` |
| dot_damage | `float` |
| ap_bonus | `float` |
| ap_dot_bonus | `float` |

**Container:** `std::unordered_map<uint32, SpellBonusEntry>` (`SpellBonusMap`)

#### SpellThreatEntry -- `spell_threat`

| Field | C++ Type |
|-------|----------|
| flatMod | `int32` |
| pctMod | `float` |
| apPctMod | `float` |

**Container:** `std::unordered_map<uint32, SpellThreatEntry>` (`SpellThreatMap`)

#### SpellTargetPosition -- `spell_target_position`

| Field | C++ Type |
|-------|----------|
| target_mapId | `uint32` |
| target_X | `float` |
| target_Y | `float` |
| target_Z | `float` |
| target_Orientation | `float` |

**Container:** `std::map<std::pair<uint32 /*spell_id*/, SpellEffIndex>, SpellTargetPosition>` (`SpellTargetPositionMap`)

#### PetAura -- `spell_pet_auras`

| Field | C++ Type |
|-------|----------|
| auras | `PetAuraMap` (private: `std::unordered_map<uint32, uint32>`) |
| removeOnChangePet | `bool` |
| damage | `int32` |

**Container:** `std::map<uint32, PetAura>` (`SpellPetAuraMap`)

#### SpellArea -- `spell_area`

| Field | C++ Type |
|-------|----------|
| spellId | `uint32` |
| areaId | `uint32` |
| questStart | `uint32` |
| questEnd | `uint32` |
| auraSpell | `int32` |
| raceMask | `uint32` |
| gender | `Gender` |
| questStartStatus | `uint32` |
| questEndStatus | `uint32` |
| autocast | `bool` |

**Container:** `std::multimap<uint32, SpellArea>` (`SpellAreaMap`)

#### SpellChainNode -- `spell_ranks` (and DBC talent data)

| Field | C++ Type |
|-------|----------|
| prev | `SpellInfo const*` |
| next | `SpellInfo const*` |
| first | `SpellInfo const*` |
| last | `SpellInfo const*` |
| rank | `uint8` |

**Container:** `std::unordered_map<uint32, SpellChainNode>` (`SpellChainMap`)

#### SpellRequired -- `spell_required`

**Container:** `std::multimap<uint32, uint32>` (`SpellRequiredMap`)

#### SpellCooldownOverride -- `spell_cooldown_overrides`

| Field | C++ Type |
|-------|----------|
| RecoveryTime | `uint32` |
| CategoryRecoveryTime | `uint32` |
| StartRecoveryTime | `uint32` |
| StartRecoveryCategory | `uint32` |

**Container:** `std::map<uint32, SpellCooldownOverride>` (`SpellCooldownOverrideMap`)

#### CreatureImmunities -- `creature_immunities`

| Field | C++ Type |
|-------|----------|
| School | `std::bitset<MAX_SPELL_SCHOOL>` |
| DispelType | `std::bitset<DISPEL_MAX>` |
| Mechanic | `std::bitset<MAX_MECHANIC>` |
| Effect | `std::vector<SpellEffects>` |
| Aura | `std::vector<AuraType>` |
| ImmuneAoE | `bool` |
| ImmuneChain | `bool` |

**Container:** `std::unordered_map<int32, CreatureImmunities>` (`CreatureImmunitiesMap`)

#### SpellLearnSkillNode -- DBC `SkillLineAbilityEntry`

| Field | C++ Type |
|-------|----------|
| skill | `uint16` |
| step | `uint16` |
| value | `uint16` |
| maxvalue | `uint16` |

**Container:** `std::unordered_map<uint32, SpellLearnSkillNode>` (`SpellLearnSkillMap`)

---

## 2. LootStore (13 Global Objects)

**Header:** `src/server/game/Loot/LootMgr.h`
**Source:** `src/server/game/Loot/LootMgr.cpp`

13 global `LootStore` objects, each loading a different SQL loot template table:

| Global Object | SQL Table |
|---------------|-----------|
| `LootTemplates_Creature` | `creature_loot_template` |
| `LootTemplates_Disenchant` | `disenchant_loot_template` |
| `LootTemplates_Fishing` | `fishing_loot_template` |
| `LootTemplates_Gameobject` | `gameobject_loot_template` |
| `LootTemplates_Item` | `item_loot_template` |
| `LootTemplates_Mail` | `mail_loot_template` |
| `LootTemplates_Milling` | `milling_loot_template` |
| `LootTemplates_Pickpocketing` | `pickpocketing_loot_template` |
| `LootTemplates_Prospecting` | `prospecting_loot_template` |
| `LootTemplates_Reference` | `reference_loot_template` |
| `LootTemplates_Skinning` | `skinning_loot_template` |
| `LootTemplates_Spell` | `spell_loot_template` |
| `LootTemplates_Player` | `player_loot_template` |

### LootStoreItem

| Field | C++ Type |
|-------|----------|
| itemid | `uint32` |
| reference | `int32` |
| chance | `float` |
| needs_quest | `bool` (bitfield) |
| lootmode | `uint16` |
| groupid | `uint8` (7-bit bitfield) |
| mincount | `uint8` |
| maxcount | `uint8` |
| conditions | `ConditionList` |

**Container:** Each `LootStore` holds `std::unordered_map<uint32, LootTemplate*>` (`LootTemplateMap`), where each `LootTemplate` contains `std::list<LootStoreItem*>` (`LootStoreItemList`).

---

## 3. SmartAIMgr (sSmartScriptMgr)

**Accessor:** `sSmartScriptMgr` / `SmartAIMgr::instance()`
**Class:** `SmartAIMgr`
**Header:** `src/server/game/AI/SmartScripts/SmartScriptMgr.h`
**Source:** `src/server/game/AI/SmartScripts/SmartScriptMgr.cpp`

### SmartScriptHolder -- `smart_scripts`

| Field | C++ Type |
|-------|----------|
| entryOrGuid | `int32` |
| source_type | `SmartScriptType` |
| event_id | `uint32` |
| link | `uint32` |
| event | `SmartEvent` |
| action | `SmartAction` |
| target | `SmartTarget` |
| timer | `uint32` |
| priority | `uint32` |
| active | `bool` |
| runOnce | `bool` |
| enableTimed | `bool` |

#### SmartEvent (nested in SmartScriptHolder)

| Field | C++ Type |
|-------|----------|
| type | `SMART_EVENT` |
| event_phase_mask | `uint32` |
| event_chance | `uint32` |
| event_flags | `uint32` |
| raw.param1..param6 | `uint32` (union of event-specific params) |

#### SmartAction (nested in SmartScriptHolder)

| Field | C++ Type |
|-------|----------|
| type | `SMART_ACTION` |
| raw.param1..param6 | `uint32` (union of action-specific params) |

#### SmartTarget (nested in SmartScriptHolder)

| Field | C++ Type |
|-------|----------|
| type | `SMARTAI_TARGETS` |
| x | `float` |
| y | `float` |
| z | `float` |
| o | `float` |
| raw.param1..param4 | `uint32` (union of target-specific params) |

**Container:** `std::unordered_map<int32, std::vector<SmartScriptHolder>>` (`SmartAIEventMap`), indexed by `[SMART_SCRIPT_TYPE_MAX]` (10 script types).

---

## 4. ConditionMgr (sConditionMgr)

**Accessor:** `sConditionMgr`
**Class:** `ConditionMgr`
**Header:** `src/server/game/Conditions/ConditionMgr.h`
**Source:** `src/server/game/Conditions/ConditionMgr.cpp`

### Condition -- `conditions`

| Field | C++ Type |
|-------|----------|
| SourceType | `ConditionSourceType` |
| SourceGroup | `uint32` |
| SourceEntry | `int32` |
| SourceId | `uint32` |
| ElseGroup | `uint32` |
| ConditionType | `ConditionTypes` |
| ConditionTarget | `uint8` |
| ConditionValue1 | `uint32` |
| ConditionValue2 | `uint32` |
| ConditionValue3 | `uint32` |
| NegativeCondition | `bool` |
| ErrorType | `uint32` |
| ErrorTextId | `uint32` |
| ReferenceId | `uint32` |
| ScriptId | `uint32` |

**Container:**
- `std::map<ConditionSourceType, std::map<uint32, std::list<Condition*>>>` (`ConditionContainer`)
- `std::map<uint32, std::list<Condition*>>` (`ConditionReferenceContainer`)
- `std::map<uint32, std::map<uint32, std::list<Condition*>>>` (`CreatureSpellConditionContainer`) for vehicle spells and spell click events
- `std::map<uint32, std::map<uint32, std::list<Condition*>>>` (`NpcVendorConditionContainer`) for NPC vendor conditions
- `std::map<std::pair<int32, uint32>, std::map<uint32, std::list<Condition*>>>` (`SmartEventConditionContainer`) for SmartAI events

---

## 5. GameEventMgr (sGameEventMgr)

**Accessor:** `sGameEventMgr`
**Class:** `GameEventMgr`
**Header:** `src/server/game/Events/GameEventMgr.h`
**Source:** `src/server/game/Events/GameEventMgr.cpp`

### GameEventData -- `game_event`

| Field | C++ Type |
|-------|----------|
| EventId | `uint32` |
| Start | `time_t` |
| End | `time_t` |
| NextStart | `time_t` |
| Occurence | `uint32` |
| Length | `uint32` |
| HolidayId | `HolidayIds` |
| HolidayStage | `uint8` |
| State | `GameEventState` |
| Conditions | `GameEventConditionMap` |
| PrerequisiteEvents | `std::set<uint16>` |
| Description | `std::string` |
| Announce | `uint8` |

**Container:** `std::vector<GameEventData>` (`GameEventDataMap`)

### GameEventFinishCondition -- `game_event_condition`

| Field | C++ Type |
|-------|----------|
| ReqNum | `float` |
| Done | `float` |
| MaxWorldState | `uint32` |
| DoneWorldState | `uint32` |

**Container:** `std::map<uint32, GameEventFinishCondition>` (`GameEventConditionMap`)

### ModelEquip -- `game_event_model_equip`

| Field | C++ Type |
|-------|----------|
| ModelId | `uint32` |
| ModelIdPrev | `uint32` |
| EquipmentId | `uint8` |
| EquipementIdPrev | `uint8` |

**Container:** `std::vector<std::list<std::pair<ObjectGuid::LowType, ModelEquip>>>` (`GameEventModelEquipMap`)

### Creature/GameObject Links -- `game_event_creature`, `game_event_gameobject`

**Container:**
- `std::vector<std::list<ObjectGuid::LowType>>` (`GameEventGuidMap`) for `GameEventCreatureGuids`
- `std::vector<std::list<ObjectGuid::LowType>>` (`GameEventGuidMap`) for `GameEventGameobjectGuids`

### Quest Links -- `game_event_creature_quest`, `game_event_gameobject_quest`

| Field | C++ Type |
|-------|----------|
| first | `uint32` (quest id) |
| second | `uint32` (quest id) |

**Container:** `std::vector<std::list<std::pair<uint32, uint32>>>` (`GameEventQuestMap`)

### NPCVendorEntry -- `game_event_npc_vendor`

| Field | C++ Type |
|-------|----------|
| Entry | `uint32` |
| Item | `uint32` |
| MaxCount | `int32` |
| Incrtime | `uint32` |
| ExtendedCost | `uint32` |

**Container:** `std::vector<std::list<NPCVendorEntry>>` (`GameEventNPCVendorMap`)

### Additional Tables

| Table | Store |
|-------|-------|
| `game_event_quest_condition` | `QuestIdToEventConditionMap` |
| `game_event_npcflag` | `GameEventNPCFlagMap` (guid + npcflag pairs) |
| `game_event_battleground_holiday` | `GameEventBitmask` (uint32 vector) |
| `game_event_pool` | `GameEventIdMap` (pool id lists) |
| `game_event_prerequisite` | loaded into `GameEventData.PrerequisiteEvents` |
| `game_event_seasonal_questrelation` | `GameEventSeasonalQuestsMap` |
| `game_event_save` | updates runtime state on `GameEventData` |
| `game_event_condition_save` | updates runtime `GameEventFinishCondition.Done` |

---

## 6. PoolMgr (sPoolMgr)

**Accessor:** `sPoolMgr`
**Class:** `PoolMgr`
**Header:** `src/server/game/Pools/PoolMgr.h`
**Source:** `src/server/game/Pools/PoolMgr.cpp`

### PoolTemplateData -- `pool_template`

| Field | C++ Type |
|-------|----------|
| MaxLimit | `uint32` |

**Container:** `std::unordered_map<uint32, PoolTemplateData>` (`PoolTemplateDataMap`)

### PoolObject -- `pool_creature`, `pool_gameobject`, `pool_pool`, `pool_quest`

| Field | C++ Type |
|-------|----------|
| guid | `uint32` |
| chance | `float` |

**Container:** Template-specialized `PoolGroup<T>` containing `std::vector<PoolObject>` for explicitly-chanced and equal-chanced objects.

- `std::unordered_map<uint32, PoolGroup<Creature>>` (`PoolGroupCreatureMap`)
- `std::unordered_map<uint32, PoolGroup<GameObject>>` (`PoolGroupGameObjectMap`)
- `std::unordered_map<uint32, PoolGroup<Pool>>` (`PoolGroupPoolMap`)
- `std::unordered_map<uint32, PoolGroup<Quest>>` (`PoolGroupQuestMap`)

---

## 7. WaypointMgr (sWaypointMgr)

**Accessor:** `sWaypointMgr`
**Class:** `WaypointMgr`
**Header:** `src/server/game/Movement/Waypoints/WaypointMgr.h`
**Source:** `src/server/game/Movement/Waypoints/WaypointMgr.cpp`

### WaypointNode -- `waypoint_data` + `waypoint_data_addon`

| Field | C++ Type |
|-------|----------|
| Id | `uint32` |
| X | `float` |
| Y | `float` |
| Z | `float` |
| Orientation | `std::optional<float>` |
| Velocity | `float` |
| Delay | `uint32` |
| EventId | `uint32` |
| MoveType | `uint32` |
| EventChance | `uint8` |
| SmoothTransition | `bool` |
| SplinePoints | `std::vector<G3D::Vector3>` |

### WaypointPath

| Field | C++ Type |
|-------|----------|
| Id | `uint32` |
| Nodes | `std::vector<WaypointNode>` |

**Container:** `std::unordered_map<uint32, WaypointPath>` (`_waypointStore`)

---

## 8. AchievementGlobalMgr (sAchievementMgr)

**Accessor:** `sAchievementMgr`
**Class:** `AchievementGlobalMgr`
**Header:** `src/server/game/Achievements/AchievementMgr.h`
**Source:** `src/server/game/Achievements/AchievementMgr.cpp`

### AchievementCriteriaData -- `achievement_criteria_data`

| Field | C++ Type |
|-------|----------|
| dataType | `AchievementCriteriaDataType` |
| raw.value1 | `uint32` (union of type-specific data) |
| raw.value2 | `uint32` (union of type-specific data) |
| ScriptId | `uint32` |

**Container:** `std::map<uint32, AchievementCriteriaDataSet>` (`AchievementCriteriaDataMap`), where each `AchievementCriteriaDataSet` holds `std::vector<AchievementCriteriaData>`.

### AchievementReward -- `achievement_reward`

| Field | C++ Type |
|-------|----------|
| titleId | `uint32[2]` |
| itemId | `uint32` |
| sender | `uint32` |
| subject | `std::string` |
| text | `std::string` |
| mailTemplate | `uint32` |

**Container:** `std::map<uint32, AchievementReward>` (`AchievementRewards`)

### AchievementRewardLocale -- `achievement_reward_locale`

| Field | C++ Type |
|-------|----------|
| Subject | `std::vector<std::string>` |
| Text | `std::vector<std::string>` |

**Container:** `std::map<uint32, AchievementRewardLocale>` (`AchievementRewardLocales`)

### CompletedAchievements -- `character_achievement` (Characters DB)

| Field | C++ Type |
|-------|----------|
| date | `SystemTimePoint` |

**Container:** `std::unordered_map<uint32, SystemTimePoint>` (`AllCompletedAchievements`)

---

## 9. LFGMgr (sLFGMgr)

**Accessor:** `sLFGMgr`
**Class:** `lfg::LFGMgr`
**Header:** `src/server/game/DungeonFinding/LFGMgr.h`
**Source:** `src/server/game/DungeonFinding/LFGMgr.cpp`

### LfgReward -- `lfg_dungeon_rewards`

| Field | C++ Type |
|-------|----------|
| maxLevel | `uint32` |
| firstQuest | `uint32` |
| otherQuest | `uint32` |

**Container:** `std::multimap<uint32, LfgReward const*>` (`LfgRewardContainer`)

### LFGDungeonData -- `lfg_dungeon_template` + DBC `LFGDungeonEntry`

| Field | C++ Type |
|-------|----------|
| id | `uint32` |
| name | `std::string` |
| map | `uint16` |
| type | `uint8` |
| expansion | `uint8` |
| group | `uint8` |
| minlevel | `uint8` |
| maxlevel | `uint8` |
| difficulty | `Difficulty` |
| seasonal | `bool` |
| x | `float` |
| y | `float` |
| z | `float` |
| o | `float` |

**Container:** `std::unordered_map<uint32, LFGDungeonData>` (`LFGDungeonContainer`)

---

## 10. BattlegroundMgr (sBattlegroundMgr)

**Accessor:** `sBattlegroundMgr`
**Class:** `BattlegroundMgr`
**Header:** `src/server/game/Battlegrounds/BattlegroundMgr.h`

### BattlegroundTemplate -- `battleground_template`

| Field | C++ Type |
|-------|----------|
| Id | `BattlegroundTypeId` |
| MinPlayersPerTeam | `uint16` |
| MaxPlayersPerTeam | `uint16` |
| MinLevel | `uint8` |
| MaxLevel | `uint8` |
| StartLocation | `std::array<Position, PVP_TEAMS_COUNT>` |
| MaxStartDistSq | `float` |
| Weight | `uint8` |
| ScriptId | `uint32` |
| BattlemasterEntry | `BattlemasterListEntry const*` |

**Container:** `std::map<BattlegroundTypeId, BattlegroundTemplate>` (`BattlegroundTemplateMap`)

---

## 11. DisableMgr (sDisableMgr)

**Accessor:** `sDisableMgr`
**Class:** `DisableMgr`
**Header:** `src/server/game/Conditions/DisableMgr.h`

### DisableData -- `disables`

| Field | C++ Type |
|-------|----------|
| flags | `uint8` |
| params[0] | `std::set<uint32>` |
| params[1] | `std::set<uint32>` |

**Container:** `std::array<std::unordered_map<uint32, DisableData>, MAX_DISABLE_TYPES>` (`DisableMap`)

---

## 12. FormationMgr (sFormationMgr)

**Accessor:** `sFormationMgr`
**Class:** `FormationMgr`
**Header:** `src/server/game/Entities/Creature/CreatureGroups.h`

### FormationInfo -- `creature_formations`

| Field | C++ Type |
|-------|----------|
| leaderGUID | `ObjectGuid::LowType` |
| follow_dist | `float` |
| follow_angle | `float` |
| groupAI | `uint16` |
| point_1 | `uint32` |
| point_2 | `uint32` |

**Container:** `std::unordered_map<ObjectGuid::LowType, FormationInfo>` (`CreatureGroupInfoType`)

---

## 13. CreatureTextMgr (sCreatureTextMgr)

**Accessor:** `sCreatureTextMgr`
**Class:** `CreatureTextMgr`
**Header:** `src/server/game/Texts/CreatureTextMgr.h`

### CreatureTextEntry -- `creature_text`

| Field | C++ Type |
|-------|----------|
| entry | `uint32` |
| group | `uint8` |
| id | `uint8` |
| text | `std::string` |
| type | `ChatMsg` |
| lang | `Language` |
| probability | `float` |
| emote | `Emote` |
| duration | `uint32` |
| sound | `uint32` |
| TextRange | `CreatureTextRange` |
| BroadcastTextId | `uint32` |

**Container:** `std::unordered_map<uint32, std::unordered_map<uint8, std::vector<CreatureTextEntry>>>` (`CreatureTextMap`)

### CreatureTextLocale -- `creature_text_locale`

| Field | C++ Type |
|-------|----------|
| Text | `std::vector<std::string>` |

**Container:** `std::map<CreatureTextId, CreatureTextLocale>` (`LocaleCreatureTextMap`)

---

## 14. WardenCheckMgr (sWardenCheckMgr)

**Accessor:** `sWardenCheckMgr`
**Class:** `WardenCheckMgr`
**Header:** `src/server/game/Warden/WardenCheckMgr.h`

### WardenCheck -- `warden_checks`

| Field | C++ Type |
|-------|----------|
| Type | `uint8` |
| Data | `BigNumber` |
| Address | `uint32` |
| Length | `uint8` |
| Str | `std::string` |
| Comment | `std::string` |
| CheckId | `uint16` |
| IdStr | `std::array<char, 4>` |
| Action | `uint32` |

**Container:** `std::vector<WardenCheck>` (`CheckContainer`)

### WardenCheckResult -- `warden_action`

| Field | C++ Type |
|-------|----------|
| Result | `BigNumber` |

**Container:** `std::map<uint32, WardenCheckResult>` (`CheckResultContainer`)

---

## 15. ServerMailMgr (sServerMailMgr)

**Accessor:** `sServerMailMgr`
**Class:** `ServerMailMgr`
**Header:** `src/server/game/Mails/ServerMailMgr.h`

### ServerMail -- `mail_server_template` + `mail_server_template_items` + `mail_server_template_conditions`

| Field | C++ Type |
|-------|----------|
| id | `uint32` |
| moneyA | `uint32` |
| moneyH | `uint32` |
| subject | `std::string` |
| body | `std::string` |
| active | `uint8` |
| conditions | `std::vector<ServerMailCondition>` |
| itemsA | `std::vector<ServerMailItems>` |
| itemsH | `std::vector<ServerMailItems>` |

#### ServerMailCondition (nested)

| Field | C++ Type |
|-------|----------|
| type | `ServerMailConditionType` |
| value | `uint32` |
| state | `uint32` |

#### ServerMailItems (nested)

| Field | C++ Type |
|-------|----------|
| item | `uint32` |
| itemCount | `uint32` |

**Container:** `std::unordered_map<uint32, ServerMail>` (`ServerMailContainer`)

---

## 16. TransportMgr (sTransportMgr)

**Accessor:** `sTransportMgr`
**Class:** `TransportMgr`
**Header:** `src/server/game/Maps/TransportMgr.h`

### TransportTemplate -- `gameobject_template` (type=15) + `transports`

| Field | C++ Type |
|-------|----------|
| mapsUsed | `std::set<uint32>` |
| inInstance | `bool` |
| pathTime | `uint32` |
| keyFrames | `std::vector<KeyFrame>` (`KeyFrameVec`) |
| accelTime | `float` |
| accelDist | `float` |
| entry | `uint32` |

**Container:** `std::unordered_map<uint32, TransportTemplate>` (`TransportTemplates`)

---

## 17. WeatherMgr (namespace)

**Accessor:** `WeatherMgr::LoadWeatherData()`, `WeatherMgr::GetWeatherData()`
**Header:** `src/server/game/Weather/WeatherMgr.h`
**Source:** `src/server/game/Weather/WeatherMgr.cpp`

### WeatherData -- `game_weather`

| Field | C++ Type |
|-------|----------|
| data[WEATHER_SEASONS] | `WeatherSeasonChances[4]` (rainChance, snowChance, stormChance) |
| ScriptId | `uint32` |

#### WeatherSeasonChances (nested)

| Field | C++ Type |
|-------|----------|
| rainChance | `uint32` |
| snowChance | `uint32` |
| stormChance | `uint32` |

---

## 18. OutdoorPvPMgr (sOutdoorPvPMgr)

**Accessor:** `sOutdoorPvPMgr`
**Class:** `OutdoorPvPMgr`
**Header:** `src/server/game/OutdoorPvP/OutdoorPvPMgr.h`

### OutdoorPvPData -- `outdoorpvp_template`

| Field | C++ Type |
|-------|----------|
| TypeId | `OutdoorPvPTypes` |
| ScriptId | `uint32` |

**Container:** `std::map<OutdoorPvPTypes, std::unique_ptr<OutdoorPvPData>>` (`m_OutdoorPvPDatas`)

---

## 19. ItemEnchantmentMgr (standalone)

**Header:** `src/server/game/Entities/Item/ItemEnchantmentMgr.h`
**Source:** `src/server/game/Entities/Item/ItemEnchantmentMgr.cpp`

### Random Enchantment Data -- `item_enchantment_template`

- **Struct:** `EnchStoreItem`
- **Container:** `EnchantmentStore` = `std::unordered_map<uint32, std::vector<EnchStoreItem>>` (static `RandomItemEnch`)
- **Loaders:** `LoadRandomEnchantmentsTable()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry | map key | uint32 | Enchantment group ID |
| ench | ench | uint32 | SpellItemEnchantment ID |
| chance | chance | float | Weight 0-100 |

---

## 20. ArenaSeasonMgr (sArenaSeasonMgr)

**Accessor:** `sArenaSeasonMgr`
**Class:** `ArenaSeasonMgr`
**Header:** `src/server/game/Battlegrounds/ArenaSeason/ArenaSeasonMgr.h`

### ArenaSeasonRewardGroup -- `arena_season_reward_group` + `arena_season_reward`

| Field | C++ Type |
|-------|----------|
| season | `uint8` |
| criteriaType | `ArenaSeasonRewardGroupCriteriaType` |
| minCriteria | `float` |
| maxCriteria | `float` |
| rewardMailTemplateID | `uint32` |
| rewardMailSubject | `std::string` |
| rewardMailBody | `std::string` |
| goldReward | `uint32` |
| itemRewards | `std::vector<ArenaSeasonReward>` |
| achievementRewards | `std::vector<ArenaSeasonReward>` |

#### ArenaSeasonReward (nested)

| Field | C++ Type |
|-------|----------|
| entry | `uint32` |
| type | `ArenaSeasonRewardType` |

**Container:** `std::unordered_map<uint8, std::vector<ArenaSeasonRewardGroup>>` (`ArenaSeasonRewardGroupsBySeasonContainer`)

---

## 21. AutobroadcastMgr (sAutobroadcastMgr)

**Accessor:** `sAutobroadcastMgr`
**Class:** `AutobroadcastMgr`
**Header:** `src/server/game/Autobroadcast/AutobroadcastMgr.h`

### Autobroadcast Data -- `autobroadcast` (Login DB) + `autobroadcast_locale`

| Field | C++ Type |
|-------|----------|
| _autobroadcasts | `std::map<uint8, std::vector<std::string>>` (`AutobroadcastsMap`) |
| _autobroadcastsWeights | `std::map<uint8, uint8>` (`AutobroadcastsWeightMap`) |
| _announceType | `AnnounceType` |

---

## 22. MotdMgr (sMotdMgr)

**Accessor:** `sMotdMgr`
**Class:** `MotdMgr`
**Header:** `src/server/game/Motd/MotdMgr.h`
**Database:** `db_auth` (LoginDatabase)

### MOTD Data -- `motd` + `motd_localized`

- **Containers:** `std::unordered_map<LocaleConstant, std::string>` (text) + `std::unordered_map<LocaleConstant, WorldPacket>` (pre-built packets)
- **Loaders:** `LoadMotd()`, `LoadMotdLocale()`

#### `motd`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| realmid | *(WHERE clause)* | uint32 | Filtered by realm |
| text | motd string | std::string | Stored for LOCALE_enUS |

#### `motd_localized`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| realmid | *(WHERE clause)* | uint32 | Filtered by realm |
| locale | locale key | std::string | Maps to LocaleConstant |
| text | localized text | std::string | Stored per locale |

---

## 23. TicketMgr (sTicketMgr)

**Accessor:** `sTicketMgr`
**Class:** `TicketMgr`
**Header:** `src/server/game/Tickets/TicketMgr.h`
**Database:** `db_characters`

### Load Functions
- `LoadTickets()` -- loads from `gm_ticket`
- `LoadSurveys()` -- reads `MAX(surveyId)` from `gm_survey`

### GmTicket -- `gm_ticket`

- **Struct:** `GmTicket`
- **Container:** `GmTicketList` = `std::map<uint32, GmTicket*>` keyed by ticket ID
- **Member:** `_ticketList`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | _id | uint32 | Ticket ID |
| type | _type | TicketType | |
| playerGuid | _playerGuid | ObjectGuid | Player |
| name | _playerName | std::string | |
| description | _message | std::string | |
| createTime | _createTime | uint64 | |
| mapId | _mapId | uint16 | |
| posX | _posX | float | |
| posY | _posY | float | |
| posZ | _posZ | float | |
| lastModifiedTime | _lastModifiedTime | uint64 | |
| closedBy | _closedBy | ObjectGuid | Player |
| assignedTo | _assignedTo | ObjectGuid | Player |
| comment | _comment | std::string | |
| response | _response | std::string | |
| completed | _completed | bool | |
| escalated | _escalatedStatus | GMTicketEscalationStatus | |
| viewed | _viewed | bool | |
| needMoreHelp | _needMoreHelp | bool | |
| resolvedBy | _resolvedBy | ObjectGuid | Player |

### gm_survey

Only `MAX(surveyId)` is read to track the last survey ID. Individual survey data is not loaded into memory.

---

## 24. PetitionMgr (sPetitionMgr)

**Accessor:** `sPetitionMgr`
**Class:** `PetitionMgr`
**Header:** `src/server/game/Petitions/PetitionMgr.h`
**Database:** `db_characters`

### Load Functions
- `LoadPetitions()` -- loads from `petition`
- `LoadSignatures()` -- loads from `petition_sign`

### Petition -- `petition`

- **Struct:** `Petition`
- **Container:** `PetitionContainer` = `std::map<ObjectGuid, Petition>` keyed by item GUID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| ownerguid | ownerGuid | ObjectGuid | Player |
| petitionguid | petitionGuid | ObjectGuid | Item |
| name | petitionName | std::string | |
| type | petitionType | uint8 | |
| petition_id | petitionId | uint32 | |

### Signatures -- `petition_sign`

- **Container:** `SignatureContainer` = `std::map<ObjectGuid, Signatures>` keyed by item GUID
  - `Signatures::signatureMap` = `std::map<ObjectGuid, uint32>` (playerGuid → accountId)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| petition_id | *(lookup key)* | uint32 | Maps to itemGuid via PetitionIdToItemGuid |
| playerguid | signatureMap key | ObjectGuid | Player |
| player_account | signatureMap value | uint32 | Account ID |

---

## 25. InstanceSaveMgr (sInstanceSaveMgr)

**Accessor:** `sInstanceSaveMgr`
**Class:** `InstanceSaveMgr`
**Header:** `src/server/game/Instances/InstanceSaveMgr.h`
**Database:** `db_characters`

### Load Functions
- `LoadInstances()` -- orchestrator calling the below
- `LoadResetTimes()` -- loads from `instance_reset`
- `LoadInstanceSaves()` -- loads from `instance`
- `LoadCharacterBinds()` -- loads from `character_instance`

### InstanceSave -- `instance`

- **Class:** `InstanceSave`
- **Container:** `InstanceSaveHashMap` = `std::unordered_map<uint32, InstanceSave*>` keyed by instance ID
- **Member:** `m_instanceSaveById`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | m_instanceid | uint32 | Instance ID |
| map | m_mapid | uint32 | Map ID |
| resettime | m_resetTime | time_t | |
| difficulty | m_difficulty | Difficulty | |
| completedEncounters | m_completedEncounterMask | uint32 | Bitmask |
| data | m_instanceData | std::string | |

### Reset Times -- `instance_reset`

- **Container:** `ResetTimeByMapDifficultyMap` = `std::unordered_map<uint32, time_t>` keyed by PAIR32(mapId, difficulty)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| mapid | key part | uint16 | Packed with difficulty |
| difficulty | key part | Difficulty | Packed with mapid |
| resettime | value | time_t | |

### Character Binds -- `character_instance`

- **Container:** `PlayerBindStorage` = `std::unordered_map<ObjectGuid, BoundInstancesMapWrapper*>` keyed by player GUID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | outer key | ObjectGuid | Player |
| instance | *(links to InstanceSave)* | uint32 | |
| permanent | InstancePlayerBind::perm | bool | |
| extended | InstancePlayerBind::extended | bool | |

---

## 26. GroupMgr (sGroupMgr)

**Accessor:** `sGroupMgr`
**Class:** `GroupMgr`
**Header:** `src/server/game/Groups/GroupMgr.h`
**Database:** `db_characters`

### Load Function
- `LoadGroups()` -- loads from `groups`, `group_member`, `lfg_data`

### Group Data -- `groups`

- **Class:** `Group`
- **Container:** `GroupContainer` = `std::map<uint32, Group*>` keyed by group GUID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | GUID | uint32 | Group ID |
| leaderGuid | LeaderGuid | ObjectGuid | Player |
| lootMethod | m_lootMethod | LootMethod | |
| looterGuid | LooterGuid | ObjectGuid | Player |
| lootThreshold | m_lootThreshold | uint32 | |
| icon1-8 | m_targetIcons[0-7] | uint64 | Target markers |
| groupType | m_groupType | GroupType | |
| difficulty | m_dungeonDifficulty | Difficulty | |
| raidDifficulty | m_raidDifficulty | Difficulty | |
| masterLooterGuid | MasterLooterGuid | ObjectGuid | Player |

### Group Members -- `group_member`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | *(find Group)* | uint32 | Group ID |
| memberGuid | *(passed to LoadMemberFromDB)* | ObjectGuid | Player |
| memberFlags | flags | uint8 | |
| subgroup | group | uint8 | Subgroup number |
| roles | roles | uint8 | Roles bitmask |

### LFG Data -- `lfg_data`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | *(FK to groups)* | uint32 | |
| dungeon | m_LfgDungeonEntry | uint32 | |
| state | m_LfgState | LfgState | |

---

## 27. GuildMgr (sGuildMgr)

**Accessor:** `sGuildMgr`
**Class:** `GuildMgr`
**Header:** `src/server/game/Guilds/GuildMgr.h`
**Database:** `db_characters`

### Load Function
- `LoadGuilds()` -- loads 8 sub-tables in sequence

### Guild -- `guild`

- **Class:** `Guild`
- **Container:** `GuildContainer` = `std::unordered_map<uint32, Guild*>` keyed by guild ID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guildid | m_id | uint32 | |
| name | m_name | std::string | |
| leaderguid | m_leaderGuid | ObjectGuid | Player |
| EmblemStyle | m_emblemInfo.GetStyle() | uint8 | |
| EmblemColor | m_emblemInfo.GetColor() | uint8 | |
| BorderStyle | m_emblemInfo.GetBorderStyle() | uint8 | |
| BorderColor | m_emblemInfo.GetBorderColor() | uint8 | |
| BackgroundColor | m_emblemInfo.GetBackgroundColor() | uint8 | |
| info | m_info | std::string | |
| motd | m_motd | std::string | |
| createdate | m_createdDate | time_t | |
| BankMoney | m_bankMoney | uint64 | |

Also loads: `guild_rank`, `guild_member` (joined with `guild_member_withdraw` and `characters`), `guild_bank_right`, `guild_eventlog`, `guild_bank_eventlog`, `guild_bank_tab`, `guild_bank_item` (joined with `item_instance`).

---

## 28. ArenaTeamMgr (sArenaTeamMgr)

**Accessor:** `sArenaTeamMgr`
**Class:** `ArenaTeamMgr`
**Header:** `src/server/game/Battlegrounds/ArenaTeamMgr.h`
**Database:** `db_characters`

### Load Function
- `LoadArenaTeams()` -- loads from `arena_team`, `arena_team_member` (joined with `characters` and `character_arena_stats`)

### ArenaTeam -- `arena_team`

- **Class:** `ArenaTeam`
- **Container:** `ArenaTeamContainer` = `std::unordered_map<uint32, ArenaTeam*>` keyed by arenaTeamId

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| arenaTeamId | GetId() | uint32 | |
| name | GetName() | std::string | |
| captainGuid | GetCaptain() | ObjectGuid | Player |
| type | GetType() | uint8 | 2v2, 3v3, 5v5 |
| backgroundColor | BackgroundColor | uint32 | |
| emblemStyle | EmblemStyle | uint32 | |
| emblemColor | EmblemColor | uint32 | |
| borderStyle | BorderStyle | uint32 | |
| borderColor | BorderColor | uint32 | |
| rating | Rating | uint32 | |
| weekGames | WeekGames | uint32 | |
| weekWins | WeekWins | uint32 | |
| seasonGames | SeasonGames | uint32 | |
| seasonWins | SeasonWins | uint32 | |
| rank | Rank | uint32 | |

### ArenaTeam Members -- `arena_team_member`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | Guid | ObjectGuid | Player |
| weekGames | WeekGames | uint16 | |
| weekWins | WeekWins | uint16 | |
| seasonGames | SeasonGames | uint16 | |
| seasonWins | SeasonWins | uint16 | |
| personalRating | PersonalRating | uint16 | From `character_arena_stats` |
| matchMakerRating | MatchMakerRating | uint16 | From `character_arena_stats` |

---

## 29. CalendarMgr (sCalendarMgr)

**Accessor:** `sCalendarMgr`
**Class:** `CalendarMgr`
**Header:** `src/server/game/Calendar/CalendarMgr.h`
**Database:** `db_characters`

### Load Function
- `LoadFromDB()` -- loads from `calendar_events` and `calendar_invites`

### CalendarEvent -- `calendar_events`

- **Class:** `CalendarEvent`
- **Container:** `CalendarEventStore` = `std::unordered_set<CalendarEvent*>`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | _eventId | uint64 | |
| creator | _creatorGUID | ObjectGuid | Player |
| title | _title | std::string | |
| description | _description | std::string | |
| type | _type | CalendarEventType | |
| dungeon | _dungeonId | int32 | |
| eventtime | _eventTime | time_t | |
| flags | _flags | uint32 | |
| time2 | _timezoneTime | time_t | |

### CalendarInvite -- `calendar_invites`

- **Class:** `CalendarInvite`
- **Container:** `CalendarEventInviteStore` = `std::unordered_map<uint64, CalendarInviteStore>` keyed by event ID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | _inviteId | uint64 | |
| event | _eventId | uint64 | |
| invitee | _invitee | ObjectGuid | Player |
| sender | _senderGUID | ObjectGuid | Player |
| status | _status | CalendarInviteStatus | |
| statustime | _statusTime | time_t | |
| rank | _rank | CalendarModerationRank | |
| text | _text | std::string | |

---

## 30. AuctionHouseMgr (sAuctionMgr)

**Accessor:** `sAuctionMgr`
**Class:** `AuctionHouseMgr`
**Header:** `src/server/game/AuctionHouse/AuctionHouseMgr.h`
**Database:** `db_characters`

### Load Functions
- `LoadAuctionItems()` -- loads items from `item_instance`
- `LoadAuctions()` -- loads auctions from `auctionhouse`

### AuctionEntry -- `auctionhouse`

- **Struct:** `AuctionEntry`
- **Containers:** `_hordeAuctions`, `_allianceAuctions`, `_neutralAuctions` -- each `AuctionHouseObject` containing `AuctionEntryMap` = `std::map<uint32, AuctionEntry*>` keyed by auction ID

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | Id | uint32 | Auction ID |
| houseid | houseId | AuctionHouseId | |
| itemguid | item_guid | ObjectGuid | Item |
| item_template | *(from item_instance join)* | uint32 | |
| itemCount | *(from item_instance join)* | uint32 | |
| itemowner | owner | ObjectGuid | Player |
| buyoutprice | buyout | uint32 | |
| time | expire_time | time_t | |
| buyguid | bidder | ObjectGuid | Player |
| lastbid | bid | uint32 | |
| startbid | startbid | uint32 | |
| deposit | deposit | uint32 | |

Auction items loaded via `Item::LoadFromDB()` from `item_instance`.

---

## 31. AddonMgr (namespace)

**Header:** `src/server/game/Addons/AddonMgr.h`
**Database:** `db_characters`

### Load Function
- `LoadFromDB()` -- loads from `addons` and `banned_addons`

### Saved Addons -- `addons`

- **Struct:** `SavedAddon`
- **Container:** `std::list<SavedAddon>` (file-scope `m_knownAddons`)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| name | Name | std::string | Addon name (PK) |
| crc | CRC | uint32 | |

### Banned Addons -- `banned_addons`

- **Struct:** `BannedAddon`
- **Container:** `std::list<BannedAddon>` (file-scope `m_bannedAddons`)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| Id | Id | uint32 | + 102 offset |
| Name | NameMD5 | std::array&lt;uint8, 16&gt; | MD5 hashed |
| Version | VersionMD5 | std::array&lt;uint8, 16&gt; | MD5 hashed |
| Timestamp | Timestamp | time_t | |
