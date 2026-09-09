"""travel tool: mod-playerbots travel graph inspection & verification.

The mod-playerbots TravelMgr builds bot travel routes from a node/path graph
stored in `acore_playerbots` (playerbots_travelnode / playerbots_travelnode_path,
~1.4M path points). This tool inspects that graph statically and verifies
paths against the actual MMap terrain data - the same mmap/vmap data the
worldserver uses at runtime - without needing a running server.

Modes (all read-only, acore_playerbots + mmap data; the mod DB is optional -
absence is a clean error, not a crash):
  travel(map=0)                 -> graph stats (nodes, edges, path points)
  travel(map=0, node=2776)      -> node details + neighbours
  travel(map=0, from=0, to=2776)-> decoded path + navmesh verification
"""

from typing import Any, Dict, List, Optional

DB = "acore_playerbots"
_MAX_POINTS_SHOWN = 200
_OFF_GROUND_TOLERANCE = 5.0


class _TravelError(Exception):
    pass


def _query(server, sql: str, params: Optional[List[Any]] = None,
           limit_guard: bool = True):
    rows, err = server.database._query_database(sql, db_name=DB, params=params)
    if err:
        if "doesn't exist" in err or "Unknown database" in err:
            raise _TravelError(
                "acore_playerbots database not found - this install does not "
                "have mod-playerbots (the travel graph only exists with the mod)."
            )
        raise _TravelError(f"query failed: {err[:200]}")
    return rows or []


def _node(server, map_id: int, node_id: int) -> Optional[Dict[str, Any]]:
    rows = _query(
        server,
        "SELECT id, name, x, y, z, linked FROM playerbots_travelnode "
        "WHERE map_id = %s AND id = %s",
        [map_id, node_id],
    )
    return rows[0] if rows else None


def _stats(server, map_id: int) -> Dict[str, Any]:
    n = _query(
        server,
        "SELECT COUNT(*) AS c, SUM(linked) AS linked FROM playerbots_travelnode "
        "WHERE map_id = %s",
        [map_id],
    )
    p = _query(
        server,
        "SELECT COUNT(*) AS points, COUNT(DISTINCT CONCAT(node_id, ',', to_node_id)) AS edges "
        "FROM playerbots_travelnode_path WHERE map_id = %s",
        [map_id],
    )
    samples = _query(
        server,
        "SELECT id, name, x, y, z FROM playerbots_travelnode "
        "WHERE map_id = %s AND name != '' ORDER BY id LIMIT 5",
        [map_id],
    )
    nodes = int(n[0]["c"] or 0) if n else 0
    points = int(p[0]["points"] or 0) if p else 0
    edges = int(p[0]["edges"] or 0) if p else 0
    if not nodes and not points:
        raise _TravelError(
            f"No travel data for map {map_id} - the travel graph was never "
            "generated for this map (run 'travelmgr gen' on the worldserver "
            "to build it, or check the map id)."
        )
    return {
        "mode": "stats",
        "map": map_id,
        "node_count": nodes,
        "linked_nodes": int(n[0]["linked"] or 0) if n else 0,
        "path_point_count": points,
        "edge_count": edges,
        "sample_named_nodes": [
            {"id": r["id"], "name": r["name"],
             "x": round(float(r["x"]), 2), "y": round(float(r["y"]), 2),
             "z": round(float(r["z"]), 2)}
            for r in samples
        ],
        "metadata": {
            "sql_tables": ["playerbots_travelnode", "playerbots_travelnode_path"],
            "sql_database": DB,
            "note": "Use travel(map, node=N) to inspect a node or "
                    "travel(map, from=A, to=B) to decode + verify a path.",
        },
    }


