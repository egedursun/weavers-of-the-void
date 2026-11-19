from aerona.db.tables.evolution import (
    CarrierRow,
    CureResearchRow,
    EcosystemServiceRow,
    LineageMarkRow,
    PlagueResponseRow,
    SpeciesTraitRow,
    TrophicLevelRow,
    WorldCycleRow,
)
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
MIGRATION = "migration 3ccb476b4bb5"
EVOLUTION_SECTION = "section-evolution"
COMMUNITIES = ("people", "settlement")

EVOLUTION_MECHANICS = (
    Mechanic(
        key="trait_evolution",
        tools=("shape_trait",),
        spec_item="S3.2/RP3",
        title=(
            "Trait evolution: each range of a species carries its own size, speed, armour, venom, camouflage, "
            "cold tolerance, wits, fecundity and wariness, moved by selection"
        ),
        subsystem=S.ECOLOGY,
        phases=("trait_evolution", "ecology", "speciation"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: every range draws its traits from its species on the first epoch after the upgrade",
        tables=(SpeciesTraitRow.__tablename__,),
        targets=("species", "region"),
        couplings=(
            Coupling(
                S.ECOLOGY,
                "prey grow faster and harder to see where hunters live, and hunters follow their prey's speed",
                EdgeKind.MODIFIER,
                "trait_evolution.predator_pressure",
            ),
            Coupling(
                S.ENVIRONMENT, "a land colder or warmer than a species likes moves its cold tolerance", EdgeKind.MODIFIER, "trait_evolution.climate_pressure"
            ),
            Coupling(S.ECONOMY, "hunted species grow wary and smaller", EdgeKind.MODIFIER, "trait_evolution.hunting_pressure"),
            Coupling(S.MAGIC, "a leaking land widens the spread of every trait", EdgeKind.MODIFIER, "trait_evolution.leak_variance"),
            Coupling(S.FAITH, "a species sacred to a god is spared part of selection", EdgeKind.MODIFIER, "trait_evolution.protection_relax_pct"),
            Coupling(
                S.ECOLOGY, "a range whose traits drift far from its kind splits off as a subspecies", EdgeKind.TRIGGER, "trait_evolution.speciation_distance"
            ),
        ),
    ),
    Mechanic(
        key="niches",
        spec_item="S3.2/RP3",
        title=(
            "Niches: species sharing a diet, a time of day and a size compete in each land until one is excluded "
            "or shifts, and survivors spread into niches extinction empties"
        ),
        subsystem=S.ECOLOGY,
        phases=("niches",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: niches are read from the traits of each range",
        tables=(SpeciesTraitRow.__tablename__,),
        targets=("species", "region"),
        couplings=(
            Coupling(S.ECOLOGY, "the weaker of two species in one niche loses numbers and may be excluded", EdgeKind.MODIFIER, "niches.exclusion_loss"),
            Coupling(S.ECOLOGY, "a losing species may shift its size instead", EdgeKind.TRIGGER, "niches.displacement_pct"),
            Coupling(S.ECOLOGY, "a niche emptied by extinction draws a surviving kin", EdgeKind.TRIGGER, "niches.radiation_pct"),
        ),
    ),
    Mechanic(
        key="trophic_flow",
        spec_item="S3.2/RP3",
        title="Trophic levels: the plants of a land bound its grazers, grazers bound hunters and hunters bound the apex, and a level above its bound starves",
        subsystem=S.ECOLOGY,
        phases=("trophic_flow",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: the levels are counted from the first epoch after the upgrade",
        tables=(TrophicLevelRow.__tablename__,),
        targets=("region", "species"),
        couplings=(
            Coupling(S.ENVIRONMENT, "forest, soil and wetland feed the first level", EdgeKind.FLOW, "trophic.efficiency_pct"),
            Coupling(S.ECOLOGY, "a level above its bound loses numbers", EdgeKind.MODIFIER, "trophic.collapse"),
        ),
    ),
    Mechanic(
        key="keystones",
        spec_item="S3.2/RP3",
        title=(
            "Keystone species: pollinators, soil-makers, dam-builders and scavengers give their lands "
            "harvest, soil, wetland and health, and their loss costs the land"
        ),
        subsystem=S.ECOLOGY,
        phases=("keystones", "environment_derive", "harvest"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: keystone roles are given by body and diet on the first epoch after the upgrade",
        tables=(EcosystemServiceRow.__tablename__,),
        fields=("keystone",),
        targets=("species", "region"),
        couplings=(
            Coupling(S.ECONOMY, "pollinators raise the harvest", EdgeKind.MODIFIER, "keystones.harvest_gain"),
            Coupling(S.ENVIRONMENT, "soil-makers enrich the soil", EdgeKind.FLOW, "keystones.soil_gain"),
            Coupling(S.ENVIRONMENT, "dam-builders hold wetland", EdgeKind.MODIFIER, "keystones.wetland_gain"),
            Coupling(S.BODY, "scavengers keep disease away", EdgeKind.MODIFIER, "keystones.disease_relief"),
            Coupling(S.ECONOMY, "a land that lost its keystone loses soil and harvest", EdgeKind.MODIFIER, "keystones.lost_decay"),
        ),
    ),
    Mechanic(
        key="feral_reversion",
        spec_item="S3.2/RP3",
        title="Feral herds: herds of fallen communities run loose, kept kinds step back toward the wild and become wild breeds of their own",
        subsystem=S.ECOLOGY,
        phases=("feral_reversion",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: herds of communities already gone go loose on the first epoch after the upgrade",
        fields=("feral_epoch",),
        targets=("species", *COMMUNITIES),
        couplings=(
            Coupling(S.ECOLOGY, "a loosed herd joins the wild numbers of its land", EdgeKind.FLOW, "feral.release_abundance"),
            Coupling(S.ECOLOGY, "a kept kind steps back toward the wild", EdgeKind.TRIGGER, "feral.revert_years"),
        ),
    ),
    Mechanic(
        key="lineages",
        spec_item="S3.2/RP3",
        title="Lineage marks: blessings of sacred species and taints of leaking lands pass to their young, their breeds and the beasts born of them",
        subsystem=S.ECOLOGY,
        phases=("lineages",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: lines are marked from the first epoch after the upgrade",
        tables=(LineageMarkRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("mark_lineage",),
        targets=("species", "beast", "son"),
        couplings=(
            Coupling(S.FAITH, "a species sacred to a god may be blessed down its line", EdgeKind.TRIGGER, "lineages.blessing_pct"),
            Coupling(S.MAGIC, "a species of a leaking land may be tainted down its line", EdgeKind.TRIGGER, "lineages.taint_pct"),
            Coupling(S.BODY, "beasts born of a marked line carry its blessing or taint", EdgeKind.FLOW, "lineages.taint_leak"),
        ),
    ),
    Mechanic(
        key="pathogen_evolution",
        spec_item="S3.4/RP3",
        title=(
            "Pathogen evolution: diseases grow milder among sparse folk, spread faster in crowds, resist "
            "treatment, escape immunity and fit the climate they live in"
        ),
        subsystem=S.BODY,
        phases=("pathogen_evolution", "epidemics"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: diseases begin at middling tolerance and no resistance",
        fields=("cold_tolerance", "heat_tolerance", "resistance"),
        targets=("disease",),
        couplings=(
            Coupling(S.DEMOGRAPHY, "sparse peoples breed milder strains and crowds faster ones", EdgeKind.MODIFIER, "pathogen_evolution.lethality_drop"),
            Coupling(S.KNOWLEDGE, "treatment breeds resistance that blunts cures and hospitals", EdgeKind.MODIFIER, "pathogen_evolution.resistance_pct"),
            Coupling(S.BODY, "wide immunity drives a disease to throw off a new strain", EdgeKind.TRIGGER, "pathogen_evolution.escape_pct"),
            Coupling(S.ENVIRONMENT, "a disease adapts to the cold or heat of the lands it spreads in", EdgeKind.MODIFIER, "pathogen_evolution.climate_step"),
        ),
    ),
    Mechanic(
        key="carriers",
        spec_item="S3.4/RP3",
        title="Carriers: named mortals carry a sickness unseen and seed it where they travel, until physicians who know contagion find them",
        subsystem=S.BODY,
        phases=("carriers",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: carriers appear from the first epoch after the upgrade",
        tables=(CarrierRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("find_carrier",),
        targets=("mortal", "disease"),
        couplings=(
            Coupling(S.DEMOGRAPHY, "a carrier who travels seeds an outbreak where it goes", EdgeKind.TRIGGER, "carriers.seed_pct"),
            Coupling(S.KNOWLEDGE, "a physician who knows contagion finds a carrier", EdgeKind.TRIGGER, "carriers.identify_skill"),
        ),
    ),
    Mechanic(
        key="spillover",
        spec_item="S3.4/RP3",
        title="Spillover: diseases of wild hosts jump to the folk of their land, more often where the land is cleared, the host hunted or herds graze",
        subsystem=S.BODY,
        phases=("spillover",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: hosts begin to pass their diseases on from the first epoch after the upgrade",
        targets=("species", "region", "disease"),
        couplings=(
            Coupling(S.ENVIRONMENT, "cleared land brings folk near the wild host", EdgeKind.MODIFIER, "spillover.cleared_pct"),
            Coupling(S.ECONOMY, "hunting the host brings its sickness home", EdgeKind.MODIFIER, "spillover.hunted_pct"),
            Coupling(S.ECOLOGY, "herds grazing among the host carry it over", EdgeKind.MODIFIER, "spillover.herd_pct"),
        ),
    ),
    Mechanic(
        key="plague_responses",
        spec_item="S3.4/RP3",
        title="Plague responses: communities close borders, quarantine, burn the dead, drive out the sick, pray or seek a cure, each with its price",
        subsystem=S.SOCIAL,
        phases=("plague_responses", "trade_flow", "epidemics"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: communities answer outbreaks from the first epoch after the upgrade",
        tables=(PlagueResponseRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("move_plague_response", "answer_sickness"),
        targets=(*COMMUNITIES, "disease", "son", "mortal"),
        couplings=(
            Coupling(S.ECONOMY, "closed borders cut the trade of the community's routes", EdgeKind.MODIFIER, "plague_responses.border_trade_pct"),
            Coupling(S.POLITY, "closed borders and quarantine riots unsettle the community", EdgeKind.MODIFIER, "plague_responses.riot_unrest"),
            Coupling(S.FAITH, "burning the dead grieves folk whose rites forbid it", EdgeKind.MODIFIER, "plague_responses.burn_cohesion"),
            Coupling(S.SOCIAL, "driving out the sick marks the disease with stigma", EdgeKind.MODIFIER, "plague_responses.expel_stigma"),
            Coupling(
                S.BODY,
                "quarantine, burning and expulsion slow the spread and prayer crowds speed it",
                EdgeKind.MODIFIER,
                "plague_responses.quarantine_spread_pct",
            ),
        ),
    ),
    Mechanic(
        key="vaccination",
        spec_item="S3.4/RP3",
        title="Variolation and vaccination: communities that know inoculation raise their immunity before a disease arrives, variolation at some risk",
        subsystem=S.BODY,
        phases=("vaccination",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: inoculating communities begin from the first epoch after the upgrade",
        targets=COMMUNITIES,
        couplings=(
            Coupling(S.KNOWLEDGE, "a true theory of contagion turns variolation into safe vaccination", EdgeKind.RULE_SWITCH, "vaccination.variolation_pct"),
            Coupling(S.DEMOGRAPHY, "variolation kills a few of those treated", EdgeKind.FLOW, "vaccination.risk_pct"),
        ),
    ),
    Mechanic(
        key="cure_research",
        spec_item="S3.4/RP3",
        title=(
            "Cure research: hospitals, academies and monasteries race for a cure with their scholars and "
            "specimens; the cure brings prestige and is sold along trade routes"
        ),
        subsystem=S.KNOWLEDGE,
        phases=("cure_research",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: institutions take up the search when an outbreak reaches their land",
        tables=(CureResearchRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("seek_cure",),
        targets=("structure", "disease", *COMMUNITIES, "mortal"),
        couplings=(
            Coupling(S.SOCIAL, "the community that finds a cure wins prestige", EdgeKind.MODIFIER, "cure_research.prestige"),
            Coupling(S.ECONOMY, "trade partners buy the cure for coin", EdgeKind.FLOW, "cure_research.price"),
            Coupling(S.KNOWLEDGE, "a true theory of contagion speeds the search", EdgeKind.MODIFIER, "cure_research.theory_pct"),
        ),
    ),
    Mechanic(
        key="biome_succession",
        spec_item="S6.1/RP3",
        title=(
            "Biome succession: lands move from bare ground through grass and shrub to young and old forest, or into "
            "marsh and swamp forest, and fire, grazing and farming push them back"
        ),
        subsystem=S.ENVIRONMENT,
        phases=("biome_succession", "environment_derive", "terrain_hazards"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: every land takes the stage its forest and wetland show",
        fields=("succession", "succession_progress", "burned_epoch"),
        targets=("region",),
        couplings=(
            Coupling(S.ENVIRONMENT, "each stage bounds the forest cover of its land", EdgeKind.MODIFIER, "biome_succession.rate"),
            Coupling(S.ENVIRONMENT, "dry woods long unburned catch fire", EdgeKind.TRIGGER, "biome_succession.fire_pct"),
            Coupling(S.ECONOMY, "heavy grazing holds grassland and farmers clear forest by fire", EdgeKind.MODIFIER, "biome_succession.grazing_hold"),
        ),
    ),
    Mechanic(
        key="land_shaping",
        spec_item="S6.1/RP3",
        title=(
            "Land shaping: gods raise and lower lands, carve and fill valleys, open springs, call lava and sink "
            "coasts, and the folk of the land hold them in awe or dread for it"
        ),
        subsystem=S.GODS,
        phases=("environment_survey",),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: a raised or lowered land keeps the height a god gives it",
        exposure=Exposure.TOOL,
        tools=("reshape_land",),
        levers=("land:reshape", "land:shape", "land:stir", "land:release"),
        targets=("region", "son", "creator"),
        couplings=(
            Coupling(S.ENVIRONMENT, "a raised or lowered land keeps its height and its climate follows", EdgeKind.MODIFIER, "land_shaping.step"),
            Coupling(S.COSMOS, "called lava wakes the world's fire", EdgeKind.FLOW, "land_shaping.lava_volcanism"),
            Coupling(
                S.FAITH, "folk lose awe for a god who drowns or burns their land and gain it for one who waters it", EdgeKind.MODIFIER, "land_shaping.awe_loss"
            ),
        ),
    ),
    Mechanic(
        key="world_cycles",
        spec_item="S10.9/RP3",
        title=(
            "World cycles: carbon, water and nutrients flow through each world from fire, forest, ocean, ice, "
            "ash, rivers and erosion, and set its warmth, rain, seas and soil"
        ),
        subsystem=S.COSMOS,
        phases=("world_cycles", "regional_climate", "environment_derive", "planetary_climate"),
        surface=Surface(drawer=EVOLUTION_SECTION),
        backfill=f"{MIGRATION}: every world starts its cycles in balance",
        tables=(WorldCycleRow.__tablename__,),
        targets=("world",),
        couplings=(
            Coupling(S.COSMOS, "the balance of the carbon cycle feeds the greenhouse warmth of the air", EdgeKind.FLOW, "world_cycles.forest_uptake"),
            Coupling(S.ENVIRONMENT, "free water swells the rain", EdgeKind.MODIFIER, "world_cycles.rain_pct"),
            Coupling(S.COSMOS, "free water raises the seas and drowns coasts", EdgeKind.FLOW, "world_cycles.sea_level"),
            Coupling(S.ECONOMY, "nutrients above balance enrich the soil", EdgeKind.MODIFIER, "world_cycles.fertility_pct"),
        ),
    ),
)
