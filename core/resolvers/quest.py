"""Resolve quest_template with enriched cross-reference data.

For each quest row, automatically includes:
- Starters: NPCs/GOs that offer this quest (creature_queststarter, gameobject_queststarter)
- Ender:   NPCs/GOs that accept this quest (creature_questender, gameobject_questender)
- POIs:    Point-of-interest coordinates from quest_poi + quest_poi_points
- Chain:   prevQuestID, nextQuestID, breadcrumbForQuestId from quest_template_addon

On top of the generic field resolution (faction, spell, item refs).

Uses two-pass batch resolution to minimize SQL queries: Pass 1 collects all entity
IDs across all quest rows, Pass 2 resolves them in bulk via single queries per table.
"""
from typing import Any, Dict, List

from .ref_utils import resolve_sql_ref, batch_resolve_sql


def _get_row_pk(row: Dict) -> str:
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def _fetch_starters_enders(server, quest_ids):
    """Pass 1a: Fetch all starter/ender relationships for given quests."""
    qs = ",".join(["%s"] * len(quest_ids))

    data = {"npc_starters": [], "go_starters": [], "npc_enders": [], "go_enders": []}

    try:
        rows, _ = server.database._query_database(
            f"SELECT id, quest FROM creature_queststarter WHERE quest IN ({qs}) LIMIT 400",
            params=tuple(quest_ids),
        )
        data["npc_starters"] = rows or []
    except Exception:
        pass

    try:
        rows, _ = server.database._query_database(
            f"SELECT id, quest FROM gameobject_queststarter WHERE quest IN ({qs}) LIMIT 400",
            params=tuple(quest_ids),
        )
        data["go_starters"] = rows or []
    except Exception:
        pass

    try:
        rows, _ = server.database._query_database(
            f"SELECT id, quest FROM creature_questender WHERE quest IN ({qs}) LIMIT 400",
            params=tuple(quest_ids),
        )
        data["npc_enders"] = rows or []
    except Exception:
        pass

    try:
        rows, _ = server.database._query_database(
            f"SELECT id, quest FROM gameobject_questender WHERE quest IN ({qs}) LIMIT 400",
            params=tuple(quest_ids),
        )
        data["go_enders"] = rows or []
    except Exception:
        pass

    return data


def _fetch_chain(server, quest_ids):
    """Pass 1b: Fetch all chain info for given quests."""
    qs = ",".join(["%s"] * len(quest_ids))

    try:
        rows, _ = server.database._query_database(
            f"SELECT ID, PrevQuestId, NextQuestId, BreadcrumbForQuestId FROM quest_template_addon WHERE ID IN ({qs})",
            params=tuple(quest_ids),
        )
        return {r["ID"]: r for r in (rows or [])}
    except Exception:
        return {}


def _fetch_pois(server, quest_ids):
    """Pass 1c: Fetch all POI data for given quests."""
    qs = ",".join(["%s"] * len(quest_ids))

    try:
        rows, _ = server.database._query_database(
            f"""SELECT qp.id, qp.questID, qp.MapID, qp.ObjectiveIndex, qp.Flags,
                       qp.Idx1, qp.Idx2, qp.Icon, qpp.SurveyLongitude, qpp.SurveyLatitude
                FROM quest_poi qp
                LEFT JOIN quest_poi_points qpp ON qp.id = qpp.ID AND qp.questID = qpp.QuestId
                WHERE qp.questID IN ({qs})
                LIMIT 400""",
            params=tuple(quest_ids),
        )
        return rows or []
    except Exception:
        return []


