#!/usr/bin/env python3
"""Patch remaining polymorphic annotations for item_template and Spell DBC.

Task 3 (item_template): Add class/subclass relevance notes to missing fields.
Task 4 (SpellEntry): Add comprehensive Effect* polymorphic annotations.
"""

import json
import sys

def main():
    with open("datastore_registry.json") as f:
        reg = json.load(f)

    # === Task 3: ItemTemplate - fix fields missing notes ===
    it_fields = reg["entries"]["ItemTemplate"]["fields"]

    task3_patches = {
        "stat_type1..10": (
            "Only relevant for class=2(Weapon) and class=4(Armor). Each entry has stat_type(ItemModType: 1=Strength,2=Agi,3=Sta,4=Int,5=Spi,6=Stam,7=ArmorPct,8=ResH,9=ResF,10=ResS,11=ResN,12=ResA) and stat_value."
        ),
        "dmg_min1..2, dmg_max1..2, dmg_type1..2": (
            "Only relevant for class=2(Weapon). Weapon damage range. Min/Max can be 0 for some weapon types. Damage type references SpellSchool enum (1=Holy,2=Fire,3=Nature,4=Frost,5=Shadow,6=Physical)."
        ),
        "socketColor_1..3": (
            "Only relevant for class=2(Weapon) and class=4(Armor). References SocketColors.dbc. 0=None,1=Meta(orange),2=Red(yellow),3=Blue(black),4=Yellow(prismatic)."
        ),
        "Armor": (
            "Only relevant for class=4(Armor). Armor rating value."
        ),
    }

    task3_count = 0
    for name, note in task3_patches.items():
        if name in it_fields:
            old = it_fields[name].get("notes", "")
            if not old or old.startswith("-"):
                it_fields[name]["notes"] = note
                task3_count += 1
                print(f"  [Task3] Patched ItemTemplate.{name}")

    # === Task 4: SpellEntry - Effect polymorphic annotations ===
    se_fields = reg["entries"]["SpellEntry"]["fields"]

    # Map of field index -> note content
    task4_patches = {
        # === Effect enum (SPELL_EFFECT) ===
        "71": "Spell effect type for slot 0. Enum SpellEffect (164 values). Determines meaning of all Effect* fields in this slot. Common: 2=SCHOOL_DAMAGE, 6=APPLY_AURA, 15=ENVIRONMENTAL_DMG, 23=DRAIN, 24=LEECH, 28=SUMMON, 34=SILENCE, 36=LEARN_SPELL, 38=TRIGGER_SPELL, 51=OPEN_DOOR_LOCK_SUMMON, 70=SKILL, 76=SUMMON_GAMEOBJECT, 115=DUMMY.",
        "72": "Same as Effect[0] for slot 1 (second effect). A spell can stack multiple effects.",
        "73": "Same as Effect[0] for slot 2 (third effect).",

        # === EffectDieSides ===
        "74": "Dice roll amount for slot 0. Added to EffectBasePoints. Used for ranged/melee damage variance, some DoTs.",
        "75": "EffectDieSides for slot 1.",
        "76": "EffectDieSides for slot 2.",

        # === EffectBasePoints ===
        "80": "Base value for slot 0. Meaning depends on Effect[0]: SCHOOL_DAMAGE/APPLY_AURA=amount, SUMMON=entry of summoned entity, LEARN_SPELL=spellID, DUMMY=special value used by script. Negative = heal/absorb.",
        "81": "EffectBasePoints for slot 1.",
        "82": "EffectBasePoints for slot 2.",

        # === EffectMechanic ===
        "83": "SpellMechanic enum for slot 0 (9 values). Only if Effect[0]=APPLY_AURA: 1=Charge,2=ClearCD,3=Shield,4=Sprintf,5=Stealth,6=SkilleDodge,7=Parry,8=Block,9=Offhand. NULL(0)=no mechanic.",
        "84": "EffectMechanic for slot 1.",
        "85": "EffectMechanic for slot 2.",

        # === EffectImplicitTargetA/B ===
        "86": "Targeting method A for slot 0. Enum TargetedPosition/FindTarget (37 values). Common: 0=custom code, 1=self, 2=destination on player, 3=current destination, 6=CONE_hostile, 8=AREA_hostile, 12=AOE_self, 15=CASTER_DEST_location. See Targets.h in C++ source.",
        "87": "EffectImplicitTargetA for slot 1.",
        "88": "EffectImplicitTargetA for slot 2.",
        "89": "Secondary targeting B for slot 0. Used when effect has dual targets (e.g., chain, bounce). 0=None.",
        "90": "EffectImplicitTargetB for slot 1.",
        "91": "EffectImplicitTargetB for slot 2.",

        # === EffectRadiusIndex ===
        "92": "Area radius index for slot 0. References SpellRadius.dbc. 0=ray(100 units), 30=15m, 31=25m. Used by area/circle effects (TARGET_AREA, TARGET_CIRCLE).",
        "93": "EffectRadiusIndex for slot 1.",
        "94": "EffectRadiusIndex for slot 2.",

        # === EffectApplyAuraName ===
        "95": "Only meaningful when Effect[0]=6(APPLY_AURA). Enum SpellAura (317 values). Determines what aura effect is applied. Further reinterprets EffectMiscValue. Common: 1=MOD_DAMAGE, 4=DOT, 5=PERSISTENT_PROC, 8=OOC_REGEN, 11=MOD_RESISTANCE, 20=CASTING_ID, 39=CONTROL_VEHICLE, 56=TRANSPORT, 77=SUSPEND_POWER_REGENERATION, 100=MOD_RANGED_DAMAGE_DONE_PCT. See SpellAuraDefines.h.",
        "96": "EffectApplyAuraName for slot 1 (same semantics as slot 0).",
        "97": "EffectApplyAuraName for slot 2 (same semantics as slot 0).",

        # === EffectAmplitude ===
        "98": "Wave amplitude for slot 0. Used by periodic damage over area effects with sine-wave pattern.",
        "99": "EffectAmplitude for slot 1.",
        "100": "EffectAmplitude for slot 2.",

        # === EffectValueMultiplier ===
        "101": "Formula multiplier for slot 0. Applied to effect value calculation. Used by some damage/healing spells.",
        "102": "EffectValueMultiplier for slot 1.",
        "103": "EffectValueMultiplier for slot 2.",

        # === EffectChainTarget ===
        "104": "Max chain targets for slot 0. If >0 spell chains to this many nearby eligible units from primary target.",
        "105": "EffectChainTarget for slot 1.",
        "106": "EffectChainTarget for slot 2.",

        # === EffectItemType ===
        "107": "ItemClass filter for slot 0. References ItemClass enum (17 classes). Used by effects requiring specific item type equip/use.",
        "108": "EffectItemType for slot 1.",
        "109": "EffectItemType for slot 2.",

        # === EffectMiscValue ===
        "110": "Polymorphic value for slot 0. Meaning depends on Effect[0] type AND EffectApplyAuraName[0] if Effect=APPLY_AURA. Common: SUMMON=creature entry, LEARN_SPELL=spellID, APPLY_AURA+DOT=spellID, APPLY_AURA+TRANSFORM=creature model entry, SCHOOL=school mask (1=Holy..6=Physical).",
        "111": "EffectMiscValue for slot 1 (same polymorphic semantics as slot 0).",
        "112": "EffectMiscValue for slot 2 (same polymorphic semantics as slot 0).",

        # === EffectMiscValueB ===
        "113": "Secondary polymorphic value for slot 0. Less commonly used. Meaning depends on Effect+Aura combo.",
        "114": "EffectMiscValueB for slot 1.",

        # === EffectTriggerSpell ===
        "115": "Spell ID triggered by slot 0 effect. Relevant for TRIGGER_SPELL(38), PROC/PROC_ON_M SpellID, LEARN_SPELL(36) target spell.",
        "117": "EffectTriggerSpell for slot 1.",
        "118": "EffectTriggerSpell for slot 2.",

        # === EffectPointsPerComboPoint ===
        "119": "Value per combo point for slot 0. Used by Rogue combo-finishing moves (Eviscerate, etc.).",
        "120": "EffectPointsPerComboPoint for slot 1.",
        "121": "EffectPointsPerComboPoint for slot 2.",

        # === EffectSpellClassMask ===
        "122": "Spell class filter for slot 0. flag96 (96 bits, 3 masks of 32). Only effects targeting spells of these classes will trigger.",
        "123": "EffectSpellClassMask for slot 1.",
        "124": "EffectSpellClassMask for slot 2.",

        # === EffectRealPointsPerLevel ===
        "77": "Per-level scaling (float) for slot 0. Combined with EffectBasePoints to compute final value: total = base + real*level.",
        "78": "EffectRealPointsPerLevel for slot 1.",
        "79": "EffectRealPointsPerLevel for slot 2.",

        # === EffectChainTarget (duplicate idx 116 fix) ===
        "116": "Duplicate of EffectTriggerSpell[0] in registry. Likely EffectMiscValueB[2] mislabeled.",
    }

    task4_count = 0
    for idx, note in task4_patches.items():
        if idx in se_fields:
            old = se_fields[idx].get("notes", "")
            if not old or old.strip() == "-":
                se_fields[idx]["notes"] = note
                task4_count += 1
                print(f"  [Task4] Patched SpellEntry.{se_fields[idx]['name']} (idx={idx})")

    # Save
    with open("datastore_registry.json", "w") as f:
        json.dump(reg, f, indent=2)

    print(f"\nDone: Task3={task3_count} fields patched, Task4={task4_count} fields patched")
    return 0

if __name__ == "__main__":
    sys.exit(main())
