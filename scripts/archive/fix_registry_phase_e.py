#!/usr/bin/env python3
"""
Phase E: remove phantom DBC fields whose index exceeds the DBC file's real
field_count (confirmed: DBC header field_count == DBCfmt.h format field_count).

  EmotesTextEntry.19          (_padding)             EmotesText field_count=19
  RandomPropertiesPointsEntry.16 (UncommonPropertiesPoints[4])  RandPropPoints field_count=16
  TaxiNodesEntry.24          (MountCreatureID[1])   TaxiNodes field_count=24

These fields cannot be parsed (out of range) and are not present in the DBC,
so they are removed from the registry.
"""
import json, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REG_PATH = ROOT / "datastore_registry.json"
reg = json.loads(REG_PATH.read_text())
E = reg["entries"]

# (entry, index_str) to delete, with the expected field name for safety
REMOVE = [
    ("EmotesTextEntry", "19", "_padding"),
    ("RandomPropertiesPointsEntry", "16", "UncommonPropertiesPoints[4]"),
    ("TaxiNodesEntry", "24", "MountCreatureID[1]"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from core.formats import FormatParser
    from core.dbc import WDBCReader
    import struct, os

    fmt = FormatParser("/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h")
    DBC = "/root/azerothcore-wotlk/env/dist/bin/dbc"

    done, skip = [], []
    for entry, idx_s, expect_name in REMOVE:
        e = E.get(entry)
        if e is None:
            skip.append((entry, "entry missing")); continue
        f = e["fields"].get(idx_s)
        if f is None:
            skip.append((entry, idx_s, "field missing")); continue
        if f.get("name") != expect_name:
            skip.append((entry, idx_s, f"name mismatch: {f.get('name')}")); continue
        # verify out-of-range against the DBC header field_count
        dbcfile = e.get("dbc_name")
        p = os.path.join(DBC, f"{dbcfile}.dbc")
        if os.path.exists(p):
            with open(p, "rb") as fh:
                data = fh.read(24)
            rec, fcount = struct.unpack_from("<II", data, 4)
        else:
            fcount = len(fmt.get_format(dbcfile) or [])
        if int(idx_s) < fcount:
            skip.append((entry, idx_s, f"NOT out of range (fcount={fcount})")); continue
        if a.apply:
            del e["fields"][idx_s]
        done.append((entry, idx_s, expect_name, fcount))

    print("=" * 56)
    print(f"PHASE E {'APPLIED' if a.apply else '(dry-run)'}")
    print("=" * 56)
    for d in done:
        print(f"  remove {d[0]}.{d[1]} ({d[2]})  [dbc_field_count={d[3]}]")
    for s in skip:
        print("  SKIP", s)
    if a.apply and not skip:
        REG_PATH.write_text(json.dumps(reg, indent=2) + "\n")
        print(f"\n[Wrote {REG_PATH}]")


if __name__ == "__main__":
    main()
