#!/usr/bin/env python3
"""
Triage sql_column drift precisely.

For each registry entry with a sql_table, compare every field's sql_column
against the LIVE table's full column set (uncapped). Categorises each mismatch:
  - ARRAY_FAMILY : sql_column encodes a range/family (spell1..8, name, locale)
                   -> not a real bug (represents multiple columns)
  - CAP_ARTIFACT : column exists beyond the 50-col cap the audit used
  - REAL_MISMATCH: a simple column name that genuinely does not exist
  - OVERLAY_SPARSE: dbc_backed entry; overlay table is a reduced subset

Writes a JSON triage + prints a summary.
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
reg = json.loads((ROOT / "datastore_registry.json").read_text())
E = reg["entries"]

from core.database import Database
db = Database(); db._auto_detect_db_config(); db._check_db_connection()

def full_columns(table):
    rows, _ = db._query_database(
        "SELECT COLUMN_NAME FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name=%s",
        params=(db._resolve_table_database(table, db.db_name) or db.db_name, table),
    )
    return {r["COLUMN_NAME"].lower() for r in rows}

# regexes for array/locale/family sql_columns
def is_family(sc):
    s = sc.lower()
    if re.search(r"\d\.\.\d", s):            # spell1..8, resistance1..7
        return True
    if re.search(r"\[\d+\]", s):             # bracket
        return True
    return False

def family_covers(sc, cols):
    """Does a family sql_column have at least one matching real column?"""
    m = re.match(r"^(.*?)\d*\.\.(\d+)$", sc.lower())
    if m:
        base, last = m.group(1), int(m.group(2))
        # try base0..baselast
        for i in range(last + 1):
            if f"{base}{i}".lower() in cols or f"{base}{i+1}".lower() in cols:
                return True
        return base.lower() in cols
    return False

triage = defaultdict(list)
table_cols = {}
for n, e in E.items():
    table = e.get("sql_table")
    if not table:
        continue
    if table not in table_cols:
        table_cols[table] = full_columns(table)
    cols = table_cols[table]
    if not cols:
        continue
    cat_entry = e.get("category", "")
    for k, f in e.get("fields", {}).items():
        sc = (f.get("sql_column") or "").strip()
        if not sc or sc.lower() in cols:
            continue
        if is_family(sc) or family_covers(sc, cols):
            triage["ARRAY_FAMILY"].append((n, k, sc))
        elif cat_entry == "dbc_backed":
            triage["OVERLAY_SPARSE"].append((n, k, sc, table))
        else:
            triage["REAL_MISMATCH"].append((n, k, sc, table))

print("=" * 66)
print("SQL_COLUMN DRIFT TRIAGE")
print("=" * 66)
for cat in ["REAL_MISMATCH", "ARRAY_FAMILY", "OVERLAY_SPARSE", "CAP_ARTIFACT"]:
    print(f"  {cat:16} {len(triage[cat])}")

print("\n=== REAL_MISMATCH (fixable bugs) by entry ===")
by = Counter(x[0] for x in triage["REAL_MISMATCH"])
for e_, c in by.most_common(60):
    print(f"  {e_:30} {c}")

print("\n=== SAMPLE REAL_MISMATCH (first 60) ===")
for n, k, sc, table in triage["REAL_MISMATCH"][:60]:
    print(f"  {n:26} {sc:24} table={table}")

(ROOT / "scripts" / "_drift_triage.json").write_text(json.dumps(
    {cat: [list(x) for x in v] for cat, v in triage.items()}, indent=2))
print("\n[triage written to scripts/_drift_triage.json]")
