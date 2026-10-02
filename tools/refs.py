"""
Reverse-reference tool for acore-data.

Finds which rows in OTHER tables reference a given record (data-level reverse
lookup driven by the registry's `referenced_by` metadata). Answers questions
like "which items use spell 40230" (refs(name='Spell', id=40230)) in one call
instead of hand-written cross-table SQL.
"""

from typing import Dict, Any, List, Optional
import re


def get_schema() -> Dict[str, Any]:
    """Return the JSON-RPC tool schema for the refs tool."""
    return {
        "name": "refs",
        "description": (
            "Reverse lookup: find rows in other tables that reference a given record. "
            "Uses the registry's referenced_by metadata to scan SQL tables for rows whose "
            "foreign-key field(s) equal `id`. E.g. refs(name='Spell', id=40230) lists the "
            "items/enchants/procs that use spell 40230. For item targets, loot sources "
            "(creature/gameobject/etc. loot tables) are resolved both directly (Item=id) "
            "and indirectly through shared reference_loot_template entries (Reference=…). "
            "Optional `source` restricts to one referencing table/struct. Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Datastore being referenced (DBC file, SQL table, or struct), e.g. 'Spell', 'ItemTemplate'.",
                },
                "id": {
                    "type": "number",
                    "description": "The record's primary-key value to find references to.",
                },
                "source": {
                    "type": "string",
                    "description": "Optional: restrict to one referencing source (struct name or sql_table), e.g. 'ItemTemplate' or 'item_template'.",
                },
                "limit": {
                    "type": "number",
                    "description": "Max referencing rows to return per source (default 20, max 100).",
                },
            },
            "required": ["name", "id"],
        },
    }


def _expand_field_spec(source_entry: Dict, field_spec: str) -> List[str]:
    """Expand a `referenced_by` field spec into candidate SQL column names.

    Handles the notations emitted by the registry:
      - comma lists:        "RequiredSpell, spellclickspellspecifier, socketspell"
      - dot ranges:         "spellid_1..5", "spell1..8", "RequiredItemId1..6"
      - bracket ranges:     "SpellId[0..3]" -> "SpellId_1".."SpellId_4" (slot suffix)
    """
    fields = source_entry.get("fields", {})
    name_to_col: Dict[str, str] = {}
    for fkey, finfo in fields.items():
        if not isinstance(finfo, dict):
            continue
        sql_col = finfo.get("sql_column", "")
        name = finfo.get("name", "")
        if sql_col:
            name_to_col[fkey] = sql_col
            name_to_col[name] = sql_col

    candidates: List[str] = []
    for part in field_spec.split(","):
        part = part.strip()
        if not part:
            continue

        # Bracket range: Name[0..2] -> Name_1..Name_3 (SQL overlay slot suffix)
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\.\.(\d+)\]$", part)
        if m:
            base, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            for i in range(start, end + 1):
                candidates.append(f"{base}_{i + 1}")
            continue

        # Dot range: col1..5 (extract the trailing digits as the start index)
        m = re.match(r"^(.+?)\.\.(\d+)$", part)
        if m:
            base, end = m.group(1), int(m.group(2))
            m2 = re.match(r"^(.*?)(\d+)$", base)
            if m2:
                prefix, start = m2.group(1), int(m2.group(2))
                for i in range(start, end + 1):
                    candidates.append(f"{prefix}{i}")
            else:
                candidates.append(base)
            continue

        # Single field: map C field name -> sql column when known
        col = name_to_col.get(part)
        if col and ".." not in col:
            candidates.append(col)
        else:
            candidates.append(part)

    return candidates


def _map_to_real_columns(candidates: List[str], schema_columns: List[str]) -> List[str]:
    """Filter candidate columns down to those that actually exist in the table."""
    real = {c.lower() for c in schema_columns}
    out: List[str] = []
    seen = set()
    for c in candidates:
        low = c.lower()
        if low in real and low not in seen:
            out.append(c)
            seen.add(low)
    return out


