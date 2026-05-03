"""
smart_scripts table resolver.

Handles triple-polymorphic field resolution: event_type, action_type, target_type
each have their own enum translation and param resolution logic.
"""
from typing import Any, Dict, List, Optional

from ..enums import (
    _SAI_EVENT_NAMES,
    _SAI_ACTION_NAMES,
    _SAI_TARGET_NAMES,
    _SAI_SOURCE_TYPE_NAMES,
    _TEXT_EMOTE_NAMES,
    _ANIM_EMOTE_NAMES,
)
from .ref_utils import resolve_dbc_ref, resolve_sql_ref


def resolve_sai_entry(server, source_type: int, entryorguid: int) -> Optional[str]:
    """Resolve entryorguid based on source_type and sign."""
    if entryorguid == 0:
        return None

    pos = abs(entryorguid)
    if source_type == 0:  # Creature
        if entryorguid > 0:
            name = resolve_sql_ref(server, "creature_template", pos, "entry")
            return f"creature (entry={pos}) -> {name}" if name else f"creature (entry={pos})"
        else:
            return f"creature (guid={entryorguid})"
    elif source_type == 1:  # Gameobject
        if entryorguid > 0:
            name = resolve_sql_ref(server, "gameobject_template", pos, "entry")
            return f"gameobject (entry={pos}) -> {name}" if name else f"gameobject (entry={pos})"
        else:
            return f"gameobject (guid={entryorguid})"
    elif source_type == 2:  # Areatrigger
        try:
            name = resolve_sql_ref(server, "areatrigger_scripts", pos, "entry")
            return f"areatrigger (entry={pos}) -> {name}" if name else f"areatrigger (entry={pos})"
        except Exception:
            return f"areatrigger (entry={pos})"
    elif source_type == 9:  # TimedActionList
        return f"timed_actionlist (entry={entryorguid})"

    return None


