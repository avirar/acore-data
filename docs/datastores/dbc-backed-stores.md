# DBC-Backed Datastores

This document lists all datastores that originate from binary DBC files, with optional SQL overlay tables. For architecture details, see [README.md](README.md).

Each entry includes:
- The C++ struct name and its fields with types
- The DBC file name
- The SQL overlay table name
- The global store variable
- The format string variable

## Table of Contents

1. [AchievementEntry](#achievemententry)
2. [AchievementCategoryEntry](#achievementcategoryentry)
3. [AchievementCriteriaEntry](#achievementcriteriaentry)
4. [AreaTableEntry](#areatableentry)
5. [AreaGroupEntry](#areagroupentry)
6. [AreaPOIEntry](#areapoientry)
7. [AuctionHouseEntry](#auctionhouseentry)
8. [BankBagSlotPricesEntry](#bankbagslotpricesentry)
9. [BarberShopStyleEntry](#barbershopstyleentry)
10. [BattlemasterListEntry](#battlemasterlistentry)
11. [CharStartOutfitEntry](#charstartoutfitentry)
12. [CharSectionsEntry](#charsectionsentry)
13. [CharTitlesEntry](#chartitlesentry)
14. [ChatChannelsEntry](#chatchannelsentry)
15. [ChrClassesEntry](#chrclassesentry)
16. [ChrRacesEntry](#chrracesentry)
17. [CinematicCameraEntry](#cinematiccameraentry)
18. [CinematicSequencesEntry](#cinematicsequencesentry)
19. [CreatureDisplayInfoEntry](#creaturedisplayinfoentry)
20. [CreatureDisplayInfoExtraEntry](#creaturedisplayinfoextraentry)
21. [CreatureFamilyEntry](#creaturefamilyentry)
22. [CreatureModelDataEntry](#creaturemodeldataentry)
23. [CreatureSpellDataEntry](#creaturespelldataentry)
24. [CreatureTypeEntry](#creaturetypeentry)
25. [CurrencyTypesEntry](#currencytypesentry)
26. [DestructibleModelDataEntry](#destructiblemodeldataentry)
27. [DungeonEncounterEntry](#dungeonencounterentry)
28. [DurabilityCostsEntry](#durabilitycostsentry)
29. [DurabilityQualityEntry](#durabilityqualityentry)
30. [EmotesEntry](#emotesentry)
31. [EmotesTextEntry](#emotestextentry)
32. [EmotesTextSoundEntry](#emotetextsoundentry)
33. [FactionEntry](#factionentry)
34. [FactionTemplateEntry](#factiontemplateentry)
35. [GameObjectArtKitEntry](#gameobjectartkitentry)
36. [GameObjectDisplayInfoEntry](#gameobjectdisplayinfoentry)
37. [GemPropertiesEntry](#gempropertiesentry)
38. [GlyphPropertiesEntry](#glyphpropertiesentry)
39. [GlyphSlotEntry](#glyphslotentry)
40. [GtBarberShopCostBaseEntry](#gtbarbershopcostbaseentry)
41. [GtCombatRatingsEntry](#gtcombatratingsentry)
42. [GtChanceToMeleeCritBaseEntry](#gtchancetomeleecritbaseentry)
43. [GtChanceToMeleeCritEntry](#gtchancetomeleecritentry)
44. [GtChanceToSpellCritBaseEntry](#gtchancetospellcritbaseentry)
45. [GtChanceToSpellCritEntry](#gtchancetospellcritentry)
46. [GtNPCManaCostScalerEntry](#gtnpcmanacostscalerentry)
47. [GtOCTClassCombatRatingScalarEntry](#gtoctclasscombatratingscalarentry)
48. [GtOCTRegenHPEntry](#gtoctregenhpentry)
49. [GtRegenHPPerSptEntry](#gtregenhppersptentry)
50. [GtRegenMPPerSptEntry](#gtregenmppersptentry)
51. [HolidaysEntry](#holidaysentry)
52. [ItemEntry](#itementry)
53. [ItemBagFamilyEntry](#itembagfamilyentry)
54. [ItemDisplayInfoEntry](#itemdisplayinfoentry)
55. [ItemExtendedCostEntry](#itemextendedcostentry)
56. [ItemLimitCategoryEntry](#itemlimitcategoryentry)
57. [ItemRandomPropertiesEntry](#itemrandompropertiesentry)
58. [ItemRandomSuffixEntry](#itemrandomsuffixentry)
59. [ItemSetEntry](#itemsetentry)
60. [LFGDungeonEntry](#lfgdungeonentry)
61. [LightEntry](#lightentry)
62. [LiquidTypeEntry](#liquidtypeentry)
63. [LockEntry](#lockentry)
64. [MailTemplateEntry](#mailtemplateentry)
65. [MapEntry](#mapentry)
66. [MapDifficultyEntry](#mapdifficultyentry)
67. [MovieEntry](#movieentry)
68. [NamesReservedEntry](#namesreservedentry)
69. [NamesProfanityEntry](#namesprofanityentry)
70. [OverrideSpellDataEntry](#overridespelldataentry)
71. [PowerDisplayEntry](#powerdisplayentry)
72. [PvPDifficultyEntry](#pvpdifficultyentry)
73. [QuestSortEntry](#questsortentry)
74. [QuestXPEntry](#questxpentry)
75. [QuestFactionRewEntry](#questfactionrewentry)
76. [RandomPropertiesPointsEntry](#randompropertypointsentry)
77. [ScalingStatDistributionEntry](#scalingstatdistributionentry)
78. [ScalingStatValuesEntry](#scalingstatvaluesentry)
79. [SkillLineEntry](#skilllineentry)
80. [SkillLineAbilityEntry](#skilllineabilityentry)
81. [SkillRaceClassInfoEntry](#skillraceclassinfoentry)
82. [SkillTiersEntry](#skilltiersentry)
83. [SoundEntriesEntry](#soundentriesentry)
84. [SpellEntry](#spellentry)
85. [SpellCastTimesEntry](#spellcasttimesentry)
86. [SpellCategoryEntry](#spellcategoryentry)
87. [SpellDifficultyEntry](#spelldifficultyentry)
88. [SpellDurationEntry](#spelldurationentry)
89. [SpellFocusObjectEntry](#spellfocusobjectentry)
90. [SpellItemEnchantmentEntry](#spellitemenchantmententry)
91. [SpellItemEnchantmentConditionEntry](#spellitemenchantmentconditionentry)
92. [SpellRadiusEntry](#spellradiusentry)
93. [SpellRangeEntry](#spellrangeentry)
94. [SpellRuneCostEntry](#spellrunecostentry)
95. [SpellShapeshiftFormEntry](#spellshapeshiftformentry)
96. [SpellVisualEntry](#spellvisualentry)
97. [StableSlotPricesEntry](#stableslotpricesentry)
98. [SummonPropertiesEntry](#summonpropertiesentry)
99. [TalentEntry](#talententry)
100. [TalentTabEntry](#talenttabentry)
101. [TaxiNodesEntry](#taxinodesentry)
102. [TaxiPathEntry](#taxipathentry)
103. [TaxiPathNodeEntry](#taxipathnodeentry)
104. [TeamContributionPointsEntry](#teamcontributionpointsentry)
105. [TotemCategoryEntry](#totemcategoryentry)
106. [TransportAnimationEntry](#transportanimationentry)
107. [TransportRotationEntry](#transportrotationentry)
108. [VehicleEntry](#vehicleentry)
109. [VehicleSeatEntry](#vehicleseatentry)
110. [WMOAreaTableEntry](#wmoareatableentry)
111. [WorldMapAreaEntry](#worldmapareaentry)
112. [WorldMapOverlayEntry](#worldmapoverlayentry)

---

## AchievementEntry

- **DBC File:** Achievement.dbc
- **SQL Table:** achievement_dbc
- **Store:** `sAchievementStore` (`DBCStorage<AchievementEntry>`)
- **Format:** `Achievementfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | requiredFaction | int32 | requiredFaction | -1=all, 0=horde, 1=alliance |
| 2 | mapID | int32 | mapID | -1=none |
| 4-19 | name | std::array<char const*,16> | name[0..15] | Localized |
| 38 | categoryId | uint32 | categoryId | - |
| 39 | points | uint32 | points | - |
| 41 | flags | uint32 | flags | - |
| 60 | count | uint32 | count | Completed criterias needed |
| 61 | refAchievement | uint32 | refAchievement | - |

## AchievementCategoryEntry

- **DBC File:** Achievement_Category.dbc
- **SQL Table:** achievement_category_dbc
- **Store:** `sAchievementCategoryStore` (`DBCStorage<AchievementCategoryEntry>`)
- **Format:** `AchievementCategoryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | int32 | ID | Primary key |
| 1 | parentCategory | int32 | parentCategory | -1=main |
| 19 | sortOrder | uint32 | sortOrder | - |

## AchievementCriteriaEntry

- **DBC File:** Achievement_Criteria.dbc
- **SQL Table:** achievement_criteria_dbc
- **Store:** `sAchievementCriteriaStore` (`DBCStorage<AchievementCriteriaEntry>`)
- **Format:** `AchievementCriteriafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | referredAchievement | uint32 | referredAchievement | - |
| 2 | requiredType | uint32 | requiredType | - |
| 3 | contentGroupID | uint32 | contentGroupID | Union - varies by type |
| 4 | thresholdcount | uint32 | thresholdcount | Union |
| 5-8 | additionalRequirements | - | additionalRequirements[2] | Type+value pairs |
| 26 | flags | uint32 | flags | - |
| 27 | timedType | uint32 | timedType | - |
| 28 | timerStartEvent | uint32 | timerStartEvent | - |
| 29 | timeLimit | uint32 | timeLimit | - |
| 30 | showOrder | uint32 | showOrder | - |

## AreaTableEntry

- **DBC File:** AreaTable.dbc
- **SQL Table:** areatable_dbc
- **Store:** `sAreaTableStore` (`DBCStorage<AreaTableEntry>`)
- **Format:** `AreaTableEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | mapid | uint32 | mapid | - |
| 2 | zone | uint32 | zone | 0=zone itself |
| 3 | exploreFlag | uint32 | exploreFlag | - |
| 4 | flags | uint32 | flags | - |
| 10 | area_level | int32 | area_level | - |
| 11-26 | area_name | char const*[16] | area_name[0..15] | Localized |
| 28 | team | uint32 | team | - |
| 29-32 | LiquidTypeOverride | uint32 | LiquidTypeOverride[0..3] | - |

## AreaGroupEntry

- **DBC File:** AreaGroup.dbc
- **SQL Table:** areagroup_dbc
- **Store:** `sAreaGroupStore` (`DBCStorage<AreaGroupEntry>`)
- **Format:** `AreaGroupEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | AreaGroupId | uint32 | AreaGroupId | Primary key |
| 1-6 | AreaId | uint32 | AreaId[0..5] | - |
| 7 | nextGroup | uint32 | nextGroup | - |

## AreaPOIEntry

- **DBC File:** AreaPOI.dbc
- **SQL Table:** areapoi_dbc
- **Store:** `sAreaPOIStore` (`DBCStorage<AreaPOIEntry>`)
- **Format:** `AreaPOIEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |
| 1-11 | icon | uint32 | icon[0..10] | - |
| 12 | x | float | x | - |
| 13 | y | float | y | - |
| 14 | z | float | z | - |
| 15 | mapId | uint32 | mapId | - |
| 17 | zoneId | uint32 | zoneId | - |
| 52 | worldState | uint32 | worldState | - |

## AuctionHouseEntry

- **DBC File:** AuctionHouse.dbc
- **SQL Table:** auctionhouse_dbc
- **Store:** `sAuctionHouseStore` (`DBCStorage<AuctionHouseEntry>`)
- **Format:** `AuctionHouseEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | houseId | uint32 | houseId | Primary key |
| 1 | faction | uint32 | faction | - |
| 2 | depositPercent | uint32 | depositPercent | - |
| 3 | cutPercent | uint32 | cutPercent | - |

## BankBagSlotPricesEntry

- **DBC File:** BankBagSlotPrices.dbc
- **SQL Table:** bankbagslotprices_dbc
- **Store:** `sBankBagSlotPricesStore` (`DBCStorage<BankBagSlotPricesEntry>`)
- **Format:** `BankBagSlotPricesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | price | uint32 | price | - |

## BarberShopStyleEntry

- **DBC File:** BarberShopStyle.dbc
- **SQL Table:** barbershopstyle_dbc
- **Store:** `sBarberShopStyleStore` (`DBCStorage<BarberShopStyleEntry>`)
- **Format:** `BarberShopStyleEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | type | uint32 | type | 0=hair, 2=facialhair |
| 37 | race | uint32 | race | - |
| 38 | gender | uint32 | gender | 0=male, 1=female |
| 39 | hair_id | uint32 | hair_id | - |

## BattlemasterListEntry

- **DBC File:** BattlemasterList.dbc
- **SQL Table:** battlemasterlist_dbc
- **Store:** `sBattlemasterListStore` (`DBCStorage<BattlemasterListEntry>`)
- **Format:** `BattlemasterListEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |
| 1-8 | mapid | int32 | mapid[0..7] | - |
| 9 | type | uint32 | type | 3=BG, 4=arena |
| 11-26 | name | char const*[16] | name[0..15] | Localized |
| 28 | maxGroupSize | uint32 | maxGroupSize | - |
| 29 | HolidayWorldStateId | uint32 | HolidayWorldStateId | - |

## CharStartOutfitEntry

- **DBC File:** CharStartOutfit.dbc
- **SQL Table:** charstartoutfit_dbc
- **Store:** `sCharStartOutfitStore` (`DBCStorage<CharStartOutfitEntry>`)
- **Format:** `CharStartOutfitEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | Race | uint8 | Race | - |
| 2 | Class | uint8 | Class | - |
| 3 | Gender | uint8 | Gender | - |
| 5-28 | ItemId | int32 | ItemId[0..23] | - |

## CharSectionsEntry

- **DBC File:** CharSections.dbc
- **SQL Table:** charsections_dbc
- **Store:** `sCharSectionsStore` (`DBCStorage<CharSectionsEntry>`)
- **Format:** `CharSectionsEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | Race | uint32 | Race | - |
| - | Gender | uint32 | Gender | - |
| - | GenType | uint32 | GenType | - |
| - | Flags | uint32 | Flags | - |
| - | Type | uint32 | Type | - |
| - | Color | uint32 | Color | - |

## CharTitlesEntry

- **DBC File:** CharTitles.dbc
- **SQL Table:** chartitles_dbc
- **Store:** `sCharTitlesStore` (`DBCStorage<CharTitlesEntry>`)
- **Format:** `CharTitlesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 2-17 | nameMale | char const*[16] | nameMale[0..15] | Localized |
| 19-34 | nameFemale | char const*[16] | nameFemale[0..15] | Localized |
| 36 | bit_index | uint32 | bit_index | - |

## ChatChannelsEntry

- **DBC File:** ChatChannels.dbc
- **SQL Table:** chatchannels_dbc
- **Store:** `sChatChannelsStore` (`DBCStorage<ChatChannelsEntry>`)
- **Format:** `ChatChannelsEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ChannelID | uint32 | ChannelID | Primary key |
| 1 | flags | uint32 | flags | - |
| 3-18 | pattern | char const*[16] | pattern[0..15] | Localized |

## ChrClassesEntry

- **DBC File:** ChrClasses.dbc
- **SQL Table:** chrclasses_dbc
- **Store:** `sChrClassesStore` (`DBCStorage<ChrClassesEntry>`)
- **Format:** `ChrClassesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ClassID | uint32 | ClassID | Primary key |
| 2 | powerType | uint32 | powerType | - |
| 56 | spellfamily | uint32 | spellfamily | - |
| 58 | CinematicSequence | uint32 | CinematicSequence | - |
| 59 | expansion | uint32 | expansion | - |

## ChrRacesEntry

- **DBC File:** ChrRaces.dbc
- **SQL Table:** chrraces_dbc
- **Store:** `sChrRacesStore` (`DBCStorage<ChrRacesEntry>`)
- **Format:** `ChrRacesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | RaceID | uint32 | RaceID | Primary key |
| 1 | Flags | uint32 | Flags | - |
| 2 | FactionID | uint32 | FactionID | - |
| 4 | model_m | uint32 | model_m | - |
| 5 | model_f | uint32 | model_f | - |
| 7 | TeamID | uint32 | TeamID | 7=Alliance, 1=Horde |
| 12 | CinematicSequence | uint32 | CinematicSequence | - |
| 13 | alliance | uint32 | alliance | 0=alliance, 1=horde |
| 68 | expansion | uint32 | expansion | - |

## CinematicCameraEntry

- **DBC File:** CinematicCamera.dbc
- **SQL Table:** cinematiccamera_dbc
- **Store:** `sCinematicCameraStore` (`DBCStorage<CinematicCameraEntry>`)
- **Format:** `CinematicCameraEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | Model | char const* | Model | - |
| 2 | SoundID | uint32 | SoundID | - |
| 3-5 | Origin | DBCPosition3D | Origin | X, Y, Z |
| 6 | OriginFacing | float | OriginFacing | - |

## CinematicSequencesEntry

- **DBC File:** CinematicSequences.dbc
- **SQL Table:** cinematicsequences_dbc
- **Store:** `sCinematicSequencesStore` (`DBCStorage<CinematicSequencesEntry>`)
- **Format:** `CinematicSequencesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 2 | cinematicCamera | uint32 | cinematicCamera | - |

## CreatureDisplayInfoEntry

- **DBC File:** CreatureDisplayInfo.dbc
- **SQL Table:** creaturedisplayinfo_dbc
- **Store:** `sCreatureDisplayInfoStore` (`DBCStorage<CreatureDisplayInfoEntry>`)
- **Format:** `CreatureDisplayInfofmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Displayid | uint32 | Displayid | Primary key |
| 1 | ModelId | uint32 | ModelId | - |
| 3 | ExtendedDisplayInfoID | uint32 | ExtendedDisplayInfoID | - |
| 4 | scale | float | scale | - |

## CreatureDisplayInfoExtraEntry

- **DBC File:** CreatureDisplayInfoExtra.dbc
- **SQL Table:** creaturedisplayinfoextra_dbc
- **Store:** `sCreatureDisplayInfoExtraStore` (`DBCStorage<CreatureDisplayInfoExtraEntry>`)
- **Format:** `CreatureDisplayInfoExtrafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | DisplayRaceID | uint32 | DisplayRaceID | - |

## CreatureFamilyEntry

- **DBC File:** CreatureFamily.dbc
- **SQL Table:** creaturefamily_dbc
- **Store:** `sCreatureFamilyStore` (`DBCStorage<CreatureFamilyEntry>`)
- **Format:** `CreatureFamilyfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | minScale | float | minScale | - |
| 2 | minScaleLevel | uint32 | minScaleLevel | - |
| 3 | maxScale | float | maxScale | - |
| 4 | maxScaleLevel | uint32 | maxScaleLevel | - |
| 5-6 | skillLine | uint32 | skillLine[0..1] | - |
| 7 | petFoodMask | uint32 | petFoodMask | - |
| 8 | petTalentType | int32 | petTalentType | - |

## CreatureModelDataEntry

- **DBC File:** CreatureModelData.dbc
- **SQL Table:** creaturemodeldata_dbc
- **Store:** `sCreatureModelDataStore` (`DBCStorage<CreatureModelDataEntry>`)
- **Format:** `CreatureModelDatafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | Flags | uint32 | Flags | - |
| - | Scale | float | Scale | - |
| - | CollisionWidth | float | CollisionWidth | - |
| - | CollisionHeight | float | CollisionHeight | - |
| - | MountHeight | float | MountHeight | - |

## CreatureSpellDataEntry

- **DBC File:** CreatureSpellData.dbc
- **SQL Table:** creaturespelldata_dbc
- **Store:** `sCreatureSpellDataStore` (`DBCStorage<CreatureSpellDataEntry>`)
- **Format:** `CreatureSpellDatafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-4 | spellId | uint32 | spellId[0..3] | - |

## CreatureTypeEntry

- **DBC File:** CreatureType.dbc
- **SQL Table:** creaturetype_dbc
- **Store:** `sCreatureTypeStore` (`DBCStorage<CreatureTypeEntry>`)
- **Format:** `CreatureTypefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 18 | no_expirience | uint32 | no_expirience | - |

## CurrencyTypesEntry

- **DBC File:** CurrencyTypes.dbc
- **SQL Table:** currencytypes_dbc
- **Store:** `sCurrencyTypesStore` (`DBCStorage<CurrencyTypesEntry>`)
- **Format:** `CurrencyTypesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | ItemId | uint32 | ItemId | Used as real index |
| 3 | BitIndex | uint32 | BitIndex | - |

## DestructibleModelDataEntry

- **DBC File:** DestructibleModelData.dbc
- **SQL Table:** destructiblemodeldata_dbc
- **Store:** `sDestructibleModelDataStore` (`DBCStorage<DestructibleModelDataEntry>`)
- **Format:** `DestructibleModelDatafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | DamagedDisplayId | uint32 | DamagedDisplayId | - |
| - | DestroyedDisplayId | uint32 | DestroyedDisplayId | - |
| - | RebuildingDisplayId | uint32 | RebuildingDisplayId | - |
| - | SmokeDisplayId | uint32 | SmokeDisplayId | - |

## DungeonEncounterEntry

- **DBC File:** DungeonEncounter.dbc
- **SQL Table:** dungeonencounter_dbc
- **Store:** `sDungeonEncounterStore` (`DBCStorage<DungeonEncounterEntry>`)
- **Format:** `DungeonEncounterfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |
| 1 | mapId | uint32 | mapId | - |
| 2 | difficulty | uint32 | difficulty | - |
| 4 | encounterIndex | uint32 | encounterIndex | - |
| 5-20 | encounterName | char const*[16] | encounterName[0..15] | Localized |

## DurabilityCostsEntry

- **DBC File:** DurabilityCosts.dbc
- **SQL Table:** durabilitycosts_dbc
- **Store:** `sDurabilityCostsStore` (`DBCStorage<DurabilityCostsEntry>`)
- **Format:** `DurabilityCostsfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Itemlvl | uint32 | Itemlvl | Primary key |
| 1-29 | multiplier | uint32 | multiplier[0..28] | - |

## DurabilityQualityEntry

- **DBC File:** DurabilityQuality.dbc
- **SQL Table:** durabilityquality_dbc
- **Store:** `sDurabilityQualityStore` (`DBCStorage<DurabilityQualityEntry>`)
- **Format:** `DurabilityQualityfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | quality_mod | float | quality_mod | - |

## EmotesEntry

- **DBC File:** Emotes.dbc
- **SQL Table:** emotes_dbc
- **Store:** `sEmotesStore` (`DBCStorage<EmotesEntry>`)
- **Format:** `EmotesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 3 | Flags | uint32 | Flags | - |
| 4 | EmoteType | uint32 | EmoteType | 0/1/2 |
| 5 | UnitStandState | uint32 | UnitStandState | - |

## EmotesTextEntry

- **DBC File:** EmotesText.dbc
- **SQL Table:** emotestext_dbc
- **Store:** `sEmotesTextStore` (`DBCStorage<EmotesTextEntry>`)
- **Format:** `EmotesTextEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | textid | uint32 | textid | - |

## EmotesTextSoundEntry

- **DBC File:** EmotesTextSound.dbc
- **SQL Table:** emotetextsound_dbc
- **Store:** `sEmotesTextSoundStore` (`DBCStorage<EmotesTextSoundEntry>`)
- **Format:** `EmotesTextSoundEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | EmotesTextId | uint32 | EmotesTextId | - |
| 2 | RaceId | uint32 | RaceId | - |
| 3 | SexId | uint32 | SexId | 0=male, 1=female |
| 4 | SoundId | uint32 | SoundId | - |

## FactionEntry

- **DBC File:** Faction.dbc
- **SQL Table:** faction_dbc
- **Store:** `sFactionStore` (`DBCStorage<FactionEntry>`)
- **Format:** `FactionEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | reputationListID | int32 | reputationListID | - |
| 2-5 | BaseRepRaceMask | uint32 | BaseRepRaceMask[0..3] | - |
| 6-9 | BaseRepClassMask | uint32 | BaseRepClassMask[0..3] | - |
| 10-13 | BaseRepValue | int32 | BaseRepValue[0..3] | - |
| 14-17 | ReputationFlags | uint32 | ReputationFlags[0..3] | - |
| 18 | team | uint32 | team | - |
| 19 | spilloverRateIn | float | spilloverRateIn | - |
| 20 | spilloverRateOut | float | spilloverRateOut | - |
| 21 | spilloverMaxRankIn | uint32 | spilloverMaxRankIn | - |

## FactionTemplateEntry

- **DBC File:** FactionTemplate.dbc
- **SQL Table:** factiontemplate_dbc
- **Store:** `sFactionTemplateStore` (`DBCStorage<FactionTemplateEntry>`)
- **Format:** `FactionTemplateEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | faction | uint32 | faction | - |
| 2 | factionFlags | uint32 | factionFlags | - |
| 3 | ourMask | uint32 | ourMask | - |
| 4 | friendlyMask | uint32 | friendlyMask | - |
| 5 | hostileMask | uint32 | hostileMask | - |
| 6-9 | enemyFaction | uint32 | enemyFaction[0..3] | - |
| 10-13 | friendFaction | uint32 | friendFaction[0..3] | - |

## GameObjectArtKitEntry

- **DBC File:** GameObjectArtKit.dbc
- **SQL Table:** gameobjectartkit_dbc
- **Store:** `sGameObjectArtKitStore` (`DBCStorage<GameObjectArtKitEntry>`)
- **Format:** `GameObjectArtKitfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |

## GameObjectDisplayInfoEntry

- **DBC File:** GameObjectDisplayInfo.dbc
- **SQL Table:** gameobjectdisplayinfo_dbc
- **Store:** `sGameObjectDisplayInfoStore` (`DBCStorage<GameObjectDisplayInfoEntry>`)
- **Format:** `GameObjectDisplayInfofmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Displayid | uint32 | Displayid | Primary key |
| 1 | filename | char const* | filename | - |
| - | minX | float | minX | Bounding box |
| - | minY | float | minY | Bounding box |
| - | minZ | float | minZ | Bounding box |
| - | maxX | float | maxX | Bounding box |
| - | maxY | float | maxY | Bounding box |
| - | maxZ | float | maxZ | Bounding box |

## GemPropertiesEntry

- **DBC File:** GemProperties.dbc
- **SQL Table:** gemproperties_dbc
- **Store:** `sGemPropertiesStore` (`DBCStorage<GemPropertiesEntry>`)
- **Format:** `GemPropertiesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ID | uint32 | ID | Primary key |
| - | spellitemenchantement | uint32 | spellitemenchantement | - |
| - | color | uint32 | color | - |

## GlyphPropertiesEntry

- **DBC File:** GlyphProperties.dbc
- **SQL Table:** glyphproperties_dbc
- **Store:** `sGlyphPropertiesStore` (`DBCStorage<GlyphPropertiesEntry>`)
- **Format:** `GlyphPropertiesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | SpellId | uint32 | SpellId | - |
| - | TypeFlags | uint32 | TypeFlags | - |

## GlyphSlotEntry

- **DBC File:** GlyphSlot.dbc
- **SQL Table:** glyphslot_dbc
- **Store:** `sGlyphSlotStore` (`DBCStorage<GlyphSlotEntry>`)
- **Format:** `GlyphSlotfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | TypeFlags | uint32 | TypeFlags | - |
| - | Order | uint32 | Order | - |

## GtBarberShopCostBaseEntry

- **DBC File:** gtBarberShopCostBase.dbc
- **SQL Table:** gtbarbershopcostbase_dbc
- **Store:** `sGtBarberShopCostBaseStore` (`DBCStorage<GtBarberShopCostBaseEntry>`)
- **Format:** `GtBarberShopCostBasefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | cost | float | cost | - |

## GtCombatRatingsEntry

- **DBC File:** gtCombatRatings.dbc
- **SQL Table:** gtcombatratings_dbc
- **Store:** `sGtCombatRatingsStore` (`DBCStorage<GtCombatRatingsEntry>`)
- **Format:** `GtCombatRatingsfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtChanceToMeleeCritBaseEntry

- **DBC File:** gtChanceToMeleeCritBase.dbc
- **SQL Table:** gtchancetomeleecritbase_dbc
- **Store:** `sGtChanceToMeleeCritBaseStore` (`DBCStorage<GtChanceToMeleeCritBaseEntry>`)
- **Format:** `GtChanceToMeleeCritBasefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | base | float | base | - |

## GtChanceToMeleeCritEntry

- **DBC File:** gtChanceToMeleeCrit.dbc
- **SQL Table:** gtchancetomeleecrit_dbc
- **Store:** `sGtChanceToMeleeCritStore` (`DBCStorage<GtChanceToMeleeCritEntry>`)
- **Format:** `GtChanceToMeleeCritfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtChanceToSpellCritBaseEntry

- **DBC File:** gtChanceToSpellCritBase.dbc
- **SQL Table:** gtchancetospellcritbase_dbc
- **Store:** `sGtChanceToSpellCritBaseStore` (`DBCStorage<GtChanceToSpellCritBaseEntry>`)
- **Format:** `GtChanceToSpellCritBasefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | base | float | base | - |

## GtChanceToSpellCritEntry

- **DBC File:** gtChanceToSpellCrit.dbc
- **SQL Table:** gtchancetospellcrit_dbc
- **Store:** `sGtChanceToSpellCritStore` (`DBCStorage<GtChanceToSpellCritEntry>`)
- **Format:** `GtChanceToSpellCritfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtNPCManaCostScalerEntry

- **DBC File:** gtNPCManaCostScaler.dbc
- **SQL Table:** gtnpcmanacostscaler_dbc
- **Store:** `sGtNPCManaCostScalerStore` (`DBCStorage<GtNPCManaCostScalerEntry>`)
- **Format:** `GtNPCManaCostScalerfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtOCTClassCombatRatingScalarEntry

- **DBC File:** gtOCTClassCombatRatingScalar.dbc
- **SQL Table:** gtoctclasscombatratingscalar_dbc
- **Store:** `sGtOCTClassCombatRatingScalarStore` (`DBCStorage<GtOCTClassCombatRatingScalarEntry>`)
- **Format:** `GtOCTClassCombatRatingScalarfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtOCTRegenHPEntry

- **DBC File:** gtOCTRegenHP.dbc
- **SQL Table:** gtoctregenhp_dbc
- **Store:** `sGtOCTRegenHPStore` (`DBCStorage<GtOCTRegenHPEntry>`)
- **Format:** `GtOCTRegenHPfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtRegenHPPerSptEntry

- **DBC File:** gtRegenHPPerSpt.dbc
- **SQL Table:** gtregenhpperspt_dbc
- **Store:** `sGtRegenHPPerSptStore` (`DBCStorage<GtRegenHPPerSptEntry>`)
- **Format:** `GtRegenHPPerSptfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## GtRegenMPPerSptEntry

- **DBC File:** gtRegenMPPerSpt.dbc
- **SQL Table:** gtregenmpperspt_dbc
- **Store:** `sGtRegenMPPerSptStore` (`DBCStorage<GtRegenMPPerSptEntry>`)
- **Format:** `GtRegenMPPerSptfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ratio | float | ratio | - |

## HolidaysEntry

- **DBC File:** Holidays.dbc
- **SQL Table:** holidays_dbc
- **Store:** `sHolidaysStore` (`DBCStorage<HolidaysEntry>`)
- **Format:** `Holidaysfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1-10 | Duration | uint32 | Duration[0..9] | - |
| 11-36 | Date | uint32 | Date[0..25] | - |
| 37 | Region | uint32 | Region | - |
| 38 | Looping | uint32 | Looping | - |
| 39-48 | CalendarFlags | uint32 | CalendarFlags[0..9] | - |
| 51 | TextureFilename | char const* | TextureFilename | - |
| 52 | Priority | uint32 | Priority | - |
| 53 | CalendarFilterType | int32 | CalendarFilterType | - |

## ItemEntry

- **DBC File:** Item.dbc
- **SQL Table:** item_dbc
- **Store:** `sItemStore` (`DBCStorage<ItemEntry>`)
- **Format:** `Itemfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | ClassID | uint32 | ClassID | - |
| 2 | SubclassID | uint32 | SubclassID | - |
| 3 | SoundOverrideSubclassID | int32 | SoundOverrideSubclassID | - |
| 4 | Material | int32 | Material | - |
| 5 | DisplayInfoID | uint32 | DisplayInfoID | - |
| 6 | InventoryType | uint32 | InventoryType | - |
| 7 | SheatheType | uint32 | SheatheType | - |

## ItemBagFamilyEntry

- **DBC File:** ItemBagFamily.dbc
- **SQL Table:** itembagfamily_dbc
- **Store:** `sItemBagFamilyStore` (`DBCStorage<ItemBagFamilyEntry>`)
- **Format:** `ItemBagFamilyfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |

## ItemDisplayInfoEntry

- **DBC File:** ItemDisplayInfo.dbc
- **SQL Table:** itemdisplayinfo_dbc
- **Store:** `sItemDisplayInfoStore` (`DBCStorage<ItemDisplayInfoEntry>`)
- **Format:** `ItemDisplayTemplateEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 3 | inventoryIcon | char const* | inventoryIcon | - |

## ItemExtendedCostEntry

- **DBC File:** ItemExtendedCost.dbc
- **SQL Table:** itemextendedcost_dbc
- **Store:** `sItemExtendedCostStore` (`DBCStorage<ItemExtendedCostEntry>`)
- **Format:** `ItemExtendedCostEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | reqhonorpoints | uint32 | reqhonorpoints | - |
| 2 | reqarenapoints | uint32 | reqarenapoints | - |
| 3 | reqarenaslot | uint32 | reqarenaslot | - |
| 4-8 | reqitem | uint32 | reqitem[0..4] | - |
| 9-13 | reqitemcount | uint32 | reqitemcount[0..4] | - |
| 14 | reqpersonalarenarating | uint32 | reqpersonalarenarating | - |

## ItemLimitCategoryEntry

- **DBC File:** ItemLimitCategory.dbc
- **SQL Table:** itemlimitcategory_dbc
- **Store:** `sItemLimitCategoryStore` (`DBCStorage<ItemLimitCategoryEntry>`)
- **Format:** `ItemLimitCategoryEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 18 | maxCount | uint32 | maxCount | - |
| 19 | mode | uint32 | mode | 0=have, 1=equip |

## ItemRandomPropertiesEntry

- **DBC File:** ItemRandomProperties.dbc
- **SQL Table:** itemrandomproperties_dbc
- **Store:** `sItemRandomPropertiesStore` (`DBCStorage<ItemRandomPropertiesEntry>`)
- **Format:** `ItemRandomPropertiesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 2-6 | Enchantment | uint32 | Enchantment[0..4] | - |
| 7-22 | Name | std::array<char const*,16> | Name[0..15] | Localized |

## ItemRandomSuffixEntry

- **DBC File:** ItemRandomSuffix.dbc
- **SQL Table:** itemrandomsuffix_dbc
- **Store:** `sItemRandomSuffixStore` (`DBCStorage<ItemRandomSuffixEntry>`)
- **Format:** `ItemRandomSuffixfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-16 | Name | std::array<char const*,16> | Name[0..15] | Localized |
| 19-23 | Enchantment | uint32 | Enchantment[0..4] | - |
| 24-28 | AllocationPct | uint32 | AllocationPct[0..4] | - |

## ItemSetEntry

- **DBC File:** ItemSet.dbc
- **SQL Table:** itemset_dbc
- **Store:** `sItemSetStore` (`DBCStorage<ItemSetEntry>`)
- **Format:** `ItemSetEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1-16 | name | std::array<char const*,16> | name[0..15] | Localized |
| 18-27 | itemId | uint32 | itemId[0..9] | - |
| 35-42 | spells | uint32 | spells[0..7] | - |
| 43-50 | items_to_triggerspell | uint32 | items_to_triggerspell[0..7] | - |
| 51 | required_skill_id | uint32 | required_skill_id | - |
| 52 | required_skill_value | uint32 | required_skill_value | - |

## LFGDungeonEntry

- **DBC File:** LFGDungeons.dbc
- **SQL Table:** lfgdungeons_dbc
- **Store:** `sLFGDungeonStore` (`DBCStorage<LFGDungeonEntry>`)
- **Format:** `LFGDungeonEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-16 | Name | std::array<char const*,16> | Name[0..15] | Localized |
| 18 | MinLevel | uint32 | MinLevel | - |
| 19 | MaxLevel | uint32 | MaxLevel | - |
| 23 | MapID | uint32 | MapID | - |
| 24 | Difficulty | uint32 | Difficulty | - |
| 25 | Flags | uint32 | Flags | - |
| 26 | TypeID | uint32 | TypeID | - |
| 29 | ExpansionLevel | uint32 | ExpansionLevel | - |
| 31 | GroupID | uint32 | GroupID | - |

## LightEntry

- **DBC File:** Light.dbc
- **SQL Table:** light_dbc
- **Store:** `sLightStore` (`DBCStorage<LightEntry>`)
- **Format:** `LightEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | MapId | uint32 | MapId | - |
| - | X | float | X | - |
| - | Y | float | Y | - |
| - | Z | float | Z | - |

## LiquidTypeEntry

- **DBC File:** LiquidType.dbc
- **SQL Table:** liquidtype_dbc
- **Store:** `sLiquidTypeStore` (`DBCStorage<LiquidTypeEntry>`)
- **Format:** `LiquidTypefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | Type | uint32 | Type | - |
| - | SpellId | uint32 | SpellId | - |

## LockEntry

- **DBC File:** Lock.dbc
- **SQL Table:** lock_dbc
- **Store:** `sLockStore` (`DBCStorage<LockEntry>`)
- **Format:** `LockEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-8 | Type | uint32 | Type[0..7] | - |
| 9-16 | Index | uint32 | Index[0..7] | - |
| 17-24 | Skill | uint32 | Skill[0..7] | - |

## MailTemplateEntry

- **DBC File:** MailTemplate.dbc
- **SQL Table:** mailtemplate_dbc
- **Store:** `sMailTemplateStore` (`DBCStorage<MailTemplateEntry>`)
- **Format:** `MailTemplateEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 18-33 | content | std::array<char const*,16> | content[0..15] | Localized |

## MapEntry

- **DBC File:** Map.dbc
- **SQL Table:** map_dbc
- **Store:** `sMapStore` (`DBCStorage<MapEntry>`)
- **Format:** `MapEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | MapID | uint32 | MapID | Primary key |
| 2 | map_type | uint32 | map_type | - |
| 3 | Flags | uint32 | Flags | - |
| 5-20 | name | std::array<char const*,16> | name[0..15] | Localized |
| 22 | linked_zone | uint32 | linked_zone | - |
| 57 | multimap_id | uint32 | multimap_id | - |
| 59 | entrance_map | int32 | entrance_map | - |
| 60 | entrance_x | float | entrance_x | - |
| 61 | entrance_y | float | entrance_y | - |
| 63 | expansionID | uint32 | expansionID | - |
| 65 | maxPlayers | uint32 | maxPlayers | - |

## MapDifficultyEntry

- **DBC File:** MapDifficulty.dbc
- **SQL Table:** mapdifficulty_dbc
- **Store:** `sMapDifficultyStore` (`DBCStorage<MapDifficultyEntry>`)
- **Format:** `MapDifficultyEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | MapId | uint32 | MapId | - |
| 2 | Difficulty | uint32 | Difficulty | - |
| 3-18 | areaTriggerText | char const*[16] | areaTriggerText[0..15] | Localized |
| 20 | resetTime | uint32 | resetTime | - |
| 21 | maxPlayers | uint32 | maxPlayers | - |

## MovieEntry

- **DBC File:** Movie.dbc
- **SQL Table:** movie_dbc
- **Store:** `sMovieStore` (`DBCStorage<MovieEntry>`)
- **Format:** `MovieEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 2 | volume | uint32 | volume | - |

## NamesReservedEntry

- **DBC File:** NamesReserved.dbc
- **SQL Table:** namesreserved_dbc
- **Store:** `sNamesReservedStore` (`DBCStorage<NamesReservedEntry>`)
- **Format:** `NamesReservedfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | Pattern | char const* | Pattern | - |

## NamesProfanityEntry

- **DBC File:** NamesProfanity.dbc
- **SQL Table:** namesprofanity_dbc
- **Store:** `sNamesProfanityStore` (`DBCStorage<NamesProfanityEntry>`)
- **Format:** `NamesProfanityfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | Pattern | char const* | Pattern | - |

## OverrideSpellDataEntry

- **DBC File:** OverrideSpellData.dbc
- **SQL Table:** overridespelldata_dbc
- **Store:** `sOverrideSpellDataStore` (`DBCStorage<OverrideSpellDataEntry>`)
- **Format:** `OverrideSpellDatafmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |
| 1-10 | spellId | uint32 | spellId[0..9] | - |

## PowerDisplayEntry

- **DBC File:** PowerDisplay.dbc
- **SQL Table:** powerdisplay_dbc
- **Store:** `sPowerDisplayStore` (`DBCStorage<PowerDisplayEntry>`)
- **Format:** `PowerDisplayfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | PowerType | uint32 | PowerType | - |

## PvPDifficultyEntry

- **DBC File:** PvpDifficulty.dbc
- **SQL Table:** pvpdifficulty_dbc
- **Store:** `sPvPDifficultyStore` (`DBCStorage<PvPDifficultyEntry>`)
- **Format:** `PvPDifficultyfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | mapId | uint32 | mapId | - |
| 2 | bracketId | uint32 | bracketId | - |
| 3 | minLevel | uint32 | minLevel | - |
| 4 | maxLevel | uint32 | maxLevel | - |
| 5 | difficulty | uint32 | difficulty | - |

## QuestSortEntry

- **DBC File:** QuestSort.dbc
- **SQL Table:** questsort_dbc
- **Store:** `sQuestSortStore` (`DBCStorage<QuestSortEntry>`)
- **Format:** `QuestSortEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |

## QuestXPEntry

- **DBC File:** QuestXP.dbc
- **SQL Table:** questxp_dbc
- **Store:** `sQuestXPStore` (`DBCStorage<QuestXPEntry>`)
- **Format:** `QuestXPfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | id | uint32 | id | Primary key |
| - | Exp | uint32 | Exp[0..9] | - |

## QuestFactionRewEntry

- **DBC File:** QuestFactionReward.dbc
- **SQL Table:** questfactionreward_dbc
- **Store:** `sQuestFactionRewardStore` (`DBCStorage<QuestFactionRewEntry>`)
- **Format:** `QuestFactionRewardfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | id | uint32 | id | Primary key |
| - | QuestRewFactionValue | int32 | QuestRewFactionValue[0..9] | - |

## RandomPropertiesPointsEntry

- **DBC File:** RandPropPoints.dbc
- **SQL Table:** randproppoints_dbc
- **Store:** `sRandomPropertiesPointsStore` (`DBCStorage<RandomPropertiesPointsEntry>`)
- **Format:** `RandomPropertiesPointsfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | itemLevel | uint32 | itemLevel | - |
| 2-6 | EpicPropertiesPoints | uint32 | EpicPropertiesPoints[0..4] | - |
| 7-11 | RarePropertiesPoints | uint32 | RarePropertiesPoints[0..4] | - |
| 12-16 | UncommonPropertiesPoints | uint32 | UncommonPropertiesPoints[0..4] | - |

## ScalingStatDistributionEntry

- **DBC File:** ScalingStatDistribution.dbc
- **SQL Table:** scalingstatdistribution_dbc
- **Store:** `sScalingStatDistributionStore` (`DBCStorage<ScalingStatDistributionEntry>`)
- **Format:** `ScalingStatDistributionfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1-10 | StatMod | int32 | StatMod[0..9] | - |
| 11-20 | Modifier | uint32 | Modifier[0..9] | - |
| 21 | MaxLevel | uint32 | MaxLevel | - |

## ScalingStatValuesEntry

- **DBC File:** ScalingStatValues.dbc
- **SQL Table:** scalingstatvalues_dbc
- **Store:** `sScalingStatValuesStore` (`DBCStorage<ScalingStatValuesEntry>`)
- **Format:** `ScalingStatValuesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | Level | uint32 | Level | - |
| 2-5 | ssdMultiplier | uint32 | ssdMultiplier[0..3] | - |
| 6-9 | armorMod | uint32 | armorMod[0..3] | - |
| 10-15 | dpsMod | uint32 | dpsMod[0..5] | - |
| 16 | spellPower | uint32 | spellPower | - |

## SkillLineEntry

- **DBC File:** SkillLine.dbc
- **SQL Table:** skillline_dbc
- **Store:** `sSkillLineStore` (`DBCStorage<SkillLineEntry>`)
- **Format:** `SkillLinefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | id | uint32 | id | Primary key |
| 1 | categoryId | int32 | categoryId | - |
| 3-18 | name | std::array<char const*,16> | name[0..15] | Localized |
| 37 | spellIcon | uint32 | spellIcon | - |
| 55 | canLink | uint32 | canLink | - |

## SkillLineAbilityEntry

- **DBC File:** SkillLineAbility.dbc
- **SQL Table:** skilllineability_dbc
- **Store:** `sSkillLineAbilityStore` (`DBCStorage<SkillLineAbilityEntry>`)
- **Format:** `SkillLineAbilityfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | SkillLine | uint32 | SkillLine | - |
| 2 | Spell | uint32 | Spell | - |
| 3 | RaceMask | uint32 | RaceMask | - |
| 4 | ClassMask | uint32 | ClassMask | - |
| 7 | MinSkillLineRank | uint32 | MinSkillLineRank | - |
| 8 | SupercededBySpell | uint32 | SupercededBySpell | - |
| 9 | AcquireMethod | uint32 | AcquireMethod | - |
| 10 | TrivialSkillLineRankHigh | uint32 | TrivialSkillLineRankHigh | - |
| 11 | TrivialSkillLineRankLow | uint32 | TrivialSkillLineRankLow | - |

## SkillRaceClassInfoEntry

- **DBC File:** SkillRaceClassInfo.dbc
- **SQL Table:** skillraceclassinfo_dbc
- **Store:** `sSkillRaceClassInfoStore` (`DBCStorage<SkillRaceClassInfoEntry>`)
- **Format:** `SkillRaceClassInfofmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | SkillID | uint32 | SkillID | - |
| 2 | RaceMask | uint32 | RaceMask | - |
| 3 | ClassMask | uint32 | ClassMask | - |
| 4 | Flags | uint32 | Flags | - |
| 6 | SkillTierID | uint32 | SkillTierID | - |

## SkillTiersEntry

- **DBC File:** SkillTiers.dbc
- **SQL Table:** skilltiers_dbc
- **Store:** `sSkillTiersStore` (`DBCStorage<SkillTiersEntry>`)
- **Format:** `SkillTiersfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 17-32 | Value | uint32 | Value[0..15] | - |

## SoundEntriesEntry

- **DBC File:** SoundEntries.dbc
- **SQL Table:** soundentries_dbc
- **Store:** `sSoundEntriesStore` (`DBCStorage<SoundEntriesEntry>`)
- **Format:** `SoundEntriesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |

## SpellEntry

- **DBC File:** Spell.dbc
- **SQL Table:** spell_dbc
- **Store:** `sSpellStore` (`DBCStorage<SpellEntry>`)
- **Format:** `SpellEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | Category | uint32 | Category | - |
| 2 | Dispel | uint32 | Dispel | - |
| 3 | Mechanic | uint32 | Mechanic | - |
| 4 | Attributes | uint32 | Attributes | - |
| 5 | AttributesEx | uint32 | AttributesEx | - |
| 6 | AttributesEx2 | uint32 | AttributesEx2 | - |
| 7 | AttributesEx3 | uint32 | AttributesEx3 | - |
| 8 | AttributesEx4 | uint32 | AttributesEx4 | - |
| 9 | AttributesEx5 | uint32 | AttributesEx5 | - |
| 10 | AttributesEx6 | uint32 | AttributesEx6 | - |
| 11 | AttributesEx7 | uint32 | AttributesEx7 | - |
| 12 | Stances | uint32 | Stances | - |
| 14 | StancesNot | uint32 | StancesNot | - |
| 16 | Targets | uint32 | Targets | - |
| 17 | TargetCreatureType | uint32 | TargetCreatureType | - |
| 18 | RequiresSpellFocus | uint32 | RequiresSpellFocus | - |
| 19 | FacingCasterFlags | uint32 | FacingCasterFlags | - |
| 20 | CasterAuraState | uint32 | CasterAuraState | - |
| 21 | TargetAuraState | uint32 | TargetAuraState | - |
| 22 | CasterAuraStateNot | uint32 | CasterAuraStateNot | - |
| 23 | TargetAuraStateNot | uint32 | TargetAuraStateNot | - |
| 24 | CasterAuraSpell | uint32 | CasterAuraSpell | - |
| 25 | TargetAuraSpell | uint32 | TargetAuraSpell | - |
| 26 | ExcludeCasterAuraSpell | uint32 | ExcludeCasterAuraSpell | - |
| 27 | ExcludeTargetAuraSpell | uint32 | ExcludeTargetAuraSpell | - |
| 28 | CastingTimeIndex | uint32 | CastingTimeIndex | - |
| 29 | RecoveryTime | uint32 | RecoveryTime | - |
| 30 | CategoryRecoveryTime | uint32 | CategoryRecoveryTime | - |
| 31 | InterruptFlags | uint32 | InterruptFlags | - |
| 32 | AuraInterruptFlags | uint32 | AuraInterruptFlags | - |
| 33 | ChannelInterruptFlags | uint32 | ChannelInterruptFlags | - |
| 34 | ProcFlags | uint32 | ProcFlags | - |
| 35 | ProcChance | uint32 | ProcChance | - |
| 36 | ProcCharges | uint32 | ProcCharges | - |
| 37 | MaxLevel | uint32 | MaxLevel | - |
| 38 | BaseLevel | uint32 | BaseLevel | - |
| 39 | SpellLevel | uint32 | SpellLevel | - |
| 40 | DurationIndex | uint32 | DurationIndex | - |
| 41 | PowerType | uint32 | PowerType | - |
| 42 | ManaCost | uint32 | ManaCost | - |
| 43 | ManaCostPerlevel | uint32 | ManaCostPerlevel | - |
| 44 | ManaPerSecond | uint32 | ManaPerSecond | - |
| 45 | ManaPerSecondPerLevel | uint32 | ManaPerSecondPerLevel | - |
| 46 | RangeIndex | uint32 | RangeIndex | - |
| 47 | Speed | float | Speed | - |
| 49 | StackAmount | uint32 | StackAmount | - |
| 50-51 | Totem | uint32 | Totem[0..1] | - |
| 52-59 | Reagent | int32 | Reagent[0..7] | - |
| 60-67 | ReagentCount | uint32 | ReagentCount[0..7] | - |
| 68 | EquippedItemClass | int32 | EquippedItemClass | - |
| 69 | EquippedItemSubClassMask | int32 | EquippedItemSubClassMask | - |
| 70 | EquippedItemInventoryTypeMask | int32 | EquippedItemInventoryTypeMask | - |
| 71-73 | Effect | uint32 | Effect[0..2] | - |
| 74-76 | EffectDieSides | int32 | EffectDieSides[0..2] | - |
| 77-79 | EffectRealPointsPerLevel | float | EffectRealPointsPerLevel[0..2] | - |
| 80-82 | EffectBasePoints | int32 | EffectBasePoints[0..2] | - |
| 83-85 | EffectMechanic | uint32 | EffectMechanic[0..2] | - |
| 86-88 | EffectImplicitTargetA | uint32 | EffectImplicitTargetA[0..2] | - |
| 89-91 | EffectImplicitTargetB | uint32 | EffectImplicitTargetB[0..2] | - |
| 92-94 | EffectRadiusIndex | uint32 | EffectRadiusIndex[0..2] | - |
| 95-97 | EffectApplyAuraName | uint32 | EffectApplyAuraName[0..2] | - |
| 98-100 | EffectAmplitude | uint32 | EffectAmplitude[0..2] | - |
| 101-103 | EffectValueMultiplier | float | EffectValueMultiplier[0..2] | - |
| 104-106 | EffectChainTarget | uint32 | EffectChainTarget[0..2] | - |
| 107-109 | EffectItemType | uint32 | EffectItemType[0..2] | - |
| 110-112 | EffectMiscValue | int32 | EffectMiscValue[0..2] | - |
| 113-115 | EffectMiscValueB | int32 | EffectMiscValueB[0..2] | - |
| 116-118 | EffectTriggerSpell | uint32 | EffectTriggerSpell[0..2] | - |
| 119-121 | EffectPointsPerComboPoint | float | EffectPointsPerComboPoint[0..2] | - |
| 122-130 | EffectSpellClassMask | flag96 | EffectSpellClassMask[0..2] | - |
| 131-132 | SpellVisual | uint32 | SpellVisual[0..1] | - |
| 133 | SpellIconID | uint32 | SpellIconID | - |
| 134 | ActiveIconID | uint32 | ActiveIconID | - |
| 136-151 | SpellName | std::array<char const*,16> | SpellName[0..15] | Localized |
| 153-168 | Rank | std::array<char const*,16> | Rank[0..15] | Localized |
| 204 | ManaCostPercentage | uint32 | ManaCostPercentage | - |
| 205 | StartRecoveryCategory | uint32 | StartRecoveryCategory | - |
| 206 | StartRecoveryTime | uint32 | StartRecoveryTime | - |
| 207 | MaxTargetLevel | uint32 | MaxTargetLevel | - |
| 208 | SpellFamilyName | uint32 | SpellFamilyName | - |
| 209-211 | SpellFamilyFlags | flag96 | SpellFamilyFlags | - |
| 212 | MaxAffectedTargets | uint32 | MaxAffectedTargets | - |
| 213 | DmgClass | uint32 | DmgClass | - |
| 214 | PreventionType | uint32 | PreventionType | - |
| 222-223 | TotemCategory | uint32 | TotemCategory[0..1] | - |
| 224 | AreaGroupId | int32 | AreaGroupId | - |
| 225 | SchoolMask | uint32 | SchoolMask | - |
| 226 | RuneCostID | uint32 | RuneCostID | - |
| 229-231 | EffectBonusMultiplier | float | EffectBonusMultiplier[0..2] | - |

## SpellCastTimesEntry

- **DBC File:** SpellCastTimes.dbc
- **SQL Table:** spellcasttimes_dbc
- **Store:** `sSpellCastTimesStore` (`DBCStorage<SpellCastTimesEntry>`)
- **Format:** `SpellCastTimefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | CastTime | int32 | CastTime | - |

## SpellCategoryEntry

- **DBC File:** SpellCategory.dbc
- **SQL Table:** spellcategory_dbc
- **Store:** `sSpellCategoryStore` (`DBCStorage<SpellCategoryEntry>`)
- **Format:** `SpellCategoryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Id | uint32 | Id | Primary key |
| - | Flags | uint32 | Flags | - |

## SpellDifficultyEntry

- **DBC File:** SpellDifficulty.dbc
- **SQL Table:** spelldifficulty_dbc
- **Store:** `sSpellDifficultyStore` (`DBCStorage<SpellDifficultyEntry>`)
- **Format:** `SpellDifficultyfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | SpellID | int32 | SpellID[0] | 10N |
| 2 | SpellID | int32 | SpellID[1] | 25N |
| 3 | SpellID | int32 | SpellID[2] | 10H |
| 4 | SpellID | int32 | SpellID[3] | 25H |

## SpellDurationEntry

- **DBC File:** SpellDuration.dbc
- **SQL Table:** spellduration_dbc
- **Store:** `sSpellDurationStore` (`DBCStorage<SpellDurationEntry>`)
- **Format:** `SpellDurationfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ID | uint32 | ID | Primary key |
| - | Duration | int32 | Duration[0..2] | - |

## SpellFocusObjectEntry

- **DBC File:** SpellFocusObject.dbc
- **SQL Table:** spellfocusobject_dbc
- **Store:** `sSpellFocusObjectStore` (`DBCStorage<SpellFocusObjectEntry>`)
- **Format:** `SpellFocusObjectfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |

## SpellItemEnchantmentEntry

- **DBC File:** SpellItemEnchantment.dbc
- **SQL Table:** spellitemenchantment_dbc
- **Store:** `sSpellItemEnchantmentStore` (`DBCStorage<SpellItemEnchantmentEntry>`)
- **Format:** `SpellItemEnchantmentfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | charges | uint32 | charges | - |
| 2-4 | type | uint32 | type[0..2] | - |
| 5-7 | amount | uint32 | amount[0..2] | - |
| 11-13 | spellid | uint32 | spellid[0..2] | - |
| 14-29 | description | std::array<char const*,16> | description[0..15] | Localized |
| 31 | aura_id | uint32 | aura_id | - |
| 32 | slot | uint32 | slot | - |
| 33 | GemID | uint32 | GemID | - |
| 34 | EnchantmentCondition | uint32 | EnchantmentCondition | - |
| 35 | requiredSkill | uint32 | requiredSkill | - |
| 36 | requiredSkillValue | uint32 | requiredSkillValue | - |
| 37 | requiredLevel | uint32 | requiredLevel | - |

## SpellItemEnchantmentConditionEntry

- **DBC File:** SpellItemEnchantmentCondition.dbc
- **SQL Table:** spellitemenchantmentcondition_dbc
- **Store:** `sSpellItemEnchantmentConditionStore` (`DBCStorage<SpellItemEnchantmentConditionEntry>`)
- **Format:** `SpellItemEnchantmentConditionEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-5 | Color | uint8 | Color[0..4] | - |
| 11-15 | Comparator | uint8 | Comparator[0..4] | - |
| 21-25 | Value | uint32 | Value[0..4] | - |

## SpellRadiusEntry

- **DBC File:** SpellRadius.dbc
- **SQL Table:** spellradius_dbc
- **Store:** `sSpellRadiusStore` (`DBCStorage<SpellRadiusEntry>`)
- **Format:** `SpellRadiusfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | ID | uint32 | ID | Primary key |
| - | RadiusMin | float | RadiusMin | - |
| - | RadiusPerLevel | float | RadiusPerLevel | - |
| - | RadiusMax | float | RadiusMax | - |

## SpellRangeEntry

- **DBC File:** SpellRange.dbc
- **SQL Table:** spellrange_dbc
- **Store:** `sSpellRangeStore` (`DBCStorage<SpellRangeEntry>`)
- **Format:** `SpellRangefmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1-2 | RangeMin | float | RangeMin[0..1] | - |
| 3-4 | RangeMax | float | RangeMax[0..1] | - |
| 5 | Flags | uint32 | Flags | - |

## SpellRuneCostEntry

- **DBC File:** SpellRuneCost.dbc
- **SQL Table:** spellrunecost_dbc
- **Store:** `sSpellRuneCostStore` (`DBCStorage<SpellRuneCostEntry>`)
- **Format:** `SpellRuneCostfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | RuneCost | uint32 | RuneCost[0] | Blood |
| 2 | RuneCost | uint32 | RuneCost[1] | Frost |
| 3 | RuneCost | uint32 | RuneCost[2] | Unholy |
| 4 | runePowerGain | uint32 | runePowerGain | - |

## SpellShapeshiftFormEntry

- **DBC File:** SpellShapeshiftForm.dbc
- **SQL Table:** spellshapeshiftform_dbc
- **Store:** `sSpellShapeshiftFormStore` (`DBCStorage<SpellShapeshiftFormEntry>`)
- **Format:** `SpellShapeshiftFormEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 19 | flags1 | uint32 | flags1 | - |
| 20 | creatureType | int32 | creatureType | - |
| 22 | attackSpeed | uint32 | attackSpeed | - |
| 23 | modelID_A | uint32 | modelID_A | Alliance |
| 24 | modelID_H | uint32 | modelID_H | Horde |
| 27-34 | stanceSpell | uint32 | stanceSpell[0..7] | - |

## SpellVisualEntry

- **DBC File:** SpellVisual.dbc
- **SQL Table:** spellvisual_dbc
- **Store:** `sSpellVisualStore` (`DBCStorage<SpellVisualEntry>`)
- **Format:** `SpellVisualfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | HasMissile | uint32 | HasMissile | - |
| - | MissileModel | int32 | MissileModel | - |

## StableSlotPricesEntry

- **DBC File:** StableSlotPrices.dbc
- **SQL Table:** stableslotprices_dbc
- **Store:** `sStableSlotPricesStore` (`DBCStorage<StableSlotPricesEntry>`)
- **Format:** `StableSlotPricesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | Slot | uint32 | Slot | - |
| - | Price | uint32 | Price | - |

## SummonPropertiesEntry

- **DBC File:** SummonProperties.dbc
- **SQL Table:** summonproperties_dbc
- **Store:** `sSummonPropertiesStore` (`DBCStorage<SummonPropertiesEntry>`)
- **Format:** `SummonPropertiesfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | Category | uint32 | Category | - |
| 2 | Faction | uint32 | Faction | - |
| 3 | Type | uint32 | Type | - |
| 4 | Slot | uint32 | Slot | - |
| 5 | Flags | uint32 | Flags | - |

## TalentEntry

- **DBC File:** Talent.dbc
- **SQL Table:** talent_dbc
- **Store:** `sTalentStore` (`DBCStorage<TalentEntry>`)
- **Format:** `TalentEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | TalentID | uint32 | TalentID | Primary key |
| 1 | TalentTab | uint32 | TalentTab | - |
| 2 | Row | uint32 | Row | - |
| 3 | Col | uint32 | Col | - |
| 4-8 | RankID | std::array<uint32,5> | RankID[0..4] | - |
| 13 | DependsOn | uint32 | DependsOn | - |
| 16 | DependsOnRank | uint32 | DependsOnRank | - |
| 19 | addToSpellBook | uint32 | addToSpellBook | - |

## TalentTabEntry

- **DBC File:** TalentTab.dbc
- **SQL Table:** talenttab_dbc
- **Store:** `sTalentTabStore` (`DBCStorage<TalentTabEntry>`)
- **Format:** `TalentTabEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | TalentTabID | uint32 | TalentTabID | Primary key |
| 20 | ClassMask | uint32 | ClassMask | - |
| 21 | petTalentMask | uint32 | petTalentMask | - |
| 22 | tabpage | uint32 | tabpage | - |

## TaxiNodesEntry

- **DBC File:** TaxiNodes.dbc
- **SQL Table:** taxinodes_dbc
- **Store:** `sTaxiNodesStore` (`DBCStorage<TaxiNodesEntry>`)
- **Format:** `TaxiNodesEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | map_id | uint32 | map_id | - |
| 2 | x | float | x | - |
| 3 | y | float | y | - |
| 4 | z | float | z | - |
| 5-21 | name | std::array<char const*,16> | name[0..15] | Localized |
| 23-24 | MountCreatureID | uint32 | MountCreatureID[0..1] | - |

## TaxiPathEntry

- **DBC File:** TaxiPath.dbc
- **SQL Table:** taxipath_dbc
- **Store:** `sTaxiPathStore` (`DBCStorage<TaxiPathEntry>`)
- **Format:** `TaxiPathEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 1 | from | uint32 | from | - |
| 2 | to | uint32 | to | - |
| 3 | price | uint32 | price | - |

## TaxiPathNodeEntry

- **DBC File:** TaxiPathNode.dbc
- **SQL Table:** taxipathnode_dbc
- **Store:** `sTaxiPathNodeStore` (static)
- **Format:** `TaxiPathNodeEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | path | uint32 | path | - |
| 2 | index | uint32 | index | - |
| 3 | mapid | uint32 | mapid | - |
| 4 | x | float | x | - |
| 5 | y | float | y | - |
| 6 | z | float | z | - |
| 7 | actionFlag | uint32 | actionFlag | - |
| 8 | delay | uint32 | delay | - |

## TeamContributionPointsEntry

- **DBC File:** TeamContributionPoints.dbc
- **SQL Table:** teamcontributionpoints_dbc
- **Store:** `sTeamContributionPointsStore` (`DBCStorage<TeamContributionPointsEntry>`)
- **Format:** `TeamContributionPointsfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | value | float | value | - |

## TotemCategoryEntry

- **DBC File:** TotemCategory.dbc
- **SQL Table:** totemcategory_dbc
- **Store:** `sTotemCategoryStore` (`DBCStorage<TotemCategoryEntry>`)
- **Format:** `TotemCategoryEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 18 | categoryType | uint32 | categoryType | - |
| 19 | categoryMask | uint32 | categoryMask | - |

## TransportAnimationEntry

- **DBC File:** TransportAnimation.dbc
- **SQL Table:** transportanimation_dbc
- **Store:** `sTransportAnimationStore` (`DBCStorage<TransportAnimationEntry>`)
- **Format:** `TransportAnimationfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | TransportEntry | uint32 | TransportEntry | - |
| - | TimeSeg | uint32 | TimeSeg | - |
| - | X | float | X | - |
| - | Y | float | Y | - |
| - | Z | float | Z | - |

## TransportRotationEntry

- **DBC File:** TransportRotation.dbc
- **SQL Table:** transportrotation_dbc
- **Store:** `sTransportRotationStore` (`DBCStorage<TransportRotationEntry>`)
- **Format:** `TransportRotationfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| - | TransportEntry | uint32 | TransportEntry | - |
| - | TimeSeg | uint32 | TimeSeg | - |
| - | X | float | X | - |
| - | Y | float | Y | - |
| - | Z | float | Z | - |
| - | W | float | W | - |

## VehicleEntry

- **DBC File:** Vehicle.dbc
- **SQL Table:** vehicle_dbc
- **Store:** `sVehicleStore` (`DBCStorage<VehicleEntry>`)
- **Format:** `VehicleEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | m_ID | uint32 | m_ID | Primary key |
| 1 | m_flags | uint32 | m_flags | - |
| 2 | m_turnSpeed | float | m_turnSpeed | - |
| 3 | m_pitchSpeed | float | m_pitchSpeed | - |
| 6-13 | m_seatID | uint32 | m_seatID[0..7] | - |
| 18-28 | - | float | m_facingLimitRight/left, m_msslTrgt fields | - |
| 29 | m_msslTrgtArcTexture | char const* | m_msslTrgtArcTexture | - |
| 33 | m_cameraYawOffset | float | m_cameraYawOffset | - |
| 37 | m_powerDisplayId | uint32 | m_powerDisplayId | - |

## VehicleSeatEntry

- **DBC File:** VehicleSeat.dbc
- **SQL Table:** vehicleseat_dbc
- **Store:** `sVehicleSeatStore` (`DBCStorage<VehicleSeatEntry>`)
- **Format:** `VehicleSeatEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | m_ID | uint32 | m_ID | Primary key |
| 1 | m_flags | uint32 | m_flags | - |
| 2 | m_attachmentID | int32 | m_attachmentID | - |
| 3 | m_attachmentOffsetX | float | m_attachmentOffsetX | - |
| 4 | m_attachmentOffsetY | float | m_attachmentOffsetY | - |
| 5 | m_attachmentOffsetZ | float | m_attachmentOffsetZ | - |
| 45 | m_flagsB | uint32 | m_flagsB | - |

## WMOAreaTableEntry

- **DBC File:** WMOAreaTable.dbc
- **SQL Table:** wmoareatable_dbc
- **Store:** `sWMOAreaTableStore` (`DBCStorage<WMOAreaTableEntry>`)
- **Format:** `WMOAreaTableEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | Id | uint32 | Id | Primary key |
| 1 | rootId | int32 | rootId | - |
| 2 | adtId | int32 | adtId | - |
| 3 | groupId | int32 | groupId | - |
| 9 | Flags | uint32 | Flags | - |
| 10 | areaId | uint32 | areaId | - |

## WorldMapAreaEntry

- **DBC File:** WorldMapArea.dbc
- **SQL Table:** worldmaparea_dbc
- **Store:** `sWorldMapAreaStore` (`DBCStorage<WorldMapAreaEntry>`)
- **Format:** `WorldMapAreaEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 1 | map_id | uint32 | map_id | - |
| 2 | area_id | uint32 | area_id | - |
| 4 | y1 | float | y1 | - |
| 5 | y2 | float | y2 | - |
| 6 | x1 | float | x1 | - |
| 7 | x2 | float | x2 | - |
| 8 | virtual_map_id | int32 | virtual_map_id | - |

## WorldMapOverlayEntry

- **DBC File:** WorldMapOverlay.dbc
- **SQL Table:** worldmapoverlay_dbc
- **Store:** `sWorldMapOverlayStore` (`DBCStorage<WorldMapOverlayEntry>`)
- **Format:** `WorldMapOverlayEntryfmt`

| DBC Col | SQL Column | C++ Type | Field Name | Notes |
|---------|-----------|----------|------------|-------|
| 0 | ID | uint32 | ID | Primary key |
| 2-5 | areatableID | uint32 | areatableID[0..3] | - |
