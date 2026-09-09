"""enums tool: decode C++ enum values from the AzerothCore source.

Indexes every named enum in the source tree (core/enums.py, one cached
pass) and decodes magic numbers:
  enums()                          -> summary (count, biggest enums)
  enums(search="mech")             -> enum names matching the substring
  enums(enum="Mechanics", value=17)-> "MECHANIC_POLYMORPH"
  enums(enum="Mechanics")          -> full value table
  enums(value=17)                  -> which enums contain value 17
  enums(enum="Mechanics", member="POLYMORPH") -> reverse lookup

Answers the "what does this number mean?" class of questions (eval T1:
Spell.Mechanic=17 -> MECHANIC_POLYMORPH) without the agent grepping the
tree. Works with any azerothcore-wotlk source layout (ACORE_SRC_ROOT
override); a missing tree is a clean error.
"""

from typing import Any, Dict, List, Optional

from core import enum_index as enums_core

_MAX_TABLE = 300
_MAX_SCAN = 20


def _get_index(server) -> Dict[str, Dict[str, Any]]:
    if not hasattr(server, "_enum_index") or server._enum_index is None:
        server._enum_index = enums_core.build_enum_index()
    return server._enum_index


def enums_tools(server) -> Dict[str, Any]:
    args = server.args or {}

    enum_name = args.get("enum")
    value = args.get("value")
    member = args.get("member")
    search = args.get("search")

    if value is not None and (not isinstance(value, (int, float))
                              or isinstance(value, bool)):
        return {"error": "'value' must be a number.", "isError": True}
    if value is not None:
        value = int(value)

    index = _get_index(server)
    if not index:
        return {
            "error": (
                f"No enums found - C++ source tree not available at "
                f"{enums_core._src_root()}. Set ACORE_SRC_ROOT to the "
                f"azerothcore-wotlk source root."
            ),
            "isError": True,
        }

    # ---- direct decode: enum + value ---------------------------------------
    if isinstance(enum_name, str) and enum_name and value is not None:
        info = index.get(enum_name)
        if info is None:
            import difflib
            close = difflib.get_close_matches(enum_name, index.keys(), n=5)
            return {
                "error": f"Enum '{enum_name}' not found in the source.",
                **({"did_you_mean": close} if close else {}),
                "isError": True,
            }
        members = info["members"]
        if value in members:
            return {
                "enum": enum_name,
                "value": value,
                "member": members[value],
                "file": info["file"],
            }
        # near values for orientation
        near = {v: members[v] for v in sorted(members)
                if abs(v - value) <= 2 and v != value}
        return {
            "enum": enum_name,
            "value": value,
            "member": None,
            "error": f"Value {value} is not in enum {enum_name}.",
            **({"nearby": near} if near else {}),
            "file": info["file"],
            "isError": True,
        }

    # ---- reverse lookup: enum + member name --------------------------------
    if isinstance(enum_name, str) and enum_name and isinstance(member, str):
        info = index.get(enum_name)
        if info is None:
            import difflib
            close = difflib.get_close_matches(enum_name, index.keys(), n=5)
            return {
                "error": f"Enum '{enum_name}' not found in the source.",
                **({"did_you_mean": close} if close else {}),
                "isError": True,
            }
        needle = member.upper()
        hits = {v: n for v, n in info["members"].items() if needle in n.upper()}
        if not hits:
            return {"error": f"No member matching '{member}' in {enum_name}.",
                    "isError": True}
        return {"enum": enum_name, "member": member,
                "matches": hits}

    # ---- full table: enum ----------------------------------------------------
    if isinstance(enum_name, str) and enum_name:
        info = index.get(enum_name)
        if info is None:
            import difflib
            close = difflib.get_close_matches(enum_name, index.keys(), n=5)
            return {
                "error": f"Enum '{enum_name}' not found in the source.",
                **({"did_you_mean": close} if close else {}),
                "isError": True,
            }
        members = dict(sorted(info["members"].items()))
        return {
            "enum": enum_name,
            "member_count": len(members),
            "file": info["file"],
            "members": members if len(members) <= _MAX_TABLE
                       else dict(list(members.items())[:_MAX_TABLE]),
            **({"truncated": True} if len(members) > _MAX_TABLE else {}),
        }

    # ---- value scan across all enums -----------------------------------------
    if value is not None:
        hits = enums_core.find_enums_by_value(index, value, _MAX_SCAN)
        return {
            "value": value,
            "matches": hits,
            "metadata": {
                "note": (
                    "Values are only meaningful within their enum - pick the "
                    "enum that matches your field (e.g. Spell.Mechanic -> "
                    "'Mechanics'), then use enum=... value=... for a "
                    "definitive answer."
                ) if len(hits) > 1 else
                    "Single match - unambiguous."
            },
        }

    # ---- name search / summary -------------------------------------------------
    if isinstance(search, str) and search:
        s = search.lower()
        names = sorted(n for n in index if s in n.lower())[:50]
        return {
            "search": search,
            "match_count": len(names),
            "enums": names,
        }

    sized = sorted(index.items(), key=lambda kv: -len(kv[1]["members"]))
    return {
        "enum_count": len(index),
        "total_members": sum(len(i["members"]) for i in index.values()),
        "largest": [
            {"enum": n, "member_count": len(i["members"]), "file": i["file"]}
            for n, i in sized[:15]
        ],
        "metadata": {
            "note": "Use enum='Name' for the full table, enum='Name' value=N "
                    "to decode, or search='...'/value=N to find enums.",
        },
    }


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "enums",
        "description": (
            "Decode C++ enum values from the AzerothCore source: enums() = "
            "summary; enums(search='mech') = name search; "
            "enums(enum='Mechanics', value=17) = decode a value "
            "(MECHANIC_POLYMORPH); enums(enum='Mechanics') = full value "
            "table; enums(value=17) = which enums contain the value; "
            "enums(enum='Mechanics', member='POLYMORPH') = reverse lookup. "
            "Requires the C++ source tree (ACORE_SRC_ROOT); absence is a "
            "clean error."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "enum": {
                    "type": "string",
                    "description": "Enum name (exact, as in the C++ source)."
                },
                "value": {
                    "type": "number",
                    "description": "Value to decode (with enum=) or scan for."
                },
                "member": {
                    "type": "string",
                    "description": "Member-name substring for reverse lookup (with enum=)."
                },
                "search": {
                    "type": "string",
                    "description": "Case-insensitive substring match on enum names."
                },
            },
        },
    }
