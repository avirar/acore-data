#!/usr/bin/env python3
"""Update datastore_registry.json for zero-field entries investigation.

Changes:
1. GossipText: Add 89 fields (ID + 8 options × 11 SQL columns)
2. SpellRequired: Add 2 fields (spell_id, req_spell)
3. CreatureCustomIDs: Remove — not a queryable datastore (config-loaded vector)
4. ScriptNameStore: Remove — runtime-indexed string list, no single source table
5. gm_survey: Convert to sql_auxiliary direct SQL table with schema fields
"""

import json


def build_gossip_text_fields():
    """Build flattened field mappings for GossipText (npc_text table).

    Struct: GossipText has Options[8], each GossipTextOption has:
      Text_0, Text_1, BroadcastTextID, Language, Probability, Emotes[3] (each Emote has _Delay, _Emote)

    SQL flat columns per option i (0-7):
      text{i}_0, text{i}_1, BroadcastTextID{i}, lang{i}, Probability{i},
      em{i}_0 (delay), em{i}_1 (emote), em{i}_2 (delay), em{i}_3 (emote), em{i}_4 (delay), em{i}_5 (emote)
    """
    fields = {}

    # Primary key
    fields["0"] = {
        "name": "ID",
        "type": "uint32",
        "sql_column": "ID",
        "notes": "Primary key"
    }

    option_idx = 1  # Starting field index after ID
    for i in range(8):
        prefix = f"Options[{i}]."
        fields[str(option_idx)] = {
            "name": f"{prefix}Text_0",
            "type": "std::string",
            "sql_column": f"text{i}_0",
            "notes": f"Gossip text option {i}, primary text"
        }
        option_idx += 1

        fields[str(option_idx)] = {
            "name": f"{prefix}Text_1",
            "type": "std::string",
            "sql_column": f"text{i}_1",
            "notes": f"Gossip text option {i}, alternative text"
        }
        option_idx += 1

        fields[str(option_idx)] = {
            "name": f"{prefix}BroadcastTextID",
            "type": "uint32",
            "sql_column": f"BroadcastTextID{i}",
            "notes": f"DBC BroadcastText ID override (0=use raw text), option {i}"
        }
        option_idx += 1

        fields[str(option_idx)] = {
            "name": f"{prefix}Language",
            "type": "uint8",
            "sql_column": f"lang{i}",
            "notes": f"Language enum, option {i}"
        }
        option_idx += 1

        fields[str(option_idx)] = {
            "name": f"{prefix}Probability",
            "type": "float",
            "sql_column": f"Probability{i}",
            "notes": f"Weighting for random selection (0.0-1.0), option {i}"
        }
        option_idx += 1

        # Emotes: each option has 3 emote slots, each with (_Delay, _Emote) = 6 columns
        for e in range(3):
            base = e * 2
            fields[str(option_idx)] = {
                "name": f"{prefix}Emotes[{e}]._Delay",
                "type": "uint16",
                "sql_column": f"em{i}_{base}",
                "notes": f"Emote delay (ms) for option {i}, slot {e}"
            }
            option_idx += 1

            fields[str(option_idx)] = {
                "name": f"{prefix}Emotes[{e}]._Emote",
                "type": "uint16",
                "sql_column": f"em{i}_{base+1}",
                "notes": f"Emote ID for option {i}, slot {e}"
            }
            option_idx += 1

    return fields


def build_spell_required_fields():
    """Build fields for SpellRequired (spell_required table).

    Stored as std::multimap<uint32, uint32>: spell_id -> req_spell
    SQL: SELECT spell_id, req_spell FROM spell_required
    """
    return {
        "0": {
            "name": "spell_id",
            "type": "uint32",
            "sql_column": "spell_id",
            "notes": "The spell being looked up"
        },
        "1": {
            "name": "req_spell",
            "type": "uint32",
            "sql_column": "req_spell",
            "notes": "Prerequisite spell required for spell_id"
        }
    }


def build_gm_survey_entry():
    """Rebuild gm_survey as sql_auxiliary direct SQL table entry.

    Table lives in db_characters, not loaded into memory (write-only).
    Schema from data/sql/base/db_characters/gm_survey.sql:
      surveyId INT AUTO_INCREMENT, guid INT, mainSurvey INT, comment LONGTEXT,
      createTime INT, maxMMR SMALLINT
    """
    return {
        "category": "sql_auxiliary",
        "sql_table": "gm_survey",
        "sql_database": "db_characters",
        "c_struct": "gm_survey",  # No actual C++ struct; table name as placeholder
        "fields": {
            "0": {
                "name": "surveyId",
                "type": "uint32",
                "sql_column": "surveyId",
                "notes": "Primary key, auto-increment"
            },
            "1": {
                "name": "guid",
                "type": "uint32",
                "sql_column": "guid",
                "notes": "Player GUID"
            },
            "2": {
                "name": "mainSurvey",
                "type": "uint32",
                "sql_column": "mainSurvey",
                "notes": "Reference to GMSurveyCurrentSurvey.dbc"
            },
            "3": {
                "name": "comment",
                "type": "std::string",
                "sql_column": "comment",
                "notes": "Free-form player comment"
            },
            "4": {
                "name": "createTime",
                "type": "uint32",
                "sql_column": "createTime",
                "notes": "UNIX timestamp of submission"
            },
            "5": {
                "name": "maxMMR",
                "type": "int16",
                "sql_column": "maxMMR",
                "notes": "Max MMR (present in schema, not populated by INSERT)"
            }
        }
    }


def main():
    with open("datastore_registry.json") as f:
        reg = json.load(f)

    entries = reg["entries"]

    # 1. Update GossipText with 89 fields
    gt_entry = entries.get("GossipText", {})
    gt_fields = build_gossip_text_fields()
    gt_entry["fields"] = gt_fields
    print(f"GossipText: added {len(gt_fields)} fields")

    # 2. Update SpellRequired with 2 fields
    sr_entry = entries.get("SpellRequired", {})
    sr_fields = build_spell_required_fields()
    sr_entry["fields"] = sr_fields
    print(f"SpellRequired: added {len(sr_fields)} fields")

    # 3. Remove CreatureCustomIDs (config-loaded vector, not queryable)
    if "CreatureCustomIDs" in entries:
        del entries["CreatureCustomIDs"]
        print("CreatureCustomIDs: removed (not a queryable datastore)")

    # 4. Remove ScriptNameStore (runtime-indexed string list)
    if "ScriptNameStore" in entries:
        del entries["ScriptNameStore"]
        print("ScriptNameStore: removed (runtime-indexed lookup, no single source table)")

    # 5. Convert gm_survey to sql_auxiliary with direct SQL schema
    new_gm = build_gm_survey_entry()
    entries["gm_survey"] = new_gm
    print(f"gm_survey: converted to sql_auxiliary with {len(new_gm['fields'])} fields")

    # Update total_entries meta
    reg["_meta"]["total_entries"] = len(entries)

    with open("datastore_registry.json", "w") as f:
        json.dump(reg, f, indent=2)

    print(f"\nRegistry updated: {reg['_meta']['total_entries']} total entries")


if __name__ == "__main__":
    main()
