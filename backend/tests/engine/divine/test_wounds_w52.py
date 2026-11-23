import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.divine import DivineStandingRow, DivineWoundRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.divine import DivineWoundKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.engine.divine import control
from aerona.engine.divine.avatars import manifest
from aerona.engine.divine.wounds import NEGLECT_FIXUP, avatar_slain, betrayed, mark_neglect, neglect_wounds
from tests.engine.divine.pantheon import god, worship
from tests.engine.society.factories import Realm, context, mortal, settlement, tuned


async def test_a_god_no_people_worships_any_more_takes_the_wound_of_neglect(realm: Realm) -> None:
    lonely = await god(realm, "Erem", Domain.MOON, Domain.DREAM)
    kept = await god(realm, "Orun", Domain.SUN, Domain.LIFE)
    town = await settlement(realm, "Silentford")
    realm.session.add(DivineStandingRow(community_entity_id=town.id, god_node_id=lonely.id, locked=[]))
    realm.session.add(DivineStandingRow(community_entity_id=town.id, god_node_id=kept.id, locked=[]))
    await worship(realm, town, kept.id)
    ctx = context(realm.session)
    assert await neglect_wounds(ctx) == 1
    wound = await realm.session.scalar(select(DivineWoundRow).where(DivineWoundRow.god_node_id == lonely.id))
    assert wound is not None and wound.kind is DivineWoundKind.FORGOTTEN_NAME and wound.cause is WoundCause.NEGLECT
    assert await realm.session.scalar(select(DivineWoundRow).where(DivineWoundRow.god_node_id == kept.id)) is None
    assert await neglect_wounds(ctx) == 0
    told = await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind == "divine.wound_forgotten_name"))
    assert told is not None


async def test_a_mortal_who_kills_a_mortal_form_wounds_the_god_as_its_slayer(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    town = await settlement(realm, "Saltmouth")
    hunter = await mortal(realm, "Vesk", location_id=town.id)
    ctx = context(realm.session)
    avatar = await manifest(ctx, sea, town)
    wound = await avatar_slain(ctx, avatar.id, hunter.id)
    assert wound is not None and wound.cause is WoundCause.MORTAL_SLAYER and wound.cause_node_id == hunter.id
    assert wound.severity == ctx.rules.divine_wounds.mortal_slayer_severity


async def test_betrayal_wounds_the_god_and_the_lever_asks_a_mortal_for_a_mortal_deed(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    traitor = await mortal(realm, "Ash")
    ctx = context(realm.session, tuned(divine_wounds={"betrayal_pct": 100}))
    wound = await betrayed(ctx, sea.id, traitor.id)
    assert wound is not None and wound.cause is WoundCause.BETRAYAL and wound.kind is DivineWoundKind.STOLEN_NAME
    with pytest.raises(ValidationFailedError):
        await control.wound_god(ctx, sea.id, DivineWoundKind.BOUND, 30, None, cause=WoundCause.MORTAL_SLAYER)
    dealt = await control.wound_god(ctx, sea.id, DivineWoundKind.BOUND, 30, None, cause=WoundCause.MORTAL_SLAYER, cause_node_id=traitor.id)
    assert dealt.cause is WoundCause.MORTAL_SLAYER and dealt.cause_node_id == traitor.id


async def test_old_wounds_of_lost_worship_take_the_cause_of_neglect_once(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    realm.session.add(DivineWoundRow(god_node_id=sea.id, kind=DivineWoundKind.LOST_WORSHIPPERS, cause=WoundCause.DUEL, locked=[]))
    realm.session.add(DivineWoundRow(god_node_id=sea.id, kind=DivineWoundKind.BOUND, cause=WoundCause.DUEL, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session)
    assert await mark_neglect(ctx) == 1
    assert await realm.session.get(AppliedFixupRow, NEGLECT_FIXUP) is not None
    assert await mark_neglect(ctx) == 0
    causes = {row.kind: row.cause for row in await realm.session.scalars(select(DivineWoundRow).where(DivineWoundRow.god_node_id == sea.id))}
    assert causes == {DivineWoundKind.LOST_WORSHIPPERS: WoundCause.NEGLECT, DivineWoundKind.BOUND: WoundCause.DUEL}
