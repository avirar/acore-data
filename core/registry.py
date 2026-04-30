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
        """Find field names similar to the given key using fuzzy matching."""
        fields = reg_entry.get("fields", {})
        key_lower = str(key).lower()
        suggestions = []

        for idx_str, info in fields.items():
            field_name = info.get("name", "")
            sql_col = info.get("sql_column", "")

            for name in [field_name, sql_col]:
                if not name:
                    continue

                n_lower = name.lower()

                if key_lower in n_lower or n_lower in key_lower:
                    suggestions.append(name)
                    continue

                if len(key_lower) >= 3 and n_lower.startswith(key_lower[:3]):
                    suggestions.append(name)

        seen = set()
        unique: List[str] = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique.append(s)

        return unique[:10]

    def _resolve_filter_key(
        self, key, reg_entry: Dict, dbc_name: str, all_tables: Set[str]
    ) -> Tuple[int, str, Optional[str]]:
        """Resolve filter key to DBC field index. Returns (index, resolved_name, note)."""
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

        # Check field name cache first
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

        # Fuzzy match
        suggestions = self._find_similar_field_names(key, reg_entry)
        error = f"Filter key '{key}' not found in {dbc_name}."
        if suggestions:
            error += f"\n  Did you mean: {', '.join(suggestions[:5])}"
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
