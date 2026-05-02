"""
Registry module for acore-data.

Handles datastore metadata lookup, name resolution, fuzzy matching,
and field name caching.
"""

import json
import difflib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set


class Registry:
    """Datastore registry for cross-referencing AzerothCore datastores."""

    def __init__(self, registry_path: str):
        """
        Initialize the registry.

        Args:
            registry_path: Path to datastore_registry.json
        """
        self.registry_path = Path(registry_path)
        self.registry: Dict[str, Any] = {"entries": {}, "indices": {}}
        self._field_name_cache: Dict[str, Dict[str, List[Dict]]] = {}

        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self.registry = json.load(f)
            except Exception:
                pass

    def _build_field_name_cache(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Pre-compute field name → index mapping for all DBC-backed stores."""
        cache: Dict[str, Dict[str, List[Dict]]] = {}
        entries = self.registry.get("entries", {})

        for struct_name, entry in entries.items():
            if entry.get("category") != "dbc_backed":
                continue

            dbc_name = entry.get("dbc_name", "")
            if not dbc_name:
                continue

            cache[dbc_name.lower()] = {}

            for idx_str, field_info in entry.get("fields", {}).items():
                c_field = field_info.get("name", "")
                sql_col = field_info.get("sql_column", "")
                idx = int(idx_str)
                ftype = field_info.get("type", "unknown")

                if c_field:
                    c_lower = c_field.lower()
                    if c_lower not in cache[dbc_name.lower()]:
                        cache[dbc_name.lower()][c_lower] = []
                    cache[dbc_name.lower()][c_lower].append({
                        "index": idx,
                        "type": ftype,
                        "source": "c_struct",
                        "sql_column": sql_col,
                        "original_name": c_field
                    })

                if sql_col and sql_col.lower() != c_field.lower():
                    s_lower = sql_col.lower()
                    if s_lower not in cache[dbc_name.lower()]:
                        cache[dbc_name.lower()][s_lower] = []
                    cache[dbc_name.lower()][s_lower].append({
                        "index": idx,
                        "type": ftype,
                        "source": "sql_column",
                        "c_struct_field": c_field,
                        "original_name": sql_col
                    })

        return cache

    def _resolve_entry(self, name: str) -> Optional[Tuple[str, Dict]]:
        """Resolve a name to (struct_name, entry) using all lookup indices."""
        entries = self.registry.get("entries", {})
        indices = self.registry.get("indices", {})

        # Direct struct name lookup
        if name in entries:
            return name, entries[name]

        # Try each index
        for idx_name in ["by_sql_table", "by_dbc_name", "by_dbc_file", "by_store_variable"]:
            idx = indices.get(idx_name, {})
            if name in idx:
                struct_name = idx[name]
                if struct_name in entries:
                    return struct_name, entries[struct_name]

        # Try with "Entry" suffix for DBC names
        if name + "Entry" in entries:
            return name + "Entry", entries[name + "Entry"]

        # Try stripping "Entry" suffix
        if name.endswith("Entry"):
            stripped = name[:-5]
            if stripped in entries:
                return stripped, entries[stripped]
            for idx in indices.values():
                if stripped in idx:
                    struct_name = idx[stripped]
                    if struct_name in entries:
                        return struct_name, entries[struct_name]

        return None

    def _find_similar_field_names(self, key: str, reg_entry: Dict) -> List[str]:
        """Find field names similar to the given key using relevance-ranked fuzzy matching.

        Compact display: bracket-indexed families shown as `BaseName[0-2]` (one suggestion slot).
        Groups by base family name so distinct fields get representation instead of
        a single family consuming all 12 slots via [0],[1],[2] variants.
        """
        fields = reg_entry.get("fields", {})
        key_lower = str(key).lower()

        # Group field names by base family: e.g., EffectItemType[0/1/2] + EffectItemType -> family "effectitemtype"
        # Each entry: {highest_score, display_name, slot_indices}
        families: Dict[str, Dict] = {}

        for idx_str, info in fields.items():
            field_name = info.get("name", "")
            sql_col = info.get("sql_column", "")

            for name in [field_name, sql_col]:
                if not name:
                    continue

                score = self._score_for_name(name, key_lower)
                if score <= 0.0:
                    continue

                n_lower = name.lower()

                # Determine base family key: strip bracket notation for grouping
                bracket_match = re.match(r'^([^\[]+)\[(\d+)\]$', n_lower)
                family_key = bracket_match.group(1).lower() if bracket_match else n_lower
                slot_idx = int(bracket_match.group(2)) if bracket_match else None

                if family_key not in families:
                    families[family_key] = {"score": 0, "name": "", "slots": []}

                fam = families[family_key]
                if score > fam["score"]:
                    fam["score"] = score
                    fam["name"] = name
                if slot_idx is not None and slot_idx not in fam["slots"]:
                    fam["slots"].append(slot_idx)

        # Sort families by score descending
        ranked = sorted(families.values(), key=lambda f: -f["score"])

        # Build compact display list
        result = []
        for fam in ranked[:12]:
            if fam["slots"]:
                slots = sorted(fam["slots"])
                compact = f"{fam['name'].split('[')[0]}[{slots[0]}-{slots[-1]}]" if len(slots) > 1 else f"{fam['name'].split('[')[0]}[{slots[0]}]"
                result.append(compact)
            else:
                result.append(fam["name"])

        return result

    def _score_for_name(self, name: str, key_lower: str) -> float:
        """Compute relevance score for a suggestion name against the search key."""
        n_lower = name.lower()
        if key_lower == n_lower:
            return 10.0

        score = 0.0

        # Substring containment — penalize short matches that barely cover the key
        if key_lower in n_lower or n_lower in key_lower:
            ratio = len(min(key_lower, n_lower, key=len)) / max(len(key_lower), len(n_lower))
            score = max(score, 5.0 if ratio > 0.6 else 2.0)

        # Base name match (strips trailing slot/underscore number)
        norm = re.match(r'^(.+?)_(\d+)$', key_lower) or re.match(r'^(.+?)\[(\d+)\]$', key_lower)
        if norm:
            base = norm.group(1)
            if base in n_lower or n_lower.startswith(base):
                score = max(score, 3.0)

        # Prefix match (weak signal)
        if len(key_lower) >= 3 and n_lower.startswith(key_lower[:3]):
            score = max(score, 1.0)

        # Fuzzy: SequenceMatcher for misspellings/near-misses
        ratio = difflib.SequenceMatcher(None, key_lower, n_lower).ratio()
        if ratio > 0.45:
            fuzzy_score = ratio * 3.0  # maps 0.45-1.0 → ~1.35-3.0
            score = max(score, fuzzy_score)

        return score

    def _find_sibling_indices(self, key: str, dbc_name: str) -> Tuple[Optional[int], List[int]]:
        """Find sibling array slots for a filter key that matches a bare base field name.

        If the key matches multiple array slots in the DBC cache (e.g., EffectMiscValue → indices 110, 111, 112),
        returns (primary_index, [sibling_indices]).

        Returns (None, []) if the key doesn't need multi-slot OR expansion.
        """
        key_lower = str(key).lower().strip()
        dbc_cache = self._field_name_cache.get(dbc_name.lower(), {})

        matches = dbc_cache.get(key_lower, [])
        if len(matches) < 2:
            return None, []

        # Check if all matches are for the same SQL column (array field family)
        sql_cols = set()
        indices = []
        for m in matches:
            sql_cols.add(m.get("sql_column", ""))
            indices.append(m["index"])

        if len(sql_cols) == 1 and indices:
            primary = min(indices)
            siblings = [i for i in sorted(indices) if i != primary]
            return primary, siblings

        return None, []

    def _resolve_filter_key(
        self, key, reg_entry: Dict, dbc_name: str, all_tables: Set[str]
    ) -> Tuple[int, str, Optional[str]]:
        """Resolve filter key to DBC field index. Returns (index, resolved_name, note).

        Supports multiple notations:
        - Integer index: "110" → field at position 110
        - C struct bracket: "EffectMiscValue[0]" → exact match
        - SQL underscore alias: "EffectMiscValue_1" → EffectMiscValue[0] (1-based→0-based)
        - SQL column name: "EffectMiscValue" → first slot (with note about ambiguity)
        """
        try:
            idx = int(key)
            return idx, str(idx), None
        except (ValueError, TypeError):
            pass

        if not reg_entry:
            raise ValueError(
                f"Filter key '{key}' is not numeric and no registry info available. "
                f"Use lookup(name='{dbc_name}') to see available fields."
            )

        dbc_lower = dbc_name.lower()
        key_str = str(key)
        key_lower = key_str.lower().strip()

        # Check field name cache first (exact match on bracket notation or SQL column)
        dbc_cache = self._field_name_cache.get(dbc_lower, {})

        if key_lower in dbc_cache:
            matches = dbc_cache[key_lower]
            if len(matches) == 1:
                return matches[0]["index"], matches[0].get("original_name", key), None
            else:
                best = min(matches, key=lambda m: m["index"])
                locale_idx = (
                    int(best["index"] % 16)
                    if "array" in str(best.get("type", "")).lower()
                    or "[" in best.get("original_name", "")
                    else 0
                )
                note = f"Field '{key}' matches {len(matches)} array elements. Using [{locale_idx}] (default locale)."
                return best["index"], best.get("original_name", key), note

        # Array notation: FieldName[0]
        array_match = re.match(r'^(.+?)\[(\d+)\]$', key_str)
        if array_match:
            base_field, array_idx = array_match.groups()
            fields = reg_entry.get("fields", {})
            for idx_str, info in fields.items():
                field_name = info.get("name", "")
                if field_name.lower() == f"{base_field.lower()}[{array_idx}]":
                    return int(idx_str), key_str, None

        # SQL underscore alias: FieldName_N → FieldName[N-1] (1-based to 0-based)
        underscore_match = re.match(r'^(.+?)_(\d+)$', key_str)
        if underscore_match:
            base_field = underscore_match.group(1)
            slot_number = int(underscore_match.group(2))
            # Convert 1-based (SQL convention) to 0-based (DBC bracket notation)
            zero_based_slot = slot_number - 1
            bracket_form = f"{base_field}[{zero_based_slot}]"
            bracket_lower = bracket_form.lower()

            if bracket_lower in dbc_cache:
                matches = dbc_cache[bracket_lower]
                if len(matches) == 1:
                    return matches[0]["index"], matches[0].get("original_name", bracket_form), None

            # Also try direct array match against fields
            fields = reg_entry.get("fields", {})
            for idx_str, info in fields.items():
                field_name = info.get("name", "")
                if field_name.lower() == bracket_lower:
                    return int(idx_str), bracket_form, None

        # Fuzzy match with improved suggestions
        suggestions = self._find_similar_field_names(key, reg_entry)
        error = f"Filter key '{key}' not found in {dbc_name}."
        if suggestions:
            # Add underscore alias hint to relevant suggestions
            error += f"\n  Did you mean: {', '.join(suggestions[:8])}"
            if underscore_match:
                base_field = underscore_match.group(1)
                matching_bracket = [s for s in suggestions if s.lower().startswith(base_field.lower() + "[")]
                if matching_bracket:
                    error += f"\n  (Used 1-based slot notation. Try {matching_bracket[0]} or {base_field}_1, {base_field}_2, ...)"
        error += f"\n\n  Use lookup(name='{dbc_name}') for complete field list."
        raise ValueError(error)

    def _suggest_similar_store(
        self, name: str, all_tables: Set[str]
    ) -> List[Tuple[str, str, float]]:
        """Fuzzy match against registry entries AND SQL tables.
        
        Returns: [(suggestion_name, category_hint, similarity_score), ...]
        
        Matches on:
        - C++ struct names (SpellEntry, CreatureEntry)
        - SQL table names (quest_template, spell_proc_event)  
        - Store variables (sSpellStore)
        - All discovered DB tables (arena_team from acore_characters)
        """
        candidates = []
        
        # Add registry struct names
        for struct_name, entry in self.registry.get("entries", {}).items():
            candidates.append(struct_name.lower())
            
            # SQL table
            sql_table = entry.get("sql_table", "")
            if sql_table:
                candidates.append(sql_table.lower())
                
            # Store variable
            store_var = entry.get("store_variable", "")
            if store_var:
                candidates.append(store_var.lower())
        
        # Add all discovered tables (includes multi-DB coverage)
        candidates.extend(all_tables)
        
        name_lower = name.lower()
        matches = difflib.get_close_matches(name_lower, candidates, n=10, cutoff=0.45)
        
        # Deduplicate and add category hints
        seen = {}
        for m in matches:
            if m in seen:
                continue
            
            # Determine category hint
            if m in self.registry.get("indices", {}).get("by_struct_name", {}):
                category = "struct"
            elif m.endswith("_dbc"):
                category = "dbc_overlay"
            elif "_dbc" not in m and any(
                m == e.get("c_struct", "").lower()
                for e in self.registry.get("entries", {}).values()
            ):
                category = "struct"
            else:
                category = "table"
            
            score = difflib.SequenceMatcher(None, name_lower, m).ratio()
            seen[m] = (m, category, score)
        
        # Sort by similarity score descending
        sorted_suggestions = sorted(seen.values(), key=lambda x: x[2], reverse=True)
        return sorted_suggestions[:5]
