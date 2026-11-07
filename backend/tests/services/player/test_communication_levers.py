import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.communication import CipherRow, PublicOpinionRow, SignalLinkRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, OpinionSubject, SignalKind, SignalState
from aerona.domain.enums.entity import EntityType
from aerona.services.player import communication
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_sends_edits_holds_and_unmakes_messages(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make_entity(session, "Ostmark", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Penrith", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    effect = await communication.post(
        scope, communication.SendDispatch(sender_id=first.id, recipient_id=second.id, content=DispatchContent.PLEA, medium=Medium.BIRD)
    )
    row = await session.get(MessageRow, effect.values["message_id"])
    assert row is not None and row.content is DispatchContent.PLEA and row.state is DispatchState.UNDER_WAY
    await communication.edit_dispatch(scope, communication.EditDispatch(message_id=row.id, state=DispatchState.LOST, forged=True))
    assert row.state is DispatchState.LOST and row.forged and {"state", "forged"} <= set(row.locked)
    await communication.hold_dispatch(scope, communication.EditDispatch(message_id=row.id, hold=False))
    assert row.locked == []
    with pytest.raises(ValidationFailedError):
        await communication.post(scope, communication.SendDispatch(sender_id=first.id, recipient_id=first.id, content=DispatchContent.PLEA))
    await communication.delete_dispatch(scope, communication.DispatchTarget(message_id=row.id))
    with pytest.raises(NotFoundError):
        await communication.delete_dispatch(scope, communication.DispatchTarget(message_id=row.id))


async def test_the_god_sets_opinions_ciphers_and_signal_links(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Quillon", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    lord = await make_entity(session, "Rhosyn", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    far = await make_entity(session, "Sallow Fen", EntityType.REGION, world_id=world.world.id)
    await communication.set_opinion(scope, communication.SetOpinion(community_id=town.id, subject_id=lord.id, subject=OpinionSubject.RULER, approval=-40))
    opinion = await session.get(PublicOpinionRow, (town.id, lord.id))
    assert opinion is not None and opinion.approval == -40 and "approval" in opinion.locked
    await communication.delete_opinion(scope, communication.OpinionTarget(community_id=town.id, subject_id=lord.id))
    assert await session.get(PublicOpinionRow, (town.id, lord.id)) is None
    await communication.set_cipher(scope, communication.SetCipher(owner_id=town.id, strength=70))
    cipher = await session.get(CipherRow, town.id)
    assert cipher is not None and cipher.strength == 70
    await communication.break_cipher(scope, communication.BreakCipher(owner_id=town.id, breaker_id=lord.id))
    assert cipher.broken_by == [lord.id]
    await communication.mend_cipher(scope, communication.CipherTarget(owner_id=town.id))
    assert cipher.broken_by == []
    await communication.delete_cipher(scope, communication.CipherTarget(owner_id=town.id))
    built = await communication.build_signal(
        scope, communication.BuildSignal(owner_id=town.id, kind=SignalKind.POST_STATION, from_region_id=world.region.id, to_region_id=far.id)
    )
    link = await session.get(SignalLinkRow, built.values["link_id"])
    assert link is not None and link.state is SignalState.ACTIVE
    await communication.edit_signal(scope, communication.EditSignal(link_id=link.id, state=SignalState.BURNED))
    assert link.state is SignalState.BURNED
    await communication.delete_signal(scope, communication.SignalTarget(link_id=link.id))
    assert await session.get(SignalLinkRow, link.id) is None
