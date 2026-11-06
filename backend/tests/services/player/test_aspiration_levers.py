import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.mind import FearRow, InspirationRow, LifeDreamRow, PerkRow, WantRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import DreamState, FearKind, FocusKind, InspirationKind, InspirationState, LifeGoal, PerkKind, WantKind
from aerona.domain.enums.modifier import ModifierSource
from aerona.services.player import aspirations
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def hero_of(session: AsyncSession, world: PlayerWorld, name: str) -> int:
    hero = await make_entity(session, name, EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    return hero.id


async def test_the_god_gives_holds_and_takes_away_a_dream(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await hero_of(session, world, "Aster")
    await aspirations.set_dream(scope, aspirations.SetDream(holder_id=hero, goal=LifeGoal.SEE_THE_WORLD, progress=70, hold=True))
    dream = await session.get(LifeDreamRow, hero)
    assert dream is not None and dream.milestones == [33, 66] and dream.locked == ["progress"]
    await aspirations.set_dream(scope, aspirations.SetDream(holder_id=hero, goal=LifeGoal.SEE_THE_WORLD, progress=100, state=DreamState.FULFILLED))
    assert dream.state is DreamState.FULFILLED and dream.ended_epoch is not None
    await aspirations.remove_dream(scope, aspirations.MortalTarget(holder_id=hero))
    assert await session.get(LifeDreamRow, hero) is None
    with pytest.raises(ValidationFailedError):
        await aspirations.set_dream(scope, aspirations.SetDream(holder_id=world.region.id, goal=LifeGoal.FIND_LOVE))


async def test_the_god_gives_meets_and_takes_away_wants_and_fears(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await hero_of(session, world, "Brannoc")
    made = await aspirations.add_want(scope, aspirations.AddWant(holder_id=hero, kind=WantKind.TRAVEL))
    want = await session.get_one(WantRow, made.values["want_id"])
    await aspirations.edit_want(scope, aspirations.EditWant(want_id=want.id, fulfilled=True, hold=False))
    assert want.fulfilled_epoch is not None and want.locked == []
    await aspirations.remove_want(scope, aspirations.WantTarget(want_id=want.id))
    assert await session.get(WantRow, want.id) is None
    feared = await aspirations.set_fear(scope, aspirations.SetFear(holder_id=hero, kind=FearKind.PLAGUE, strength=30))
    await aspirations.set_fear(scope, aspirations.SetFear(holder_id=hero, kind=FearKind.PLAGUE, strength=80))
    fear = await session.get_one(FearRow, feared.values["fear_id"])
    assert fear.strength == 80
    assert len(list(await session.scalars(select(FearRow).where(FearRow.holder_node_id == hero)))) == 1
    await aspirations.remove_fear(scope, aspirations.FearTarget(fear_id=fear.id))
    assert await session.get(FearRow, fear.id) is None


async def test_the_god_sets_a_focus_grants_perks_and_holds_conviction(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await hero_of(session, world, "Cerys")
    craft = next(perk for perk in PerkKind if aspirations.PERKS[perk].focus is FocusKind.CRAFT)
    await aspirations.set_focus(scope, aspirations.SetFocus(holder_id=hero, focus=FocusKind.CRAFT))
    await aspirations.grant_perk(scope, aspirations.PerkTarget(holder_id=hero, perk=craft))
    assert await session.get(PerkRow, (hero, craft)) is not None
    modifier = select(ModifierRow).where(ModifierRow.target_node_id == hero, ModifierRow.source_kind == ModifierSource.PERK)
    assert list(await session.scalars(modifier))
    with pytest.raises(ValidationFailedError):
        await aspirations.grant_perk(scope, aspirations.PerkTarget(holder_id=hero, perk=craft))
    await aspirations.set_focus(scope, aspirations.SetFocus(holder_id=hero, focus=FocusKind.MARTIAL))
    assert await session.get(PerkRow, (hero, craft)) is None and not list(await session.scalars(modifier))
    await aspirations.set_conviction(scope, aspirations.SetConviction(holder_id=hero, value=90))
    profile = await session.get_one(MortalProfileRow, hero)
    assert profile.conviction == 90 and {"conviction", "focus"} <= set(profile.locked)


async def test_the_god_seizes_reshapes_and_quenches_an_inspiration(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await hero_of(session, world, "Dagny")
    made = await aspirations.inspire(scope, aspirations.Inspire(holder_id=hero, kind=InspirationKind.MASTERWORK_FEVER, material="gold", epochs=3))
    row = await session.get_one(InspirationRow, made.values["inspiration_id"])
    assert row.state is InspirationState.BURNING and row.deadline_epoch == row.started_epoch + 3
    await aspirations.edit_inspiration(scope, aspirations.EditInspiration(inspiration_id=row.id, deadline_epoch=40, state=InspirationState.FAILED))
    assert row.deadline_epoch == 40 and row.state is InspirationState.FAILED
    await aspirations.remove_inspiration(scope, aspirations.InspirationTarget(inspiration_id=row.id))
    assert await session.get(InspirationRow, row.id) is None
