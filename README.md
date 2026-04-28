# acore-data MCP Server

Unified data query tool for AzerothCore World of Warcraft server. Provides access to all game datastores: DBC binary files, SQL ObjectMgr tables, and SQL Manager stores.

## Tools

- `query(name, id?, filter?, fields?, limit?, compact?)` - Query any datastore
- `lookup(name, detail?)` - Get schema/metadata for a store
- `list(search?, category?)` - List available stores
- `sql(query)` - Execute raw SQL with smart routing

## Environment Variables

| Variable | Default |
|----------|---------|
| `ACORE_DBC_PATH` | `/root/azerothcore-wotlk/env/dist/bin/dbc` |
| `ACORE_FORMAT_FILE` | `/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h` |
| `DB_HOST` | (auto-detected) |
| `DB_PORT` | `3306` |
| `DB_USER` | (auto-detected) |
| `DB_PASSWORD` | (auto-detected) |
| `DB_NAME` | `acore_world` |

## Usage

```bash
python3 /root/acore-data/server.py
```

See AGENTS.md for LLM usage instructions.
