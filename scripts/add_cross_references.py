#!/usr/bin/env python3
"""Add cross-reference metadata to fields in datastore_registry.json.

Phase 1: Auto-detect references from field naming conventions.
Fields matching patterns like 'spell_id', 'mapId', 'areaEntry' get
references/target entries mapped automatically.

Output: Updated datastore_registry.json with new metadata fields:
  - references: Target registry entry name (e.g., "SpellEntry")
  - reference_type: Auto-inferred from target category  
  - reference_column: Primary key column in target ("ID" default)
"""

import json
from collections import Counter


# Phase 1 prefix map: field prefix -> target registry entry
PREFIX_MAP = {
    # Skill/Spell
    "skill_line": "SkillLineEntry",
    "skill": "SkillLineEntry",
    "spell": "SpellEntry",
    "map": "MapEntry",
    
    # Areas/Zones
    "area": "AreaTableEntry",
    "areagroup": "AreaGroupEntry",
    
    # Items/Displays
    "item": "ItemEntry",
    "display": "ItemDisplayInfoEntry",
    
    # Living entities
    "creature": "CreatureEntry",
    "creatureentry": "CreatureEntry",
    
    # Game objects
    "gameobject": "GameObjectEntry",
    "gameobject_template": "GameObjectTemplate",
    
    # Quests
    "quest": "QuestEntry",
    "parent_quest": "QuestEntry",
    "prev_quest": "QuestEntry", 
    "next_quest": "QuestEntry",
    "required_quest": "QuestEntry",
    "prerequisite_quest": "QuestEntry",
    
    # Factions
    "faction": "FactionEntry",
    "faction_template": "FactionTemplateEntry",
    "factiontemplate": "FactionTemplateEntry",
    
    # Character types
    "class": "ChrClassesEntry",
    "race": "ChrRacesEntry",
    
    # Currency/Achievements/Vehicles
    "currency": "CurrencyTypesEntry",
    "achievement": "AchievementEntry",
    "criteria": "AchievementCriteriaEntry",
    "vehicle_seat": "VehicleSeatEntry",
    "seat": "VehicleSeatEntry",
    "vehicle": "VehicleEntry",
    
    # Guilds
    "guildbank": "GuildBankTabEntry",
    "guild": "GuildEntry",
    
    # PvP/Combat
    "battleground": "BattlegroundTemplate",
    "battlemaster": "BattlemasterListEntry",
    
    # Travel
    "taxi": "TaxiNodeEntry",
    "taxipath": "TaxiPathEntry",
    
    # Cosmetics
    "emote": "EmotesEntry",
    "title": "CharTitlesEntry",
    
    # Item sets/Locks
    "itemset": "ItemSetEntry",
    "lock": "LockEntry",
    
    # Dungeons/Instances
    "dungeon": "DungeonEncounter",
    "difficulty": "DungeonProgressionRequirements",
    
    # Pools
    "pool": "PoolEntry",
    
    # Miscellaneous
    "emotetext": "EmotesTextEntry",
}

# Fields to exclude (false positives) - checked as substring in field name OR column
EXCLUDED_FIELDS = {
    "ID", "id", "Guid", "guid", "PlayerGuid", "playerGuid", 
    "OwnerGuid", "ownerGuid", "CreatorGuid", "creatorGuid",
    "Difficult", "difficult", "Probability", "probability",
    "priority", "Priority", "title", "Title", "text", "Text",
    "log", "Log", "name", "Name", "description", "Description",
    "target", "Target",  # spell targets, not references
    "spellid_64", "SpellId_64", "guid_64", "Guid_64",
}

# Field types that cannot be cross-references (not numeric IDs)
NON_ID_TYPES = {
    "std::string", "_title", "_text", "_name", "_desc", "char", 
    "bool", "float32", "float64", "double",
    "map key",  # AC_* map keys are internal, not references
    "ptrdiff_t", "size_t",
}

# Explicitly excluded (entry_name.field_name -> target) known false matches
EXPLICIT_EXCLUSIONS = {
    ("LFGData", "uint32", "DungeonEncounter"),  # guid field, not dungeon reference
}


def get_field_prefix(col_name: str) -> str:
    """Extract the prefix from a field name.
    
    Handles both snake_case and camelCase naming conventions.
    'spell_id' -> 'spell', 'mapId' -> 'map', 'areaentry' -> 'area'
    """
    n = col_name.lower()
    
    # Try longest prefixes first for better accuracy
    for prefix in sorted(PREFIX_MAP.keys(), key=len, reverse=True):
        if n.startswith(prefix):
            remainder = n[len(prefix):]
            # Valid suffixes: _id, Id, entry, Entry, or nothing (exact match)
            if remainder in ("", "_id", "id", "entry", "entryid"):
                return prefix
    
    return ""


