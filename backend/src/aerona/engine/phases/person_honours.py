from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.honours.persons import tend_person_honours
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.deeds",
    "table.entities",
    "table.faction_profiles",
    "table.honour_kinds",
    "table.honours_held",
    "table.node_births",
    "table.nodes",
    "table.org_governance",
    "table.polity_profiles",
    "table.traits",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.honour_kinds",
    "table.honours_held",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
)
async def person_honours(ctx: TickContext) -> None:
    for key, value in asdict(await tend_person_honours(ctx)).items():
        ctx.count(f"person_honours_{key}", value)


PHASES = (Phase("person_honours", person_honours),)
