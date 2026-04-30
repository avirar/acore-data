"""
Extract C++ field -> SQL column mappings from AzerothCore source code.

For sql_manager registry entries missing explicit sql_column mappings, this
script scans prepared statements and inline queries in the AzerothCore source,
then parses fields[N] assignments to build the mapping between:
  - SQL column names (from SELECT statements)  
  - C++ struct field names (from assignment targets)

Usage:
    python3 scripts/generate_sql_manager_mapping.py
    # Output: scripts/sql_manager_mapping.json

The output can be merged into datastore_registry.json by running:
    python3 scripts/merge_mappings.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ACORE_SRC = Path("/root/azerothcore-wotlk/src/server")
REGISTRY_PATH = Path("/root/acore-data/datastore_registry.json")
OUTPUT_PATH = Path("/root/acore-data/scripts/sql_manager_mapping.json")

# Key files
WORLD_DB_CPP = ACORE_SRC / "database" / "Database" / "Implementation" / "WorldDatabase.cpp"


def load_registry() -> Dict:
    return json.load(open(REGISTRY_PATH))


def get_entries_needing_mapping(registry: Dict) -> List[Tuple[str, Dict]]:
    """Find sql_manager entries where some/all fields lack explicit sql_column."""
    result = []
    for name, entry in registry.get("entries", {}).items():
        if entry.get("category") != "sql_manager":
            continue
        sql_table = entry.get("sql_table", "")
        fields = entry.get("fields", {})
        if not sql_table or not fields:
            continue
        has_missing = any(
            isinstance(fi, dict) and not (fi.get("sql_column") or "").strip()
            for fi in fields.values()
        )
        if has_missing:
            result.append((name, entry))
    return result


# ─── SQL Column Extraction ───────────────────────────────────────────────────

def extract_all_prepared_statements() -> Dict[str, List[str]]:
    """Extract ALL prepared statements from WorldDatabase.cpp.
    
    Returns: {sql_table_name: [col1, col2, ...]}
    """
    if not WORLD_DB_CPP.exists():
        print(f"[WARN] {WORLD_DB_CPP} not found", file=sys.stderr)
        return {}

    content = WORLD_DB_CPP.read_text()
    pattern = re.compile(
        r'PrepareStatement\(\s*\w+,\s*"SELECT\s+(.+?)\s+FROM\s+(`?)(\w+)\2',
        re.IGNORECASE
    )

    result = {}
    for match in pattern.finditer(content):
        columns_str = match.group(1)
        table_name = match.group(3).lower()
        columns = [c.strip().strip("`") for c in columns_str.split(",")]
        result[table_name] = columns

    return result


# Legacy table name aliases: registry uses modern names, loader may use old ones
TABLE_ALIASES = {
    "spell_proc_event": ["spell_proc"],
    "game_weather": ["weather"],
}


def extract_inline_query_columns(sql_table: str) -> Optional[List[str]]:
    """Search .cpp files for inline Query(SELECT ... FROM table) calls.
    
    Also tries known alias table names if exact match fails.
    Returns list of SQL column names or None if not found.
    """
    tables_to_try = [sql_table] + TABLE_ALIASES.get(sql_table, [])

    for tbl in tables_to_try:
        pattern = re.compile(
            rf'Query\(\s*"SELECT\s+(.+?)\s+FROM\s+(?:`)?{re.escape(tbl)}(?:`)?',
            re.IGNORECASE | re.DOTALL
        )

        for cpp_file in ACORE_SRC.glob("**/*.cpp"):
            try:
                content = cpp_file.read_text(errors="ignore")
            except Exception:
                continue
            match = pattern.search(content)
            if match:
                col_str = match.group(1).replace("\n", " ")
                return [c.strip().strip("`") for c in col_str.split(",")]

    return None


def get_sql_columns(sql_table: str, prep_stmts: Dict) -> Optional[List[str]]:
    """Get SQL column list for a table from prepared statements or inline queries.
    
    Also tries alias table names if exact match fails.
    """
    # Check prepared statements first (also try aliases)
    if sql_table in prep_stmts:
        return prep_stmts[sql_table]

    # Try aliases in prepared statements
    for alias in TABLE_ALIASES.get(sql_table, []):
        if alias in prep_stmts:
            return prep_stmts[alias]

    # Fallback: inline query search (slower)
    return extract_inline_query_columns(sql_table)


# ─── C++ Field Assignment Extraction ─────────────────────────────────────────

def find_loader_files(sql_table: str) -> List[Path]:
    """Find .cpp files that contain SQL queries referencing this table.

    Also searches for known alias table names.
    """
    tables_to_try = [sql_table] + TABLE_ALIASES.get(sql_table, [])

    # First try exact match patterns
    patterns = [
        rf'(?:Query|PreparedStatement|PrepareStatement).*{re.escape(tbl)}'
        for tbl in tables_to_try
    ]

    results = []
    seen_paths = set()

    for pat_str in patterns:
        pattern = re.compile(pat_str, re.IGNORECASE | re.DOTALL)

        for cpp_file in ACORE_SRC.glob("**/*.cpp"):
            cpp_path = str(cpp_file.resolve())
            if cpp_path in seen_paths:
                continue
            try:
                content = cpp_file.read_text(errors="ignore")
            except Exception:
                continue
            if pattern.search(content):
                results.append(cpp_file)
                seen_paths.add(cpp_path)

    return results


def extract_field_assignments(cpp_files: List[Path]) -> Dict[int, str]:
    """Extract fields[N] -> C++ field_name mappings from loader code.
    
    Pattern matches:
        temp.fieldName = fields[5].Get<T>()
        baseProcEntry.ProcsPerMinute = fields[12].Get<float>()
        entry.someField = fields[3].Get<uint32>()
    
    Returns: {N: "fieldName", ...}
    """
    assignments = {}

    # Direct assignment: variable.field = fields[N].Get<...>
    pattern_direct = re.compile(r'(\w+)\.(\w+)\s*=\s*fields\[(\d+)\]')

    for cpp_file in cpp_files:
        try:
            content = cpp_file.read_text(errors="ignore")
        except Exception:
            continue

        for match in pattern_direct.finditer(content):
            _obj = match.group(1)  # e.g., temp, baseProcEntry
            field_name = match.group(2)  # e.g., ProcsPerMinute
            index = int(match.group(3))
            assignments[index] = field_name

    return assignments


# ─── Mapping Builder ────────────────────────────────────────────────────────

def build_mapping_for_entry(
    entry_name: str, entry_data: Dict, prep_stmts: Dict[str, List[str]]
) -> Optional[Dict]:
    """Build sql_column mapping for one registry entry.
    
    Returns new fields dict with updated mappings, or None if skipped.
    """
    sql_table = entry_data.get("sql_table", "")
    fields = entry_data.get("fields", {})
    if not sql_table:
        return None

    # Step 1: Get SQL columns
    sql_columns = get_sql_columns(sql_table, prep_stmts)
    if not sql_columns:
        print(f"  [SKIP] No SQL source found for '{sql_table}'", file=sys.stderr)
        return None

    # Step 2: Find loader files and extract assignments
    loader_files = find_loader_files(sql_table)
    cpp_assignments = extract_field_assignments(loader_files) if loader_files else {}

    # Step 3: Build new field mappings
    new_fields = {}
    added_count = 0

    for field_key, field_info in fields.items():
        if not isinstance(field_info, dict):
            new_fields[field_key] = field_info
            continue

        existing_sql = (field_info.get("sql_column") or "").strip()
        cpp_name = (field_info.get("name") or "").strip()

        # Already has mapping - keep as is
        if existing_sql:
            new_fields[field_key] = field_info
            continue

        # Try to find the C++ field in assignments and resolve SQL column
        resolved_col = _resolve_column(cpp_name, cpp_assignments, sql_columns, field_key)

        if resolved_col:
            new_info = dict(field_info)
            new_info["sql_column"] = resolved_col
            new_fields[field_key] = new_info
            added_count += 1
        else:
            # Try direct SQL column name match (field key might already be the SQL col)
            fk_lower = field_key.lower()
            for sc in sql_columns:
                if fk_lower == sc.lower():
                    new_info = dict(field_info)
                    new_info["sql_column"] = sc
                    new_fields[field_key] = new_info
                    added_count += 1
                    break
            else:
                new_fields[field_key] = field_info

    return {"fields": new_fields, "added": added_count}


def _resolve_column(
    cpp_name: str, cpp_assignments: Dict[int, str], sql_columns: List[str], field_key: str
) -> Optional[str]:
    """Try to resolve a C++ field name to its SQL column via index mapping."""
    if not cpp_name:
        return None

    # Direct match: look for the C++ field in assignments
    for idx, assigned_field in cpp_assignments.items():
        if cpp_name.lower() == assigned_field.lower():
            if 0 <= idx < len(sql_columns):
                return sql_columns[idx]

    # Fuzzy: check if any SQL column matches by name similarity
    for sc in sql_columns:
        if _names_similar(cpp_name, sc):
            return sc

    # Field key might be the C++ name itself (some registries use C++ name as key)
    fk_lower = field_key.lower()
    for idx, assigned_field in cpp_assignments.items():
        if fk_lower == assigned_field.lower():
            if 0 <= idx < len(sql_columns):
                return sql_columns[idx]

    return None


def _names_similar(a: str, b: str) -> bool:
    """Check if two names are similar enough (case-insensitive + common transforms)."""
    a_lower = a.lower()
    b_lower = b.lower()

    # Direct match
    if a_lower == b_lower:
        return True

    # Common camelCase <-> snake_case transform
    import re as re_mod
    snake_a = re_mod.sub(r'(?<!^)(?=[A-Z])', '_', a).lower()
    camel_b = ''.join(w.capitalize() for w in b_lower.split('_'))

    if snake_a == b_lower or a_lower == camel_b.lower():
        return True

    # Strip common prefixes/suffixes
    for strip_a in ['m_', '_m', 'the']:
        if a_lower.startswith(strip_a):
            if a_lower[len(strip_a):] == b_lower:
                return True

    return False


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    registry = load_registry()
    entries = get_entries_needing_mapping(registry)

    print(f"[1/3] Found {len(entries)} sql_manager entries needing mapping", file=sys.stderr)

    # Extract prepared statements (one-time, reused for all entries)
    prep_stmts = extract_all_prepared_statements()
    print(f"[2/3] Loaded {len(prep_stmts)} prepared statement definitions", file=sys.stderr)

    output = {"_meta": {
        "generated_by": "generate_sql_manager_mapping.py",
        "prep_statement_count": len(prep_stmts),
    }}

    total_added = 0
    total_processed = 0
    skipped = 0

    for entry_name, entry_data in entries:
        sql_table = entry_data.get("sql_table", "")
        missing_before = sum(
            1 for fi in entry_data["fields"].values()
            if isinstance(fi, dict) and not (fi.get("sql_column") or "").strip()
        )

        print(f"\n[{total_processed+1}/{len(entries)}] {entry_name} "
              f"(table: {sql_table}, {missing_before} missing)", file=sys.stderr)

        result = build_mapping_for_entry(entry_name, entry_data, prep_stmts)

        if not result:
            skipped += 1
            continue

        added = result["added"]
        new_fields = result["fields"]

        # Count remaining missing after mapping
        missing_after = sum(
            1 for fi in new_fields.values()
            if isinstance(fi, dict) and not (fi.get("sql_column") or "").strip()
        )

        total_processed += 1
        total_added += added

        if added > 0:
            output[entry_name] = {
                "sql_table": sql_table,
                "fields": new_fields,
            }
            print(f"  +{added} mappings (remaining: {missing_after})", file=sys.stderr)
        else:
            print(f"  No change", file=sys.stderr)

    # Write output
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\n[3/3] Wrote results to {OUTPUT_PATH}", file=sys.stderr)
    print(f"     Processed: {total_processed}/{len(entries)}")
    print(f"     Mappings added: {total_added}")
    print(f"     Skipped (no SQL source): {skipped}", file=sys.stderr)

    return total_added


if __name__ == "__main__":
    sys.exit(0 if main() > 0 else 1)
