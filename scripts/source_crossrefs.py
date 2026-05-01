#!/usr/bin/env python3
"""Phase 3: Parse AzerothCore source code for cross-reference patterns.

Finds patterns like sXxxStore.LookupEntry(obj->Field) to identify
which fields reference which registry entries.

Pattern: s<Target>Store.LookupEntry(source-><field>) -> field references Target Entry
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict

SOURCE_DIR = Path(os.path.expanduser("~/azerothcore-wotlk/src/server/game"))
REGISTRY_PATH = "datastore_registry.json"

# Map store variable names to registry entry names
STORE_TO_ENTRY = {
    "sAchievementStore": "AchievementEntry",
    "sAchievementCategoryStore": "AchievementCategoryEntry",
    "sAchievementCriteriaStore": "AchievementCriteriaEntry",
    "sAreaGroupStore": "AreaGroupEntry",
    "sAreaPOIStore": "AreaPOIEntry",
    "sAreaTableStore": "AreaTableEntry",
    "sAuctionHouseStore": "AuctionHouseEntry",
    "sBarberShopStyleStore": "BarberShopStyleEntry",
    "sBattlemasterListStore": "BattlemasterListEntry",
    "sCharSectionsStore": "CharSectionsEntry",
    "sCharStartOutfitStore": "CharStartOutfitEntry",
    "sChrClassesStore": "ChrClassesEntry",
    "sChrRacesStore": "ChrRacesEntry",
    "sCinematicCameraStore": "CinematicCameraEntry",
    "sCinematicSequencesStore": "CinematicSequencesEntry",
    "sCreatureDisplayInfoStore": "CreatureDisplayInfoEntry",
    "sCreatureFamilyStore": "CreatureFamilyEntry",
    "sCreatureModelDataStore": "CreatureModelDataEntry",
    "sCreatureSpellDataStore": "CreatureSpellDataEntry",
    "sCreatureTypeStore": "CreatureTypeEntry",
    "sCurrencyTypesStore": "CurrencyTypesEntry",
    "sDestructibleModelDataStore": "DestructibleModelDataEntry",
    "sDungeonEncounterStore": "DungeonEncounterEntry",
    "sDurabilityCostsStore": "DurabilityCostsEntry",
    "sDurabilityQualityStore": "DurabilityQualityEntry",
    "sEmotesStore": "EmotesEntry",
    "sEmotesTextStore": "EmotesTextEntry",
    "sEmotesTextSoundStore": "EmotesTextSoundEntry",
    "sFactionStore": "FactionEntry",
    "sFactionTemplateStore": "FactionTemplateEntry",
    "sGameObjectArtKitStore": "GameObjectArtKitEntry",
    "sGameObjectDisplayInfoStore": "GameObjectDisplayInfoEntry",
    "sGemPropertiesStore": "GemPropertiesEntry",
    "sGlyphPropertiesStore": "GlyphPropertiesEntry",
    "sGlyphSlotStore": "GlyphSlotEntry",
    "sHolidaysStore": "HolidaysEntry",
    "sItemBagFamilyStore": "ItemBagFamilyEntry",
    "sItemDisplayInfoStore": "ItemDisplayInfoEntry",
    "sItemExtendedCostStore": "ItemExtendedCostEntry",
    "sItemLimitCategoryStore": "ItemLimitCategoryEntry",
    "sItemRandomPropertiesStore": "ItemRandomPropertiesEntry",
    "sItemRandomSuffixStore": "ItemRandomSuffixEntry",
    "sItemSetStore": "ItemSetEntry",
    "sItemSparseStore": "ItemEntry",  # ItemEntry = sparse data
    "sLFGDungeonStore": "LFGDungeonEntry",
    "sLightStore": "LightEntry",
    "sLiquidTypeStore": "LiquidTypeEntry",
    "sLockStore": "LockEntry",
    "sMailTemplateStore": "MailTemplateEntry",
    "sMapDifficultyStore": "MapDifficultyEntry",
    "sMapStore": "MapEntry",
    "sMovieStore": "MovieEntry",
    "sOverrideSpellDataStore": "OverrideSpellDataEntry",
    "sPowerDisplayStore": "PowerDisplayEntry",
    "sPvPDifficultyStore": "PvPDifficultyEntry",
    "sQuestFactionRewStore": "QuestFactionRewEntry",
    "sQuestSortStore": "QuestSortEntry",
    "sQuestXPStore": "QuestXPEntry",
    "sRandomPropertiesPointsStore": "RandomPropertiesPointsEntry",
    "sScalingStatDistributionStore": "ScalingStatDistributionEntry",
    "sSkillLineAbilityStore": "SkillLineAbilityEntry",
    "sSkillLineStore": "SkillLineEntry",
    "sSkillRaceClassInfoStore": "SkillRaceClassInfoEntry",
    "sSkillTiersStore": "SkillTiersEntry",
    "sSoundEntriesStore": "SoundEntriesEntry",
    "sSpellCastTimesStore": "SpellCastTimesEntry",
    "sSpellCategoryStore": "SpellCategoryEntry",
    "sSpellDifficultyStore": "SpellDifficultyEntry",
    "sSpellDurationStore": "SpellDurationEntry",
    "sSpellFocusObjectStore": "SpellFocusObjectEntry",
    "sSpellItemEnchantmentConditionStore": "SpellItemEnchantmentConditionEntry",
    "sSpellItemEnchantmentStore": "SpellItemEnchantmentEntry",
    "sSpellRadiusStore": "SpellRadiusEntry",
    "sSpellRangeStore": "SpellRangeEntry",
    "sSpellRuneCostStore": "SpellRuneCostEntry",
    "sSpellShapeshiftFormStore": "SpellShapeshiftFormEntry",
    "sSpellVisualStore": "SpellVisualEntry",
    "sSpellStore": "SpellEntry",
    "sStableSlotPricesStore": "StableSlotPricesEntry",
    "sSummonPropertiesStore": "SummonPropertiesEntry",
    "sTalentStore": "TalentEntry",
    "sTalentTabStore": "TalentTabEntry",
    "sTaxiNodesStore": "TaxiNodesEntry",
    "sTaxiPathStore": "TaxiPathEntry",
    "sTaxiPathNodeStore": "TaxiPathNodeEntry",
    "sTotemCategoryStore": "TotemCategoryEntry",
    "sTransportAnimationStore": "TransportAnimationEntry",
    "sTransportRotationStore": "TransportRotationEntry",
    "sVehicleSeatStore": "VehicleSeatEntry",
    "sVehicleStore": "VehicleEntry",
    "sWMOAreaTableStore": "WMOAreaTableEntry",
    "sWorldMapAreaStore": "WorldMapAreaEntry",
    "sWorldMapOverlayStore": "WorldMapOverlayEntry",
}


def find_lookup_patterns(source_dir):
    """Scan source code for sXxxStore.LookupEntry(obj->Field) patterns."""
    refs = set()  # (source_struct, field_name, target_entry, file_path, line_num)
    
    # Key patterns to search for:
    # sXxxStore.LookupEntry(ptr->field) or sXxxStore.GetEntry(field)
    pattern = re.compile(
        r'(s\w+Store)\.(LookupEntry|GetEntry)\(\s*(\w+)\s*->\s*(\w+)'
    )
    # Also match direct variable use: sXxxStore.LookupEntry(varName)
    pattern2 = re.compile(
        r'(s\w+Store)\.(LookupEntry|GetEntry)\(\s*(\w+)\s*\)'
    )
    
    for cpp_file in sorted(source_dir.rglob("*.cpp")):
        try:
            content = cpp_file.read_text(errors='ignore')
        except (PermissionError, OSError):
            continue
        
        for i, line in enumerate(content.split('\n'), 1):
            # Pattern 1: ptr->Field access
            for m in pattern.finditer(line):
                store_name = m.group(1)
                var_name = m.group(3)
                field_name = m.group(4)
                
                target_entry = STORE_TO_ENTRY.get(store_name)
                if not target_entry:
                    continue
                
                # Try to infer source struct from variable name
                source_struct = infer_source_struct(var_name)
                if source_struct:
                    refs.add((source_struct, field_name, target_entry, 
                             str(cpp_file), i))
            
            # Pattern 2: Direct variable access (less precise but finds more)
            # Only for specific known patterns like "talentInfo->RankID[i]"
    
    return refs


def infer_source_struct(var_name):
    """Try to guess which struct a variable belongs to based on naming.
    
    Common patterns:
        spellInfo -> SpellEntry
        talentInfo -> TalentEntry
        mapInfo -> MapEntry
        creatureProto, entry -> CreatureTemplate (not DBC)
    """
    var_name = re.sub(r'(?:Info|Ptr|Data|Entry)?$', '', var_name)
    
    # Direct matches based on common variable naming
    struct_map = {
        "spell": ["SpellEntry"],
        "talent": ["TalentEntry"],
        "achievement": ["AchievementEntry"],
        "areagroup": ["AreaGroupEntry"],
        "creaturefamily": ["CreatureFamilyEntry"],
        "emote": ["EmotesEntry"],
        "faction": ["FactionEntry"],
        "gameobject": ["GameObjectTemplate"],  # SQL, not DBC
        "holidays": ["HolidaysEntry"],
        "itemdisplayinfo": ["ItemDisplayInfoEntry"],
        "lock": ["LockEntry"],
        "map": ["MapEntry"],
        "spellvisual": ["SpellVisualEntry"],
        "talenttab": ["TalentTabEntry"],
        "vehicleseat": ["VehicleSeatEntry"],
    }
    
    var_lower = var_name.lower()
    for prefix, structs in sorted(struct_map.items(), key=lambda x: -len(x[0])):
        if var_lower.startswith(prefix):
            return structs[0]
    
    return None


def main():
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)
    
    entries = registry["entries"]
    entry_names = set(entries.keys())
    
    # Existing references lookup
    existing = set()
    for entry_name, entry_data in entries.items():
        for idx, field_info in entry_data.get("fields", {}).items():
            if "references" in field_info and isinstance(field_info["references"], str):
                base = re.sub(r'\[\d*\]$', '', field_info["name"])
                existing.add((entry_name, field_info["name"]))
                existing.add((entry_name, base))
    
    # Scan source code for references
    print(f"Scanning {SOURCE_DIR} for LookupEntry patterns...")
    refs = find_lookup_patterns(SOURCE_DIR)
    
    print(f"\nFound {len(refs)} raw reference patterns")
    
    # Filter: target must be in registry, must not already exist
    new_refs = []
    stats = {"dup": 0, "not_in_registry": 0, "added": 0}
    
    for source_struct, field_name, target_entry, filepath, lineno in refs:
        if target_entry not in entry_names:
            stats["not_in_registry"] += 1
            continue
        
        key = (source_struct, field_name)
        if key in existing or any(source_struct == e and f.startswith(field_name) 
                                   for e, f in existing):
            stats["dup"] += 1
            continue
        
        new_refs.append((source_struct, field_name, target_entry))
    
    print(f"New unique refs: {len(new_refs)}")
    print(f"Duplicates: {stats['dup']}")
    print(f"Not in registry: {stats['not_in_registry']}")
    
    if new_refs:
        # Show samples
        by_target = defaultdict(list)
        for src, field, tgt in sorted(new_refs):
            by_target[tgt].append((src, field))
        
        print(f"\n=== NEW REFERENCES BY TARGET ===")
        count = 0
        for target, refs_list in sorted(by_target.items()):
            print(f"\n{target} ({len(refs_list)} sources):")
            for src, field in refs_list[:5]:
                print(f"  {src}.{field}")
            if len(refs_list) > 5:
                print(f"  ... and {len(refs_list)-5} more")
            count += len(refs_list)
    
    # Apply new references
    applied = 0
    category_map = {n: e.get("category", "") for n, e in entries.items()}
    
    for source_struct, field_name, target_entry in new_refs:
        if source_struct not in entries:
            continue
        
        entry_data = entries[source_struct]
        
        # Find the field (may have array suffix)
        found_field = False
        for idx, field_info in entry_data.get("fields", {}).items():
            fn = field_info.get("name", "")
            base = re.sub(r'\[\d*\]$', '', fn)
            
            if base == field_name or fn == field_name:
                if "references" not in field_info:
                    field_info["references"] = target_entry
                    field_info["reference_type"] = category_map.get(target_entry, "unknown")
                    field_info["reference_column"] = "ID"
                    applied += 1
                found_field = True
        
        if new_refs and applied <= 3 and not found_field:
            # Debug: show what we tried to match
            print(f"  NOTE: {source_struct}.{field_name} - field not found in registry")
    
    if applied:
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)
        print(f"\nApplied {applied} new cross-references to datastore_registry.json")
    else:
        print("\nNo new references applied (fields not found in registry)")


if __name__ == "__main__":
    main()
