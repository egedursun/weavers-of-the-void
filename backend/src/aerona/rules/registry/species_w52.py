from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

E = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class DietsRules:
    parasite_host_drain: int = rule(5, 0, 50, E, "Abundance a parasite at full numbers drains from the hosts of its land each epoch")
    parasite_host_need: int = rule(10, 0, 100, E, "Abundance of hosts a parasite needs in its land before it thins")
    decomposer_return_pct: int = rule(20, 0, 100, E, "Share of dead ground a decomposer at full numbers turns back into soil each epoch (%)")
    chemosynthetic_vent_need: int = rule(30, 0, 100, E, "Abundance a life of the chemicals loses each epoch away from vents, deep water or volcanic ground")
    energy_draw: int = rule(5, 0, 50, E, "Magic density feeders on power at full numbers draw from their land each epoch")


@dataclass(frozen=True)
class SpeciesFormsRules:
    colony_harvest_pct: int = rule(30, 0, 100, E, "Catch a ground on a nesting colony gains (%)")
    colony_collapse_pct: int = rule(20, 0, 100, E, "Abundance below which a nesting colony collapses")
    swarm_crop_harm: int = rule(15, 0, 100, E, "Harvest a swarm at full numbers strips from its land each epoch")
    swarm_move: int = rule(3, 0, 20, E, "Lands a swarm may move through in an epoch")


@dataclass(frozen=True)
class BiochemistryRules:
    carbon_methane_heat_max: int = rule(10, 0, 100, E, "Temperature above which life of carbon and methane dies back")
    plasma_heat_min: int = rule(80, 0, 100, E, "Temperature below which life of plasma dies back")
    out_of_band_loss: int = rule(10, 0, 100, E, "Abundance life loses each epoch in a land outside its warmth")


@dataclass(frozen=True)
class DomesticationDepthRules:
    commensal_chance_pct: int = rule(5, 0, 100, E, "Chance a wild kind living by a settlement on its waste or pests begins to live beside its people (%)")
    commensal_tame_gain: int = rule(20, 0, 100, E, "How much faster a kind that lives beside people is tamed (%)")
    feral_chance_pct: int = rule(10, 0, 100, E, "Chance a kept kind whose keepers are gone runs wild in an epoch (%)")
    feral_graze_harm: int = rule(10, 0, 100, E, "Overgrazing a feral herd at full numbers leaves on its land each epoch")
    feral_retake_gain: int = rule(30, 0, 100, E, "How much faster a feral kind is taken back (%)")


@dataclass(frozen=True)
class SpeciesRolesRules:
    hunting_catch_pct: int = rule(30, 0, 200, E, "Catch hunting animals add to the grounds of their keepers (%)")
    sport_draw: int = rule(10, 0, 100, E, "Prestige a gathering gains from the sport animals its hosts keep")
    medicine_yield: int = rule(3, 0, 100, E, "Medicine each epoch the medicine animals of a community yield")
    messenger_speed: int = rule(50, 0, 100, E, "Share of a letter's road the messenger animals of its sender's town spare it (%)")
    messenger_intercept_pct: int = rule(10, 0, 100, E, "Chance a letter carried by an animal is caught on the way (%)")


@dataclass(frozen=True)
class PlantsDepthRules:
    epiphyte_host_need: int = rule(30, 0, 100, E, "Forest cover an epiphyte needs before it thins")
    parasitic_host_harm: int = rule(10, 0, 100, E, "Harvest a parasitic plant at full numbers takes from its land each epoch")
    resin_tap_yield: int = rule(10, 0, 100, E, "Incense a tapped resin plant at full numbers yields each epoch")
    resin_tap_harm: int = rule(5, 0, 100, E, "Abundance tapping takes from a resin plant each epoch")


