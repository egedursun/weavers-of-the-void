from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

E = RuleGroup.CREATURES
D = RuleGroup.DISEASE
W = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class TraitEvolutionRules:
    predator_pressure: int = rule(2, 0, 20, E, "How far predators move the speed and camouflage of their prey each epoch")
    arms_race: int = rule(1, 0, 20, E, "How far a predator's speed follows the speed of its prey each epoch")
    climate_pressure: int = rule(2, 0, 20, E, "How far a land colder or warmer than a species likes moves its cold tolerance each epoch")
    hunting_pressure: int = rule(2, 0, 20, E, "How far hunting moves a species toward wariness and smaller size each epoch")
    protection_relax_pct: int = rule(50, 0, 100, E, "Share of selection a species sacred to a god is spared (%)")
    leak_variance: int = rule(2, 0, 20, E, "Variance the leak of a land adds to each trait each epoch at full leak")
    speciation_distance: int = rule(25, 0, 100, E, "Trait distance between a range and the rest of its species past which it splits off")
    escape_pct: int = rule(30, 0, 100, E, "How much a prey's speed and camouflage spare it from its hunters at full measure (%)")
    wariness_pct: int = rule(30, 0, 100, E, "How much wariness spares a species from hunting at full measure (%)")
    cold_reach: int = rule(10, 0, 50, E, "Degrees below its usual coldest a species can bear at full cold tolerance")
    heat_reach: int = rule(10, 0, 50, E, "Degrees above its usual hottest a species can bear at full heat tolerance")
    drought_reach: int = rule(20, 0, 100, E, "Moisture below its need a species can bear at full drought tolerance")
    drought_pressure: int = rule(2, 0, 20, E, "How far a land drier than a species needs moves its drought tolerance each epoch")
    senses_pct: int = rule(20, 0, 100, E, "How much keen senses spare a species from its hunters at full measure (%)")
    fecundity_pct: int = rule(20, 0, 100, E, "Extra growth a species of full fecundity gains (%)")
    per_epoch: int = rule(400, 0, 100000, E, "Species ranges whose traits move each epoch at most")


@dataclass(frozen=True)
class NicheRules(Spanned):
    exclusion_loss: int = rule(6, 0, 100, E, "Abundance the less fit of two species in one niche and land loses each epoch")
    excluded_at: int = rule(3, 0, 100, E, "Abundance below which the losing species is excluded from the land")
    displacement_pct: int = rule(20, 0, 100, E, "Chance each epoch the losing species shifts its niche instead (%)")
    radiation_pct: int = rule(10, 0, 100, E, "Chance each epoch a surviving lineage spreads into a niche emptied by extinction (%)")
    vacated_window_years: int = span(50, 1, 2500, E, "Years a niche stays open after its species is lost")

    @property
    def vacated_window(self) -> int:
        return self.epochs(self.vacated_window_years)


@dataclass(frozen=True)
class TrophicRules:
    efficiency_pct: int = rule(150, 1, 400, E, "Biomass a trophic level can hold for each hundred of the level below it (%)")
    collapse: int = rule(12, 0, 100, E, "Abundance a level above its bound loses each epoch")


@dataclass(frozen=True)
class KeystoneRules:
    harvest_gain: int = rule(10, 0, 100, E, "Harvest a land's pollinators add at full strength (%)")
    soil_gain: int = rule(2, 0, 100, E, "Soil fertility a land's soil-makers add each epoch at full strength")
    wetland_gain: int = rule(10, 0, 100, E, "Wetland a land's dam-builders hold at full strength")
    disease_relief: int = rule(8, 0, 100, E, "Disease load a land's scavengers keep away at full strength")
    lost_decay: int = rule(2, 0, 100, E, "Soil fertility and harvest a land loses each epoch once its keystone is gone")


@dataclass(frozen=True)
class FeralRules(Spanned):
    revert_years: int = span(20, 1, 2500, E, "Years after which a released herd steps one stage back toward the wild")
    release_abundance: int = rule(20, 0, 100, E, "Abundance a released herd brings to the land it is loosed in")
    breed_after_years: int = span(100, 1, 2500, E, "Years feral after which a domestic species becomes a new wild breed")

    @property
    def revert_epochs(self) -> int:
        return self.epochs(self.revert_years)

    @property
    def breed_after(self) -> int:
        return self.epochs(self.breed_after_years)


@dataclass(frozen=True)
class LineageRules:
    blessing_pct: int = rule(20, 0, 100, E, "Chance each epoch a species sacred to a god is marked with a blessing its lineage inherits (%)")
    taint_leak: int = rule(80, 0, 100, E, "Leak of a land past which a species living there is tainted down its line")
    taint_pct: int = rule(10, 0, 100, E, "Chance each epoch such a species is tainted (%)")


