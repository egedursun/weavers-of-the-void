from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.occupation_regime.tend import tend_regimes
from aerona.engine.phase import Phase


@reads(
    "people.wealth",
    "table.collaborations",
    "table.node_births",
    "table.occupation_measures",
    "table.occupation_regimes",
    "table.occupations",
    "table.polity_members",
    "table.polity_territories",
)
@writes(
    "people.wealth",
    "table.applied_fixups",
    "table.captive_cohorts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collaborations",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.occupation_measures",
    "table.occupation_regimes",
    "table.occupations",
    "table.polity_profiles",
)
async def occupation_regimes(ctx: TickContext) -> None:
    for key, value in asdict(await tend_regimes(ctx)).items():
        ctx.count(f"occupation_regimes_{key}", value)


PHASES = (Phase("occupation_regimes", occupation_regimes),)
