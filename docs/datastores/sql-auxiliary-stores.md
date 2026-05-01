# SQL Auxiliary Stores

Auto-discovered SQL tables not in the static AzerothCore datastore registry. These tables are queried directly by various managers and systems. For architecture details, see [README.md](README.md).

## Table of Contents
- [acore_world](#acore-world)
- [acore_characters](#acore-characters)
- [acore_auth](#acore-auth)
- [acore_playerbots](#acore-playerbots)

## acore_world (35 tables)

### AntidosOpcodePolicies

- **SQL Table:** antidos_opcode_policies
- **Database:** acore_world

| Column | Type |
|--------|------|
| Opcode | int32 |
| Policy | int8 |
| MaxAllowedCount | int32 |

### ArenaSeasonReward

- **SQL Table:** arena_season_reward
- **Database:** acore_world

| Column | Type |
|--------|------|
| group_id | int32 |
| type | enum |
| entry | int32 |

### ArenaSeasonRewardGroup

- **SQL Table:** arena_season_reward_group
- **Database:** acore_world

| Column | Type |
|--------|------|
| id | int32 |
| arena_season | int8 |
| criteria_type | enum |
| min_criteria | float |
| max_criteria | float |
| reward_mail_template_id | int32 |
| reward_mail_subject | string |
| reward_mail_body | string |
| gold_reward | int32 |

### BroadcastTextLocale

- **SQL Table:** broadcast_text_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| MaleText | string |
| FemaleText | string |
| VerifiedBuild | int32 |

### CreatureLootTemplate

- **SQL Table:** creature_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### CreatureTemplateLocale

- **SQL Table:** creature_template_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| entry | int32 |
| locale | string |
| Name | string |
| Title | string |
| VerifiedBuild | int32 |

### DisenchantLootTemplate

- **SQL Table:** disenchant_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### FishingLootTemplate

- **SQL Table:** fishing_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### GameobjectLootTemplate

- **SQL Table:** gameobject_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### GameobjectTemplateLocale

- **SQL Table:** gameobject_template_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| entry | int32 |
| locale | string |
| name | string |
| castBarCaption | string |
| VerifiedBuild | int32 |

### GossipMenuOptionLocale

- **SQL Table:** gossip_menu_option_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| MenuID | int32 |
| OptionID | int32 |
| Locale | string |
| OptionText | string |
| BoxText | string |

### HolidayDates

- **SQL Table:** holiday_dates
- **Database:** acore_world

| Column | Type |
|--------|------|
| id | int32 |
| date_id | int8 |
| date_value | int32 |
| holiday_duration | int32 |

### ItemLootTemplate

- **SQL Table:** item_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### ItemSetNamesLocale

- **SQL Table:** item_set_names_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| Name | string |
| VerifiedBuild | int32 |

### ItemTemplateLocale

- **SQL Table:** item_template_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| Name | string |
| Description | string |
| VerifiedBuild | int32 |

### MailLootTemplate

- **SQL Table:** mail_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### MillingLootTemplate

- **SQL Table:** milling_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### ModuleStringLocale

- **SQL Table:** module_string_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| module | string |
| id | int32 |
| locale | enum |
| string | string |

### NpcTextLocale

- **SQL Table:** npc_text_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| Locale | string |
| Text0_0 | longtext |
| Text0_1 | longtext |
| Text1_0 | longtext |
| Text1_1 | longtext |
| Text2_0 | longtext |
| Text2_1 | longtext |
| Text3_0 | longtext |
| Text3_1 | longtext |
| Text4_0 | longtext |
| Text4_1 | longtext |
| Text5_0 | longtext |
| Text5_1 | longtext |
| Text6_0 | longtext |
| Text6_1 | longtext |
| Text7_0 | longtext |
| Text7_1 | longtext |

### NpcTrainer

- **SQL Table:** npc_trainer
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| SpellID | int32 |
| MoneyCost | int32 |
| ReqSkillLine | int32 |
| ReqSkillRank | int32 |
| ReqLevel | int8 |
| ReqSpell | int32 |

### PageTextLocale

- **SQL Table:** page_text_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| Text | string |
| VerifiedBuild | int32 |

### PetNameGenerationLocale

- **SQL Table:** pet_name_generation_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| Locale | string |
| Word | tinytext |
| Entry | int32 |
| Half | int8 |

### PickpocketingLootTemplate

- **SQL Table:** pickpocketing_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### PlayerbotsRpgRaces

- **SQL Table:** playerbots_rpg_races
- **Database:** acore_world

| Column | Type |
|--------|------|
| id | int32 |
| entry | int32 |
| race | int32 |
| minl | int32 |
| maxl | int32 |

### PlayerLootTemplate

- **SQL Table:** player_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### PointsOfInterestLocale

- **SQL Table:** points_of_interest_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| Name | string |
| VerifiedBuild | int32 |

### ProspectingLootTemplate

- **SQL Table:** prospecting_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### QuestGreetingLocale

- **SQL Table:** quest_greeting_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| type | int8 |
| locale | string |
| Greeting | string |
| VerifiedBuild | int32 |

### QuestOfferRewardLocale

- **SQL Table:** quest_offer_reward_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| RewardText | string |
| VerifiedBuild | int32 |

### QuestRequestItemsLocale

- **SQL Table:** quest_request_items_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| CompletionText | string |
| VerifiedBuild | int32 |

### QuestTemplateLocale

- **SQL Table:** quest_template_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| ID | int32 |
| locale | string |
| Title | string |
| Details | string |
| Objectives | string |
| EndText | string |
| CompletedText | string |
| ObjectiveText1 | string |
| ObjectiveText2 | string |
| ObjectiveText3 | string |
| ObjectiveText4 | string |
| VerifiedBuild | int32 |

### ReferenceLootTemplate

- **SQL Table:** reference_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### SkinningLootTemplate

- **SQL Table:** skinning_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### SpellLootTemplate

- **SQL Table:** spell_loot_template
- **Database:** acore_world

| Column | Type |
|--------|------|
| Entry | int32 |
| Item | int32 |
| Reference | int32 |
| Chance | float |
| QuestRequired | int8 |
| LootMode | int32 |
| GroupId | int8 |
| MinCount | int8 |
| MaxCount | int8 |
| Comment | string |

### TrainerLocale

- **SQL Table:** trainer_locale
- **Database:** acore_world

| Column | Type |
|--------|------|
| Id | int32 |
| locale | string |
| Greeting_lang | mediumtext |
| VerifiedBuild | int32 |

## acore_characters (93 tables)

### AccountData

- **SQL Table:** account_data
- **Database:** acore_characters

| Column | Type |
|--------|------|
| accountId | int32 |
| type | int8 |
| time | int32 |
| data | binary |

### AccountInstanceTimes

- **SQL Table:** account_instance_times
- **Database:** acore_characters

| Column | Type |
|--------|------|
| accountId | int32 |
| instanceId | int32 |
| releaseTime | int64 |

### AccountTutorial

- **SQL Table:** account_tutorial
- **Database:** acore_characters

| Column | Type |
|--------|------|
| accountId | int32 |
| tut0 | int32 |
| tut1 | int32 |
| tut2 | int32 |
| tut3 | int32 |
| tut4 | int32 |
| tut5 | int32 |
| tut6 | int32 |
| tut7 | int32 |

### ActiveArenaSeason

- **SQL Table:** active_arena_season
- **Database:** acore_characters

| Column | Type |
|--------|------|
| season_id | int8 |
| season_state | int8 |

### BattlegroundDeserters

- **SQL Table:** battleground_deserters
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| type | int8 |
| datetime | timestamp |

### Bugreport

- **SQL Table:** bugreport
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| type | longtext |
| content | longtext |
| State | int8 |
| Assignee | string |
| Comment | longtext |

### Channels

- **SQL Table:** channels
- **Database:** acore_characters

| Column | Type |
|--------|------|
| channelId | int32 |
| name | string |
| team | int32 |
| announce | int8 |
| ownership | int8 |
| password | string |
| lastUsed | int32 |

### ChannelsBans

- **SQL Table:** channels_bans
- **Database:** acore_characters

| Column | Type |
|--------|------|
| channelId | int32 |
| playerGUID | int32 |
| banTime | int32 |

### ChannelsRights

- **SQL Table:** channels_rights
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name | string |
| flags | int32 |
| speakdelay | int32 |
| joinmessage | string |
| delaymessage | string |
| moderators | string |

### CharacterAccountData

- **SQL Table:** character_account_data
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| type | int8 |
| time | int32 |
| data | binary |

### CharacterAchievement

- **SQL Table:** character_achievement
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| achievement | int32 |
| date | int32 |

### CharacterAchievementOfflineUpdates

- **SQL Table:** character_achievement_offline_updates
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| update_type | int8 |
| arg1 | int32 |
| arg2 | int32 |
| arg3 | int32 |

### CharacterAchievementProgress

- **SQL Table:** character_achievement_progress
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| criteria | int32 |
| counter | int32 |
| date | int32 |

### CharacterAction

- **SQL Table:** character_action
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spec | int8 |
| button | int8 |
| action | int32 |
| type | int8 |

### CharacterArenaStats

- **SQL Table:** character_arena_stats
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| slot | int8 |
| matchMakerRating | int32 |
| maxMMR | int32 |

### CharacterAura

- **SQL Table:** character_aura
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| casterGuid | int64 |
| itemGuid | int64 |
| spell | int32 |
| effectMask | int8 |
| recalculateMask | int8 |
| stackCount | int8 |
| amount0 | int32 |
| amount1 | int32 |
| amount2 | int32 |
| base_amount0 | int32 |
| base_amount1 | int32 |
| base_amount2 | int32 |
| maxDuration | int32 |
| remainTime | int32 |
| remainCharges | int8 |

### CharacterBanned

- **SQL Table:** character_banned
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| bandate | int32 |
| unbandate | int32 |
| bannedby | string |
| banreason | string |
| active | int8 |

### CharacterBattlegroundRandom

- **SQL Table:** character_battleground_random
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |

### CharacterBrewOfTheMonth

- **SQL Table:** character_brew_of_the_month
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| lastEventId | int32 |

### CharacterDeclinedname

- **SQL Table:** character_declinedname
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| genitive | string |
| dative | string |
| accusative | string |
| instrumental | string |
| prepositional | string |

### CharacterEntryPoint

- **SQL Table:** character_entry_point
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| joinX | float |
| joinY | float |
| joinZ | float |
| joinO | float |
| joinMapId | int32 |
| taxiPath0 | int32 |
| taxiPath1 | int32 |
| mountSpell | int32 |

### CharacterEquipmentsets

- **SQL Table:** character_equipmentsets
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| setguid | int64 |
| setindex | int8 |
| name | string |
| iconname | string |
| ignore_mask | int32 |
| item0 | int32 |
| item1 | int32 |
| item2 | int32 |
| item3 | int32 |
| item4 | int32 |
| item5 | int32 |
| item6 | int32 |
| item7 | int32 |
| item8 | int32 |
| item9 | int32 |
| item10 | int32 |
| item11 | int32 |
| item12 | int32 |
| item13 | int32 |
| item14 | int32 |
| item15 | int32 |
| item16 | int32 |
| item17 | int32 |
| item18 | int32 |

### CharacterGifts

- **SQL Table:** character_gifts
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| item_guid | int32 |
| entry | int32 |
| flags | int32 |

### CharacterGlyphs

- **SQL Table:** character_glyphs
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| talentGroup | int8 |
| glyph1 | int32 |
| glyph2 | int32 |
| glyph3 | int32 |
| glyph4 | int32 |
| glyph5 | int32 |
| glyph6 | int32 |

### CharacterHomebind

- **SQL Table:** character_homebind
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| mapId | int32 |
| zoneId | int32 |
| posX | float |
| posY | float |
| posZ | float |

### CharacterInventory

- **SQL Table:** character_inventory
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| bag | int32 |
| slot | int8 |
| item | int32 |

### CharacterPet

- **SQL Table:** character_pet
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| entry | int32 |
| owner | int32 |
| modelid | int32 |
| CreatedBySpell | int32 |
| PetType | int8 |
| level | int32 |
| exp | int32 |
| Reactstate | int8 |
| name | string |
| renamed | int8 |
| slot | int8 |
| curhealth | int32 |
| curmana | int32 |
| curhappiness | int32 |
| savetime | int32 |
| abdata | string |

### CharacterPetDeclinedname

- **SQL Table:** character_pet_declinedname
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| owner | int32 |
| genitive | string |
| dative | string |
| accusative | string |
| instrumental | string |
| prepositional | string |

### CharacterQueststatus

- **SQL Table:** character_queststatus
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |
| status | int8 |
| explored | int8 |
| timer | int32 |
| mobcount1 | int32 |
| mobcount2 | int32 |
| mobcount3 | int32 |
| mobcount4 | int32 |
| itemcount1 | int32 |
| itemcount2 | int32 |
| itemcount3 | int32 |
| itemcount4 | int32 |
| itemcount5 | int32 |
| itemcount6 | int32 |
| playercount | int32 |

### CharacterQueststatusDaily

- **SQL Table:** character_queststatus_daily
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |
| time | int32 |

### CharacterQueststatusMonthly

- **SQL Table:** character_queststatus_monthly
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |

### CharacterQueststatusRewarded

- **SQL Table:** character_queststatus_rewarded
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |
| active | int8 |

### CharacterQueststatusSeasonal

- **SQL Table:** character_queststatus_seasonal
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |
| event | int32 |

### CharacterQueststatusWeekly

- **SQL Table:** character_queststatus_weekly
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| quest | int32 |

### CharacterReputation

- **SQL Table:** character_reputation
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| faction | int32 |
| standing | int32 |
| flags | int32 |

### Characters

- **SQL Table:** characters
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| account | int32 |
| name | string |
| race | int8 |
| class | int8 |
| gender | int8 |
| level | int8 |
| xp | int32 |
| money | int32 |
| skin | int8 |
| face | int8 |
| hairStyle | int8 |
| hairColor | int8 |
| facialStyle | int8 |
| bankSlots | int8 |
| restState | int8 |
| playerFlags | int32 |
| position_x | float |
| position_y | float |
| position_z | float |
| map | int32 |
| instance_id | int32 |
| instance_mode_mask | int8 |
| orientation | float |
| taximask | string |
| online | int8 |
| cinematic | int8 |
| totaltime | int32 |
| leveltime | int32 |
| logout_time | int32 |
| is_logout_resting | int8 |
| rest_bonus | float |
| resettalents_cost | int32 |
| resettalents_time | int32 |
| trans_x | float |
| trans_y | float |
| trans_z | float |
| trans_o | float |
| transguid | int32 |
| extra_flags | int32 |
| stable_slots | int8 |
| at_login | int32 |
| zone | int32 |
| death_expire_time | int32 |
| taxi_path | string |
| arenaPoints | int32 |
| totalHonorPoints | int32 |
| todayHonorPoints | int32 |
| yesterdayHonorPoints | int32 |
| totalKills | int32 |
| todayKills | int32 |
| yesterdayKills | int32 |
| chosenTitle | int32 |
| knownCurrencies | int64 |
| watchedFaction | int32 |
| drunk | int8 |
| health | int32 |
| power1 | int32 |
| power2 | int32 |
| power3 | int32 |
| power4 | int32 |
| power5 | int32 |
| power6 | int32 |
| power7 | int32 |
| latency | int32 |
| talentGroupsCount | int8 |
| activeTalentGroup | int8 |
| exploredZones | longtext |
| equipmentCache | longtext |
| ammoId | int32 |
| knownTitles | longtext |
| actionBars | int8 |
| grantableLevels | int8 |
| order | int8 |
| creation_date | timestamp |
| deleteInfos_Account | int32 |
| deleteInfos_Name | string |
| deleteDate | int32 |
| innTriggerId | int32 |
| extraBonusTalentCount | int32 |

### CharacterSettings

- **SQL Table:** character_settings
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| source | string |
| data | string |

### CharacterSkills

- **SQL Table:** character_skills
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| skill | int32 |
| value | int32 |
| max | int32 |

### CharacterSocial

- **SQL Table:** character_social
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| friend | int32 |
| flags | int8 |
| note | string |

### CharacterSpell

- **SQL Table:** character_spell
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spell | int32 |
| specMask | int8 |

### CharacterSpellCooldown

- **SQL Table:** character_spell_cooldown
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spell | int32 |
| category | int32 |
| item | int32 |
| time | int32 |
| needSend | int8 |

### CharacterStats

- **SQL Table:** character_stats
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| maxhealth | int32 |
| maxpower1 | int32 |
| maxpower2 | int32 |
| maxpower3 | int32 |
| maxpower4 | int32 |
| maxpower5 | int32 |
| maxpower6 | int32 |
| maxpower7 | int32 |
| strength | int32 |
| agility | int32 |
| stamina | int32 |
| intellect | int32 |
| spirit | int32 |
| armor | int32 |
| resHoly | int32 |
| resFire | int32 |
| resNature | int32 |
| resFrost | int32 |
| resShadow | int32 |
| resArcane | int32 |
| blockPct | float |
| dodgePct | float |
| parryPct | float |
| critPct | float |
| rangedCritPct | float |
| spellCritPct | float |
| attackPower | int32 |
| rangedAttackPower | int32 |
| spellPower | int32 |
| resilience | int32 |

### CharacterTalent

- **SQL Table:** character_talent
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spell | int32 |
| specMask | int8 |

### Corpse

- **SQL Table:** corpse
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| posX | float |
| posY | float |
| posZ | float |
| orientation | float |
| mapId | int32 |
| phaseMask | int32 |
| displayId | int32 |
| itemCache | string |
| bytes1 | int32 |
| bytes2 | int32 |
| guildId | int32 |
| flags | int8 |
| dynFlags | int8 |
| time | int32 |
| corpseType | int8 |
| instanceId | int32 |

### CreatureRespawn

- **SQL Table:** creature_respawn
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| respawnTime | int32 |
| mapId | int32 |
| instanceId | int32 |

### GameEventConditionSave

- **SQL Table:** game_event_condition_save
- **Database:** acore_characters

| Column | Type |
|--------|------|
| eventEntry | int8 |
| condition_id | int32 |
| done | float |

### GameEventSave

- **SQL Table:** game_event_save
- **Database:** acore_characters

| Column | Type |
|--------|------|
| eventEntry | int8 |
| state | int8 |
| next_start | int32 |

### GameobjectRespawn

- **SQL Table:** gameobject_respawn
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| respawnTime | int32 |
| mapId | int32 |
| instanceId | int32 |

### gm_survey

- **SQL Table:** gm_survey
- **Database:** acore_characters

| Column | Type |
|--------|------|
| surveyId | uint32 |
| guid | uint32 |
| mainSurvey | uint32 |
| comment | std::string |
| createTime | uint32 |
| maxMMR | int16 |

### GmSubsurvey

- **SQL Table:** gm_subsurvey
- **Database:** acore_characters

| Column | Type |
|--------|------|
| surveyId | int32 |
| questionId | int32 |
| answer | int32 |
| answerComment | string |

### GmSurvey

- **SQL Table:** gm_survey
- **Database:** acore_characters

| Column | Type |
|--------|------|
| surveyId | int32 |
| guid | int32 |
| mainSurvey | int32 |
| comment | longtext |
| createTime | int32 |
| maxMMR | int32 |

### GuildBankEventlog

- **SQL Table:** guild_bank_eventlog
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| LogGuid | int32 |
| TabId | int8 |
| EventType | int8 |
| PlayerGuid | int32 |
| ItemOrMoney | int32 |
| ItemStackCount | int32 |
| DestTabId | int8 |
| TimeStamp | int32 |

### GuildBankItem

- **SQL Table:** guild_bank_item
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| TabId | int8 |
| SlotId | int8 |
| item_guid | int32 |

### GuildBankRight

- **SQL Table:** guild_bank_right
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| TabId | int8 |
| rid | int8 |
| gbright | int8 |
| SlotPerDay | int32 |

### GuildBankTab

- **SQL Table:** guild_bank_tab
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| TabId | int8 |
| TabName | string |
| TabIcon | string |
| TabText | string |

### GuildEventlog

- **SQL Table:** guild_eventlog
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| LogGuid | int32 |
| EventType | int8 |
| PlayerGuid1 | int32 |
| PlayerGuid2 | int32 |
| NewRank | int8 |
| TimeStamp | int32 |

### GuildMember

- **SQL Table:** guild_member
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| guid | int32 |
| rank | int8 |
| pnote | string |
| offnote | string |

### GuildMemberWithdraw

- **SQL Table:** guild_member_withdraw
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| tab0 | int32 |
| tab1 | int32 |
| tab2 | int32 |
| tab3 | int32 |
| tab4 | int32 |
| tab5 | int32 |
| money | int32 |

### GuildRank

- **SQL Table:** guild_rank
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guildid | int32 |
| rid | int8 |
| rname | string |
| rights | int32 |
| BankMoneyPerDay | int32 |

### InstanceSavedGoStateData

- **SQL Table:** instance_saved_go_state_data
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| guid | int32 |
| state | int8 |

### ItemInstance

- **SQL Table:** item_instance
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| itemEntry | int32 |
| owner_guid | int32 |
| creatorGuid | int32 |
| giftCreatorGuid | int32 |
| count | int32 |
| duration | int32 |
| charges | tinytext |
| flags | int32 |
| enchantments | string |
| randomPropertyId | int32 |
| durability | int32 |
| playedTime | int32 |
| text | string |

### ItemLootStorage

- **SQL Table:** item_loot_storage
- **Database:** acore_characters

| Column | Type |
|--------|------|
| containerGUID | int32 |
| itemid | int32 |
| count | int32 |
| item_index | int32 |
| randomPropertyId | int32 |
| randomSuffix | int32 |
| follow_loot_rules | int8 |
| freeforall | int8 |
| is_blocked | int8 |
| is_counted | int8 |
| is_underthreshold | int8 |
| needs_quest | int8 |
| conditionLootId | int32 |

### ItemRefundInstance

- **SQL Table:** item_refund_instance
- **Database:** acore_characters

| Column | Type |
|--------|------|
| item_guid | int32 |
| player_guid | int32 |
| paidMoney | int32 |
| paidExtendedCost | int32 |

### ItemSoulboundTradeData

- **SQL Table:** item_soulbound_trade_data
- **Database:** acore_characters

| Column | Type |
|--------|------|
| itemGuid | int32 |
| allowedPlayers | string |

### LagReports

- **SQL Table:** lag_reports
- **Database:** acore_characters

| Column | Type |
|--------|------|
| reportId | int32 |
| guid | int32 |
| lagType | int8 |
| mapId | int32 |
| posX | float |
| posY | float |
| posZ | float |
| latency | int32 |
| createTime | int32 |

### LogArenaFights

- **SQL Table:** log_arena_fights
- **Database:** acore_characters

| Column | Type |
|--------|------|
| fight_id | int32 |
| time | timestamp |
| type | int8 |
| duration | int32 |
| winner | int32 |
| loser | int32 |
| winner_tr | int32 |
| winner_mmr | int32 |
| winner_tr_change | int32 |
| loser_tr | int32 |
| loser_mmr | int32 |
| loser_tr_change | int32 |
| currOnline | int32 |

### LogArenaMemberstats

- **SQL Table:** log_arena_memberstats
- **Database:** acore_characters

| Column | Type |
|--------|------|
| fight_id | int32 |
| member_id | int8 |
| name | string |
| guid | int32 |
| team | int32 |
| account | int32 |
| ip | string |
| damage | int32 |
| heal | int32 |
| kblows | int32 |

### LogEncounter

- **SQL Table:** log_encounter
- **Database:** acore_characters

| Column | Type |
|--------|------|
| time | timestamp |
| map | int32 |
| difficulty | int8 |
| creditType | int8 |
| creditEntry | int32 |
| playersInfo | string |

### LogMoney

- **SQL Table:** log_money
- **Database:** acore_characters

| Column | Type |
|--------|------|
| sender_acc | int32 |
| sender_guid | int32 |
| sender_name | string |
| sender_ip | string |
| receiver_acc | int32 |
| receiver_name | string |
| money | int64 |
| topic | string |
| date | timestamp |
| type | int8 |

### Mail

- **SQL Table:** mail
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| messageType | int8 |
| stationery | int8 |
| mailTemplateId | int32 |
| sender | int32 |
| receiver | int32 |
| subject | longtext |
| body | longtext |
| has_items | int8 |
| expire_time | int32 |
| deliver_time | int32 |
| money | int32 |
| cod | int32 |
| checked | int8 |

### MailItems

- **SQL Table:** mail_items
- **Database:** acore_characters

| Column | Type |
|--------|------|
| mail_id | int32 |
| item_guid | int32 |
| receiver | int32 |

### MailServerCharacter

- **SQL Table:** mail_server_character
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| mailId | int32 |

### MailServerTemplate

- **SQL Table:** mail_server_template
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| moneyA | int32 |
| moneyH | int32 |
| subject | string |
| body | string |
| active | int8 |

### MailServerTemplateConditions

- **SQL Table:** mail_server_template_conditions
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| templateID | int32 |
| conditionType | enum |
| conditionValue | int32 |
| conditionState | int32 |

### MailServerTemplateItems

- **SQL Table:** mail_server_template_items
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| templateID | int32 |
| faction | enum |
| item | int32 |
| itemCount | int32 |

### PetAura

- **SQL Table:** spell_pet_auras
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| casterGuid | int64 |
| spell | int32 |
| effectMask | int8 |
| recalculateMask | int8 |
| stackCount | int8 |
| amount0 | int32 |
| amount1 | int32 |
| amount2 | int32 |
| base_amount0 | int32 |
| base_amount1 | int32 |
| base_amount2 | int32 |
| maxDuration | int32 |
| remainTime | int32 |
| remainCharges | int8 |

### PetAuraCharacter

- **SQL Table:** pet_aura
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | uint32 |
| casterGuid | uint64 |
| spell | uint32 |
| effectMask | uint8 |
| recalculateMask | uint8 |
| stackCount | uint8 |
| amount0 | int32 |
| amount1 | int32 |
| amount2 | int32 |

### PetEntry

- **SQL Table:** character_pet
- **Database:** acore_characters

*No field data available.*

### PetSpell

- **SQL Table:** pet_spell
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spell | int32 |
| active | int8 |

### PetSpellCooldown

- **SQL Table:** pet_spell_cooldown
- **Database:** acore_characters

| Column | Type |
|--------|------|
| guid | int32 |
| spell | int32 |
| category | int32 |
| time | int32 |

### PlayerbotsArenaTeamNames

- **SQL Table:** playerbots_arena_team_names
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name_id | int32 |
| name | string |
| type | int8 |

### PlayerbotsGuildNames

- **SQL Table:** playerbots_guild_names
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name_id | int32 |
| name | string |

### PlayerbotsNames

- **SQL Table:** playerbots_names
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name_id | int32 |
| name | string |
| gender | int8 |

### PoolQuestSave

- **SQL Table:** pool_quest_save
- **Database:** acore_characters

| Column | Type |
|--------|------|
| pool_id | int32 |
| quest_id | int32 |

### ProfanityName

- **SQL Table:** profanity_name
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name | string |

### PvpstatsBattlegrounds

- **SQL Table:** pvpstats_battlegrounds
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int64 |
| winner_faction | int8 |
| bracket_id | int8 |
| type | int8 |
| date | timestamp |

### PvpstatsPlayers

- **SQL Table:** pvpstats_players
- **Database:** acore_characters

| Column | Type |
|--------|------|
| battleground_id | int64 |
| character_guid | int32 |
| winner | bit |
| score_killing_blows | int32 |
| score_deaths | int32 |
| score_honorable_kills | int32 |
| score_bonus_honor | int32 |
| score_damage_done | int32 |
| score_healing_done | int32 |
| attr_1 | int32 |
| attr_2 | int32 |
| attr_3 | int32 |
| attr_4 | int32 |
| attr_5 | int32 |

### QuestTracker

- **SQL Table:** quest_tracker
- **Database:** acore_characters

| Column | Type |
|--------|------|
| id | int32 |
| character_guid | int32 |
| quest_accept_time | timestamp |
| quest_complete_time | timestamp |
| quest_abandon_time | timestamp |
| completed_by_gm | int8 |
| core_hash | string |
| core_revision | string |

### RecoveryItem

- **SQL Table:** recovery_item
- **Database:** acore_characters

| Column | Type |
|--------|------|
| Id | int32 |
| Guid | int32 |
| ItemEntry | int32 |
| Count | int32 |
| DeleteDate | int32 |

### ReservedName

- **SQL Table:** reserved_name
- **Database:** acore_characters

| Column | Type |
|--------|------|
| name | string |

### SpamReports

- **SQL Table:** spam_reports
- **Database:** acore_characters

| Column | Type |
|--------|------|
| ID | int32 |
| SpamType | int8 |
| SpammerGuid | int32 |
| Unk1 | int32 |
| MailIdOrMessageType | int32 |
| ChannelId | int32 |
| SecondsSinceMessage | int32 |
| Description | longtext |
| Time | int32 |

### WorldState

- **SQL Table:** world_state
- **Database:** acore_characters

| Column | Type |
|--------|------|
| Id | int32 |
| Data | longtext |

### Worldstates

- **SQL Table:** worldstates
- **Database:** acore_characters

| Column | Type |
|--------|------|
| entry | int32 |
| value | int32 |
| comment | tinytext |

## acore_auth (16 tables)

### Account

- **SQL Table:** account
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| username | string |
| salt | binary |
| verifier | binary |
| session_key | binary |
| totp_secret | varbinary |
| email | string |
| reg_mail | string |
| joindate | timestamp |
| last_ip | string |
| last_attempt_ip | string |
| failed_logins | int32 |
| locked | int8 |
| lock_country | string |
| last_login | timestamp |
| online | int32 |
| expansion | int8 |
| Flags | int32 |
| mutetime | int64 |
| mutereason | string |
| muteby | string |
| locale | int8 |
| os | string |
| recruiter | int32 |
| totaltime | int32 |

### AccountAccess

- **SQL Table:** account_access
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| gmlevel | int8 |
| RealmID | int32 |
| comment | string |

### AccountBanned

- **SQL Table:** account_banned
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| bandate | int32 |
| unbandate | int32 |
| bannedby | string |
| banreason | string |
| active | int8 |

### AccountMuted

- **SQL Table:** account_muted
- **Database:** acore_auth

| Column | Type |
|--------|------|
| guid | int32 |
| mutedate | int32 |
| mutetime | int32 |
| mutedby | string |
| mutereason | string |

### Autobroadcast

- **SQL Table:** autobroadcast
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| id | int8 |
| weight | int8 |
| text | longtext |

### AutobroadcastLocale

- **SQL Table:** autobroadcast_locale
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| id | int32 |
| locale | string |
| text | longtext |

### BuildInfo

- **SQL Table:** build_info
- **Database:** acore_auth

| Column | Type |
|--------|------|
| build | int32 |
| majorVersion | int32 |
| minorVersion | int32 |
| bugfixVersion | int32 |
| hotfixVersion | string |
| winAuthSeed | string |
| win64AuthSeed | string |
| mac64AuthSeed | string |
| winChecksumSeed | string |
| macChecksumSeed | string |

### IpBanned

- **SQL Table:** ip_banned
- **Database:** acore_auth

| Column | Type |
|--------|------|
| ip | string |
| bandate | int32 |
| unbandate | int32 |
| bannedby | string |
| banreason | string |

### Logs

- **SQL Table:** logs
- **Database:** acore_auth

| Column | Type |
|--------|------|
| time | int32 |
| realm | int32 |
| type | string |
| level | int8 |
| string | string |

### LogsIpActions

- **SQL Table:** logs_ip_actions
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| account_id | int32 |
| character_guid | int32 |
| type | int8 |
| ip | string |
| systemnote | string |
| unixtime | int32 |
| time | timestamp |
| comment | string |

### Motd

- **SQL Table:** motd
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| text | longtext |

### MotdLocalized

- **SQL Table:** motd_localized
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| locale | string |
| text | longtext |

### Realmcharacters

- **SQL Table:** realmcharacters
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| acctid | int32 |
| numchars | int8 |

### Realmlist

- **SQL Table:** realmlist
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| address | string |
| localAddress | string |
| localSubnetMask | string |
| port | int32 |
| icon | int8 |
| flag | int8 |
| timezone | int8 |
| allowedSecurityLevel | int8 |
| population | float |
| gamebuild | int32 |

### SecretDigest

- **SQL Table:** secret_digest
- **Database:** acore_auth

| Column | Type |
|--------|------|
| id | int32 |
| digest | string |

### Uptime

- **SQL Table:** uptime
- **Database:** acore_auth

| Column | Type |
|--------|------|
| realmid | int32 |
| starttime | int32 |
| uptime | int32 |
| maxplayers | int32 |
| revision | string |

## acore_playerbots (27 tables)

### AiPlayerbotTexts

- **SQL Table:** ai_playerbot_texts
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| text | string |
| say_type | int8 |
| reply_type | int8 |
| text_loc1 | string |
| text_loc2 | string |
| text_loc3 | string |
| text_loc4 | string |
| text_loc5 | string |
| text_loc6 | string |
| text_loc7 | string |
| text_loc8 | string |

### AiPlayerbotTextsChance

- **SQL Table:** ai_playerbot_texts_chance
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int64 |
| name | string |
| probability | int64 |

### PlayerbotsAccountKeys

- **SQL Table:** playerbots_account_keys
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| account_id | int32 |
| security_key | string |
| created_at | timestamp |

### PlayerbotsAccountLinks

- **SQL Table:** playerbots_account_links
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| account_id | int32 |
| linked_account_id | int32 |
| created_at | timestamp |

### PlayerbotsAccountType

- **SQL Table:** playerbots_account_type
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| account_id | int32 |
| account_type | int8 |
| assignment_date | timestamp |

### PlayerbotsCustomStrategy

- **SQL Table:** playerbots_custom_strategy
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| idx | int32 |
| owner | int32 |
| action_line | string |

### PlayerbotsDbStore

- **SQL Table:** playerbots_db_store
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| guid | int32 |
| key | string |
| value | string |

### PlayerbotsDungeonSuggestionAbbrevation

- **SQL Table:** playerbots_dungeon_suggestion_abbrevation
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int8 |
| definition_slug | string |
| abbrevation | string |

### PlayerbotsDungeonSuggestionDefinition

- **SQL Table:** playerbots_dungeon_suggestion_definition
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int8 |
| slug | string |
| name | string |
| expansion | int8 |
| difficulty | int8 |
| min_level | int8 |
| max_level | int8 |
| comment | string |

### PlayerbotsDungeonSuggestionStrategy

- **SQL Table:** playerbots_dungeon_suggestion_strategy
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int8 |
| definition_slug | string |
| strategy | string |
| difficulty | int8 |

### PlayerbotsEnchants

- **SQL Table:** playerbots_enchants
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| class | int8 |
| spec | int8 |
| spellid | int32 |
| slotid | int8 |
| name | string |

### PlayerbotsEquipCache

- **SQL Table:** playerbots_equip_cache
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| clazz | int8 |
| lvl | int32 |
| slot | int8 |
| quality | int32 |
| item | int32 |

### PlayerbotsGuildTasks

- **SQL Table:** playerbots_guild_tasks
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| owner | int32 |
| guildid | int32 |
| time | int32 |
| validIn | int32 |
| type | string |
| value | int32 |
| data | string |

### PlayerbotsItemInfoCache

- **SQL Table:** playerbots_item_info_cache
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| quality | int32 |
| slot | int32 |
| source | int64 |
| sourceId | int64 |
| team | int64 |
| faction | int64 |
| factionRepRank | int64 |
| minLevel | int64 |
| scale_1 | int64 |
| scale_2 | int64 |
| scale_3 | int64 |
| scale_4 | int64 |
| scale_5 | int64 |
| scale_6 | int64 |
| scale_7 | int64 |
| scale_8 | int64 |
| scale_9 | int64 |
| scale_10 | int64 |
| scale_11 | int64 |
| scale_12 | int64 |
| scale_13 | int64 |
| scale_14 | int64 |
| scale_15 | int64 |
| scale_16 | int64 |
| scale_17 | int64 |
| scale_18 | int64 |
| scale_19 | int64 |
| scale_20 | int64 |
| scale_21 | int64 |
| scale_22 | int64 |
| scale_23 | int64 |
| scale_24 | int64 |
| scale_25 | int64 |
| scale_26 | int64 |
| scale_27 | int64 |
| scale_28 | int64 |
| scale_29 | int64 |
| scale_30 | int64 |
| scale_31 | int64 |
| scale_32 | int64 |

### PlayerbotsPreferredMounts

- **SQL Table:** playerbots_preferred_mounts
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| guid | int32 |
| type | int8 |
| spellid | int32 |

### PlayerbotsRandomBots

- **SQL Table:** playerbots_random_bots
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| owner | int32 |
| bot | int32 |
| time | int32 |
| validIn | int32 |
| event | string |
| value | int32 |
| data | string |

### PlayerbotsRarityCache

- **SQL Table:** playerbots_rarity_cache
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| item | int32 |
| rarity | float |

### PlayerbotsRnditemCache

- **SQL Table:** playerbots_rnditem_cache
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| lvl | int32 |
| type | int32 |
| item | int32 |

### PlayerbotsSpeech

- **SQL Table:** playerbots_speech
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| text | string |
| type | string |

### PlayerbotsSpeechProbability

- **SQL Table:** playerbots_speech_probability
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| probability | int32 |

### PlayerbotsTeleCache

- **SQL Table:** playerbots_tele_cache
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| level | int8 |
| map_id | int32 |
| x | float |
| y | float |
| z | float |

### PlayerbotsTravelnode

- **SQL Table:** playerbots_travelnode
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| map_id | int32 |
| x | float |
| y | float |
| z | float |
| linked | int8 |

### PlayerbotsTravelnodeLink

- **SQL Table:** playerbots_travelnode_link
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| node_id | int32 |
| to_node_id | int32 |
| type | int8 |
| object | int32 |
| distance | float |
| swim_distance | float |
| extra_cost | float |
| calculated | int8 |
| max_creature_0 | int8 |
| max_creature_1 | int8 |
| max_creature_2 | int8 |

### PlayerbotsTravelnodePath

- **SQL Table:** playerbots_travelnode_path
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| node_id | int32 |
| to_node_id | int32 |
| nr | int32 |
| map_id | int32 |
| x | float |
| y | float |
| z | float |

### PlayerbotsWeightscaleData

- **SQL Table:** playerbots_weightscale_data
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| field | string |
| val | int32 |

### PlayerbotsWeightscales

- **SQL Table:** playerbots_weightscales
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| id | int32 |
| name | string |
| class | int8 |

### VersionDbPlayerbots

- **SQL Table:** version_db_playerbots
- **Database:** acore_playerbots

| Column | Type |
|--------|------|
| sql_rev | string |
| required_rev | string |
| date | string |
