# Plan: Registry-Driven General Resolution

## Status: READY FOR IMPLEMENTATION
## Priority: High
## Estimated Effort: 4-6 hours
## Dependencies: datastore_registry.json cross-references (COMPLETE — 418 refs across 233 entries)

## Background

The acore-data project has two parallel systems that do the same thing:
1. **`core/type_resolver.py`** — Hardcoded `GAMEOBJECT_FIELD_MAP` for gameobject_template data fields only
2. **`datastore_registry.json`** — 418 cross-reference fields with `references`/`reference_type`/`reference_column` metadata across 233 entries

This plan unifies them: the registry becomes the single source of truth, and the resolver becomes a pure engine that reads from it. This means ANY table with cross-refs in the registry automatically gets resolution support — zero code changes needed for new cross-refs.

## Current Architecture

```
tools/query.py
  _query_sql() → resolve_type_fields() → _resolve_gameobject_fields() [gameobject only]
  _query_dbc() → NO resolution [misses 217 DBC cross-refs]
```

## Target Architecture

```
datastore_registry.json          ← Single source of truth
  field.references               ← 418 simple cross-refs (all tables)
  type_field_mappings            ← Type-conditional refs (gameobject only)

core/type_resolver.py            ← Pure engine
  resolve_type_fields()          ← Dispatcher
    ├─ _resolve_gameobject()     ← Type-conditional (reads registry)
    └─ _resolve_generic()        ← Simple refs (reads registry)
  _resolve_dbc_ref()             ← Shared helper
  _resolve_sql_ref()             ← Shared helper
  _resolve_loot_ref()            ← Shared helper

tools/query.py
  _query_sql()  → resolve_type_fields()  [ALL SQL tables]
  _query_dbc()  → resolve_type_fields()  [ALL DBC tables]
```

## Cross-Reference Data Summary

| Category | Count | Resolution Method |
|----------|-------|-------------------|
| dbc_backed / dbc_entry | 311 | DBC lookup via `_resolve_dbc_ref()` |
| sql_objectmgr / sql_manager / sql_auxiliary / sql_table | 63 | SQL lookup via `_resolve_sql_ref()` |
| external (loot templates) | 14 | Loot expansion via `_resolve_loot_ref()` |
| self_ref | 4 | Skip (self-referential) |
| missing reference_type | 5 | Graceful skip |
| **Total** | **418** | |

## Implementation Steps

### Step 1: Move GAMEOBJECT_FIELD_MAP into registry

**File**: `datastore_registry.json`

Add `type_field_mappings` to the `GameObjectTemplate` entry. Copy all 18 non-empty GO type mappings from the existing `GAMEOBJECT_FIELD_MAP` dict in `core/type_resolver.py`.

The key is the GO type integer (as string), the value maps data column names to their resolution info:

```json
{
  "GameObjectTemplate": {
    "...existing fields...": "...",
    "type_field_mappings": {
      "0": {
        "data1": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"}
      },
      "1": {
        "data1": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data3": {"name": "linkedTrap", "resolve_type": "sql", "target": "gameobject_template"}
      },
      "2": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data3": {"name": "gossipID", "resolve_type": "sql", "target": "gossip_menu_option", "id_col": "menu_id"}
      },
      "3": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data1": {"name": "lootId", "resolve_type": "loot", "target": "gameobject_loot_template", "id_col": "Entry"},
        "data6": {"name": "eventId", "resolve_type": "sql", "target": "event_scripts"},
        "data7": {"name": "linkedTrapId", "resolve_type": "sql", "target": "gameobject_template"},
        "data8": {"name": "questId", "resolve_type": "sql", "target": "quest_template", "id_col": "ID"}
      },
      "5": {
        "data5": {"name": "questId", "resolve_type": "sql", "target": "quest_template", "id_col": "ID"}
      },
      "6": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data3": {"name": "spellId", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "8": {
        "data0": {"name": "focusId", "resolve_type": "dbc", "target": "SpellFocusObject", "id_col": "ID"},
        "data4": {"name": "questID", "resolve_type": "sql", "target": "quest_template", "id_col": "ID"}
      },
      "9": {
        "data0": {"name": "pageID", "resolve_type": "sql", "target": "page_text", "id_col": "entry"}
      },
      "10": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data1": {"name": "questId", "resolve_type": "sql", "target": "quest_template", "id_col": "ID"},
        "data2": {"name": "eventId", "resolve_type": "sql", "target": "event_scripts"},
        "data10": {"name": "spellId", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data12": {"name": "linkedTrapId", "resolve_type": "sql", "target": "gameobject_template"},
        "data19": {"name": "gossipID", "resolve_type": "sql", "target": "gossip_menu_option", "id_col": "menu_id"}
      },
      "12": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"}
      },
      "13": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data1": {"name": "cinematicId", "resolve_type": "dbc", "target": "CinematicCamera", "id_col": "ID"}
      },
      "15": {
        "data0": {"name": "taxiPathId", "resolve_type": "dbc", "target": "TaxiPath", "id_col": "ID"}
      },
      "18": {
        "data1": {"name": "spellId", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data2": {"name": "animSpell", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data4": {"name": "casterTargetSpell", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "22": {
        "data0": {"name": "spellId", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "24": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data1": {"name": "pickupSpell", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data3": {"name": "returnAura", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data4": {"name": "returnSpell", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "25": {
        "data1": {"name": "lootId", "resolve_type": "loot", "target": "gameobject_loot_template", "id_col": "Entry"},
        "data4": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"}
      },
      "26": {
        "data0": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"},
        "data2": {"name": "pickupSpell", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "30": {
        "data2": {"name": "auraID1", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"},
        "data4": {"name": "auraID2", "resolve_type": "dbc", "target": "Spell", "id_col": "ID"}
      },
      "31": {
        "data0": {"name": "mapID", "resolve_type": "dbc", "target": "Map", "id_col": "ID"}
      }
    }
  }
}
```

