#!/usr/bin/env python3
"""
Verify SPELL_EFFECT_NAMES against AzerothCore's SharedDefines.h

Parses the SpellEffects enum directly from AzerothCore source code and compares
against the acore-data core/enums.py implementation.

Usage:
    python scripts/verify_spell_effects.py
    python scripts/verify_spell_effects.py --verbose
    python scripts/verify_spell_effects.py --critical-only
"""

import re
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Paths relative to repo root
ACORE_DATA_DIR = Path(__file__).parent.parent
AZEROTHCORE_DIR = ACORE_DATA_DIR.parent / "azerothcore-wotlk"

SHARED_DEFINES_PATH = AZEROTHCORE_DIR / "src/server/shared/SharedDefines.h"
ENUM_MODULE_PATH = ACORE_DATA_DIR / "core/enums.py"

# Critical effect IDs that are commonly used in game content
CRITICAL_EFFECTS = {
    1: "INSTAKILL",
    24: "CREATE_ITEM",
    25: "WEAPON",
    71: "PICKPOCKET",
    78: "ATTACK",
    85: "SUMMON_PLAYER",
    95: "SKINNING",
    99: "DISENCHANT",
    108: "DISPEL_MECHANIC",
    127: "PROSPECTING",
    158: "MILLING",
    164: "REMOVE_AURA",
    157: "CREATE_RANDOM_ITEM",
}


def parse_shared_defines_spell_effects(header_path: Path) -> Dict[int, str]:
    """
    Parse the SpellEffects enum from SharedDefines.h
    
    Returns:
        Dictionary mapping effect index to name, e.g., {1: "INSTAKILL", 24: "CREATE_ITEM", ...}
    """
    if not header_path.exists():
        raise FileNotFoundError(f"Header not found: {header_path}")
    
    content = header_path.read_text(encoding="utf-8")
    
    # Find the SpellEffects enum block
    enum_pattern = r"enum\s+SpellEffects\s*\{(.+?)\};\s*//"
    match = re.search(enum_pattern, content, re.DOTALL)
    if not match:
        raise ValueError("Could not find SpellEffects enum in SharedDefines.h")
    
    enum_block = match.group(1)
    
    # Parse each enum entry: SPELL_EFFECT_NAME = number,
    entry_pattern = r"SPELL_EFFECT_(\w+)\s*=\s*(\d+)"
    entries = re.findall(entry_pattern, enum_block)
    
    result = {}
    for name, value in entries:
        index = int(value)
        # Normalize name: remove PREFIX_ if present, make readable
        clean_name = name.replace("SPELL_EFFECT_", "")
        result[index] = clean_name
    
    return result


def load_acore_data_enum() -> Dict[int, str]:
    """
    Load SPELL_EFFECT_NAMES from acore-data core/enums.py
    
    Returns:
        Dictionary mapping effect index to name
    """
    # Add parent to path to import
    sys.path.insert(0, str(ACORE_DATA_DIR))
    try:
        from core.enums import SPELL_EFFECT_NAMES
        return SPELL_EFFECT_NAMES
    finally:
        sys.path.pop(0)


def compare_enums(
    expected: Dict[int, str],
    actual: Dict[int, str],
    ignore_missing_zero: bool = True
) -> List[Tuple[int, str, str, str]]:
    """
    Compare two enum dictionaries
    
    Args:
        expected: Dictionary from source ( AzerothCore)
        actual: Dictionary from acore-data
        ignore_missing_zero: If True, skip index 0 in actual if not in expected
    
    Returns:
        List of (index, status, expected_name, actual_name)
        status is "match", "mismatch", or "missing"
    """
    
    def normalize(name: str) -> str:
        """Normalize names for comparison - handle UNKNOWN vs numbered forms"""
        # "112" -> "UNKNOWN112", "122" -> "UNKNOWN122", etc.
        if name.isdigit():
            return f"UNKNOWN{name}"
        # "UNKNOWN112" -> "UNKNOWN112" (already normalized)
        return name
    
    results = []
    
    # Get all indices from both dicts
    all_indices = set(expected.keys()) | set(actual.keys())
    
    for idx in sorted(all_indices):
        # Skip placeholder zero if not in source
        if ignore_missing_zero and idx == 0 and idx not in expected:
            continue
            
        if idx not in expected:
            results.append((idx, "missing", "-", actual.get(idx, "?")))
        elif idx not in actual:
            results.append((idx, "missing", expected.get(idx, "?"), "-"))
        elif normalize(expected[idx]) != normalize(actual[idx]):
            results.append((idx, "mismatch", expected[idx], actual[idx]))
        else:
            results.append((idx, "match", expected[idx], actual[idx]))
    
    return results


