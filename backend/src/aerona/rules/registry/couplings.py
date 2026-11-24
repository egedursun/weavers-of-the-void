from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

L = RuleGroup.LANGUAGE_AND_NAMES
B = RuleGroup.THE_BEYOND
E = RuleGroup.ENVIRONMENT
P = RuleGroup.POLITY
W = RuleGroup.WAR_AND_DIPLOMACY
M = RuleGroup.MATERIALS
S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class CouplingRules:
    component_block_pct: int = rule(
        20, 0, 100, B, "A body function below this share cannot give a rite the part that needs it (speech for spoken rites, hands for gestures)"
    )
    slow_casting_pct: int = rule(50, 1, 100, B, "Share of a rite's strength a caster of slow biology keeps, since its rites take long to cast")
    hive_casting_pct: int = rule(150, 100, 400, B, "Share of a rite's strength a hive gives a part of the mind it casts together")
    sign_share_pct: int = rule(8, 1, 100, L, "Share of a community deaf or mute at which it shares a signed language of its own")
    sign_hunting_grounds: int = rule(
        2, 1, 100, L, "Hunting grounds a community keeps at which its hunters share a silent signed language; sea grounds as many give sailors their speech"
    )
    sign_per_epoch: int = rule(3, 0, 10000, L, "Base of the most signed languages born in one epoch, grown by the number of peoples, towns and cults")
    sign_community_divisor: int = rule(10, 0, 100000, L, "Peoples, towns and cults per extra signed language born in one epoch (0: the cap stays at its base)")
    sociolect_salience: int = rule(60, 0, 100, L, "Salience of class identity at which a community's classes speak in their own ways")
    sociolect_start: int = rule(20, 0, 100, L, "Salience a new way of speaking starts with")
    sociolect_growth: int = rule(5, 0, 100, L, "Salience a way of speaking gains each epoch its group lasts")
    sociolect_levelling: int = rule(8, 0, 100, L, "Salience a way of speaking loses each epoch once printing levels speech")
    sociolect_identity_pct: int = rule(60, 0, 100, L, "Share of a way of speaking's salience that holds up its group's sense of itself")
    cant_secrecy_pct: int = rule(50, 0, 100, L, "Share of a secret cant's salience that keeps its group's secrets")


