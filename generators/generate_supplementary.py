#!/usr/bin/env python3
"""
Generate supplementary SQL tables for the datastore registry.

This script queries INFORMATION_SCHEMA to discover all tables in acore_world
that are NOT already in the registry, and adds them as "sql_auxiliary" entries.
These are supplementary tables (loot templates, quest supplements, etc.) that
are useful for LLM data linking but not loaded as datastores by ObjectMgr.
"""

import json
import os
import subprocess
from pathlib import Path

DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_USER = os.environ.get('DB_USER', 'acore')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'acore')
DB_NAME = os.environ.get('DB_NAME', 'acore_world')

# Tables to ignore (meta/admin/mod-specific/irrelevant)
IGNORED_TABLES = {
    # Meta/admin
    'updates', 'updates_include', 'version', 'command', 'acore_string',
    # Anti-cheat/mod-specific
    'antidos_opcode_policies',
    # Auction house bot mod
    'mod_auctionhousebot', 'mod_auctionhousebot_disabled_items', 'auctionhousebot_professionItems',
    # Deprecated/unused
    'waypoints', 'script_waypoint', 'event_scripts',
    'playerbots_rpg_races',
    # Locale tables (handled separately)
    '_locale',
}

def query_database(sql: str) -> list:
    """Execute SQL query and return rows as list of dicts."""
    cmd = [
        "mysql", "-h", DB_HOST, "-P", DB_PORT, "-u", DB_USER,
        f"-p{DB_PASSWORD}", "-D", DB_NAME, "--batch", "--skip-column-names",
        "-e", sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        print(f"Query error: {result.stderr}", file=__import__('sys').stderr)
        return []
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if line:
            rows.append(line.split('\t'))
    return rows

def get_all_tables() -> set:
    """Get all table names from the database."""
    sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{}' AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME".format(DB_NAME)
    rows = query_database(sql)
    return {r[0] for r in rows if r}

def get_table_columns(table_name: str) -> list:
    """Get column info for a table."""
    sql = "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{}' AND TABLE_NAME = '{}' ORDER BY ORDINAL_POSITION".format(DB_NAME, table_name)
    rows = query_database(sql)
    return rows

def load_registry() -> dict:
    """Load existing registry."""
    registry_file = Path(__file__).parent / "datastore_registry.json"
    if not registry_file.exists():
        return {"entries": {}, "indices": {}}
    with open(registry_file, 'r') as f:
        return json.load(f)

def save_registry(reg: dict):
    """Save registry to file."""
    registry_file = Path(__file__).parent / "datastore_registry.json"
    with open(registry_file, 'w') as f:
        json.dump(reg, f, indent=2)
    print(f"Saved registry with {len(reg['entries'])} entries")

def generate_supplementary_entries(all_tables: set, registry_tables: set) -> dict:
    """Generate entries for missing tables."""
    new_entries = {}
    
    # Find tables not in registry
    missing = all_tables - registry_tables
    
    for table_name in sorted(missing):
        # Skip ignored tables
        if any(ignored in table_name.lower() for ignored in IGNORED_TABLES):
            continue
        
        # Get columns
        columns = get_table_columns(table_name)
        if not columns:
            continue
        
        # Build fields dict (index -> field info)
        fields = {}
        for i, col in enumerate(columns):
            col_name, data_type, col_key, _ = col
            # Map MySQL types to simple types
            type_map = {
                'int': 'int32', 'bigint': 'int64', 'smallint': 'int32',
                'tinyint': 'int8', 'mediumint': 'int32',
                'decimal': 'float', 'float': 'float', 'double': 'float',
                'varchar': 'string', 'text': 'string', 'char': 'string',
                'datetime': 'timestamp', 'date': 'date', 'time': 'time',
                'blob': 'binary', 'binary': 'binary',
            }
            simple_type = type_map.get(data_type, data_type)
            fields[str(i)] = {
                "name": col_name,
                "type": simple_type,
                "sql_column": col_name,
            }
        
        # Create c_struct name (CamelCase from snake_case)
        parts = table_name.split('_')
        c_struct = ''.join(p.capitalize() for p in parts)
        
        new_entries[c_struct] = {
            "category": "sql_auxiliary",
            "sql_table": table_name,
            "sql_database": DB_NAME,
            "c_struct": c_struct,
            "fields": fields,
            "loader_function": "",
            "store_variable": "",
            "header_file": "",
            "container_type": "",
            "hints": {
                "loading": f"Supplementary table: {table_name}. Use lookup_datastore(query='{table_name}') to get column schema.",
                "access_pattern": f"Direct SQL query: SELECT * FROM {table_name}"
            }
        }
    
    return new_entries

def update_registry_indices(reg: dict):
    """Update lookup indices."""
    indices = reg.get("indices", {})
    
    # Rebuild indices for all entries
    indices["by_sql_table"] = {}
    indices["by_c_struct"] = {}
    
    for c_struct, entry in reg["entries"].items():
        sql_table = entry.get("sql_table", "")
        if sql_table:
            indices["by_sql_table"][sql_table] = c_struct
        indices["by_c_struct"][c_struct] = c_struct
    
    reg["indices"] = indices

def main():
    print("Generating supplementary table entries...")
    
    # Get all tables from DB
    all_tables = get_all_tables()
    print(f"Found {len(all_tables)} tables in database")
    
    # Load existing registry
    reg = load_registry()
    existing_count = len(reg.get("entries", {}))
    print(f"Registry currently has {existing_count} entries")
    
    # Get tables already in registry
    registry_tables = set()
    for entry in reg.get("entries", {}).values():
        t = entry.get("sql_table", "")
        if t:
            registry_tables.add(t.lower())
    
    # Generate new entries
    new_entries = generate_supplementary_entries(all_tables, registry_tables)
    print(f"Adding {len(new_entries)} new supplementary table entries")
    
    # Add to registry
    reg["entries"].update(new_entries)
    
    # Update indices
    update_registry_indices(reg)
    
    # Save
    save_registry(reg)
    
    print(f"\nRegistry now has {len(reg['entries'])} total entries")
    print(f"Added {len(new_entries)} new entries")
    
    # Print sample of new entries
    if new_entries:
        print("\nSample new entries:")
        for name in list(new_entries.keys())[:5]:
            entry = new_entries[name]
            print(f"  {name}: sql_table={entry['sql_table']}, fields={len(entry['fields'])}")

if __name__ == "__main__":
    main()
