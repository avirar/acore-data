#!/usr/bin/env python3
"""
Phase D: fix the last 14 precise sql_column drift items found by the improved
audit (family families + cross-DB single columns).

  RENAME families : RewardItemId1..4 -> RewardItem1..4, etc.
  NONE families   : resistance1..7, spell1..8 (removed in AzerothCore)
  single cols     : matchMakerRating->personalRating, NameMD5->Name, etc.
"""
import json, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
REG_PATH = ROOT / "datastore_registry.json"
reg = json.loads(REG_PATH.read_text())
E = reg["entries"]

# (entry, field_key) -> new sql_column (or None)
FIX = {
    # family renames (real columns exist)
    ("Quest", "RewardItemId1..4"): "RewardItem1..4",
    ("Quest", "RewardFactionValueId1..5"): "RewardFactionValue1..5",
    ("Quest", "RewardFactionValueIdOverride1..5"): "RewardFactionOverride1..5",
    ("GroupData", "icon1-8"): "icon1..8",
    # removed families
    ("CreatureTemplate", "resistance1..7"): None,
    ("CreatureTemplate", "spell1..8"): None,
    ("Quest", "RewardChoiceItemCount1..6"): None,
    ("Quest", "RewardItemIdCount1..4"): None,
    # single columns
    ("ArenaTeamMembers", "matchMakerRating"): "personalRating",
    ("BannedAddons", "Name"): "Name",
    ("BannedAddons", "Version"): "Version",
    ("WardenCheckResult", "Result"): None,
    ("AuctionEntry", "item_template"): None,
    ("AuctionEntry", "itemCount"): None,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from core.database import Database
    db = Database(); db._auto_detect_db_config(); db._check_db_connection()
    db._discover_all_tables()
    done, missing, bad = [], [], []
    for (entry, fkey), new in FIX.items():
        e = E.get(entry)
        if e is None or fkey not in e.get("fields", {}):
            missing.append((entry, fkey)); continue
        if new is not None and ".." not in new:
            table = e.get("sql_table")
            d = db._resolve_table_database(table, db.db_name) or db.db_name
            rows, _ = db._query_database(
                "SELECT COLUMN_NAME FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s", params=(d, table))
            if new.lower() not in {r["COLUMN_NAME"].lower() for r in rows}:
                bad.append((entry, fkey, new, table)); continue
        e["fields"][fkey]["sql_column"] = new
        done.append((entry, fkey, new))

    print("=" * 56)
    print(f"PHASE D {'APPLIED' if a.apply else '(dry-run)'}")
    print("=" * 56)
    print(f"  applied: {len(done)}   missing: {len(missing)}   bad targets: {len(bad)}")
    for b in bad:
        print("    !!", b)
    for m in missing:
        print("    ??", m)
    if a.apply and not bad and not missing:
        REG_PATH.write_text(json.dumps(reg, indent=2) + "\n")
        print(f"\n[Wrote {REG_PATH}]")


if __name__ == "__main__":
    main()
