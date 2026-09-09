# Output-size report — flat-row / strict-error rework

Branch: `fix/mcp-ergonomics`
Method: `scripts/capture_output_sizes.py` measures the exact JSON text
delivered to the MCP client (`tools/call` → `text` field), 9 representative
scenarios, live DB + DBC.
- Pre-fix baseline: `/tmp/opencode/baseline` — **146,882 B total**
- Post-fix capture: `/tmp/opencode/after2` — **45,786 B total**

## Per-scenario

| scenario | before | after | delta |
|---|---:|---:|---:|
| lookup_spellentry_schema (183-field DBC schema) | 59,885 | 27,591 | **-54%** |
| list_dbc_backed (default limit) | 32,459 | 9,271 | **-71%** |
| query_spell_118 `Spell id=118` | 14,342 | 1,062 | **-93%** |
| query_map_filter_name `Map name=Eastern Kingdoms` | 13,600 | 307 | **-98%** |
| lookup_quests_summary `quest_template summary` | 10,031 | 3,351 | **-67%** |
| query_quest_murloc_fields (2 selected cols) | 7,100 | 416 | **-94%** |
| query_quest_46_links `quest 46 links=true` | 5,031 | 2,276 | **-55%*** |
| query_creature_100 `creature_template id=100` | 4,211 | 1,297 | **-69%** |
| query_bad_store (error) | 223 | 215 | -4% |
| **TOTAL (9 scenarios)** | **146,882** | **45,786** | **-69%** |

\* links=true is an opt-in feature that didn't exist before; its output
  replaces the previously-emitted spammy `referenced_by` metadata.

## What changed

- Flat `{name: value}` rows; locale arrays collapse to a scalar (list when
  multiple non-empty). `annotate=true` restores the legacy per-field shape.
- `id`/`row_index` → one object (or a specific error); `filter` → list
  (limit 100); identity field (index 0) always survives `compact`.
- `list` defaults to 50 entries + `metadata.total`; dropped format strings.
- `lookup` drops `notes:"-"` / false `is_primary_key` noise; live
  `sql_columns` only for SQL-native tables, as flat `name:type [PK]`.
- `hints` / `links` opt-in metadata (default off).
- Errors are per-source (`DBC … | SQL overlay …`) with difflib suggestions
  for unknown args/fields; unknown ids report the id.
- Transport: one-line JSON-RPC, no responses to `notifications/*`,
  client `protocolVersion` echoed, MCP `isError` set on failures.

## Reproducing

```bash
.venv/bin/python3 scripts/capture_output_sizes.py /tmp/opencode/before   # at f437de9
.venv/bin/python3 scripts/capture_output_sizes.py /tmp/opencode/after2   # at branch tip
.venv/bin/python3 scripts/capture_output_sizes.py --compare \
    /tmp/opencode/baseline /tmp/opencode/after2
```
