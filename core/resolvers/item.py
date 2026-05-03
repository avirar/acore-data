"""Resolve item_template with enriched cross-reference data.

For each item row, automatically includes:
- Loot template contents from item_loot_template (for items with Flags & 0x04)
- Spell names and conditions for spellid_1..5 (on-use spells)
- Start quest name if startquest is set

Uses batch resolution to minimize SQL queries.
"""
from typing import Any, Dict, List

from .ref_utils import resolve_loot_ref, resolve_dbc_ref, batch_resolve_sql
from ..enums import ITEM_CLASS_NAMES, ITEM_SUBCLASS_MAP


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

    For items with spellid_1..5, resolves spell names and their conditions.
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

    # --- Pre-collect all spell IDs for batch resolution ---
    all_spell_ids = set()
    for row in rows:
        for i in range(1, 6):
            sid = row.get(f"spellid_{i}", 0) or 0
            if sid > 0:
                all_spell_ids.add(int(sid))

    # --- Batch resolve spell names from DBC ---
    spell_name_map = {}
    if all_spell_ids and "dbc" in allowed:
        for sid in all_spell_ids:
            name = resolve_dbc_ref(server, "Spell", sid, "ID")
            if name:
                spell_name_map[sid] = name

    # --- Fetch spell conditions for all spell IDs ---
    spell_conditions = {}
    if all_spell_ids and "sql" in allowed:
        from .spell import _fetch_spell_conditions, collect_spell_condition_ids
        from .spell import _format_condition_row
        if all_spell_ids:
            from .condition import _collect_condition_ids, _prewarm_condition_cache
            conds_by_spell = _fetch_spell_conditions(server, list(all_spell_ids))
            if conds_by_spell:
                all_conds = [c for cs in conds_by_spell.values() for c in cs]
                collected = _collect_condition_ids(all_conds)
                if collected:
                    _prewarm_condition_cache(server, collected)
                for sid, conds in conds_by_spell.items():
                    limit = resolve_max if resolve_max else len(conds)
                    spell_conditions[sid] = [_format_condition_row(server, c) for c in conds[:limit]]

    # --- Pre-collect start quest IDs ---
    all_start_quest_ids = set()
    for row in rows:
        sq = row.get("startquest", 0) or 0
        if sq:
            all_start_quest_ids.add(int(sq))

    start_quest_map = {}
    if all_start_quest_ids and "sql" in allowed:
        start_quest_map = batch_resolve_sql(server, "quest_template", list(all_start_quest_ids), "ID")

    resolved = {}
    for row in rows:
        entry = _get_row_pk(row)
        flags = row.get("Flags", 0)

        enriched = {}

        # --- Loot resolution ---
        if "loot" in allowed and flags and (int(flags) & _ITEM_FLAG_HAS_LOOT):
            loot_result = resolve_loot_ref(
                server, "item_loot_template", int(entry), "Entry", resolve_max
            )
            if loot_result and "items" in loot_result:
                enriched["loot"] = {
                    "resolved_to": loot_result.get("resolved_to", ""),
                    "items": loot_result["items"],
                }
                if "warning" in loot_result:
                    enriched["loot"]["warning"] = loot_result["warning"]

        # --- Spell resolution ---
        if spell_name_map or spell_conditions:
            spells = {}
            for i in range(1, 6):
                sid = row.get(f"spellid_{i}", 0) or 0
                if sid <= 0:
                    continue
                spell_info = {"id": int(sid)}
                if sid in spell_name_map:
                    spell_info["name"] = spell_name_map[sid]
                trigger = row.get(f"spelltrigger_{i}", 0) or 0
                trigger_names = {0: "on_use", 1: "on_equip", 2: "chance_on_hit", 4: "soulstone", 5: "use_with_delay", 6: "learn"}
                if trigger:
                    spell_info["trigger"] = trigger_names.get(trigger, f"trigger_{trigger}")
                if sid in spell_conditions:
                    spell_info["conditions"] = spell_conditions[sid]
                spells[f"spellid_{i}"] = spell_info
            if spells:
                enriched["spells"] = spells

        # --- Start quest resolution ---
        sq = row.get("startquest", 0) or 0
        if sq and start_quest_map:
            enriched["startquest"] = {
                "id": int(sq),
                "name": start_quest_map.get(int(sq), f"quest_template [{sq}] (not found)"),
            }

        # --- Class/Subclass decoding ---
        item_class = row.get("class", 0) or 0
        item_subclass = row.get("subclass", 0) or 0
        if item_class and "sql" in allowed:
            class_name = ITEM_CLASS_NAMES.get(item_class, f"class_{item_class}")
            subclass_map = ITEM_SUBCLASS_MAP.get(item_class, {})
            subclass_name = subclass_map.get(item_subclass, f"subclass_{item_subclass}") if subclass_map else None
            enriched["item_type"] = {
                "class_id": int(item_class),
                "class_name": class_name,
                "subclass_id": int(item_subclass),
            }
            if subclass_name:
                enriched["item_type"]["subclass_name"] = subclass_name

        # Merge base + enrichment
        entry_resolved = base_resolved.get(entry, {})
        merged = {**entry_resolved, **enriched}
        if merged:
            resolved[entry] = merged

    return resolved
