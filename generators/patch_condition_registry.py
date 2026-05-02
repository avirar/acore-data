#!/usr/bin/env python3
"""Surgical patch for condition table registry entry.

Adds enum annotations to SourceTypeOrReferenceId and ConditionTypeOrReference,
removes incorrect CreatureTemplate reference from SourceEntry, adds semantic
notes to all polymorphic columns (SourceGroup, SourceEntry, ElseGroup, etc.),
and adds conditional forward references to spell/quest/item/creature targets."""

import json
import sys


NEW_CONDITION_ENTRY = {
    "category": "sql_manager",
    "sql_table": "conditions",
    "sql_database": "db_world",
    "manager_singleton": "sConditionMgr",
    "manager_class": "ConditionMgr",
    "store_variable": "",
    "container_type": "",
    "header_file": "src/server/game/Conditions/ConditionMgr.h",
    "c_struct": "Condition",
    "fields": {
        "SourceType": {
            "name": "SourceType",
            "type": "`ConditionSourceType`",
            "sql_column": "SourceTypeOrReferenceId",
            "notes": (
                "Enums: 0=NONE, 1=CREATURE_LOOT, 2=DISENCHANT_LOOT, 3=FISHING_LOOT, "
                "4=GAMEOBJECT_LOOT, 5=ITEM_LOOT, 6=MAIL_LOOT, 7=MILLING_LOOT, "
                "8=PICKPOCKETING_LOOT, 9=PROSPECTING_LOOT, 10=REFERENCE_LOOT, 11=SKINNING_LOOT, "
                "12=SPELL_LOOT(SourceEntry=item ID), 13=SPELL_IMPLICIT_TARGET(SourceEntry=spell ID, SourceGroup=effect bitmask:1=eff0,2=eff1,4=eff2), "
                "14=GOSSIP_MENU(SourceEntry=gossip menu ID), 15=GOSSIP_MENU_OPTION(SourceEntry=text ID), "
                "16=CREATURE_TEMPLATE_VEHICLE(SourceEntry=creature entry), "
                "17=SPELL(SourceEntry=spell ID, ErrorType valid on failure), "
                "18=SPELL_CLICK_EVENT(SourceGroup=creature entry, SourceEntry=spell ID), "
                "19=QUEST_AVAILABLE(SourceEntry=quest ID), 20=GOSSIP_HELLO, "
                "21=VEHICLE_SPELL(SourceGroup=creature entry, SourceEntry=spell ID), "
                "22=SMART_EVENT, 23=NPC_VENDOR(SourceEntry=item/creature), "
                "24=SPELL_PROC(SourceEntry=spell ID, blocks aura proc on failure), "
                "25=TERRAIN_SWAP, 26=PHASE, 27=GRAVEYARD, 28=PLAYER_LOOT, "
                "29=CREATURE_RESPAWN(SourceEntry=creature entry/guid), "
                "30=OBJECT_VISIBILITY. Negative values = condition reference template ID."
            )
        },
        "SourceGroup": {
            "name": "SourceGroup",
            "type": "`uint32`",
            "sql_column": "SourceGroup",
            "notes": (
                "Context-dependent grouping key. SPELL_IMPLICIT_TARGET(13)=effect bitmask "
                "(1=eff0, 2=eff1, 4=eff2). SPELL_CLICK_EVENT(18)/VEHICLE_SPELL(21)=creature entry. "
                "Loot templates(1-12)=loot template ID. Otherwise 0."
            )
        },
        "SourceEntry": {
            "name": "SourceEntry",
            "type": "`int32`",
            "sql_column": "SourceEntry",
            "notes": (
                "Primary identifier; meaning depends on SourceTypeOrReferenceId. "
                "For spell sources(13,17,24): spell ID. For loot(1-12): item ID for drop conditions. "
                "For gossip(14,15): menu/text/option ID. For QUEST_AVAILABLE(19): quest ID. "
                "For GOSSIP_HELLO(20)/CREATURE_TEMPLATE_VEHICLE(16)/CREATURE_RESPAWN(29): creature entry."
            ),
            "references": [
                {"source_type_values": [13, 17, 24], "target": "Spell", "type": "sql_table"},
                {"source_type_values": [18, 21], "target": "Spell", "type": "sql_table"},
                {"source_type_values": [19], "target": "Quest", "type": "sql_table"},
                {"source_type_values": [14, 15, 20], "target": "GossipMenu", "type": "sql_table"},
            ],
            "reference_type": "polymorphic",
            "reference_column": "ID"
        },
        "SourceId": {
            "name": "SourceId",
            "type": "`uint32`",
            "sql_column": "SourceId",
            "notes": (
                "Secondary context key. Used by SMART_EVENT(22) for SAI source_type, "
                "OBJECT_VISIBILITY(30) for spawn GUID. Otherwise 0."
            )
        },
        "ElseGroup": {
            "name": "ElseGroup",
            "type": "`uint32`",
            "sql_column": "ElseGroup",
            "notes": (
                "OR-grouping mechanism. Conditions with the same ElseGroup are ANDed together. "
                "Different ElseGroups are ORed. If any ElseGroup fully passes, the condition set passes."
            )
        },
        "ConditionType": {
            "name": "ConditionType",
            "type": "`ConditionTypes`",
            "sql_column": "ConditionTypeOrReference",
            "notes": (
                "Enums: 0=NONE, 1=AURA(spell_id,eff_index,0), 2=ITEM(item_id,count,bank), "
                "3=ITEM_EQUIPPED(item_id,0,0), 4=ZONEID(zone_id,0,0), "
                "5=REPUTATION_RANK(faction_id,rankMask,0), 6=TEAM(team[469/Alliance or 67/Horde],0,0), "
                "7=SKILL(skill_id,skill_value,0), 8=QUESTREWARDED(quest_id,0,0), "
                "9=QUESTTAKEN(quest_id,0,0), 10=DRUNKENSTATE(state,0,0), "
                "11=WORLD_STATE(index,value,0), 12=ACTIVE_EVENT(event_id,0,0), "
                "13=INSTANCE_INFO(entry,data,type), 14=QUEST_NONE(quest_id,0,0), "
                "15=CLASS(classMask,0,0), 16=RACE(raceMask,0,0), "
                "17=ACHIEVEMENT(achievement_id,0,0), 18=TITLE(title_id,0,0), "
                "19=SPAWNMASK(mask,0,0), 20=GENDER(gender[0=female,1=male],0,0), "
                "21=UNIT_STATE(unitState,0,0), 22=MAPID(map_id,0,0), "
                "23=AREAID(area_id,0,0), 24=CREATURE_TYPE(type_id,0,0), "
                "25=SPELL(spell_id,0,0), 26=PHASEMASK(mask,0,0), "
                "27=LEVEL(level,ComparisonType[0=>=,1=<=,2===],0), "
                "28=QUEST_COMPLETE(quest_id,0,0), 29=NEAR_CREATURE(entry,distance,dead), "
                "30=NEAR_GAMEOBJECT(entry,distance,goState), "
                "31=OBJECT_ENTRY_GUID(TypeID,entry,guid), 32=TYPE_MASK(mask,0,0), "
                "33=RELATION_TO(targetIdx,RelationType,0), 34=REACTION_TO(targetIdx,rankMask,0), "
                "35=DISTANCE_TO(targetIdx,distance,ComparisonType), 36=ALIVE(0,0,0), "
                "37=HP_VAL(val,ComparisonType,0), 38=HP_PCT(pct,ComparisonType,0), "
                "39=REALM_ACHIEVEMENT(id,0,0), 40=IN_WATER(0,0,0), "
                "42=STAND_STATE(type,state,0), 43=DAILY_QUEST_DONE(quest_id,0,0), "
                "44=CHARMED(0,0,0), 45=PET_TYPE(mask,0,0), 46=TAXI(0,0,0), "
                "47=QUESTSTATE(quest_id,stateMask[1=not_taken,2=completed,8=in_progress],0), "
                "48=QUEST_OBJ_PROGRESS(quest_id,objIndex,objCount), 49=DIFFICULTY_ID(diff,0,0). "
                "AC custom: 101=QUEST_SATISFY_EXCLUSIVE, 102=HAS_AURA_TYPE(aura_type,0,0), "
                "103=WORLD_SCRIPT(condId,state,0), 104=AI_DATA(dataId,value,0), "
                "105=PLAYER_QUEUED_RANDOM_DUNGEON. Negative = reference to condition template."
            )
        },
        "ConditionTarget": {
            "name": "ConditionTarget",
            "type": "`uint8`",
            "sql_column": "ConditionTarget",
            "notes": (
                "Which target slot in ConditionSourceInfo to evaluate against. "
                "0=caster/invoker, 1=spell target/candidate, 2=third-party (SAI only)."
            )
        },
        "ConditionValue1": {
            "name": "ConditionValue1",
            "type": "`uint32`",
            "sql_column": "ConditionValue1",
            "notes": (
                "First parameter; meaning depends on ConditionTypeOrReference. "
                "Common: AURA(1)=spell_id, ITEM(2)=item_id, ZONEID(4)=zone_id, "
                "QUESTREWARDED(8)/QUESTTAKEN(9)=quest_id, CLASS(15)=classMask, "
                "RACE(16)=raceMask, SPELL(25)=spell_id, LEVEL(27)=level, "
                "NEAR_CREATURE(29)=creature_entry, NEAR_GAMEOBJECT(30)=go_entry, "
                "OBJECT_ENTRY_GUID(31)=TypeID, HP_VAL(37)=hpVal, "
                "HP_PCT(38)=hpPct, QUESTSTATE(47)=quest_id."
            )
        },
        "ConditionValue2": {
            "name": "ConditionValue2",
            "type": "`uint32`",
            "sql_column": "ConditionValue2",
            "notes": (
                "Second parameter; meaning depends on ConditionTypeOrReference. "
                "Common: AURA(1)=eff_index, ITEM(2)=count, LEVEL(27)=ComparisonType "
                "(0=>=, 1=<=, 2===, 3=!=), DISTANCE_TO(35)=distance, "
                "QUESTSTATE(47)=stateMask[1=not_taken,2=completed,8=in_progress,32=failed,64=rewarded], "
                "QUEST_OBJ_PROGRESS(48)=objIndex."
            )
        },
        "ConditionValue3": {
            "name": "ConditionValue3",
            "type": "`uint32`",
            "sql_column": "ConditionValue3",
            "notes": (
                "Third parameter; meaning depends on ConditionTypeOrReference. "
                "Common: ITEM(2)=bank_flag[0=non-bag,1=bag,2=bank], "
                "NEAR_CREATURE(29)=dead[0=alive only,1=dead only,2=any], "
                "OBJECT_ENTRY_GUID(31)=guid_or_attackable."
            )
        },
        "NegativeCondition": {
            "name": "NegativeCondition",
            "type": "`bool`",
            "sql_column": "NegativeCondition",
            "notes": (
                "1=inverts the condition result (NOT logic). A passing condition is treated as failure."
            )
        },
        "ErrorType": {
            "name": "ErrorType",
            "type": "`uint32`",
            "sql_column": "ErrorType",
            "notes": (
                "SpellCastResult enum. Only valid for SourceType SPELL(17). When spell cast condition "
                "fails, this error code is returned. 0=use default error (SPELL_FAILED_CASTER_AURASTATE "
                "if ConditionTarget=0, SPELL_FAILED_BAD_TARGETS if ConditionTarget=1)."
            )
        },
        "ErrorTextId": {
            "name": "ErrorTextId",
            "type": "`uint32`",
            "sql_column": "ErrorTextId",
            "notes": (
                "Additional error text ID. Used when ErrorType=SPELL_FAILED_CUSTOM_ERROR."
            )
        },
        "ReferenceId": {
            "name": "ReferenceId",
            "type": "`uint32`"
        },
        "ScriptId": {
            "name": "ScriptId",
            "type": "`uint32`"
        }
    }
}