@dataclass(frozen=True)
class CarrionRules:
    rotting_disease: int = rule(6, 0, 100, E, "Disease load the rotting dead add to their region each epoch")
    rotting_scavenger: int = rule(100, 0, 200, E, "Draw the rotting dead hold for scavengers against rotting dead (%)")
    rotting_restless: int = rule(100, 0, 200, E, "Chance the rotting dead raise a restless spirit against rotting dead (%)")
    rotting_fossil: int = rule(0, 0, 100, E, "Chance in an epoch that the rotting dead of a region lay a bed of remains (%)")
    mummified_disease: int = rule(1, 0, 100, E, "Disease load the dried dead add to their region each epoch")
    mummified_scavenger: int = rule(40, 0, 200, E, "Draw the dried dead hold for scavengers against rotting dead (%)")
    mummified_restless: int = rule(120, 0, 200, E, "Chance the dried dead raise a restless spirit against rotting dead (%)")
    mummified_fossil: int = rule(10, 0, 100, E, "Chance in an epoch that the dried dead of a region lay a bed of remains (%)")
    frozen_disease: int = rule(0, 0, 100, E, "Disease load the frozen dead add to their region each epoch")
    frozen_scavenger: int = rule(20, 0, 200, E, "Draw the frozen dead hold for scavengers against rotting dead (%)")
    frozen_restless: int = rule(100, 0, 200, E, "Chance the frozen dead raise a restless spirit against rotting dead (%)")
    frozen_fossil: int = rule(20, 0, 100, E, "Chance in an epoch that the frozen dead of a region lay a bed of remains (%)")
    drifting_disease: int = rule(0, 0, 100, E, "Disease load the drifting dead add to their region each epoch")
    drifting_scavenger: int = rule(0, 0, 200, E, "Draw the drifting dead hold for scavengers against rotting dead (%)")
    drifting_restless: int = rule(50, 0, 200, E, "Chance the drifting dead raise a restless spirit against rotting dead (%)")
    drifting_fossil: int = rule(0, 0, 100, E, "Chance in an epoch that the drifting dead of a region lay a bed of remains (%)")
    floating_disease: int = rule(0, 0, 100, E, "Disease load the floating dead add to their region each epoch")
    floating_scavenger: int = rule(0, 0, 200, E, "Draw the floating dead hold for scavengers against rotting dead (%)")
    floating_restless: int = rule(150, 0, 200, E, "Chance the floating dead raise a restless spirit against rotting dead (%)")
    floating_fossil: int = rule(0, 0, 100, E, "Chance in an epoch that the floating dead of a region lay a bed of remains (%)")
    buried_disease: int = rule(1, 0, 100, E, "Disease load the buried dead add to their region each epoch")
    buried_scavenger: int = rule(10, 0, 200, E, "Draw the buried dead hold for scavengers against rotting dead (%)")
    buried_restless: int = rule(30, 0, 200, E, "Chance the buried dead raise a restless spirit against rotting dead (%)")
    buried_fossil: int = rule(30, 0, 100, E, "Chance in an epoch that the buried dead of a region lay a bed of remains (%)")
    burned_disease: int = rule(0, 0, 100, E, "Disease load the burned dead add to their region each epoch")
    burned_scavenger: int = rule(0, 0, 200, E, "Draw the burned dead hold for scavengers against rotting dead (%)")
    burned_restless: int = rule(10, 0, 200, E, "Chance the burned dead raise a restless spirit against rotting dead (%)")
    burned_fossil: int = rule(0, 0, 100, E, "Chance in an epoch that the burned dead of a region lay a bed of remains (%)")
    sunk_disease: int = rule(0, 0, 100, E, "Disease load the sunk dead add to their region each epoch")
    sunk_scavenger: int = rule(60, 0, 200, E, "Draw the sunk dead hold for scavengers against rotting dead (%)")
    sunk_restless: int = rule(40, 0, 200, E, "Chance the sunk dead raise a restless spirit against rotting dead (%)")
    sunk_fossil: int = rule(15, 0, 100, E, "Chance in an epoch that the sunk dead of a region lay a bed of remains (%)")
    mass_dead: int = rule(20, 1, 1000, E, "Dead in one region and one epoch, per thousand of its living people, that leave a carrion pulse (at least one)")
    scavenge_pct: int = rule(40, 0, 100, E, "Share of the carrion scavengers clear each epoch")
    scavenger_boom: int = rule(8, 0, 100, E, "Abundance scavengers gain in a region with carrion")
    vermin_disease: int = rule(6, 0, 100, E, "Disease load vermin feeding on carrion add to a region")
    predators_drawn: int = rule(4, 0, 100, E, "Danger predators drawn to carrion add to a region")
    haunting: int = rule(3, 0, 100, E, "Haunting the unburied dead add to a region each epoch")
    restless_dead: int = rule(
        50, 1, 1000, E, "Unburied dead in a region, per thousand of its living people, from which a restless spirit may rise (at least one)"
    )
    restless_chance: int = rule(20, 0, 100, E, "Chance a restless spirit rises from that many unburied dead")
    unburied_unrest_base: int = rule(40, 0, 100, E, "Unrest of the restless dead before their numbers count")
    unburied_unrest_per: int = rule(5, 0, 100, E, "Unrest the restless dead gain for each further mass of unburied dead in their region")
    unburied_calm: int = rule(15, 0, 100, E, "Unrest the restless dead lose each epoch once the dead of their region are buried or gone")
    burial: int = rule(150, 0, 100000, E, "Dead the living bury or burn in a region each epoch for every thousand of its living people")
    dry_moisture: int = rule(15, 0, 100, E, "Moisture of a region at or below which its unburied dead dry out instead of rotting")
    frozen_latitude: int = rule(70, 0, 90, E, "Latitude at or beyond which the unburied dead of a region freeze instead of rotting")
    floating_hazard: int = rule(5, 0, 100, E, "Danger the dead floating in a void or among broken rock add to a region each epoch")
    burial_cost: int = rule(2, 0, 100, E, "Prosperity a town spends each epoch burying the dead of its region")
    scavenged_disease: int = rule(1, 0, 100, E, "Disease load the dead eaten and scattered by scavengers add to their region each epoch")
    scavenged_scavenger: int = rule(30, 0, 100, E, "Abundance the scavengers of a region gain from the dead they eat and scatter")
    scavenged_restless: int = rule(2, 0, 100, E, "Chance in an epoch that the scattered dead of a region rise restless (%)")
    scavenged_fossil: int = rule(1, 0, 100, E, "Chance in an epoch that the scattered dead of a region lay a bed of remains (%)")
    scavenged_disease_cut_pct: int = rule(60, 0, 100, E, "Share of the disease load scavengers take away from a region where they scatter the dead (%)")


