from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CREATURES
E = RuleGroup.ENVIRONMENT
V = RuleGroup.CIVILIZATION
W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class MicrobeRules:
    rest: int = rule(50, 0, 100, E, "Life the soil of a land drifts toward before moisture, fertility, pollution and salt move it")
    moisture_pct: int = rule(30, 0, 100, E, "Share of a land's moisture that adds to the life of its soil (%)")
    fertility_pct: int = rule(30, 0, 100, E, "Share of a land's base fertility that adds to the life of its soil (%)")
    pollution_pct: int = rule(60, 0, 200, E, "Share of a land's pollution that kills the life of its soil (%)")
    salinity_pct: int = rule(50, 0, 200, E, "Share of a land's salt that kills the life of its soil (%)")
    drift_pct: int = rule(20, 0, 100, E, "Share of the gap to its target the life of a living soil closes each epoch (%)")
    sterile_below: int = rule(15, 0, 100, E, "Life under which a soil counts as sterile and heals only slowly")
    sterile_drift_pct: int = rule(5, 0, 100, E, "Share of the gap a sterile soil closes each epoch (%)")
    recycling_pct: int = rule(60, 0, 200, E, "How much faster or slower a soil recycles its nutrients for each step of life above or below the middle (%)")


@dataclass(frozen=True)
class FermentationRules:
    found_chance: int = rule(10, 0, 100, V, "Chance a town that ferments, bakes, cures or pickles founds a culture of its own in an epoch (%)")
    start_quality: int = rule(30, 0, 100, V, "Quality a newly founded culture starts at")
    tending: int = rule(2, 0, 100, V, "Quality a kept culture gains each epoch it is used")
    ceiling: int = rule(90, 0, 100, V, "Highest quality tending alone can bring a culture to")
    plague_loss_chance: int = rule(25, 0, 100, V, "Chance a culture is lost in an epoch while sickness rages where it is kept (%)")
    trade_chance: int = rule(5, 0, 100, V, "Chance a culture passes along a trade route to the partner town in an epoch (%)")
    traded_quality_pct: int = rule(70, 0, 100, V, "Share of its quality a culture keeps when it passes to another town (%)")
    delight_pct: int = rule(50, 0, 200, V, "Delight a dish made with a culture gains at full quality (%)")
    hand_tending: int = rule(5, 0, 100, V, "Quality a mortal who tends a culture by hand adds to it")
    wild_spoil_pct: int = rule(10, 0, 100, V, "Chance in an epoch that a wild culture of a place spoils and is lost (%)")
    wild_found_pct: int = rule(20, 0, 100, V, "Chance a town founding a culture keeps the wild mixed culture of its place instead (%)")


@dataclass(frozen=True)
class SymbiosisRules:
    form_chance: int = rule(4, 0, 100, C, "Chance two kinds that share a land form a bond between them in an epoch (%)")
    shared_abundance: int = rule(20, 0, 100, C, "Abundance both kinds need in a land before a bond can form there")
    start_strength: int = rule(40, 0, 100, C, "Strength a newly formed bond between kinds starts at")
    mutual_pct: int = rule(20, 0, 100, C, "Room a kind gains in a land from a mutualist living there, at full strength (%)")
    commensal_pct: int = rule(8, 0, 100, C, "Room the beneficiary of a commensal bond gains in a land, at full strength (%)")
    parasite_loss: int = rule(4, 0, 50, C, "Abundance a host loses each epoch to a parasite sharing its land, at full strength")
    livestock_loss: int = rule(3, 0, 100, C, "Livestock a town loses each epoch to a parasite of its herds living in its land, at full strength")
    mimic_shield_pct: int = rule(50, 0, 100, C, "Share of hunting a mimic escapes where the kind it copies lives, at full strength (%)")
    vector_load: int = rule(3, 0, 100, C, "Disease load a parasite of herds raises in its land each epoch, at full strength")
    mimic_alarm_pct: int = rule(80, 0, 100, C, "Share of the danger of the kind it copies a mimic is read with by those who meet it there (%)")
    farming_pct: int = rule(40, 0, 200, C, "More room a kind that tends another kind, and the kind it tends, gain from each other at full strength (%)")


@dataclass(frozen=True)
class DormancyRules:
    torpor_food_cut_pct: int = rule(30, 0, 100, C, "How much less food a kind that slows in daily torpor needs (%)")
    cryptobiosis_survival_pct: int = rule(90, 0, 100, C, "Share of the losses of a starving or stricken land a near-lifeless kind lives through (%)")
    cryptobiosis_wake_pct: int = rule(
        20, 0, 100, C, "Chance in an epoch that a near-lifeless kind gone from a land wakes there again once its season turns (%)"
    )
    disturb_chance: int = rule(10, 0, 100, C, "Chance a sleeping aggressive kind is woken by the folk of a crowded land in an epoch (%)")
    seasonal_at: int = rule(20, 0, 100, C, "Seasonality of its home land from which a small kind that stays put sleeps through its harshest season")
    disturb_aggression: int = rule(50, 0, 100, C, "Aggression from which a sleeping kind wakes hungry when disturbed")
    disturb_population: int = rule(3000, 0, 1000000, C, "Folk a land holds before its hunters and woodcutters disturb the sleepers there")
    woken_raid_pct: int = rule(200, 100, 500, C, "Chance of raiding a woken kind has, against its usual chance (%)")
    lair_hunt_pct: int = rule(50, 0, 200, C, "Easier a hunt for a kind is while it sleeps in its lair (%)")
    diapause_survival_pct: int = rule(
        60, 0, 100, C, "Share of its numbers a kind that pauses its young until the season returns keeps through a failed season (%)"
    )
    mesotherm_food_pct: int = rule(70, 0, 100, C, "Food a kind with a warm core and cooler limbs needs against a warm-blooded kind (%)")