def _node_details(server, map_id: int, node_id: int) -> Dict[str, Any]:
    node = _node(server, map_id, node_id)
    if not node:
        # suggest near ids
        near = _query(
            server,
            "SELECT id, name FROM playerbots_travelnode "
            "WHERE map_id = %s ORDER BY ABS(id - %s) LIMIT 5",
            [map_id, node_id],
        )
        raise _TravelError(
            f"No node {node_id} on map {map_id}. Nearest ids: "
            + str([{"id": r["id"], "name": r["name"]} for r in near])
        )
    out_go = _query(
        server,
        "SELECT DISTINCT to_node_id FROM playerbots_travelnode_path "
        "WHERE map_id = %s AND node_id = %s LIMIT 50",
        [map_id, node_id],
    )
    in_go = _query(
        server,
        "SELECT DISTINCT node_id FROM playerbots_travelnode_path "
        "WHERE map_id = %s AND to_node_id = %s LIMIT 50",
        [map_id, node_id],
    )
    names = {}
    for r in out_go + in_go:
        nid = int(r["to_node_id"] if "to_node_id" in r else r["node_id"])
        if nid not in names:
            n = _node(server, map_id, nid)
            names[nid] = n["name"] if n else None
    return {
        "mode": "node",
        "map": map_id,
        "node": {
            "id": int(node["id"]),
            "name": node["name"],
            "x": round(float(node["x"]), 2),
            "y": round(float(node["y"]), 2),
            "z": round(float(node["z"]), 2),
            "linked": int(node["linked"]),
        },
        "neighbours": {
            "outgoing": [{"id": int(r["to_node_id"]), "name": names.get(int(r["to_node_id"]))}
                         for r in out_go],
            "incoming": [{"id": int(r["node_id"]), "name": names.get(int(r["node_id"]))}
                         for r in in_go],
        },
        "metadata": {
            "sql_tables": ["playerbots_travelnode", "playerbots_travelnode_path"],
            "sql_database": DB,
        },
    }


