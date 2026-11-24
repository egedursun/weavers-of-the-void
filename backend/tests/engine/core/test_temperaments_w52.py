from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.beast_tempers import AVENGING, GATHERING, GUARDING, REMEMBERING, TEMPERAMENTS
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import BeastGrudgeRow, BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.body import BodyPart, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.ecology import Temperament
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.models.entity_stats import ArmyStats, BeastStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.beast_ways import GRUDGES_FIXUP, backfill_grudges, gathers, grudge_town, guard_land, keep_grudges
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement


async def beast_of(
    session: AsyncSession, world: CoreWorld, temperament: Temperament, name: str = "Old Coil"
) -> tuple[EntityRow, BeastProfileRow, CreatureAnatomyRow]:
    region = world.regions[0]
    beast = await entity(session, name, EntityType.BEAST, BeastStats(hp=200), world_id=world.world.id, location_id=region.id)
    row = BeastProfileRow(beast_entity_id=beast.id, endurance=50, lair_place_id=region.id, locked=[])
    anatomy = CreatureAnatomyRow(node_id=beast.id, temperament=temperament, locked=[])
    session.add_all([row, anatomy])
    await session.flush()
    return beast, row, anatomy


def test_nine_temperaments_and_the_new_three_avenge_gather_and_guard() -> None:
    assert len(TEMPERAMENTS) == len(Temperament) == 11
    assert Temperament.VENGEFUL in AVENGING and Temperament.VENGEFUL in REMEMBERING
    assert Temperament.ACQUISITIVE in GATHERING and Temperament.PROTECTIVE in GUARDING
    assert Temperament.PLACID not in AVENGING | GATHERING | GUARDING


async def test_a_vengeful_beast_swears_a_grudge_and_seeks_the_town_of_its_wronger(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row, anatomy = await beast_of(session, world, Temperament.VENGEFUL)
    town = await settlement(session, "Kettle", world, world.regions[0])
    hunter = await mortal(session, "Arn", world, town.id)
    await remember(session, ctx.rules, holder_id=beast.id, subject_id=hunter.id, kind=MemoryKind.HARMED_ME, magnitude=-40, epoch=ctx.epoch)
    grudges = await keep_grudges(ctx, beast, anatomy)
    assert [grudge.target_node_id for grudge in grudges] == [hunter.id]
    found = await grudge_town(ctx, await RegionAtlas.load(session), row, grudges)
    assert found is not None and found[0].id == town.id
    await session.flush()
    assert "beast.grudge_sworn" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_placid_beast_keeps_no_grudge(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, _row, anatomy = await beast_of(session, world, Temperament.PLACID)
    hunter = await mortal(session, "Bel", world, world.regions[0].id)
    await remember(session, ctx.rules, holder_id=beast.id, subject_id=hunter.id, kind=MemoryKind.HARMED_ME, magnitude=-40, epoch=ctx.epoch)
    assert await keep_grudges(ctx, beast, anatomy) == []


async def test_a_protective_beast_strikes_an_army_in_its_land(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, row, anatomy = await beast_of(session, world, Temperament.PROTECTIVE)
    army = await entity(session, "Iron Host", EntityType.ARMY, ArmyStats(size=1000), world_id=world.world.id, location_id=world.regions[0].id)
    struck = await guard_land(ctx, await RegionAtlas.load(session), beast, row, anatomy)
    assert struck == 1 and stat_or(army, "size", 0) < 1000
    other, other_row, other_anatomy = await beast_of(session, world, Temperament.ACQUISITIVE, "Gold Coil")
    assert await guard_land(ctx, await RegionAtlas.load(session), other, other_row, other_anatomy) == 0
    assert gathers(other_anatomy) and not gathers(anatomy)


async def test_beasts_wounded_in_the_record_gain_their_grudges_once(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    beast, _row, _anatomy = await beast_of(session, world, Temperament.VENGEFUL)
    hunter = await mortal(session, "Cass", world, world.regions[0].id)
    session.add(
        InjuryRow(
            bearer_node_id=beast.id,
            part=BodyPart.TORSO,
            kind=InjuryKind.CUT,
            damage_type=DamageType.CUT,
            severity=2,
            state=InjuryState.HEALED_SCAR,
            function_loss=0,
            cause_kind=HarmCause.MONSTER,
            cause_node_id=hunter.id,
            epoch=1,
        )
    )
    await session.flush()
    assert await backfill_grudges(ctx) == 1
    grudge = await session.scalar(select(BeastGrudgeRow).where(BeastGrudgeRow.beast_entity_id == beast.id))
    assert grudge is not None and grudge.target_node_id == hunter.id
    assert await session.get(AppliedFixupRow, GRUDGES_FIXUP) is not None
    assert await backfill_grudges(ctx) == 0