@dataclass(frozen=True)
class PlantProductsRules:
    fodder_herd_gain: int = rule(20, 0, 100, E, "Herd growth a community gains each epoch while it holds fodder for its herds (%)")
    fodder_per_head: int = rule(10, 1, 1000, E, "Head of herd one unit of fodder carries through the lean season")
    stimulant_habit_pct: int = rule(10, 0, 100, E, "Added chance a stimulating custom becomes a habit where the people's lands grow a stimulant (%)")
    grain_value: int = rule(100, 0, 1000, E, "Worth of a harvest of grain against an ordinary harvest (%)")
    tuber_value: int = rule(100, 0, 1000, E, "Worth of a harvest of tubers against an ordinary harvest (%)")
    fibre_value: int = rule(100, 0, 1000, E, "Worth of a harvest of fibre against an ordinary harvest (%)")
    dye_value: int = rule(100, 0, 1000, E, "Worth of a harvest of dye against an ordinary harvest (%)")
    timber_value: int = rule(100, 0, 1000, E, "Worth of a harvest of timber against an ordinary harvest (%)")
    fruit_value: int = rule(100, 0, 1000, E, "Worth of a harvest of fruit against an ordinary harvest (%)")
    herb_value: int = rule(100, 0, 1000, E, "Worth of a harvest of herbs against an ordinary harvest (%)")
    brew_base_value: int = rule(100, 0, 1000, E, "Worth of a harvest of brew base against an ordinary harvest (%)")
    reagent_value: int = rule(100, 0, 1000, E, "Worth of a harvest of reagents against an ordinary harvest (%)")
    poison_value: int = rule(100, 0, 1000, E, "Worth of a harvest of poison against an ordinary harvest (%)")
    oil_value: int = rule(120, 0, 1000, E, "Worth of a harvest of oil against an ordinary harvest (%)")
    sugar_value: int = rule(110, 0, 1000, E, "Worth of a harvest of sugar against an ordinary harvest (%)")
    spice_value: int = rule(300, 0, 1000, E, "Worth of a harvest of spice against an ordinary harvest (%)")
    resin_value: int = rule(200, 0, 1000, E, "Worth of a harvest of resin against an ordinary harvest (%)")
    stimulant_value: int = rule(150, 0, 1000, E, "Worth of a harvest of stimulants against an ordinary harvest (%)")
    fodder_value: int = rule(80, 0, 1000, E, "Worth of a harvest of fodder against an ordinary harvest (%)")


@dataclass(frozen=True)
class BeastTemperRules(Spanned):
    wounded_hp_pct: int = rule(40, 0, 100, E, "Share of its full strength below which a beast turns wounded and keeps to its lair (%)")
    wounded_fury_pct: int = rule(30, 0, 200, E, "More harm a wounded beast does when it turns on the one who wounded it (%)")
    brooding_fear_pct: int = rule(150, 0, 500, E, "Dread a beast guarding its young spreads against a beast at rest (%)")
    cowed_years: int = span(2, 0, 1000, E, "Years a beast driven off keeps away before its temper decides whether it returns")


@dataclass(frozen=True)
class BeastActsRules:
    vengeance_reach: int = rule(5, 0, 50, E, "Lands a vengeful beast crosses to reach the house or people it holds a grudge against")
    grudge_fade: int = rule(2, 0, 50, E, "Strength a beast's grudge loses in an epoch with no new harm")
    acquisitive_raid_pct: int = rule(20, 0, 100, E, "Chance in an epoch that an acquisitive beast raids the richest town in its reach (%)")
    protective_strike_pct: int = rule(30, 0, 100, E, "Share of an army in its land a protective beast strikes down in an epoch (%)")


@dataclass(frozen=True)
class HabitatWaysRules:
    magma_surface_pct: int = rule(10, 0, 100, E, "Chance in an epoch that a beast of the magma sea surfaces from volcanic ground (%)")
    ethereal_cross_pct: int = rule(5, 0, 100, E, "Chance in an epoch that a beast of the spirit realms crosses into the world, doubled where ley lines run (%)")


@dataclass(frozen=True)
class AversionRules:
    light_ward_pct: int = rule(40, 0, 100, E, "Chance in an epoch that a lit town drives off a beast that shuns light (%)")
    cold_ward_pct: int = rule(40, 0, 100, E, "Chance in an epoch that a town in frozen land drives off a beast that shuns cold (%)")


@dataclass(frozen=True)
class BeastWakingRules:
    disturbance_range: int = rule(1, 0, 10, E, "Lands from its lair within which a battle or siege can wake a sleeping beast")
    disturbance_pct: int = rule(20, 0, 100, E, "Chance a battle or siege in reach wakes a beast stirred by disturbance (%)")
    theft_pct: int = rule(80, 0, 100, E, "Chance a taking from its hoard wakes a beast stirred by theft (%)")
    sky_sign_pct: int = rule(50, 0, 100, E, "Chance a sign in its world's sky wakes a beast tied to the sky (%)")
    summons_bind_pct: int = rule(30, 0, 100, E, "Chance a beast woken by a summoning rite is bound to the town that keeps the rite (%)")
    hoard_theft_pct: int = rule(5, 0, 100, E, "Chance in an epoch that the bold of a town near a sleeping beast steal from its hoard (%)")