@dataclass(frozen=True)
class TeachingRules:
    unrest_error_pct: int = rule(50, 0, 100, B, "Share of a spirit's unrest that turns into errors in what it teaches")
    lore_intelligence: int = rule(60, 0, 100, B, "Intelligence a beast needs to keep the memory of an age")
    lore_lifespan: int = rule(300, 1, 100000, B, "Lifespan a beast needs to keep the memory of an age")
    memories_per_epoch: int = rule(3, 0, 100, B, "Happenings a lore-keeping beast remembers each epoch")
    beast_chance: int = rule(15, 0, 100, B, "Chance a lore-keeping beast teaches or sells to a community near it each epoch")
    beast_price: int = rule(5, 0, 100, B, "Wealth a lore-keeping beast asks for what it teaches when the learner can pay")
    spirit_chance: int = rule(10, 0, 100, B, "Chance a spirit teaches the living near it each epoch")
    veneration_bonus: int = rule(15, 0, 100, B, "Added chance a spirit teaches a people that venerates its ancestors")


@dataclass(frozen=True)
class OfficeMakingRules:
    cost: int = rule(400, 0, 1000000000, P, "Treasury a realm spends to make a new office for its rising elites")
    upkeep: int = rule(40, 0, 1000000000, P, "Treasury each such office costs every epoch")
    grievance: int = rule(30, 0, 100, P, "Memory of slight a holder keeps when the office made for them is abolished")
    fiscal_distress: int = rule(70, 0, 100, P, "Fiscal distress at which a realm abolishes the offices it made to save money")
    elite_pressure: int = rule(60, 0, 100, P, "Elite overproduction at which a realm makes offices to hold its aspirants")
    most: int = rule(6, 0, 10000, P, "Most offices a realm makes for its aspirants for every hundred thousand of its people (at least this many)")


@dataclass(frozen=True)
class FieldDiplomacyRules(Spanned):
    parley_chance: int = rule(30, 0, 100, W, "Chance commanders parley before a battle")
    parley_margin: int = rule(10, 0, 100, W, "Gap in charisma within which a parley ends in a truce instead of battle")
    truce_years: int = span(1, 0, 2500, W, "Years a truce agreed in the field lasts")
    surrender_honour: int = rule(30, -100, 100, W, "Honour the victor pledges with surrender terms")
    broken_memory: int = rule(40, 0, 100, W, "Memory of betrayal a broken field agreement leaves")
    exchange_chance: int = rule(25, 0, 100, W, "Chance two sides holding each other's captives exchange them and their dead")
    fraternise_rounds: int = rule(4, 1, 100, W, "Rounds of a siege after which the lines fraternise")
    fraternise_weariness: int = rule(5, 0, 100, W, "War weariness fraternising lines add to each side")
    terms_supplies: int = rule(60, 0, 100000, W, "Supplies left in a besieged town at or below which it takes the terms a commander offers")

    @property
    def truce_epochs(self) -> int:
        return self.epochs(self.truce_years)

    burial_battles: int = rule(2, 0, 50, W, "Battles a war must see before its sides may pause to bury their dead")
    burial_chance: int = rule(25, 0, 100, W, "Chance the sides of a bloody war pause to bury their dead in an epoch (%)")
    burial_ease: int = rule(3, 0, 50, W, "Weariness each side sheds when it may bury its dead in peace")