def resolve_smart_scripts(
    server,
    reg_entry: Dict,
    rows: List[Dict[str, Any]],
    resolve_filter: Any,
    resolve_max: int = 10,
) -> Dict[str, Any]:
    """Resolve smart_scripts triple-polymorphic fields.

    Translates event_type, action_type, target_type to enum names.
    Resolves event_param1-6 based on event_type (spell/quest/creature refs).
    Resolves action_param1-6 based on action_type (spell/creature/GO/quest refs).
    Resolves target_param1-4 based on target_type (creature/GO entry refs).
    Resolves entryorguid based on source_type.
    """
    if not rows or not resolve_filter:
        return {}

    if isinstance(resolve_filter, list):
        allowed = set(resolve_filter)
    elif resolve_filter is True:
        allowed = {"dbc", "sql", "loot"}
    else:
        return {}

    resolved = {}
    for row in rows:
        entryorguid = row.get("entryorguid", 0) or 0
        source_type = row.get("source_type", 0) or 0
        event_type = row.get("event_type", 0) or 0
        action_type = row.get("action_type", 0) or 0
        target_type = row.get("target_type", 0) or 0

        entry_resolved = {}

        # --- Entry/guid resolution based on source_type ---
        if entryorguid and "sql" in allowed:
            entry_label = resolve_sai_entry(server, source_type, entryorguid)
            if entry_label:
                entry_resolved["entryorguid"] = {
                    "raw": entryorguid,
                    "source_type_name": _SAI_SOURCE_TYPE_NAMES.get(source_type, f"UNKNOWN({source_type})"),
                    "resolved_to": entry_label,
                }

        # --- Enum name translation for all three axes ---
        event_name = _SAI_EVENT_NAMES.get(event_type)
        action_name = _SAI_ACTION_NAMES.get(action_type)
        target_name = _SAI_TARGET_NAMES.get(target_type)

        if event_name:
            entry_resolved["event_type"] = {"raw": event_type, "name": event_name}
        if action_name:
            entry_resolved["action_type"] = {"raw": action_type, "name": action_name}
        if target_name:
            entry_resolved["target_type"] = {"raw": target_type, "name": target_name}

        # --- Event param resolution (by event_type) ---
        if "sql" in allowed or "dbc" in allowed:
            ep1 = row.get("event_param1", 0) or 0
            ep2 = row.get("event_param2", 0) or 0
            ep3 = row.get("event_param3", 0) or 0

            # Spell events: param1=SpellID
            if event_type in (8, 23, 24, 31) and ep1:
                spell_name = resolve_dbc_ref(server, "Spell", ep1)
                entry_resolved["event_param1"] = {"meaning": "SpellId", "raw": ep1, "resolved_to": spell_name}

            # Quest events: param1=QuestID
            if event_type in (19, 20) and ep1:
                quest_name = resolve_sql_ref(server, "quest_template", ep1, "ID")
                entry_resolved["event_param1"] = {"meaning": "QuestId", "raw": ep1, "resolved_to": quest_name}

            # Respawn event: param2=MapId (type=1), param3=ZoneId (type=2)
            if event_type == 11:
                resp_parts = {}
                if ep2 and ep1 == 1:
                    map_name = resolve_dbc_ref(server, "Map", ep2)
                    resp_parts["map_id"] = {"raw": ep2, "resolved_to": map_name}
                if ep3 and ep1 == 2:
                    area_name = resolve_dbc_ref(server, "AreaTable", ep3)
                    resp_parts["zone_id"] = {"raw": ep3, "resolved_to": area_name}
                if resp_parts:
                    entry_resolved["event_params_respawn"] = resp_parts

            # Kill event: param1=CreatureId (0=all), param2-4=Cooldown
            if event_type == 5 and ep1:
                cn = resolve_sql_ref(server, "creature_template", ep1, "entry")
                entry_resolved["event_param1"] = {"meaning": "CreatureId (0=all)", "raw": ep1, "resolved_to": cn}

            # Summoned/summon-despawned unit: param1=CreatureId
            if event_type in (17, 35, 82) and ep1:
                crit_name = resolve_sql_ref(server, "creature_template", ep1, "entry")
                entry_resolved["event_param1"] = {"meaning": "CreatureId", "raw": ep1, "resolved_to": crit_name}

            # Gossip select: param1=MenuID, param2=OptionID
            if event_type == 62 and ep1:
                gossip_parts = {}
                gossip_parts["menu_id"] = {"raw": ep1}
                try:
                    gname = resolve_sql_ref(server, "gossip_menu", ep1, "entry")
                    gossip_parts["menu_id"]["resolved_to"] = gname
                except Exception:
                    pass
                if ep2:
                    gossip_parts["option_id"] = {"raw": ep2}
                entry_resolved["event_params_gossip"] = gossip_parts

            # RECEIVE_EMOTE: param1=TextEmotes enum ID (chat-text emotes, NOT animation)
            if event_type == 22 and ep1:
                text_emote = _TEXT_EMOTE_NAMES.get(ep1, f"unknown_text_emote({ep1})")
                entry_resolved["event_param1"] = {"meaning": "TextEmotes", "raw": ep1, "resolved_to": text_emote}

            # Game event: param1=eventEntry
            if event_type in (68, 69) and ep1:
                try:
                    ge = resolve_sql_ref(server, "game_event", ep1, "eventEntry")
                    entry_resolved["event_param1"] = {"meaning": "game_event.eventEntry", "raw": ep1, "resolved_to": ge}
                except Exception:
                    entry_resolved["event_param1"] = {"meaning": "game_event.eventEntry", "raw": ep1}

            # Distance creature/GO: param2=entry
            if event_type == 75 and ep2:
                cn = resolve_sql_ref(server, "creature_template", ep2, "entry")
                entry_resolved["event_param2"] = {"meaning": "creature_template.entry", "raw": ep2, "resolved_to": cn}
            if event_type == 76 and ep2:
                gn = resolve_sql_ref(server, "gameobject_template", ep2, "entry")
                entry_resolved["event_param2"] = {"meaning": "gameobject_template.entry", "raw": ep2, "resolved_to": gn}

            # Victim casting: param3=SpellId
            if event_type == 13 and (ep3 or 0):
                s = ep3 or 0
                if s:
                    sn = resolve_dbc_ref(server, "Spell", s)
                    entry_resolved["event_param3"] = {"meaning": "SpellId", "raw": s, "resolved_to": sn}

            # Friendly missing buff: param1=SpellId
            if event_type == 16 and ep1:
                sn = resolve_dbc_ref(server, "Spell", ep1)
                entry_resolved["event_param1"] = {"meaning": "SpellId", "raw": ep1, "resolved_to": sn}

        # --- Action param resolution (by action_type) ---
        if "sql" in allowed or "dbc" in allowed:
            ap1 = row.get("action_param1", 0) or 0
            ap2 = row.get("action_param2", 0) or 0
            ap3 = row.get("action_param3", 0) or 0
            ap4 = row.get("action_param4", 0) or 0

            # CAST: param1=SpellId
            if action_type == 11 and ap1:
                spell_name = resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": spell_name}

            # SUMMON_CREATURE: param1=creature_template.entry
            if action_type == 12 and ap1:
                cn = resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # QUEST actions: param1=quest_id
            if action_type in (6, 7, 15, 26) and ap1:
                qn = resolve_sql_ref(server, "quest_template", ap1, "ID")
                entry_resolved["action_param1"] = {"meaning": "QuestId", "raw": ap1, "resolved_to": qn}

            # CALL_KILLEDMONSTER: param1=creature_template.entry
            if action_type == 33 and ap1:
                cn = resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "RequiredNpcOrGo (creature)", "raw": ap1, "resolved_to": cn}

            # MORPH/MOUNT: param1=creature_template.entry
            if action_type in (3, 43) and ap1:
                cn = resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # UPDATE_TEMPLATE: param1=creature_template.entry
            if action_type == 36 and ap1:
                cn = resolve_sql_ref(server, "creature_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "creature_entry", "raw": ap1, "resolved_to": cn}

            # FOLLOW: param3=creature_template.entry
            if action_type == 29 and ap3:
                cn = resolve_sql_ref(server, "creature_template", ap3, "entry")
                entry_resolved["action_param3"] = {"meaning": "End_creature_entry", "raw": ap3, "resolved_to": cn}

            # SUMMON_GO: param1=gameobject_template.entry
            if action_type == 50 and ap1:
                gn = resolve_sql_ref(server, "gameobject_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "gameobject_entry", "raw": ap1, "resolved_to": gn}

            # TALK/SIMPLE_TALK: param1=creature_text.GroupID
            if action_type in (1, 84) and ap1:
                try:
                    cn = resolve_sql_ref(server, "creature_text", ap1, "GroupID")
                    entry_resolved["action_param1"] = {"meaning": "creature_text.GroupID", "raw": ap1, "resolved_to": cn}
                except Exception:
                    pass

            # SOUND/MUSIC: param1=SoundEntriesDLC_ID
            if action_type in (4, 216) and ap1:
                sn = resolve_dbc_ref(server, "SoundEntries", ap1)
                entry_resolved["action_param1"] = {"meaning": "SoundId", "raw": ap1, "resolved_to": sn}

            # PLAY_EMOTE/SET_EMOTE_STATE: param1=Emote animation enum ID (SharedDefines.h)
            if action_type in (5, 17) and ap1:
                anim_emote = _ANIM_EMOTE_NAMES.get(ap1, f"unknown_anim_emote({ap1})")
                entry_resolved["action_param1"] = {"meaning": "Emote", "raw": ap1, "resolved_to": anim_emote}

            # ACTIVATE_TAXI: param1=TaxiNodes
            if action_type == 52 and ap1:
                tn = resolve_dbc_ref(server, "TaxiNodes", ap1)
                entry_resolved["action_param1"] = {"meaning": "TaxiNodeID", "raw": ap1, "resolved_to": tn}

            # ESCORT_START: param2=waypoints.entry, param4=quest_template.id
            if action_type == 53:
                escort_parts = {}
                if ap2:
                    try:
                        wn = resolve_sql_ref(server, "waypoints", ap2, "entry")
                        escort_parts["waypoints_entry"] = {"raw": ap2, "resolved_to": wn}
                    except Exception:
                        escort_parts["waypoints_entry"] = {"raw": ap2}
                if ap4:
                    qn = resolve_sql_ref(server, "quest_template", ap4, "ID")
                    escort_parts["quest_id"] = {"raw": ap4, "resolved_to": qn}
                if escort_parts:
                    entry_resolved["action_params_escorts"] = escort_parts

            # ADD_ITEM/REMOVE_ITEM: param1=item_template.entry
            if action_type in (56, 57) and ap1:
                iname = resolve_sql_ref(server, "item_template", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "item_entry", "raw": ap1, "resolved_to": iname}

            # SELF_CAST/CROSS_CAST/INVOKER_CAST: param1=SpellId
            if action_type in (85, 86, 134) and ap1:
                sn = resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": sn}

            # ADD_AURA/REMOVEAURASFROMSPELL: param1=SpellId
            if action_type in (75, 28) and ap1:
                sn = resolve_dbc_ref(server, "Spell", ap1)
                entry_resolved["action_param1"] = {"meaning": "SpellId", "raw": ap1, "resolved_to": sn}

            # INTERRUPT_SPELL: param2=SpellId
            if action_type == 92 and ap2:
                sn = resolve_dbc_ref(server, "Spell", ap2)
                entry_resolved["action_param2"] = {"meaning": "SpellId", "raw": ap2, "resolved_to": sn}

            # SEND_GOSSIP_MENU: param1=gossip_menu.entry, param2=text_id
            if action_type == 98 and ap1:
                gossip_parts = {}
                gn = resolve_sql_ref(server, "gossip_menu", ap1, "entry")
                gossip_parts["menu_id"] = {"raw": ap1, "resolved_to": gn}
                if ap2:
                    try:
                        tn = resolve_sql_ref(server, "npc_text", ap2, "ID")
                        gossip_parts["text_id"] = {"raw": ap2, "resolved_to": tn}
                    except Exception:
                        try:
                            tn = resolve_sql_ref(server, "creature_text", ap2, "GroupID")
                            gossip_parts["text_id"] = {"raw": ap2, "resolved_to": tn}
                        except Exception:
                            gossip_parts["text_id"] = {"raw": ap2}
                entry_resolved["action_params_gossip"] = gossip_parts

            # GAME_EVENT_START/STOP: param1=eventEntry
            if action_type in (111, 112) and ap1:
                try:
                    ge = resolve_sql_ref(server, "game_event", ap1, "eventEntry")
                    entry_resolved["action_param1"] = {"meaning": "game_event.eventEntry", "raw": ap1, "resolved_to": ge}
                except Exception:
                    entry_resolved["action_param1"] = {"meaning": "game_event.eventEntry", "raw": ap1}

            # SET_GOSSIP_MENU: param1=gossipMenuId
            if action_type == 240 and ap1:
                gn = resolve_sql_ref(server, "gossip_menu", ap1, "entry")
                entry_resolved["action_param1"] = {"meaning": "gossip_menu.entry", "raw": ap1, "resolved_to": gn}

            # TELEPORT: param1=MapId, target_x/y/z/o destination coordinates
            if action_type == 62:
                teleport_info = {}
                if ap1:
                    map_name = resolve_dbc_ref(server, "Map", ap1)
                    teleport_info["map_id"] = {"raw": ap1, "resolved_to": map_name}
                entry_resolved["teleport_info"] = teleport_info

        # --- Target param resolution (by target_type) ---
        if "sql" in allowed:
            tp1 = row.get("target_param1", 0) or 0

            # Creature by entry (range/distance/closest)
            if target_type in (9, 11, 19) and tp1:
                cn = resolve_sql_ref(server, "creature_template", tp1, "entry")
                entry_resolved["target_param1"] = {"meaning": "creature_entry", "raw": tp1, "resolved_to": cn}

            # Creature by guid
            if target_type == 10 and tp1:
                abs_guid = abs(tp1)
                cn = resolve_sql_ref(server, "creature_template", (row.get("target_param2", 0) or 0), "entry")
                entry_resolved["target_param1"] = {"meaning": "creature_guid", "raw": tp1, "resolved_to": f"guid:{abs_guid}" + (f", template: {cn}" if cn else "")}

            # GO by entry (range/distance/closest)
            if target_type in (13, 15, 20) and tp1:
                gn = resolve_sql_ref(server, "gameobject_template", tp1, "entry")
                entry_resolved["target_param1"] = {"meaning": "gameobject_entry", "raw": tp1, "resolved_to": gn}

            # GO by guid
            if target_type == 14 and tp1:
                abs_guid = abs(tp1)
                entry_resolved["target_param1"] = {"meaning": "gameobject_guid", "raw": tp1, "resolved_to": f"guid:{abs_guid}"}

            # Player with aura: param1=spellID
            if target_type == 201 and tp1:
                sn = resolve_dbc_ref(server, "Spell", tp1)
                entry_resolved["target_param1"] = {"meaning": "SpellId (aura)", "raw": tp1, "resolved_to": sn}

        # --- Position coordinates annotation ---
        tx = row.get("target_x")
        ty = row.get("target_y")
        tz = row.get("target_z")
        if target_type == 8 and any(v is not None and v != 0 for v in [tx, ty, tz]):
            entry_resolved["position"] = {
                "type_name": "POSITION",
                "x": tx,
                "y": ty,
                "z": tz,
                "orientation": row.get("target_o"),
            }

        # TELEPORT destination coordinates (action_type 62 uses target_x/y/z/o as dest)
        if action_type == 62 and any(v is not None and v != 0 for v in [tx, ty, tz]):
            entry_resolved["teleport_destination"] = {
                "map_id": ap1,
                "x": tx,
                "y": ty,
                "z": tz,
                "orientation": row.get("target_o"),
            }

        # Skip empty entries — only include if we resolved something meaningful
        if entry_resolved:
            pk = str(abs(entryorguid)) + "_" + str(row.get("source_type", 0)) + "_" + str(row.get("id", 0))
            resolved[pk] = entry_resolved

    return resolved
