from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class CreatureAnatomyRules:
    extra_limb_pct: int = rule(8, 0, 100, G, "Chance a generated body grows a pair of limbs beyond its plan (%)")
    extra_head_pct: int = rule(4, 0, 100, G, "Chance a generated body grows a second head (%)")
    wings_pct: int = rule(5, 0, 100, G, "Chance a generated body that cannot fly grows wings (%)")
    tail_pct: int = rule(45, 0, 100, G, "Chance a generated body has a tail (%)")
    breath_pct: int = rule(6, 0, 100, G, "Chance an ordinary kind is given a breath its traits do not already give (%)")
    bite_pct: int = rule(4, 0, 100, G, "Chance an ordinary kind's bite carries an affliction (%)")
    hate_pct: int = rule(15, 0, 100, G, "Chance a generated creature hates something that keeps it away (%)")
    monster_limb_pct: int = rule(35, 0, 100, G, "Chance a monster of a kind of its own grows limbs beyond its plan (%)")
    monster_head_pct: int = rule(25, 0, 100, G, "Chance a monster of a kind of its own grows more heads (%)")
    monster_wings_pct: int = rule(25, 0, 100, G, "Chance a monster of a kind of its own grows wings (%)")
    exotic_tissue_pct: int = rule(60, 0, 100, G, "Chance a monster of a kind of its own is made of an exotic tissue (%)")
    monster_breath_pct: int = rule(55, 0, 100, G, "Chance a monster of a kind of its own has a breath attack (%)")
    monster_bite_pct: int = rule(30, 0, 100, G, "Chance a monster's bite carries an affliction (%)")
    gaze_pct: int = rule(25, 0, 100, G, "Chance a monster of a kind of its own has a gaze attack (%)")
    hoard_pct: int = rule(70, 0, 100, G, "Chance a monster hoards one material above all others (%)")
    abductor_pct: int = rule(15, 0, 100, G, "Chance a monster of a kind of its own carries people off rather than killing them (%)")
    awakening_pct: int = rule(50, 0, 100, G, "Chance a monster of a kind of its own wakes only to a trigger (%)")
    breath_harm_pct: int = rule(30, 0, 300, G, "Harm a breath attack adds to a creature's raids (%)")
    head_harm_pct: int = rule(20, 0, 300, G, "Harm each head beyond the first adds to a creature's raids (%)")
    limb_harm_pct: int = rule(5, 0, 100, G, "Harm each limb beyond its plan adds to a creature's raids (%)")
    skin_damage_pct: int = rule(100, 0, 300, G, "Weight of the armour of a creature's skin against the harm of each wound it takes (%)")
    armour_power_pct: int = rule(50, 0, 300, G, "Weight of the armour of a creature's skin in its fights with heroes (%)")
    gaze_terror: int = rule(10, 0, 100, G, "Terror a gaze attack adds to a creature each time it raids")
    terror_stress: int = rule(8, 0, 100, G, "Stress a terrifying gaze lays on each mortal of a town it raids")
    sleep_raid_pct: int = rule(40, 0, 300, G, "Harm a raid does beyond its due while a sleeping gaze holds the town's watch (%)")
    petrify_severity: int = rule(3, 1, 5, G, "Severity of the limb a petrifying gaze turns to stone")
    hoard_take: int = rule(3, 0, 1000, G, "Units of its favoured material a hoarding creature carries off from a raid")
    noise_population: int = rule(5000, 0, 10000000, G, "Population at which a town is loud enough to keep off a creature that hates noise")


@dataclass(frozen=True)
class MonstersRules:
    awaken_depth_pct: int = rule(50, 0, 100, G, "How deep a mine must be dug, as a share of its seam, to wake a creature that sleeps beneath its land (%)")
    emerge_depth_pct: int = rule(80, 0, 100, G, "How deep a mine must be dug before something of its own kind may climb out of the deep (%)")
    emerge_pct: int = rule(3, 0, 100, G, "Chance each epoch something climbs out of a mine dug that deep (%)")
    emerge_hp: int = rule(400, 1, 100000, G, "Vigour of a creature that climbs out of the deep")
    emerge_danger: int = rule(70, 0, 100, G, "Danger and strength of a creature that climbs out of the deep")
    emerge_power: int = rule(6, 1, 10, G, "Power of a creature that climbs out of the deep")
    emerge_cap: int = rule(1, 0, 100, G, "Most creatures that climb out of the deep across the cosmos in an epoch")
    desecration_epochs: int = rule(1, 0, 50, G, "Epochs a desecration in its land stays fresh enough to wake a creature")
    abduct_pct: int = rule(25, 0, 100, G, "Chance each epoch a waking abductor carries someone off from a town in its reach (%)")
    necro_tower_pct: int = rule(20, 0, 100, G, "Chance each epoch a mortal who knows a rite of death raises a tower (%)")
    necro_raise_pct: int = rule(25, 0, 100, G, "Chance each epoch a necromancer with a tower raises a host of the dead (%)")
    necro_undead_per_power: int = rule(40, 0, 10000, G, "Dead raised per point of power of the necromancer's strongest rite of death")
    necro_siege_pct: int = rule(20, 0, 100, G, "Chance each epoch a necromancer's host lays siege to the nearest town (%)")
    necro_cap: int = rule(2, 0, 100, G, "Most necromancers who act across the cosmos in an epoch")
    void_roam_pct: int = rule(30, 0, 100, G, "Chance each epoch a free creature of the void crosses a road between worlds (%)")
    void_route_danger: int = rule(10, 0, 100, G, "Danger a creature of the void adds to the road between worlds it crosses")
    void_glass_trophy: int = rule(3, 0, 1000, G, "Units of void glass a slain creature of the void yields its slayer")