@dataclass(frozen=True)
class BeastProductsRules:
    meat_value: int = rule(100, 0, 1000, E, "Worth of meat taken from a kind against its usual worth (%)")
    meat_yield: int = rule(100, 0, 100, E, "Share of its usual amount of meat a kind gives when hunted or kept (%)")
    hide_value: int = rule(100, 0, 1000, E, "Worth of hide taken from a kind against its usual worth (%)")
    hide_yield: int = rule(100, 0, 100, E, "Share of its usual amount of hide a kind gives when hunted or kept (%)")
    calcified_tissue_value: int = rule(100, 0, 1000, E, "Worth of bone taken from a kind against its usual worth (%)")
    calcified_tissue_yield: int = rule(100, 0, 100, E, "Share of its usual amount of bone a kind gives when hunted or kept (%)")
    ivory_value: int = rule(100, 0, 1000, E, "Worth of ivory taken from a kind against its usual worth (%)")
    ivory_yield: int = rule(100, 0, 100, E, "Share of its usual amount of ivory a kind gives when hunted or kept (%)")
    chitin_value: int = rule(100, 0, 1000, E, "Worth of chitin taken from a kind against its usual worth (%)")
    chitin_yield: int = rule(100, 0, 100, E, "Share of its usual amount of chitin a kind gives when hunted or kept (%)")
    venom_value: int = rule(100, 0, 1000, E, "Worth of venom taken from a kind against its usual worth (%)")
    venom_yield: int = rule(100, 0, 100, E, "Share of its usual amount of venom a kind gives when hunted or kept (%)")
    silk_value: int = rule(100, 0, 1000, E, "Worth of silk taken from a kind against its usual worth (%)")
    silk_yield: int = rule(100, 0, 100, E, "Share of its usual amount of silk a kind gives when hunted or kept (%)")
    wool_value: int = rule(100, 0, 1000, E, "Worth of wool taken from a kind against its usual worth (%)")
    wool_yield: int = rule(100, 0, 100, E, "Share of its usual amount of wool a kind gives when hunted or kept (%)")
    milk_value: int = rule(100, 0, 1000, E, "Worth of milk taken from a kind against its usual worth (%)")
    milk_yield: int = rule(100, 0, 100, E, "Share of its usual amount of milk a kind gives when hunted or kept (%)")
    feathers_value: int = rule(100, 0, 1000, E, "Worth of feathers taken from a kind against its usual worth (%)")
    feathers_yield: int = rule(100, 0, 100, E, "Share of its usual amount of feathers a kind gives when hunted or kept (%)")
    magic_reagents_value: int = rule(100, 0, 1000, E, "Worth of reagents taken from a kind against its usual worth (%)")
    magic_reagents_yield: int = rule(100, 0, 100, E, "Share of its usual amount of reagents a kind gives when hunted or kept (%)")
    great_beast_tissue_value: int = rule(100, 0, 1000, E, "Worth of the tissue of great beasts taken from a kind against its usual worth (%)")
    great_beast_tissue_yield: int = rule(100, 0, 100, E, "Share of its usual amount of the tissue of great beasts a kind gives when hunted or kept (%)")
    eggs_value: int = rule(100, 0, 1000, E, "Worth of eggs taken from a kind against its usual worth (%)")
    eggs_yield: int = rule(100, 0, 100, E, "Share of its usual amount of eggs a kind gives when hunted or kept (%)")
    blood_value: int = rule(120, 0, 1000, E, "Worth of blood taken from a kind against its usual worth (%)")
    blood_yield: int = rule(60, 0, 100, E, "Share of its usual amount of blood a kind gives when hunted or kept (%)")
    organs_value: int = rule(150, 0, 1000, E, "Worth of organs taken from a kind against its usual worth (%)")
    organs_yield: int = rule(40, 0, 100, E, "Share of its usual amount of organs a kind gives when hunted or kept (%)")
    fat_value: int = rule(90, 0, 1000, E, "Worth of fat taken from a kind against its usual worth (%)")
    fat_yield: int = rule(70, 0, 100, E, "Share of its usual amount of fat a kind gives when hunted or kept (%)")
    scent_value: int = rule(250, 0, 1000, E, "Worth of scent taken from a kind against its usual worth (%)")
    scent_yield: int = rule(20, 0, 100, E, "Share of its usual amount of scent a kind gives when hunted or kept (%)")
    honey_value: int = rule(140, 0, 1000, E, "Worth of honey taken from a kind against its usual worth (%)")
    honey_yield: int = rule(50, 0, 100, E, "Share of its usual amount of honey a kind gives when hunted or kept (%)")
    wax_value: int = rule(160, 0, 1000, E, "Worth of wax taken from a kind against its usual worth (%)")
    wax_yield: int = rule(30, 0, 100, E, "Share of its usual amount of wax a kind gives when hunted or kept (%)")


