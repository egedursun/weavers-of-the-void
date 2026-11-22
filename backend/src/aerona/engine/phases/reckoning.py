from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.reckoning.tend import tend_reckonings


@reads(
    "table.collaborations",
    "table.collection_members",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.leader_cults",
    "table.node_births",
    "table.offices",
    "table.reckoning_cases",
    "table.reckoning_measures",
    "table.reckonings",
)
@writes(
    "table.accounts",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.offices",
    "table.polity_profiles",
    "table.reckoning_cases",
    "table.reckoning_measures",
    "table.reckonings",
    "table.settlement_profiles",
)
async def reckoning(ctx: TickContext) -> None:
    for key, value in asdict(await tend_reckonings(ctx)).items():
        ctx.count(f"reckoning_{key}", value)


PHASES = (Phase("reckoning", reckoning),)
