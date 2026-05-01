#!/usr/bin/env python3
"""
Generator script to populate 'referenced_by' in datastore_registry.json.

Scans all entries' cross-reference fields and builds a reverse index so that
any target entry knows which other entries reference it. This helps LLMs
trace relationships in both directions.

Usage:
    cd /root/acore-data
    python3 generators/generate_referenced_by.py [--dry-run]

Behavior:
    - Reads datastore_registry.json
    - Scans all forward refs (regular fields + type_field_mappings)
    - Groups array fields into ranges (e.g., ItemId[0..23])
    - Preserves existing hand-crafted referenced_by entries (merges, does not replace)
    - Skips self_refs and targets not in registry
    - Writes grouped referenced_by arrays back to registry JSON
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "datastore_registry.json"


def load_registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def extract_array_info(field_name):
    """Extract base name and index from array field names like 'ItemId[0]'."""
    m = re.match(r"^(.+?)\[(\d+)\]$", field_name)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def group_array_fields(refs_for_same_target):
    """Group array fields into ranges.

    Given [('ItemId', 0), ('ItemId', 1), ..., ('ItemId', 23)],
    returns 'ItemId[0..23]'.
    Non-array fields remain as-is.
    """
    # Separate array and non-array entries
    arrays = defaultdict(list)
    non_arrays = []

    for field_name in refs_for_same_target:
        base, idx = extract_array_info(field_name)
        if base is not None:
            arrays[base].append(idx)
        else:
            non_arrays.append(field_name)

    result = []

    # Process non-array fields (deduplicate)
    for name in sorted(set(non_arrays)):
        result.append(name)

    # Process array groups - consolidate into ranges
    for base, indices in sorted(arrays.items()):
        indices = sorted(set(indices))
        if len(indices) == 1:
            result.append(f"{base}[{indices[0]}]")
        elif _is_contiguous(indices):
            result.append(f"{base}[{indices[0]}..{indices[-1]}]")
        else:
            # Split into contiguous sub-ranges
            ranges = _split_ranges(indices)
            for r in ranges:
                if len(r) == 1:
                    result.append(f"{base}[{r[0]}]")
                else:
                    result.append(f"{base}[{r[0]}..{r[-1]}]")

    return result


def _is_contiguous(sorted_indices):
    """Check if sorted list of integers is contiguous."""
    for i in range(1, len(sorted_indices)):
        if sorted_indices[i] != sorted_indices[i - 1] + 1:
            return False
    return True


def _split_ranges(sorted_indices):
    """Split sorted indices into list of contiguous sub-ranges."""
    if not sorted_indices:
        return []
    ranges = [[sorted_indices[0]]]
    for i in range(1, len(sorted_indices)):
        if sorted_indices[i] == sorted_indices[i - 1] + 1:
            ranges[-1].append(sorted_indices[i])
        else:
            ranges.append([sorted_indices[i]])
    return ranges


def scan_forward_refs(registry):
    """Scan all entries for forward references, build reverse map.

    Returns: defaultdict(str -> list) where str is target entry name,
             and list contains dicts with 'source', 'field', optional 'condition'.
    """
    entries = registry.get("entries", {})
    entry_names = set(entries.keys())

    # Map from target_name -> [(source_name, field_name, condition_or_None)]
    reverse_map = defaultdict(list)

    for source_name, source_entry in entries.items():
        if not isinstance(source_entry, dict):
            continue

        # --- Regular field references ---
        fields = source_entry.get("fields", {})
        for fid, finfo in fields.items():
            if not isinstance(finfo, dict):
                continue
            target = finfo.get("references")
            if not target or target == "self_ref":
                continue
            if isinstance(target, list):
                # Complex multi-ref (e.g., gameobject data[]) - skip for auto-gen
                continue
            if target not in entry_names:
                continue

            field_name = finfo.get("name", fid)
            reverse_map[target].append((source_name, field_name, None))

        # --- type_field_mappings (gameobject_template etc.) ---
        type_mappings = source_entry.get("type_field_mappings", {})
        for go_type, field_map in type_mappings.items():
            if not isinstance(field_map, dict):
                continue
            condition = f"type={go_type}"

            for data_col, field_info in field_map.items():
                if not isinstance(field_info, dict):
                    continue
                target = field_info.get("target")
                if not target or target not in entry_names:
                    continue

                field_name = field_info.get("name", data_col)
                reverse_map[target].append((source_name, field_name, condition))

    return reverse_map


def deduplicate_source_fields(reverse_map):
    """For each target, group refs by source and consolidate fields into ranges.

    Returns: dict of target_name -> [referenced_by_entry]
    """
    result = {}

    for target_name, refs in reverse_map.items():
        # Group by source entry
        by_source = defaultdict(list)
        for source_name, field_name, condition in refs:
            key = (source_name, condition or "")
            by_source[key].append(field_name)

        entries = []
        for (source_name, condition), field_names in sorted(by_source.items()):
            grouped = group_array_fields(field_names)
            entry = {
                "source": source_name,
                "field": ", ".join(grouped) if len(grouped) > 1 else grouped[0] if grouped else "",
            }
            if condition:
                entry["condition"] = condition
            entries.append(entry)

        result[target_name] = entries

    return result


def merge_with_handcrafted(registry, auto_refs):
    """Merge auto-generated refs with existing hand-crafted referenced_by.

    Existing hand-crafted entries are preserved as-is (they may have
    special formatting or conditions we don't want to lose).
    Auto-generated entries are appended for sources not already present.
    """
    entries = registry.get("entries", {})
    merged_count = 0
    unchanged_count = 0

    for target_name, auto_entry_list in auto_refs.items():
        if target_name not in entries:
            continue

        reg_entry = entries[target_name]
        existing = reg_entry.get("referenced_by")

        # Build a lookup of existing sources (including their conditions)
        existing_keys = set()
        if existing:
            for item in existing:
                key = (item.get("source", ""), item.get("condition", ""))
                existing_keys.add(key)

        # Filter auto entries to only those not already present
        new_entries = [
            e for e in auto_entry_list
            if (e.get("source", ""), e.get("condition", "")) not in existing_keys
        ]

        if not new_entries:
            unchanged_count += 1
            continue

        # Merge: existing + new
        merged = list(existing) + new_entries if existing else new_entries
        reg_entry["referenced_by"] = merged
        merged_count += 1

    return merged_count, unchanged_count


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"Loading registry from {REGISTRY_PATH}...")
    registry = load_registry()

    entries = registry.get("entries", {})
    total_entries = len(entries)
    existing_with_refs = sum(
        1 for e in entries.values() if isinstance(e, dict) and "referenced_by" in e
    )

    print(f"Total entries: {total_entries}")
    print(f"Entries with existing referenced_by: {existing_with_refs}")
    print(f"Entries needing enrichment: {total_entries - existing_with_refs}")

    print("\nScanning forward references...")
    reverse_map = scan_forward_refs(registry)

    print(f"  Found {len(reverse_map)} unique target entries that are referenced by others")

    print("\nConsolidating fields into ranges...")
    auto_refs = deduplicate_source_fields(reverse_map)

    # Stats before merge
    targets_needing_update = sum(
        1 for name in auto_refs
        if name in entries and "referenced_by" not in entries[name]
    )
    targets_getting_supplemental = sum(
        1 for name in auto_refs
        if name in entries and "referenced_by" in entries[name]
    )

    print(f"  Targets with NO existing referenced_by: {targets_needing_update}")
    print(f"  Targets with existing refs getting supplemental: {targets_getting_supplemental}")

    if dry_run:
        print("\n--- DRY RUN ---")
        # Show what would be added for top targets
        sorted_targets = sorted(auto_refs.items(), key=lambda x: len(x[1]), reverse=True)
        print("\nTop 20 targets by reference count:")
        for target, refs in sorted_targets[:20]:
            print(f"  {target}: {len(refs)} sources")
            for r in refs[:3]:
                condition_str = f" (if {r.get('condition', '')})" if r.get("condition") else ""
                print(f"    <- {r['source']}.{r['field']}{condition_str}")
            if len(refs) > 3:
                print(f"    ... and {len(refs) - 3} more")
        return

    print("\nMerging with existing hand-crafted data...")
    merged_count, unchanged_count = merge_with_handcrafted(registry, auto_refs)

    new_total_with_refs = existing_with_refs + merged_count
    print(f"  Merged {merged_count} entries")
    print(f"  Skipped {unchanged_count} entries (already complete or no new refs)")
    print(f"  Total entries with referenced_after: {new_total_with_refs}")

    if dry_run or input("\nWrite changes to datastore_registry.json? [y/N]: ").strip().lower() != "y":
        if not dry_run:
            print("Aborted.")
        return

    save_registry(registry)
    print(f"\nSaved updated registry ({new_total_with_refs} entries now have referenced_by).")


if __name__ == "__main__":
    main()
