from aerona.db.tables.body_systems import BodySystemRow, SensitivityRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.tables.plants import PlantAnatomyRow, PlantPartRow
from aerona.db.tables.space_weather import SpaceWeatherEventRow, StarActivityRow, WorldFieldRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.tables.water import CoastRow, LocalClimateRow, RegionCryosphereRow, SedimentFlowRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind

NATURE50_MECHANICS = (
    Mechanic(
        key="facets",
        spec_item="S50.16",
        title=(
            "Practices: every practice a community keeps follows what it knows, holds and "
            "has built, and acts on its order, health, wealth, learning and defence"
        ),
        subsystem=S.CULTURE,
        phases=("facets",),
        surface=Surface(drawer="section-practices"),
        backfill="facets: every community gains its practices from its sources on its first epoch",
        templates=("facets.",),
        tables=(FacetPracticeRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("shape_folk",),
        levers=("facet_practice:create",),
        targets=("people", "settlement"),
        couplings=(
            Coupling(S.SOCIAL, "practices move a town's order, crime, unrest and sanitation", E.MODIFIER, "facets.channel_cap"),
            Coupling(S.ECONOMY, "practices move a community's prosperity and wealth", E.MODIFIER, "facets.effect_pct"),
            Coupling(S.KNOWLEDGE, "practices of learning feed a community's research", E.MODIFIER, "facets.effect_pct"),
            Coupling(S.BODY, "practices of care and medicine ease the outbreaks of a community's land", E.MODIFIER, "facets.effect_pct"),
        ),
    ),
    Mechanic(
        key="space_weather",
        spec_item="S50.22",
        title="Space weather: stars turn through their cycles and send flares and storms, fields reverse, and worlds take what their shields let through",
        subsystem=S.COSMOS,
        phases=("space_weather",),
        surface=Surface(drawer="section-space-weather"),
        backfill="space_weather: every world gains its field from its magnetism and air, every star its cycle from its stability and radiation",
        templates=(
            "sky.flare",
            "sky.particle_storm",
            "sky.field_storm",
            "sky.field_reversal",
            "sky.cosmic_ray_burst",
            "sky.wind_surge",
            "sky.outage",
            "sky.aurora_spread",
        ),
        tables=(WorldFieldRow.__tablename__, StarActivityRow.__tablename__, SpaceWeatherEventRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("shield_world",),
        levers=("world_field:create", "star_activity:create", "space_weather_event:create"),
        targets=("world", "star", "mortal", "settlement", "species"),
        couplings=(
            Coupling(S.BODY, "a dose past the outage threshold harms mortals outside shelter", E.MODIFIER, "space_weather.dose_harm_per_point"),
            Coupling(S.COMMUNICATION, "a strong dose silences the networks of the world", E.TRIGGER, "space_weather.outage_threshold"),
            Coupling(S.ECOLOGY, "the dose raises the mutation of the world's kinds of life", E.MODIFIER, "space_weather.mutation_per_dose_pct"),
            Coupling(S.ECONOMY, "a compass that errs loses its pilots their way", E.MODIFIER, "space_weather.compass_error_threshold"),
            Coupling(S.FAITH, "a field reversal or a great aurora is read as an omen", E.MODIFIER, "space_weather.omen_piety"),
            Coupling(S.ECONOMY, "an extreme dose stresses the world's harvests", E.MODIFIER, "space_weather.crop_loss"),
        ),
    ),
    Mechanic(
        key="water_and_ice",
        spec_item="S50.23",
        title=(
            "Water, ice and sediment: ice comes and goes, snow melts into rivers, sediment builds "
            "deltas and silts harbours, coasts build or wear and towns warm their own air"
        ),
        subsystem=S.ENVIRONMENT,
        phases=("water_and_ice",),
        surface=Surface(drawer="section-water-and-ice"),
        backfill="water_and_ice: every land gains its ice, coast and sediment flows from its warmth, terrain, rivers and coast",
        templates=("land.",),
        tables=(RegionCryosphereRow.__tablename__, SedimentFlowRow.__tablename__, CoastRow.__tablename__, LocalClimateRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("dredge", "move_ice"),
        levers=("region_cryosphere:create", "sediment_flow:create", "coast:create", "local_climate:create"),
        targets=("region", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "ice closes river and sea roads for its months", E.MODIFIER, "water_and_ice.ice_route_block_months"),
            Coupling(S.ECONOMY, "a silted harbour costs its town prosperity", E.MODIFIER, "water_and_ice.silted_loss"),
            Coupling(S.ECOLOGY, "a growing delta enriches its land's soil", E.MODIFIER, "water_and_ice.delta_fertility"),
            Coupling(S.BODY, "crowded hot towns feed the outbreaks of their land", E.MODIFIER, "water_and_ice.heat_outbreak"),
            Coupling(S.KNOWLEDGE, "a thaw gives up the frozen beds of remains", E.TRIGGER, "water_and_ice.thaw_step"),
        ),
    ),
    Mechanic(
        key="disease_agents",
        spec_item="S50.24",
        title="Agents of disease: what a disease is decides which cures work, where it survives and how fast it changes",
        subsystem=S.BODY,
        phases=("disease_agents",),
        surface=Surface(drawer="section-disease-agents"),
        backfill="disease_agents: every disease gains its agent from its vector, design and host",
        templates=("disease.",),
        tables=(DiseaseAgentRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("answer_sickness", "seek_cure"),
        levers=("disease_agent:create",),
        targets=("disease", "people", "settlement"),
        couplings=(
            Coupling(S.FAITH, "a cure that fails costs a community's healers trust", E.MODIFIER, "disease.wrong_cure_trust_loss"),
            Coupling(S.KNOWLEDGE, "healers of enough medicine learn what a disease is", E.TRIGGER, "disease.identify_level"),
            Coupling(S.ECOLOGY, "a reservoir kind or soil keeps a disease in its land", E.TRIGGER, "disease.linger_load"),
            Coupling(S.BODY, "an overused cure breeds resistance", E.MODIFIER, "disease.resistance_per_overuse"),
        ),
    ),
    Mechanic(
        key="body_systems",
        spec_item="S50.25",
        title="Body systems and sensitivities: what each body bears decides where its people can live and what it cannot meet",
        subsystem=S.BODY,
        phases=("body_systems",),
        surface=Surface(drawer="section-body-systems"),
        backfill="body_systems: every biology gains its systems from its body, its breath and its world",
        templates=("body.tolerance_exceeded", "body.system_failed", "body.system_recovered", "body.adapted", "body.sensitivity_reaction"),
        tables=(BodySystemRow.__tablename__, SensitivityRow.__tablename__),
        levers=("body_system:create", "sensitivity:create"),
        targets=("people", "species", "mortal", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "a world past what a people bears weighs on its towns", E.MODIFIER, "body_systems.tolerance_harm_per_point"),
            Coupling(
                S.DEMOGRAPHY, "a colony is not founded where its settlers' bodies cannot bear the world", E.TRIGGER, "body_systems.system_loss_capacity_pct"
            ),
            Coupling(S.BODY, "a being meets what it is sensitive to and falls ill", E.TRIGGER, "body_systems.sensitivity_reaction_pct"),
        ),
    ),
    Mechanic(
        key="plant_bodies",
        spec_item="S50.26",
        title="Plant bodies: a plant's form and parts give its goods, expose it to storm and fire and carry its seeds",
        subsystem=S.ECOLOGY,
        phases=("plant_bodies",),
        surface=Surface(drawer="section-plant-bodies"),
        backfill="plant_bodies: every plant gains its body from its class and growth cycle, and its goods from its parts",
        templates=("life.plant_spread", "life.plant_invaded", "life.plant_domesticated"),
        tables=(PlantAnatomyRow.__tablename__, PlantPartRow.__tablename__),
        levers=("plant_anatomy:create", "plant_part:create"),
        targets=("species", "region"),
        couplings=(
            Coupling(S.ECONOMY, "a plant's parts become the goods its people gather", E.FLOW, "plants.spread_abundance"),
            Coupling(S.ENVIRONMENT, "storms lay down tall forms and fires burn low ones", E.MODIFIER, "plants.storm_damage_tree_pct"),
            Coupling(S.ECOLOGY, "an invading plant crowds out what grows in its new land", E.MODIFIER, "plants.invasion_loss"),
        ),
    ),
    Mechanic(
        key="forecasting",
        spec_item="S50.28",
        title="Forecasts and weather works: peoples foresee hard seasons by their ways, and weather works turn a land's sky at the cost of the land downwind",
        subsystem=S.ENVIRONMENT,
        phases=("forecasting",),
        surface=Surface(drawer="section-forecasting"),
        backfill="forecasting: every people gains its ways from its weather lore, astronomy and writing",
        templates=("weather.",),
        tables=(ObservationMethodRow.__tablename__, WeatherWorkRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("forecast", "work_weather"),
        levers=("observation_method:create", "weather_work:create"),
        targets=("people", "region", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "a foreseen hard season costs its towns less", E.MODIFIER, "forecasting.kept_refund"),
            Coupling(S.FAITH, "a faithful people does not believe instruments, observers or models", E.TRIGGER, "forecasting.ignore_piety"),
            Coupling(S.POLITY, "a weather work that harms the land downwind turns its folk against the worker", E.MODIFIER, "forecasting.grievance"),
            Coupling(S.ECONOMY, "a people's reading of sky and weather sharpens its pilots", E.MODIFIER, "forecasting.navigation_share_pct"),
        ),
    ),
    Mechanic(
        key="hypocrisy",
        spec_item="S50.29",
        title="Professed values: the gap between what beings profess and what they do comes out and costs trust and following",
        subsystem=S.SOCIAL,
        phases=("hypocrisy",),
        surface=Surface(drawer="section-professions"),
        backfill="hypocrisy: beings profess their strong values the first time they act",
        templates=("standing.",),
        tables=(ProfessionOfValueRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("expose_hypocrisy",),
        levers=("profession_of_value:create",),
        targets=("mortal", "people", "polity", "faction", "cult", "son", "foreign_god", "creator"),
        couplings=(
            Coupling(S.MIND, "an act against a professed value widens the gap", E.MODIFIER, "standing.gap_per_act"),
            Coupling(S.POLITY, "an exposed gap costs legitimacy and renown", E.MODIFIER, "standing.hypocrisy_trust_loss"),
            Coupling(S.FAITH, "an exposed leader loses followers", E.MODIFIER, "standing.hypocrisy_follower_loss_pct"),
        ),
    ),
)
