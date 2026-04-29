#!/usr/bin/env python3
"""
Generate datastore_registry.json from the docs/datastores markdown documentation.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any


# Fix for portable location relative to generators/ subdirectory
DOCS_DIR = Path(__file__).parent.parent / "docs" / "datastores"


def _meta(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def _col_range(s: str) -> List[int]:
    s = s.strip().rstrip('.')
    if not s or s == '-':
        return []
    m = re.match(r'(\d+)\s*-\s*(\d+)', s)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    m = re.match(r'(\d+)', s)
    return [int(m.group(1))] if m else []


def _parse_table_rows(section: str) -> List[List[str]]:
    """Extract all data rows from markdown tables in a section."""
    rows = []
    in_table = False
    for line in section.split('\n'):
        line = line.strip()
        if '|' in line and re.search(r'\|[-:]+', line):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith('|'):
            in_table = False
            continue
        cells = [c.strip() for c in line.split('|')]
        # filter empties from leading/trailing pipes
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        # skip header rows
        if cells and cells[0] in ('DBC Col', 'SQL Column', 'Field', 'SQL Column (COALESCE)'):
            continue
        # skip separator rows
        if all(re.match(r'^[-: ]*$', c) for c in cells):
            continue
        rows.append(cells)
    return rows


def parse_dbc_backed() -> Dict[str, Any]:
    content = (DOCS_DIR / "dbc-backed-stores.md").read_text()
    entries = {}

    for section in re.split(r'\n## ', content):
        header = section.split('\n')[0].strip()
        if not header.endswith('Entry'):
            continue

        dbc_file = _meta(section, r'DBC File:\*\*\s*`?([^`\n]+)`?')
        if not dbc_file:
            continue

        sql_table = _meta(section, r'SQL Table:\*\*\s*`?([^`\n]+)`?') or ""
        store_raw = _meta(section, r'Store:\*\*\s*`([^`]+)`') or ""
        fmt_var = _meta(section, r'Format:\*\*\s*`([^`]+)`') or ""

        store_var = store_raw.split(' ')[0] if store_raw else ""
        store_type = ""
        m = re.search(r'\(([^)]+)\)', store_raw)
        if m:
            store_type = m.group(1)

        fields = {}
        for cells in _parse_table_rows(section):
            if len(cells) < 4:
                continue
            col_str, sql_col, cpp_type, field_name = cells[0], cells[1], cells[2], cells[3]
            notes = cells[4] if len(cells) > 4 else ""
            if not field_name or field_name == 'Field Name':
                continue

            indices = _col_range(col_str)
            for idx in indices:
                arr_idx = idx - indices[0] if len(indices) > 1 else -1
                base_name = re.sub(r'\[0\.\.\d+\]', '', field_name)
                if len(indices) > 1 and arr_idx >= 0:
                    dname = f"{base_name}[{arr_idx}]"
                elif '[0]' in field_name:
                    dname = field_name
                else:
                    dname = field_name

                fields[str(idx)] = {
                    "name": dname,
                    "type": cpp_type,
                    "sql_column": sql_col,
                    "notes": notes
                }

        entries[header] = {
            "category": "dbc_backed",
            "dbc_file": dbc_file,
            "dbc_name": dbc_file.replace('.dbc', ''),
            "sql_table": sql_table,
            "sql_database": "db_world",
            "store_variable": store_var,
            "store_type": store_type,
            "format_variable": fmt_var,
            "header_file": "src/server/shared/DataStores/DBCStructure.h",
            "c_struct": header,
            "fields": fields
        }

    return entries


def _parse_manager_fields(section: str) -> Dict[str, Any]:
    """Parse fields from a manager sub-section, handling both table formats."""
    fields = {}
    for cells in _parse_table_rows(section):
        if len(cells) < 2:
            continue

        # Detect table format:
        # "SQL Column | C++ Type | Field Name | Notes" (4+ cols, first looks like SQL col)
        if len(cells) >= 3 and re.match(r'^[a-z_]', cells[0]):
            sql_col = cells[0]
            cpp_type = cells[1]
            field_name = cells[2]
            notes = cells[3] if len(cells) > 3 else ""
            skip_vals = {'*(WHERE clause)*', '*(not loaded)*'}
            if sql_col in skip_vals or sql_col.startswith('*('):
                continue
            fields[sql_col] = {
                "name": field_name,
                "type": cpp_type,
                "sql_column": sql_col,
                "notes": notes
            }
        else:
            # "Field | C++ Type" format
            field_name = cells[0]
            cpp_type = cells[1] if len(cells) > 1 else ""
            notes = cells[2] if len(cells) > 2 else ""
            if field_name and not field_name.startswith('*('):
                fields[field_name] = {
                    "name": field_name,
                    "type": cpp_type,
                    "notes": notes
                }

    return fields


SKIP_OBJMGR_HEADERS = {
    'SQL-Only Datastores (ObjectMgr)', 'Locale Stores',
    'Faction Change Stores', 'Trainer Stores', 'Fishing',
    'Reserved/Profanity Names'
}

SQL_TABLE_PATTERNS = [
    r'\*\*SQL Table[s]?:\*\*\s*`([^`]+)`',
    r'\*\*SQL Tables:\*\*\s*`([^`]+)`',
]


def parse_sql_objectmgr() -> Dict[str, Any]:
    content = (DOCS_DIR / "sql-objectmgr-stores.md").read_text()
    entries = {}

    for section in re.split(r'\n## ', content):
        header = section.split('\n')[0].strip()
        if header in SKIP_OBJMGR_HEADERS or header.startswith('Table of Contents') or header.startswith('#'):
            continue

        sql_table_raw = None
        for pat in SQL_TABLE_PATTERNS:
            sql_table_raw = _meta(section, pat)
            if sql_table_raw:
                break

        struct_line = _meta(section, r'Struct:\*\*\s*(.+)')
        store_info = _meta(section, r'Store:\*\*\s*`([^`]+)`')
        loader_info = _meta(section, r'Loader:\*\*\s*`([^`]+)`')

        if not sql_table_raw and not store_info:
            continue

        sql_table = sql_table_raw.split()[0].rstrip('(') if sql_table_raw else ""

        c_struct = ""
        header_file = ""
        if struct_line:
            first_bt = re.search(r'`([^`]+)`', struct_line)
            if first_bt:
                raw = first_bt.group(1)
                m = re.match(r'(\w+)', raw)
                if m:
                    c_struct = m.group(1)
                hf = re.search(r'\(([^)]+)\)', raw)
                if hf:
                    header_file = hf.group(1)
            if not header_file:
                hf = re.search(r'\(`([^`]+)`\)', struct_line)
                if hf:
                    header_file = hf.group(1)
            if not header_file:
                hf = re.search(r'\(([^)]+\.h)\)', struct_line)
                if hf:
                    header_file = hf.group(1).strip()

        store_var = ""
        container_type = ""
        if store_info:
            parts = store_info.split('(')
            store_var = parts[0].strip()
            if len(parts) > 1:
                container_type = parts[-1].rstrip(')').strip()

        loader_func = ""
        if loader_info:
            m = re.match(r'([\w:]+\(\))', loader_info)
            if m:
                loader_func = m.group(1)

        fields = {}
        for cells in _parse_table_rows(section):
            if len(cells) < 3:
                continue
            sql_col = cells[0]
            cpp_type = cells[1] if len(cells) > 1 else ""
            field_name = cells[2] if len(cells) > 2 else sql_col
            notes = cells[3] if len(cells) > 3 else ""

            skip_vals = {
                '*(WHERE clause)*', '*(not loaded)*', '*(grouping)*', '*(ordering)*',
                '*(selects store)*', '*(lookup key)*', '*(determines HighGuid)*',
                '*(FK to groups)*', '*(find Group)*', '*(passed to LoadMemberFromDB)*',
                '*(links to InstanceSave)*', '*(from item_instance join)*', '*(not loaded)',
            }
            if not sql_col or sql_col in skip_vals or sql_col.startswith('*('):
                continue

            fields[sql_col] = {
                "name": field_name,
                "type": cpp_type,
                "sql_column": sql_col,
                "notes": notes
            }

        if not c_struct:
            c_struct = header.replace(' ', '')

        entries[c_struct] = {
            "category": "sql_objectmgr",
            "sql_table": sql_table,
            "sql_database": "db_world",
            "store_variable": store_var,
            "store_type": container_type,
            "container_type": container_type,
            "loader_function": loader_func,
            "header_file": header_file,
            "c_struct": c_struct,
            "fields": fields
        }

    return entries


def parse_sql_managers() -> Dict[str, Any]:
    content = (DOCS_DIR / "sql-manager-stores.md").read_text()
    entries = {}

    # Split by numbered manager sections
    parts = re.split(r'\n##\s+\d+\.\s+', content)
    # parts[0] is the header, rest are manager sections

    for part in parts[1:]:
        lines = part.split('\n')
        first_line = lines[0].strip()

        # Parse manager header: "SpellMgr (sSpellMgr)" or "ItemEnchantmentMgr (standalone)"
        m = re.match(r'(\w+)\s*(?:\((\w+)\))?', first_line)
        if not m:
            continue
        mgr_class = m.group(1)
        mgr_singleton = m.group(2) or ""

        # Extract header/source info
        header_file = _meta(part, r'Header:\*\*\s*`([^`]+)`') or ""

        # Find sub-entries by splitting on both ### and ####
        # Some managers use ### for entries, others use #### within ### Stores
        sub_parts = re.split(r'\n####?\s+', part)

        for sub in sub_parts[1:]:  # skip manager overview
            sub_header = sub.split('\n')[0].strip()

            # Skip "Stores", "Load Functions", "Load Function" etc
            if sub_header.lower() in ('stores', 'load functions', 'load function',
                                       'additional tables', 'loaders:', 'sub-struct'):
                continue

            # Parse "SpellProcEntry -- `spell_proc_event`"
            # or "LootStoreItem" (no SQL table in header)
            # or "Random Enchantment Data -- `item_enchantment_template`"
            m2 = re.match(r'([\w\s]+?)\s*(?:--\s*`?([^`\n]+)`?)?$', sub_header)
            if not m2:
                continue

            c_struct_raw = m2.group(1).strip()
            c_struct = c_struct_raw.replace(' ', '')
            sql_table = m2.group(2).strip().rstrip('`') if m2.group(2) else ""

            # Handle SQL tables with "+" like "waypoint_data` + `waypoint_data_addon"
            # Just take the first table
            if '` + `' in sql_table:
                sql_table = sql_table.split('` + `')[0].strip()

            # Handle "(Login DB)" annotations
            sql_database = "db_world"
            if 'Login DB' in sub_header or '(Login DB)' in sub:
                sql_database = "db_auth"
            elif 'characters DB' in sub_header or 'Characters DB' in sub:
                sql_database = "db_characters"

            # Extract container
            container_m = re.search(r'Container:\*\*\s*`([^`]+)`', sub)
            container_type = container_m.group(1) if container_m else ""

            # Parse fields (handles both table formats)
            fields = _parse_manager_fields(sub)

            entries[c_struct] = {
                "category": "sql_manager",
                "sql_table": sql_table,
                "sql_database": sql_database,
                "manager_singleton": mgr_singleton,
                "manager_class": mgr_class,
                "store_variable": container_type,
                "container_type": container_type,
                "header_file": header_file,
                "c_struct": c_struct,
                "fields": fields
            }

    return entries


def build_indices(registry: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    indices = {
        "by_struct_name": {},
        "by_sql_table": {},
        "by_dbc_file": {},
        "by_dbc_name": {},
        "by_store_variable": {}
    }

    for struct_name, entry in registry.items():
        indices["by_struct_name"][struct_name] = struct_name

        if entry.get("sql_table"):
            indices["by_sql_table"][entry["sql_table"]] = struct_name

        if entry.get("dbc_file"):
            indices["by_dbc_file"][entry["dbc_file"]] = struct_name

        if entry.get("dbc_name"):
            indices["by_dbc_name"][entry["dbc_name"]] = struct_name

        sv = entry.get("store_variable", "")
        if sv:
            sv_clean = sv.split('(')[0].strip()
            if sv_clean:
                indices["by_store_variable"][sv_clean] = struct_name

    return indices


def main():
    print("Generating datastore_registry.json from docs/datastores/...")

    dbc = parse_dbc_backed()
    print(f"  DBC-backed: {len(dbc)} entries")

    obj = parse_sql_objectmgr()
    print(f"  SQL ObjectMgr: {len(obj)} entries")

    mgr = parse_sql_managers()
    print(f"  SQL Manager: {len(mgr)} entries")

    registry = {}
    registry.update(dbc)
    registry.update(obj)
    registry.update(mgr)

    indices = build_indices(registry)

    output = {
        "_meta": {
            "description": "AzerothCore datastore registry",
            "source": "Generated from docs/datastores/ documentation",
            "categories": ["dbc_backed", "sql_objectmgr", "sql_manager"],
            "total_entries": len(registry)
        },
        "entries": registry,
        "indices": indices
    }

    out_path = Path(__file__).parent.parent / "datastore_registry.json"
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    total_fields = sum(len(e.get("fields", {})) for e in registry.values())
    print(f"\n  Total: {len(registry)} entries, {total_fields} field mappings")
    print(f"  Written to {out_path}")

    # Category breakdown
    for cat in ["dbc_backed", "sql_objectmgr", "sql_manager"]:
        count = sum(1 for e in registry.values() if e["category"] == cat)
        print(f"    {cat}: {count}")


if __name__ == "__main__":
    main()
