# AGENTS.md — working notes for agents editing acore-data

## What this repo is

An MCP server (JSON-RPC over stdio) that wraps an AzerothCore (WotLK 3.3.5)
data universe for LLM agents: DBC binary files, the C++ struct definitions
(`DBCfmt.h` / `DBCStructure.h`), and live SQL tables (`acore_world`,
`acore_characters`, `acore_auth`, `acore_playerbots`). The registry
(`datastore_registry.json`) is the cross-reference: every datastore carries
`c_struct`, `dbc_file`, `sql_table`, `store_variable` and per-field
`sql_column` mappings, so an agent can enter from any angle (C field name,
DBC file, SQL table, store variable) and traverse to the others.

## Hard rules

- Run everything with `.venv/bin/python3` (has `pymysql`). The system
  `python3` has no `pymysql` — the server falls back to a `mysql` CLI
  subprocess (it now interpolates params and honors `MYSQL_PWD`, so it
  works, but it is slower and the test harness uses the venv).
- `DB_*` env vars auto-detect from
  `/root/azerothcore-wotlk/env/dist/etc/worldserver.conf` when unset.
- DBC path: `/root/azerothcore-wotlk/env/dist/bin/dbc`; format file
  (single source of format strings):
  `/root/azerothcore-wotlk/src/server/shared/DataStores/DBCfmt.h`.
- Never rewrite `datastore_registry.json` wholesale with re-sorted keys —
  editors must preserve structure; make surgical edits (see
  `scripts/update_*.py` conventions).

## Tool semantics (post rework, branch fix/mcp-ergonomics)

- `query` returns **flat `{name: value}` rows** by default. `id`/`row_index`
  lookups → one object (or a specific error if missing/filtered out);
  `filter`/unconstrained → list capped by `limit` (100). Locale arrays
  (`name[0..15]`) collapse to a scalar or, if multiple non-empty slots, a
  list of values.
- `annotate=true` restores the legacy per-field arrays (index/type/sql_column/
  source). `hints=true` adds `field_references`/`referenced_by`. `links=true`
  adds `metadata.links` (one-hop relation map, capped 25 rows × ~15 entries,
  built on `core.type_resolver.resolve_type_fields`).
- Unknown argument names and unknown `fields` are **hard errors with
  difflib suggestions** — do not reintroduce silent argument/field ignoring.
- Every response is one line of JSON-RPC; MCP-level `isError` is set on tool
  failures; `notifications/*` get no response; the client `protocolVersion`
  is echoed.
- DBC + SQL overlay merge (`_merge_dbc_sql`): overlay wins when present and
  applies the same field projection (`_project_overlay_fields` maps registry
  C names onto live slot-suffixed columns, e.g. `EffectTriggerSpell` →
  `EffectTriggerSpell_1`), compaction and single-record shaping. Errors
  report per source (`DBC Spell.dbc: ... | SQL overlay spell_dbc: ...`).

## Gotchas

- Live `*_dbc` overlay tables (`spell_dbc`, `map_dbc`, `item_dbc`…) use the
  original WotLK SQL column style (`EffectTriggerSpell_1`,
  `MapName_Lang_enUS`…), not the C++ field names. `map_dbc` and `item_dbc`
  are empty in the live DB; `spell_dbc` has a few thousand rows.
- The DBC set is a reduced WotLK extraction: Map id 571 = "Northrend",
  id 0 = "Eastern Kingdoms"; not every high spell/item id exists in DBC
  (ids may only live in the SQL overlay — e.g. spell 4051).
- **Registry audit** — `scripts/audit_registry.py` is the health gate. Run
  `.venv/bin/python3 scripts/audit_registry.py --db` (add `--json out.json`
  for machine output). Checks: dangling_refs, duplicate_identifiers (two
  fields with the identical full name), type_as_name, missing_data_source,
  dbc_index_drift (registry index past the DBC/format field_count),
  sql_column_drift (field's sql_column absent from the live table — full
  uncapped columns, array/family and dbc_backed sparse-overlay skipped,
  cross-DB tables resolved), and missing_cross_refs (heuristic FK gap).
  As of this branch all structural signals are 0 except ~3 legit `string`
  column names and ~300 low-confidence missing_cross_refs (PKs/enum ids/guids
  intentionally left un-annotated).
- The registry's `sql_column` values are aligned to the **live AzerothCore**
  schema, not vanilla WotLK. Several tables were restructured (e.g.
  `quest_template` `Level`→`QuestLevel`, `Details`→`QuestDescription`,
  `CompletedText`→`QuestCompletionLog`; `creature_template` uses
  `difficulty_entry_1`; `spell_target_position` `TargetX`→`PositionX`).
  Fields whose column was dropped in this build carry `sql_column: None`
  (kept as C++ members, not DB-projectable).
- Registry quirks are allowed but audited by `tests/test_regression.py`
  (`TestRegistryAudit`): duplicate real field-identifier names per entry are
  **not** allowed (the old Spell idx 115/116 swap is fixed — 115 =
  `EffectMiscValueB[2]`, 116 = `EffectTriggerSpell[0]`, per DBCStructure.h;
  see `test_spell_effect_indices_match_dbc_structure`).
- `core/formats.py` parses `DBCfmt.h` with a tolerant regex (const/constexpr
  variants, line-wrapped, string-concatenated literals) — 114 formats
  expected.
- Baseline vs. post-change output sizes:
  `python3 scripts/capture_output_sizes.py <dir>` and `--compare
  <before> <after>`; pre-rework capture lives in `/tmp/opencode/baseline`
  (146,882 bytes across 9 scenarios).

## Tests

- `tests/test_regression.py` — 21 tests, the rework's contract (shape,
  strictness, links, protocol, registry audit, format parser).
- `tests/test_integration.py` — 75 tests (live DB + DBC; each test spawns
  the server via subprocess and needs ~10 s).
- `tests/test_helpers.py` — 20 fast unit tests (no DB).
- No `npm`/build step; no lint config. Run all suites with:
  `.venv/bin/python3 -m pytest tests/ -q` (or the standalone runners).

## Change process

- Committed per logical area on feature branches with short imperative
  messages (`fix(query): …`, `feat(list+lookup): …`).
- After changing tool output: re-run `tests/test_regression.py` and capture
  a new `capture_output_sizes.py` run; compare against the baseline dir.
- After changing `datastore_registry.json`: run the audit gate
  `.venv/bin/python3 scripts/audit_registry.py --db` and confirm the
  structural signals stay 0. `scripts/fix_registry_phase_[a-f].py` are the
  one-off migrations that brought the registry to that state (dangling refs,
  type-as-name, missing data sources, SpellEntry 115/116 swap, curated
  cross-refs, sql_column drift, phantom DBC fields, type-as-name residue);
  re-running them is a no-op once applied.
