from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kin_dynamics.tend import tend_kin
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.community_relations",
    "table.culture_ethics",
    "table.designated_heirs",
    "table.elder_sway",
    "table.entities",
    "table.held_identities",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.kin_blends",
    "table.kin_disownings",
    "table.kin_dynamics",
    "table.kin_favours",
    "table.kin_rivalries",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.relationships",
    "table.reputations",
    "table.tradition_profiles",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.designated_heirs",
    "table.elder_sway",
    "table.house_members",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.kin_blends",
    "table.kin_disownings",
    "table.kin_dynamics",
    "table.kin_favours",
    "table.kin_rivalries",
    "table.memories",
    "table.professions_of_value",
)
async def kin_dynamics(ctx: TickContext) -> None:
    for key, value in asdict(await tend_kin(ctx)).items():
        ctx.count(f"kin_dynamics_{key}", value)


PHASES = (Phase("kin_dynamics", kin_dynamics),)
