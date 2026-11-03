import inspect
import re
import sys

from aerona.db.tables.body import BodyCustomRow, BodyRow, ConditionRow, InjuryRow, MaimedCohortRow, ProsthesisRow
from aerona.db.tables.environment import CalendarRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.domain.enums.body import ConditionKind, InjuryKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.interconnect.registry import MECHANICS, Coupling, Exposure, Mechanic, Subsystem, Surface, register
from aerona.engine.phase import Phase
from aerona.engine.pipeline import PHASE_REGISTRY

MECHANICS_SECTION = "section-mechanics"
ENVIRONMENT_SECTION = "section-environment"
SEASONS_SECTION = "section-seasons"
BODY_SECTION = "section-body"
MAIMED_SECTION = "section-maimed"
CUSTOMS_SECTION = "section-body-customs"

BUILT_IN = (
    Mechanic(
        key="modifiers",
        spec_item="F9",
        title="Modifier bus",
        subsystem=Subsystem.CORE,
        phases=("modifier_upkeep",),
        surface=Surface(drawer=MECHANICS_SECTION),
        backfill="none: modifiers start empty",
        tables=(ModifierRow.__tablename__,),
        couplings=tuple(Coupling(subsystem, "typed modifiers on stats and capacities") for subsystem in Subsystem if subsystem is not Subsystem.CORE),
    ),
    Mechanic(
        key="incidents",
        spec_item="F10",
        title="Causality log",
        subsystem=Subsystem.CORE,
        phases=(),
        surface=Surface(drawer=MECHANICS_SECTION),
        backfill="migration 26caa21842b3: incidents from chronicle rows",
        templates=("chronicle template keys",),
        tables=(IncidentRow.__tablename__, IncidentParticipantRow.__tablename__),
    ),
    Mechanic(
        key="levies",
        spec_item="F28",
        title="Levies and demobilisation",
        targets=("people", "settlement", "cult", "army"),
        subsystem=Subsystem.WAR,
        phases=("war_upkeep", "campaigns"),
        surface=Surface(drawer=MECHANICS_SECTION),
        backfill="none: armies already raised keep their soldiers",
        fields=("population", "followers"),
        flows=("population -> army size", "army size -> population"),
        couplings=(Coupling(Subsystem.DEMOGRAPHY, "soldiers leave and return to their community"),),
    ),
    Mechanic(
        key="sub_clocks",
        spec_item="F1",
        title="Sampled years, campaign seasons and notable years",
        subsystem=Subsystem.CORE,
        phases=("harvest", "campaigns"),
        surface=Surface(drawer=SEASONS_SECTION),
        backfill="none: earlier epochs keep their single roll; sub-clocks run from the next epoch (K.2)",
        templates=("environment.notable_year.hunger", "environment.notable_year.plenty", "environment.notable_year.weather"),
        tables=(NotableYearRow.__tablename__,),
        targets=("region", "army"),
        couplings=(
            Coupling(Subsystem.WAR, "each war lives through campaign seasons with a real season, year and weather"),
            Coupling(Subsystem.ECONOMY, "the epoch's harvest is the mean of its sampled years"),
            Coupling(Subsystem.CULTURE, "hungry years become famine records, remembered and fasted for"),
        ),
    ),
    Mechanic(
        key="region_environment",
        spec_item="F2.1",
        title="Region and place environment",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("environment_survey", "environment_derive"),
        surface=Surface(drawer=ENVIRONMENT_SECTION),
        backfill="environment_survey: every region is profiled from its stored map; soil is solved so the derived fertility equals the stored stat",
        fields=("fertility", "danger"),
        tables=(RegionEnvironmentRow.__tablename__, PlaceEnvironmentRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("region", "place"),
        couplings=(
            Coupling(Subsystem.WAR, "defensibility, chokepoints, height advantage and battlefield scars"),
            Coupling(Subsystem.DEMOGRAPHY, "water sources and passability shape capacity and migration"),
            Coupling(Subsystem.ECONOMY, "mineral seams feed resources; route ease feeds trade"),
            Coupling(Subsystem.ECOLOGY, "wild land carries wild species"),
            Coupling(Subsystem.MAGIC, "magic density draws magic storms"),
            Coupling(Subsystem.COSMOS, "the leak tears wounds into the land"),
        ),
    ),
    Mechanic(
        key="world_seasons",
        spec_item="F2.2",
        title="World seasons and calendars",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("environment_survey", "calendars"),
        surface=Surface(drawer=SEASONS_SECTION),
        backfill="environment_survey: tilt, year, day, moons and seasons are generated for every world from its seed and orbit",
        templates=("environment.calendar_adopted", "tools.son.reorder_seasons"),
        tables=(WorldSeasonRow.__tablename__, CalendarRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("reorder_seasons",),
        targets=("knowledge",),
        couplings=(
            Coupling(Subsystem.WAR, "season fitness for war"),
            Coupling(Subsystem.ECONOMY, "season growth and travel"),
            Coupling(Subsystem.KNOWLEDGE, "astronomy records keep calendars that plan the harvest"),
            Coupling(Subsystem.CULTURE, "calendars keep fasts for hungry years"),
            Coupling(Subsystem.COSMOS, "moons raise tides and eclipses"),
        ),
    ),
    Mechanic(
        key="weather",
        spec_item="F2.3",
        title="Weather on demand",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("harvest", "campaigns", "travel"),
        surface=Surface(drawer=ENVIRONMENT_SECTION),
        backfill="none: weather is drawn when a mechanic needs it and never stored",
        targets=("region", "army"),
        couplings=(
            Coupling(Subsystem.WAR, "footing, visibility, cold, heat and camp fever in every campaign season"),
            Coupling(Subsystem.GODS, "omens read through the patron god's domains"),
            Coupling(Subsystem.ECONOMY, "growth of the sampled year's harvest"),
            Coupling(Subsystem.COSMOS, "wind at departure endangers journeys"),
        ),
    ),
    Mechanic(
        key="derived_environment",
        spec_item="F2.4",
        title="Derived fertility, harvest and passability",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("environment_derive", "harvest", "society_economy"),
        surface=Surface(drawer=ENVIRONMENT_SECTION),
        backfill="environment_survey: fertility is kept as it was and its soil solved backwards",
        fields=("fertility",),
        targets=("region", "place", "people", "settlement"),
        couplings=(
            Coupling(Subsystem.ECONOMY, "food production follows the harvest"),
            Coupling(Subsystem.DEMOGRAPHY, "carrying capacity follows fertility"),
        ),
    ),
    Mechanic(
        key="ley_lines",
        spec_item="F2.6",
        title="Ley lines and magic geography",
        subsystem=Subsystem.MAGIC,
        phases=("ley_lines", "magic_storms", "wizards"),
        surface=Surface(drawer=ENVIRONMENT_SECTION),
        backfill="ley_lines: lines and nexus are woven from the existing magic of neighbouring regions on the first run",
        templates=("environment.ley_line_formed", "environment.nexus_formed", "tools.son.sever_ley"),
        fields=("function",),
        tables=(LeyLineRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("sever_ley",),
        targets=("region", "place", "structure"),
        couplings=(
            Coupling(Subsystem.ENVIRONMENT, "ley convergence raises magic density; salted earth and leak wounds cut lines"),
            Coupling(Subsystem.CULTURE, "works standing on ley lines and nexus gain function"),
            Coupling(Subsystem.MAGIC, "magic storms run down the lines; wizards on a line act more often"),
        ),
    ),
    Mechanic(
        key="land_use",
        spec_item="F2.5",
        title="Land use and ecological pressure",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("land_use", "resource_economy"),
        surface=Surface(drawer=ENVIRONMENT_SECTION),
        backfill="environment_survey: inhabited regions start at the land use their people already need",
        targets=("region",),
        couplings=(
            Coupling(Subsystem.ECOLOGY, "clearing shrinks wild land"),
            Coupling(Subsystem.ECONOMY, "erosion and overfarming wear out the soil"),
            Coupling(Subsystem.DEMOGRAPHY, "building and crowding raise disease"),
        ),
    ),
    Mechanic(
        key="anatomy",
        spec_item="F4.1",
        title="Body plans",
        subsystem=Subsystem.BODY,
        phases=("body_survey",),
        surface=Surface(drawer=BODY_SECTION),
        backfill="body_survey: every mortal, son and foreign god gets the body plan of their species, or a humanoid or divine body",
        fields=("plan", "traits", "fingers"),
        tables=(BodyRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("mortal", "species", "son", "foreign_god"),
        couplings=(Coupling(Subsystem.ECOLOGY, "a species' traits add wings, venom glands, horns and tails"),),
    ),
    Mechanic(
        key="injuries",
        spec_item="F4.2",
        title="Typed injuries on body parts",
        subsystem=Subsystem.BODY,
        phases=("disaster_casualties", "natural_disasters", "curse_decay", "cursed_items", "glory_hunts", "heroes"),
        surface=Surface(drawer=BODY_SECTION),
        backfill="body_survey: mortals who fell in battle, siege, captivity or disaster before bodies existed get one fatal wound; others start unhurt",
        templates=tuple(f"injury.{kind.value}" for kind in InjuryKind),
        fields=("part", "kind", "severity", "state", "function_loss", "visible"),
        tables=(InjuryRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("mortal", "son", "foreign_god"),
        couplings=(
            Coupling(Subsystem.WAR, "battles, duels and sieges wound by weapon mix and armour cover"),
            Coupling(Subsystem.GODS, "sons and foreign gods carry divine wounds from their trials and wars"),
        ),
    ),
    Mechanic(
        key="hits",
        spec_item="F4.3",
        title="From weapons to injuries",
        subsystem=Subsystem.BODY,
        phases=("campaigns",),
        surface=Surface(drawer=BODY_SECTION),
        backfill="none: armour cover is read from the people's metallurgy and the armour each bearer owns",
        fields=("armour_head", "armour_torso", "armour_limbs"),
        tables=(BodyRow.__tablename__,),
        targets=("mortal", "son", "foreign_god"),
        couplings=(
            Coupling(Subsystem.KNOWLEDGE, "metallurgy gives helmets; a people without them breeds one-eyed veterans"),
            Coupling(Subsystem.ECOLOGY, "flying beasts strike heads, giants trample legs"),
        ),
    ),
    Mechanic(
        key="healing",
        spec_item="F4.4",
        title="Healing, infection and death from wounds",
        subsystem=Subsystem.BODY,
        phases=("body_healing", "mortal_wounds"),
        surface=Surface(drawer=BODY_SECTION),
        backfill="none: open wounds begin healing on the next epoch",
        templates=("healing.amputated", "healing.reattached", "healing.prosthesis"),
        fields=("hp_max", "patients_healed", "patients_lost"),
        tables=(InjuryRow.__tablename__, ProsthesisRow.__tablename__),
        targets=("mortal", "son", "foreign_god"),
        couplings=(
            Coupling(Subsystem.ENVIRONMENT, "the region's disease load makes wounds fester"),
            Coupling(Subsystem.KNOWLEDGE, "medicine brings herbs, surgery, prosthetics and reattachment"),
            Coupling(Subsystem.SOCIAL, "wounded notables seek the best healer within reach and bind to them"),
        ),
    ),
    Mechanic(
        key="conditions",
        spec_item="F4.5",
        title="Permanent conditions and derived capacities",
        subsystem=Subsystem.BODY,
        phases=("body_conditions",),
        surface=Surface(drawer=BODY_SECTION),
        backfill="body_conditions: the chosen gain their mark; other conditions arise from play",
        templates=tuple(f"condition.gained.{kind.value}" for kind in ConditionKind),
        fields=("melee", "missile", "command", "craft", "scholarship", "presence", "mobility", "fertility", "pain"),
        tables=(ConditionRow.__tablename__, BodyRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("mortal", "son", "foreign_god"),
        couplings=(
            Coupling(Subsystem.WAR, "melee, command and mobility drive duels, commanders, hunts and escapes"),
            Coupling(Subsystem.CULTURE, "craft and scholarship drive making, teaching and sensing hidden roads"),
            Coupling(Subsystem.DEMOGRAPHY, "fertility shapes the children of couples"),
            Coupling(Subsystem.FAITH, "presence shapes preaching; madness, possession and void taint follow sanity and spirits"),
        ),
    ),
    Mechanic(
        key="body_customs",
        spec_item="F4.5",
        title="How a people reads scars and missing parts",
        subsystem=Subsystem.CULTURE,
        phases=("body_society",),
        surface=Surface(drawer=CUSTOMS_SECTION),
        backfill="body_survey: each people's reading comes from its patron's domains and its martiality",
        templates=("body.ruler_set_aside", "body.maimed_cult"),
        fields=("reading", "wholeness_required", "seer_eye", "scar_festivals", "pension"),
        tables=(BodyCustomRow.__tablename__,),
        targets=("people",),
        couplings=(
            Coupling(Subsystem.POLITY, "a people that demands wholeness sets aside a maimed ruler"),
            Coupling(Subsystem.FAITH, "cults that sanctify suffering take in the maimed"),
        ),
    ),
    Mechanic(
        key="maimed_cohorts",
        spec_item="F4.5",
        title="The maimed as a population",
        subsystem=Subsystem.DEMOGRAPHY,
        phases=("body_society", "couple_births"),
        surface=Surface(drawer=MAIMED_SECTION),
        backfill="none: cohorts start empty and fill from the soldiers of later battles",
        templates=("cohort.scar_festival",),
        fields=("count", "veterans"),
        tables=(MaimedCohortRow.__tablename__,),
        targets=("settlement", "people"),
        couplings=(
            Coupling(Subsystem.ECONOMY, "the maimed lower food and craft output and drain prosperity without a pension"),
            Coupling(Subsystem.WAR, "a maimed people grows wary of new wars; a martial one holds scar festivals"),
            Coupling(Subsystem.SOCIAL, "the maimed raise the birth of healers"),
        ),
    ),
)

MODULE_SUBSYSTEMS: dict[str, Subsystem] = {
    "warfare": Subsystem.WAR,
    "casualties": Subsystem.WAR,
    "prisoners": Subsystem.WAR,
    "tribute": Subsystem.WAR,
    "grudges": Subsystem.WAR,
    "espionage": Subsystem.INTRIGUE,
    "diplomacy": Subsystem.POLITY,
    "factions": Subsystem.POLITY,
    "institutions": Subsystem.POLITY,
    "civilization": Subsystem.POLITY,
    "dark_ages": Subsystem.POLITY,
    "world_age": Subsystem.POLITY,
    "births": Subsystem.DEMOGRAPHY,
    "mortals": Subsystem.DEMOGRAPHY,
    "life_cycles": Subsystem.DEMOGRAPHY,
    "heroes": Subsystem.DEMOGRAPHY,
    "heroism": Subsystem.DEMOGRAPHY,
    "living_stats": Subsystem.DEMOGRAPHY,
    "population": Subsystem.DEMOGRAPHY,
    "migration": Subsystem.DEMOGRAPHY,
    "refugees": Subsystem.DEMOGRAPHY,
    "settlements": Subsystem.DEMOGRAPHY,
    "ruins": Subsystem.DEMOGRAPHY,
    "society": Subsystem.ECONOMY,
    "society_economy": Subsystem.ECONOMY,
    "market": Subsystem.ECONOMY,
    "trade": Subsystem.ECONOMY,
    "prosperity": Subsystem.ECONOMY,
    "resources": Subsystem.ECONOMY,
    "environment": Subsystem.ENVIRONMENT,
    "economy": Subsystem.ECONOMY,
    "cosmic_economy": Subsystem.ECONOMY,
    "mechanics_assignment": Subsystem.ECONOMY,
    "religion_spread": Subsystem.FAITH,
    "native_faith": Subsystem.FAITH,
    "belief_memory": Subsystem.FAITH,
    "pantheon": Subsystem.FAITH,
    "afterlife": Subsystem.FAITH,
    "spirits": Subsystem.FAITH,
    "remembrance": Subsystem.CULTURE,
    "culture_exchange": Subsystem.CULTURE,
    "works": Subsystem.CULTURE,
    "wonders": Subsystem.CULTURE,
    "knowledge_levels": Subsystem.KNOWLEDGE,
    "writing": Subsystem.KNOWLEDGE,
    "language_contact": Subsystem.LANGUAGE,
    "language_death": Subsystem.LANGUAGE,
    "dialects": Subsystem.LANGUAGE,
    "creatures": Subsystem.ECOLOGY,
    "monsters": Subsystem.ECOLOGY,
    "ecology": Subsystem.ECOLOGY,
    "life_seed": Subsystem.ECOLOGY,
    "climate": Subsystem.ENVIRONMENT,
    "disasters": Subsystem.ENVIRONMENT,
    "geography": Subsystem.ENVIRONMENT,
    "sky": Subsystem.ENVIRONMENT,
    "magic": Subsystem.MAGIC,
    "curses": Subsystem.MAGIC,
    "horror": Subsystem.MAGIC,
    "sons": Subsystem.GODS,
    "god_power": Subsystem.GODS,
    "god_death": Subsystem.GODS,
    "creator_mood": Subsystem.GODS,
    "reputation": Subsystem.GODS,
    "goals": Subsystem.GODS,
    "travel": Subsystem.COSMOS,
    "exploration": Subsystem.COSMOS,
    "cosmos_upkeep": Subsystem.COSMOS,
    "doom": Subsystem.COSMOS,
    "world_balance": Subsystem.COSMOS,
}
PACKAGE_SUBSYSTEMS: dict[str, Subsystem] = {"gods": Subsystem.GODS, "cosmos": Subsystem.COSMOS, "lifecycle": Subsystem.DEMOGRAPHY}
EXISTING_BACKFILL = "existing mechanic: its state is already in the world"


def subsystem_of(module: str) -> Subsystem:
    parts = module.split(".")
    if parts[-1] in MODULE_SUBSYSTEMS:
        return MODULE_SUBSYSTEMS[parts[-1]]
    return next((PACKAGE_SUBSYSTEMS[part] for part in parts if part in PACKAGE_SUBSYSTEMS), Subsystem.CORE)


ENTITY_TYPE_TOKEN = re.compile(r"\bEntityType\.([A-Z_]+)\b")


def targets_of(module: str) -> tuple[str, ...]:
    source = inspect.getsource(sys.modules[module])
    names = {EntityType[name].value for name in ENTITY_TYPE_TOKEN.findall(source) if name in EntityType.__members__}
    return tuple(sorted(names))


def existing_mechanic(phase: Phase) -> Mechanic:
    return Mechanic(
        key=phase.name,
        spec_item="J.16c",
        title=phase.name.replace("_", " ").capitalize(),
        subsystem=subsystem_of(phase.run.__module__),
        phases=(phase.name,),
        surface=Surface(drawer=MECHANICS_SECTION),
        backfill=EXISTING_BACKFILL,
        targets=targets_of(phase.run.__module__),
    )


for mechanic in BUILT_IN:
    register(mechanic)
CLAIMED = {phase for mechanic in BUILT_IN for phase in mechanic.phases}
for phase in PHASE_REGISTRY.values():
    if phase.name not in CLAIMED:
        register(existing_mechanic(phase))

REGISTERED = MECHANICS