@dataclass(frozen=True)
class PathogenRules:
    sparse_population: int = rule(800, 0, 1000000, D, "Population below which a lethal disease is selected toward mildness")
    lethality_drop: int = rule(2, 0, 100, D, "Lethality a disease loses each epoch among sparse peoples")
    crowd_population: int = rule(6000, 0, 10000000, D, "Population above which a disease is selected toward spreading")
    transmission_gain: int = rule(2, 0, 100, D, "Virulence a disease gains each epoch in crowded places")
    resistance_gain: int = rule(3, 0, 100, D, "Resistance a disease gains each epoch where it is treated")
    resistance_pct: int = rule(50, 0, 100, D, "How much full resistance blunts treatment and cures (%)")
    escape_immune_pct: int = rule(60, 0, 100, D, "Immune share of its hosts past which a disease is driven to escape immunity")
    escape_pct: int = rule(25, 0, 100, D, "Chance each epoch such a disease throws off a new strain (%)")
    climate_step: int = rule(2, 0, 100, D, "How far a disease's cold or heat tolerance moves toward the lands it spreads in each epoch")
    symptom_pct: int = rule(20, 0, 100, D, "Chance each epoch a crowded disease takes up a symptom that spreads it by its own way (%)")
    incubation_step: int = rule(1, 0, 20, D, "Epochs of incubation a disease gains among sparse peoples, spreading before it is seen")


@dataclass(frozen=True)
class VectorRules:
    warm_bite_pct: int = rule(130, 0, 400, D, "Spread of a bitten sickness in warm lands, where its biting hosts thrive (%)")
    cold_bite_pct: int = rule(50, 0, 400, D, "Spread of a bitten sickness in cold lands (%)")
    herd_head: int = rule(60, 1, 100000, D, "Head of a kept herd that counts as a full stock of a host")
    migrant_pct: int = rule(50, 0, 100, D, "Share of its numbers a migrating host carries along each land of its path (%)")


@dataclass(frozen=True)
class CarrierRules:
    carrier_pct: int = rule(8, 0, 100, D, "Chance a named mortal in a land with an outbreak carries the disease without falling ill (%)")
    seed_pct: int = rule(25, 0, 100, D, "Chance each epoch a carrier who has travelled seeds an outbreak where it now is (%)")
    identify_skill: int = rule(50, 0, 100, D, "Medicine a physician needs to find a carrier, with the contagion theory known")
    theory_truth: int = rule(60, 0, 100, D, "Truth a community's ruling theory of medicine needs to count as knowing how contagion passes")
    per_epoch: int = rule(40, 0, 10000, D, "Carriers who may appear each epoch at most")
    seed_severity: int = rule(30, 0, 100, D, "Severity of an outbreak a carrier seeds")


@dataclass(frozen=True)
class SpilloverRules:
    base_pct: int = rule(1, 0, 100, D, "Chance each epoch a wild host's disease jumps to the folk of its land (%)")
    cleared_pct: int = rule(4, 0, 100, D, "Extra chance at fully cleared land (%)")
    hunted_pct: int = rule(4, 0, 100, D, "Extra chance where the host is hunted hard (%)")
    herd_pct: int = rule(3, 0, 100, D, "Extra chance where herds graze among the host (%)")
    per_epoch: int = rule(3, 0, 1000, D, "Spillovers each epoch at most")
    severity: int = rule(25, 0, 100, D, "Severity of an outbreak a spillover begins")


@dataclass(frozen=True)
class PlagueResponseRules(Spanned):
    choose_pct: int = rule(40, 0, 100, D, "Chance each epoch a community struck by an outbreak takes up a response (%)")
    length_years: int = span(3, 1, 2500, D, "Years a response lasts unless renewed")
    border_trade_pct: int = rule(40, 0, 100, D, "Trade a community loses while its borders are closed (%)")
    border_unrest: int = rule(4, 0, 100, D, "Unrest closed borders raise each epoch")
    quarantine_spread_pct: int = rule(40, 0, 100, D, "Spread a quarantine stops (%)")
    riot_pct: int = rule(10, 0, 100, D, "Chance each epoch a quarantine sets off a riot (%)")
    riot_unrest: int = rule(10, 0, 100, D, "Unrest a quarantine riot raises")
    burn_spread_pct: int = rule(20, 0, 100, D, "Spread burning the dead stops (%)")
    burn_cohesion: int = rule(3, 0, 100, D, "Cohesion burning the dead costs a people whose funeral rites forbid it")
    expel_stigma: int = rule(10, 0, 100, D, "Stigma expelling the sick adds to a disease")
    expel_spread_pct: int = rule(15, 0, 100, D, "Spread expelling the sick stops at home (%)")
    prayer_morale: int = rule(5, 0, 100, D, "Satisfaction prayer gatherings bring")
    prayer_spread_pct: int = rule(20, 0, 100, D, "Extra spread at prayer gatherings (%)")
    cure_points: int = rule(5, 0, 1000, D, "Extra research the community's institutions give a cure it seeks")

    @property
    def length(self) -> int:
        return self.epochs(self.length_years)


