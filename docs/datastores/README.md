# AzerothCore Datastore Reference

## Overview

AzerothCore has three categories of datastores:

1. **DBC-Backed Stores** (~112 stores) - Binary `.dbc` files loaded into packed C structs via `DBCStorage<T>`, with optional SQL overlay tables (`*_dbc` in `db_world`). See [dbc-backed-stores.md](dbc-backed-stores.md).

2. **SQL-Only Stores (ObjectMgr)** (~100+ tables) - Template/spawn data for creatures, gameobjects, items, quests, etc. loaded directly via `WorldDatabase.Query()` into `std::unordered_map` containers managed by `ObjectMgr`. See [sql-objectmgr-stores.md](sql-objectmgr-stores.md).

3. **SQL Stores (Other Managers)** (~30+ managers) - Data loaded by other singleton managers: `SpellMgr`, `PoolMgr`, `GameEventMgr`, `LootStore`, `SmartAIMgr`, `ConditionMgr`, `WaypointMgr`, etc. See [sql-manager-stores.md](sql-manager-stores.md).

For a complete cross-reference index, see [cross-reference.md](cross-reference.md).

## Source File Map

### DBC Infrastructure

| File | Purpose |
|------|---------|
| `src/common/DataStores/DBCFileLoader.h/cpp` | Binary .dbc file parser |
| `src/server/shared/DataStores/DBCStore.h/cpp` | `DBCStorageBase` and `DBCStorage<T>` template |
| `src/server/shared/DataStores/DBCStorageIterator.h` | Forward iterator for DBCStorage |
| `src/server/shared/DataStores/DBCDatabaseLoader.h/cpp` | SQL overlay loader |
| `src/server/shared/DataStores/DBCStructure.h` | All ~112 `*Entry` C structs (packed with `#pragma pack(1)`) |
| `src/server/shared/DataStores/DBCfmt.h` | Format strings mapping DBC columns to C types |
| `src/server/shared/DataStores/DBCEnums.h` | Enumerations for DBC fields |
| `src/server/game/DataStores/DBCStores.h` | Declarations of all global `DBCStorage<T>` externs |
| `src/server/game/DataStores/DBCStores.cpp` | Store instantiation, `LoadDBCStores()`, post-load indexing |
| `data/sql/base/db_world/*_dbc.sql` | ~112 SQL overlay table definitions |

### SQL-Only Infrastructure

| File | Purpose |
|------|---------|
| `src/server/game/Globals/ObjectMgr.h/cpp` | `ObjectMgr` singleton - loads ~100+ SQL tables |
| `src/server/database/Database/Field.h` | Wraps a single SQL column value with `Get<T>()` |
| `src/server/database/Database/QueryResult.h` | `ResultSet` and `PreparedResultSet` wrappers |
| `src/server/database/Database/PreparedStatement.h` | Prepared statement support |
| `src/server/database/Database/DatabaseWorkerPool.h` | Connection pool manager |

### Struct Definition Files

| File | Key Structs |
|------|-------------|
| `src/server/game/Entities/Creature/CreatureData.h` | `CreatureTemplate`, `CreatureData`, `CreatureBaseStats`, `CreatureAddon`, `EquipmentInfo`, `VendorItem`, `CreatureModelInfo` |
| `src/server/game/Entities/GameObject/GameObjectData.h` | `GameObjectTemplate`, `GameObjectTemplateAddon`, `GameObjectData`, `GameObjectAddon` |
| `src/server/game/Entities/Item/ItemTemplate.h` | `ItemTemplate`, `ItemSetNameEntry` |
| `src/server/game/Quests/QuestDef.h` | `Quest` class |
| `src/server/game/Globals/ObjectMgr.h` | `PageText`, `BroadcastText`, `GameTele`, `ScriptInfo`, `GossipMenus`, `GossipMenuItems`, `PointOfInterest`, `QuestGreeting`, `QuestPOI`, `ReputationOnKillEntry`, etc. |
| `src/server/game/Spells/SpellMgr.h` | `SpellProcEntry`, `SpellBonusEntry`, `SpellThreatEntry`, `SpellArea`, `SpellChainNode`, `SpellCooldownOverride`, etc. |
| `src/server/game/Loot/LootMgr.h` | `LootStoreItem` |
| `src/server/game/AI/SmartScripts/SmartScriptMgr.h` | `SmartScriptHolder` |
| `src/server/game/Conditions/ConditionMgr.h` | `Condition` |
| `src/server/game/Events/GameEventMgr.h` | `GameEventData` |
| `src/server/game/Pools/PoolMgr.h` | `PoolTemplateData`, `PoolObject` |

## DBC Loading Pipeline

