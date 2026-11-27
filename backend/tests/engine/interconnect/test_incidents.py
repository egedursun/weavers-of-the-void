from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.hits import Harm
from aerona.engine.interconnect.incidents import chain_to, recent_chain
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.phases.interconnect import incident_threads
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import recording
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune


async def test_causes_chain_through_the_recording_scope_and_open_a_thread(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), incidents={"thread_chain_min": 3})
    ctx = make_ctx(session, rules, epoch=4)
    king = await make(session, "Varn", EntityType.MORTAL, world_id, hp=100, strength=60, agility=50, age=40)
    rival = await make(session, "Osk", EntityType.MORTAL, world_id, hp=100, strength=60, agility=50, age=30)
    battle = await record(
        ctx, "player.history", roles={IncidentRole.ACTOR: (king.id, rival.id)}, facts={"account": "Varn and Osk met at the ford."}, magnitude=40
    )
    async with recording(ctx, "player.history", cause=battle.incident_id):
        await apply_hits(ctx, king, Harm(200, HarmCause.BATTLE, "fell at the ford", killer_id=rival.id, source_node_id=rival.id))
        await record(ctx, "player.history", roles={IncidentRole.ACTOR: rival.id}, facts={"account": "Osk claimed the throne of Varn."}, magnitude=40)
    rows = list(await session.scalars(select(IncidentRow).order_by(IncidentRow.id)))
    assert rows[0].id == battle.incident_id and all(row.cause_incident_id is not None for row in rows[1:])
    assert all(row.magnitude > 0 for row in rows)
    death = next(row for row in rows if row.kind == "mortal.death.slain")
    roles = {(item.node_id, item.role) for item in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == death.id))}
    assert (king.id, IncidentRole.VICTIM) in roles and (rival.id, IncidentRole.ACTOR) in roles
    chain = await chain_to(session, rows[-1].id, rules.incidents.chain_depth)
    assert chain.texts[0] == "Varn and Osk met at the ford." and len(chain.incident_ids) >= 3
    assert await recent_chain(session, rival.id, rules.incidents.chain_depth) is not None
    await incident_threads(ctx)
    thread = await session.scalar(select(ThreadRow))
    assert thread is not None and "the ford" in thread.text


async def test_a_story_opened_from_an_old_chain_keeps_the_age_it_began_in_and_tells_only_told_lines(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), incidents={"thread_chain_min": 3})
    old, now = make_ctx(session, rules, epoch=4), make_ctx(session, rules, epoch=8)
    duelist = await make(session, "Zemor", EntityType.MORTAL, world_id, hp=100, strength=60, agility=50, age=40)
    first = await record(old, "player.history", roles={IncidentRole.ACTOR: duelist.id}, facts={"account": "Zemor called out a rival."}, magnitude=40)
    async with recording(old, "player.history", cause=first.incident_id):
        second = await record(old, "player.history", roles={IncidentRole.ACTOR: duelist.id}, facts={"account": "The rival answered."}, magnitude=40)
    async with recording(now, "player.history", cause=second.incident_id):
        third = await record(now, "player.history", roles={IncidentRole.ACTOR: duelist.id}, facts={"account": "Word of the duel spread."}, magnitude=40)
    async with recording(now, "player.history", cause=third.incident_id):
        fourth = await record(now, "player.history", roles={IncidentRole.ACTOR: duelist.id}, facts={"account": "Nobody told this."}, magnitude=40)
    untold = await session.get(IncidentRow, fourth.incident_id)
    assert untold is not None
    untold.chronicle_id = None
    await session.flush()
    await incident_threads(now)
    thread = await session.scalar(select(ThreadRow))
    assert thread is not None and thread.epoch == 4
    assert thread.text.startswith("Zemor called out a rival.") and thread.text.endswith("Word of the duel spread.")