@dataclass(frozen=True)
class ThermoregulationRules:
    heterotherm_switch: int = rule(
        30, 0, 100, C, "Share of a cold-blooded kind's slowing a kind that switches between warm and cold takes in a cold season (%)"
    )
    frozen_pct: int = rule(30, 0, 200, C, "Activity a cold-blooded kind keeps in a frozen season (%)")
    cold_pct: int = rule(60, 0, 200, C, "Activity a cold-blooded kind keeps in a cold season (%)")
    warm_pct: int = rule(115, 0, 200, C, "Activity a cold-blooded kind has in a warm season (%)")
    hot_pct: int = rule(125, 0, 200, C, "Activity a cold-blooded kind has in a hot season (%)")
    endotherm_cold_food_pct: int = rule(125, 100, 300, C, "Food a warm-blooded people needs in a cold or frozen season, against its usual need (%)")
    labour_pct: int = rule(100, 0, 100, V, "Share of the loss of activity a cold-blooded people's work suffers in the cold (%)")
    winter_war_pct: int = rule(100, 0, 100, W, "Share of the loss of activity a cold-blooded people's armies suffer in a cold season (%)")


@dataclass(frozen=True)
class SenseRules:
    electric_range: int = rule(2, 0, 20, C, "Reach in lands at which an electric sense finds hidden living beings; at two it reaches fully")
    electric_water_pct: int = rule(200, 0, 500, W, "Strength of an electric sense for those who live in water or wetland (%)")
    ultraviolet_track_pct: int = rule(30, 0, 100, W, "Weight an ultraviolet sense gives to following trails and signs others cannot see (%)")
    base_sight: int = rule(50, 0, 100, C, "Sight a kind or people starts with when its senses are first read")
    sharpened: int = rule(20, 0, 100, C, "Acuity a sense gains when a god sharpens it")
    gift: int = rule(70, 0, 100, C, "Acuity of a sense a kind or people is born with when its senses are first read")
    agents_pct: int = rule(60, 0, 200, W, "More quickly agents are found among a people whose senses detect them, at full acuity (%)")
    night_pct: int = rule(30, 0, 200, W, "Strength an army gains at night from senses that see in the dark, at full acuity (%)")
    ambush_pct: int = rule(50, 0, 100, W, "Share of an ambush's surprise an army's keen senses take away, at full acuity (%)")
    tracking_pct: int = rule(40, 0, 200, C, "More game a people's hunters take with senses that track, at full acuity (%)")
    navigation_pct: int = rule(30, 0, 100, V, "Share of the losses at sea a people's sense of direction spares, at full acuity (%)")
    spirits_pct: int = rule(50, 0, 100, W, "Share more often a people that sees spirits uncovers the spies of the gods, at full acuity (%)")
    pressure_warning_pct: int = rule(
        40, 0, 100, C, "Share of the chance of a seasonal hazard folk who sense coming storms and water movement avoid at a full sense (%)"
    )
    taste_poison_cut_pct: int = rule(50, 0, 100, C, "Share of the sickness of a poisoned catch folk who taste poison avoid at a full sense (%)")


@dataclass(frozen=True)
class PlantDefenceRules:
    stinging_harm: int = rule(5, 0, 50, E, "Danger stinging plants lend a land they cover fully, and the fibre its towns handle from them each epoch")
    guardian_harm: int = rule(10, 0, 50, E, "Abundance a plant's guardian allies drive from the grazers of a land they cover fully each epoch")
    default_potency: int = rule(50, 0, 100, E, "Potency a plant's defence takes when its maker names the defence but not its strength")
    thorn_passage_pct: int = rule(30, 0, 100, E, "Share of a land's passage thorns take where they cover all of it, at full potency (%)")
    thorn_grazing_pct: int = rule(40, 0, 100, E, "Share of grazing thorns spoil where they cover all of a land, at full potency (%)")
    toxin_forage_pct: int = rule(30, 0, 100, E, "Share of what foragers take that toxic plants spoil where they cover all of a land, at full potency (%)")
    toxin_medicine: int = rule(2, 0, 100, E, "Medicine a town gathers each epoch from the toxic plants covering its land, at full cover and potency")
    allelopathy_pct: int = rule(
        30, 0, 100, E, "Share of a land's harvest plants that poison their neighbours take, where they cover all of it, at full potency (%)"
    )
    carnivorous_danger: int = rule(20, 0, 100, E, "Danger a land gains from flesh-eating plants that cover all of it, at full potency")
    mimicry_cut_pct: int = rule(30, 0, 100, E, "Share of the overgrazing of a land plants that look like guarded plants spare it at full cover (%)")
    regrowth_cut_pct: int = rule(40, 0, 100, E, "Share of the overgrazing of a land plants that grow back fast heal at full cover (%)")


@dataclass(frozen=True)
class IslandRules:
    drift_epochs: int = rule(8, 1, 100, C, "Epochs a kind must live on islands alone before its size drifts one step")
    endemic_regions: int = rule(2, 1, 20, C, "Most lands a kind may live in and still count as endemic")
    relict_pct: int = rule(25, 0, 100, C, "Share of its widest range under which a kind counts as a relict (%)")
    revered_value: int = rule(60, 0, 100, C, "Weight of nature among a people's values from which it spares endemic and relict kinds")