def refs_tools(server) -> Dict[str, Any]:
    """Find rows referencing a given record via the registry's referenced_by metadata."""
    name = server.args.get("name")
    rid = server.args.get("id")
    source_filter = server.args.get("source")
    try:
        limit = int(server.args.get("limit", 20) or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 100))

    if not name or rid is None:
        return {
            "error": "refs: usage: refs(name='<datastore>', id=<value>[, source='<table>'][, limit=N])",
            "isError": True,
        }

    resolved = server.registry._resolve_entry(str(name))
    if not resolved:
        return {"error": f"refs: unknown datastore '{name}'", "isError": True}
    struct_name, entry = resolved

    referenced_by = [
        rb for rb in entry.get("referenced_by", []) if rb.get("field") and rb.get("source")
    ]
    if not referenced_by:
        return {
            "error": f"refs: '{struct_name}' has no registered referencing sources",
            "isError": True,
        }

    target_value = int(rid)

    results: List[Dict[str, Any]] = []
    skipped: List[str] = []
    scanned_empty: List[str] = []
    loot_sources: List[tuple] = []  # (src_name, sql_table, db_name) with a `Reference` column

    for rb in referenced_by:
        src_name = rb["source"]
        src_resolved = server.registry._resolve_entry(src_name)
        if not src_resolved:
            skipped.append(f"{src_name}: unknown source")
            continue
        _, src_entry = src_resolved
        sql_table = src_entry.get("sql_table", "")

        # Optional single-source restriction (match struct name or sql table).
        if source_filter:
            fl = str(source_filter).lower()
            if fl not in (src_name.lower(), sql_table.lower()):
                continue

        category = src_entry.get("category", "")
        if not sql_table or not category.startswith("sql_"):
            skipped.append(f"{src_name}: not a SQL table (DBC-backed, skipped)")
            continue

        db_name = server.database._resolve_table_database(sql_table, server.database.db_name)
        if not db_name:
            skipped.append(f"{sql_table}: not found in any configured database")
            continue

        # Full column list (INFORMATION_SCHEMA) — the shared schema cache truncates
        # at 50 columns, which would miss spellid_1..5 on wide tables like item_template.
        col_rows, col_err = server.database._query_database(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            params=(db_name, sql_table),
        )
        if col_err or not col_rows:
            skipped.append(f"{sql_table}: no schema info")
            continue
        schema_cols = [r.get("COLUMN_NAME", "") for r in col_rows]

        # Loot tables (and only loot tables here) carry a `Reference` column that
        # points into a shared reference_loot_template — tracked for 2-level
        # indirect resolution below.
        is_loot = "reference" in {c.lower() for c in schema_cols}
        if is_loot:
            loot_sources.append((src_name, sql_table, db_name))

        candidates = _expand_field_spec(src_entry, rb["field"])
        columns = _map_to_real_columns(candidates, schema_cols)
        if not columns:
            skipped.append(f"{src_name}.{rb['field']}: no matching columns in {sql_table}")
            continue

        if is_loot and columns == ["Item"]:
            # Loot rows with Reference != 0 are indirect (their Item value is a
            # placeholder); a true direct drop has Reference = 0.
            query = f"SELECT * FROM `{sql_table}` WHERE `Item` = %s AND `Reference` = 0 LIMIT {limit}"
            params = (target_value,)
        else:
            or_clause = " OR ".join([f"`{c}` = %s" for c in columns])
            query = f"SELECT * FROM `{sql_table}` WHERE {or_clause} LIMIT {limit}"
            params = tuple([target_value] * len(columns))
        rows, err = server.database._query_database(query, db_name=db_name, params=params)
        if err:
            skipped.append(f"{sql_table}: {err}")
            continue

        if rows:
            results.append(
                {
                    "source": src_name,
                    "table": sql_table,
                    "db": db_name,
                    "matched_columns": columns,
                    "count": len(rows),
                    "rows": rows,
                }
            )
        else:
            scanned_empty.append(f"{src_name}({sql_table})")

    # Loot reference-template expansion (2-level): an item may live only in a
    # shared reference_loot_template; source loot tables reach it via their
    # `Reference` column. Resolve those indirect droppers.
    if loot_sources:
        ref_db = server.database._resolve_table_database("reference_loot_template", server.database.db_name) or server.database.db_name
        ref_rows, ref_err = server.database._query_database(
            "SELECT Entry FROM reference_loot_template WHERE Item = %s",
            db_name=ref_db, params=(target_value,))
        if not ref_err and ref_rows:
            ref_ids = [r["Entry"] for r in ref_rows]
            placeholders = ",".join(["%s"] * len(ref_ids))
            for src_name, sql_table, db_name in loot_sources:
                if sql_table == "reference_loot_template":
                    continue
                rows, err = server.database._query_database(
                    f"SELECT * FROM `{sql_table}` WHERE `Reference` IN ({placeholders}) LIMIT {limit}",
                    db_name=db_name, params=tuple(ref_ids))
                if err:
                    continue
                if rows:
                    results.append({
                        "source": src_name,
                        "table": sql_table,
                        "db": db_name,
                        "matched_columns": ["Reference"],
                        "via": f"reference_loot_template(Item={target_value})",
                        "count": len(rows),
                        "rows": rows,
                    })

    note = (
        f"Referencing rows for {struct_name} id {target_value}: "
        f"{sum(r['count'] for r in results)} found across {len(results)} table(s); "
        f"{len(scanned_empty)} table(s) scanned with no match; "
        f"{len(skipped)} source(s) skipped."
    )
    return {"result": results, "scanned_empty": scanned_empty, "skipped": skipped, "note": note}
