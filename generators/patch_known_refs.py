#!/usr/bin/env python3
"""Patch known-wrong cross-reference annotations in datastore_registry.json.

These were produced by an archived heuristic (fix_registry_phase_b.py) that
mapped fields by name similarity instead of by what the data means:

  * TalentEntry.RankID[0..4] holds *spell ids* (the rank spells), so it
    references SpellEntry - not TalentEntry.
  * ItemSetEntry.spells[0..7] holds *spell ids* and references SpellEntry;
    ItemSetEntry.items_to_triggerspell[0..7] holds the number of set pieces
    needed to trigger the spell (a count), so it references nothing.

The patch also repairs the derived `referenced_by` arrays so the `refs`
tool / reverse lookups stay correct. Run with the repo venv:

    .venv/bin/python3 generators/patch_known_refs.py [--dry-run]

Follow up with generators/generate_referenced_by.py to refresh anything else.
"""

import json
import sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "datastore_registry.json"

SPELL_REF = {"references": "SpellEntry", "reference_type": "dbc_backed", "reference_column": "ID"}


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    registry = json.loads(REGISTRY_PATH.read_text())
    entries = registry["entries"]
    changes = []

    # --- forward references -------------------------------------------------
    talent = entries["TalentEntry"]
    for key, field in talent["fields"].items():
        if field.get("name", "").startswith("RankID[") and field.get("references") != "SpellEntry":
            field.update(SPELL_REF)
            changes.append(f"TalentEntry.fields[{key}] {field['name']} -> SpellEntry")

    item_set = entries["ItemSetEntry"]
    for key, field in item_set["fields"].items():
        name = field.get("name", "")
        if name.startswith("spells[") and field.get("references") != "SpellEntry":
            field.update(SPELL_REF)
            changes.append(f"ItemSetEntry.fields[{key}] {name} -> SpellEntry")
        elif name.startswith("items_to_triggerspell["):
            removed = [k for k in ("references", "reference_type", "reference_column") if k in field]
            for k in removed:
                field.pop(k)
            if removed:
                changes.append(f"ItemSetEntry.fields[{key}] {name} -> (count, no reference)")

    # --- derived reverse references ----------------------------------------
    spell_rb = entries["SpellEntry"].setdefault("referenced_by", [])
    for rb in spell_rb:
        if rb.get("source") == "ItemSetEntry" and "items_to_triggerspell" in rb.get("field", ""):
            rb["field"] = "spells[0..7]"
            changes.append("SpellEntry.referenced_by ItemSetEntry field -> spells[0..7]")
    if not any(rb.get("source") == "TalentEntry" for rb in spell_rb):
        spell_rb.append({"source": "TalentEntry", "field": "RankID[0..4]"})
        changes.append("SpellEntry.referenced_by += TalentEntry RankID[0..4]")

    talent_rb = entries["TalentEntry"].get("referenced_by", [])
    # Drop stale entries that point at TalentEntry via fields that are not talents.
    kept = [
        rb for rb in talent_rb
        if not (rb.get("source") == "TalentEntry" and "RankID" in rb.get("field", ""))
    ]
    if len(kept) != len(talent_rb):
        entries["TalentEntry"]["referenced_by"] = kept
        changes.append("TalentEntry.referenced_by -= RankID self-reference")

    if not changes:
        print("patch_known_refs: nothing to change (already patched)")
        return 0

    for c in changes:
        print(f"  {c}")
    if dry_run:
        print(f"patch_known_refs: dry run, {len(changes)} change(s) not written")
        return 0

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    print(f"patch_known_refs: wrote {len(changes)} change(s) to {REGISTRY_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
