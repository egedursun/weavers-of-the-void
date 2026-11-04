from aerona.db.tables.environment import StructureLeyRow
from aerona.engine.environment.battles import BATTLE_FIXUP
from aerona.engine.environment.ley_works import LEY_FIXUP
from aerona.engine.environment.works import WORKS_FIXUP
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface
from aerona.engine.lore.calendar_rites import HOLY_DAY_FIXUP

ENVIRONMENT = "section-environment"
SEASONS = "section-seasons"
S = Subsystem

COUPLING_MECHANICS = (
    Mechanic(
        key="yearly_variance",
        spec_item="F1",
        title="Sampled years under one budget: births, fires, mine hazards, disease seasons and market swings",
        subsystem=S.CORE,
        phases=("population_growth", "settlement_life", "resource_economy", "epidemics", "markets"),
        surface=Surface(drawer=SEASONS, chart="chart-market-swing"),
        backfill="none: earlier epochs keep the rolls they had; every yearly system shares the epoch's sampled years from the next epoch (K.2)",
        templates=("settlement.fire_wind",),
        fields=("population",),
        targets=("people", "settlement", "region"),
        couplings=(
            Coupling(S.DEMOGRAPHY, "births and deaths are lived year by year in the epoch's sampled years", EdgeKind.FLOW),
            Coupling(S.DEMOGRAPHY, "a wet, hot sickly season in a sampled year speeds spread and deaths", EdgeKind.MODIFIER, "seasonal.disease_wet_pct"),
            Coupling(S.ECONOMY, "a sampled year's lost growth lifts food prices; other goods swing", EdgeKind.MODIFIER, "seasonal.food_swing_pct"),
            Coupling(S.ENVIRONMENT, "the budget caps every sampled-year evaluation and counts what it extrapolates", EdgeKind.TRIGGER),
        ),
    ),
    Mechanic(
        key="season_traditions",
        spec_item="F2.2",
        title="Festivals bound to their season, dates fixed by a calendar, holy-day fasts and sleep customs under long days",
        subsystem=S.CULTURE,
        phases=("tradition_cycles", "calendars"),
        surface=Surface(drawer=SEASONS),
        backfill=f"{HOLY_DAY_FIXUP}: every holy day already kept founds its fast; traditions bind to their season at their next celebration",
        targets=("tradition", "people", "settlement", "knowledge"),
        exposure=Exposure.CONTEXT,
        couplings=(
            Coupling(
                S.ENVIRONMENT,
                "a feast kept in a season of plenty costs less food; out of season it counts for less",
                EdgeKind.MODIFIER,
                "seasonal.in_season_pct",
            ),
            Coupling(S.KNOWLEDGE, "a calendar fixes the date, so the tradition never drifts off its season", EdgeKind.MODIFIER, "seasonal.drift_chance"),
            Coupling(S.CULTURE, "a hungry year remembered on a holy day becomes a fast kept by the calendar's folk", EdgeKind.TRIGGER),
            Coupling(S.SOCIAL, "long days bring the midday rest (less unrest) or the night vigil (less crime)", EdgeKind.MODIFIER, "seasonal.long_day_hours"),
        ),
    ),
    Mechanic(
        key="weather_fire",
        spec_item="F2.3",
        title="Wind spreads fire; wet weather damps fires and fire rites",
        subsystem=S.ENVIRONMENT,
        phases=("settlement_life", "wizards"),
        surface=Surface(drawer=ENVIRONMENT),
        backfill="none: weather is drawn when a fire or a rite needs it",
        templates=("settlement.fire_wind",),
        targets=("settlement", "rite"),
        couplings=(
            Coupling(S.SOCIAL, "a gale makes a great fire burn more and kill more", EdgeKind.MODIFIER, "fire.wind_spread_pct"),
            Coupling(S.SOCIAL, "a wet year puts out fires before they start", EdgeKind.MODIFIER, "fire.wet_damp_pct"),
            Coupling(S.MAGIC, "fire rites lose strength under wet weather", EdgeKind.MODIFIER, "rites.fire_wet_pct"),
        ),
    ),
    Mechanic(
        key="typed_works",
        spec_item="F2.4",
        title="Irrigation works and bridges feed fertility and passability; cleared forest dries the rains",
        subsystem=S.ENVIRONMENT,
        phases=("settlement_life", "environment_survey", "environment_derive"),
        surface=Surface(drawer=ENVIRONMENT),
        backfill=f"{WORKS_FIXUP}: bridge and harbour structures become works of their settlement; settlements that already irrigated keep irrigation works",
        fields=("fertility",),
        targets=("settlement", "region"),
        exposure=Exposure.CONTEXT,
        couplings=(
            Coupling(S.ECONOMY, "each level of irrigation works lifts the fertility of river land", EdgeKind.MODIFIER, "environment.irrigation_works_pct"),
            Coupling(S.ECONOMY, "bridges ease river crossings for traders and armies", EdgeKind.MODIFIER, "passability.bridge_crossing_pct"),
            Coupling(S.ECOLOGY, "clearing the forest takes rain from the land", EdgeKind.MODIFIER, "environment.forest_rain_pct"),
        ),
    ),
    Mechanic(
        key="ley_attunement",
        spec_item="F2.6",
        title="Works that channel the ley gain function on a line and more at a nexus",
        subsystem=S.MAGIC,
        phases=("ley_lines",),
        surface=Surface(drawer=ENVIRONMENT, layer="map-layer-ley"),
        backfill=f"{LEY_FIXUP}: temples, observatories, towers, gates and shrines already standing are recorded as channelling the ley",
        fields=("function",),
        tables=(StructureLeyRow.__tablename__,),
        targets=("structure",),
        couplings=(Coupling(S.MAGIC, "an attuned work on a live line gains function each epoch", EdgeKind.MODIFIER, "environment.ley_function_gain"),),
    ),
    Mechanic(
        key="battle_ground_record",
        spec_item="F1",
        title="Every recorded battle carries its year, season, weather and ground",
        subsystem=S.WAR,
        phases=("environment_survey",),
        surface=Surface(drawer=SEASONS),
        backfill=f"{BATTLE_FIXUP}: historical battles get terrain and season from their place and year",
        targets=("army",),
        couplings=(Coupling(S.ENVIRONMENT, "the ground and the year's weather are written into the record of each battle", EdgeKind.TRIGGER),),
    ),
)
