#!/usr/bin/env python3
"""
Phase F: fix the remaining type-as-name defects that the Phase A sweep missed.

Phase A fixed fields whose `name` is a *primitive* type string (uint32, ...).
It missed fields whose `name` is a *custom* type string shared by several
distinct fields of that entry -- e.g. four GmTicket columns all named
"ObjectGuid", a quat's four components all named "G3D::Quat". Such a name is
a type, not a field identifier: the real identifier is the field key.

Rule: within one entry, if a PLAIN name (no `[...]` array/locale slot) is
shared by more than one field, that name is a type -> set name = field key
(field key is a proper identifier for these SQL entries).
"""
import json, re, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
REG_PATH = ROOT / "datastore_registry.json"
reg = json.loads(REG_PATH.read_text())
E = reg["entries"]

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def plain_name(name):
    """Return the name with array/locale slots stripped, or None if it has slots."""
    if re.search(r"\[\d", name):
        return None
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    fixed, skipped = [], []
    for n, e in E.items():
        fields = e.get("fields", {})
        groups = {}
        for k, f in fields.items():
            if not isinstance(f, dict):
                continue
            nm = f.get("name", "")
            pn = plain_name(nm)
            if pn is None:
                continue  # array/locale slot -> legit
            groups.setdefault(pn, []).append(k)
        for pn, keys in groups.items():
            if len(keys) < 2:
                continue
            for k in keys:
                # only fix if the field key is a proper identifier (not numeric DBC index)
                if not IDENT.match(k):
                    skipped.append((n, k, pn, "key not an identifier"))
                    continue
                old = e["fields"][k].get("name")
                if a.apply:
                    e["fields"][k]["name"] = k
                fixed.append((n, k, old, k))

    print("=" * 58)
    print(f"PHASE F {'APPLIED' if a.apply else '(dry-run)'}")
    print("=" * 58)
    print(f"  fixed type-as-name fields: {len(fixed)}")
    by = {}
    for n, k, old, new in fixed:
        by.setdefault(n, []).append(f"{k} ({old})")
    for n, l in by.items():
        print(f"   {n:28} {l}")
    print(f"  skipped (non-identifier key): {len(skipped)}")
    for s in skipped:
        print("     ??", s)
    if a.apply:
        REG_PATH.write_text(json.dumps(reg, indent=2) + "\n")
        print(f"\n[Wrote {REG_PATH}]  (skipped {len(skipped)} non-identifier key(s), left unchanged)")


if __name__ == "__main__":
    main()