def resolve_quest_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve quest_template with enriched cross-reference data."""
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

    if "sql" not in allowed:
        return base_resolved

    quest_ids = [int(_get_row_pk(row)) for row in rows]

    # --- Pass 1: Collect all relationships ---
    se_data = _fetch_starters_enders(server, quest_ids)
    chain_data = _fetch_chain(server, quest_ids)
    poi_rows = _fetch_pois(server, quest_ids)

    # Gather unique entity IDs for batch resolution
    all_npc_ids = set()
    all_go_ids = set()
    all_quest_chain_ids = set()

    for r in se_data["npc_starters"] + se_data["npc_enders"]:
        nid = r.get("id", 0)
        if nid:
            all_npc_ids.add(nid)
    for r in se_data["go_starters"] + se_data["go_enders"]:
        gid = r.get("id", 0)
        if gid:
            all_go_ids.add(gid)
    for cr in chain_data.values():
        for col in ["PrevQuestId", "NextQuestId", "BreadcrumbForQuestId"]:
            val = cr.get(col, 0) or 0
            if val:
                all_quest_chain_ids.add(val)

    # --- Pass 2: Batch resolve entity names ---
    npc_map = batch_resolve_sql(server, "creature_template", list(all_npc_ids), "entry") if all_npc_ids else {}
    go_map = batch_resolve_sql(server, "gameobject_template", list(all_go_ids), "entry") if all_go_ids else {}
    quest_chain_map = batch_resolve_sql(server, "quest_template", list(all_quest_chain_ids), "ID") if all_quest_chain_ids else {}

    # --- Pass 3: Build resolved output ---
    # Index starter/ender data by quest ID
    npc_starter_by_quest = {}
    for r in se_data["npc_starters"]:
        qid = r.get("quest", 0)
        if qid:
            npc_starter_by_quest.setdefault(qid, []).append(r)

    go_starter_by_quest = {}
    for r in se_data["go_starters"]:
        qid = r.get("quest", 0)
        if qid:
            go_starter_by_quest.setdefault(qid, []).append(r)

    npc_ender_by_quest = {}
    for r in se_data["npc_enders"]:
        qid = r.get("quest", 0)
        if qid:
            npc_ender_by_quest.setdefault(qid, []).append(r)

    go_ender_by_quest = {}
    for r in se_data["go_enders"]:
        qid = r.get("quest", 0)
        if qid:
            go_ender_by_quest.setdefault(qid, []).append(r)

    # Index POI data by quest ID
    poi_by_quest = {}
    for p in poi_rows:
        qid = p.get("questID", 0)
        if qid:
            poi_by_quest.setdefault(qid, []).append(p)

    resolved = {}
    for row in rows:
        quest_id = _get_row_pk(row)
        entry_resolved = base_resolved.get(quest_id, {})

        starters = []
        enders = []
        pois = []
        chain = {}

        # --- Starters (NPCs + GOs) ---
        for r in npc_starter_by_quest.get(int(quest_id), [])[:20]:
            npc_id = r.get("id", 0)
            if npc_id:
                starters.append({"type": "npc", "id": npc_id, "name": npc_map.get(npc_id, f"creature_template [{npc_id}]")})
        for r in go_starter_by_quest.get(int(quest_id), [])[:20]:
            go_id = r.get("id", 0)
            if go_id:
                starters.append({"type": "go", "id": go_id, "name": go_map.get(go_id, f"gameobject_template [{go_id}]")})

        # --- Enders (NPCs + GOs) ---
        for r in npc_ender_by_quest.get(int(quest_id), [])[:20]:
            npc_id = r.get("id", 0)
            if npc_id:
                enders.append({"type": "npc", "id": npc_id, "name": npc_map.get(npc_id, f"creature_template [{npc_id}]")})
        for r in go_ender_by_quest.get(int(quest_id), [])[:20]:
            go_id = r.get("id", 0)
            if go_id:
                enders.append({"type": "go", "id": go_id, "name": go_map.get(go_id, f"gameobject_template [{go_id}]")})

        # --- POIs ---
        for p in poi_by_quest.get(int(quest_id), [])[:20]:
            pois.append({
                "ObjectiveIndex": p.get("ObjectiveIndex", -1),
                "turn_in_point": p.get("ObjectiveIndex", -1) == -1,
                "MapID": p.get("MapID"),
                "longitude": p.get("SurveyLongitude"),
                "latitude": p.get("SurveyLatitude"),
                "icon": p.get("Icon"),
            })

        # --- Chain ---
        cr = chain_data.get(int(quest_id))
        if cr:
            prev_id = cr.get("PrevQuestId", 0) or 0
            next_id = cr.get("NextQuestId", 0) or 0
            breadcrumb_id = cr.get("BreadcrumbForQuestId", 0) or 0

            if prev_id:
                chain["prev_quest"] = {"id": prev_id, "name": quest_chain_map.get(prev_id, f"quest_template [{prev_id}]")}
            if next_id:
                chain["next_quest"] = {"id": next_id, "name": quest_chain_map.get(next_id, f"quest_template [{next_id}]")}
            if breadcrumb_id:
                chain["breadcrumb_for"] = {"id": breadcrumb_id, "name": quest_chain_map.get(breadcrumb_id, f"quest_template [{breadcrumb_id}]")}

        # Merge enriched data into resolved entry
        enriched = {}
        if starters:
            enriched["starters"] = starters
        if enders:
            enriched["enders"] = enders
        if pois:
            enriched["pois"] = pois
        if chain:
            enriched["chain"] = chain

        merged = {**entry_resolved, **enriched}
        if merged:
            resolved[quest_id] = merged

    return resolved
