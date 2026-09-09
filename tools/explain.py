"""explain tool: agent-friendly digest of a single record.

Wraps the query pipeline (annotate + links) and distills one record into:
  - a one-line summary (name, source, field/relation counts)
  - key_fields: the non-trivial fields in natural order (capped)
  - overlay_overrides: for DBC-backed stores, the fields the live SQL
    overlay changed relative to the vanilla DBC (the "what did the DB
    customize" signal)
  - relations: one-hop cross-references with resolved target names

Read-only. Any datastore, any source (DBC / SQL / overlay).
"""

from typing import Any, Dict, List, Optional

from tools import query as query_tool

_MAX_KEY_FIELDS = 20
_MAX_RELATIONS = 15


def _nontrivial(v: Any) -> bool:
    if v is None or v is False or v == 0 or v == "":
        return False
    if isinstance(v, str) and not v.strip():
        return False
    if isinstance(v, (list, dict)) and not v:
        return False
    return True


def _flatten_links(links: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(links, list):
        return out
    for blk in links:
        for item in blk.get("links", []) if isinstance(blk, dict) else []:
            out.append({
                "field": item.get("field"),
                "value": item.get("value"),
                "target": item.get("target"),
                "target_name": item.get("target_name"),
            })
    return out[:_MAX_RELATIONS]


def _dbc_overrides(server, name: str, id_: int,
                   row: Dict[str, Any]) -> tuple:
    """Diff a live (overlay-merged) row against the vanilla DBC record.

    Returns (overrides, dbc_exists): overrides maps live column -> value for
    each field the SQL overlay changed vs the DBC. When the record has no
    vanilla DBC row (overlay-only id), overrides is {} and dbc_exists is
    False. Best-effort: lookup failures yield ({}, True).
    """
    try:
        resolved = server.registry._resolve_entry(name)
        if not resolved:
            return {}, True
        _, entry = resolved
        dbc_file = entry.get("dbc_file")
        if not dbc_file:
            return {}, True
        if dbc_file.endswith(".dbc"):
            dbc_file = dbc_file[:-4]
        reader = server._load_dbc(dbc_file)
        rec = reader.get_record_by_id(id_)
        if not rec:
            return {}, False
        out: Dict[str, Any] = {}
        # row keys use the live SQL column style (ID, Effect_1,
        # Name_Lang_enUS) while the registry maps C names (Id, Effect[0],
        # SpellName[0]) - match base, _1.._5 slots and locale variants,
        # all case-insensitive.
        row_by_lower = {str(k).lower(): k for k in row.keys()}

        def live_key(fname: str, ftype: str) -> str | None:
            base = str(fname).split("[")[0]  # SpellName[0] -> SpellName
            # C names like SpellName[0] map to live Name_Lang_* columns:
            # also try the base with a known leading entity prefix stripped
            bases = [base]
            bl = base.lower()
            for pre in ("spell", "item", "creature", "quest", "object", "npc"):
                if bl.startswith(pre) and len(bl) > len(pre):
                    bases.append(base[len(pre):])
                    break
            for b in bases:
                for cand in [b] + [f"{b}_{n}" for n in range(1, 6)]:
                    hit = row_by_lower.get(cand.lower())
                    if hit is not None:
                        return hit
            if "char const*" in ftype:  # locale arrays: Name_Lang_*
                pref = None
                for b in bases:
                    for k in row_by_lower:
                        if k.startswith(b.lower() + "_lang_"):
                            if "enus" in k:
                                pref = row_by_lower[k]
                                break
                            if pref is None:
                                pref = row_by_lower[k]
                    if pref is not None:
                        break
                return pref
            return None

        for idx, f in (entry.get("fields") or {}).items():
            try:
                i = int(idx)
            except (TypeError, ValueError):
                continue
            fname = f.get("name")
            if not fname:
                continue
            lk = live_key(fname, str(f.get("type") or ""))
            if lk is None:
                continue
            live, dbc = row.get(lk), rec.get(i)
            if _nontrivial(live) and (dbc is None or live != dbc):
                out[lk] = live
        return out, True
    except Exception:
        return {}, True


def explain_tools(server) -> Dict[str, Any]:
    args = server.args or {}

    name = args.get("name")
    if not name or not isinstance(name, str):
        return {"error": "'name' is required (a datastore name).",
                "isError": True}
    id_ = args.get("id")
    if not isinstance(id_, (int, float)) or isinstance(id_, bool) or id_ < 0:
        return {"error": "'id' is required (the record's primary key).",
                "isError": True}
    id_ = int(id_)

    # Reuse the query pipeline: annotated single record + one-hop links.
    saved_args = server.args
    server.args = {"name": name, "id": id_,
                   "links": True, "annotate": True, "compact": True}
    try:
        q = query_tool.query_tools(server)
    finally:
        server.args = saved_args

    if isinstance(q, dict) and q.get("isError"):
        return q

    result = q.get("result") if isinstance(q, dict) else None
    metadata = q.get("metadata", {}) if isinstance(q, dict) else {}

    if not result:
        return {"error": f"No record {name} #{id_} found.", "isError": True}

    relations = _flatten_links(metadata.get("links"))

    # --- DBC-annotated shape: list of field dicts -------------------------
    if (isinstance(result, list) and result
            and isinstance(result[0], dict)
            and "index" in result[0] and "value" in result[0]):
        fields: List[Dict[str, Any]] = result
        row = {f.get("name"): f.get("value") for f in fields}
        key_fields = {
            f["name"]: f["value"]
            for f in fields if _nontrivial(f.get("value"))
        }
        overrides = {
            f["name"]: f["value"]
            for f in fields
            if f.get("source") == "sql" and _nontrivial(f.get("value"))
        }
        name_val = None
        for f in fields:
            fn = str(f.get("name") or "").lower()
            if (fn == "name" or fn.endswith("name[0]")) and isinstance(
                    f.get("value"), str) and f["value"].strip():
                name_val = f["value"].strip()
                break
        src = metadata.get("source") or name
        source = {"dbc": src}
        if metadata.get("sql_table"):
            source["sql_table"] = metadata["sql_table"]
        if overrides:
            source["note"] = (
                f"{len(overrides)} field(s) come from the live SQL overlay "
                f"({source.get('sql_table')}), not the vanilla DBC."
            )
        # pin the name field into the digest when the cap would drop it
        if name_val is not None:
            for f in fields:
                fn = str(f.get("name") or "").lower()
                if (fn == "name" or fn.endswith("name[0]")) \
                        and isinstance(f.get("value"), str) and f["value"].strip():
                    name_key = f["name"]
                    key_fields = {name_key: f["value"], **key_fields}
                    break
    else:
        # SQL / merged-overlay shape: a flat row dict (single record)
        if isinstance(result, dict):
            row = result
        elif isinstance(result, list) and result and isinstance(result[0], dict):
            row = result[0]
        else:
            row = {"value": result}
        fields = None
        key_fields = {k: v for k, v in row.items() if _nontrivial(v)}
        source = {"sql_table": metadata.get("sql_table") or name}
        # overlay diff: when the SQL overlay won the merge, diff vs the DBC
        if metadata.get("sql_table") and metadata.get("source") == "database":
            overrides, dbc_exists = _dbc_overrides(server, name, id_, row)
            if not dbc_exists:
                source["note"] = (
                    f"Record exists only in the SQL overlay "
                    f"({source['sql_table']}) - no vanilla DBC row, so no "
                    f"overlay diff is available."
                )
        else:
            overrides = {}
        name_val = None
        for k in ("name", "LogTitle", "title", "Name"):
            if isinstance(row.get(k), str) and row[k].strip():
                name_val = row[k].strip()
                break
        if name_val is None:
            for k, v in row.items():
                if str(k).lower().endswith("name[0]") and isinstance(v, str) \
                        and v.strip():
                    name_val = v.strip()
                    break
        if name_val is None:
            # overlay-only rows keep raw locale column style (Name_Lang_enUS)
            for k, v in row.items():
                if str(k).lower() == "name_lang_enus" and isinstance(v, str) \
                        and v.strip():
                    name_val = v.strip()
                    break

    # Cap key fields in natural order
    capped = dict(list(key_fields.items())[:_MAX_KEY_FIELDS])
    truncated = len(key_fields) > _MAX_KEY_FIELDS

    label = name_val or f"{id_}"
    store = source.get("dbc") or source.get("sql_table") or name
    parts = [f"{label} ({store})"]
    n_kv = len(key_fields)
    if n_kv:
        parts.append(f"{n_kv} fields with values" + (f", {len(capped)} shown" if truncated else ""))
    if overrides:
        parts.append(f"{len(overrides)} overridden by SQL overlay")
    if relations:
        parts.append(f"{len(relations)} cross-reference(s)")
    summary = " — ".join(parts)

    out: Dict[str, Any] = {
        "datastore": name,
        "id": id_,
        "name": name_val,
        "summary": summary,
        "key_fields": capped,
        "relations": relations,
        "source": source,
    }
    if overrides:
        out["overlay_overrides"] = overrides
    out["metadata"] = {
        "note": (
            "key_fields is capped at " + str(_MAX_KEY_FIELDS)
            + (" (truncated)" if truncated else "")
            + "; use query(name, id) for the full record."
        ),
    }
    return out


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "explain",
        "description": (
            "Agent-friendly digest of a single record from any datastore: "
            "one-line summary, non-trivial fields (capped at 20), one-hop "
            "cross-references with resolved target names, and - for DBC-backed "
            "stores - which fields the live SQL overlay changed vs the vanilla "
            "DBC. Read-only; wraps the query pipeline."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Datastore name (DBC file, SQL table, or struct)."
                },
                "id": {
                    "type": "number",
                    "description": "The record's primary key."
                },
            },
            "required": ["name", "id"],
        },
    }
