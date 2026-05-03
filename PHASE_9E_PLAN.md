# Phase 9E: Spell → Conditions Cross-Reference Resolver

## Status: COMPLETE
## Depends On: Phase 9D (item_template resolver) — DONE (`993c967`)

## Overview

When querying Spell entries (via DBC or SQL), automatically enrich them with their
cast conditions from the `conditions` table. Spell conditions control when a spell
can be cast, what targets it can hit, and what happens on failure.

The spell resolver (`core/resolvers/spell.py`) already exists as an untracked file
with working logic. This phase refactors it for production quality by eliminating
code duplication and adding pre-warming.

## Current State

| Component | Status |
|---|---|
| `_fetch_spell_conditions()` — batch SQL fetch | Done (inline IDs for CLI compat) |
| `_format_condition_row()` — per-condition formatting | Done (delegates to condition.py) |
| `resolve_spell_fields()` — main dispatcher | Done |
| `collect_spell_condition_ids()` — spell ID collector | Done |
| Registration in `__init__.py` | Done |
| Pre-warming of condition value refs | **Done** |
| Tests | **Done (5/5 pass)** |

## Spell Conditions Data Profile

### Source Types (when conditions apply to spells)

| SourceType | Count | Name |
|---|---|---|
| 13 | 3,789 | SPELL_IMPLICIT_TARGET |
| 17 | 870 | SPELL |
| 18 | 164 | SPELL_CLICK_EVENT |
| 21 | 14 | VEHICLE_SPELL |
| 24 | 4 | SPELL_PROC |
| **Total** | **4,841** | |

### Top Condition Types for Spells

| ConditionType | Count | SQL/DBC refs resolved |
|---|---|---|
| 31 (OBJECT_ENTRY_GUID) | 3,908 | creature_template, item_template, gameobject_template |
| 36 (ALIVE) | 304 | None (enum-only) |
| 1 (AURA) | 119 | Spell DBC |
| 29 (NEAR_CREATURE) | 111 | creature_template |
| 9 (QUESTTAKEN) | 91 | quest_template |
| 8 (QUESTREWARDED) | 55 | quest_template |
| 30 (NEAR_GAMEOBJECT) | 32 | gameobject_template |
| 23 (AREAID) | 27 | AreaTable DBC |
| 33 (TEAM) | 21 | None (enum) |
| 38 (HP_PCT) | 20 | None (comparison) |

### Top Spells by Condition Count

| Spell ID | Conditions | Notes |
|---|---|---|
| 48649 | 191 | Highly conditional |
| 46903 | 78 | Paired conditions |
| 46904 | 78 | Paired conditions |
| 62575 | 59 | |
| 60535 | 58 | |

## Design Decision: Reuse condition.py (Option B)

### Why reuse instead of keeping separate code

The current `spell.py._format_condition_row()` duplicates ~80% of
`condition.py._resolve_condition_values()`. Over time these will drift:
new condition types added to one but not the other, bug fixes applied
inconsistently, etc.

**Importing from condition.py gives:**

1. **Single source of truth** — 50+ condition types resolved in one place
2. **Structured output** — machine-readable dicts (`{"target_entity": {"type": "creature", "id": 456, "name": "Defias Bandit"}}`) instead of flat strings (`"Target: UNIT entry=456"`)
3. **Automatic pre-warming** — `_collect_condition_ids` already knows which condition types reference which tables

### Functions to import from condition.py

| Function | Purpose |
|---|---|
| `_collect_condition_ids(rows)` | Collect all SQL/DBC IDs from condition rows, grouped by `(table, id_col)` |
| `_prewarm_condition_cache(server, collected_ids)` | Batch-resolve collected IDs into per-request cache |
| `_resolve_condition_source(server, source_type, source_entry, source_group)` | Resolve SourceEntry based on SourceType |
| `_resolve_condition_values(server, condition_type, v1, v2, v3)` | Resolve ConditionValue1-3 based on ConditionType |

### Functions that stay in spell.py

| Function | Why it stays |
|---|---|
| `_get_spell_id(row)` | Spell-specific ID extraction (handles DBC + SQL row formats) |
| `collect_spell_condition_ids(rows)` | Collector for pre-warming — gathers spell IDs to fetch conditions for |
| `_fetch_spell_conditions(server, spell_ids)` | Batch SQL fetch of conditions for given spell IDs |
| `resolve_spell_fields(...)` | Main resolver dispatcher — orchestrates the flow |

### What `_format_condition_row()` becomes

Instead of ~80 lines of duplicated condition resolution logic, it became
a thin wrapper (~45 lines) that:

1. Calls `_resolve_condition_source()` for the source entry
2. Calls `_resolve_condition_values()` for the condition values
3. Adds spell-specific envelope: source type name, effect bitmask, negative condition, error type
4. Merges into a clean structured output (dict with `values` key)

### Implementation notes

- `_fetch_spell_conditions()` uses **inline integer IDs** (not `%s` params) because
  the system may fall back to mysql CLI when pymysql is unavailable, and CLI mode
  doesn't support parameterized queries. This is safe since spell IDs are always ints.

## Implementation Steps

### Step 1: Refactor `_format_condition_row()`

**File**: `core/resolvers/spell.py`

Replace the current `_format_condition_row()` with a thin wrapper that delegates
to condition.py's shared functions:

