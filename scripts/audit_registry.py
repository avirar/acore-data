"""
Systematic registry audit for acore-data.

Checks every datastore entry (DBC + SQL + abstract C structs) for:
  1. dangling_refs        - `references` target that resolves to NO entry
  2. duplicate_identifiers- two fields with the same canonical id (Spell idx116 rule)
  3. type_as_name         - field name that is a raw C type string (known defect)
  4. missing_data_source  - sql_* entry with no sql_table / dbc_backed with no dbc
  5. dbc_index_drift      - registry field index outside the DBC format field count
  6. sql_column_drift     - sql_column not present in the live table (needs DB)
  7. missing_cross_refs   - FK-like field name with no `references` annotation (gap)

Usage:
  .venv/bin/python3 scripts/audit_registry.py [--db] [--json out.json]
"""
import json
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # allow `import core` when run as a script
REG = json.loads((ROOT / "datastore_registry.json").read_text())
E = REG["entries"]

# Canonical identifier of a field: strip array slots [n] and locale slots
def canon(name: str) -> str:
    # "EffectMiscValue[0]" -> "EffectMiscValue", "name[3]" -> "name"
    return re.sub(r"\[\d+\]$", "", name)

TYPE_STRINGS = {
    "uint8", "int8", "uint16", "int16", "uint32", "int32", "uint64", "int64",
    "float", "double", "char", "bool", "string", "std::string", "void",
    "byte", "short", "long", "size_t",
}


def resolve_target(target: str):
    """Return the struct name a references target resolves to, or None."""
    idx = REG.get("indices", {})
    if target in E:
        return target
    for key in ["by_sql_table", "by_dbc_name", "by_dbc_file", "by_store_variable", "by_struct_name"]:
        m = idx.get(key, {})
        if target in m:
            return m[target]
        # case-insensitive
        for k, v in m.items():
            if k.lower() == target.lower():
                return v
    # Entry suffix heuristic
    if target + "Entry" in E:
        return target + "Entry"
    return None


