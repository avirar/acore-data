#!/usr/bin/env python3
"""Registry hygiene migration (one-off, idempotent).

Adds the live-but-unregistered tables discovered by the coverage audit:
  - playerbots_bis_gear  (acore_playerbots; present only with mod-playerbots)
  - updates / updates_include (SQL update-management, all four DBs)
  - version              (acore_world core/DB version row)

Run: .venv/bin/python3 scripts/update_registry_hygiene.py
Re-running is a no-op (entries are skipped if already present).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REG = ROOT / "datastore_registry.json"


def F(name, type_, col=None):
    return {"name": name, "type": type_, "sql_column": col or name}


NEW_ENTRIES = {
    "Updates": {
        "category": "sql_auxiliary",
        "sql_table": "updates",
        "sql_database": "acore_world",
        "c_struct": "Updates",
        "fields": {
            "0": F("name", "string"),
            "1": F("hash", "string"),
            "2": F("state", "string"),
            "3": F("timestamp", "string"),
            "4": F("speed", "uint32"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "SQL update-management table. Present in all four databases "
            "(acore_world, acore_characters, acore_auth, acore_playerbots); "
            "rows track which .sql updates are applied (state RELEASED/ARCHIVED/CUSTOM). "
            "For another DB, query via sql tool with `USE <db>;` prefix."
        ),
    },
    "UpdatesInclude": {
        "category": "sql_auxiliary",
        "sql_table": "updates_include",
        "sql_database": "acore_world",
        "c_struct": "UpdatesInclude",
        "fields": {
            "0": F("path", "string"),
            "1": F("state", "string"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "SQL update-management table (directory includes), present in all four databases."
        ),
    },
    "Version": {
        "category": "sql_auxiliary",
        "sql_table": "version",
        "sql_database": "acore_world",
        "c_struct": "Version",
        "fields": {
            "0": F("core_version", "string"),
            "1": F("core_revision", "string"),
            "2": F("db_version", "string"),
            "3": F("cache_id", "uint32"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": "AzerothCore core/DB version row (single row in acore_world).",
    },
    "PlayerbotsBisGear": {
        "category": "sql_auxiliary",
        "sql_table": "playerbots_bis_gear",
        "sql_database": "acore_playerbots",
        "c_struct": "PlayerbotsBisGear",
        "fields": {
            "0": F("class", "uint32"),
            "1": F("tab", "uint32"),
            "2": F("slot", "uint32"),
            "3": F("faction", "uint32"),
            "4": F("auto_gear_score_limit", "uint32"),
            "5": F("item_id", "uint32"),
            "6": F("phase", "string"),
            "7": F("class_name", "string"),
            "8": F("spec_name", "string"),
            "9": F("slot_name", "string"),
            "10": F("faction_name", "string"),
            "11": F("item_name", "string"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "mod-playerbots: best-in-slot gear per class/spec/phase used by bot gear "
            "selection. Optional table - only present when mod-playerbots is installed "
            "(absent on upstream AzerothCore installs); item_id references item_template."
        ),
    },
    "RbacPermissions": {
        "category": "sql_auxiliary",
        "sql_table": "rbac_permissions",
        "sql_database": "acore_auth",
        "c_struct": "RbacPermissions",
        "fields": {
            "0": F("id", "uint32"),
            "1": F("name", "string"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "RBAC: permission definitions (GM role names). permissionId in the other "
            "rbac_* tables references this id."
        ),
    },
    "RbacAccountPermissions": {
        "category": "sql_auxiliary",
        "sql_table": "rbac_account_permissions",
        "sql_database": "acore_auth",
        "c_struct": "RbacAccountPermissions",
        "fields": {
            "0": F("accountId", "uint32"),
            "1": F("permissionId", "uint32"),
            "2": F("granted", "uint8"),
            "3": F("realmId", "int32"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "RBAC: per-account permission grants. accountId -> accounts in acore_auth; "
            "permissionId -> rbac_permissions.id."
        ),
    },
    "RbacDefaultPermissions": {
        "category": "sql_auxiliary",
        "sql_table": "rbac_default_permissions",
        "sql_database": "acore_auth",
        "c_struct": "RbacDefaultPermissions",
        "fields": {
            "0": F("secId", "uint32"),
            "1": F("permissionId", "uint32"),
            "2": F("realmId", "int32"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "RBAC: default permissions per security level (secId = SecurityLevel enum). "
            "permissionId -> rbac_permissions.id."
        ),
    },
    "RbacLinkedPermissions": {
        "category": "sql_auxiliary",
        "sql_table": "rbac_linked_permissions",
        "sql_database": "acore_auth",
        "c_struct": "RbacLinkedPermissions",
        "fields": {
            "0": F("id", "uint32"),
            "1": F("linkedId", "uint32"),
        },
        "loader_function": "",
        "store_variable": "",
        "header_file": "",
        "container_type": "",
        "is_leaf": True,
        "reference_notes": (
            "RBAC: linked permissions (id -> rbac_permissions.id, grants also include linkedId)."
        ),
    },
}


def main():
    reg = json.loads(REG.read_text())
    entries, indices, meta = reg["entries"], reg["indices"], reg["_meta"]

    added = 0
    for name, entry in NEW_ENTRIES.items():
        if name in entries:
            print(f"skip {name} (already present)")
            continue
        entries[name] = entry
        indices["by_struct_name"][name] = name
        indices["by_sql_table"][entry["sql_table"]] = name
        added += 1
        print(f"added {name} -> {entry['sql_table']}")

    # second pass: FK reference annotations (idempotent; applies to
    # entries added by an earlier run too)
    refs_applied = 0
    for name, field_key, target in [
        ("PlayerbotsBisGear", "5", "ItemTemplate"),       # item_id -> item_template
        ("RbacAccountPermissions", "1", "RbacPermissions"),  # permissionId
        ("RbacDefaultPermissions", "1", "RbacPermissions"),  # permissionId
        ("RbacLinkedPermissions", "1", "RbacPermissions"),   # linkedId
    ]:
        e = entries.get(name)
        if not e:
            continue
        f = e.get("fields", {}).get(field_key)
        if f and f.get("references") != target:
            f["references"] = target
            refs_applied += 1
            print(f"reference {name}.{field_key} -> {target}")

    if added or refs_applied:
        meta["total_entries"] = len(entries)
        REG.write_text(json.dumps(reg, indent=2) + "\n")
        print(f"\n{added} entries added, {refs_applied} references set; total_entries = {meta['total_entries']}")
    else:
        print("\nno changes (registry already up to date)")


if __name__ == "__main__":
    main()
