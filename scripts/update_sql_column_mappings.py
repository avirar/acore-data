#!/usr/bin/env python3
"""
Update sql_manager entries in datastore_registry.json with accurate C++ field → SQL column mappings.

Mappings are derived from analyzing AzerothCore source code loaders (prepared statements + inline queries).

Run from project root: python3 scripts/update_sql_column_mappings.py
"""

import json
import sys
from pathlib import Path

# Map: entry_name -> {cpp_field_name: sql_column_name}
# Derived from AzerothCore source code field assignments.

MAPPINGS = {
    # === SpellProcEntry (spell_proc) ===
    # src/server/game/Spells/SpellMgr.cpp:1894
    # SELECT SpellId, SchoolMask, SpellFamilyName, SpellFamilyMask0, SpellFamilyMask1, SpellFamilyMask2,
    #        ProcFlags, SpellTypeMask, SpellPhaseMask, HitMask, AttributesMask, DisableEffectsMask,
    #        ProcsPerMinute, Chance, Cooldown, Charges FROM spell_proc
    "SpellProcEntry": {
        "SchoolMask": "SchoolMask",
        "SpellFamilyName": "SpellFamilyName",
        "SpellFamilyMask": "SpellFamilyMask0",  # split across 3 columns; map to first as representative
        "ProcFlags": "ProcFlags",
        "SpellTypeMask": "SpellTypeMask",
        "SpellPhaseMask": "SpellPhaseMask",
        "HitMask": "HitMask",
        "AttributesMask": "AttributesMask",
        "DisableEffectsMask": "DisableEffectsMask",
        "ProcsPerMinute": "ProcsPerMinute",
        "Chance": "Chance",
        "Cooldown": "Cooldown",
        "Charges": "Charges",
    },

    # === SpellEnchantProcEntry (spell_enchant_proc_data) ===
    # src/server/game/Spells/SpellMgr.cpp:2427
    # SELECT entry, customChance, PPMChance, procEx, attributeMask FROM spell_enchant_proc_data
    "SpellEnchantProcEntry": {
        "customChance": "customChance",
        "PPMChance": "PPMChance",
        "procEx": "procEx",
        "attributeMask": "attributeMask",
    },

    # === SpellBonusEntry (spell_bonus_data) ===
    # src/server/game/Spells/SpellMgr.cpp:2183
    # SELECT entry, direct_bonus, dot_bonus, ap_bonus, ap_dot_bonus FROM spell_bonus_data
    "SpellBonusEntry": {
        "direct_damage": "direct_bonus",
        "dot_damage": "dot_bonus",
        "ap_bonus": "ap_bonus",
        "ap_dot_bonus": "ap_dot_bonus",
    },

    # === SpellThreatEntry (spell_threat) ===
    # src/server/game/Spells/SpellMgr.cpp:2224
    # SELECT entry, flatMod, pctMod, apPctMod FROM spell_threat
    "SpellThreatEntry": {
        "flatMod": "flatMod",
        "pctMod": "pctMod",
        "apPctMod": "apPctMod",
    },

    # === SpellCooldownOverride (spell_cooldown_overrides) ===
    # src/server/game/Spells/SpellMgr.cpp:2940
    # SELECT Id, RecoveryTime, CategoryRecoveryTime, StartRecoveryTime, StartRecoveryCategory FROM spell_cooldown_overrides
    "SpellCooldownOverride": {
        "RecoveryTime": "RecoveryTime",
        "CategoryRecoveryTime": "CategoryRecoveryTime",
        "StartRecoveryTime": "StartRecoveryTime",
        "StartRecoveryCategory": "StartRecoveryCategory",
    },

    # === SpellArea (spell_area) ===
    # src/server/game/Spells/SpellMgr.cpp:2702
    # SELECT spell, area, quest_start, quest_start_status, quest_end_status, quest_end, aura_spell, racemask, gender, autocast FROM spell_area
    "SpellArea": {
        "spellId": "spell",
        "areaId": "area",
        "questStart": "quest_start",
        "questEnd": "quest_end",
        "auraSpell": "aura_spell",
        "raceMask": "racemask",
        "gender": "gender",
        "questStartStatus": "quest_start_status",
        "questEndStatus": "quest_end_status",
        "autocast": "autocast",
    },

    # === SpellTargetPosition (spell_target_position) ===
    # src/server/database/WorldDatabase.cpp: prepared statement WORLD_SEL_SPELL_TARGET_POSITION
    # SELECT TargetMapID, TargetX, TargetY, TargetZ, TargetOrientation FROM spell_target_position
    "SpellTargetPosition": {
        "target_mapId": "TargetMapID",
        "target_X": "TargetX",
        "target_Y": "TargetY",
        "target_Z": "TargetZ",
        "target_Orientation": "TargetOrientation",
    },

    # === CreatureImmunities (creature_immunities) ===
    # src/server/game/Spells/SpellMgr.cpp:66
    # SELECT ID, SchoolMask, DispelTypeMask, MechanicsMask, Effects, Auras, ImmuneAoE, ImmuneChain FROM creature_immunities
    "CreatureImmunities": {
        "School": "SchoolMask",
        "DispelType": "DispelTypeMask",
        "Mechanic": "MechanicsMask",
        "Effect": "Effects",
        "Aura": "Auras",
        "ImmuneAoE": "ImmuneAoE",
        "ImmuneChain": "ImmuneChain",
    },

    # === SmartScriptHolder (smart_scripts) ===
    # WORLD_SEL_SMART_SCRIPTS:
    # SELECT entryorguid, source_type, id, link, event_type, event_phase_mask, event_chance, event_flags,
    #        event_param1-6, action_type, action_param1-6, target_type, target_param1-4, target_x/y/z/o
    # NOTE: fields like timer, priority, active, runOnce, enableTimed have no SQL column
    "SmartScriptHolder": {
        "entryOrGuid": "entryorguid",
        "source_type": "source_type",
        "event_id": "id",
        "link": "link",
        # Nested struct fields (temp.event.type etc.) - map as flat keys for filter support
        "event_type": "event_type",
        "event_phase_mask": "event_phase_mask",
        "event_chance": "event_chance",
        "event_flags": "event_flags",
        "action_type": "action_type",
        "target_type": "target_type",
    },

    # === Condition (conditions) ===
    # SQL table columns: SourceTypeOrReferenceId, SourceGroup, SourceEntry, SourceId, ElseGroup,
    #                     ConditionTypeOrReference, ConditionTarget, ConditionValue1-3, NegativeCondition,
    #                     ErrorType, ErrorTextId, ScriptName, Comment
    "Condition": {
        "SourceType": "SourceTypeOrReferenceId",  # different name in SQL
        "SourceGroup": "SourceGroup",
        "SourceEntry": "SourceEntry",
        "SourceId": "SourceId",
        "ElseGroup": "ElseGroup",
        "ConditionType": "ConditionTypeOrReference",  # different name in SQL
        "ConditionTarget": "ConditionTarget",
        "ConditionValue1": "ConditionValue1",
        "ConditionValue2": "ConditionValue2",
        "ConditionValue3": "ConditionValue3",
        "NegativeCondition": "NegativeCondition",
        "ErrorType": "ErrorType",
        "ErrorTextId": "ErrorTextId",
        # ReferenceId and ScriptId have no direct SQL column (ScriptName is not mapped to ScriptId)
    },

    # === GameEventData (game_event) ===
    # WORLD_SEL_GAME_EVENTS: SELECT eventEntry, UNIX_TIMESTAMP(start_time), UNIX_TIMESTAMP(end_time),
    #                         occurence, length, holiday, holidayStage, description, world_event, announce
    "GameEventData": {
        "EventId": "eventEntry",
        "Start": "start_time",
        "End": "end_time",
        "Occurence": "occurence",
        "Length": "length",
        "HolidayId": "holiday",
        "HolidayStage": "holidayStage",
        "Description": "description",
        "Announce": "announce",
        # State, NextStart, Conditions, PrerequisiteEvents are computed at runtime, no SQL column
    },

    # === GameEventFinishCondition (game_event_condition) ===
    # WORLD_SEL_GAME_EVENT_CONDITION_DATA: SELECT eventEntry, condition_id, req_num, max_world_state_field, done_world_state_field
    "GameEventFinishCondition": {
        "ReqNum": "req_num",
        "Done": "done_world_state_field",  # maps to the 'done' computation from done_world_state_field
        "MaxWorldState": "max_world_state_field",
        "DoneWorldState": "done_world_state_field",
    },

    # === BattlegroundTemplate (battleground_template) ===
    # Inline query: SELECT ID, MinPlayersPerTeam, MaxPlayersPerTeam, MinLvl, MaxLvl,
    #               AllianceStartLoc, AllianceStartO, HordeStartLoc, HordeStartO, StartMaxDist, Weight, ScriptName
    "BattlegroundTemplate": {
        "Id": "ID",
        "MinPlayersPerTeam": "MinPlayersPerTeam",
        "MaxPlayersPerTeam": "MaxPlayersPerTeam",
        "MinLevel": "MinLvl",
        "MaxLevel": "MaxLvl",
        "Weight": "Weight",
        # StartLocation is array of Positions from Alliance/HordeStartLoc - no single SQL column
        # MaxStartDistSq derived from StartMaxDist (squared in code)
        # BattlemasterEntry loaded from DBC, not SQL
    },

    # === CreatureTextEntry (creature_text) ===
    # WORLD_SEL_CREATURE_TEXT: SELECT CreatureID, GroupID, ID, Text, Type, Language, Probability, Emote, Duration, Sound, BroadcastTextId, TextRange
    "CreatureTextEntry": {
        "entry": "CreatureID",
        "group": "GroupID",
        "id": "ID",
        "text": "Text",
        "type": "Type",
        "lang": "Language",
        "probability": "Probability",
        "emote": "Emote",
        "duration": "Duration",
        "sound": "Sound",
        "BroadcastTextId": "BroadcastTextId",
        "TextRange": "TextRange",
    },

    # === CreatureTextLocale (creature_text_locale) ===
    "CreatureTextLocale": {
        "Text": "Text_loc",  # locale-specific text column
    },

    # === FormationInfo (creature_formations) ===
    # Inline: SELECT leaderGUID, memberGUID, dist, angle, groupAI, point_1, point_2 FROM creature_formations
    "FormationInfo": {
        "leaderGUID": "leaderGUID",
        "follow_dist": "dist",
        "follow_angle": "angle",
        "groupAI": "groupAI",
        "point_1": "point_1",
        "point_2": "point_2",
    },

    # === NPCVendorEntry (game_event_npc_vendor) ===
    # WORLD_SEL_GAME_EVENT_NPC_VENDOR: SELECT eventEntry, guid, item, maxcount, incrtime, ExtendedCost
    "NPCVendorEntry": {
        "Item": "item",
        "MaxCount": "maxcount",
        "Incrtime": "incrtime",
        "ExtendedCost": "ExtendedCost",
    },

    # === AchievementReward (achievement_reward) ===
    # Inline: SELECT ID, TitleA, TitleH, ItemID, Sender, Subject, Body, MailTemplateID FROM achievement_reward
    "AchievementReward": {
        "titleId": "TitleA",  # array [2] mapped from TitleA/TitleH; TitleA as representative
        "itemId": "ItemID",
        "sender": "Sender",
        "subject": "Subject",
        "text": "Body",
        "mailTemplate": "MailTemplateID",
    },

    # === AchievementRewardLocale (achievement_reward_locale) ===
    # Inline: SELECT ID, Locale, Subject, Text FROM achievement_reward_locale
    "AchievementRewardLocale": {
        "Subject": "Subject",
        "Text": "Text",
    },

    # === LfgReward (lfg_dungeon_rewards) ===
    # WORLD_SEL_LFG_REWARD: SELECT minLevel, maxLevel, firstQuestId, otherQuestId FROM lfg_dungeon_rewards
    "LfgReward": {
        "maxLevel": "maxLevel",
        "firstQuest": "firstQuestId",
        "otherQuest": "otherQuestId",
    },

    # === Guild (guild table in characters DB) ===
    # GuildMgr.cpp:102-105: SELECT g.guildid, g.name, g.leaderguid, g.EmblemStyle, g.EmblemColor, g.BorderStyle, g.BorderColor,
    #                        g.BackgroundColor, g.info, g.motd, g.createdate, g.BankMoney, COUNT(gbt.guildid)
    "Guild": {
        "EmblemStyle": "EmblemStyle",
        "EmblemColor": "EmblemColor",
        "BorderStyle": "BorderStyle",
        "BorderColor": "BorderColor",
        "BackgroundColor": "BackgroundColor",
        "BankMoney": "BankMoney",
    },

    # === ModelEquip (game_event_model_equip) ===
    # GameEventMgr.cpp:629-630: ModelId = fields[5], EquipmentId = fields[6]
    "ModelEquip": {
        "ModelId": "modelid",
        "EquipmentId": "equipment_id",
    },

    # === AchievementCriteriaData (achievement_criteria_data) ===
    # WORLD_SEL_ACHIEVEMENT_CRITERIA_DATA: SELECT criteria_id, type, value1, value2, script_name FROM achievement_criteria_data
    "AchievementCriteriaData": {
        "dataType": "type",
        "raw.value1": "value1",
        "raw.value2": "value2",
    },

    # === OutdoorPvPData (outdoorpvp_template) ===
    # WORLD_SEL_OUTDOOR_PVP: SELECT TypeId, ScriptName FROM outdoorpvp_template
    "OutdoorPvPData": {
        "TypeId": "TypeId",
        "ScriptId": "ScriptName",
    },

    # === WardenCheckResult (warden_action) ===
    # Select from warden_action table
    "WardenCheckResult": {
        "Result": "result",
    },

    # === BannedAddons (banned_addons) ===
    # SQL: Id, NameMD5, VersionMD5, Timestamp
    "BannedAddons": {
        "Id": "Id",
        "Name": "NameMD5",
        "Version": "VersionMD5",
        "Timestamp": "Timestamp",
    },

    # === PoolTemplateData (pool_template) ===
    # pool_template: entry, max_limit, description
    "PoolTemplateData": {
        "MaxLimit": "max_limit",
    },

    # === DisableData (disables table) ===
    # disables: flag1, flag2, params
    "DisableData": {
        "flags": "flag1",
    },

    # === WaypointPath ===
    # waypoints: entry, id, position_x, position_y, position_z, orientation, delay
    "WaypointPath": {
        "Id": "id",
    },

    # === LootStoreItem (loot_template -> loot) ===
    # No single table; these are computed from loot templates. Skip complex ones.
    "LootStoreItem": {},


    # === WardenCheck (warden_checks) ===
    "WardenCheck": {
        "Type": "type",
        "Data": "data",
        "Address": "address",
        "Length": "length",
        "Str": "str",
        "Comment": "comment",
        "CheckId": "check_id",
        "IdStr": "id_str",
        "Action": "action",
    },

    # === WeatherData (game_weather -> weather table) ===
    "WeatherData": {
        "ScriptId": "script_name",
    },
}


