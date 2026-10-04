# Scripting against acore-data

For bulk work (census, coverage, joins over thousands of rows) use the Python
facade instead of MCP round-trips or hand-rolled DBC parsers.

**Always run scripts with the repo venv** (has `pymysql`, so SQL uses the fast
connection path instead of the `mysql` CLI fallback):

```bash
.venv/bin/python3 my_census.py
```

## DBC stores

```python
from core.api import open_store, resolve

spells = open_store("Spell")            # any resolvable name: struct, DBC file, SQL table, store var
print(spells.record_count)              # 49839
print(spells.field_names()["Effect[0]"])  # 71

row = spells.by_id(16378)               # flat {field_name: value}, zero/null dropped
for row in spells.find_iter():          # exact-match iteration, or .find(limit=N, Field=value)
    ...
```

`Store` rows match the MCP `query` tool's flat shape; `compact=False` keeps
null/zero fields.

## SQL

```python
from core.api import sql

rows = sql("SELECT ID, LogTitle FROM quest_template WHERE RequiredItemId1 = %s", params=(12472,))
rows = sql("SELECT * FROM ai_playerbot_texts WHERE id BETWEEN %s AND %s", db="acore_playerbots",
           params=(1900, 2000))
```

`db` defaults to smart routing by table name (world/characters/auth/playerbots).

## Cross-references (the usual trap)

Datastore semantics often differ from field names. Two rules of thumb:

1. Check the annotation before trusting a field:
   `open_store("Talent").entry["fields"]["4"]["references"]`.
2. Ask `refs` instead of guessing: it reverse-scans annotated SQL **and DBC**
   fields.

```
refs(name="Spell", id=12281)
  -> SkillLineAbilityEntry Spell=12281, TalentEntry RankID[0]=12281 (talent 123)
```

Known annotation fixes live in `generators/patch_known_refs.py` (e.g.
`TalentEntry.RankID[]` are rank *spell* ids; `ItemSetEntry.spells[]` are spell
ids while `items_to_triggerspell[]` are thresholds). Re-run it after any
registry regeneration that reintroduces the old heuristic, then
`generators/generate_referenced_by.py`.