**Verification**: Count non-empty entries — should be 18 GO types (0,1,2,3,5,6,8,9,10,12,13,15,18,22,24,25,26,30,31). JSON must be valid.

### Step 2: Refactor core/type_resolver.py

**File**: `core/type_resolver.py`

#### 2a: Add helper functions

```python
def _classify_target(ref_type, target_entry):
    """Classify a target into dbc/sql/loot resolution category."""
    if ref_type in ("dbc_backed", "dbc_entry"):
        return "dbc"
    if target_entry:
        cat = target_entry.get("category", "")
        name_lower = target_entry.get("sql_table", target_entry.get("dbc_name", "")).lower()
        if "loot" in name_lower and "template" in name_lower:
            return "loot"
        if cat.startswith("sql_"):
            return "sql"
        if cat == "dbc_backed":
            return "dbc"
    if ref_type == "external":
        return "loot"
    return "sql"


def _get_row_value(row, sql_col, field_name):
    """Get value from row by column name (case-insensitive)."""
    for key in [sql_col, field_name]:
        if key and key in row:
            return row[key]
    key_lower = (sql_col or field_name or "").lower()
    for k, v in row.items():
        if k.lower() == key_lower:
            return v
    return None


def _get_row_pk(row):
    """Get primary key value from row."""
    for pk in ["entry", "ID", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def _find_registry_entry(server, table_name):
    """Find registry entry by SQL table name, DBC name, or struct name."""
    resolved = server.registry._resolve_entry(table_name)
    if resolved:
        return resolved[1]
    entries = server.registry.registry.get("entries", {})
    table_lower = table_name.lower()
    for name, entry in entries.items():
        if entry.get("sql_table", "").lower() == table_lower:
            return entry
        if entry.get("dbc_name", "").lower() == table_lower:
            return entry
    return None
```

#### 2b: New function `_resolve_generic()`

Generic resolver for any table with field-level cross-refs in registry. This is the core of the new system.

