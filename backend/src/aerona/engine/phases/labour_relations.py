from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.labour.tend import tend_labour
from aerona.engine.phase import Phase


@reads(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.community_labour",
    "table.community_society",
    "table.company_profiles",
    "table.entities",
    "table.faction_profiles",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.labour_contracts",
    "table.labour_disputes",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mind_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.state_changes",
    "table.worker_bodies",
    "table.workshops",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.faction_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.labour_contracts",
    "table.labour_disputes",
    "table.name_registry",
    "table.node_births",
    "table.worker_bodies",
)
async def labour_relations(ctx: TickContext) -> None:
    for key, value in asdict(await tend_labour(ctx)).items():
        ctx.count(f"labour_{key}", value)


PHASES = (Phase("labour_relations", labour_relations),)