```python
def _format_condition_row(server, cond: Dict) -> Dict:
    """Format a single condition row using shared resolution from condition.py."""
    from .condition import (
        _resolve_condition_source, _resolve_condition_values,
    )

    source_type = cond.get("SourceTypeOrReferenceId", 0) or 0
    condition_type = cond.get("ConditionTypeOrReference", 0) or 0
    value1 = cond.get("ConditionValue1", 0) or 0
    value2 = cond.get("ConditionValue2", 0) or 0
    value3 = cond.get("ConditionValue3", 0) or 0
    source_entry = cond.get("SourceEntry", 0) or 0
    source_group = cond.get("SourceGroup", 0) or 0
    neg_cond = cond.get("NegativeCondition", 0) or 0
    error_type = cond.get("ErrorType", 0) or 0
    else_group = cond.get("ElseGroup", 0) or 0

    entry = {
        "source": _SOURCE_TYPE_NAMES.get(source_type, f"UNKNOWN({source_type})"),
        "type": _CONDITION_TYPE_NAMES.get(condition_type, f"UNKNOWN({condition_type})"),
        "raw_values": {"v1": value1, "v2": value2, "v3": value3},
    }

    if else_group:
        entry["else_group"] = int(else_group)

    if neg_cond:
        entry["negative_condition"] = True
        entry["type"] = f"NOT_{entry['type']}"

    # Effect bitmask for SPELL_IMPLICIT_TARGET (source_type=13)
    if source_type == 13 and source_group:
        effects = []
        if source_group & 1: effects.append("effect0")
        if source_group & 2: effects.append("effect1")
        if source_group & 4: effects.append("effect2")
        entry["effects"] = f"mask[{','.join(effects)}]"

    # Delegate resolution to shared condition functions
    if source_entry:
        resolved_source = _resolve_condition_source(
            server, source_type, source_entry, source_group
        )
        if resolved_source:
            entry["source_entry"] = resolved_source

    resolved_values = _resolve_condition_values(
        server, condition_type, value1, value2, value3
    )
    if resolved_values:
        entry["values"] = resolved_values

    # Error type annotation
    if error_type and error_type != 0:
        entry["error"] = _ERROR_TYPE_NAMES.get(error_type, f"error({error_type})")

    return entry
```

This replaces ~120 lines of duplicated logic with ~50 lines of delegation.
The output format becomes richer (structured `values` dict instead of flat `meaning` string).

### Step 2: Add Pre-warming

**File**: `core/resolvers/spell.py`

Add pre-warming call in `resolve_spell_fields()` between fetching conditions
and formatting them:

```python
# After _fetch_spell_conditions():
conditions_by_spell = _fetch_spell_conditions(server, spell_ids)

# NEW: Pre-warm cache with batch lookups for all condition value references
if "sql" in allowed and conditions_by_spell:
    from .condition import _collect_condition_ids, _prewarm_condition_cache
    all_conds = [c for conds in conditions_by_spell.values() for c in conds]
    collected = _collect_condition_ids(all_conds)
    if collected:
        _prewarm_condition_cache(server, collected)
```

### Step 3: Clean Up spell.py

Remove dead code from spell.py:
- Remove the `_COMP_TYPES` dict (already in condition.py)
- Remove the `_ERROR_TYPE_NAMES` dict (already in condition.py) — import from condition.py instead
- Remove the `_try_spell_name` helper (now handled by `_resolve_condition_source`)
- Remove individual condition type handlers (AURA, ITEM, CLASS, RACE, etc.) — all delegated to condition.py

Net result: spell.py goes from ~270 lines to ~120 lines while producing richer output.

### Step 4: Add Tests

**File**: `tests/test_integration.py`

New `TestSpellResolution` class:

| Test | Description |
|---|---|
| T1 | Query Spell DBC with `resolve=true` → should include `conditions` in `$resolved_fields` |
| T2 | Spell with OBJECT_ENTRY_GUID conditions → structured `values.target_entity` with creature/item names |
| T3 | Spell with no conditions → no `conditions` key in output |
| T4 | `resolve=false` → no conditions fetched (SQL guard works) |
| T5 | `resolve_max` limit enforcement → warning message when conditions exceed limit |

Test approach: Pick a well-known spell ID (e.g., 48649 with 191 conditions) and verify
the structure and content of the resolved output.

### Step 5: Update Progress Tracking

**File**: `BATCH_PROGRESS.md`

Add Phase 9E entry with status and commit hash.

## Files Modified

| File | Change |
|---|---|
| `core/resolvers/spell.py` | Refactor: import from condition.py, add pre-warming, ~150 lines removed |
| `core/resolvers/__init__.py` | Already modified (uncommitted) — spell resolver registration |
| `tests/test_integration.py` | Add `TestSpellResolution` class (~80 lines) |
| `BATCH_PROGRESS.md` | Update with Phase 9E status |

## Performance Impact

| Scenario | Before | After |
|---|---|---|
| Single spell (10 conditions) | ~30 individual queries | ~4 batch queries |
| 20 spells (200 conditions) | ~200 individual queries | ~8 batch queries |
| Subsequent requests (any) | Same | ~0 (TTL cache) |

## Commit Message Template

```
Phase 9E: Spell → Conditions cross-reference resolver with shared resolution

- Refactor spell.py to delegate condition resolution to condition.py's shared
  functions (_resolve_condition_source, _resolve_condition_values, _collect_condition_ids)
- Add pre-warming: batch-resolve all condition value SQL/DBC refs before formatting loop
- Remove ~150 lines of duplicated enum maps and condition handlers from spell.py
- Structured output replaces flat "meaning" strings for machine-readability
- Add TestSpellResolution class with 5 tests
- Register Spell and spell_dbc resolvers in __init__.py
```