@dataclass(frozen=True)
class TransmissionRules:
    further_route_pct: int = rule(40, 0, 100, E, "Chance a new sickness holds one further route beside its main one (%)")
    further_share_min: int = rule(10, 1, 50, E, "Least share of the spread a further route carries (%)")
    further_share_max: int = rule(35, 1, 90, E, "Greatest share of the spread a further route carries (%)")
    inhalation_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the inhalation route where it holds it (%)")
    inhalation_block_pct: int = rule(30, 0, 100, E, "Share of the inhalation route a people that knows how to block it cuts away (%)")
    water_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the water route where it holds it (%)")
    water_block_pct: int = rule(50, 0, 100, E, "Share of the water route a people that knows how to block it cuts away (%)")
    contact_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the contact route where it holds it (%)")
    contact_block_pct: int = rule(40, 0, 100, E, "Share of the contact route a people that knows how to block it cuts away (%)")
    bite_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the bite route where it holds it (%)")
    bite_block_pct: int = rule(30, 0, 100, E, "Share of the bite route a people that knows how to block it cuts away (%)")
    spirit_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the spirit route where it holds it (%)")
    spirit_block_pct: int = rule(40, 0, 100, E, "Share of the spirit route a people that knows how to block it cuts away (%)")
    void_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the void route where it holds it (%)")
    void_block_pct: int = rule(20, 0, 100, E, "Share of the void route a people that knows how to block it cuts away (%)")
    curse_rate: int = rule(50, 0, 100, E, "How readily a sickness passes by the curse route where it holds it (%)")
    curse_block_pct: int = rule(40, 0, 100, E, "Share of the curse route a people that knows how to block it cuts away (%)")
    ingestion_rate: int = rule(40, 0, 100, E, "How readily a sickness passes by the ingestion route where it holds it (%)")
    ingestion_block_pct: int = rule(50, 0, 100, E, "Share of the ingestion route a people that knows how to block it cuts away (%)")
    blood_rate: int = rule(30, 0, 100, E, "How readily a sickness passes by the blood route where it holds it (%)")
    blood_block_pct: int = rule(30, 0, 100, E, "Share of the blood route a people that knows how to block it cuts away (%)")
    birth_rate: int = rule(20, 0, 100, E, "How readily a sickness passes by the birth route where it holds it (%)")
    birth_block_pct: int = rule(10, 0, 100, E, "Share of the birth route a people that knows how to block it cuts away (%)")
    rite_rate: int = rule(30, 0, 100, E, "How readily a sickness passes by the rite route where it holds it (%)")
    rite_block_pct: int = rule(40, 0, 100, E, "Share of the rite route a people that knows how to block it cuts away (%)")
    gaze_rate: int = rule(30, 0, 100, E, "How readily a sickness passes by the gaze route where it holds it (%)")
    gaze_block_pct: int = rule(30, 0, 100, E, "Share of the gaze route a people that knows how to block it cuts away (%)")
    experience_rate: int = rule(30, 0, 100, E, "How readily a sickness passes by the experience route where it holds it (%)")
    experience_block_pct: int = rule(20, 0, 100, E, "Share of the experience route a people that knows how to block it cuts away (%)")
    intimate_rate: int = rule(20, 0, 100, E, "How readily a sickness passes by the intimate route where it holds it (%)")
    intimate_block_pct: int = rule(40, 0, 100, E, "Share of the intimate route a people that knows how to block it cuts away (%)")
    objects_rate: int = rule(40, 0, 100, E, "How readily a sickness passes by the objects route where it holds it (%)")
    objects_block_pct: int = rule(40, 0, 100, E, "Share of the objects route a people that knows how to block it cuts away (%)")


