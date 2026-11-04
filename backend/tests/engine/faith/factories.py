from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import JudgementDoctrine, TenetKind
from aerona.domain.models.entity_stats import CultStats, MortalStats, PeopleStats, SettlementStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, bond, make_context, make_entity, make_son

EPOCH = 4


@dataclass
class Faithful:
    god: SonRow
    town: EntityRow
    people: EntityRow
    cult: EntityRow
    doctrine: CultDoctrineRow


def tick(session: AsyncSession, rules: Rules, epoch: int = EPOCH) -> TickContext:
    return make_context(session, rules, epoch)


async def faithful(session: AsyncSession, world: GodsWorld, *, tenets: tuple[TenetKind, ...] = (), name: str = "Ilun") -> Faithful:
    god = await make_son(session, name, world.world.id)
    town = await make_entity(
        session,
        f"{name}ford",
        EntityType.SETTLEMENT,
        world_id=world.world.id,
        location_id=world.region.id,
        stats=SettlementStats(population=900, prosperity=40),
    )
    people = await make_entity(
        session, f"{name} Folk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id, stats=PeopleStats(population=600)
    )
    cult = await make_entity(
        session, f"Church of {name}", EntityType.CULT, world_id=world.world.id, location_id=town.id, stats=CultStats(followers=2000, zeal=50, influence=30)
    )
    for worshipper in (town, people, cult):
        await bond(session, worshipper.id, god.id, BondKind.WORSHIPS)
    doctrine = CultDoctrineRow(
        cult_entity_id=cult.id,
        judgement=JudgementDoctrine.DEEDS,
        orthodoxy=50,
        tithe_rate=20,
        treasury=0,
        clergy_count=0,
        clergy_quality=60,
        zeal_parts={},
        excommunicated=[],
        updated_epoch=1,
        locked=[],
    )
    session.add(doctrine)
    for tenet in tenets:
        session.add(CultTenetRow(cult_entity_id=cult.id, tenet=tenet, since_epoch=1))
    await session.flush()
    return Faithful(god, town, people, cult, doctrine)


async def mortal(
    session: AsyncSession, world: GodsWorld, home: EntityRow, name: str, *, dead: bool = False, role: MortalRole = MortalRole.COMMONER
) -> EntityRow:
    found = await make_entity(session, name, EntityType.MORTAL, world_id=world.world.id, location_id=home.id, stats=MortalStats(age=30), mortal_role=role)
    if dead:
        found.status, found.end_epoch = EntityStatus.DEAD, EPOCH
    await session.flush()
    return found


async def spirit(session: AsyncSession, world: GodsWorld, home: EntityRow, name: str, *, unrest: int = 10) -> EntityRow:
    return await make_entity(session, name, EntityType.SPIRIT, world_id=world.world.id, location_id=home.id, stats=SpiritStats(strength=40, unrest=unrest))