```
  .dbc Binary Files (client data)
         |
         v
  DBCFileLoader::Load()          -- Parse WDBC header + records
         |
         v
  AutoProduceData()              -- Generate packed C struct array + sparse index table
         |
         v
  AutoProduceStrings()           -- Resolve string pointers from DBC string table
         |
         v
  DBCStorageBase::Load()         -- Store into DBCStorage<T>
         |
         v
  LoadStringsFrom() x N locales  -- Overlay localized strings (enUS, deDE, frFR, etc.)
         |
         v
  LoadFromDB()                   -- SQL overlay via DBCDatabaseLoader
         |
         v
  Post-load indexing             -- Build auxiliary maps, sets, masks
         |
         v
  Ready: sXxxStore.LookupEntry(id) -> T const*
```

## Format String System

Each DBC type has a format string in `DBCfmt.h`. Characters map one-to-one to DBC columns:

| Char | Constant | C++ Type | Meaning |
|------|----------|----------|---------|
| `n` | `FT_IND` | `uint32` | Index field (used as lookup key, stored in struct) |
| `i` | `FT_INT` | `uint32` | Integer |
| `f` | `FT_FLOAT` | `float` | Floating-point |
| `s` | `FT_STRING` | `char*` | Localized string pointer |
| `b` | `FT_BYTE` | `uint8` | Byte |
| `d` | `FT_SORT` | _(skipped)_ | Sort/index field (not stored in struct) |
| `x` | `FT_NA` | _(skipped)_ | Not used, 4-byte padding |
| `X` | `FT_NA_BYTE` | _(skipped)_ | Not used, 1-byte padding |
| `l` | `FT_LOGIC` | _(assertion)_ | Boolean (triggers ASSERT if encountered) |

The format string length must exactly equal `fieldCount` from the DBC file header. `sizeof(T)` is validated against `GetFormatRecordSize(format)` at load time.

## SQL Overlay Mechanism

Every DBC store has a corresponding SQL table named `<name>_dbc` in the `db_world` database. The overlay works as follows:

1. **Binary DBC loads first** into memory via `DBCFileLoader`
2. **SQL overlay loads second** via `DBCDatabaseLoader::Load()` which executes `SELECT * FROM <table> ORDER BY ID DESC`
3. For each SQL row:
   - If the ID matches an existing DBC entry, the SQL data **completely replaces** the DBC entry
   - If the ID is new, the entry is **added** to the store
   - For string fields: if the SQL string is empty AND old DBC data exists, the DBC string is **preserved**
4. The index table is resized if SQL contains higher IDs than the DBC file

This allows server operators to modify game data without editing binary DBC files.

## SQL-Only Loading Pattern

Non-DBC SQL data follows a simpler pattern:

1. A `Load*()` function on a manager class executes `WorldDatabase.Query("SELECT ...")`
2. Results are iterated via `Field* fields = result->Fetch()`
3. Individual fields are read with `fields[N].Get<uint32>()`, `fields[N].Get<std::string>()`, etc.
4. Data is stored in `std::unordered_map<uint32, StructType>` or similar containers
5. Access is provided via `Get*()` methods

No common base class or generic storage template exists for SQL-only data. Each manager class implements its own loading logic.

## Global Database Accessors

```cpp
DatabaseWorkerPool<WorldDatabaseConnection>     WorldDatabase;     // db_world
DatabaseWorkerPool<CharacterDatabaseConnection>  CharacterDatabase; // db_characters
DatabaseWorkerPool<LoginDatabaseConnection>      LoginDatabase;     // db_auth
```

## Manager Singletons

| Singleton | Class | Header |
|-----------|-------|--------|
| `sObjectMgr` | `ObjectMgr` | `Globals/ObjectMgr.h` |
| `sSpellMgr` | `SpellMgr` | `Spells/SpellMgr.h` |
| `sPoolMgr` | `PoolMgr` | `Pools/PoolMgr.h` |
| `sGameEventMgr` | `GameEventMgr` | `Events/GameEventMgr.h` |
| `sConditionMgr` | `ConditionMgr` | `Conditions/ConditionMgr.h` |
| `sWaypointMgr` | `WaypointMgr` | `Movement/Waypoints/WaypointMgr.h` |
| `sAchievementMgr` | `AchievementGlobalMgr` | `Achievements/AchievementMgr.h` |
| `sLFGMgr` | `LFGMgr` | `DungeonFinding/LFGMgr.h` |
| `sDisableMgr` | `DisableMgr` | `Conditions/DisableMgr.h` |
| `sFormationMgr` | `FormationMgr` | `Entities/Creature/CreatureGroups.h` |
| `sCreatureTextMgr` | `CreatureTextMgr` | `Texts/CreatureTextMgr.h` |
| `sBattlegroundMgr` | `BattlegroundMgr` | `Battlegrounds/BattlegroundMgr.h` |
| `SmartAIMgr::instance()` | `SmartAIMgr` | `AI/SmartScripts/SmartScriptMgr.h` |
| `sServerMailMgr` | `ServerMailMgr` | `Mails/ServerMailMgr.h` |
| `sTransportMgr` | `TransportMgr` | `Maps/TransportMgr.h` |
| `sWardenCheckMgr` | `WardenCheckMgr` | `Warden/WardenCheckMgr.h` |