def run_verification(verbose: bool = False, critical_only: bool = False) -> Tuple[bool, str]:
    """
    Run the full verification process
    
    Returns:
        (success, message)
    """
    print("=" * 60)
    print("SPELL_EFFECT_NAMES Verification")
    print("=" * 60)
    print()
    print(f"Source: {SHARED_DEFINES_PATH}")
    print(f"Script: {ENUM_MODULE_PATH}")
    print()
    
    # Parse source
    print("Parsing SharedDefines.h...")
    try:
        source_enums = parse_shared_defines_spell_effects(SHARED_DEFINES_PATH)
        print(f"  Found {len(source_enums)} entries")
    except Exception as e:
        return False, f"Failed to parse source: {e}"
    
    # Load acore-data
    print("Loading acore-data enums...")
    try:
        acore_enums = load_acore_data_enum()
        print(f"  Found {len(acore_enums)} entries")
    except Exception as e:
        return False, f"Failed to load enums: {e}"
    
    # Compare
    print("Comparing...")
    results = compare_enums(source_enums, acore_enums)
    
    # Analyze results
    match_count = sum(1 for _, status, _, _ in results if status == "match")
    mismatch_count = sum(1 for _, status, _, _ in results if status == "mismatch")
    missing_count = sum(1 for _, status, _, _ in results if status == "missing")
    
    print()
    print("-" * 60)
    if critical_only:
        print("CRITICAL EFFECTS TEST")
        print("-" * 60)
        
        all_pass = True
        for idx, expected_name in sorted(CRITICAL_EFFECTS.items()):
            actual_name = acore_enums.get(idx, "MISSING")
            expected_from_source = source_enums.get(idx, expected_name)
            
            if actual_name == expected_from_source:
                status = "✓"
            else:
                status = "✗"
                all_pass = False
            
            print(f"  {status} Effect {idx:3d}: {actual_name:20s} (expected {expected_from_source})")
        
        print()
        if all_pass:
            return True, "All critical effects verified"
        else:
            return False, "Some critical effects mismatch"
    
    # Full comparison
    print(f"FULL COMPARISON ({len(results)} entries)")
    print("-" * 60)
    
    # Show mismatches first, then matches
    mismatches = [(i, s, e, a) for i, s, e, a in results if s != "match"]
    matches = [(i, s, e, a) for i, s, e, a in results if s == "match"]
    
    if mismatches:
        print(f"\nMISMATCHES / MISSING ({len(mismatches)}):")
        for idx, status, expected, actual in mismatches:
            if status == "missing":
                if expected == "-":
                    print(f"  ✗ Index {idx:3d}: EXTRA in acore-data: '{actual}'")
                else:
                    print(f"  ✗ Index {idx:3d}: MISSING in acore-data (expected '{expected}')")
            else:
                print(f"  ✗ Index {idx:3d}: '{actual}' != '{expected}'")
    
    # Show a sample of matches
    if verbose and matches:
        print(f"\nVERIFIED MATCHES (showing first 20):")
        for idx, _, expected, actual in matches[:20]:
            print(f"  ✓ Index {idx:3d}: {expected}")
    
    # Summary
    print()
    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"  Matches:    {match_count}/{len(results)}")
    print(f"  Mismatches: {mismatch_count}")
    print(f"  Missing:    {missing_count}")
    
    if mismatch_count == 0 and missing_count == 0:
        return True, f"All {match_count} entries verified"
    else:
        return False, f"Issues found: {mismatch_count} mismatches, {missing_count} missing"


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify SPELL_EFFECT_NAMES against AzerothCore source"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including matches"
    )
    parser.add_argument(
        "--critical-only", "-c",
        action="store_true",
        help="Only test critical effect IDs"
    )
    args = parser.parse_args()
    
    success, message = run_verification(
        verbose=args.verbose,
        critical_only=args.critical_only
    )
    
    print()
    print("=" * 60)
    print(f"RESULT: {message}")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()