from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.BODY


@dataclass(frozen=True)
class StrikeRules:
    momentum_scale_pct: int = rule(100, 0, 500, G, "Momentum of a strike at full weapon mass and full skilled speed (%)")
    unarmed_mass: int = rule(25, 0, 100, G, "Mass behind a strike with no weapon, on the scale of solid density")
    speed_floor_pct: int = rule(50, 0, 100, G, "Speed of a strike from an unskilled hand (% of the most skilled)")
    blunt_force_pct: int = rule(100, 0, 300, G, "Blunt force per point of momentum, compared against impact yield (%)")
    deflect_keep_pct: int = rule(35, 0, 100, G, "Momentum a turned-aside edge still carries through as blunt force (%)")
    blunt_absorb_pct: int = rule(60, 0, 100, G, "Blunt force a layer soaks per point of its impact yield when it does not break (% per 100)")
    severity_momentum_pct: int = rule(100, 0, 300, G, "Wound severity a fully spent strike keeps (% of the severity its momentum would give)")
    fire_heat: int = rule(40, 0, 100, G, "Heat of ordinary flame, on the scale of melting points")
    magma_heat: int = rule(80, 0, 100, G, "Heat of magma and volcanic fire")
    dragon_heat: int = rule(90, 0, 100, G, "Heat of a great beast's fire")
    fire_conduct_pct: int = rule(100, 0, 300, G, "Burn a layer passes through per point of its heat conduction (% per 100)")
    melt_wear: int = rule(40, 0, 100, G, "Condition armour loses when fire reaches its melting point")
    shield_block_pct: int = rule(60, 0, 100, G, "Chance a shield takes a strike at full shield coverage (%)")
    limb_cover_pct: int = rule(60, 0, 100, G, "Share of the limbs a body armour or cloak covers (%)")
    divine_metallurgy: int = rule(5, 0, 10, G, "Metallurgy level whose armour a god's own body is reckoned to wear")
    shape_floor_pct: int = rule(50, 0, 100, G, "Armour piercing a unit's weapons keep when their material only matches the armour's (%)")
