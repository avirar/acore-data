"""
Query tool for acore-data.

Merged from query_game_data + query_dbc.
Unified entry point for ALL data: DBC binary, SQL tables, overlays, auxiliary.

Parameters renamed: dbc_name -> name
"""

import difflib
import json
import re
import sys
from typing import Dict, Any, List, Optional, Tuple

from core.annotation import (
    _annotate_dbc_result as _annotate_dbc_impl,
    _build_schema_error as _build_schema_error_impl,
    _convert_filter_for_dbc as _convert_filter_for_dbc_impl,
    _dbc_filter_to_sql_where,
    _escape_like_pattern,
    _resolve_field_name_to_index,
    compact_sql_rows,
)
from core.type_resolver import resolve_type_fields


def _resolve_sql_column(
    reg_entry: Dict, key: str, sql_table: str
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a filter key to the actual SQL column name.

    Checks registry field definitions for both C++ struct field names
    and SQL column names with case-insensitive matching. Falls back
    to fuzzy matching suggestions.

    Returns:
        (resolved_sql_col, suggestion_or_error) -- if resolved_sql_col is None,
        the suggestion string contains available field hints.
    """
    fields = reg_entry.get("fields", {})
    key_lower = str(key).lower()

    # Exact match (case-insensitive) on sql_column first
    for idx_str, info in fields.items():
        sql_col = info.get("sql_column", "")
        if sql_col and sql_col.lower() == key_lower:
            return sql_col, None

        # Also match against the field key itself (registry may use sql_column as key)
        if str(idx_str).lower() == key_lower and sql_col:
            return sql_col, None

    # Match on C++ struct name -> resolve to SQL column
    for idx_str, info in fields.items():
        c_name = info.get("name", "")
        if c_name and c_name.lower() == key_lower:
            sql_col = info.get("sql_column", c_name)
            return sql_col or c_name, None

    # Fuzzy match — build deduplicated list of (display_name, lower_name)
    seen = set()
    all_names = []
    for idx_str, info in fields.items():
        for n in [info.get("sql_column", ""), info.get("name", ""), str(idx_str)]:
            if n:
                n_lower = n.lower()
                if n_lower not in seen:
                    seen.add(n_lower)
                    all_names.append((n, n_lower))

    suggestions_lower = difflib.get_close_matches(key_lower, [n[1] for n in all_names], n=5, cutoff=0.4)
    # Map back to original casing
    suggestion_map = {n[1]: n[0] for n in all_names}
    if not suggestions_lower and len(key_lower) >= 3:
        start_matches = [(n[0], n[1]) for n in all_names if n[1].startswith(key_lower[:3])][:5]
        suggestions_lower = [s[1] for s in start_matches]

    if suggestions_lower:
        display = [suggestion_map.get(s, s) for s in suggestions_lower[:5]]
        return None, f"Did you mean: {', '.join(display)}? "
    display_all = [n[0] for n in all_names[:10]]
    return None, f"Available fields ({min(len(all_names), 10)}): {', '.join(display_all)} "


def _build_sql_filter_clause(
    col_name: str, val: Any
) -> Tuple[Optional[str], Optional[str], bool]:
    """Build a single SQL WHERE clause from a column name and value.

    Handles $like / $ilike dict operators and exact match values.

    Returns:
        (fragment_with_%s_or_literal, param_value_or_None, is_error)
    """
    if isinstance(val, dict):
        if "$like" in val:
            pattern = _escape_like_pattern(val["$like"])
            return f"{col_name} LIKE %s", val["$like"], False
        elif "$ilike" in val:
            # MySQL case-insensitive: use LOWER() wrapper + lower'd param
            return f"LOWER({col_name}) LIKE LOWER(%s)", val["$ilike"].lower(), False
        return None, None, True

    if isinstance(val, str):
        return f"{col_name} = %s", val, False

    # Numeric / boolean values
    return f"{col_name} = %s", val, False


def _validate_fields_param(
    reg_entry: Dict, fields_param: List, display_name: str
) -> Optional[Dict[str, Any]]:
    """Validate field selectors against the registry. Returns an error dict or None."""
    fields_meta = reg_entry.get("fields", {})
    valid_numeric = {int(k) for k in fields_meta.keys() if k.isdigit()}
    all_names = []
    seen = set()
    for info in fields_meta.values():
        for n in [info.get("name", ""), info.get("sql_column", "")]:
            if n and n.lower() not in seen:
                seen.add(n.lower())
                all_names.append(n)

    for f in fields_param:
        ok = False
        if isinstance(f, bool):
            pass  # invalid, handled below
        elif isinstance(f, int) or (isinstance(f, str) and f.strip().isdigit()):
            ok = int(f) in valid_numeric
        elif isinstance(f, str):
            low = f.lower()
            ok = low in seen or bool(_resolve_field_name_to_index(f, fields_meta))

        if not ok:
            candidates = [n.lower() for n in all_names]
            num_candidates = [str(i) for i in sorted(valid_numeric)[:200]]
            sugg = difflib.get_close_matches(
                str(f).lower(), candidates + num_candidates, n=5, cutoff=0.4
            )
            msg = f"Unknown field '{f}' for {display_name}."
            if sugg:
                msg += f" Did you mean: {', '.join(sorted(set(sugg)))}?"
            return {"error": msg, "isError": True}

    return None


def _dbc_record_matches(record: Dict[int, Any], value: Any) -> bool:
    """Check a DBC field value against a filter value (supports $like/$ilike dicts)."""
    if isinstance(value, dict):
        if "$like" in value:
            pat, ci = value["$like"], False
        elif "$ilike" in value:
            pat, ci = value["$ilike"], True
        else:
            return False
        rx = re.escape(str(pat)).replace("\\%", ".*").replace("_", ".")
        hay = "" if record is None else str(record)
        return re.match("^" + rx + "$", hay, re.IGNORECASE if ci else 0) is not None
    return record == value


def query_tools(server):
    """
    Query any datastore.
    
    Args:
        server: Server instance with all modules
        
    Returns:
        {"result": [...], "metadata": {...}} or {"error": "...", "isError": True}
        
    Supported data:
      - DBC binary files (Spell, Item, SkillLine)
      - SQL ObjectMgr tables (quest_template, creature_template)
      - SQL Manager tables (smart_scripts, spell_proc_event)
      - Auxiliary tables (gameobject_questitem, loot templates)
      
    Features:
      - ID lookup (O(1) with index)
      - Named field filters
      - $like / $ilike pattern matching
      - Field selection by name or index
      - Compact mode strips nulls
      - Single-record unwrapping for ID lookups
    """
    name = server.args.get("name")
    if not name:
        return {"error": "name is required", "isError": True}

    resolved = server.registry._resolve_entry(name)
    
    if resolved:
        struct_name, entry = resolved
        category = entry.get("category", "")

        if category == "dbc_backed":
            return _query_dbc(server, args=server.args, reg_entry=entry)
        elif category in ("sql_objectmgr", "sql_manager", "sql_auxiliary"):
            return _query_sql(server, args=server.args, reg_entry=entry)

    # Fallback: fuzzy matching
    suggestions = server.registry._suggest_similar_store(
        name, server.database._all_tables_cache
    )
    if suggestions:
        formatted = [f"{n} ({c})" for n, c, _ in suggestions[:5]]
        return {
            "error": f"Store '{name}' not found.",
            "suggestion": f"Did you mean: {', '.join(formatted)}?",
            "isError": True,
        }

    # Last resort: try as raw DBC
    return _query_dbc(server, args=server.args, reg_entry=None)


def _query_dbc(
    server, args: Dict[str, Any], reg_entry: Optional[Dict]
) -> Dict[str, Any]:
    """Query DBC-backed store with optional SQL overlay."""
    name = args.get("name")
    id_value = args.get("id")
    row_index = args.get("row_index")
    filter_data = args.get("filter")
    fields_param = args.get("fields")
    limit = args.get("limit", 100)
    compact = args.get("compact", True)
    info_mode = args.get("info", False)

    dbc_load_name = reg_entry.get('dbc_name', name) if reg_entry else name

    # Info mode - return DBC metadata
    if info_mode:
        try:
            reader = server._load_dbc(dbc_load_name)
            info = reader.get_info()
            return {
                "result": {
                    "file": info["file"],
                    "record_count": info["record_count"],
                    "field_count": info["field_count"],
                    "record_size": info["record_size"],
                }
            }
        except Exception as e:
            return {"error": f"DBC error: {e}", "isError": True}

    # Strict validation of requested fields (unknown names -> error + suggestions)
    if fields_param and reg_entry:
        err = _validate_fields_param(reg_entry, fields_param, name)
        if err:
            return err

    # Convert named filter to numeric indices (with OR group detection)
    dbc_filter = {}
    filter_notes = []
    or_groups = None  # {primary_idx: [sibling_indices]} for multi-slot OR matching
    if filter_data and reg_entry:
        try:
            dbc_name_for_filter = reg_entry.get('dbc_name', name) if reg_entry else name
            dbc_filter, filter_notes, or_groups = _convert_filter_for_dbc_impl(
                server.registry, filter_data, reg_entry, dbc_name_for_filter
            )
        except ValueError as e:
            return _build_schema_error_impl(name, str(e), reg_entry, filter_data)

    # Query DBC
    dbc_result = None
    dbc_error = None

    try:
        reader = server._load_dbc(dbc_load_name)

        if id_value is not None:
            record = reader.get_record_by_id(id_value)
            if record and dbc_filter:
                # AND semantics: the record must also satisfy all filter conditions
                or_group_indices = {p for p in (or_groups or {}).keys()}
                ok = all(
                    any(
                        _dbc_record_matches(record.get(i), dbc_filter[p])
                        for i in [p] + or_groups[p]
                    )
                    for p in or_group_indices
                )
                if ok:
                    ok = all(
                        _dbc_record_matches(record.get(k), v)
                        for k, v in dbc_filter.items()
                        if k not in or_group_indices
                    )
                if not ok:
                    dbc_result = None
                    return {
                        "error": (
                            f"Record id {id_value} exists but does not satisfy the filter "
                            f"{json.dumps(filter_data)}. If this was a typo, adjust the "
                            f"filter; otherwise query without the id constraint."
                        ),
                        "isError": True,
                    }
                dbc_result = [record]
            else:
                dbc_result = [record] if record else []
        elif row_index is not None:
            record = reader.get_record(int(row_index))
            dbc_result = [record] if record else []
        elif dbc_filter:
            # Query with all non-OR-group filters first, then handle OR groups via post-filter
            or_group_indices = set()
            for primary, siblings in (or_groups or {}).items():
                or_group_indices.add(primary)

            and_filter = {k: v for k, v in dbc_filter.items() if k not in or_group_indices}
            dbc_result = reader.query(filter_dict=and_filter if and_filter else None)

            # Post-filter: OR across sibling slots for multi-slot fields
            if or_groups and dbc_result:
                def matches_or_group(record, primary_idx, siblings):
                    target_val = dbc_filter[primary_idx]
                    return any(record.get(i) == target_val for i in [primary_idx] + siblings)

                dbc_result = [r for r in dbc_result
                              if all(matches_or_group(r, p, s)
                                     for p, s in or_groups.items())]

            if limit and len(dbc_result) > limit:
                dbc_result = dbc_result[:limit]
        else:
            # Return all records (limited)
            dbc_result = []
            for i in range(min(limit, reader.record_count)):
                record = reader.get_record(i)
                if record:
                    dbc_result.append(record)
                else:
                    break

    except Exception as e:
        dbc_error = str(e)

    # Query SQL overlay
    sql_table = reg_entry.get("sql_table", "") if reg_entry else ""
    db_result = None
    db_error = None

    overlay_notes: list = []
    if sql_table and server.database.db_available:
        db_result, db_error, overlay_notes = _query_sql_overlay(
            server, sql_table, id_value, dbc_filter, limit, reg_entry
        )

    annotate_mode = bool(args.get("annotate", False))

    # Merge results
    merged = _merge_dbc_sql(
        server, dbc_result, db_result, reg_entry, fields_param, compact,
        id_value is not None, annotate_mode
    )

    if merged.get("error"):
        parts = []
        if dbc_error:
            parts.append(f"DBC {dbc_load_name}.dbc: {dbc_error}")
        elif dbc_result is None:
            parts.append(f"DBC {dbc_load_name}.dbc: not available")
        elif not dbc_result:
            parts.append(f"DBC {dbc_load_name}.dbc: 0 matching records")
        if db_error:
            parts.append(f"SQL overlay {sql_table}: {db_error}")
        elif sql_table and db_result is None:
            parts.append(f"SQL overlay {sql_table}: query not run (db unavailable)")
        elif sql_table and db_result == []:
            parts.append(f"SQL overlay {sql_table}: 0 matching rows")
        if overlay_notes:
            parts.append("overlay: " + "; ".join(dict.fromkeys(overlay_notes)))
        detail = " | ".join(parts) if parts else ""
        suffix = f": {detail}" if detail else ""
        id_part = f" (id {id_value})" if id_value is not None else ""
        return {
            "error": f"No data found for '{name}'{id_part}{suffix}",
            "isError": True,
        }

    if overlay_notes:
        filter_notes.extend(overlay_notes)

    metadata = {
        "source": merged.pop("source", "unknown"),
    }

    if reg_entry:
        c_struct = reg_entry.get("c_struct", "")
        if c_struct:
            metadata["c_struct"] = c_struct
        if sql_table:
            metadata["sql_table"] = sql_table
        store_variable = reg_entry.get("store_variable", "")
        if store_variable:
            metadata["store_variable"] = store_variable
        if args.get("hints"):
            refs = _extract_field_references(reg_entry)
            if refs:
                metadata["field_references"] = refs
            referenced_by = [
                rb for rb in reg_entry.get("referenced_by", []) if rb.get("field")
            ]
            if referenced_by:
                metadata["referenced_by"] = referenced_by

    if filter_notes:
        metadata["filter_notes"] = filter_notes

    # Resolve cross-reference fields for DBC-backed stores
    resolve_filter = args.get("resolve", False)
    resolve_max = args.get("resolve_max", 10)

    if resolve_filter and merged.get("result"):
        raw_rows = _extract_rows_for_resolution(merged["result"], id_value is not None)
        if raw_rows:
            resolved = resolve_type_fields(
                server, dbc_load_name, raw_rows, resolve_filter, resolve_max
            )
            if resolved:
                metadata["$resolved_fields"] = resolved
                metadata["type_resolved"] = True

    # Opt-in relation map: one hop to related rows (the C<->DBC<->SQL traversal)
    if args.get("links") and merged.get("result"):
        raw_rows = _extract_rows_for_resolution(merged["result"], id_value is not None)
        if raw_rows:
            # When `fields` narrowed the output, resolve against full rows
            # (bounded side-lookup on the PK) so link columns are present.
            if fields_param and reg_entry and sql_table and server.database.db_available:
                identity_name = (
                    reg_entry.get("fields", {}).get("0", {}).get("name", "ID")
                )
                ids = [
                    r.get(identity_name) for r in raw_rows[:25]
                    if isinstance(r, dict) and r.get(identity_name) is not None
                ] or [
                    r.get("ID") for r in raw_rows[:25]
                    if isinstance(r, dict) and r.get("ID") is not None
                ]
                if ids:
                    pk_col = server.database._find_primary_key(reg_entry, sql_table)
                    placeholders = ", ".join(["%s"] * len(ids))
                    link_sql = f"SELECT * FROM {sql_table} WHERE {pk_col} IN ({placeholders})"
                    full_rows, link_err = server.database._query_database(
                        link_sql, params=tuple(ids)
                    )
                    if not link_err and full_rows:
                        raw_rows = full_rows
                        metadata["links_note"] = (
                            "links resolved against full rows (extra lookup on selected ids)"
                        )
            resolved_links = resolve_type_fields(
                server, dbc_load_name, raw_rows[:25], True, 1
            )
            links = _shape_links(resolved_links)
            if links:
                metadata["links"] = links

    return {"result": merged.get("result", []), "metadata": metadata}


def _query_sql(
    server, args: Dict[str, Any], reg_entry: Dict
) -> Dict[str, Any]:
    """Query SQL-only store."""
    name = args.get("name")
    id_value = args.get("id")
    filter_data = args.get("filter")
    limit = args.get("limit", 100)
    compact = args.get("compact", True)
    resolve_filter = args.get("resolve", False)
    resolve_max = args.get("resolve_max", 10)

    sql_table = reg_entry.get("sql_table", "")
    if not sql_table:
        return {
            "error": f"No SQL table for {reg_entry.get('c_struct', 'unknown')}",
            "isError": True,
        }

    if not server.database.db_available:
        return {
            "error": (
                f"Database not available "
                f"({server.database.db_user}@{server.database.db_host}:{server.database.db_port}/{server.database.db_name})"
            ),
            "isError": True,
        }

    # Smart routing
    target_db = server.database._resolve_table_database(sql_table, server.database.db_name)
    if target_db:
        print(
            f"Routing query to {target_db} for table '{sql_table}'", file=sys.stderr
        )

    # Field selection (strict: unknown names are errors)
    fields_param = args.get("fields")
    pk_col = server.database._find_primary_key(reg_entry, sql_table)
    selected_cols: List[str] = []
    if fields_param:
        fields_meta = reg_entry.get("fields", {})
        seen_cols = set()
        # Identity column always travels with a narrowed selection
        if pk_col:
            seen_cols.add(pk_col.lower())
            selected_cols.append(pk_col)
        for f in fields_param:
            col = None
            if isinstance(f, bool):
                return {
                    "error": f"Invalid field selector: {f!r} (use a field name or index)",
                    "isError": True,
                }
            if isinstance(f, int) or (isinstance(f, str) and f.strip().isdigit()):
                info = fields_meta.get(str(int(f)))
                if info:
                    col = info.get("sql_column") or info.get("name") or str(f)
            elif isinstance(f, str):
                col, err = _resolve_sql_column(reg_entry, f, sql_table)
                if col is None:
                    return {
                        "error": f"Unknown field '{f}' for table '{sql_table}'. {err}",
                        "isError": True,
                    }
            else:
                return {
                    "error": f"Invalid field selector: {f!r} (use a field name or index)",
                    "isError": True,
                }
            if col and col.lower() not in seen_cols:
                seen_cols.add(col.lower())
                selected_cols.append(col)
        if not selected_cols:
            return {
                "error": f"No valid fields in {fields_param!r} for '{sql_table}'",
                "isError": True,
            }

    # Build SQL with parameterized values
    select_clause = ", ".join(selected_cols) if selected_cols else "*"
    sql = f"SELECT {select_clause} FROM {sql_table}"
    where_fragments = []
    params: list = []

    if id_value is not None and pk_col:
        where_fragments.append(f"{pk_col} = %s")
        params.append(id_value)

    if filter_data:
        for col, val in filter_data.items():
            resolved_col, err_msg = _resolve_sql_column(reg_entry, col, sql_table)
            if resolved_col is None:
                return {
                    "error": f"Unknown field '{col}' for table '{sql_table}'. {err_msg}",
                    "isError": True,
                }
            fragment, param_val, is_err = _build_sql_filter_clause(resolved_col, val)
            if is_err:
                return {
                    "error": f"Unsupported filter operator for '{col}'",
                    "isError": True,
                }
            where_fragments.append(fragment)
            params.append(param_val)

    if where_fragments:
        sql += " WHERE " + " AND ".join(where_fragments)

    sql += f" LIMIT {limit}"

    rows, error = server.database._query_database(sql, db_name=target_db, params=tuple(params))

    if error:
        error_msg = f"Database error: {error}"
        col_match = re.search(r"Unknown column '([^']+)'", error)
        if col_match:
            bad_col = col_match.group(1)
            suggestion = server.database._suggest_column(sql_table, bad_col)
            if suggestion:
                error_msg += f"\n{suggestion}"
        return {"error": error_msg, "isError": True}

    # Resolve type-specific fields (e.g. gameobject data[0-19] meanings)
    resolved = resolve_type_fields(server, sql_table, rows or [], resolve_filter, resolve_max)

    metadata = {
        "source": "database",
        "category": reg_entry.get("category", ""),
        "sql_table": sql_table,
        "c_struct": reg_entry.get("c_struct", ""),
        "store_variable": reg_entry.get("store_variable", ""),
        "primary_key": pk_col,
    }

    # Add cross-reference hints (opt-in)
    if args.get("hints"):
        refs = _extract_field_references(reg_entry)
        if refs:
            metadata["field_references"] = refs
        referenced_by = [
            rb for rb in reg_entry.get("referenced_by", []) if rb.get("field")
        ]
        if referenced_by:
            metadata["referenced_by"] = referenced_by

    mgr = reg_entry.get("manager_singleton", "")
    if mgr:
        metadata["manager_singleton"] = mgr

    if args.get("annotate") and server.database.db_available:
        schema = server.database._get_table_schema(sql_table, target_db)
        if schema:
            metadata["types"] = {
                c["COLUMN_NAME"]: c["DATA_TYPE"] for c in schema
            }

    if resolved:
        metadata["$resolved_fields"] = resolved
        metadata["type_resolved"] = True

    # Apply compact filtering to SQL results (before setting columns)
    if compact and rows:
        pk_col = metadata.get("primary_key", "")
        keep = set(selected_cols)
        if pk_col:
            keep.add(pk_col)
        rows = compact_sql_rows(rows, keep or None)

    # Set columns after compaction to reflect actual returned fields
    if rows:
        metadata["columns"] = list(rows[0].keys())
    elif server.database.db_available:
        schema = server.database._get_table_schema(sql_table, target_db)
        if schema:
            metadata["columns"] = [c["COLUMN_NAME"] for c in schema]

    # Opt-in relation map: one hop to related rows. Resolves against full
    # rows (bounded side-lookup on the PK) so link columns are present even
    # when `fields` narrowed the output.
    if args.get("links") and rows and pk_col:
        link_rows = rows
        if selected_cols:
            ids = [
                r.get(pk_col) for r in rows[:25]
                if isinstance(r, dict) and r.get(pk_col) is not None
            ]
            if ids:
                placeholders = ", ".join(["%s"] * len(ids))
                link_sql = f"SELECT * FROM {sql_table} WHERE {pk_col} IN ({placeholders})"
                link_rows, link_err = server.database._query_database(
                    link_sql, db_name=target_db, params=tuple(ids)
                )
                if not link_err and link_rows:
                    metadata["links_note"] = (
                        "links resolved against full rows (extra lookup on selected ids)"
                    )
                link_rows = link_rows or rows
        resolved_links = resolve_type_fields(server, sql_table, link_rows[:25], True, 1)
        links = _shape_links(resolved_links)
        if links:
            metadata["links"] = links

    return {"result": rows or [], "count": len(rows or []), "metadata": metadata}


def _query_sql_overlay(
    server, sql_table: str, id_value: Optional[int], dbc_filter: Dict, limit: int, reg_entry: Optional[Dict] = None
) -> tuple:
    """Query SQL overlay for DBC-backed store.

    Returns (rows, error, notes). Conditions on columns missing from the
    live overlay table are skipped (with a note) instead of raising a SQL
    error that would hide the DBC-side result.
    """
    sql = f"SELECT * FROM {sql_table}"
    where_fragments = []
    params: list = []
    notes: list = []

    if id_value is not None:
        pk_col = "ID"
        if len(dbc_filter) == 0:
            where_fragments.append(f"{pk_col} = %s")
            params.append(id_value)

    if dbc_filter:
        available_columns = None
        if server.database.db_available:
            target_db = server.database._resolve_table_database(sql_table, server.database.db_name)
            schema = server.database._get_table_schema(sql_table, target_db)
            if schema:
                available_columns = {c["COLUMN_NAME"].lower() for c in schema}
        clauses, notes = _dbc_filter_to_sql_where(dbc_filter, reg_entry, available_columns)
        for frag, param_val in clauses:
            where_fragments.append(frag)
            params.append(param_val)

    if where_fragments:
        sql += " WHERE " + " AND ".join(where_fragments)
    sql += f" LIMIT {limit}"

    rows, error = server.database._query_database(sql, params=tuple(params))
    return rows, error, notes


def _project_overlay_fields(
    rows: List[Dict[str, Any]],
    fields_param: Optional[List],
    reg_entry: Optional[Dict],
) -> Any:
    """Project overlay rows to the requested DBC fields (strict on miss).

    Live overlay tables use suffixed slot columns (e.g. EffectTriggerSpell_1)
    while the registry maps C names (EffectTriggerSpell) - try the base and
    the _1.._5 variants.
    """
    if not fields_param or not rows or not isinstance(rows[0], dict):
        return rows
    available = set(rows[0].keys())
    fields_meta = (reg_entry or {}).get("fields", {})
    selected: List[str] = []
    for f in fields_param:
        info: Optional[Dict] = None
        if isinstance(f, str):
            low = f.lower()
            for v in fields_meta.values():
                if v.get("name", "").lower() == low or v.get("sql_column", "").lower() == low:
                    info = v
                    break
        elif isinstance(f, int) and not isinstance(f, bool):
            info = fields_meta.get(str(f))
        base = (info.get("sql_column") or info.get("name") or str(f)) if info else str(f)
        cands = [base] + [f"{base}_{n}" for n in range(1, 6)]
        cand = next((c for c in cands if c in available), None)
        if cand is None:
            return {
                "error": (
                    f"Field '{base}' has no matching column in the overlay row. "
                    f"Available columns (sample): {sorted(available)[:15]}"
                ),
                "isError": True,
            }
        if cand not in selected:
            selected.append(cand)
    selected.append(next((c for c in ("ID", "Id") if c in available), ""))
    selected = [c for c in selected if c]
    return [{k: r[k] for k in selected if k in r} for r in rows]


def _merge_dbc_sql(
    server,
    dbc_result: List,
    db_result: Optional[List],
    reg_entry: Optional[Dict],
    fields_param: Optional[List],
    compact: bool,
    single_record: bool,
    annotate: bool = False,
) -> Dict[str, Any]:
    """Merge DBC and SQL results with annotation."""
    if db_result and not dbc_result:
        projected = _project_overlay_fields(db_result, fields_param, reg_entry)
        if isinstance(projected, dict) and projected.get("error"):
            return projected
        if compact and projected:
            projected = compact_sql_rows(projected, None)
        if single_record and isinstance(projected, list) and len(projected) == 1:
            projected = projected[0]
        return {"result": projected, "source": "database"}

    if dbc_result and not db_result:
        annotated = _annotate_dbc_result(
            dbc_result, reg_entry, None, fields_param, compact, single_record, annotate
        )
        return {"result": annotated, "source": "dbc"}

    if dbc_result and db_result:
        annotated = _annotate_dbc_result(
            dbc_result, reg_entry, db_result, fields_param, compact, single_record, annotate
        )
        return {"result": annotated, "source": "hybrid"}

    return {"error": "No data found", "isError": True}


def _row_to_flat(row_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert an annotated DBC row (list of field dicts) to a flat {name: value}.

    Locale/array fields (e.g. name[0..15]) are collapsed into their base
    name: a single non-empty slot becomes the scalar value, multiple
    non-empty slots become a list.
    """
    flat: Dict[str, Any] = {}
    groups: Dict[str, List[Any]] = {}

    for f in row_fields:
        name = f.get("name") or f"Field{f.get('index')}"
        m = re.match(r'^(.*?)\[(\d+)\]$', name)
        if m:
            groups.setdefault(m.group(1), []).append(f.get("value"))
        elif name not in flat:
            flat[name] = f.get("value")

    for base, vals in groups.items():
        non_empty = [v for v in vals if v is not None and v != ""]
        if len(non_empty) == 1:
            flat[base] = non_empty[0]
        elif len(non_empty) > 1:
            flat[base] = non_empty
    return flat


def _annotate_dbc_result(
    result: List,
    reg_entry: Optional[Dict],
    db_result: Optional[List] = None,
    fields_param: Optional[List] = None,
    compact: bool = True,
    single_record: bool = False,
    annotate: bool = False,
) -> Any:
    """Annotate DBC results.

    Output shape:
      annotate=True : legacy per-field arrays ({index, name, value, type, ...});
                      single-record id lookups return a flat list of field dicts,
                      multi-record results return a list of such rows.
      annotate=False: flat {name: value} dicts (locale arrays collapsed);
                      single-record id lookups return one dict,
                      multi-record results return a list of dicts.
    """
    if not result:
        return []

    actual_fields = fields_param if fields_param is not False else None

    annotated = _annotate_dbc_impl(
        result, reg_entry, db_result, actual_fields, compact
    )
    rows = annotated.get("result", []) if isinstance(annotated, dict) else annotated

    if annotate:
        if single_record and len(result) == 1:
            return rows[0] if rows else []
        return rows

    flat_rows = [_row_to_flat(r) for r in rows]
    if single_record:
        return flat_rows[0] if flat_rows else {}
    return flat_rows


def _shape_links(resolved: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Shape resolve_type_fields output into a budgeted relation map.

    Handles both resolver output shapes:
      generic: {pk: {col: {meaning, raw, resolved_to, items?}}}
      quest:   {pk: {starters|enders: [{type, id, name}], items: {col: {id, name}}}}
    """
    out = []
    for pk, fields in resolved.items():
        items = []
        for col, v in list(fields.items())[:12]:
            if isinstance(v, list):
                for e in v[:3]:
                    if isinstance(e, dict):
                        items.append({
                            "field": col,
                            "target": e.get("type", ""),
                            "value": e.get("id"),
                            "target_name": e.get("name"),
                        })
            elif isinstance(v, dict):
                if "resolved_to" in v or ("meaning" in v and "raw" in v):
                    entry: Dict[str, Any] = {
                        "field": v.get("meaning") or col, "value": v.get("raw")
                    }
                    if v.get("resolved_to") is not None:
                        entry["target_name"] = v["resolved_to"]
                    if v.get("items"):
                        entry["items"] = list(v["items"])[:1]
                    if "target_name" in entry or "items" in entry:
                        items.append(entry)
                elif "id" in v and "name" in v:
                    items.append({"field": col, "value": v.get("id"), "target_name": v.get("name")})
                elif v and all(
                    isinstance(x, dict) and "id" in x and "name" in x for x in v.values()
                ):
                    for sub, sv in list(v.items())[:5]:
                        items.append({"field": sub, "value": sv.get("id"), "target_name": sv.get("name")})
        if items:
            out.append({"id": pk, "links": items[:15]})
    return out


def _extract_field_references(reg_entry: Optional[Dict]) -> Optional[Dict[str, List]]:
    """Extract field-level references from registry entry for metadata hints."""
    if not reg_entry or "fields" not in reg_entry:
        return None

    refs = {}
    for field_key, field_info in reg_entry["fields"].items():
        if field_info.get("references"):
            field_name = field_info.get("name", field_key)
            refs[field_name] = field_info["references"]

    return refs if refs else None


def _extract_rows_for_resolution(merged_result: Any, single_record: bool) -> List[Dict[str, Any]]:
    """Convert annotated DBC results into plain {field_name: value} dicts for resolution.

    Handles both annotation formats:
      - Single record (ID lookup): flat list of {index, name, value, ...} field dicts
      - Multi-record: list of rows, each row is a list of {index, name, value, ...} field dicts
      - Plain dicts (SQL-only path): passed through as-is

    Returns list of {field_name: value} dicts suitable for resolve_type_fields().
    """
    if not merged_result:
        return []

    # Single flat record dict (default DBC shape for id lookups)
    if isinstance(merged_result, dict):
        return [merged_result]

    # If already a list of plain dicts (e.g., SQL-only merge), pass through
    if isinstance(merged_result, list) and merged_result:
        first = merged_result[0]
        if isinstance(first, dict):
            # Could be plain {col: value} OR annotated [{index, name, value}, ...]
            # Check if it looks like an annotated field (single-record flat format)
            if "value" in first and "name" in first:
                # Single-record flat annotation: [{index:0, name:"ID", value:118}, ...]
                row = {}
                for field in merged_result:
                    fname = field.get("name", "")
                    if fname:
                        row[fname] = field.get("value")
                return [row]
            # Already plain {col: value} dicts
            return merged_result
        elif isinstance(first, list):
            # Multi-record annotation: [[{index, name, value}, ...], ...]
            rows = []
            for row_fields in merged_result:
                row = {}
                for field in row_fields:
                    fname = field.get("name", "")
                    if fname:
                        row[fname] = field.get("value")
                rows.append(row)
            return rows

    return []


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "query",
        "description": (
            "Query any datastore (DBC binary, SQL table, or overlay). "
            "Result rows are flat {field: value} objects; id/row_index lookups return one "
            "object (or an error if the id is missing), filter/unconstrained queries return "
            "a list, capped by limit (default 100). Unknown argument/field names are errors "
            "with suggestions. compact (default true) strips null/0/empty values. "
            "annotate=true switches DBC rows to the legacy per-field arrays with DBC index, "
            "type, sql_column and source. hints=true adds field_references/referenced_by "
            "metadata. links=true adds a one-hop relation map (metadata.links) to related "
            "rows across DBC/SQL tables. resolve=true gives type-aware field decoding. "
            "For aggregations (COUNT, SUM, GROUP BY) or cross-table joins, use the sql tool."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Datastore name: DBC file (Spell), SQL table (quest_template),"
                        " or struct (SpellEntry). Use lookup(query='<name>') to find valid names."
                    )
                },
                "id": {
                    "type": "number",
                    "description": (
                        "Primary key ID for O(1) lookup. If a filter is also given, both "
                        "must match (AND); an existing record that fails the filter is an error."
                    )
                },
                "filter": {
                    "type": "object",
                    "description": (
                        "Filter by field names or indices."
                        " Supports $like and $ilike patterns."
                        ' Example: {"name": "Polymorph"} or {"0": 118}'
                    ),
                    "additionalProperties": True
                },
                "fields": {
                    "type": "array",
                    "items": {"type": ["number", "string"]},
                    "description": (
                        "Select specific fields by index [38, 39] or name ['BaseLevel', 'SpellLevel']."
                        " Strict: unknown names are errors with suggestions. None = all fields."
                    )
                },
                "annotate": {
                    "type": "boolean",
                    "description": (
                        "Return DBC rows as legacy per-field arrays with DBC index, type, "
                        "sql_column, source and sql_override (default false = flat {name: value}). "
                        "On SQL tables, attaches column types to metadata."
                    )
                },
                "hints": {
                    "type": "boolean",
                    "description": (
                        "Include cross-reference metadata: field_references and referenced_by "
                        "(default false)"
                    )
                },
                "links": {
                    "type": "boolean",
                    "description": (
                        "Add metadata.links: one-hop relation map for the returned rows - for each "
                        "registered cross-reference field with a non-trivial value, the related row's "
                        "identity (default false; capped at 25 rows x 10 fields)"
                    )
                },
                "limit": {
                    "type": "number",
                    "description": "Max records to return (default: 100)"
                },
                "compact": {
                    "type": "boolean",
                    "description": "Strip null fields (default: true)"
                },
                "info": {
                    "type": "boolean",
                    "description": (
                        "Return DBC file metadata (file, record_count, field_count, "
                        "record_size) instead of records (default false)"
                    )
                },
                "resolve": {
                    "oneOf": [
                        {"type": "boolean"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": (
                        "Resolve cross-reference fields to their targets. "
                        "Use true to resolve all, or ['dbc', 'sql', 'loot', 'enum'] to pick types. "
                        "Works for ALL tables with cross-reference metadata in the registry: "
                        "gameobject_template (type-aware data[0-19]), "
                        "creature_template (faction, lootid, spell1-8, mapId...), "
                        "SpellEntry (Category, DurationIndex, RangeIndex, Effect[0..2] with enum names...), "
                        "Quest (RewardSpell, RequiredSkill, ZoneOrSort...), "
                        "and 200+ other entries. DBC and SQL lookups resolve to names/labels. "
                        "Enum resolves spell effects (Effect=24 -> 'CREATE_ITEM') when 'enum' is included."
                    )
                },
                "resolve_max": {
                    "type": "number",
                    "description": (
                        "Max items to return per loot table resolution (default: 10). "
                        "Use 0 for no limit."
                    )
                }
            },
            "required": ["name"]
        }
    }

