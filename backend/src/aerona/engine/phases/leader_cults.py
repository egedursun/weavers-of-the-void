from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.leader_cults.cults import tend_cults
from aerona.engine.phase import Phase


@reads("table.leader_cults", "table.node_births", "table.offices", "table.satires")
@writes(
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.leader_cults",
    "table.oaths",
    "table.polity_profiles",
    "table.satires",
    "table.settlement_profiles",
)
async def leader_cults(ctx: TickContext) -> None:
    for key, value in asdict(await tend_cults(ctx)).items():
        ctx.count(f"leader_cults_{key}", value)


PHASES = (Phase("leader_cults", leader_cults),)