@dataclass(frozen=True)
class VaccinationRules:
    immune_gain: int = rule(15, 0, 100, D, "Immune share variolation or vaccination gives a community each epoch")
    risk_pct: int = rule(2, 0, 100, D, "Share of those treated who fall ill of the treatment (%)")
    variolation_pct: int = rule(50, 0, 100, D, "How much of the gain variolation gives compared with vaccination (%)")


@dataclass(frozen=True)
class CureResearchRules:
    per_scholar: int = rule(3, 0, 100, D, "Research a scholar of medicine at an institution adds each epoch")
    scholar_skill: int = rule(30, 0, 100, D, "Medicine a mortal needs to count as a scholar of an institution")
    theory_pct: int = rule(50, 0, 300, D, "Extra research when the institution holds a true theory of contagion (%)")
    specimen: int = rule(4, 0, 100, D, "Research an outbreak in the institution's land adds each epoch")
    threshold: int = rule(100, 1, 100000, D, "Research a cure needs")
    prestige: int = rule(8, 0, 100, D, "Prestige the community that finds a cure wins")
    price: int = rule(30, 0, 100000, D, "Coin a community pays the holders of a cure to learn it")
    diffusion_pct: int = rule(15, 0, 100, D, "Chance each epoch a cure passes along a trade route (%)")


@dataclass(frozen=True)
class BiomeSuccessionRules:
    rate: int = rule(8, 0, 100, E, "Progress a land makes toward its next stage each epoch in a mild, wet and fertile land")
    grazing_hold: int = rule(30, 0, 100, E, "Grazing past which a grassland stays a grassland")
    fire_pct: int = rule(4, 0, 100, E, "Chance each epoch a dry land in a young or old forest burns (%)")
    fire_rain: int = rule(30, 0, 100, E, "Rainfall below which a land is dry enough to burn")
    slash_pct: int = rule(5, 0, 100, E, "Chance each epoch farmed forest land is cleared by fire (%)")
    burn_scar: int = rule(10, 0, 100, E, "Depth of the burn scar a fire in the woods leaves")


@dataclass(frozen=True)
class CycleRules:
    volcanic_carbon: int = rule(3, 0, 100, W, "Carbon a fully volcanic world adds each epoch")
    burning_carbon: int = rule(4, 0, 100, W, "Carbon fully cleared or burned lands add each epoch")
    forest_uptake: int = rule(4, 0, 100, W, "Carbon fully forested lands take up each epoch")
    ocean_uptake: int = rule(2, 0, 100, W, "Carbon a full ocean takes up each epoch")
    respiration: int = rule(2, 0, 100, W, "Carbon the breath and decay of a land's animals add each epoch at full biomass")
    weathering: int = rule(1, 0, 100, W, "Carbon rough, weathering rock takes up each epoch at full roughness")
    evaporation: int = rule(1, 0, 100, W, "Water a full ocean frees into the air each epoch for each degree of warmth")
    discharge: int = rule(1, 0, 100, W, "Water rivers carry back to the sea each epoch on a world of rivers")
    water_from_heat: int = rule(2, 0, 100, W, "Water each degree of warmth frees from the ice each epoch")
    rain_pct: int = rule(20, 0, 200, W, "Share of the water cycle's swing that reaches each land's rainfall (%)")
    sea_level: int = rule(1, 0, 100, W, "Sea level each step of free water above the middle raises")
    erosion_loss: int = rule(2, 0, 100, W, "Nutrients fully eroded lands lose each epoch")
    ash_gain: int = rule(3, 0, 100, W, "Nutrients volcanic ash brings each epoch at full volcanism")
    river_gain: int = rule(2, 0, 100, W, "Nutrients rivers bring their lands each epoch")
    fertility_pct: int = rule(20, 0, 200, W, "Share of the nutrient cycle's swing that reaches each land's soil (%)")


@dataclass(frozen=True)
class LandShapingRules:
    step: int = rule(10, 1, 100, E, "Elevation a god raises or lowers a land by in one act")
    spring_moisture: int = rule(15, 0, 100, E, "Moisture a spring opened by a god brings")
    lava_volcanism: int = rule(20, 0, 100, W, "Volcanism called lava adds to its world")
    awe_loss: int = rule(6, 0, 100, E, "Awe the folk of a land lose for a god who drowns, burns or sinks it")
    awe_gain: int = rule(3, 0, 100, E, "Awe the folk of a land gain for a god who waters or raises it")
    downstream_moisture: int = rule(8, 0, 100, E, "Moisture the land downstream gains or loses when a god carves, fills or waters a valley")
    coast_lift: int = rule(40, 0, 100, E, "Elevation past which a raised coastal land stands above the sea and loses its harbours")