def fk_like(name: str) -> bool:
    """Heuristic: does this field name look like a foreign key to another store?"""
    n = name.lower()
    c = canon(n)
    # exact / suffix matches on known FK stems
    if re.fullmatch(r"(entry|id|mapid?|areaid?|zoneid?)", c):
        return True
    suffix_stems = [
        "id", "entry", "spell", "spellid", "item", "itemid", "creature",
        "creatureid", "map", "mapid", "area", "areaid", "zone", "zoneid",
        "object", "objectid", "objectguid", "npc", "npcid", "quest",
        "questid", "talent", "talentid", "skill", "skillid", "language",
        "lang", "faction", "factionid", "money", "condition", "lootid",
        "loottable", "spellname", "displayid", "emote", "emoteid", "sound",
        "soundid", "page", "pagetext", "pageid", "battleground", "dungeon",
        "instance", "instanceid", "vehicle", "areadata", "subarea", "page",
    ]
    for s in suffix_stems:
        if c.endswith(s) and len(c) > len(s):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", action="store_true", help="run live-DB checks (sql_column_drift)")
    ap.add_argument("--json", help="write full report to this JSON path")
    args = ap.parse_args()

    report = {c: [] for c in [
        "dangling_refs", "duplicate_identifiers", "type_as_name",
        "missing_data_source", "dbc_index_drift", "sql_column_drift",
        "missing_cross_refs",
    ]}

    # ---- 1. dangling refs ------------------------------------------------
    # ---- 2. duplicate identifiers ---------------------------------------
    # ---- 3. type-as-name -------------------------------------------------
    for n, e in E.items():
        for k, f in e.get("fields", {}).items():
            if not isinstance(f, dict):
                continue
            fname = f.get("name", "")
            refs = f.get("references")
            # 1
            if isinstance(refs, str):
                if refs != "self_ref" and not resolve_target(refs):
                    report["dangling_refs"].append(
                        {"entry": n, "field": k, "name": fname, "references": refs}
                    )
            # 3
            if canon(fname).lower() in TYPE_STRINGS and not (isinstance(refs, str) and refs):
                report["type_as_name"].append({"entry": n, "field": k, "name": fname})
        # 2: true duplicates = two fields with the IDENTICAL full name
        #    (case-insensitive, including array/locale slots). Legit arrays
        #    (name[0..15], additionalRequirements[2][0..3]) have distinct full
        #    names per slot, so they are not flagged.
        seen = defaultdict(list)
        for k, f in e.get("fields", {}).items():
            if isinstance(f, dict) and f.get("name"):
                seen[str(f["name"]).lower()].append(k)
        for cid, keys in seen.items():
            if len(keys) > 1:
                report["duplicate_identifiers"].append(
                    {"entry": n, "canon": cid, "field_keys": sorted(keys)}
                )
        # 4: missing data source (skip structs explicitly flagged in-memory only)
        if e.get("in_memory_only"):
            continue
        cat = e.get("category", "")
        if cat.startswith("sql_") and not e.get("sql_table"):
            report["missing_data_source"].append(
                {"entry": n, "category": cat, "c_struct": e.get("c_struct")}
            )
        if cat == "dbc_backed" and not (e.get("dbc_name") or e.get("dbc_file")):
            report["missing_data_source"].append(
                {"entry": n, "category": cat, "c_struct": e.get("c_struct")}
            )

    # ---- 5. DBC index drift --------------------------------------------
    try:
        from core.formats import FormatParser
        dbcfmt = str(ROOT / ".." / "azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h")
        # fall back to env
        import os
        dbcfmt = os.environ.get("DBC_FORMAT_FILE", dbcfmt)
        fp = FormatParser(dbcfmt)
        formats = fp.parse()
    except Exception as ex:
        formats = {}
        print(f"[warn] format parser unavailable: {ex}", file=sys.stderr)

    fmt_cache = {}
    for n, e in E.items():
        if e.get("category") != "dbc_backed":
            continue
        dbc = e.get("dbc_name", "")
        if not dbc:
            continue
        if dbc not in fmt_cache:
            fmt_cache[dbc] = fp.get_format(dbc) if formats else None
        fmt = fmt_cache[dbc]
        if not fmt:
            continue
        field_count = len(fmt)
        for k, f in e.get("fields", {}).items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                continue
            if idx >= field_count:
                report["dbc_index_drift"].append(
                    {"entry": n, "dbc": dbc, "field": k, "name": f.get("name"),
                     "index": idx, "format_field_count": field_count}
                )

    # ---- 6. sql column drift (DB) ---------------------------------------
    if args.db:
        # Precise drift check:
        #   - full (uncapped) column list, not the 50-row _get_table_schema
        #   - skip array/locale family sql_columns (spell1..8, name, [n])
        #   - skip dbc_backed entries (their sql_table is a sparse overlay, so
        #     missing columns are expected, not drift)
        #   - skip expression-based projections (COALESCE/aliases)
        try:
            from core.database import Database
            db = Database()
            db._auto_detect_db_config()
            db._check_db_connection()
            if db.db_available:
                db._discover_all_tables()  # populate _table_to_db_cache (cross-DB)

                def _full_cols(table):
                    d = db._resolve_table_database(table, db.db_name) or db.db_name
                    rows, _ = db._query_database(
                        "SELECT COLUMN_NAME FROM information_schema.columns "
                        "WHERE table_schema=%s AND table_name=%s", params=(d, table))
                    return {r["COLUMN_NAME"].lower() for r in rows}

                def _family_covers(sc, cols):
                    m = re.match(r"^(.*?)\d*\.\.(\d+)$", sc.lower())
                    if not m:
                        return False
                    base, last = m.group(1), int(m.group(2))
                    for i in range(last + 1):
                        if f"{base}{i}" in cols or f"{base}{i + 1}" in cols:
                            return True
                    return base in cols

                for n, e in E.items():
                    if not e.get("sql_table"):
                        continue
                    if e.get("category") == "dbc_backed":
                        continue  # sparse overlay; drift expected
                    table = e["sql_table"]
                    cols = _full_cols(table)
                    if not cols:
                        report["sql_column_drift"].append(
                            {"entry": n, "table": table, "issue": "TABLE_MISSING"}
                        )
                        continue
                    for k, f in e.get("fields", {}).items():
                        sc = (f.get("sql_column") or "").strip()
                        if not sc:
                            continue
                        # expression-based projections (COALESCE / cmo.X aliases)
                        if " " in sc or sc.upper().startswith("COALESCE"):
                            continue
                        low = sc.lower()
                        if re.search(r"\d\.\.\d", low):
                            # range family (spell1..8): covered if any slot exists
                            if _family_covers(sc, cols):
                                continue
                            report["sql_column_drift"].append(
                                {"entry": n, "table": table, "field": k,
                                 "name": f.get("name"), "sql_column": sc,
                                 "issue": "FAMILY_NOT_COVERED"})
                            continue
                        if "." in low and not re.search(r"\[\d", low):
                            continue  # qualified alias (cmo.SpawnId) -> not a plain column
                        if sc.lower() in cols:
                            continue
                        if _family_covers(sc, cols):
                            continue
                        report["sql_column_drift"].append(
                            {"entry": n, "table": table, "field": k,
                             "name": f.get("name"), "sql_column": sc})
        except Exception as ex:
            print(f"[warn] DB check failed: {ex}", file=sys.stderr)

    # ---- 7. missing cross-refs (heuristic gap) --------------------------
    for n, e in E.items():
        for k, f in e.get("fields", {}).items():
            if not isinstance(f, dict):
                continue
            fname = f.get("name", "") or f.get("sql_column", "")
            if not fname:
                continue
            if f.get("references"):
                continue
            # skip pure primary keys (field 0 / named id/entry at index 0)
            if k == "0":
                continue
            if fk_like(fname):
                report["missing_cross_refs"].append(
                    {"entry": n, "field": k, "name": fname}
                )

    # ---- summary --------------------------------------------------------
    print("=" * 70)
    print("ACORE-DATA REGISTRY AUDIT")
    print("=" * 70)
    for c in report:
        print(f"  {c:24} {len(report[c]):5}")
    print("-" * 70)

    # show a capped sample of each
    for c, items in report.items():
        if items:
            print(f"\n### {c} ({len(items)})")
            for it in items[:25]:
                print("   ", json.dumps(it))
            if len(items) > 25:
                print(f"    ... and {len(items)-25} more")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"summary": {c: len(v) for c, v in report.items()}, "report": report},
            indent=2,
        ))
        print(f"\n[report written to {args.json}]")


if __name__ == "__main__":
    main()
