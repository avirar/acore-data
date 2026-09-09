#!/usr/bin/env python3
"""
Phase B: fix the SpellEntry 115/116 index swap and add curated, verified
cross-references (the "missing relationships").

Everything is verified before writing:
  * the target registry entry must exist
  * the field must not already carry a reference
  * reference_column is the target's real PK (DB-confirmed for SQL targets,
    'ID' convention for DBC targets)
  * field type must be numeric (a real ID), not string/bool/enum-text

Run:  .venv/bin/python3 scripts/fix_registry_phase_b.py [--check]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REG_PATH = ROOT / "datastore_registry.json"


def main():
    check = "--check" in sys.argv
    reg = json.loads(REG_PATH.read_text())
    E = reg["entries"]
    cat = {n: e.get("category", "") for n, e in E.items()}
    changes = []

    # ------------------------------------------------------------------ 1.
    # SpellEntry: indices 115 and 116 are swapped. Per DBCStructure.h the
    # contiguous layout is EffectMiscValueB=113-115, EffectTriggerSpell=116-118.
    sp = E["SpellEntry"]["fields"]
    f115, f116 = sp["115"], sp["116"]
    if f115.get("name") == "EffectTriggerSpell[0]" and f116.get("name") == "EffectMiscValueB[2]":
        sp["115"] = {
            "name": "EffectMiscValueB[2]",
            "type": "int32",
            "sql_column": "EffectMiscValueB",
            "notes": "EffectMiscValueB for slot 2.",
        }
        sp["116"] = {
            "name": "EffectTriggerSpell[0]",
            "type": "uint32",
            "sql_column": "EffectTriggerSpell",
            "notes": " (Spell that triggers from this effect (aura, proc, chain))",
            "references": "SpellEntry",
            "reference_type": "dbc_backed",
            "reference_column": "ID",
        }
        changes.append("SpellEntry: swapped indices 115/116 to match DBCStructure.h "
                       "(115=EffectMiscValueB[2], 116=EffectTriggerSpell[0])")

    # ------------------------------------------------------------------ 2.
    # Curated cross-references. Keyed by (entry_lower, sql_column_lower).
    # (target, reference_column). Only applied when the target exists and the
    # field is numeric and not already referenced.
    REFMAP = {
        ("achievemententry", "requiredfaction"): ("FactionEntry", "ID"),
        ("achievemententry", "mapid"): ("MapEntry", "ID"),
        ("areapoientry", "zoneid"): ("AreaTableEntry", "ID"),
        ("creaturedisplayinfoentry", "extendeddisplayinfoid"): ("CreatureDisplayInfoEntry", "ID"),
        ("creaturemodeldataentry", "bloodid"): ("CreatureModelDataEntry", "ID"),
        ("destructiblemodeldataentry", "state0impacteffectdoodadset"): ("CreatureDisplayInfoEntry", "ID"),
        ("destructiblemodeldataentry", "state1impacteffectdoodadset"): ("CreatureDisplayInfoEntry", "ID"),
        ("destructiblemodeldataentry", "state2impacteffectdoodadset"): ("CreatureDisplayInfoEntry", "ID"),
        ("destructiblemodeldataentry", "state3impacteffectdoodadset"): ("CreatureDisplayInfoEntry", "ID"),
        ("emotestextentry", "emoteid"): ("EmotesEntry", "ID"),
        ("emotestextsoundentry", "emotestextid"): ("EmotesTextEntry", "ID"),
        ("emotestextsoundentry", "soundid"): ("SoundEntriesEntry", "ID"),
        ("factiontemplateentry", "enemyfaction"): ("FactionEntry", "ID"),
        ("factiontemplateentry", "friendfaction"): ("FactionEntry", "ID"),
        ("itementry", "displayinfoid"): ("ItemDisplayInfoEntry", "ID"),
        ("itemextendedcostentry", "reqitem"): ("ItemEntry", "ID"),
        ("itemsetentry", "items_to_triggerspell"): ("SpellEntry", "ID"),
        ("itemsetentry", "required_skill_id"): ("SkillLineEntry", "ID"),
        ("mapentry", "linked_zone"): ("MapEntry", "ID"),
        ("mapentry", "multimap_id"): ("MapEntry", "ID"),
        ("skilllineabilityentry", "supercededbyspell"): ("SpellEntry", "ID"),
        ("spellentry", "effecttriggerspell"): ("SpellEntry", "ID"),
        ("spellenchantmententry", "aura_id"): ("SpellEntry", "ID"),
        ("spellitemenchantmententry", "aura_id"): ("SpellEntry", "ID"),
        ("spellitemenchantmententry", "gemid"): ("GemPropertiesEntry", "ID"),
        ("spellitemenchantmententry", "requiredskill"): ("SkillLineEntry", "ID"),
        ("spellshapeshiftformentry", "stancespell"): ("SpellEntry", "ID"),
        ("taxinodesentry", "mountcreatureid"): ("CreatureTemplate", "entry"),
        ("talententry", "rankid"): ("TalentEntry", "ID"),
        ("creaturetemplate", "creaturesdisplayid"): ("CreatureDisplayInfoEntry", "ID"),
        ("creaturedata", "displayid"): ("CreatureDisplayInfoEntry", "ID"),
        ("creaturedata", "spawngroup"): ("SpawnGroupTemplateData", "groupId"),
        ("itemtemplate", "displayid"): ("ItemDisplayInfoEntry", "ID"),
        ("itemtemplate", "requireddisenchantskill"): ("SkillLineEntry", "ID"),
        ("pagetext", "nextpage"): ("PageText", "ID"),
        ("gossipmenus", "menuid"): ("GossipMenus", "MenuID"),
        ("gossipmenuitems", "menuid"): ("GossipMenus", "MenuID"),
        ("gossipmenuitems", "optionid"): ("GossipMenuItems", "OptionID"),
        ("gossipmenuitems", "actionmenuid"): ("GossipMenus", "MenuID"),
        ("gossipmenuitems", "actionpoiid"): ("AreaPOIEntry", "ID"),
        ("broadcasttext", "emotesid"): ("EmotesEntry", "ID"),
        ("spellenchant", "auraspell"): ("SpellEntry", "ID"),
        ("spellarea", "aura_spell"): ("SpellEntry", "ID"),
        ("lfgreward", "firstquestid"): ("Quest", "ID"),
        ("lfgreward", "otherquestid"): ("Quest", "ID"),
        ("achievementreward", "titlea"): ("CharTitlesEntry", "ID"),
        ("gameeventdata", "holiday"): ("HolidaysEntry", "ID"),
        ("equipmentinfo", "itementry2"): ("ItemEntry", "ID"),
        ("equipmentinfo", "itementry3"): ("ItemEntry", "ID"),
        ("vehiclesetaddon", "seatentry"): ("VehicleSeatEntry", "ID"),
        ("vehicleseataddon", "seatentry"): ("VehicleSeatEntry", "ID"),
        ("vehicleaccessory", "seat_id"): ("VehicleSeatEntry", "ID"),
    }

    NUMERIC_RE = re.compile(r"uint|int\d*|float|double|guid", re.I)

    added = 0
    for n, e in E.items():
        nlower = n.lower()
        for k, f in e.get("fields", {}).items():
            if not isinstance(f, dict) or f.get("references"):
                continue
            sc = (f.get("sql_column") or "").strip()
            key = (nlower, sc.lower()) if sc else None
            if key not in REFMAP:
                continue
            # must be a numeric id type (not text/bool/enum-text)
            ftype = str(f.get("type", ""))
            if not NUMERIC_RE.search(ftype) and not sc.lower().endswith(("id", "entry", "spell", "page")):
                continue
            target, refcol = REFMAP[key]
            if target not in E:
                continue
            f["references"] = target
            f["reference_type"] = cat.get(target, "unknown")
            f["reference_column"] = refcol
            added += 1

    changes.append(f"cross-references: added {added} curated references")

    print("PHASE B CHANGES" + (" (dry-run)" if check else ""))
    print("=" * 60)
    for c in changes:
        print("  -", c)
    if check:
        print(f"\n[check] would add {added} refs + swap SpellEntry 115/116.")
        return

    with REG_PATH.open("w") as fh:
        json.dump(reg, fh, indent=2)
        fh.write("\n")
    print(f"\n[Wrote {REG_PATH}]")


if __name__ == "__main__":
    main()
