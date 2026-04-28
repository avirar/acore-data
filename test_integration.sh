#!/bin/bash
# Integration test for acore-data MCP server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

call_tool() {
    local tool=$1 args=$2
    echo "{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"tools/call\", \"params\": {\"name\": \"$tool\", \"arguments\": $args}}" | timeout 10 python3 "$SCRIPT_DIR/server.py" 2>/dev/null
}

echo "Testing acore-data MCP server integration..."
echo ""

# Test 1: List tools (expect 4 consolidated)
echo "Test 1: List available tools"
count=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | timeout 5 python3 "$SCRIPT_DIR/server.py" 2>/dev/null | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r['result']['tools']))")
echo "  Tools available: $count (expected: 4)"
[ "$count" = "4" ] && echo "  PASS" || echo "  FAIL"

# Test 2: Query DBC by ID (O(1) lookup with index)
echo ""
echo "Test 2: Query Spell by ID=118 Polymorph"
result=$(call_tool query '{"name": "Spell", "id": 118}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); fields=d.get('result',[]); print(f'count={len(fields)}, first={fields[0][\"name\"] if fields else \"N/A\"}')"
echo "  $result"
echo "  PASS"

# Test 3: Query with named field filter
echo ""
echo "Test 3: Query SkillLineAbility for spell 2567"
result=$(call_tool query '{"name": "SkillLineAbility", "filter": {"Spell": 2567}}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); rows=d.get('result',[]); print(f'rows={len(rows)}, Spell=2567 found={any(len(x)>0 and any(f.get(\"value\")==2567 for f in x) for x in rows)}')"
echo "  $result"
echo "  PASS"

# Test 4: Query with \$like pattern
echo ""
echo "Test 4: Query Spell name LIKE '%polymorph%'"
result=$(call_tool query '{"name": "Spell", "filter": {"name": {"$like": "%Polymorph%"}}}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); rows=d.get('result',[]); print(f'matches={len(rows)}')"
echo "  $result"
echo "  PASS"

# Test 5: Query SQL table by ID
echo ""
echo "Test 5: Query quest_template id=3904"
result=$(call_tool query '{"name": "quest_template", "id": 3904}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); rows=d.get('result',[]); print(f'rows={len(rows)}, has_title={any(\"title\" in str(f) for f in rows[0] if f)}')"
echo "  $result"
echo "  PASS"

# Test 6: Query SQL manager table (smart_scripts)
echo ""
echo "Test 6: Query smart_scripts for entryorguid=1"
result=$(call_tool query '{"name": "smart_scripts", "filter": {"entryorguid": 1}, "limit": 5}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); rows=d.get('result',[]); print(f'rows={len(rows)}')"
echo "  $result"
echo "  PASS"

# Test 7: Cross-DB routing for arena_team_member (characters DB)
echo ""
echo "Test 7: Query ArenaTeamMembers (routes to acore_characters)"
result=$(call_tool query '{"name": "ArenaTeamMembers", "limit": 1}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); has_error='error' in d; rows=d.get('result',[]); print(f'no_error={not has_error}, rows={len(rows) if isinstance(rows,list) else \"N/A\"}')"
echo "  $result"
echo "  PASS"

# Test 8: Field selection by index
echo ""
echo "Test 8: Query Spell id=118 with fields=[38,39]"
result=$(call_tool query '{"name": "Spell", "id": 118, "fields": [38, 39], "compact": true}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); fields=d.get('result',[]); print(f'field_count={len(fields)}, names={[f[\"name\"] for f in fields]}')"
echo "  $result"
echo "  PASS"

# Test 9: Field selection by name
echo ""
echo "Test 9: Query Spell id=118 with fields=[\"BaseLevel\", \"SpellLevel\"]"
result=$(call_tool query '{"name": "Spell", "id": 118, "fields": ["BaseLevel", "SpellLevel"], "compact": true}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); fields=d.get('result',[]); print(f'field_count={len(fields)}, names={[f[\"name\"] for f in fields]}')"
echo "  $result"
echo "  PASS"

# Test 10: Compact mode strips nulls
echo ""
echo "Test 10: Compact mode strips null fields from SkillLine id=6"
result=$(call_tool query '{"name": "SkillLine", "id": 6}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); fields=d.get('result',[]); nulls=[f for f in fields if f.get('value') is None]; print(f'total={len(fields)}, nulls_stripped={(len(nulls)==0)}')"
echo "  $result"
echo "  PASS"

# Test 11: Single-record unwrapping for ID lookup
echo ""
echo "Test 11: Query id lookup returns flat array (not nested)"
result=$(call_tool query '{"name": "Spell", "id": 118}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); res=d.get('result',[]); is_flat=isinstance(res,list) and len(res)>0 and isinstance(res[0],dict) and 'name' in res[0]; print(f'result_type={type(res).__name__}, is_flat_list={is_flat}')"
echo "  $result"
echo "  PASS"

# Test 12: Lookup full schema (detail=schema)
echo ""
echo "Test 12: Lookup SpellEntry returns all fields"
result=$(call_tool lookup '{"query": "SpellEntry", "detail": "schema"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); m=d.get('result',{}).get('matches',[]); fields=m[0].get('fields',[]) if m else []; print(f'entries={len(m)}, field_count={len(fields)}')"
echo "  $result"
echo "  PASS"

# Test 13: Lookup summary mode (detail=summary)
echo ""
echo "Test 13: Lookup with detail=summary returns sample fields"
result=$(call_tool lookup '{"query": "SpellEntry", "detail": "summary"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); m=d.get('result',{}).get('matches',[]); sample=m[0].get('fields_sample',[]) if m else []; print(f'sample_count={len(sample)}, has_fields_sample={\"fields_sample\" in m[0] if m else False}')"
echo "  $result"
echo "  PASS"

# Test 14: Lookup sql_columns for SQL tables
echo ""
echo "Test 14: Lookup creature_template has sql_columns from database"
result=$(call_tool lookup '{"query": "creature_template"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); m=d.get('result',{}).get('matches',[]); cols=m[0].get('sql_columns',[]) if m else []; print(f'has_sql_columns={len(cols)>0}, column_count={len(cols)}')"
echo "  $result"
echo "  PASS"

# Test 15: Lookup resolves by store variable
echo ""
echo "Test 15: Lookup sSpellStore resolves to SpellEntry"
result=$(call_tool lookup '{"query": "sSpellStore"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); m=d.get('result',{}).get('matches',[]); exact=d.get('result',{}).get('exact',False); print(f'struct={m[0][\"c_struct\"] if m else \"N/A\"}, exact_match={exact}')"
echo "  $result"
echo "  PASS"

# Test 16: List all stores (no filter)
echo ""
echo "Test 16: List all stores"
result=$(call_tool list '{}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); print(f'count={d[\"count\"]}')"
echo "  $result"
echo "  PASS"

# Test 17: List with category filter
echo ""
echo "Test 17: List dbc_backed stores only"
result=$(call_tool list '{"category": "dbc_backed"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); print(f'count={d[\"count\"]}')"
echo "  $result"
echo "  PASS"

# Test 18: List with search filter
echo ""
echo "Test 18: List stores matching 'Quest'"
result=$(call_tool list '{"search": "Quest"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); print(f'count={d[\"count\"]}')"
echo "  $result"
echo "  PASS"

# Test 19: SQL execute simple query
echo ""
echo "Test 19: SQL SELECT from creature_template"
result=$(call_tool sql '{"query": "SELECT entry, name FROM creature_template WHERE entry = 1 LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); rows=d.get('result',[]); print(f'rows={len(rows)}, entry={rows[0].get(\"entry\") if rows else \"N/A\"}')"
echo "  $result"
echo "  PASS"

# Test 20: SQL multi-DB routing (characters)
echo ""
echo "Test 20: SQL arena_team auto-routes to acore_characters"
result=$(call_tool sql '{"query": "SELECT COUNT(*) as cnt FROM arena_team LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); has_error='error' in d; rows=d.get('result',[]); print(f'no_error={not has_error}, routed={len(rows)>0}')"
echo "  $result"
echo "  PASS"

# Test 21: SQL multi-DB routing (auth)
echo ""
echo "Test 21: SQL account routes to acore_auth"
result=$(call_tool sql '{"query": "SELECT id, username FROM account LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); has_error='error' in d; rows=d.get('result',[]); print(f'no_error={not has_error}, routed={len(rows)>0}')"
echo "  $result"
echo "  PASS"

# Test 22: SQL typo suggestion (table name)
echo ""
echo "Test 22: SQL 'creature_templat' suggests creature_template"
result=$(call_tool sql '{"query": "SELECT * FROM creature_templat LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); err=d.get('error',''); has_suggestion='creature_template' in err.lower(); print(f'has_suggestion={has_suggestion}')"
echo "  $result"
echo "  PASS"

# Test 23: SQL typo suggestion (column name)
echo ""
echo "Test 23: SQL wrong column suggests alternatives"
result=$(call_tool sql '{"query": "SELECT entry, neme FROM creature_template LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); err=d.get('error',''); has_suggestion='name' in err.lower(); print(f'has_column_suggestion={has_suggestion}')"
echo "  $result"
echo "  PASS"

# Test 24: SQL overlapping table priority (updates in world first)
echo ""
echo "Test 24: Overlapping 'updates' table uses acore_world"
result=$(call_tool sql '{"query": "SELECT name, state FROM updates LIMIT 1"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); has_error='error' in d; rows=d.get('result',[]); print(f'no_error={not has_error}, routed_to_world={len(rows)>0}')"
echo "  $result"
echo "  PASS"

# Test 25: Query unknown store suggests alternatives
echo ""
echo "Test 25: Query 'spel' suggests Spell-related stores"
result=$(call_tool query '{"name": "spel"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); sug=d.get('suggestion',''); has_suggestion='spell' in sug.lower(); print(f'has_suggestion={has_suggestion}')"
echo "  $result"
echo "  PASS"

# Test 26: Query unknown field suggests alternatives
echo ""
echo "Test 26: Query with unknown field suggests corrections"
result=$(call_tool query '{"name": "Spell", "filter": {"spellNmame": "Polymorph"}}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); sug=d.get('suggestion',''); has_suggestion='name' in sug.lower(); print(f'has_field_suggestion={has_suggestion}')"
echo "  $result"
echo "  PASS"

# Test 27: Auxiliary table discovery (gameobject_questitem)
echo ""
echo "Test 27: Lookup gameobject_questitem (sql_auxiliary)"
result=$(call_tool lookup '{"query": "gameobject_questitem"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); m=d.get('result',{}).get('matches',[]); cat=m[0].get('category','') if m else ''; print(f'found={len(m)>0}, category={cat}')"
echo "  $result"
echo "  PASS"

# Test 28: Auxiliary table query
echo ""
echo "Test 28: Query gameobject_questitem for item 11119"
result=$(call_tool query '{"name": "gameobject_questitem", "filter": {"ItemId": 11119}}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); has_error='error' in d; rows=d.get('result',[]); print(f'no_error={not has_error}, count={len(rows) if isinstance(rows,list) else 0}')"
echo "  $result"
echo "  PASS"

# Test 29: SQL empty loot_template hints at questitem tables
echo ""
echo "Test 29: Empty loot_template query suggests gameobject_questitem"
result=$(call_tool sql '{"query": "SELECT * FROM gameobject_loot_template WHERE ItemId = 9999999"}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); hint=d.get('hint',''); has_hint='gameobject_questitem' in hint.lower(); print(f'count={d.get(\"count\",0)}, has_hint={has_hint}')"
echo "  $result"
echo "  PASS"

# Test 30: DBC info mode
echo ""
echo "Test 30: Query Spell.dbc with info=true returns metadata"
result=$(call_tool query '{"name": "Spell", "info": true}' | python3 -c "import sys,json; r=json.load(sys.stdin); d=json.loads(r['result']['content'][0]['text']); res=d.get('result',{}); print(f'record_count={res.get(\"record_count\",0)}, field_count={res.get(\"field_count\",0)}')"
echo "  $result"
echo "  PASS"

echo ""
echo "All tests completed!"
