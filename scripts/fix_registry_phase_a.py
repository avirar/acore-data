#!/usr/bin/env python3
"""
Phase A: fix clear, verified data bugs in datastore_registry.json.

Applied (all idempotent, structure/key-order preserving):
  1. dangling_refs   - 3 references pointed at non-existent targets
  2. type_as_name    - 200 generated sql_* fields whose `name` was a raw C type
                       string; set name = the real column (== field key == sql_column)
  3. missing_data_source - map 2 abstract structs to their real tables and correct
                       their sql_columns; flag 2 genuinely in-memory structs

Run:  .venv/bin/python3 scripts/fix_registry_phase_a.py [--check]
  --check  dry-run: report what would change, write nothing
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG_PATH = ROOT / "datastore_registry.json"

TYPES = {
    "uint8", "int8", "uint16", "int16", "uint32", "int32", "uint64", "int64",
    "float", "double", "char", "bool", "string", "void", "byte", "short",
    "long", "size_t", "std::string",
}


def canon(name: str) -> str:
    return re.sub(r"\[\d+\]$", "", name)


def main():
    check = "--check" in sys.argv
    reg = json.loads(REG_PATH.read_text())
    E = reg["entries"]

    changes = []

    # ---- 1. dangling refs ------------------------------------------------
    # GameEventData.EventId is the PK (eventEntry); it does not reference anything.
    f = E["GameEventData"]["fields"]["EventId"]
    if f.get("references") == "GameEventEntry":
        for k in ("references", "reference_type", "reference_column"):
            f.pop(k, None)
        changes.append("GameEventData.EventId: removed bogus self-PK reference")

    # GameEventCreature.eventEntry -> GameEventData (not the non-existent GameEventEntry)
    f = E["GameEventCreature"]["fields"]["0"]
    if f.get("references") == "GameEventEntry":
        f["references"] = "GameEventData"
        f["reference_type"] = "sql_manager"
        f["reference_column"] = "eventEntry"
        changes.append("GameEventCreature.eventEntry -> GameEventData (col eventEntry)")

    # CharacterPet.owner -> Characters (not the non-existent Character), col guid
    f = E["CharacterPet"]["fields"]["2"]
    if f.get("references") == "Character":
        f["references"] = "Characters"
        f["reference_type"] = "sql_auxiliary"
        f["reference_column"] = "guid"
        changes.append("CharacterPet.owner -> Characters (col guid)")

    # ---- 2. type-as-name -------------------------------------------------
    renamed = 0
    for n, e in E.items():
        for k, f in e.get("fields", {}).items():
            if not isinstance(f, dict):
                continue
            name = f.get("name", "")
            if not name or canon(name).lower() not in TYPES:
                continue
            if isinstance(f.get("references"), str) and f.get("references"):
                continue
            sc = f.get("sql_column", "")
            if sc == k and name != sc:
                f["name"] = k
                renamed += 1
    changes.append(f"type_as_name: renamed {renamed} fields (name := real column)")

    # ---- 3. missing data source -----------------------------------------
    # SpawnGroupTemplateData <- spawn_group_template (SELECT groupId, groupName, groupFlags)
    e = E["SpawnGroupTemplateData"]
    if e.get("sql_table") != "spawn_group_template":
        e["sql_table"] = "spawn_group_template"
        changes.append("SpawnGroupTemplateData: sql_table=spawn_group_template")
    sf = e["fields"]
    if sf["name"].get("sql_column") != "groupName":
        sf["name"]["sql_column"] = "groupName"
        changes.append("SpawnGroupTemplateData.name: sql_column=groupName")
    if sf["flags"].get("sql_column") != "groupFlags":
        sf["flags"]["sql_column"] = "groupFlags"
        changes.append("SpawnGroupTemplateData.flags: sql_column=groupFlags")
    # mapId is not loaded from the table (SPAWNGROUP_MAP_UNSET) - clear bogus column
    if sf["mapid"].get("sql_column") not in (None, ""):
        sf["mapid"]["sql_column"] = None
        sf["mapid"]["notes"] = "Not loaded from spawn_group_template (runtime-derived)"
        changes.append("SpawnGroupTemplateData.mapid: cleared sql_column (not in table)")
    # mapId is a real relationship to Map
    if not sf["mapid"].get("references"):
        sf["mapid"]["references"] = "MapEntry"
        sf["mapid"]["reference_type"] = "dbc_backed"
        sf["mapid"]["reference_column"] = "ID"
        changes.append("SpawnGroupTemplateData.mapid: +reference MapEntry")

    # WaypointPath <- waypoint_data (id + one row per waypoint node)
    e = E["WaypointPath"]
    if e.get("sql_table") != "waypoint_data":
        e["sql_table"] = "waypoint_data"
        changes.append("WaypointPath: sql_table=waypoint_data")
    if e["fields"]["Id"].get("sql_column") != "id":
        e["fields"]["Id"]["sql_column"] = "id"
        changes.append("WaypointPath.Id: sql_column=id")
    if e["fields"]["Nodes"].get("sql_column") not in (None, ""):
        e["fields"]["Nodes"]["sql_column"] = None
        changes.append("WaypointPath.Nodes: cleared sql_column (row-set, not a column)")
    if not e["fields"]["Nodes"].get("notes"):
        e["fields"]["Nodes"]["notes"] = "One waypoint_data row per node, grouped by id"

    # Genuinely in-memory structs (no backing table) - flag so the audit skips them
    for n in ("CellObjectGuids", "LootStoreItem"):
        if not E[n].get("in_memory_only"):
            E[n]["in_memory_only"] = True
            changes.append(f"{n}: flagged in_memory_only=True (no backing table)")

    # LootStoreItem.itemid is a real item reference
    if not E["LootStoreItem"]["fields"]["itemid"].get("references"):
        f = E["LootStoreItem"]["fields"]["itemid"]
        f["references"] = "ItemEntry"
        f["reference_type"] = "dbc_backed"
        f["reference_column"] = "ID"
        changes.append("LootStoreItem.itemid: +reference ItemEntry")

    # ---- write ------------------------------------------------------------
    print("PHASE A CHANGES" + (" (dry-run)" if check else ""))
    print("=" * 60)
    for c in changes:
        print("  -", c)
    if check:
        print(f"\n[check] {len(changes)} change(s) would be applied.")
        return

    with REG_PATH.open("w") as fh:
        json.dump(reg, fh, indent=2)
        fh.write("\n")
    print(f"\n[Wrote {REG_PATH} with {len(changes)} change(s)]")


if __name__ == "__main__":
    main()
