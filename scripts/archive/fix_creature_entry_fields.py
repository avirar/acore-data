#!/usr/bin/env python3
"""Fix the CreatureData (table: creature) registry entry.

Found via LLM tool-calling eval (nemotron-3.5-lightning-free, task T3):
`query creature filter {id: ...}` failed with "Unknown field 'id'... Did you
mean: id3, id2, id1" - the entry had id2/id3 (C++ members from
creature_multispawn) but was missing the primary `id` column, and carried a
phantom `id1` that exists in neither the C++ struct (CreatureData has
id, id2, id3 - no id1) nor the live table.

Changes (idempotent):
  - add `id` (uint32, sql_column `id`, references CreatureTemplate)
  - drop phantom `id1`
  - add DB-only spatial columns `zoneId` / `areaId` (references AreaTableEntry)

Run: .venv/bin/python3 scripts/archive/fix_creature_entry_fields.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REG = ROOT / "datastore_registry.json"

ENTRY = "CreatureData"

NEW_FIELDS = {
    "id": {"name": "id", "type": "uint32", "sql_column": "id",
           "references": "CreatureTemplate"},
    "zoneId": {"name": "zoneId", "type": "uint16", "sql_column": "zoneId",
               "references": "AreaTableEntry"},
    "areaId": {"name": "areaId", "type": "uint16", "sql_column": "areaId",
               "references": "AreaTableEntry"},
}


def main():
    reg = json.loads(REG.read_text())
    e = reg["entries"][ENTRY]
    fields = e["fields"]

    changed = False
    if "id1" in fields:
        del fields["id1"]
        changed = True
        print("dropped phantom field id1")
    for key, f in NEW_FIELDS.items():
        if key in fields:
            if fields[key].get("references") != f.get("references") or \
               fields[key].get("sql_column") != f["sql_column"]:
                fields[key] = f
                changed = True
                print(f"corrected {key}")
            continue
        # insert `id` before id2 (C++ struct order: id, id2, id3);
        # zoneId/areaId right after id for spatial grouping
        anchor = "id2" if key == "id" else None
        if anchor and anchor in fields:
            new_fields = {}
            for k, v in fields.items():
                if k == anchor:
                    new_fields[key] = f
                new_fields[k] = v
        else:
            new_fields = dict(fields)
            new_fields[key] = f
        fields.clear()
        fields.update(new_fields)
        changed = True
        print(f"added {key}")

    if not changed:
        print("no changes (entry already fixed)")
        return

    REG.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"saved; {ENTRY} now has {len(fields)} fields")


if __name__ == "__main__":
    main()