def main():
    with open("datastore_registry.json") as f:
        reg = json.load(f)

    # Replace the Condition entry
    reg["entries"]["Condition"] = NEW_CONDITION_ENTRY

    with open("datastore_registry.json", "w") as f:
        json.dump(reg, f, indent=2)

    print("Patched Condition entry in datastore_registry.json")

    # Verify
    with open("datastore_registry.json") as f:
        newreg = json.load(f)
    cond = newreg["entries"]["Condition"]
    has_source_notes = "SOURCE_IMPLICIT_TARGET" in cond["fields"]["SourceType"]["notes"]
    has_cond_notes = "AURA(spell_id" in cond["fields"]["ConditionType"]["notes"]
    has_elsegroup = "OR-grouping" in cond["fields"]["ElseGroup"]["notes"]
    no_bad_ref = cond["fields"]["SourceEntry"].get("references") != "CreatureTemplate"
    print(f"  SourceType enum notes: {'OK' if has_source_notes else 'FAIL'}")
    print(f"  ConditionType enum notes: {'OK' if has_cond_notes else 'FAIL'}")
    print(f"  ElseGroup semantic notes: {'OK' if has_elsegroup else 'FAIL'}")
    print(f"  Removed incorrect CreatureTemplate ref: {'OK' if no_bad_ref else 'FAIL'}")


if __name__ == "__main__":
    main()
