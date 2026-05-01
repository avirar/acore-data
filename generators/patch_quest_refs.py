#!/usr/bin/env python3
"""
Enhance quest-related cross-references and annotations in datastore_registry.json.

Adds ~25 forward cross-references to quest sub-tables, fixes QuestPOI annotations,
and enhances Quest entry notes.

Usage: cd /root/acore-data && python3 generators/patch_quest_refs.py
"""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "datastore_registry.json"


def load():
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save(registry):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def add_field_ref(fields_dict, field_key, target, ref_type="sql_table", ref_col="ID"):
    """Add or update a 'references' on a field."""
    if field_key in fields_dict:
        fields_dict[field_key]["references"] = target
        fields_dict[field_key]["reference_type"] = ref_type
        fields_dict[field_key]["reference_column"] = ref_col


def run(registry):
    entries = registry["entries"]
    changes = []

    # --- 1. QuestPOI (quest_poi) ---
    poi = entries["QuestPOI"]
    # Add cross-refs
    add_field_ref(poi["fields"], "QuestID", "Quest", "sql_objectmgr")
    add_field_ref(poi["fields"], "MapID", "MapEntry", "dbc_entry")
    # Fix annotations - separate table columns with notes
    poi["fields"]["ObjectiveIndex"]["notes"] = "-1=quest turn-in point, 0-3=objective index"
    poi["fields"]["MapID"]["notes"] = "Map ID (see MapEntry)"
    poi["fields"]["WorldMapAreaId"]["notes"] = "Maps to AreaTable entry for minimap overlay"
    # Mark field groups for clarity
    for fk in ("QuestID", "id", "ObjectiveIndex", "MapID", "WorldMapAreaId", "Floor", "Priority", "Flags", "VerifiedBuild"):
        if fk in poi["fields"]:
            poi["fields"][fk]["_source_table"] = "quest_poi"
    for fk in ("Idx1", "Idx2", "X", "Y"):
        if fk in poi["fields"]:
            poi["fields"][fk]["_source_table"] = "quest_poi_points"
            add_field_ref(poi["fields"], "Idx1", "QuestPOI", "sql_objectmgr")  # points to quest_poi.id

    # Remove is_leaf since it now has refs
    poi.pop("is_leaf", None)
    changes.append("QuestPOI: +2 refs (QuestID->Quest, MapID->MapEntry), fixed annotations")

    # --- 2. QuestPoiPoints ---
    pp = entries["QuestPoiPoints"]
    add_field_ref(pp["fields"], "0", "Quest", "sql_objectmgr")  # fix target name from quest_template to Quest
    pp["fields"]["0"]["notes"] = "Quest ID (FK to quest_template.ID)"
    pp["fields"]["1"]["notes"] = "Matches quest_poi.id for same QuestID"
    pp["fields"]["2"]["notes"] = "Point index within POI polygon, ORDER BY Idx2"
    changes.append("QuestPoiPoints: fixed QuestID ref target, +3 notes")

    # --- 3. QuestRelations (creature_queststarter) ---
    qr = entries["QuestRelations"]
    add_field_ref(qr["fields"], "id", "CreatureTemplate", "sql_objectmgr", "entry")
    add_field_ref(qr["fields"], "quest", "Quest", "sql_objectmgr")
    changes.append("QuestRelations: +2 refs (id->CreatureTemplate, quest->Quest)")

    # --- 4. CreatureQuestender ---
    cq = entries["CreatureQuestender"]
    add_field_ref(cq["fields"], "0", "CreatureTemplate", "sql_objectmgr", "entry")
    add_field_ref(cq["fields"], "1", "Quest", "sql_objectmgr")
    changes.append("CreatureQuestender: +2 refs (id->CreatureTemplate, quest->Quest)")

    # --- 5. GameobjectQueststarter ---
    gqs = entries["GameobjectQueststarter"]
    add_field_ref(gqs["fields"], "0", "GameObjectTemplate", "sql_objectmgr", "entry")
    add_field_ref(gqs["fields"], "1", "Quest", "sql_objectmgr")
    changes.append("GameobjectQueststarter: +2 refs (id->GameObjectTemplate, quest->Quest)")

    # --- 6. GameobjectQuestender ---
    gqe = entries["GameobjectQuestender"]
    add_field_ref(gqe["fields"], "0", "GameObjectTemplate", "sql_objectmgr", "entry")
    add_field_ref(gqe["fields"], "1", "Quest", "sql_objectmgr")
    changes.append("GameobjectQuestender: +2 refs (id->GameObjectTemplate, quest->Quest)")

    # --- 7. QuestTemplateAddon ---
    qta = entries["QuestTemplateAddon"]
    add_field_ref(qta["fields"], "4", "Quest", "sql_objectmgr")  # PrevQuestID
    add_field_ref(qta["fields"], "5", "Quest", "sql_objectmgr")  # NextQuestID
    add_field_ref(qta["fields"], "7", "Quest", "sql_objectmgr")  # BreadcrumbForQuestId
    add_field_ref(qta["fields"], "10", "SkillLineEntry", "dbc_backed")  # RequiredSkillID
    add_field_ref(qta["fields"], "12", "FactionEntry", "dbc_backed")  # RequiredMinRepFaction
    add_field_ref(qta["fields"], "13", "FactionEntry", "dbc_backed")  # RequiredMaxRepFaction
    changes.append("QuestTemplateAddon: +6 refs (Prev/Next/Breadcrumb->Quest, Skill->SkillLineEntry, Faction x2)")

    # --- 8. QuestDetails ---
    qd = entries["QuestDetails"]
    add_field_ref(qd["fields"], "0", "Quest", "sql_objectmgr")  # ID
    add_field_ref(qd["fields"], "1", "EmotesEntry", "dbc_backed")  # Emote1
    add_field_ref(qd["fields"], "2", "EmotesEntry", "dbc_backed")  # Emote2
    add_field_ref(qd["fields"], "3", "EmotesEntry", "dbc_backed")  # Emote3
    add_field_ref(qd["fields"], "4", "EmotesEntry", "dbc_backed")  # Emote4
    changes.append("QuestDetails: +5 refs (ID->Quest, Emote1-4->EmotesEntry)")

    # --- 9. QuestOfferReward ---
    qor = entries["QuestOfferReward"]
    add_field_ref(qor["fields"], "0", "Quest", "sql_objectmgr")  # ID
    add_field_ref(qor["fields"], "1", "EmotesEntry", "dbc_backed")  # Emote1
    add_field_ref(qor["fields"], "2", "EmotesEntry", "dbc_backed")  # Emote2
    add_field_ref(qor["fields"], "3", "EmotesEntry", "dbc_backed")  # Emote3
    add_field_ref(qor["fields"], "4", "EmotesEntry", "dbc_backed")  # Emote4
    changes.append("QuestOfferReward: +5 refs (ID->Quest, Emote1-4->EmotesEntry)")

    # --- 10. QuestRequestItems ---
    qri = entries["QuestRequestItems"]
    add_field_ref(qri["fields"], "0", "Quest", "sql_objectmgr")  # ID
    add_field_ref(qri["fields"], "1", "EmotesEntry", "dbc_backed")  # EmoteOnComplete
    add_field_ref(qri["fields"], "2", "EmotesEntry", "dbc_backed")  # EmoteOnIncomplete
    changes.append("QuestRequestItems: +3 refs (ID->Quest, Emote x2->EmotesEntry)")

    # --- 11. CreatureQuestItem ---
    cqi = entries["CreatureQuestItem"]
    add_field_ref(cqi["fields"], "CreatureEntry", "CreatureTemplate", "sql_objectmgr", "entry")
    changes.append("CreatureQuestItem: +1 ref (CreatureEntry->CreatureTemplate)")

    # --- 12. GameObjectQuestItem ---
    goqi = entries["GameObjectQuestItem"]
    add_field_ref(goqi["fields"], "GameObjectEntry", "GameObjectTemplate", "sql_objectmgr", "entry")
    changes.append("GameObjectQuestItem: +1 ref (GameObjectEntry->GameObjectTemplate)")

    # --- 13. Quest entry - enhance notes ---
    quest = entries["Quest"]
    qf = quest["fields"]
    # RequiredNpcOrGo is already good, just enhance notes slightly
    if "RequiredNpcOrGo1..4" in qf:
        qf["RequiredNpcOrGo1..4"]["notes"] = ">0=CreatureTemplate entry (direct look-up), <0=GameObjectTemplate entry (use abs(value)). RequiredNPCOrGoCount is how many of each must be interacted with."

    # POI fields in quest_template are a fallback single-point POI
    if "POIContinent" in qf:
        qf["POIContinent"]["notes"] = "Fallback single-point POI MapID (use quest_poi table for multi-point objectives)"
        qf["POIContinent"].setdefault("references", "MapEntry")
        qf["POIContinent"].setdefault("reference_type", "dbc_entry")
    if "POIx" in qf:
        qf["POIx"]["notes"] = "Fallback POI X coordinate (float, -16000..16000)"
    if "POIy" in qf:
        qf["POIy"]["notes"] = "Fallback POI Y coordinate (float, -16000..16000)"
    changes.append("Quest: enhanced RequiredNpcOrGo/POIContinent/POIx/POIy notes")

    return changes


def main():
    registry = load()
    changes = run(registry)
    save(registry)

    print(f"Applied {len(changes)} changes:")
    for c in changes:
        print(f"  - {c}")

    # Verify: count new cross-refs
    entries = registry["entries"]
    quest_entries = [k for k, v in entries.items() if 'quest' in k.lower() or 'Quest' in k]
    total_fwd = sum(
        sum(1 for f in e.get("fields", {}).values() if isinstance(f, dict) and f.get("references"))
        for k, e in entries.items()
        if isinstance(e, dict) and k in quest_entries
    )
    total_by = sum(
        1 for e in entries.values()
        if isinstance(e, dict) and "referenced_by" in e
    )
    print(f"\nQuest-related entries: {len(quest_entries)}")
    print(f"Quest forward refs (new): ~{total_fwd}")
    print(f"Entries with referenced_by (unchanged yet): {total_by}")


if __name__ == "__main__":
    main()