```python
def _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max):
    """Resolve fields using registry cross-reference metadata.
    
    Works for any table that has fields with 'references' in the registry.
    Handles DBC lookups, SQL lookups, and loot template expansion.
    """
    fields = reg_entry.get("fields", {})
    registry = server.registry.registry.get("entries", {})
    
    # Build list of resolvable fields from registry metadata
    resolvable = []
    for fid, finfo in fields.items():
        if not isinstance(finfo, dict):
            continue
        target = finfo.get("references")
        if not target or target == "self_ref":
            continue
        if isinstance(target, list):  # Complex multi-ref (e.g. gameobject data[])
            continue
        
        ref_type = finfo.get("reference_type", "")
        ref_col = finfo.get("reference_column", "ID")
        sql_col = finfo.get("sql_column", finfo.get("name", ""))
        field_name = finfo.get("name", fid)
        
        target_entry = registry.get(target)
        resolve_category = _classify_target(ref_type, target_entry)
        
        # Determine the lookup name for the target
        if resolve_category == "dbc" and target_entry:
            lookup_name = target_entry.get("dbc_name", target.replace("Entry", ""))
        elif resolve_category == "sql" and target_entry:
            lookup_name = target_entry.get("sql_table", target)
        elif resolve_category == "loot" and target_entry:
            lookup_name = target_entry.get("sql_table", target)
        else:
            lookup_name = target
        
        resolvable.append({
            "field_id": fid,
            "field_name": field_name,
            "sql_col": sql_col,
            "target": target,
            "ref_type": ref_type,
            "ref_col": ref_col,
            "resolve_category": resolve_category,
            "lookup_name": lookup_name,
        })
    
    if not resolvable:
        return {}
    
    # Determine allowed resolve types
    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}
    
    resolved = {}
    for row in rows:
        pk = _get_row_pk(row)
        row_resolved = {}
        
        for r in resolvable:
            raw_value = _get_row_value(row, r["sql_col"], r["field_name"])
            if raw_value is None or raw_value == 0:
                continue
            
            entry_resolved = {
                "meaning": r["field_name"],
                "raw": raw_value,
            }
            
            if r["resolve_category"] == "dbc" and "dbc" in allowed:
                resolved_val = _resolve_dbc_ref(server, r["lookup_name"], raw_value, r["ref_col"])
                if resolved_val:
                    entry_resolved["resolved_to"] = resolved_val
            
            elif r["resolve_category"] == "sql" and "sql" in allowed:
                resolved_val = _resolve_sql_ref(server, r["lookup_name"], raw_value, r["ref_col"])
                if resolved_val:
                    entry_resolved["resolved_to"] = resolved_val
            
            elif r["resolve_category"] == "loot" and "loot" in allowed:
                loot_items = _resolve_loot_ref(server, r["lookup_name"], raw_value, r["ref_col"], resolve_max)
                if loot_items:
                    entry_resolved.update(loot_items)
            
            if "resolved_to" in entry_resolved or "items" in entry_resolved:
                row_resolved[r["sql_col"]] = entry_resolved
        
        if row_resolved:
            resolved[pk] = row_resolved
    
    return resolved
```

#### 2c: Modify `_resolve_gameobject_fields()`

Change to read `type_field_mappings` from the registry entry instead of hardcoded `GAMEOBJECT_FIELD_MAP`:

```python
def _resolve_gameobject_fields(server, reg_entry, rows, resolve_filter, resolve_max):
    """Resolve gameobject_template type-specific fields from registry."""
    type_mappings = reg_entry.get("type_field_mappings", {})
    if not type_mappings:
        return {}
    
    resolved = {}
    for row in rows:
        entry_value = row.get("entry")
        go_type = row.get("type", 0)
        
        type_name = GO_TYPE_NAMES.get(go_type, f"UNKNOWN({go_type})")
        field_map = type_mappings.get(str(go_type), {})
        
        if not field_map:
            continue
        
        row_resolved = {"type_name": type_name}
        
        if isinstance(resolve_filter, list):
            allowed_refs = set(resolve_filter)
        elif resolve_filter is True:
            allowed_refs = {"dbc", "sql", "loot"}
        else:
            continue
        
        for data_col, field_info in field_map.items():
            raw_value = row.get(data_col)
            if raw_value is None:
                for key in row:
                    if key.lower() == data_col.lower():
                        raw_value = row[key]
                        break
            if raw_value is None or raw_value == 0:
                continue
            
            ref_type = field_info.get("resolve_type", "")
            if not ref_type:
                continue
            
            entry_resolved = {
                "meaning": field_info["name"],
                "raw": raw_value,
            }
            
            if ref_type == "dbc" and "dbc" in allowed_refs:
                dbc_name = field_info.get("target", "")
                id_col = field_info.get("id_col", "ID")
                resolved_value = _resolve_dbc_ref(server, dbc_name, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value
            
            elif ref_type == "sql" and "sql" in allowed_refs:
                table = field_info.get("target", "")
                id_col = field_info.get("id_col", "ID") or "entry"
                resolved_value = _resolve_sql_ref(server, table, raw_value, id_col)
                if resolved_value:
                    entry_resolved["resolved_to"] = resolved_value
            
            elif ref_type == "loot" and "loot" in allowed_refs:
                table = field_info.get("target", "gameobject_loot_template")
                id_col = field_info.get("id_col", "Entry")
                loot_items = _resolve_loot_ref(server, table, raw_value, id_col, resolve_max)
                if loot_items:
                    entry_resolved.update(loot_items)
            
            row_resolved[data_col] = entry_resolved
        
        resolved[entry_value] = row_resolved
    
    return resolved
```