def update_registry(registry_path: Path):
    with open(registry_path) as f:
        registry = json.load(f)

    updated_count = 0
    field_count = 0

    for entry_name, field_mapping in MAPPINGS.items():
        if entry_name not in registry["entries"]:
            print(f"  WARNING: Entry '{entry_name}' not found in registry, skipping.")
            continue

        entry = registry["entries"][entry_name]
        fields = entry.get("fields", {})

        for cpp_field_name, sql_column in field_mapping.items():
            # Find the field by name (registry uses numeric keys like "0", "1", ... with 'name' property)
            found_key = None
            for key, field_info in fields.items():
                if field_info.get("name") == cpp_field_name:
                    found_key = key
                    break

            if found_key is None:
                # Field may use dot notation (e.g., "raw.value1") - search partial
                for key, field_info in fields.items():
                    if field_info.get("name") and field_info["name"].endswith(cpp_field_name.split(".")[-1]):
                        found_key = key
                        break

            if found_key is None:
                print(f"  WARNING: Field '{cpp_field_name}' not found in entry '{entry_name}', skipping.")
                continue

            old_sql = fields[found_key].get("sql_column")
            if old_sql and old_sql != sql_column:
                print(f"  UPDATE: {entry_name}.{cpp_field_name}: '{old_sql}' -> '{sql_column}'")
            else:
                print(f"  SET:    {entry_name}.{cpp_field_name} -> '{sql_column}'")

            fields[found_key]["sql_column"] = sql_column
            field_count += 1
            updated_count += 1 if old_sql and old_sql != sql_column else 0

    print(f"\nUpdated {field_count} field mappings ({updated_count} changed, {field_count - updated_count} newly set)")

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")

    print("Registry saved.")


if __name__ == "__main__":
    registry_path = Path(__file__).parent.parent / "datastore_registry.json"
    if not registry_path.exists():
        print(f"ERROR: Registry file not found at {registry_path}")
        sys.exit(1)

    update_registry(registry_path)
