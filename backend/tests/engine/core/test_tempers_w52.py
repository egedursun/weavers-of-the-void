from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.beast_tempers import ACTIVE_TEMPERS, HELD_TEMPERS, HOSTILE_TEMPERS, TEMPERS
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import BeastTemper, Temperament
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import cow, shift_temper, strikes_back
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, bond, entity


async def beast_of(
    session: AsyncSession, world: CoreWorld, temperament: Temperament, *, hp: int, temper: BeastTemper = BeastTemper.HUNGRY
) -> tuple[EntityRow, BeastProfileRow]:
    beast = await entity(session, "Grey Maw", EntityType.BEAST, BeastStats(hp=hp), world_id=world.world.id, location_id=world.regions[0].id)
    row = BeastProfileRow(beast_entity_id=beast.id, endurance=50, temper=temper, locked=[])
    session.add(row)
    session.add(CreatureAnatomyRow(node_id=beast.id, temperament=temperament, locked=[]))
    await session.flush()
    return beast, row


def temper(row: BeastProfileRow) -> BeastTemper:
    return row.temper


async def kinds(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(IncidentRow.kind)))


def test_ten_tempers_and_the_three_new_ones_keep_to_the_lair() -> None:
    assert len(TEMPERS) == len(BeastTemper) == 10
    new = {BeastTemper.WOUNDED, BeastTemper.BROODING, BeastTemper.COWED}
    assert new.isdisjoint(ACTIVE_TEMPERS) and all(TEMPERS[temper].lairbound for temper in new)
    assert {BeastTemper.WOUNDED, BeastTemper.BROODING} <= HOSTILE_TEMPERS and BeastTemper.COWED not in HOSTILE_TEMPERS
    assert BeastTemper.BOUND in HELD_TEMPERS


async def test_a_badly_hurt_beast_turns_wounded_and_mends_in_its_lair(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row = await beast_of(session, world, Temperament.PLACID, hp=20)
    assert await shift_temper(ctx, beast, row) is True
    assert row.temper is BeastTemper.WOUNDED and row.temper_epoch == ctx.epoch
    assert stat_or(beast, "hp", 0) > 20
    await session.flush()
    assert "beast.wounded" in await kinds(session)


async def test_a_vengeful_wounded_beast_strikes_back_instead_of_hiding(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row = await beast_of(session, world, Temperament.VENGEFUL, hp=20)
    assert await strikes_back(ctx, beast.id)
    assert await shift_temper(ctx, beast, row) is False
    assert row.temper is BeastTemper.WOUNDED


async def test_a_driven_off_beast_stays_cowed_for_its_epochs_then_hungers_again(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row = await beast_of(session, world, Temperament.PLACID, hp=200)
    await cow(ctx, beast, world.people.id)
    assert row.temper is BeastTemper.COWED
    assert await shift_temper(ctx, beast, row) is True
    row.temper_epoch = ctx.epoch - ctx.rules.beast_tempers.epochs(ctx.rules.beast_tempers.cowed_years)
    assert await shift_temper(ctx, beast, row) is False
    assert temper(row) is BeastTemper.HUNGRY
    await session.flush()
    assert "beast.cowed" in await kinds(session)


async def test_a_beast_with_fresh_young_broods_and_leaves_brooding_when_they_grow(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row = await beast_of(session, world, Temperament.PLACID, hp=200)
    young = await entity(
        session, "Grey Whelp", EntityType.BEAST, BeastStats(hp=20), world_id=world.world.id, location_id=world.regions[0].id, birth_epoch=ctx.epoch
    )
    await bond(session, young.id, beast.id, BondKind.DESCENDS_FROM, ctx.epoch)
    assert await shift_temper(ctx, beast, row) is True
    assert row.temper is BeastTemper.BROODING
    young.birth_epoch = ctx.epoch - 5
    assert await shift_temper(ctx, beast, row) is False
    assert temper(row) is BeastTemper.TERRITORIAL
    await session.flush()
    assert "beast.brooding" in await kinds(session)


async def test_a_held_temper_is_never_shifted(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row = await beast_of(session, world, Temperament.PLACID, hp=10, temper=BeastTemper.TAMED)
    row.locked = ["temper"]
    await shift_temper(ctx, beast, row)
    assert row.temper is BeastTemper.TAMED
