import inspect
import re
import sys

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.interconnect.registry import MECHANICS, Coupling, Mechanic, Subsystem, Surface, register
from aerona.engine.phase import Phase
from aerona.engine.pipeline import PHASE_REGISTRY

MECHANICS_SECTION = "section-mechanics"

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