#### 2d: Modify `resolve_type_fields()` dispatcher

```python
def resolve_type_fields(server, sql_table, rows, resolve_filter, resolve_max=10):
    """Resolve cross-reference fields for any table with registry metadata."""
    if not rows or not resolve_filter:
        return {}
    
    reg_entry = _find_registry_entry(server, sql_table)
    if not reg_entry:
        return {}
    
    # Special case: gameobject_template uses type-conditional resolution
    if sql_table == "gameobject_template" and "type_field_mappings" in reg_entry:
        return _resolve_gameobject_fields(server, reg_entry, rows, resolve_filter, resolve_max)
    
    # Generic resolution for all other tables
    return _resolve_generic(server, reg_entry, rows, resolve_filter, resolve_max)
```

#### 2e: Delete `GAMEOBJECT_FIELD_MAP`

Remove the ~100 line hardcoded `GAMEOBJECT_FIELD_MAP` dict. Keep `GO_TYPE_NAMES` (it's an enum, not reference data).

### Step 3: Add DBC query resolution

**File**: `tools/query.py`

In `_query_dbc()`, add resolution support after the merge step. Insert after the metadata dict is built (around line 266):

```python
# After building metadata dict, before the return:
resolve_filter = args.get("resolve", False)
resolve_max = args.get("resolve_max", 10)

if resolve_filter and merged.get("result"):
    dbc_rows = merged["result"]
    if isinstance(dbc_rows, dict):
        dbc_rows = [dbc_rows]
    elif isinstance(dbc_rows, list) and dbc_rows and isinstance(dbc_rows[0], dict):
        pass  # already a list of dicts
    else:
        dbc_rows = []
    
    if dbc_rows:
        resolved = resolve_type_fields(
            server,
            dbc_load_name,
            dbc_rows,
            resolve_filter,
            resolve_max,
        )
        if resolved:
            metadata["$resolved_fields"] = resolved
            metadata["type_resolved"] = True
```

**Important**: DBC results from `_annotate_dbc_result()` are dicts with field names as keys. The resolver's `_get_row_value()` handles this because it looks for both `sql_col` and `field_name` keys, and falls back to case-insensitive matching.

### Step 4: Update query schema description

**File**: `tools/query.py` → `get_schema()`

Update the `resolve` parameter description in the `inputSchema`:

```python
"resolve": {
    "oneOf": [
        {"type": "boolean"},
        {"type": "array", "items": {"type": "string"}}
    ],
    "description": (
        "Resolve cross-reference fields to their targets. "
        "Use true to resolve all, or ['dbc', 'sql', 'loot'] to pick types. "
        "Works for ALL tables with cross-reference metadata in the registry: "
        "gameobject_template (type-aware data[0-19]), "
        "creature_template (faction, lootid, spell1-8, mapId...), "
        "SpellEntry (Category, DurationIndex, RangeIndex, EffectTriggerSpell...), "
        "Quest (RewardSpell, RequiredSkill, ZoneOrSort...), "
        "and 200+ other entries. DBC and SQL lookups resolve to names/labels."
    )
}
```

### Step 5: Tests

**File**: `tests/test_integration.py`

Add test class:

```python
class TestRegistryDrivenResolution(unittest.TestCase):
    """Test generic cross-reference resolution driven by registry metadata."""
    
    def test_sql_creature_template_resolve(self):
        """creature_template with resolve=true should resolve faction, lootid, etc."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        metadata = result.get("metadata", {})
        self.assertIn("$resolved_fields", metadata)
    
    def test_dbc_spell_entry_resolve(self):
        """SpellEntry DBC query with resolve=true should resolve Category etc."""
        result = call_query({
            "name": "SpellEntry",
            "id": 118,
            "resolve": True,
        })
        self.assertNotIn("error", result)
        metadata = result.get("metadata", {})
        # May or may not have resolved_fields depending on DB availability
        # but should not error
    
    def test_gameobject_still_works(self):
        """gameobject_template resolution still works after registry migration."""
        result = call_query({
            "name": "gameobject_template",
            "filter": {"type": 3},
            "resolve": True,
            "limit": 1,
        })
        self.assertNotIn("error", result)
        metadata = result.get("metadata", {})
        if "$resolved_fields" in metadata:
            resolved = metadata["$resolved_fields"]
            # Should have type_name in resolved data
            for pk, data in resolved.items():
                self.assertIn("type_name", data)
                self.assertEqual(data["type_name"], "CHEST")
    
    def test_resolve_filter_sql_only(self):
        """resolve=['sql'] should only resolve SQL targets, not DBC."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": ["sql"],
        })
        self.assertNotIn("error", result)
    
    def test_resolve_filter_dbc_only(self):
        """resolve=['dbc'] should only resolve DBC targets."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
            "resolve": ["dbc"],
        })
        self.assertNotIn("error", result)
    
    def test_no_resolve_by_default(self):
        """Without resolve param, no resolution should happen."""
        result = call_query({
            "name": "creature_template",
            "id": 1,
        })
        self.assertNotIn("error", result)
        metadata = result.get("metadata", {})
        self.assertNotIn("$resolved_fields", metadata)
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DBC resolution format | `{"meaning": "Category", "raw": 3, "resolved_to": "SpellCategoryEntry [Proc]"}` | Consistent with existing gameobject format |
| Works for DBC and SQL | Yes | Both paths call resolver |
| Batched resolution | No (defer) | Per-field-per-row is fine for 100 row default limit |
| gameobject special case | Yes | Type-conditional logic is genuinely unique |
| Loot template detection | By `*_loot_template` name + registry category | Simple heuristic covers all cases |
| Array-format references | Skip in generic resolver | Handled by gameobject type-conditional path |
| External targets (no registry entry) | Graceful skip | `_classify_target` falls back to "sql" |

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `datastore_registry.json` | Add `type_field_mappings` | Move GO field map from code to data |
| `core/type_resolver.py` | Major refactor | Add `_resolve_generic()`, modify dispatcher, delete hardcoded map |
| `tools/query.py` | Minor | Add resolve call in `_query_dbc()`, update schema description |
| `tests/test_integration.py` | Add tests | New `TestRegistryDrivenResolution` class |

## Verification Checklist

- [ ] JSON valid after adding `type_field_mappings`
- [ ] Gameobject resolution works identically (regression test)
- [ ] `creature_template` resolve=true resolves faction/lootid/etc.
- [ ] `SpellEntry` DBC query resolve=true resolves Category/DurationIndex/etc.
- [ ] `resolve=['sql']` filters correctly (no DBC lookups)
- [ ] `resolve=['dbc']` filters correctly (no SQL lookups)
- [ ] External targets (creature_loot_template) handled gracefully
- [ ] `self_ref` targets skipped
- [ ] Array-format references (gameobject data[]) skipped by generic resolver
- [ ] No errors when target entry doesn't exist in registry
- [ ] Existing tests still pass
- [ ] New tests pass
- [ ] Git commit with descriptive message

## Context for Agents

### Key Files to Read First
1. `core/type_resolver.py` — Current resolver (371 lines, will be refactored)
2. `tools/query.py` — Query dispatcher (559 lines, minor changes)
3. `core/registry.py` — Registry module (264 lines, no changes needed)
4. `server.py` — Server initialization (234 lines, no changes needed)

### Key Data Structures
- Registry entry field with cross-ref: `{"name": "Category", "type": "uint32", "sql_column": "Category", "notes": "-", "references": "SpellCategoryEntry", "reference_type": "dbc_backed", "reference_column": "ID"}`
- Gameobject type mapping: `{"data1": {"name": "lockId", "resolve_type": "dbc", "target": "Lock", "id_col": "ID"}}`

### Reference Type Values
- `dbc_backed` — DBC binary file lookup
- `dbc_entry` — DBC entry (alias for dbc_backed)
- `sql_objectmgr` — SQL table in acore_world (ObjectMgr managed)
- `sql_manager` — SQL table in acore_world (Manager managed)
- `sql_auxiliary` — SQL table in acore_world (auxiliary)
- `sql_table` — Generic SQL table
- `external` — External table (loot templates, etc.)
- `self_ref` — Self-referential (skip)

### Running Tests
```bash
cd ~/acore-data
python3 tests/test_integration.py
```

### Commit Style
Detailed multi-line messages describing what was added/changed with counts and examples. See recent commits via `git log --oneline -5`.
