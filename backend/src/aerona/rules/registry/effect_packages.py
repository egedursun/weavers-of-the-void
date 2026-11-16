from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.BODY


@dataclass(frozen=True)
class EffectPackageRules:
    bite_pct: int = rule(35, 0, 100, G, "Chance a bite from a bearer passes on a package carried by bite (%)")
    blood_pct: int = rule(20, 0, 100, G, "Chance a blood-cursed bearer's feeding passes the curse on (%)")
    contact_pct: int = rule(5, 0, 100, G, "Chance each epoch a package carried by contact passes to someone living beside the bearer (%)")
    birth_pct: int = rule(60, 0, 100, G, "Chance a child inherits a hereditary package from a parent (%)")
    medicine_pct: int = rule(30, 0, 100, G, "Chance each epoch a healer with enough medicine cures a package medicine can cure (%)")
    rite_pct: int = rule(25, 0, 100, G, "Chance each epoch a priest of the bearer's people cures a package a rite can cure (%)")
    technique_pct: int = rule(20, 0, 100, G, "Chance each epoch a known herbal technique cures a package a technique can cure (%)")
    wider_cure_pct: int = rule(
        20, 0, 100, G, "Chance each epoch a god, a healing power, a symbiont, a moved mind or an augment cures a package it can cure (%)"
    )
    time_epochs: int = rule(6, 1, 100, G, "Epochs in its last stage after which a package that time can cure fades")
    sunlight_harm: int = rule(15, 0, 100, G, "Harm the sun deals each epoch to a bearer who burns under it")
    rampage_pct: int = rule(40, 0, 100, G, "Chance each epoch a moon-changed bearer harms someone near them under a bright first moon (%)")
    rampage_harm: int = rule(30, 0, 200, G, "Harm a moon-changed rampage deals")
    feed_harm: int = rule(15, 0, 200, G, "Harm a blood-cursed feeding deals")
    need_pressure: int = rule(25, 0, 100, G, "Need a package stage drains each epoch from the needs it adds")
    trauma_magnitude: int = rule(70, 0, 100, G, "Strength of a memory that can leave a trauma")
    trauma_willpower: int = rule(40, 0, 100, G, "Willpower below which a heavy memory leaves a trauma")
    fear_magnitude: int = rule(40, 0, 100, G, "Strength of the fear a blessed bearer holds toward the giver")
    desecration_pct: int = rule(50, 0, 100, G, "Chance desecrating a Hunt god's shrine earns the beast curse (%)")
    blood_curse_pct: int = rule(40, 0, 100, G, "Chance a Blood god's curse on a mortal is the blood curse (%)")
    backlash_blood_pct: int = rule(15, 0, 100, G, "Chance a blood rite gone wrong leaves its caster blood-cursed (%)")
