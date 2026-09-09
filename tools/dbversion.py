"""dbversion tool: database state / version audit.

One call answers "what core/DB state is this install in?":
  - core/DB version row (acore_world.version)
  - per-database SQL update state (RELEASED/ARCHIVED/CUSTOM/MODULE/PENDING)
  - pending updates that the worldserver has not applied yet
  - which of the four AzerothCore databases are present (acore_playerbots is
    optional - only with mod-playerbots)

Read-only; works on any azerothcore-wotlk install.
"""

from typing import Any, Dict, List, Optional

_DB_ORDER = ["acore_world", "acore_characters", "acore_auth", "acore_playerbots"]
_STATES = ["RELEASED", "ARCHIVED", "CUSTOM", "MODULE", "PENDING"]


def dbversion_tools(server) -> Dict[str, Any]:
    db = server.database
    if not db.db_available:
        return {"error": "Database not available.", "isError": True}

    # ---- core/DB version row (acore_world) -------------------------------
    vrows, verr = db._query_database(
        "SELECT core_version, core_revision, db_version, cache_id FROM version "
        "LIMIT 1",
        db_name="acore_world",
    )
    version: Dict[str, Any] = {}
    if verr:
        version["error"] = f"version table unreadable: {verr[:200]}"
    elif vrows:
        v = vrows[0]
        version = {
            "core_version": v.get("core_version"),
            "core_revision": v.get("core_revision"),
            "db_version": v.get("db_version"),
            "cache_id": v.get("cache_id"),
        }

    # ---- per-database update state ---------------------------------------
    databases: Dict[str, Any] = {}
    for db_name in _DB_ORDER:
        entry: Dict[str, Any] = {}

        trows, terr = db._query_database("SHOW TABLES", db_name=db_name)
        if terr:
            entry["installed"] = False
            databases[db_name] = entry
            continue
        entry["installed"] = True
        entry["tables"] = len(trows or [])

        srows, serr = db._query_database(
            "SELECT state, COUNT(*) AS c FROM updates GROUP BY state",
            db_name=db_name,
        )
        if serr:
            entry["updates_error"] = serr[:200]
            databases[db_name] = entry
            continue

        counts = {s: 0 for s in _STATES}
        applied = 0
        for r in srows or []:
            state = str(r.get("state", "")).upper()
            c = int(r.get("c") or 0)
            if state in counts:
                counts[state] = c
            if state != "PENDING":
                applied += c
        entry["updates"] = counts
        entry["applied"] = applied
        entry["pending"] = counts["PENDING"]

        # name the pending updates (capped) - the actionable signal
        if counts["PENDING"]:
            prows, _ = db._query_database(
                "SELECT name FROM updates WHERE state = 'PENDING' ORDER BY name LIMIT 20",
                db_name=db_name,
            )
            entry["pending_updates"] = [r["name"] for r in prows or []]

        databases[db_name] = entry

    playerbots_installed = databases.get("acore_playerbots", {}).get("installed", False)

    return {
        "version": version,
        "databases": databases,
        "mod_playerbots_installed": playerbots_installed,
        "metadata": {
            "note": (
                "PENDING updates have not been applied by the worldserver yet "
                "(they apply at server start). mod_playerbots_installed=false is "
                "expected on upstream AzerothCore installs."
            )
        },
    }


def get_schema() -> Dict[str, Any]:
    """Tool schema for MCP."""
    return {
        "name": "dbversion",
        "description": (
            "Database state audit for this AzerothCore install: core/DB version row, "
            "per-database SQL update state (RELEASED/ARCHIVED/CUSTOM/MODULE/PENDING "
            "counts), pending updates not yet applied by the worldserver, and which of "
            "the four databases are present (acore_playerbots only with mod-playerbots). "
            "Read-only; answers 'what core revision / DB state is this server in?'"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    }
