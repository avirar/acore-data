"""Resolve item_template with enriched cross-reference data.

For each item row, automatically includes:
- Loot template contents from item_loot_template (for items with Flags & 0x04)

Uses batch resolution to minimize SQL queries.
"""
from typing import Any, Dict, List

from .ref_utils import resolve_loot_ref, batch_resolve_sql


# ITEM_FLAG_HAS_LOOT — item drops loot when killed/picked up
_ITEM_FLAG_HAS_LOOT = 0x04


def _get_row_pk(row: Dict) -> str:
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def collect_item_loot_ids(rows: List[Dict[str, Any]]) -> list:
    """Collect all item entry IDs that have loot templates.

    Mirrors the resolve logic so caller can pre-warm cache before main loop.
    """
    loot_ids = []
    for row in rows:
        flags = row.get("Flags", 0)
        if flags and (int(flags) & _ITEM_FLAG_HAS_LOOT):
            entry = row.get("entry")
            if entry:
                loot_ids.append(int(entry))
    return loot_ids


def resolve_item_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve item_template fields with enriched loot data.

    For items with ITEM_FLAG_HAS_LOOT (Flags & 0x04), resolves the
    item_loot_template and shows contents inline.
    """
    from ..type_resolver import _resolve_generic
    base_resolved = _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)

    if not rows:
        return base_resolved

    # Determine allowed resolve types
    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return base_resolved

    if "loot" not in allowed:
        return base_resolved

    resolved = {}
    for row in rows:
        entry = _get_row_pk(row)
        flags = row.get("Flags", 0)

        # Check if item has loot
        if not flags or not (int(flags) & _ITEM_FLAG_HAS_LOOT):
            entry_resolved = base_resolved.get(entry, {})
            if entry_resolved:
                resolved[entry] = entry_resolved
            continue

        # Resolve loot template
        loot_result = resolve_loot_ref(
            server, "item_loot_template", int(entry), "Entry", resolve_max
        )

        enriched = {}
        if loot_result and "items" in loot_result:
            enriched["loot"] = {
                "resolved_to": loot_result.get("resolved_to", ""),
                "items": loot_result["items"],
            }
            if "warning" in loot_result:
                enriched["loot"]["warning"] = loot_result["warning"]

        # Merge base + enrichment
        merged = {**base_resolved.get(entry, {}), **enriched}
        if merged:
            resolved[entry] = merged

    return resolved
