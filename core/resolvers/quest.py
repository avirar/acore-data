"""Resolve quest_template with enriched cross-reference data.

For each quest row, automatically includes:
- Starters: NPCs/GOs that offer this quest (creature_queststarter, gameobject_queststarter)
- Ender:   NPCs/GOs that accept this quest (creature_questender, gameobject_questender)
- POIs:    Point-of-interest coordinates from quest_poi + quest_poi_points
- Chain:   prevQuestID, nextQuestID, breadcrumbForQuestId from quest_template_addon

On top of the generic field resolution (faction, spell, item refs).
"""
from typing import Any, Dict, List

from .ref_utils import resolve_sql_ref


def _get_row_pk(row: Dict) -> str:
    """Get primary key value from row."""
    for pk in ["entry", "ID", "Id", "id", "guid"]:
        if pk in row:
            return row[pk]
    return str(id(row))


def resolve_quest_fields(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve quest_template with enriched cross-reference data."""
    # First get generic resolution for base fields
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
        # Quest enrichment requires SQL lookups; skip if not allowed
        return base_resolved

    # Resolve starters, enders, POIs, chain for each quest
    resolved = {}
    for row in rows:
        quest_id = _get_row_pk(row)
        entry_resolved = base_resolved.get(quest_id, {})

        starters = []
        enders = []
        pois = []
        chain = {}

        # --- Quest Starters (NPCs) ---
        try:
            npc_rows, _ = server.database._query_database(
                "SELECT id, quest FROM creature_queststarter WHERE quest = %s LIMIT 20",
                params=(int(quest_id),),
            )
            for r in npc_rows:
                npc_id = r.get("id", 0)
                if npc_id:
                    name = resolve_sql_ref(server, "creature_template", npc_id, "entry")
                    starters.append({"type": "npc", "id": npc_id, "name": name})
        except Exception:
            pass

        # --- Quest Starters (GOs) ---
        try:
            go_rows, _ = server.database._query_database(
                "SELECT id, quest FROM gameobject_queststarter WHERE quest = %s LIMIT 20",
                params=(int(quest_id),),
            )
            for r in go_rows:
                go_id = r.get("id", 0)
                if go_id:
                    name = resolve_sql_ref(server, "gameobject_template", go_id, "entry")
                    starters.append({"type": "go", "id": go_id, "name": name})
        except Exception:
            pass

        # --- Quest Enders (NPCs) ---
        try:
            ender_rows, _ = server.database._query_database(
                "SELECT id, quest FROM creature_questender WHERE quest = %s LIMIT 20",
                params=(int(quest_id),),
            )
            for r in ender_rows:
                npc_id = r.get("id", 0)
                if npc_id:
                    name = resolve_sql_ref(server, "creature_template", npc_id, "entry")
                    enders.append({"type": "npc", "id": npc_id, "name": name})
        except Exception:
            pass

        # --- Quest Enders (GOs) ---
        try:
            go_ender_rows, _ = server.database._query_database(
                "SELECT id, quest FROM gameobject_questender WHERE quest = %s LIMIT 20",
                params=(int(quest_id),),
            )
            for r in go_ender_rows:
                go_id = r.get("id", 0)
                if go_id:
                    name = resolve_sql_ref(server, "gameobject_template", go_id, "entry")
                    enders.append({"type": "go", "id": go_id, "name": name})
        except Exception:
            pass

        # --- Quest POIs ---
        try:
            poi_rows, _ = server.database._query_database(
                """SELECT qp.id, qp.questID, qp.MapID, qp.ObjectiveIndex, qp.Flags,
                          qp.Idx1, qp.Idx2, qp.Icon, qpp.SurveyLongitude, qpp.SurveyLatitude
                   FROM quest_poi qp
                   LEFT JOIN quest_poi_points qpp ON qp.id = qpp.ID AND qp.questID = qpp.QuestId
                   WHERE qp.questID = %s
                   LIMIT 20""",
                params=(int(quest_id),),
            )
            for p in poi_rows:
                pois.append({
                    "ObjectiveIndex": p.get("ObjectiveIndex", -1),
                    "turn_in_point": p.get("ObjectiveIndex", -1) == -1,
                    "MapID": p.get("MapID"),
                    "longitude": p.get("SurveyLongitude"),
                    "latitude": p.get("SurveyLatitude"),
                    "icon": p.get("Icon"),
                })
        except Exception:
            pass

        # --- Quest Chain ---
        try:
            chain_rows, _ = server.database._query_database(
                "SELECT PrevQuestId, NextQuestId, BreadcrumbForQuestId FROM quest_template_addon WHERE ID = %s LIMIT 1",
                params=(int(quest_id),),
            )
            if chain_rows:
                cr = chain_rows[0]
                prev_id = cr.get("PrevQuestId", 0) or 0
                next_id = cr.get("NextQuestId", 0) or 0
                breadcrumb_id = cr.get("BreadcrumbForQuestId", 0) or 0

                if prev_id:
                    prev_name = resolve_sql_ref(server, "quest_template", prev_id, "ID")
                    chain["prev_quest"] = {"id": prev_id, "name": prev_name}
                if next_id:
                    next_name = resolve_sql_ref(server, "quest_template", next_id, "ID")
                    chain["next_quest"] = {"id": next_id, "name": next_name}
                if breadcrumb_id:
                    bc_name = resolve_sql_ref(server, "quest_template", breadcrumb_id, "ID")
                    chain["breadcrumb_for"] = {"id": breadcrumb_id, "name": bc_name}
        except Exception:
            pass

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

        # Merge with base resolution
        merged = {**entry_resolved, **enriched}
        if merged:
            resolved[quest_id] = merged

    return resolved
