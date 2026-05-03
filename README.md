# acore-data

MCP server providing unified query access to **~462 AzerothCore game datastores** — DBC binary files, SQL tables, SQL overlays, and auxiliary stores. Exposes four tools (`query`, `lookup`, `list`, `sql`) over the JSON-RPC based [Model Context Protocol](https://modelcontextprotocol.io/).

## Overview

AzerothCore stores game data in four categories of datastores. This server gives any MCP-compatible client (LLM, IDE plugin, CLI) a single entry point to query all of them by name, with automatic name resolution, type-aware field annotation, and smart SQL routing.

| Category | Count | Description |
|----------|------:|-------------|
| `dbc_backed` | ~112 | Binary `.dbc` files loaded into packed C structs, with optional SQL overlay (`*_dbc` tables) |
| `sql_objectmgr` | ~95 | ObjectMgr SQL tables — creature templates, gameobjects, items, quests, gossip, etc. |
| `sql_manager` | ~48 | Tables loaded by other singleton managers (SpellMgr, PoolMgr, GameEventMgr, LootStore, …) |
| `sql_auxiliary` | ~171 | Discovered SQL tables not in the static registry |

For the full technical reference on how each category is loaded in AzerothCore, see [docs/datastores/README.md](docs/datastores/README.md).

## Tools

### `query`

Query any datastore by name. Accepts a DBC file name (`"Spell"`), SQL table name (`"quest_template"`), or C++ struct name (`"SpellEntry"`).

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | **Required.** Datastore name. Use `lookup` to find valid names. |
| `id` | number | Primary key for O(1) lookup. Mutually exclusive with `filter`. |
| `filter` | object | Named field filters. Supports `$like` / `$ilike` patterns. |
| `fields` | array | Select specific fields by index `[38, 39]` or name `["BaseLevel", "SpellLevel"]`. |
| `limit` | number | Max records to return (default 100). |
| `compact` | boolean | Strip null/zero fields (default `true`). |
| `resolve` | boolean or array | Resolve type-specific data fields. `true` = all, or `["dbc", "sql", "loot"]`. |
| `resolve_max` | number | Max items per loot table resolution (default 10). Use 0 for unlimited. |

**Examples:**

```
query(name="Spell", id=118)
→ O(1) DBC lookup for Polymorph

query(name="quest_template", filter={"Title": {"$ilike": "%murloc%"}})
→ SQL $ilike search across all quest titles

query(name="gameobject_template", id=180013, resolve=true)
→ Returns gameobject data with data[0-19] annotated (lockId, lootId, spellId, etc.)

query(name="Spell", id=118, fields=[38, 39], compact=true)
→ Select only BaseLevel and SpellLevel fields
```

For DBC-backed stores that also have an SQL overlay table, `query` merges both sources — SQL overlay data replaces or supplements the binary DBC data.

### `lookup`

Get schema and metadata for any datastore. Resolves by C++ struct name, SQL table, DBC file, or store variable (e.g. `sSpellStore`).

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | **Required.** Name to resolve. |
| `detail` | string | `"schema"` (default) — full field list. `"summary"` — 10 sample fields. |

Returns field definitions (name, type, SQL column, references), live SQL column metadata from the database, cross-references, and access hints (e.g. `sSpellStore.LookupEntry(id) -> SpellEntry const*`).

**Examples:**

```
lookup(query="SpellEntry")
→ Full schema with all 183 fields, SQL columns, and cross-references

lookup(query="creature_template", detail="summary")
→ Compact 10-field sample + live SQL columns from the database

lookup(query="sSpellStore")
→ Resolves store variable to SpellEntry with access pattern hints
```

### `list`

List available datastores with optional search and category filtering.

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Filter by struct name, table, DBC file, or store variable. |
| `category` | string | `"all"` (default), `"dbc_backed"`, `"sql_objectmgr"`, `"sql_manager"`, `"sql_auxiliary"`. |

**Examples:**

```
list(category="dbc_backed")
→ All ~112 DBC-backed stores with format info and field counts

list(search="Quest")
→ All stores matching "Quest" in name, table, or DBC file
```

### `sql`

Execute raw SQL queries with automatic database routing and typo suggestions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | **Required.** SQL query (SELECT, INSERT, UPDATE, DELETE only). |

Features:
- **Smart routing** — automatically directs queries to `acore_world`, `acore_characters`, or `acore_auth` based on table name
- **Typo suggestions** — suggests correct table and column names on errors
- **Safety** — blocks DROP, TRUNCATE, ALTER, GRANT, REVOKE
- **Context hints** — e.g. empty loot_template results suggest trying questitem tables

**Examples:**

```
sql(query="SELECT entry, name FROM creature_template WHERE entry = 1")
→ Routes to acore_world

sql(query="SELECT id, username FROM account LIMIT 5")
→ Auto-routes to acore_auth

sql(query="SELECT * FROM creature_templat LIMIT 1")
→ Error with suggestion: "Did you mean: creature_template?"
```

## Type Resolver

The `resolve` parameter on `query` enables type-aware field resolution for tables whose fields change meaning based on a type column. Resolution types:
- **`"dbc"`** — resolve to DBC entries (e.g. `LockEntry`, `SpellEntry`, `MapEntry`)
- **`"sql"`** — resolve to SQL tables (e.g. `quest_template`, `gossip_menu`, `page_text`)
- **`"loot"`** — expand loot templates into item lists with names

### Registry-driven resolution

Any table with cross-reference metadata in `datastore_registry.json` gets automatic field resolution via `_resolve_generic()`. Fields like faction, lootId, spellId are resolved to their target entries by name.

### Specialized table resolvers

In addition to generic registry-driven resolution, these tables have dedicated resolver modules that enrich results with custom data:

| Table | Resolver module | What it resolves |
|-------|-----------------|------------------|
| `gameobject_template` | `resolvers/gameobject.py` | type-aware `data[0-19]` annotation (lockId, lootId, spellId …) |
| `smart_scripts` | `resolvers/smart_scripts.py` | EVENT_ID/ACTION_ID/TARGET_ID → enum names + value meaning |
| `quest_template` | `resolvers/quest.py` | starter/ender NPCs, POIs, quest chain (prev/next/breadcrumb) |
| `conditions` | `resolvers/condition.py` | polymorphic SourceType → entity name, ConditionType (~49 types: AURA, QUEST, ITEM, ALIVE, CLASS, etc.), TYPEID/GENDER/RACE enums |
| `achievement_criteria_data` | `resolvers/achievement_criteria.py` | CriterionType-specific field interpretation |
| `item_template` | `resolvers/item.py` | loot template for openable items (`Flags & 0x04`) |
| `Spell` (DBC) | `resolvers/spell.py` | cast conditions from `conditions` table with full enum resolution |

```
query(name="quest_template", id=4512, resolve=true)
→ Start/ender NPCs, chain info, POIs, plus faction/spell/item refs

query(name="Spell", id=15698, resolve=true)
→ Cast conditions: "OBJECT_ENTRY_GUID(UNIT)=creature_template [Cursed Ooze], NOT_ALIVE"

query(name="item_template", id=11912, resolve=["loot"])
→ Openable item → 6x Empty Cursed Jar, 6x Empty Tainted Jar

query(name="conditions", filter={"SourceTypeOrReferenceId": 17, "SourceEntry": 15698}, resolve=true)
→ Polymorphic: source type name, condition type enum, resolved entity names

query(name="gameobject_template", id=12345, resolve=["loot"], resolve_max=20)
→ Expand loot template into up to 20 item names
```

## Setup

### Requirements

- Python 3.9+
- `pymysql` — installed via `requirements.txt` into `.venv`
- Access to an AzerothCore MySQL instance (for SQL tools)
- DBC binary files and `DBCfmt.h` from the AzerothCore source/build

### Environment Variables

| Variable | Default |
|----------|---------|
| `ACORE_DBC_PATH` | `/root/azerothcore-wotlk/env/dist/bin/dbc` |
| `ACORE_FORMAT_FILE` | `/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h` |
| `DB_HOST` | Auto-detected |
| `DB_PORT` | `3306` |
| `DB_USER` | Auto-detected |
| `DB_PASSWORD` | Auto-detected |
| `DB_NAME` | `acore_world` |

When `DB_HOST` and `DB_USER` are empty, the server attempts auto-detection from common AzerothCore configuration files.

### Running

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python3 server.py
```

**IMPORTANT:** The server MUST be launched with the `.venv` Python (`.venv/bin/python3`), NOT the system `python3`. The system Python won't have `pymysql`, causing silent fallback to the `mysql` CLI subprocess — which doesn't support parameterized queries and breaks all SQL lookups.

If run via an MCP client, point the command at the venv's Python:
```json
"command": ["/path/to/acore-data/.venv/bin/python3", "server.py"]
```

To test manually:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | .venv/bin/python3 server.py
```

## Testing

```bash
# Integration tests (30 tests — requires running MySQL)
bash test_integration.sh

# Python unit/integration tests (39 tests)
python3 -m pytest tests/ -v

# Or without pytest
python3 tests/test_integration.py
python3 tests/test_helpers.py
```

## Project Structure

```
acore-data/
├── server.py                    # MCP server entry point (JSON-RPC over stdio)
├── datastore_registry.json      # Static metadata for all ~467 datastores
├── requirements.txt             # pymysql >= 1.1, pytest >= 7.0
│
├── core/
│   ├── annotation.py            # DBC field annotation, filter conversion, schema errors
│   ├── database.py              # MySQL connection (pymysql), table discovery, smart routing
│   ├── dbc.py                   # WDBC binary file reader
│   ├── enums.py                 # Shared enum dicts: condition types, SOURCE_TYPE, TYPEID …
│   ├── formats.py               # DBCfmt.h parser (format strings → field types)
│   ├── registry.py              # Datastore registry: name resolution, fuzzy matching
│   ├── type_resolver.py         # Dispatcher + generic registry-driven resolution engine
│   └── resolvers/               # Specialized table-specific resolver modules
│       ├── __init__.py          # Resolver registry (table_name → func)
│       ├── gameobject.py        # data[0-19] annotation for GAMEOBJECT_TYPE subtypes
│       ├── smart_scripts.py     # EVENT_ID/ACTION_ID/TARGET_ID enum + value meaning
│       ├── quest.py             # Starter/ender NPCs, POIs, chain info (prev/next/breadcrumb)
│       ├── condition.py         # Polymorphic: SourceType → entity, ConditionType (~49 types), TYPEID/GENDER/RACE enums
│       ├── achievement_criteria.py  # CriterionType-specific field interpretation
│       ├── item.py              # Loot template for openable items (Flags & 0x04)
│       ├── spell.py             # Cast conditions from `conditions` table with full enum resolution
│       └── ref_utils.py         # Shared helpers: resolve_dbc_ref, resolve_sql_ref, batch_resolve_sql, resolve_loot_ref
│
├── tools/
│   ├── query.py                 # Unified query tool (DBC + SQL + overlay merge)
│   ├── lookup.py                # Schema/metadata lookup tool
│   ├── list.py                  # Datastore listing tool
│   └── sql.py                   # Raw SQL execution with routing and suggestions
│
├── tests/
│   ├── test_integration.py      # Integration tests (live DB)
│   └── test_helpers.py          # Unit tests
│
├── docs/datastores/             # Technical reference for AzerothCore datastore internals
│   ├── README.md                # Overview of DBC pipeline, SQL overlay, format strings
│   ├── dbc-backed-stores.md
│   ├── sql-objectmgr-stores.md
│   ├── sql-manager-stores.md
│   ├── sql-auxiliary-stores.md
│   └── cross-reference.md
│
├── generators/                  # Scripts to generate/update the registry
│   ├── generate_registry.py
│   └── generate_supplementary.py
│
└── scripts/                     # Utility scripts for cross-refs, column mappings, etc.
    ├── add_cross_references.py
    ├── update_sql_column_mappings.py
    └── ...
```

## How It Works

```
   MCP Client (LLM / IDE / CLI)
         │
         │  JSON-RPC over stdio
         ▼
   server.py  ───────────────────────────────────────
         │
         ├─► registry.py        datastore_registry.json
         │     Name resolution, fuzzy matching        (462 entries)
         │
         ├─► tools/query.py     ┌──► dbc.py           .dbc binary files
         │     Unified query    │    WDBCReader        (Spell.dbc, Map.dbc, …)
         │                      │
         │                      ├──► database.py       MySQL
         │                      │    Smart routing     (acore_world, _characters, _auth)
         │                      │
         │                      ├──► annotation.py     Field annotation
         │                      │    DBC ↔ SQL merge   + type-aware resolution
         │                      │
         │                      └──► type_resolver.py  gameobject_template
         │                                           data[] → lockId/lootId/spellId
         │
         ├─► tools/lookup.py    Schema + live SQL columns + cross-refs
         │
         ├─► tools/list.py      Category filtering + search
         │
         └─► tools/sql.py       Raw SQL with routing + typo suggestions
```