def _verify_path(server, map_id: int, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check path points against MMap terrain. Best-effort: no mmap data for
    the map degrades to a note instead of an error."""
    try:
        from core.terrain.map_reader import MapReader, INVALID_HEIGHT
        from core.terrain.coords import get_data_paths
    except Exception as e:  # terrain core not present
        return {"checked": 0, "note": f"terrain core unavailable: {e}"}

    try:
        reader = MapReader(get_data_paths()["maps"])
    except Exception as e:
        return {"checked": 0, "note": f"could not open maps data: {e}"}

    checked = 0
    off_ground = []
    for pt in points:
        h = reader.get_height(map_id, pt["x"], pt["y"])
        if h == INVALID_HEIGHT:
            continue
        checked += 1
        dz = abs(pt["z"] - h)
        if dz > _OFF_GROUND_TOLERANCE and len(off_ground) < 5:
            off_ground.append({
                "x": pt["x"], "y": pt["y"],
                "path_z": pt["z"], "ground_z": round(h, 2), "dz": round(dz, 2),
            })
    result = {
        "checked": checked,
        "off_ground_count": len(off_ground),
        "off_ground_examples": off_ground,
    }
    if checked == 0:
        result["note"] = "no MMap terrain data for this map - verification skipped"
        return result
    if not off_ground:
        result["note"] = (
            f"all {checked} points sit within {_OFF_GROUND_TOLERANCE}m of the "
            "MMap ground - path is terrain-consistent"
        )
    return result


def _path(server, map_id: int, from_id: int, to_id: int,
          verify: bool) -> Dict[str, Any]:
    src = _node(server, map_id, from_id)
    dst = _node(server, map_id, to_id)
    if not src and not dst:
        raise _TravelError(f"Neither node {from_id} nor {to_id} exists on map {map_id}.")
    if not src:
        raise _TravelError(f"Start node {from_id} does not exist on map {map_id}.")
    if not dst:
        raise _TravelError(f"End node {to_id} does not exist on map {map_id}.")

    rows = _query(
        server,
        "SELECT nr, x, y, z FROM playerbots_travelnode_path "
        "WHERE map_id = %s AND node_id = %s AND to_node_id = %s ORDER BY nr",
        [map_id, from_id, to_id],
    )
    if not rows:
        # reverse direction?
        rev = _query(
            server,
            "SELECT nr, x, y, z FROM playerbots_travelnode_path "
            "WHERE map_id = %s AND node_id = %s AND to_node_id = %s ORDER BY nr",
            [map_id, to_id, from_id],
        )
        if rev:
            raise _TravelError(
                f"No direct path {from_id} -> {to_id}, but the reverse "
                f"({to_id} -> {from_id}) exists with {len(rev)} points."
            )
        raise _TravelError(
            f"No stored path between nodes {from_id} and {to_id} on map {map_id}. "
            "Check the node ids (travel(map, node=N) lists neighbours) or "
            "regenerate the map's travel graph."
        )

    pts = [
        {"nr": int(r["nr"]), "x": round(float(r["x"]), 2),
         "y": round(float(r["y"]), 2), "z": round(float(r["z"]), 2)}
        for r in rows
    ]
    out: Dict[str, Any] = {
        "mode": "path",
        "map": map_id,
        "from": {"id": from_id, "name": src["name"]},
        "to": {"id": to_id, "name": dst["name"]},
        "point_count": len(pts),
        "points": pts[:_MAX_POINTS_SHOWN],
        "metadata": {
            "sql_tables": ["playerbots_travelnode", "playerbots_travelnode_path"],
            "sql_database": DB,
        },
    }
    if len(pts) > _MAX_POINTS_SHOWN:
        out["points_truncated"] = True
    if verify:
        out["navmesh_verification"] = _verify_path(server, map_id, pts)
    return out


def travel_tools(server) -> Dict[str, Any]:
    args = server.args
    args = args or {}

    map_id = args.get("map")
    if not isinstance(map_id, int) or isinstance(map_id, bool):
        return {"error": "'map' is required and must be a map id (number).",
                "isError": True}

    from_id = args.get("from")
    to_id = args.get("to")
    node_id = args.get("node")
    verify = args.get("verify", True)

    mode = "path" if (from_id is not None or to_id is not None) else \
        "node" if node_id is not None else "stats"

    def _check(n, label):
        if n is None or not isinstance(n, int) or isinstance(n, bool) or n < 0:
            return False
        return True

    try:
        if mode == "path":
            if from_id is None:
                return {"error": "'from' is required for path mode.", "isError": True}
            if to_id is None:
                return {"error": "'to' is required for path mode.", "isError": True}
            if not _check(from_id, "from") or not _check(to_id, "to"):
                return {"error": "'from' and 'to' must be non-negative node ids.",
                        "isError": True}
            return _path(server, map_id, from_id, to_id, verify)
        elif mode == "node":
            if not _check(node_id, "node"):
                return {"error": "'node' must be a non-negative node id.", "isError": True}
            return _node_details(server, map_id, node_id)
        else:
            return _stats(server, map_id)
    except _TravelError as e:
        return {"error": str(e), "isError": True}


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "travel",
        "description": (
            "Inspect the mod-playerbots travel graph and verify paths against the "
            "MMap navmesh (no running server needed). travel(map=M): graph stats "
            "(nodes/edges/path points). travel(map=M, node=N): node details + "
            "neighbours. travel(map=M, from=A, to=B): decoded path points plus "
            "terrain verification (points off the ground by >5m are flagged). "
            "Requires acore_playerbots (mod-playerbots); its absence is a clean "
            "error. Arbitrary-coordinate routing is done at runtime by the "
            "worldserver (TravelMgr)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "map": {
                    "type": "number",
                    "description": "Map id (required)."
                },
                "node": {
                    "type": "number",
                    "description": "Node id to inspect (node mode; lists neighbours)."
                },
                "from": {
                    "type": "number",
                    "description": "Start node id (path mode; requires 'to')."
                },
                "to": {
                    "type": "number",
                    "description": "End node id (path mode; requires 'from')."
                },
                "verify": {
                    "type": "boolean",
                    "description": "Path mode only: verify points against MMap terrain (default true)."
                },
            },
            "required": ["map"],
        },
    }
