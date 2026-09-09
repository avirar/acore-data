#!/usr/bin/env python3
"""
Phase C: fix sql_column drift so every registry field maps to a REAL column
in the live AzerothCore DB (or None when the column was removed).

Driven by scripts/_drift_triage.json (REAL_MISMATCH, 144 fields). For each
drifted (entry, field_key, old_sql_column) we apply a decision keyed by
(entry, old_sql_column):
  RENAME -> new live column name (asserted to exist in the live table)
  None   -> the column was removed / is runtime-only
  LEAVE  -> expression-based projections (CreatureMovementData COALESCE/cmo.*)

Self-checks: every triage item must be covered by a decision; every RENAME
target must exist in the live table. Dry-run by default; --apply writes.
"""
import json, re, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
REG_PATH = ROOT / "datastore_registry.json"
reg = json.loads(REG_PATH.read_text())
E = reg["entries"]
TR = json.loads((ROOT / "scripts" / "_drift_triage.json").read_text())["REAL_MISMATCH"]

# decision[(entry, old_sql_column)] = new_sql_column or None
D = {}
def R(entry, old, new): D[(entry, old)] = new
def N(entry, old): D[(entry, old)] = None

# ---- RENAME: live AzerothCore column is a renamed variant of the old name ----
R("CreatureTemplate", "DifficultyEntry1", "difficulty_entry_1")
R("CreatureTemplate", "DifficultyEntry2", "difficulty_entry_2")
R("CreatureTemplate", "DifficultyEntry3", "difficulty_entry_3")
R("CreatureModelInfo", "bounding_radius", "BoundingRadius")
R("CreatureModelInfo", "combat_reach", "CombatReach")
R("CreatureModelInfo", "modelid_other_gender", "DisplayID_Other_Gender")
R("ItemTemplate", "HolyRes", "holy_res")
R("ItemTemplate", "FireRes", "fire_res")
R("ItemTemplate", "NatureRes", "nature_res")
R("ItemTemplate", "FrostRes", "frost_res")
R("ItemTemplate", "ShadowRes", "shadow_res")
R("ItemTemplate", "ArcaneRes", "arcane_res")
R("ItemTemplate", "flags_custom", "flagsCustom")
R("WeatherData", "script_name", "ScriptName")
R("EquipmentInfo", "ItemEntry1", "ItemID1")
R("EquipmentInfo", "ItemEntry2", "ItemID2")
R("EquipmentInfo", "ItemEntry3", "ItemID3")
R("QuestGreeting", "EmoteType", "GreetEmoteType")
R("QuestGreeting", "EmoteDelay", "GreetEmoteDelay")
R("PageText", "NextPage", "NextPageID")
R("AreaTrigger", "id", "entry")
R("DungeonProgressionRequirements", "levelMin", "min_level")
R("DungeonProgressionRequirements", "levelMax", "max_level")
R("DungeonProgressionRequirements", "reqItemLevel", "min_avg_item_level")
R("ReputationOnKillEntry", "RepFaction1", "RewOnKillRepFaction1")
R("ReputationOnKillEntry", "RepFaction2", "RewOnKillRepFaction2")
R("ReputationOnKillEntry", "ReputationMaxCap1", "MaxStanding1")
R("ReputationOnKillEntry", "ReputationMaxCap2", "MaxStanding2")
R("ReputationOnKillEntry", "RepValue1", "RewOnKillRepValue1")
R("ReputationOnKillEntry", "RepValue2", "RewOnKillRepValue2")
R("PlayerInfo", "mapId", "map")
R("PlayerInfo", "areaId", "zone")
R("SpellProcEntry", "Chance", "CustomChance")
R("SpellProcEntry", "ProcsPerMinute", "ppmRate")
R("SpellProcEntry", "SpellTypeMask", "procFlags")
R("SpellProcEntry", "SpellPhaseMask", "procPhase")
R("SpellTargetPosition", "TargetMapID", "MapID")
R("SpellTargetPosition", "TargetX", "PositionX")
R("SpellTargetPosition", "TargetY", "PositionY")
R("SpellTargetPosition", "TargetZ", "PositionZ")
R("SpellTargetPosition", "TargetOrientation", "Orientation")
R("Quest", "Level", "QuestLevel")
R("Quest", "Details", "QuestDescription")
R("Quest", "CompletedText", "QuestCompletionLog")
R("Quest", "RewardOrRequiredMoney", "RewardMoney")
R("Quest", "SuggestedPlayers", "SuggestedGroupNum")
R("Quest", "RequiredPlayerKillCount", "RequiredPlayerKills")
R("Quest", "NextQuestInChain", "RewardNextQuest")
R("Quest", "SrcItemId", "StartItem")
R("CreatureBaseStats", "basedamage0", "damage_base")
R("CreatureBaseStats", "basedamage1", "damage_exp1")
R("CreatureBaseStats", "basedamage2", "damage_exp2")
R("CreatureTextLocale", "Text_loc", "Text")
R("WardenCheck", "check_id", "id")
R("WardenCheck", "id_str", "str")
R("VehicleTemplateAccessory", "seat_entry", "seat_id")
R("DisableData", "flag1", "flags")
R("InstanceTemplate", "ScriptName", "script")
R("GameObjectAddon", "ParentRotation", "parent_rotation0..3")

