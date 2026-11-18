from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.engine.context import TickContext
from aerona.engine.record_keepers.keepers import KeeperTally, chronicler_now, keep_record_keepers, keeper_of
from aerona.engine.record_keepers.legacy import recover_keepers
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement


async def town_of_people(session: AsyncSession, world: CoreWorld) -> EntityRow:
    town = await settlement(session, "Ardun", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    return town


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("record_keeper.")).order_by(IncidentRow.id)))


async def test_a_scribe_is_seated_as_chronicler_and_a_mortal_of_the_people_as_its_historian(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await town_of_people(session, world)
    await mortal(session, "Plain", world, town.id)
    scribe = await mortal(session, "Ehmel", world, town.id)
    scribe.mortal_role = MortalRole.SCRIBE
    await session.flush()
    tally = KeeperTally()
    await keep_record_keepers(ctx, tally)
    chronicler = await chronicler_now(session)
    historian = await keeper_of(session, RecordKeeperKind.HISTORIAN, world.people.id)
    assert chronicler is not None and chronicler.id == scribe.id
    assert historian is not None and historian.id == scribe.id
    assert tally.seated == 2 and "record_keeper.seated" in await kinds_of(session)


async def test_when_the_chronicler_dies_the_apprentice_takes_up_the_pen_and_a_held_keeper_stays(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town = await town_of_people(session, world)
    master = await mortal(session, "Master", world, town.id)
    master.mortal_role = MortalRole.SCRIBE
    apprentice = await mortal(session, "Apprentice", world, town.id)
    await bond(session, apprentice.id, master.id, BondKind.APPRENTICE_OF)
    await session.flush()
    await keep_record_keepers(ctx, KeeperTally())
    assert (await chronicler_now(session)) is not None
    master.status = EntityStatus.DEAD
    master.end_epoch = ctx.epoch
    await session.flush()
    tally = KeeperTally()
    await keep_record_keepers(ctx, tally)
    successor = await chronicler_now(session)
    assert successor is not None and successor.id == apprentice.id and tally.succeeded >= 1
    assert "record_keeper.succeeded" in await kinds_of(session)
    row = await session.scalar(select(RecordKeeperRow).where(RecordKeeperRow.kind == RecordKeeperKind.CHRONICLER))
    assert row is not None
    row.locked = ["keeper_entity_id"]
    apprentice.status = EntityStatus.DEAD
    apprentice.end_epoch = ctx.epoch
    await session.flush()
    await keep_record_keepers(ctx, KeeperTally())
    assert row.keeper_entity_id == apprentice.id


async def test_the_names_of_old_chroniclers_and_historians_become_mortals_of_the_world(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await town_of_people(session, world)
    known = await mortal(session, "Lemir", world, town.id)
    session.add_all(
        [
            EpochRow(epoch=1, chronicler_name="Lemir", chronicler_identity="scribe of the coast"),
            EpochRow(epoch=2, chronicler_name="Ossa", chronicler_identity="apprentice of Lemir"),
            HistorianViewRow(epoch=1, people_entity_id=world.people.id, historian="Tavi", text="We came first."),
        ]
    )
    await session.flush()
    assert await recover_keepers(ctx) == 3
    first = await session.get(EpochRow, 1)
    second = await session.get(EpochRow, 2)
    assert first is not None and first.chronicler_entity_id == known.id
    assert second is not None and second.chronicler_entity_id is not None
    ossa = await session.get(EntityRow, second.chronicler_entity_id)
    assert ossa is not None and ossa.entity_type is EntityType.MORTAL and ossa.status is EntityStatus.CANON
    assert (await chronicler_now(session)) == ossa
    view = await session.scalar(select(HistorianViewRow))
    assert view is not None and view.historian_entity_id is not None
    historian = await keeper_of(session, RecordKeeperKind.HISTORIAN, world.people.id)
    assert historian is not None and historian.name == "Tavi" and historian.location_id == town.id
    assert await recover_keepers(ctx) == 0
