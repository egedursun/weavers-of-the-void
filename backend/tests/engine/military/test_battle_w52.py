from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import CAPTIVE_FATES, CASUALTY_FATES
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.military import ArmyUnitRow, BattleCasualtyRow, CaptiveCohortRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.military import CaptiveFate, CasualtyFate
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import BattleOutcome
from aerona.engine.military.control import settle_cohort
from aerona.engine.military.w52_war import resolve_missing, scatter_named
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.military.w52_war_setup import army_of
from tests.engine.warfare.factories import make, make_ctx, tune


def test_every_casualty_and_captive_fate_has_its_catalogue_entry() -> None:
    assert set(CASUALTY_FATES) == set(CasualtyFate) and set(CAPTIVE_FATES) == set(CaptiveFate)
    assert CASUALTY_FATES[CasualtyFate.MISSING].unresolved and CAPTIVE_FATES[CaptiveFate.RECRUITED].serves_captor


async def test_a_routed_fighter_goes_missing_and_is_resolved_the_next_epoch(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), casualties={"loser_missing_pct": 100, "missing_return_pct": 0, "deserted_bandit_pct": 100, "wild_cover": 0})
    ctx = make_ctx(session, rules)
    winner = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=4000)
    loser = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, population=4000)
    war = await open_war(ctx, winner, loser)
    battle = BattleRow(
        war_id=war.id, epoch=ctx.epoch, sequence=1, outcome=BattleOutcome.FIELD_VICTORY, gap=0.5, winner_entity_id=winner.id, loser_entity_id=loser.id
    )
    session.add(battle)
    fighter = await make(session, "Bran", EntityType.MORTAL, world_id)
    await session.flush()
    assert await scatter_named(ctx, battle.id, fighter, loser.id, rout_pct=100) is CasualtyFate.MISSING
    later = make_ctx(session, rules, epoch=ctx.epoch + 1)
    assert await resolve_missing(later) == 1
    row = await session.scalar(select(BattleCasualtyRow).where(BattleCasualtyRow.mortal_entity_id == fighter.id))
    assert row is not None and row.resolved_epoch == later.epoch
    assert fighter.mortal_role is MortalRole.BANDIT and fighter.status is EntityStatus.CANON


async def test_captives_can_be_executed_or_pressed_into_the_army(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    captor = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=4000)
    home = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, population=4000)
    war = await open_war(ctx, captor, home)
    army_id, _ = await army_of(ctx, captor.id, world_id, count=100)
    pressed = CaptiveCohortRow(
        captor_entity_id=captor.id, origin_entity_id=home.id, war_id=war.id, count=50, social_class=SocialClass.WARRIOR, fate=CaptiveFate.HELD, since_epoch=1
    )
    doomed = CaptiveCohortRow(
        captor_entity_id=captor.id, origin_entity_id=home.id, war_id=war.id, count=20, social_class=SocialClass.FARMER, fate=CaptiveFate.HELD, since_epoch=1
    )
    session.add_all([pressed, doomed])
    await session.flush()
    await settle_cohort(ctx, pressed.id, CaptiveFate.RECRUITED, None)
    stack = await session.scalar(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id))
    kept = 50 - 50 * ctx.rules.captives.recruited_desertion_pct // 100
    assert stack is not None and stack.count == 100 + kept and pressed.fate is CaptiveFate.RECRUITED
    await settle_cohort(ctx, doomed.id, CaptiveFate.EXECUTED, None)
    assert doomed.fate is CaptiveFate.EXECUTED


async def test_a_deserter_who_goes_home_is_hunted_as_a_fugitive_by_the_side_it_left(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), casualties={"loser_missing_pct": 0, "loser_deserted_pct": 100, "deserted_bandit_pct": 0})
    ctx = make_ctx(session, rules)
    winner = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=4000)
    loser = await make(session, "Vale Folk", EntityType.PEOPLE, world_id, population=4000)
    war = await open_war(ctx, winner, loser)
    battle = BattleRow(
        war_id=war.id, epoch=ctx.epoch, sequence=1, outcome=BattleOutcome.FIELD_VICTORY, gap=0.5, winner_entity_id=winner.id, loser_entity_id=loser.id
    )
    session.add(battle)
    fighter = await make(session, "Tam", EntityType.MORTAL, world_id)
    await session.flush()
    assert await scatter_named(ctx, battle.id, fighter, loser.id, rout_pct=100) is CasualtyFate.DESERTED
    hunted = await session.scalar(select(FugitiveRow).where(FugitiveRow.mortal_entity_id == fighter.id))
    assert hunted is not None and hunted.kind is FugitiveKind.DESERTER and hunted.pursuer_entity_id == loser.id