# ---- NONE: column removed / runtime-only in this build ----
for old in ["Ground", "Swim", "Flight", "Rooted", "Chase", "Random",
            "InteractionPauseTimer", "CreatureDisplayID", "DisplayScale",
            "Probability"]:
    N("CreatureTemplate", old)
for old in ["spawnGroup", "id1", "id2", "id3", "displayid"]:
    N("CreatureData", old)
N("CreatureModelInfo", "is_trigger")
for old in ["ZoneOrSort", "Type", "MaxLevel", "RequiredClasses",
            "SourceSpellid", "PrevQuestId", "NextQuestId", "ExclusiveGroup",
            "BreadcrumbForQuestId", "RewardMailTemplateId", "RewardMailDelay",
            "RequiredSkillId", "RequiredSkillPoints", "RequiredMinRepFaction",
            "RequiredMinRepValue", "RequiredMaxRepFaction",
            "RequiredMaxRepValue", "StartItemCount", "RewardMailSenderEntry",
            "SpecialFlags", "Objectives", "OfferRewardText",
            "RequestItemsText", "EmoteOnIncomplete", "EmoteOnComplete"]:
    N("Quest", old)
for old in ["Idx1", "Idx2", "X", "Y"]:
    N("QuestPOI", old)
for old in ["quests", "items", "achievements"]:
    N("DungeonProgressionRequirements", old)
N("ScriptInfo", "guid")
for old in ["positionX/Y/Z", "displayId_m", "displayId_f", "item",
            "customSpells", "castSpells", "action", "skills", "levelInfo"]:
    N("PlayerInfo", old)
for old in ["HitMask", "AttributesMask", "DisableEffectsMask", "Charges"]:
    N("SpellProcEntry", old)
for old in ["guid", "casterGuid", "effectMask", "recalculateMask",
            "stackCount", "amount0", "amount1", "amount2", "base_amount0",
            "base_amount1", "base_amount2", "maxDuration", "remainTime",
            "remainCharges"]:
    N("PetAura", old)
N("WardenCheck", "action")

# ---- LEAVE: expression-based projections (no decision) ----
LEAVE = {("CreatureMovementData", old) for old in [
    "cmo.SpawnId",
    "COALESCE(cmo.Ground, ctm.Ground)", "COALESCE(cmo.Swim, ctm.Swim)",
    "COALESCE(cmo.Flight, ctm.Flight)", "COALESCE(cmo.Rooted, ctm.Rooted)",
    "COALESCE(cmo.Chase, ctm.Chase)", "COALESCE(cmo.Random, ctm.Random)",
    "COALESCE(cmo.InteractionPauseTimer, ctm.InteractionPauseTimer)"]}


def is_family(sc):
    s = sc.lower()
    return bool(re.search(r"\d\.\.\d", s) or re.search(r"\[\d", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from core.database import Database
    db = Database(); db._auto_detect_db_config(); db._check_db_connection()
    tbl_cache = {}
    def live_cols(table):
        if table not in tbl_cache:
            d = db._resolve_table_database(table, db.db_name) or db.db_name
            rows, _ = db._query_database(
                "SELECT COLUMN_NAME FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s", params=(d, table))
            tbl_cache[table] = {r["COLUMN_NAME"].lower() for r in rows}
        return tbl_cache[table]

    ren, none_, leave, bad_target, undecided = [], [], [], [], []
    for entry, fkey, old_sc, table in TR:
        if (entry, old_sc) in LEAVE:
            leave.append((entry, fkey, old_sc)); continue
        if (entry, old_sc) not in D:
            undecided.append((entry, fkey, old_sc, table)); continue
        new = D[(entry, old_sc)]
        f = E.get(entry, {}).get("fields", {}).get(fkey)
        if f is None:
            undecided.append((entry, fkey, old_sc, "field key missing")); continue
        if new is not None and not is_family(new):
            cols = live_cols(table)
            if new.lower() not in cols:
                bad_target.append((entry, fkey, old_sc, new, table)); continue
        f["sql_column"] = new
        (ren if new is not None else none_).append((entry, fkey, old_sc, new))

    print("=" * 62)
    print(f"PHASE C {'APPLIED' if a.apply else '(dry-run)'}")
    print("=" * 62)
    print(f"  triage REAL_MISMATCH  : {len(TR)}")
    print(f"  renames               : {len(ren)}")
    print(f"  set to None           : {len(none_)}")
    print(f"  left (expressions)    : {len(leave)}")
    print(f"  BAD rename targets    : {len(bad_target)}")
    for b in bad_target:
        print("     !!", b)
    print(f"  UNDECIDED (gaps)      : {len(undecided)}")
    for u in undecided:
        print("     ??", u)
    if a.apply and not bad_target and not undecided:
        REG_PATH.write_text(json.dumps(reg, indent=2) + "\n")
        print(f"\n[Wrote {REG_PATH}]")
    elif a.apply:
        print("\n[NOT written] unresolved issues above.")
    else:
        print("\n[check] re-run with --apply to write.")


if __name__ == "__main__":
    main()