def find_references(reg_entry_name: str, field_info: dict, registry_entries: set, category_map: dict) -> dict | None:
    """Find cross-reference metadata for a field.
    
    Returns dict with references/reference_type/reference_column if found,
    None otherwise.
    """
    col = field_info.get("sql_column", "") or ""
    cname = field_info.get("name", "") or ""
    
    # Skip if already has reference
    if "references" in field_info:
        return None
        
    # Skip excluded fields (check both SQL column and C++ name)
    if any(excl in col or excl in cname for excl in EXCLUDED_FIELDS):
        return None
    
    # Skip non-numeric field types (can't be ID references)
    field_type = (field_info.get("type", "") or "").strip().lower()
    if any(t in field_type for t in NON_ID_TYPES):
        return None
    
    # Try both SQL column name and C++ field name
    prefixes = []
    
    # Check SQL column name
    sql_prefix = get_field_prefix(col)
    if sql_prefix:
        prefixes.append(sql_prefix)
        
    # Also check C++ field name  
    cpp_prefix = get_field_prefix(cname)
    if cpp_prefix and cpp_prefix != sql_prefix:
        prefixes.append(cpp_prefix)
    
    # Find matching target entry
    for prefix in prefixes:
        target = PREFIX_MAP.get(prefix)
        if not target:
            continue
            
        # Target must exist in registry
        if target not in registry_entries:
            continue
            
        # Skip self-reference
        if target == reg_entry_name:
            continue
        
        # Check explicit exclusions
        if (reg_entry_name, cname, target) in EXPLICIT_EXCLUSIONS or \
           (reg_entry_name, col, target) in EXPLICIT_EXCLUSIONS:
            continue
        
        # Get reference type from target's category
        return {
            "references": target,
            "reference_type": category_map.get(target, "unknown"),
            "reference_column": "ID"
        }
    
    return None


def main():
    with open("datastore_registry.json") as f:
        reg = json.load(f)
    
    entries = reg["entries"]
    registry_entries = set(entries.keys())
    
    # Category map for reference_type inference
    category_map = {name: entry.get("category", "") for name, entry in entries.items()}
    
    stats = Counter()
    added_refs = []

    # Normalize pre-existing array-format references to new flat schema
    normalized = 0
    for entry_name, entry_data in entries.items():
        for idx_str, field_info in entry_data.get("fields", {}).items():
            if isinstance(field_info.get("references"), list):
                arr = field_info["references"]
                if len(arr) == 1 and "target" in arr[0]:
                    target = arr[0]["target"]
                    # Preserve original fields (notes, description)
                    existing_notes = field_info.get("notes", "-")
                    desc = arr[0].get("description", "")
                    field_info["references"] = target
                    field_info["reference_type"] = category_map.get(target, "unknown")
                    field_info["reference_column"] = "ID"
                    if desc:
                        field_info["notes"] = f"{existing_notes} ({desc})" if existing_notes != "-" else desc
                    normalized += 1

    print(f"Normalized {normalized} pre-existing array-format references")

    for entry_name, entry_data in entries.items():
        fields = entry_data.get("fields", {})
        
        for idx_str, field_info in fields.items():
            ref_meta = find_references(entry_name, field_info, registry_entries, category_map)
            
            if ref_meta:
                target = ref_meta["references"]
                ref_type = category_map.get(target, "unknown")
                ref_meta["reference_type"] = ref_type
                
                # Add metadata to field
                for key, value in ref_meta.items():
                    field_info[key] = value
                
                added_refs.append((entry_name, field_info["name"], target))
    
    print(f"Added {len(added_refs)} cross-reference fields")
    
    # Print samples for spot-checking (up to 3 per target)
    print("\n=== SAMPLES FOR VERIFICATION ===")
    by_target = {}
    for m in added_refs:
        by_target.setdefault(m[2], []).append(m)
    for target, refs in sorted(by_target.items()):
        print(f"\n{target} ({len(refs)} fields):")
        for entry_name, field_name, _ in refs[:3]:
            # Find the field info to show full context
            f = entries[entry_name]["fields"]
            for idx, fi in f.items():
                if fi["name"] == field_name:
                    print(f"  {entry_name}.{field_name} (col:{fi.get('sql_column','')}, type:{fi.get('type','')})")
                    break
        if len(refs) > 3:
            print(f"  ... and {len(refs)-3} more")

    # Print summary by target
    target_counts = Counter(m[2] for m in added_refs)
    print("\nBy target entry:")
    for target, count in target_counts.most_common():
        print(f"  {target}: {count} fields")

    # Print some samples
    src_cat = Counter(entries[m[0]].get("category", "") for m in added_refs)
    print("\nBy source category:")
    for cat, count in src_cat.most_common():
        print(f"  {cat}: {count} fields")

    # Write updated registry
    with open("datastore_registry.json", "w") as f:
        json.dump(reg, f, indent=2)
    print(f"\n[Wrote updated datastore_registry.json with {len(added_refs)} cross-references]")


if __name__ == "__main__":
    main()