@dataclass(frozen=True)
class DeepSealRules:
    strength: int = rule(70, 1, 100, M, "Strength a new seal over the deep starts with")
    decay: int = rule(4, 0, 100, M, "Strength a seal of walls and gates loses each epoch")
    rite_decay: int = rule(2, 0, 100, M, "Strength a warding seal loses each epoch while it is kept")
    structure_prosperity: int = rule(40, 0, 100, M, "Prosperity a community needs to wall up a breach it opened")
    lapsed_rite: int = rule(10, 0, 100, M, "Strength a warding seal loses when no one keeps its rite any more")
    beast_danger: int = rule(70, 0, 100, M, "Danger of a creature below at which it tests a seal")
    beast_test: int = rule(6, 0, 100, M, "Strength a dangerous creature below wears from a seal each epoch")
    unseal_reserve_pct: int = rule(20, 0, 100, M, "Share of a mine's first reserve below which its miners dig through the seal to reach the deep")
    divine_decay: int = rule(0, 0, 50, M, "Strength a god's seal loses each epoch")
    power_decay: int = rule(3, 0, 50, M, "Strength a seal held by an innate power loses each epoch while its holder lives")
    living_decay: int = rule(1, 0, 50, M, "Strength a grown barrier loses each epoch")
    pact_decay: int = rule(0, 0, 50, M, "Strength a seal held by a pact loses each epoch while the oath holds")
    structure_strength: int = rule(70, 1, 100, M, "Strength a seal of walls and gates starts with")
    rite_strength: int = rule(70, 1, 100, M, "Strength a warding seal starts with")
    divine_strength: int = rule(90, 1, 100, M, "Strength a god's seal starts with")
    power_strength: int = rule(60, 1, 100, M, "Strength a seal held by an innate power starts with")
    living_strength: int = rule(50, 1, 100, M, "Strength a grown barrier starts with")
    pact_strength: int = rule(80, 1, 100, M, "Strength a seal held by a pact with those below starts with")
    made_decay: int = rule(1, 0, 50, M, "Strength a seal kept by a made mind loses each epoch while the mind keeps it")
    made_strength: int = rule(75, 1, 100, M, "Strength a seal kept by a made mind starts with")
    made_drift_max: int = rule(60, 0, 100, M, "Drift from its making at which a made mind no longer keeps the seal it holds")
    living_feed: int = rule(5, 0, 50, M, "Strength a grown barrier gains each epoch while its line is fed")
    pact_grievance: int = rule(30, 0, 100, M, "Grievance those below hold against the breaker of a pact seal")


@dataclass(frozen=True)
class ClosureRules:
    season_cut_pct: int = rule(40, 0, 100, S, "Share of a catch a closed season stops while enforced")
    protected_cut_pct: int = rule(60, 0, 100, S, "Share of a catch protected breeding waters stop while enforced")
    quota_cut_pct: int = rule(30, 0, 100, S, "Share of a catch a quota stops while enforced")
    gear_cut_pct: int = rule(25, 0, 100, S, "Share of a catch a ban on gear stops while enforced")
    poaching_pct: int = rule(40, 0, 100, S, "Share of a closure poachers evade where no warden watches")
    wardened_poaching_pct: int = rule(10, 0, 100, S, "Share of a closure poachers evade under wardens")
    margin: int = rule(15, 0, 100, S, "Stock above its point of collapse at which a ground worked in common is closed by custom")


@dataclass(frozen=True)
class FashionRules:
    start: int = rule(80, 0, 100, S, "Novelty a new art form or dish starts with")
    saturation: int = rule(60, 1, 100, S, "Share of the communities that take up a form at which it counts as everywhere (%)")
    recovery: int = rule(10, 0, 100, S, "Novelty a rare form regains each epoch")
    drain: int = rule(15, 0, 100, S, "Novelty a form everyone has loses each epoch")
    revival_floor: int = rule(50, 0, 100, S, "Novelty a form must climb back past to come back into fashion")
