from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.hits import Harm
from aerona.engine.interconnect.incidents import chain_to, recent_chain
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.phases.interconnect import incident_threads
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune


async def test_causes_chain_through_shared_participants_and_open_a_thread(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), incidents={"thread_chain_min": 3})
    ctx = make_ctx(session, rules, epoch=4)
    king = await make(session, "Varn", EntityType.MORTAL, world_id, hp=100, strength=60, agility=50, age=40)
    rival = await make(session, "Osk", EntityType.MORTAL, world_id, hp=100, strength=60, agility=50, age=30)
    battle = await ctx.chronicle(ChronicleKind.WAR, "Varn and Osk met at the ford.", template_key="test.battle", entity_ids=[king.id, rival.id])
    await apply_hits(ctx, king, Harm(200, HarmCause.BATTLE, "fell at the ford", killer_id=rival.id, source_node_id=rival.id))
    await ctx.chronicle(ChronicleKind.WORLD, "Osk claimed the throne of Varn.", template_key="test.succession", entity_ids=[rival.id])
    rows = list(await session.scalars(select(IncidentRow).order_by(IncidentRow.id)))
    assert rows[0].id == battle.incident_id and all(row.cause_incident_id is not None for row in rows[1:])
    assert all(row.magnitude > 0 for row in rows)
    death = next(row for row in rows if row.kind == "mortal.death.cause")
    roles = {(item.node_id, item.role) for item in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == death.id))}
    assert (king.id, IncidentRole.TARGET) in roles and (rival.id, IncidentRole.ACTOR) in roles
    chain = await chain_to(session, rows[-1].id, rules.incidents.chain_depth)
    assert chain.texts[0] == "Varn and Osk met at the ford." and len(chain.incident_ids) >= 3
    assert await recent_chain(session, rival.id, rules.incidents.chain_depth) is not None
    await incident_threads(ctx)
    thread = await session.scalar(select(ThreadRow))
    assert thread is not None and "the ford" in thread.text
