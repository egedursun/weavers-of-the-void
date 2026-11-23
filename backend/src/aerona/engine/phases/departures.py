from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.departures.tend import tend_departures
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "mortal.age",
    "table.bonds",
    "table.crime_cases",
    "table.departures",
    "table.designated_heirs",
    "table.entities",
    "table.house_members",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.org_governance",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.vassalages",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.departures",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.office_history",
    "table.offices",
    "table.org_governance",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def departures(ctx: TickContext) -> None:
    for key, value in asdict(await tend_departures(ctx)).items():
        ctx.count(f"departures_{key}", value)


PHASES = (Phase("departures", departures),)