@dataclass(frozen=True)
class SpreadRules:
    wildlife_pct: int = rule(
        10, 0, 100, E, "Chance a host species carries a sickness from a stricken land into a neighbouring land of its range each epoch (%)"
    )
    migration_pct: int = rule(20, 0, 100, E, "Chance migrants and refugees leaving a stricken land carry its sickness to their new home (%)")
    gathering_pct: int = rule(30, 0, 100, E, "Chance guests at a gathering in a stricken land carry its sickness home (%)")
    waterway_pct: int = rule(25, 0, 100, E, "Chance a water-borne sickness is carried downstream into the next land along a river (%)")
    carried_severity_pct: int = rule(50, 1, 100, E, "Share of its severity a sickness keeps when one of these paths carries it to a new land (%)")


@dataclass(frozen=True)
class BodyPlanRules:
    spine_paralysis_pct: int = rule(30, 0, 100, E, "Chance a wound to the spine paralyses what lies below it (%)")
    tentacle_share: int = rule(12, 1, 50, E, "Share of grip and movement one degree of a wound to soft arms takes, so they are lost a part at a time (%)")
    carapace_guard_pct: int = rule(40, 0, 100, E, "Chance a blow at the body strikes its carapace first (%)")
    colonial_member_floor_pct: int = rule(20, 0, 100, E, "Vitality below which a body of many members has too few left to live (%)")


@dataclass(frozen=True)
class DamageRules:
    asphyxia_per_turn: int = rule(20, 0, 100, E, "Harm lack of air adds to each blow of drowning, burial, smoke or strangling, as the breath runs out (%)")


@dataclass(frozen=True)
class InjuryDepthRules:
    internal_bleed_death_pct: int = rule(30, 0, 100, E, "Chance each epoch an untreated bleed inside the body kills (%)")
    internal_bleed_hidden_pct: int = rule(70, 0, 100, E, "Chance a bleed inside the body stays hidden until a healer finds it (%)")
    dislocation_disable: int = rule(80, 0, 100, E, "Use of a limb a dislocated joint takes until it is set (%)")


@dataclass(frozen=True)
class InjuryStateRules:
    gangrene_pct: int = rule(20, 0, 100, E, "Chance an infected wound that would have killed turns gangrenous first (%)")
    gangrene_death_pct: int = rule(50, 0, 100, E, "Chance each epoch a gangrenous wound kills unless the part is cut away or treated at the right tier (%)")
    reopen_strain_pct: int = rule(10, 0, 100, E, "Chance a healing wound reopens when its bearer is hurt again or strained in the same epoch (%)")


@dataclass(frozen=True)
class HarmCauseRules:
    childbirth_risk_pct: int = rule(3, 0, 100, E, "Chance a birthing parent who lives is still harmed in the birth (%)")
    childbirth_medicine_cut_pct: int = rule(50, 0, 100, E, "Share of that risk the best medicine takes away, scaled by the medicine a community knows (%)")
    sport_harm_pct: int = rule(5, 0, 100, E, "Chance the loser of a contest of strength or of an arena bout is harmed (%)")
    childbirth_hp: int = rule(25, 1, 100, E, "Harm a birth that goes badly deals the birthing parent")
    sport_hp: int = rule(15, 1, 100, E, "Harm a contest of strength deals the one harmed")


@dataclass(frozen=True)
class TreatmentRules:
    drain_infection_cut_pct: int = rule(40, 0, 100, E, "Share of festering and of gangrene's deadliness that draining a wound takes away (%)")
    bleed_harm_pct: int = rule(20, -100, 100, E, "Harm bloodletting does: fewer wounds mend and more festering kills; below zero it helps (%)")
    medicate_effect_pct: int = rule(30, 0, 100, E, "Extra mending a remedy gives a wound or sickness it is given against (%)")
    bleeding_belief: int = rule(50, 0, 100, E, "Correctness below which a medical theory a people holds calls for bloodletting (%)")


@dataclass(frozen=True)
class BodyCapacityRules:
    endurance_labour_pct: int = rule(100, 0, 300, E, "How strongly a body's endurance spares it the toil of long journeys and hard work (%)")
    perception_watch_pct: int = rule(100, 0, 300, E, "How strongly a body's perception counts in keeping watch, scouting and tracking (%)")
