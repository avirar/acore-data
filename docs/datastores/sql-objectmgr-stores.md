# SQL-Only Datastores (ObjectMgr)

This document lists all datastores loaded exclusively from SQL (no DBC counterpart), managed by the `ObjectMgr` singleton (`sObjectMgr`). For architecture details, see [README.md](README.md).

Each entry includes:
- The C++ struct/class name and its fields with types
- The SQL table name
- The store variable and container type
- The loading function

## Table of Contents

- [CreatureTemplate](#creaturetemplate)
- [CreatureModel](#creaturemodel)
- [CreatureBaseStats](#creaturebasestats)
- [CreatureData](#creaturedata)
- [CreatureAddon](#creatureaddon)
- [CreatureModelInfo](#creaturemodelinfo)
- [EquipmentInfo](#equipmentinfo)
- [CreatureMovementData](#creaturemovementdata)
- [VendorItem](#vendoritem)
- [GameObjectTemplate](#gameobjecttemplate)
- [GameObjectTemplateAddon](#gameobjecttemplateaddon)
- [GameObjectData](#gameobjectdata)
- [GameObjectAddon](#gameobjectaddon)
- [ItemTemplate](#itemtemplate)
- [ItemSetNameEntry](#itemsetnameentry)
- [Quest](#quest)
- [QuestMoneyReward](#questmoneyreward)
- [QuestPOI](#questpoi)
- [QuestAreaTrigger](#questareatrigger)
- [QuestGreeting](#questgreeting)
- [QuestRelations](#questrelations)
- [PageText](#pagetext)
- [GossipText](#gossiptext)
- [GossipMenus](#gossipmenus)
- [GossipMenuItems](#gossipmenuitems)
- [BroadcastText](#broadcasttext)
- [PointOfInterest](#pointofinterest)
- [AreaTrigger](#areatrigger)
- [AreaTriggerTeleport](#areatriggerteleport)
- [InstanceTemplate](#instancetemplate)
- [DungeonEncounter](#dungeonencounter)
- [DungeonProgressionRequirements](#dungeonprogressionrequirements)
- [ScriptInfo](#scriptinfo)
- [RepRewardRate](#reprewardrate)
- [ReputationOnKillEntry](#reputationonkillentry)
- [RepSpilloverTemplate](#repspillovertemplate)
- [PlayerInfo](#playerinfo)
- [PetLevelInfo](#petlevelinfo)
- [SpellClickInfo](#spellclickinfo)
- [VehicleAccessory](#vehicleaccessory)
- [VehicleSeatAddon](#vehicleseataddon)
- [GameTele](#gametele)
- [MailLevelReward](#maillevelreward)
- [TempSummonData](#tempsummondata)
- [LinkedRespawn](#linkedrespawn)
- [FormationInfo](#formationinfo)
- [AcoreString](#acorestring)
- [ModuleString](#modulestring)
- [Locale Stores](#locale-stores)
- [Faction Change Stores](#faction-change-stores)
- [Trainer Stores](#trainer-stores)
- [Fishing](#fishing)
- [Reserved/Profanity Names](#reservedprofanity-names)

---

## CreatureTemplate

- **SQL Table:** `creature_template` (LEFT JOIN `creature_template_movement`)
- **Struct:** `CreatureTemplate` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Store:** `ObjectMgr::_creatureTemplateStore` (`CreatureTemplateContainer` = `std::unordered_map<uint32, CreatureTemplate>`)
- **Loader:** `ObjectMgr::LoadCreatureTemplates()` (`ObjectMgr.cpp:522`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| entry | uint32 | Entry | Primary key |
| DifficultyEntry1 | uint32 | DifficultyEntry[0] | |
| DifficultyEntry2 | uint32 | DifficultyEntry[1] | |
| DifficultyEntry3 | uint32 | DifficultyEntry[2] | |
| KillCredit1 | uint32 | KillCredit[0] | |
| KillCredit2 | uint32 | KillCredit[1] | |
| name | std::string | Name | |
| subname | std::string | SubName | |
| IconName | std::string | IconName | |
| gossip_menu_id | uint32 | GossipMenuId | |
| minlevel | uint8 | minlevel | |
| maxlevel | uint8 | maxlevel | |
| exp | uint32 | expansion | SQL column: `exp` |
| faction | uint32 | faction | |
| npcflag | uint32 | npcflag | enum NPCFlags |
| speed_walk | float | speed_walk | |
| speed_run | float | speed_run | |
| speed_swim | float | speed_swim | |
| speed_flight | float | speed_flight | |
| detection_range | float | detection_range | |
| rank | uint32 | rank | enum CreatureRank |
| dmgschool | uint32 | dmgschool | |
| DamageModifier | float | DamageModifier | |
| BaseAttackTime | uint32 | BaseAttackTime | |
| RangeAttackTime | uint32 | RangeAttackTime | |
| BaseVariance | float | BaseVariance | |
| RangeVariance | float | RangeVariance | |
| unit_class | uint32 | unit_class | enum Classes |
| unit_flags | uint32 | unit_flags | enum UnitFlags |
| unit_flags2 | uint32 | unit_flags2 | enum UnitFlags2 |
| dynamicflags | uint32 | dynamicflags | |
| family | uint32 | family | enum CreatureFamily |
| type | uint32 | type | enum CreatureType |
| type_flags | uint32 | type_flags | enum CreatureTypeFlags |
| lootid | uint32 | lootid | |
| pickpocketloot | uint32 | pickpocketLootId | |
| skinloot | uint32 | SkinLootId | |
| resistance1..7 | int32[7] | resistance | Loaded separately via LoadCreatureTemplateResistances() |
| spell1..8 | uint32[8] | spells | Loaded separately via LoadCreatureTemplateSpells() |
| PetSpellDataId | uint32 | PetSpellDataId | |
| VehicleId | uint32 | VehicleId | |
| mingold | uint32 | mingold | |
| maxgold | uint32 | maxgold | |
| AIName | std::string | AIName | |
| MovementType | uint32 | MovementType | |
| HoverHeight | float | HoverHeight | |
| HealthModifier | float | ModHealth | |
| ManaModifier | float | ModMana | |
| ArmorModifier | float | ModArmor | |
| ExperienceModifier | float | ModExperience | |
| RacialLeader | bool | RacialLeader | |
| movementId | uint32 | movementId | |
| RegenHealth | bool | RegenHealth | |
| CreatureImmunitiesId | int32 | CreatureImmunitiesId | |
| flags_extra | uint32 | flags_extra | enum CreatureFlagsExtra |
| ScriptName | uint32 | ScriptID | resolved to script ID |

Sub-struct **CreatureMovementData** (from `creature_template_movement`):

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| Ground | CreatureGroundMovementType | Ground | enum |
| Swim | bool | Swim | |
| Flight | CreatureFlightMovementType | Flight | enum |
| Rooted | bool | Rooted | |
| Chase | CreatureChaseMovementType | Chase | enum |
| Random | CreatureRandomMovementType | Random | enum |
| InteractionPauseTimer | uint32 | InteractionPauseTimer | |

Sub-struct **CreatureModel** (from `creature_template_model`):

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| CreatureDisplayID | uint32 | CreatureDisplayID | |
| DisplayScale | float | DisplayScale | |
| Probability | float | Probability | |

---

## CreatureBaseStats

- **SQL Table:** `creature_classlevelstats`
- **Struct:** `CreatureBaseStats` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Store:** `ObjectMgr::_creatureBaseStatsStore` (`CreatureBaseStatsContainer` = `std::unordered_map<uint16, CreatureBaseStats>`)
- **Loader:** `ObjectMgr::LoadCreatureClassLevelStats()` (`ObjectMgr.cpp:10488`)
- **Key:** MAKE_PAIR16(level, class)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| basehp0 | uint32 | BaseHealth[0] | Vanilla expansion |
| basehp1 | uint32 | BaseHealth[1] | TBC expansion |
| basehp2 | uint32 | BaseHealth[2] | WotLK expansion |
| basemana | uint32 | BaseMana | |
| basearmor | float | BaseArmor | |
| attackpower | uint32 | AttackPower | |
| rangedattackpower | uint32 | RangedAttackPower | |
| basedamage0 | float | BaseDamage[0] | Vanilla |
| basedamage1 | float | BaseDamage[1] | TBC |
| basedamage2 | float | BaseDamage[2] | WotLK |
| strength | uint32 | Strength | |
| agility | uint32 | Agility | |
| stamina | uint32 | Stamina | |
| intellect | uint32 | Intellect | |
| spirit | uint32 | Spirit | |

---

## CreatureData

- **SQL Table:** `creature` (LEFT JOIN `game_event_creature`, `pool_creature`)
- **Struct:** `CreatureData` (`src/server/game/Entities/Creature/CreatureData.h`) extends `SpawnData`
- **Store:** `ObjectMgr::_creatureDataStore` (`CreatureDataContainer`)
- **Loader:** `ObjectMgr::LoadCreatures()` (`ObjectMgr.cpp:2316`)

Inherited from **SpawnData** (`src/server/game/Maps/SpawnData.h`):

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| map | uint16 | mapid | |
| phaseMask | uint32 | phaseMask | |
| position_x | float | posX | |
| position_y | float | posY | |
| position_z | float | posZ | |
| orientation | float | orientation | |
| spawnMask | uint8 | spawnMask | |
| ScriptName | uint32 | ScriptId | |
| spawnGroup | uint32 | spawnGroupId | |

CreatureData own fields:

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| guid | ObjectGuid::LowType | spawnId | |
| id1 | uint32 | id1 | Primary creature entry |
| id2 | uint32 | id2 | Alternate entry (difficulty) |
| id3 | uint32 | id3 | Alternate entry (difficulty) |
| displayid | uint32 | displayid | Override model |
| equipment_id | int8 | equipmentId | |
| spawntimesecs | uint32 | spawntimesecs | |
| wander_distance | float | wander_distance | |
| currentwaypoint | uint32 | currentwaypoint | |
| curhealth | uint32 | curhealth | |
| curmana | uint32 | curmana | |
| MovementType | uint8 | movementType | |
| npcflag | uint32 | npcflag | Override, enum NPCFlags |
| unit_flags | uint32 | unit_flags | Override, enum UnitFlags |
| dynamicflags | uint32 | dynamicflags | Override |

---

## CreatureAddon

- **SQL Tables:** `creature_addon` (per-guid) and `creature_template_addon` (per-entry)
- **Struct:** `CreatureAddon` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Stores:** `ObjectMgr::_creatureAddonStore` (per-guid), `ObjectMgr::_creatureTemplateAddonStore` (per-entry)
- **Loaders:** `ObjectMgr::LoadCreatureAddons()`, `ObjectMgr::LoadCreatureTemplateAddons()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| path_id | uint32 | path_id | |
| mount | uint32 | mount | |
| bytes1 | uint32 | bytes1 | |
| bytes2 | uint32 | bytes2 | |
| emote | uint32 | emote | |
| auras | std::vector&lt;uint32&gt; | auras | Comma-separated aura spell IDs |
| visibilityDistanceType | VisibilityDistanceType | visibilityDistanceType | enum |

---

## CreatureModelInfo

- **SQL Table:** `creature_model_info`
- **Struct:** `CreatureModelInfo` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Store:** `ObjectMgr::_creatureModelStore` (`CreatureModelContainer`)
- **Loader:** `ObjectMgr::LoadCreatureModelInfo()` (`ObjectMgr.cpp:1709`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| bounding_radius | float | bounding_radius | |
| combat_reach | float | combat_reach | |
| gender | uint8 | gender | |
| modelid_other_gender | uint32 | modelid_other_gender | |
| is_trigger | float | is_trigger | |

---

## EquipmentInfo

- **SQL Table:** `creature_equip_template`
- **Struct:** `EquipmentInfo` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Store:** `ObjectMgr::_equipmentInfoStore` (`EquipmentInfoContainer`)
- **Loader:** `ObjectMgr::LoadEquipmentTemplates()` (`ObjectMgr.cpp:1479`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| ItemEntry1 | uint32 | ItemEntry[0] | |
| ItemEntry2 | uint32 | ItemEntry[1] | |
| ItemEntry3 | uint32 | ItemEntry[2] | |

---

## VendorItem

- **SQL Table:** `npc_vendor`
- **Struct:** `VendorItem` (`src/server/game/Entities/Creature/CreatureData.h`)
- **Store:** `ObjectMgr::_cacheVendorItemStore` (`CacheVendorItemContainer`)
- **Loader:** `ObjectMgr::LoadVendors()` (`ObjectMgr.cpp:9952`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| item | uint32 | item | |
| maxcount | uint32 | maxcount | 0 = infinite |
| incrtime | uint32 | incrtime | Restock timer in seconds |
| ExtendedCost | uint32 | ExtendedCost | |

---

## GameObjectTemplate

- **SQL Table:** `gameobject_template`
- **Struct:** `GameObjectTemplate` (`src/server/game/Entities/GameObject/GameObjectData.h`)
- **Store:** `ObjectMgr::_gameObjectTemplateStore` (`GameObjectTemplateContainer`)
- **Loader:** `ObjectMgr::LoadGameObjectTemplate()` (`ObjectMgr.cpp:7804`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| entry | uint32 | entry | Primary key |
| type | uint32 | type | enum GameobjectTypes |
| displayId | uint32 | displayId | |
| name | std::string | name | |
| IconName | std::string | IconName | |
| castBarCaption | std::string | castBarCaption | |
| unk1 | std::string | unk1 | |
| size | float | size | |
| data0..23 | uint32[] | data[] | Type-specific (see below) |
| AIName | std::string | AIName | |
| ScriptName | uint32 | ScriptId | |

### GameObject Data Fields by Type

The `data[]` array is interpreted differently based on `type`:

**DOOR (type 0):** data[0]=startOpen, data[1]=lockId, data[2]=autoCloseTime, data[3]=noDamageImmune, data[4]=openTextID, data[5]=closeTextID, data[6]=ignoredByPathing

**BUTTON (type 1):** data[0]=startOpen, data[1]=lockId, data[2]=autoCloseTime, data[3]=linkedTrap, data[4]=noDamageImmune, data[5]=large, data[6]=openTextID, data[7]=closeTextID, data[8]=losOK

**QUESTGIVER (type 2):** data[0]=lockId, data[1]=questList, data[2]=pageMaterial, data[3]=gossipID, data[4]=customAnim, data[5]=noDamageImmune, data[6]=openTextID, data[7]=losOK, data[8]=allowMounted, data[9]=large

**CHEST (type 3):** data[0]=lockId, data[1]=lootId, data[2]=chestRestockTime, data[3]=consumable, data[4]=minSuccessOpens, data[5]=maxSuccessOpens, data[6]=eventId, data[7]=linkedTrapId, data[8]=questId, data[9]=level, data[10]=losOK, data[11]=leaveLoot, data[12]=notInCombat, data[13]=logLoot, data[14]=openTextID, data[15]=groupLootRules, data[16]=floatingTooltip

**GENERIC (type 5):** data[0]=floatingTooltip, data[1]=highlight, data[2]=serverOnly, data[3]=large, data[4]=floatOnWater, data[5]=questID

**TRAP (type 6):** data[0]=lockId, data[1]=level, data[2]=diameter, data[3]=spellId, data[4]=type, data[5]=cooldown, data[6]=autoCloseTime, data[7]=startDelay, data[8]=serverOnly, data[9]=stealthed, data[10]=large, data[11]=invisible, data[12]=openTextID, data[13]=closeTextID, data[14]=ignoreTotems

**CHAIR (type 7):** data[0]=slots, data[1]=height, data[2]=onlyCreatorUse, data[3]=triggeredEvent

**SPELL_FOCUS (type 8):** data[0]=focusId, data[1]=dist, data[2]=linkedtrapId, data[3]=serverOnly, data[4]=questID, data[5]=large, data[6]=floatingTooltip

**TEXT (type 9):** data[0]=pageID, data[1]=language, data[2]=pageMaterial, data[3]=allowMounted

**GOOBER (type 10):** data[0]=lockId, data[1]=questId, data[2]=eventId, data[3]=autoCloseTime, data[4]=customAnim, data[5]=consumable, data[6]=cooldown, data[7]=pageId, data[8]=language, data[9]=pageMaterial, data[10]=spellId, data[11]=noDamageImmune, data[12]=linkedTrapId, data[13]=large, data[14]=openTextID, data[15]=closeTextID, data[16]=losOK, data[17]=allowMounted, data[18]=floatingTooltip, data[19]=gossipID, data[20]=WorldStateSetsState

**TRANSPORT (type 11):** data[0]=pauseAtTime, data[1]=startOpen, data[2]=autoCloseTime, data[3]=pause1EventID, data[4]=pause2EventID

**AREADAMAGE (type 12):** data[0]=lockId, data[1]=radius, data[2]=damageMin, data[3]=damageMax, data[4]=damageSchool, data[5]=autoCloseTime, data[6]=openTextID, data[7]=closeTextID

**CAMERA (type 13):** data[0]=lockId, data[1]=cinematicId, data[2]=eventID, data[3]=openTextID

**MO_TRANSPORT (type 15):** data[0]=taxiPathId, data[1]=moveSpeed, data[2]=accelRate, data[3]=startEventID, data[4]=stopEventID, data[5]=transportPhysics, data[6]=mapID, data[7]=worldState1, data[8]=canBeStopped

**SUMMONING_RITUAL (type 18):** data[0]=reqParticipants, data[1]=spellId, data[2]=animSpell, data[3]=ritualPersistent, data[4]=casterTargetSpell, data[5]=casterTargetSpellTargets, data[6]=castersGrouped, data[7]=ritualNoTargetCheck

**SPELLCASTER (type 22):** data[0]=spellId, data[1]=charges, data[2]=partyOnly, data[3]=allowMounted, data[4]=large

**MEETINGSTONE (type 23):** data[0]=minLevel, data[1]=maxLevel, data[2]=areaID

**FLAGSTAND (type 24):** data[0]=lockId, data[1]=pickupSpell, data[2]=radius, data[3]=returnAura, data[4]=returnSpell, data[5]=noDamageImmune, data[6]=openTextID, data[7]=losOK

**FISHINGHOLE (type 25):** data[0]=radius, data[1]=lootId, data[2]=minSuccessOpens, data[3]=maxSuccessOpens, data[4]=lockId

**FLAGDROP (type 26):** data[0]=lockId, data[1]=eventID, data[2]=pickupSpell, data[3]=noDamageImmune, data[4]=openTextID

**CAPTURE_POINT (type 29):** data[0]=radius, data[1]=spell, data[2-3]=worldState, data[4-5]=winEventID, data[6-7]=contestedEventID, data[8-9]=progressEventID, data[10-11]=neutralEventID, data[12]=neutralPercent, data[13]=worldstate3, data[14]=minSuperiority, data[15]=maxSuperiority, data[16]=minTime, data[17]=maxTime, data[18]=large, data[19]=highlight, data[20]=startingValue, data[21]=unidirectional

**AURA_GENERATOR (type 30):** data[0]=startOpen, data[1]=radius, data[2]=auraID1, data[3]=conditionID1, data[4]=auraID2, data[5]=conditionID2, data[6]=serverOnly

**DUNGEON_DIFFICULTY (type 31):** data[0]=mapID, data[1]=difficulty

**BARBER_CHAIR (type 32):** data[0]=chairheight, data[1]=heightOffset

**DESTRUCTIBLE_BUILDING (type 33):** data[0]=intactNumHits, data[1]=creditProxyCreature, data[3]=intactEvent, data[4]=damagedDisplayId, data[5]=damagedNumHits, data[9]=damagedEvent, data[10]=destroyedDisplayId, data[14]=destroyedEvent, data[16]=debuildingTimeSecs, data[18]=destructibleData, data[19]=rebuildingEvent, data[22]=damageEvent

**TRAPDOOR (type 35):** data[0]=whenToPause, data[1]=startOpen, data[2]=autoClose

---

## GameObjectTemplateAddon

- **SQL Table:** `gameobject_template_addon`
- **Struct:** `GameObjectTemplateAddon` (`src/server/game/Entities/GameObject/GameObjectData.h`)
- **Store:** `ObjectMgr::_gameObjectTemplateAddonStore`
- **Loader:** `ObjectMgr::LoadGameObjectTemplateAddons()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| entry | uint32 | entry | Primary key |
| faction | uint32 | faction | |
| flags | uint32 | flags | |
| mingold | uint32 | mingold | |
| maxgold | uint32 | maxgold | |
| artKit0..3 | uint32[4] | artKits | |

---

## GameObjectData

- **SQL Table:** `gameobject` (LEFT JOIN `game_event_gameobject`, `pool_gameobject`)
- **Struct:** `GameObjectData` (`src/server/game/Entities/GameObject/GameObjectData.h`) extends `SpawnData`
- **Store:** `ObjectMgr::_gameObjectDataStore` (`GameObjectDataContainer`)
- **Loader:** `ObjectMgr::LoadGameobjects()` (`ObjectMgr.cpp:2845`)

Inherits SpawnData fields (see CreatureData above). Own fields:

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| id | uint32 | id | entry in gameobject_template |
| rotation0..3 | G3D::Quat | rotation | |
| spawntimesecs | int32 | spawntimesecs | |
| animprogress | uint32 | animprogress | |
| state | GOState | go_state | enum GOState |

---

## GameObjectAddon

- **SQL Table:** `gameobject_addon`
- **Struct:** `GameObjectAddon` (`src/server/game/Entities/GameObject/GameObjectData.h`)
- **Store:** `ObjectMgr::_gameObjectAddonStore`
- **Loader:** `ObjectMgr::LoadGameObjectAddons()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| ParentRotation | QuaternionData | ParentRotation | x,y,z,w |
| invisibilityType | InvisibilityType | invisibilityType | enum |
| InvisibilityValue | uint32 | InvisibilityValue | |

---

## ItemTemplate

- **SQL Table:** `item_template`
- **Struct:** `ItemTemplate` (`src/server/game/Entities/Item/ItemTemplate.h`)
- **Store:** `ObjectMgr::_itemTemplateStore` (`ItemTemplateContainer`)
- **Loader:** `ObjectMgr::LoadItemTemplates()` (`ObjectMgr.cpp:3234`)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| entry | uint32 | ItemId | Primary key |
| class | uint32 | Class | enum ItemClass |
| subclass | uint32 | SubClass | enum ItemSubClass* |
| SoundOverrideSubclass | int32 | SoundOverrideSubclass | |
| name | std::string | Name1 | |
| displayid | uint32 | DisplayInfoID | ItemDisplayInfo.dbc |
| Quality | uint32 | Quality | enum ItemQualities |
| Flags | ItemFlags | Flags | enum ItemFlags |
| FlagsExtra | ItemFlags2 | Flags2 | enum ItemFlags2 |
| BuyCount | uint32 | BuyCount | |
| BuyPrice | int32 | BuyPrice | |
| SellPrice | uint32 | SellPrice | |
| InventoryType | uint32 | InventoryType | enum InventoryType |
| AllowableClass | uint32 | AllowableClass | Class mask |
| AllowableRace | uint32 | AllowableRace | Race mask |
| ItemLevel | uint32 | ItemLevel | |
| RequiredLevel | uint32 | RequiredLevel | |
| RequiredSkill | uint32 | RequiredSkill | SkillLine.dbc |
| RequiredSkillRank | uint32 | RequiredSkillRank | |
| RequiredSpell | uint32 | RequiredSpell | |
| RequiredHonorRank | uint32 | RequiredHonorRank | |
| RequiredCityRank | uint32 | RequiredCityRank | |
| RequiredReputationFaction | uint32 | RequiredReputationFaction | Faction.dbc |
| RequiredReputationRank | uint32 | RequiredReputationRank | |
| maxcount | int32 | MaxCount | |
| stackable | int32 | Stackable | |
| ContainerSlots | uint32 | ContainerSlots | |
| *(computed)* | uint32 | StatsCount | Counted from stat_type fields |
| stat_type1..10 | _ItemStat[10] | ItemStat | See sub-struct below |
| ScalingStatDistribution | uint32 | ScalingStatDistribution | ScalingStatDistribution.dbc |
| ScalingStatValue | uint32 | ScalingStatValue | |
| dmg_min1..2, dmg_max1..2, dmg_type1..2 | _Damage[2] | Damage | See sub-struct below |
| Armor | uint32 | Armor | |
| HolyRes | int32 | HolyRes | |
| FireRes | int32 | FireRes | |
| NatureRes | int32 | NatureRes | |
| FrostRes | int32 | FrostRes | |
| ShadowRes | int32 | ShadowRes | |
| ArcaneRes | int32 | ArcaneRes | |
| delay | uint32 | Delay | |
| ammo_type | uint32 | AmmoType | |
| RangedModRange | float | RangedModRange | |
| spellid_1..5 | _Spell[5] | Spells | See sub-struct below |
| bonding | uint32 | Bonding | enum ItemBondingType |
| description | std::string | Description | |
| PageText | uint32 | PageText | |
| LanguageID | uint32 | LanguageID | |
| PageMaterial | uint32 | PageMaterial | |
| startquest | uint32 | StartQuest | |
| LockID | uint32 | LockID | |
| Material | int32 | Material | |
| sheath | uint32 | Sheath | |
| RandomProperty | int32 | RandomProperty | ItemRandomProperties.dbc |
| RandomSuffix | int32 | RandomSuffix | ItemRandomSuffix.dbc |
| block | uint32 | Block | |
| itemset | uint32 | ItemSet | ItemSet.dbc |
| MaxDurability | uint32 | MaxDurability | |
| area | uint32 | Area | AreaTable.dbc |
| map | uint32 | Map | Map.dbc |
| BagFamily | uint32 | BagFamily | Bit mask (1 &lt;&lt; id) |
| TotemCategory | uint32 | TotemCategory | TotemCategory.dbc |
| socketColor_1..3 | _Socket[3] | Socket | See sub-struct below |
| socketBonus | uint32 | socketBonus | SpellItemEnchantment.dbc |
| GemProperties | uint32 | GemProperties | GemProperties.dbc |
| RequiredDisenchantSkill | uint32 | RequiredDisenchantSkill | |
| ArmorDamageModifier | float | ArmorDamageModifier | |
| Duration | uint32 | Duration | |
| ItemLimitCategory | uint32 | ItemLimitCategory | ItemLimitCategory.dbc |
| HolidayId | uint32 | HolidayId | Holidays.dbc |
| ScriptName | uint32 | ScriptId | |
| DisenchantID | uint32 | DisenchantID | |
| FoodType | uint32 | FoodType | |
| minMoneyLoot | uint32 | MinMoneyLoot | |
| maxMoneyLoot | uint32 | MaxMoneyLoot | |
| flags_custom | ItemFlagsCustom | FlagsCu | enum ItemFlagsCustom |

Sub-struct **_ItemStat**: ItemStatType uint32 (enum ItemModType), ItemStatValue int32

Sub-struct **_Damage**: DamageMin float, DamageMax float, DamageType uint32

Sub-struct **_Spell**: SpellId int32, SpellTrigger uint32 (enum ItemSpelltriggerType), SpellCharges int32, SpellPPMRate float, SpellCooldown int32, SpellCategory uint32, SpellCategoryCooldown int32

Sub-struct **_Socket**: Color uint32 (enum SocketColor), Content uint32

---

## ItemSetNameEntry

- **SQL Table:** `item_set_names`
- **Struct:** `ItemSetNameEntry` (`src/server/game/Entities/Item/ItemTemplate.h`)
- **Store:** `ObjectMgr::_itemSetNameStore`
- **Loader:** `ObjectMgr::LoadItemSetNames()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| entry | uint32 | entry (key) | |
| name | std::string | name | |
| InventoryType | uint32 | InventoryType | |

---

## Quest

- **SQL Tables:** `quest_template`, `quest_template_addon`, `quest_details`, `quest_request_items`, `quest_offer_reward`
- **Class:** `Quest` (`src/server/game/Quests/QuestDef.h`)
- **Store:** `ObjectMgr::_questTemplates` (`QuestMap` = `std::unordered_map<uint32, Quest*>`)
- **Loader:** `ObjectMgr::LoadQuests()` (`ObjectMgr.cpp:4998`)

**quest_template fields:**

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| ID | uint32 | Id | Primary key |
| QuestType | uint32 | Method | |
| ZoneOrSort | int32 | ZoneOrSort | |
| MinLevel | uint32 | MinLevel | |
| Level | int32 | Level | QuestLevel |
| Type | uint32 | Type | enum QuestType |
| AllowableRaces | uint32 | AllowableRaces | Race mask |
| RequiredFactionId1 | uint32 | RequiredFactionId1 | |
| RequiredFactionValue1 | int32 | RequiredFactionValue1 | |
| RequiredFactionId2 | uint32 | RequiredFactionId2 | |
| RequiredFactionValue2 | int32 | RequiredFactionValue2 | |
| SuggestedPlayers | uint32 | SuggestedPlayers | |
| TimeAllowed | uint32 | TimeAllowed | |
| Flags | uint32 | Flags | enum QuestFlags |
| RewardTitle | uint32 | RewardTitleId | |
| RequiredPlayerKillCount | uint32 | RequiredPlayerKills | |
| RewardTalents | uint32 | RewardTalents | |
| RewardArenaPoints | int32 | RewardArenaPoints | |
| NextQuestInChain | uint32 | RewardNextQuest | |
| RewardXPDifficulty | uint32 | RewardXPDifficulty | |
| SrcItemId | uint32 | StartItem | |
| LogTitle | std::string | Title | |
| Details | std::string | Details | |
| Objectives | std::string | Objectives | |
| OfferRewardText | std::string | OfferRewardText | |
| RequestItemsText | std::string | RequestItemsText | |
| AreaDescription | std::string | AreaDescription | |
| CompletedText | std::string | CompletedText | |
| RewardHonor | uint32 | RewardHonor | |
| RewardKillHonor | float | RewardKillHonor | |
| RewardOrRequiredMoney | int32 | RewardMoney | |
| RewardMoneyDifficulty | uint32 | RewardMoneyDifficulty | |
| RewardDisplaySpell | uint32 | RewardDisplaySpell | |
| RewardSpell | int32 | RewardSpell | |
| POIContinent | uint32 | POIContinent | |
| POIx | float | POIx | |
| POIy | float | POIy | |
| POIPriority | uint32 | POIPriority | |
| EmoteOnIncomplete | uint32 | EmoteOnIncomplete | |
| EmoteOnComplete | uint32 | EmoteOnComplete | |
| ObjectiveText1..4 | std::string[4] | ObjectiveText | |
| RequiredItemId1..6 | uint32[6] | RequiredItemId | |
| RequiredItemCount1..6 | uint32[6] | RequiredItemCount | |
| ItemDrop1..4 | uint32[4] | ItemDrop | |
| ItemDropQuantity1..4 | uint32[4] | ItemDropQuantity | |
| RequiredNpcOrGo1..4 | int32[4] | RequiredNpcOrGo | >0 creature, <0 gameobject |
| RequiredNpcOrGoCount1..4 | uint32[4] | RequiredNpcOrGoCount | |
| RewardChoiceItemId1..6 | uint32[6] | RewardChoiceItemId | |
| RewardChoiceItemCount1..6 | uint32[6] | RewardChoiceItemCount | |
| RewardItemId1..4 | uint32[4] | RewardItemId | |
| RewardItemIdCount1..4 | uint32[4] | RewardItemIdCount | |
| RewardFactionId1..5 | uint32[5] | RewardFactionId | |
| RewardFactionValueId1..5 | int32[5] | RewardFactionValueId | |
| RewardFactionValueIdOverride1..5 | int32[5] | RewardFactionValueIdOverride | |

**quest_details fields:** DetailsEmote1..4 uint32, DetailsEmoteDelay1..4 uint32

**quest_template_addon fields:**

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| MaxLevel | uint32 | MaxLevel | |
| RequiredClasses | uint32 | RequiredClasses | Class mask |
| SourceSpellid | uint32 | SourceSpellid | |
| PrevQuestId | int32 | PrevQuestId | |
| NextQuestId | uint32 | NextQuestId | |
| ExclusiveGroup | int32 | ExclusiveGroup | |
| BreadcrumbForQuestId | uint32 | BreadcrumbForQuestId | |
| RewardMailTemplateId | uint32 | RewardMailTemplateId | |
| RewardMailDelay | uint32 | RewardMailDelay | |
| RequiredSkillId | uint32 | RequiredSkillId | |
| RequiredSkillPoints | uint32 | RequiredSkillPoints | |
| RequiredMinRepFaction | uint32 | RequiredMinRepFaction | |
| RequiredMinRepValue | int32 | RequiredMinRepValue | |
| RequiredMaxRepFaction | uint32 | RequiredMaxRepFaction | |
| RequiredMaxRepValue | int32 | RequiredMaxRepValue | |
| StartItemCount | uint32 | StartItemCount | |
| RewardMailSenderEntry | uint32 | RewardMailSenderEntry | |
| SpecialFlags | uint32 | SpecialFlags | enum QuestSpecialFlags |

---

## QuestMoneyReward

- **SQL Table:** `quest_money_reward`
- **Struct:** `QuestMoneyRewardArray` = `std::array<uint32, 10>` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_questMoneyRewards` (`QuestMoneyRewardStore` = `std::unordered_map<uint32, QuestMoneyRewardArray>`)
- **Loader:** `ObjectMgr::LoadQuestMoneyRewards()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| Level | map key | uint32 | Quest level |
| Money0 | questMoneyReward[0] | uint32 | Reward at level offset 0 |
| Money1 | questMoneyReward[1] | uint32 | |
| Money2 | questMoneyReward[2] | uint32 | |
| Money3 | questMoneyReward[3] | uint32 | |
| Money4 | questMoneyReward[4] | uint32 | |
| Money5 | questMoneyReward[5] | uint32 | |
| Money6 | questMoneyReward[6] | uint32 | |
| Money7 | questMoneyReward[7] | uint32 | |
| Money8 | questMoneyReward[8] | uint32 | |
| Money9 | questMoneyReward[9] | uint32 | |

---

## QuestPOI

- **SQL Tables:** `quest_poi`, `quest_poi_points`
- **Structs:** `QuestPOI`, `QuestPOIPoint` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_questPOIStore` (`QuestPOIContainer` = `std::unordered_map<uint32, QuestPOIVector>`)
- **Loader:** `ObjectMgr::LoadQuestPOI()`

### quest_poi → QuestPOI

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| QuestID | map key | uint32 | Groups POIs by quest |
| id | Id | uint32 | POI identifier |
| ObjectiveIndex | ObjectiveIndex | int32 | |
| MapID | MapId | uint32 | |
| WorldMapAreaId | AreaId | uint32 | |
| Floor | FloorId | uint32 | |
| Priority | Unk3 | uint32 | |
| Flags | Unk4 | uint32 | |
| VerifiedBuild | *(not loaded)* | | |

### quest_poi_points → QuestPOIPoint

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| QuestID | *(grouping)* | | Matches to parent QuestPOI |
| Idx1 | POI id match | | Matches points to POI by id |
| Idx2 | *(ordering)* | | ORDER BY Idx2 |
| X | x | int32 | |
| Y | y | int32 | |

---

## QuestAreaTrigger

- **SQL Table:** `areatrigger_involvedrelation`
- **Store:** `ObjectMgr::_questAreaTriggerStore` (`QuestAreaTriggerContainer` = `std::unordered_map<uint32, uint32>`)
- **Loader:** `ObjectMgr::LoadQuestAreaTriggers()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | map key | uint32 | AreaTrigger entry ID |
| quest | map value | uint32 | Quest ID |

---

## QuestGreeting

- **SQL Table:** `quest_greeting`
- **Struct:** `QuestGreeting` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_questGreetingStore` keyed by (id, type)

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| EmoteType | uint16 | EmoteType | |
| EmoteDelay | uint32 | EmoteDelay | |
| Greeting | std::vector&lt;std::string&gt; | Greeting | Localized |

---

## QuestRelations

- **SQL Tables:** `creature_queststarter`, `creature_questender`, `gameobject_queststarter`, `gameobject_questender`
- **Container:** `QuestRelations` = `std::multimap<uint32, uint32>`
- **Stores:** `_creatureQuestRelations`, `_creatureQuestInvolvedRelations`, `_goQuestRelations`, `_goQuestInvolvedRelations`
- **Loaders:** `LoadCreatureQuestStarters()`, `LoadCreatureQuestEnders()`, `LoadGameobjectQuestStarters()`, `LoadGameobjectQuestEnders()`

All four tables share identical schema:

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | multimap key | uint32 | Creature/GO entry |
| quest | multimap value | uint32 | Quest ID |

---

## PageText

- **SQL Table:** `page_text`
- **Struct:** `PageText` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_pageTextStore` (`PageTextContainer`)
- **Loader:** `ObjectMgr::LoadPageTexts()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| Text | std::string | Text | |
| NextPage | uint32 | NextPage | |

---

## GossipText

- **SQL Table:** `npc_text`
- **Struct:** `GossipText` (`NPCHandler.h`)
- **Store:** `ObjectMgr::_gossipTextStore` (`GossipTextContainer`)
- **Loader:** `ObjectMgr::LoadGossipText()`

Contains `GossipTextOption[8]`, each with: Text_0 string, Text_1 string, BroadcastTextID uint32, Language uint32, Probability float, Emotes[3] QEmote (Emote+Delay pairs)

---

## GossipMenus

- **SQL Table:** `gossip_menu`
- **Struct:** `GossipMenus` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_gossipMenusStore` (`GossipMenusContainer`)
- **Loader:** `ObjectMgr::LoadGossipMenu()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| MenuID | uint32 | MenuID | |
| TextID | uint32 | TextID | |

---

## GossipMenuItems

- **SQL Table:** `gossip_menu_option`
- **Struct:** `GossipMenuItems` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_gossipMenuItemsStore` (`GossipMenuItemsContainer`)
- **Loader:** `ObjectMgr::LoadGossipMenuItems()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| MenuID | uint32 | MenuID | |
| OptionID | uint32 | OptionID | |
| OptionIcon | uint8 | OptionIcon | |
| OptionText | std::string | OptionText | |
| OptionBroadcastTextID | uint32 | OptionBroadcastTextID | |
| OptionType | uint32 | OptionType | |
| OptionNpcFlag | uint32 | OptionNpcFlag | |
| ActionMenuID | uint32 | ActionMenuID | |
| ActionPoiID | uint32 | ActionPoiID | |
| BoxCoded | bool | BoxCoded | |
| BoxMoney | uint32 | BoxMoney | |
| BoxText | std::string | BoxText | |
| BoxBroadcastTextID | uint32 | BoxBroadcastTextID | |

---

## BroadcastText

- **SQL Table:** `broadcast_text` (+ `broadcast_text_locale`)
- **Struct:** `BroadcastText` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_broadcastTextStore` (`BroadcastTextContainer`)
- **Loader:** `ObjectMgr::LoadBroadcastTexts()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| ID | uint32 | Id | |
| LanguageID | uint32 | LanguageID | |
| MaleText | std::vector&lt;std::string&gt; | MaleText | Localized |
| FemaleText | std::vector&lt;std::string&gt; | FemaleText | Localized |
| EmoteId1..3 | uint32 | EmoteId1..3 | |
| EmoteDelay1..3 | uint32 | EmoteDelay1..3 | |
| SoundEntriesId | uint32 | SoundEntriesId | |
| EmotesID | uint32 | EmotesID | |
| Flags | uint32 | Flags | |

---

## PointOfInterest

- **SQL Table:** `points_of_interest`
- **Struct:** `PointOfInterest` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_pointsOfInterestStore`
- **Loader:** `ObjectMgr::LoadPointsOfInterest()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| ID | uint32 | ID | |
| PositionX | float | PositionX | |
| PositionY | float | PositionY | |
| Icon | uint32 | Icon | |
| Flags | uint32 | Flags | |
| Importance | uint32 | Importance | |
| Name | std::string | Name | |

---

## AreaTrigger

- **SQL Table:** `areatrigger`
- **Struct:** `AreaTrigger` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_areaTriggerStore`
- **Loader:** `ObjectMgr::LoadAreaTriggers()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| id | uint32 | entry | |
| map | uint32 | map | |
| x | float | x | |
| y | float | y | |
| z | float | z | |
| radius | float | radius | |
| length | float | length | |
| width | float | width | |
| height | float | height | |
| orientation | float | orientation | |

---

## AreaTriggerTeleport

- **SQL Table:** `areatrigger_teleport`
- **Struct:** `AreaTriggerTeleport` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_areaTriggerTeleportStore`
- **Loader:** `ObjectMgr::LoadAreaTriggerTeleports()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| target_map | uint32 | target_mapId | |
| target_position_x | float | target_X | |
| target_position_y | float | target_Y | |
| target_position_z | float | target_Z | |
| target_orientation | float | target_Orientation | |

---

## InstanceTemplate

- **SQL Table:** `instance_template`
- **Struct:** `InstanceTemplate` (`Map.h`)
- **Store:** `ObjectMgr::_instanceTemplateStore`
- **Loader:** `ObjectMgr::LoadInstanceTemplate()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| parent | uint32 | Parent | |
| ScriptName | uint32 | ScriptId | |
| AllowMount | bool | AllowMount | |

---

## DungeonEncounter

- **SQL Table:** `instance_encounters`
- **Struct:** `DungeonEncounter` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_dungeonEncounterStore` (`DungeonEncounterContainer` = `std::unordered_map<uint32, DungeonEncounterList>`) keyed by `MAKE_PAIR32(mapId, difficulty)`
- **Loader:** `ObjectMgr::LoadInstanceEncounters()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry | dbcEntry | DungeonEncounterEntry const* | Looked up from `sDungeonEncounterStore` DBC |
| creditType | creditType | EncounterCreditType | 0=KILL_CREATURE, 1=CAST_SPELL |
| creditEntry | creditEntry | uint32 | |
| lastEncounterDungeon | lastEncounterDungeon | uint32 | Read as uint16, stored as uint32 |
| comment | *(not loaded)* | | |

---

## DungeonProgressionRequirements

- **SQL Tables:** `dungeon_access_template`, `dungeon_access_requirements`
- **Struct:** `DungeonProgressionRequirements` (`Player.h`)
- **Store:** `ObjectMgr::_accessRequirementStore` keyed by [mapId][difficulty]
- **Loader:** `ObjectMgr::LoadAccessRequirements()`

| Field | C++ Type | Notes |
|-------|---------|-------|
| levelMin | uint8 | |
| levelMax | uint8 | |
| reqItemLevel | uint16 | |
| quests | vector&lt;ProgressionRequirement*&gt; | |
| items | vector&lt;ProgressionRequirement*&gt; | |
| achievements | vector&lt;ProgressionRequirement*&gt; | |

---

## ScriptInfo

- **SQL Tables:** `spell_scripts`, `event_scripts`, `waypoint_scripts`
- **Struct:** `ScriptInfo` (`ObjectMgr.h`)
- **Stores:** `sSpellScripts`, `sEventScripts`, `sWaypointScripts` (global `ScriptMapMap` = `std::map<uint32, ScriptMap>`)
- **Loaders:** `LoadSpellScripts()`, `LoadEventScripts()`, `LoadWaypointScripts()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | id / outer map key | uint32 | ScriptInfo::id, also key in ScriptMapMap |
| delay | delay / inner map key | uint32 | ScriptInfo::delay, also key in ScriptMap |
| command | command | ScriptCommands | Union discriminator |
| datalong | Raw.nData[0] | uint32 | Aliased as union members (e.g. Talk.ChatType) |
| datalong2 | Raw.nData[1] | uint32 | Aliased as union members (e.g. Talk.Flags) |
| dataint | Raw.nData[2] | uint32 | Aliased as union members (e.g. Talk.TextID) |
| x | Raw.fData[0] | float | Aliased as e.g. MoveTo.DestX |
| y | Raw.fData[1] | float | Aliased as e.g. MoveTo.DestY |
| z | Raw.fData[2] | float | Aliased as e.g. MoveTo.DestZ |
| o | Raw.fData[3] | float | Aliased as e.g. TeleportTo.Orientation |
| guid | *(not loaded)* | | SQL PRIMARY KEY only |

---

## RepRewardRate

- **SQL Table:** `reputation_reward_rate`
- **Struct:** `RepRewardRate` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_repRewardRateStore`
- **Loader:** `ObjectMgr::LoadReputationRewardRate()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| faction | uint32 | map key | Primary key, Faction.dbc ID |
| quest_rate | float | questRate | |
| quest_daily_rate | float | questDailyRate |
| quest_weekly_rate | float | questWeeklyRate |
| quest_monthly_rate | float | questMonthlyRate |
| quest_repeatable_rate | float | questRepeatableRate |
| creature_rate | float | creatureRate |
| spell_rate | float | spellRate |

---

## ReputationOnKillEntry

- **SQL Table:** `creature_onkill_reputation`
- **Struct:** `ReputationOnKillEntry` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_repOnKillStore`
- **Loader:** `ObjectMgr::LoadReputationOnKill()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| RepFaction1 | uint32 | RepFaction1 | |
| RepFaction2 | uint32 | RepFaction2 | |
| ReputationMaxCap1 | uint32 | ReputationMaxCap1 | |
| RepValue1 | float | RepValue1 | |
| ReputationMaxCap2 | uint32 | ReputationMaxCap2 | |
| RepValue2 | float | RepValue2 | |
| IsTeamAward1 | bool | IsTeamAward1 | |
| IsTeamAward2 | bool | IsTeamAward2 | |
| TeamDependent | bool | TeamDependent | |

---

## RepSpilloverTemplate

- **SQL Table:** `reputation_spillover_template`
- **Struct:** `RepSpilloverTemplate` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_repSpilloverTemplateStore` (`RepSpilloverTemplateContainer` = `std::unordered_map<uint32, RepSpilloverTemplate>`)
- **Loader:** `ObjectMgr::LoadReputationSpilloverTemplate()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| faction | map key | uint32 | Read as uint16 |
| faction1 | faction[0] | uint32 | |
| rate_1 | faction_rate[0] | float | |
| rank_1 | faction_rank[0] | uint32 | |
| faction2 | faction[1] | uint32 | |
| rate_2 | faction_rate[1] | float | |
| rank_2 | faction_rank[1] | uint32 | |
| faction3 | faction[2] | uint32 | |
| rate_3 | faction_rate[2] | float | |
| rank_3 | faction_rank[2] | uint32 | |
| faction4 | faction[3] | uint32 | |
| rate_4 | faction_rate[3] | float | |
| rank_4 | faction_rank[3] | uint32 | |
| faction5 | faction[4] | uint32 | |
| rate_5 | faction_rate[4] | float | |
| rank_5 | faction_rank[4] | uint32 | |
| faction6 | faction[5] | uint32 | |
| rate_6 | faction_rate[5] | float | |
| rank_6 | faction_rank[5] | uint32 | |

---

## PlayerInfo

- **SQL Tables:** `playercreateinfo`, `playercreateinfo_item`, `playercreateinfo_skills`, `playercreateinfo_spell_custom`, `playercreateinfo_cast_spell`, `playercreateinfo_action`, `player_race_stats`, `player_class_stats`, `player_xp_for_level`
- **Struct:** `PlayerInfo` (`Player.h`)
- **Store:** `ObjectMgr::_playerInfo` (2D vector [race][class])
- **Loader:** `ObjectMgr::LoadPlayerInfo()`

| Field | C++ Type | Notes |
|-------|---------|-------|
| mapId | uint32 | |
| areaId | uint32 | |
| positionX/Y/Z | float | |
| orientation | float | |
| displayId_m | uint16 | |
| displayId_f | uint16 | |
| item | PlayerCreateInfoItems | From playercreateinfo_item |
| customSpells | PlayerCreateInfoSpells | From playercreateinfo_spell_custom |
| castSpells | PlayerCreateInfoSpells | From playercreateinfo_cast_spell |
| action | PlayerCreateInfoActions | From playercreateinfo_action |
| skills | PlayerCreateInfoSkills | From playercreateinfo_skills |
| levelInfo | PlayerLevelInfo* | From player_race_stats + player_class_stats |

---

## PetLevelInfo

- **SQL Table:** `pet_levelstats`
- **Struct:** `PetLevelInfo` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_petInfoStore` (`PetLevelInfoContainer` = `std::map<uint32, PetLevelInfo*>`) indexed by `[creature_entry][level - 1]`
- **Loader:** `ObjectMgr::LoadPetLevelInfo()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| creature_entry | map key | uint32 | Creature template entry |
| level | array index | uint8 | `level - 1` into array |
| hp | health | uint32 | |
| mana | mana | uint32 | |
| str | stats[0] | uint32 | |
| agi | stats[1] | uint32 | |
| sta | stats[2] | uint32 | |
| inte | stats[3] | uint32 | |
| spi | stats[4] | uint32 | |
| armor | armor | uint32 | |
| min_dmg | min_dmg | uint32 | |
| max_dmg | max_dmg | uint32 | |

---

## SpellClickInfo

- **SQL Table:** `npc_spellclick_spells`
- **Struct:** `SpellClickInfo` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_spellClickInfoStore`
- **Loader:** `ObjectMgr::LoadNPCSpellClickSpells()`

| SQL Column | C++ Type | Field Name | Notes |
|-----------|----------|------------|-------|
| spell_id | uint32 | spellId | |
| cast_flags | uint8 | castFlags | |
| user_type | SpellClickUserTypes | userType | enum |

---

## VehicleAccessory

- **SQL Tables:** `vehicle_template_accessory`, `vehicle_accessory`
- **Struct:** `VehicleAccessory` (`VehicleDefines.h`)
- **Stores:** `_vehicleTemplateAccessoryStore` (per-entry), `_vehicleAccessoryStore` (per-guid)
  - Both are `VehicleAccessoryContainer` = `std::map<uint32, VehicleAccessoryList>`
- **Loaders:** `LoadVehicleTemplateAccessories()`, `LoadVehicleAccessories()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry / guid | map key | uint32 | Template entry vs spawn guid |
| accessory_entry | AccessoryEntry | uint32 | |
| seat_id | SeatId | int8 | |
| minion | IsMinion | uint32 | Read as bool |
| summontype | SummonedType | uint8 | Default 6 |
| summontimer | SummonTime | uint32 | Default 30000 |
| description | *(not loaded)* | | SQL comment only |

---

## VehicleSeatAddon

- **SQL Table:** `vehicle_seat_addon`
- **Struct:** `VehicleSeatAddon` (`VehicleDefines.h`)
- **Store:** `ObjectMgr::_vehicleSeatAddonStore` (`VehicleSeatAddonContainer` = `std::unordered_map<uint32, VehicleSeatAddon>`)
- **Loader:** `ObjectMgr::LoadVehicleSeatAddon()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| SeatEntry | map key | uint32 | Validated against VehicleSeat.dbc |
| SeatOrientation | SeatOrientationOffset | float | |
| ExitParamX | ExitParameterX | float | |
| ExitParamY | ExitParameterY | float | |
| ExitParamZ | ExitParameterZ | float | |
| ExitParamO | ExitParameterO | float | |
| ExitParamValue | ExitParameter | VehicleExitParameters | Enum cast |

---

## GameTele

- **SQL Table:** `game_tele`
- **Struct:** `GameTele` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_gameTeleStore`
- **Loader:** `ObjectMgr::LoadGameTele()`

| SQL Column | C++ Type | Field Name |
|-----------|----------|------------|
| position_x | float | position_x |
| position_y | float | position_y |
| position_z | float | position_z |
| orientation | float | orientation |
| map | uint32 | mapId |
| name | std::string | name |

---

## MailLevelReward

- **SQL Table:** `mail_level_reward`
- **Struct:** `MailLevelReward` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_mailLevelRewardStore` (`MailLevelRewardContainer` = `std::unordered_map<uint8, MailLevelRewardList>`)
- **Loader:** `ObjectMgr::LoadMailLevelRewards()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| level | map key | uint8 | |
| raceMask | raceMask | uint32 | |
| mailTemplateId | mailTemplateId | uint32 | |
| senderEntry | senderEntry | uint32 | |

---

## TempSummonData

- **SQL Table:** `creature_summon_groups`
- **Struct:** `TempSummonData` (`TemporarySummon.h`)
- **Store:** `ObjectMgr::_tempSummonDataStore` (`TempSummonDataContainer` = `std::map<TempSummonGroupKey, std::vector<TempSummonData>>`)
- **Loader:** `ObjectMgr::LoadTempSummons()`

Key composite: `TempSummonGroupKey` (summonerEntry uint32, summonerType SummonerType, summonGroup uint8)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| summonerId | TempSummonGroupKey._summonerEntry | uint32 | Part of composite key |
| summonerType | TempSummonGroupKey._summonerType | SummonerType | 0=Creature, 1=GO, 2=Map |
| groupId | TempSummonGroupKey._summonGroup | uint8 | Part of composite key |
| entry | entry | uint32 | |
| position_x | pos.m_positionX | float | Via pos.Relocate() |
| position_y | pos.m_positionY | float | |
| position_z | pos.m_positionZ | float | |
| orientation | pos.m_orientation | float | |
| summonType | type | TempSummonType | |
| summonTime | time | uint32 | |
| Comment | *(not loaded)* | | |

---

## LinkedRespawn

- **SQL Table:** `linked_respawn`
- **Store:** `ObjectMgr::_linkedRespawnStore` (`LinkedRespawnContainer` = `std::map<ObjectGuid, ObjectGuid>`)
- **Loader:** `ObjectMgr::LoadLinkedRespawn()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| guid | map key | ObjectGuid | HighGuid determined by linkType |
| linkedGuid | map value | ObjectGuid | HighGuid determined by linkType |
| linkType | *(determines HighGuid)* | uint8 | 0=CREATURE_TO_CREATURE, 1=CREATURE_TO_GO, 2=GO_TO_GO, 3=GO_TO_CREATURE |

---

## AcoreString

- **SQL Table:** `acore_string`
- **Struct:** `AcoreString` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_acoreStringStore` (`AcoreStringContainer` = `std::unordered_map<int32, AcoreString>`)
- **Loader:** `ObjectMgr::LoadAcoreStrings()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry | map key | int32 | |
| content_default | Content[LOCALE_enUS] | string | |
| locale_koKR | Content[LOCALE_koKR] | string | |
| locale_frFR | Content[LOCALE_frFR] | string | |
| locale_deDE | Content[LOCALE_deDE] | string | |
| locale_zhCN | Content[LOCALE_zhCN] | string | |
| locale_zhTW | Content[LOCALE_zhTW] | string | |
| locale_esES | Content[LOCALE_esES] | string | |
| locale_esMX | Content[LOCALE_esMX] | string | |
| locale_ruRU | Content[LOCALE_ruRU] | string | |

---

## ModuleString

- **SQL Tables:** `module_string`, `module_string_locale`
- **Struct:** `ModuleString` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_moduleStringStore` (`ModuleStringContainer` = `std::map<std::pair<std::string, uint32>, ModuleString>`)
- **Loaders:** `LoadModuleStrings()`, `LoadModuleStringsLocale()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| module | key.first | std::string | Module name |
| id | key.second | uint32 | String ID |
| string | Content[LOCALE_enUS] | string | Locale overrides from `module_string_locale` |

---

## Locale Stores

All locale stores map entry ID -> localized string vectors.

| SQL Table | Struct | Store Variable | Loader |
|-----------|--------|---------------|--------|
| creature_template_locale | CreatureLocale | _creatureLocaleStore | LoadCreatureLocales() |
| gameobject_template_locale | GameObjectLocale | _gameObjectLocaleStore | LoadGameObjectLocales() |
| item_template_locale | ItemLocale | _itemLocaleStore | LoadItemLocales() |
| quest_template_locale | QuestLocale | _questLocaleStore | LoadQuestLocales() |
| quest_offer_reward_locale | QuestOfferRewardLocale | _questOfferRewardLocaleStore | LoadQuestOfferRewardLocale() |
| quest_request_items_locale | QuestRequestItemsLocale | _questRequestItemsLocaleStore | LoadQuestRequestItemsLocale() |
| gossip_menu_option_locale | GossipMenuItemsLocale | _gossipMenuItemsLocaleStore | LoadGossipMenuItemsLocales() |
| npc_text_locale | NpcTextLocale | _npcTextLocaleStore | LoadNpcTextLocales() |
| page_text_locale | PageTextLocale | _pageTextLocaleStore | LoadPageTextLocales() |
| points_of_interest_locale | PointOfInterestLocale | _pointOfInterestLocaleStore | LoadPointOfInterestLocales() |
| item_set_names_locale | ItemSetNameLocale | _itemSetNameLocaleStore | LoadItemSetNameLocales() |
| quest_greeting_locale | QuestGreeting | _questGreetingStore | LoadQuestGreetingsLocales() |
| pet_name_generation_locale | HalfNameContainerLocale | _petHalfLocaleName0/1 | LoadPetNamesLocales() |
| broadcast_text_locale | BroadcastText | _broadcastTextStore | LoadBroadcastTextLocales() |

---

## Faction Change Stores

All use `CharacterConversionMap` = `std::map<uint32, uint32>` (alliance_id -> horde_id).

| SQL Table | Store Variable | Loader |
|-----------|---------------|--------|
| player_factionchange_achievement | FactionChangeAchievements | LoadFactionChangeAchievements() |
| player_factionchange_items | FactionChangeItems | LoadFactionChangeItems() |
| player_factionchange_quests | FactionChangeQuests | LoadFactionChangeQuests() |
| player_factionchange_reputation | FactionChangeReputation | LoadFactionChangeReputations() |
| player_factionchange_spells | FactionChangeSpells | LoadFactionChangeSpells() |
| player_factionchange_titles | FactionChangeTitles | LoadFactionChangeTitles() |

---

## Trainer Stores

- **SQL Tables:** `trainer`, `trainer_spell`, `trainer_locale`
- **Class:** `Trainer::Trainer` (`Trainer.h`)
- **Store:** `ObjectMgr::_trainers` (`std::unordered_map<uint32, Trainer::Trainer>`)
- **Loader:** `ObjectMgr::LoadTrainers()`

Also: `creature_default_trainer` table maps creature entry -> trainer ID, stored in `_creatureDefaultTrainers`.

---

## Fishing

- **SQL Table:** `skill_fishing_base_level`
- **Store:** `ObjectMgr::_fishingBaseForAreaStore` (`FishingBaseSkillContainer`)
- **Loader:** `ObjectMgr::LoadFishingBaseSkillLevel()`
- Map of area ID -> base skill level

---

## Reserved/Profanity Names

| Source | Store Variable | Loader |
|--------|---------------|--------|
| reserved_name (characters DB) | _reservedNamesStore | LoadReservedPlayerNamesDB() |
| NamesReserved.dbc | _reservedNamesStore | LoadReservedPlayerNamesDBC() |
| profanity_name (characters DB) | _profanityNamesStore | LoadProfanityNamesFromDB() |
| NamesProfanity.dbc | _profanityNamesStore | LoadProfanityNamesFromDBC() |

Both use `std::set<std::wstring>` containers. DBC and SQL sources are merged into the same store.

---

## TavernAreaTrigger

- **SQL Table:** `areatrigger_tavern`
- **Store:** `ObjectMgr::_tavernAreaTriggerStore` (`TavernAreaTriggerContainer` = `std::unordered_map<uint32, uint32>`)
- **Loader:** `ObjectMgr::LoadTavernAreaTriggers()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| id | map key | uint32 | AreaTrigger entry ID |
| faction | map value | uint32 | Faction bitmask |
| name | *(not loaded)* | | Description only |

---

## AreaTriggerScript

- **SQL Table:** `areatrigger_scripts`
- **Store:** `ObjectMgr::_areaTriggerScriptStore` (`AreaTriggerScriptContainer` = `std::unordered_map<uint32, uint32>`)
- **Loader:** `ObjectMgr::LoadAreaTriggerScripts()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry | map key | uint32 | AreaTrigger ID |
| ScriptName | map value | uint32 | Resolved to script ID via GetScriptId() |

---

## CreatureSparring

- **SQL Table:** `creature_sparring`
- **Store:** `ObjectMgr::_creatureSparringStore` (`CreatureSparringContainer` = `std::unordered_map<ObjectGuid::LowType, std::vector<float>>`)
- **Loader:** `ObjectMgr::LoadCreatureSparring()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| GUID | map key | ObjectGuid::LowType | Creature spawn GUID |
| SparringPCT | vector element | float | Health percentage (0-100) |

---

## ExplorationBaseXP

- **SQL Table:** `exploration_basexp`
- **Store:** `ObjectMgr::_baseXPTable` (`BaseXPContainer` = `std::map<uint32, uint32>`)
- **Loader:** `ObjectMgr::LoadExplorationBaseXP()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| level | map key | uint32 | Read as uint8 |
| basexp | map value | uint32 | Base XP for level |

---

## PlayerXPperLevel

- **SQL Table:** `player_xp_for_level`
- **Store:** `ObjectMgr::_playerXPperLevel` (`PlayerXPperLevel` = `std::vector<uint32>`)
- **Loader:** Loaded inside `ObjectMgr::LoadPlayerInfo()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| Level | array index | uint8 | Vector index |
| Experience | vector element | uint32 | XP required for next level |

---

## PetNameGeneration

- **SQL Table:** `pet_name_generation`
- **Stores:** `ObjectMgr::_petHalfName0` (prefix), `ObjectMgr::_petHalfName1` (suffix) — both `HalfNameContainer` = `std::map<uint32, std::vector<std::string>>`
- **Loader:** `ObjectMgr::LoadPetNames()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| entry | map key | uint32 | Creature family entry |
| word | vector element | std::string | Name word part |
| half | *(selects store)* | uint8 | 0 = _petHalfName0 (prefix), 1 = _petHalfName1 (suffix) |

---

## CreatureCustomIDs

- **Source:** Config key `Creatures.CustomIDs` (comma-separated list)
- **Store:** `ObjectMgr::_creatureCustomIDsStore` (`CreatureCustomIDsContainer` = `std::vector<uint32>`)
- **Loader:** `ObjectMgr::LoadCreatureCustomIDs()`

No SQL table. Parsed from worldserver.conf at startup.

---

## CreatureMovementOverride

- **SQL Tables:** `creature_movement_override` (COALESCE with `creature_template_movement`)
- **Struct:** `CreatureMovementData` (`CreatureData.h`)
- **Store:** `ObjectMgr::_creatureMovementOverrides` (`std::unordered_map<ObjectGuid::LowType, CreatureMovementData>`)
- **Loader:** `ObjectMgr::LoadCreatureMovementOverrides()`

| SQL Column (COALESCE) | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| cmo.SpawnId | map key | ObjectGuid::LowType | |
| COALESCE(cmo.Ground, ctm.Ground) | Ground | CreatureGroundMovementType | None=0, Run=1, Hover=2 |
| COALESCE(cmo.Swim, ctm.Swim) | Swim | bool | |
| COALESCE(cmo.Flight, ctm.Flight) | Flight | CreatureFlightMovementType | None=0, DisableGravity=1, CanFly=2 |
| COALESCE(cmo.Rooted, ctm.Rooted) | Rooted | bool | |
| COALESCE(cmo.Chase, ctm.Chase) | Chase | CreatureChaseMovementType | Run=0, CanWalk=1, AlwaysWalk=2 |
| COALESCE(cmo.Random, ctm.Random) | Random | CreatureRandomMovementType | Walk=0, CanRun=1, AlwaysRun=2 |
| COALESCE(cmo.InteractionPauseTimer, ctm.InteractionPauseTimer) | InteractionPauseTimer | uint32 | Milliseconds |

---

## GameObjectQuestItem

- **SQL Table:** `gameobject_questitem`
- **Store:** `ObjectMgr::_gameObjectQuestItemStore` (`GameObjectQuestItemMap` = `std::unordered_map<uint32, std::vector<uint32>>`)
- **Loader:** `ObjectMgr::LoadGameObjectQuestItems()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| GameObjectEntry | map key | uint32 | GO template entry |
| ItemId | vector element | uint32 | Item entry |
| Idx | *(ordering)* | uint32 | ORDER BY only |
| VerifiedBuild | *(not loaded)* | | |

---

## CreatureQuestItem

- **SQL Table:** `creature_questitem`
- **Store:** `ObjectMgr::_creatureQuestItemStore` (`CreatureQuestItemMap` = `std::unordered_map<uint32, std::vector<uint32>>`)
- **Loader:** `ObjectMgr::LoadCreatureQuestItems()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| CreatureEntry | map key | uint32 | Creature template entry |
| ItemId | vector element | uint32 | Item entry |
| Idx | *(ordering)* | uint32 | ORDER BY only |
| VerifiedBuild | *(not loaded)* | | |

---

## GameObjectSummonData

- **SQL Table:** `gameobject_summon_groups`
- **Struct:** `GameObjectSummonData` (`ObjectMgr.h`), `TempSummonGroupKey` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_goSummonDataStore` (`GameObjectSummonDataContainer` = `std::map<TempSummonGroupKey, std::vector<GameObjectSummonData>>`)
- **Loader:** `ObjectMgr::LoadGameObjectSummons()`

Key composite: `TempSummonGroupKey` (summonerEntry, summonerType, summonGroup)

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| summonerId | TempSummonGroupKey._summonerEntry | uint32 | Key part |
| summonerType | TempSummonGroupKey._summonerType | SummonerType | 0=Creature, 1=GO, 2=Map |
| groupId | TempSummonGroupKey._summonGroup | uint8 | Key part |
| entry | entry | uint32 | GO template to summon |
| position_x | pos.x | float | |
| position_y | pos.y | float | |
| position_z | pos.z | float | |
| orientation | pos.orientation | float | |
| rotation0 | rot | G3D::Quat | Quaternion w |
| rotation1 | rot | G3D::Quat | Quaternion x |
| rotation2 | rot | G3D::Quat | Quaternion y |
| rotation3 | rot | G3D::Quat | Quaternion z |
| respawnTime | respawnTime | uint32 | Seconds |
| Comment | *(not loaded)* | | |

---

## SpawnGroupData

- **Source:** Hardcoded default (no SQL table in base schema)
- **Struct:** `SpawnGroupTemplateData` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_spawnGroupDataStore` (`SpawnGroupDataContainer` = `std::unordered_map<uint32, SpawnGroupTemplateData>`)
- **Loader:** Initialized in ObjectMgr constructor

| Field | C++ Type | Notes |
|-------|----------|-------|
| groupId | uint32 | |
| name | std::string | |
| mapid | uint16 | |
| flags | SpawnGroupFlags | SPAWNGROUP_FLAG_SYSTEM, etc. |

Default entry: `{0, "Default Group", 0, SPAWNGROUP_FLAG_SYSTEM}`

---

## PlayerTotemModel

- **SQL Table:** `player_totem_model`
- **Store:** `ObjectMgr::_playerTotemModel` (`PlayerTotemModelMap` = `std::map<std::pair<SummonSlot, Races>, uint32>`)
- **Loader:** `ObjectMgr::LoadPlayerTotemModels()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| TotemID | key.first | SummonSlot | SUMMON_SLOT_TOTEM_FIRE=1, etc. |
| RaceID | key.second | Races | ChrRacesEntry validated |
| ModelID | map value | uint32 | Creature display ID |

---

## PlayerShapeshiftModel

- **SQL Table:** `player_shapeshift_model`
- **Store:** `ObjectMgr::_playerShapeshiftModel` (`PlayerShapeshiftModelMap` = `std::map<std::tuple<ShapeshiftForm, uint8, uint8, uint8>, uint32>`)
- **Loader:** `ObjectMgr::LoadPlayerShapeshiftModels()`

| SQL Column | C++ Field | C++ Type | Notes |
|-----------|----------|----------|-------|
| ShapeshiftID | get<0> | ShapeshiftForm | |
| RaceID | get<1> | uint8 | ChrRacesEntry validated |
| CustomizationID | get<2> | uint8 | Skin/hair color index |
| GenderID | get<3> | uint8 | GENDER_MALE=0, GENDER_FEMALE=1 |
| ModelID | map value | uint32 | Creature display ID |

---

## ScriptNameStore

- **Source:** UNION of DISTINCT ScriptName from multiple tables
- **Store:** `ObjectMgr::_scriptNamesStore` (`ScriptNameContainer` = `std::vector<std::string>`)
- **Loader:** `ObjectMgr::LoadScriptNames()`

Aggregates ScriptName columns from: `achievement_criteria_data`, `battleground_template`, `creature`, `creature_template`, `gameobject`, `gameobject_template`, `item_template`, `areatrigger_scripts`, `spell_script_names`, `transports`, `game_weather`, `conditions`, `outdoorpvp_template`, `instance_template`.

Index 0 is always empty (dummy "no script"). Each unique name gets a numeric ID (its vector index).

---

## MapObjectGuids

- **Source:** Derived from `creature` and `gameobject` spawn data
- **Struct:** `CellObjectGuids` (`ObjectMgr.h`)
- **Store:** `ObjectMgr::_mapObjectGuidsStore` (`MapObjectGuids` = nested `std::unordered_map`)
- **Loader:** Populated during `LoadCreatures()` / `LoadGameobjects()` via `AddCreatureToGrid()` / `AddGameobjectToGrid()`

Outer key: `MAKE_PAIR32(mapId, spawnMode)`, Inner key: grid cell ID.

| Field | C++ Type | Notes |
|-------|----------|-------|
| creatures | std::set&lt;ObjectGuid::LowType&gt; | Creature spawn GUIDs in this cell |
| gameobjects | std::set&lt;ObjectGuid::LowType&gt; | GO spawn GUIDs in this cell |
