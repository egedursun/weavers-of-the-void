from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.divine import AvatarRow
from aerona.db.tables.dominion import CreatureLessonRow, DivineCreatureRow, MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import CreatureDeed, CreatureLesson
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.engine.divine.old_gods import old_gods_act
from aerona.engine.dominion.creatures import tended_by_old_god
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, settlement, tuned_rules

DEEDS_CERTAIN = {"miracle_pct": 100, "avatar_pct": 100, "creature_pct": 100}


async def old_god(session: AsyncSession, world: CoreWorld) -> ForeignGodRow:
    row = ForeignGodRow(
        name="The Elder of the Shallows",
        domain_primary=Domain.SEA,
        world_id=world.world.id,
        power=60,
        status=ForeignGodStatus.AWAKE,
        strength=50,
        endurance=50,
        agility=50,
        wisdom=50,
        cunning=50,
        will=50,
        creativity=50,
        charisma=50,
        might=50,
        sanity=80,
        created_epoch=1,
    )
    session.add(row)
    await session.flush()
    return row


async def test_an_awake_old_god_works_a_miracle_for_its_flock_walks_among_unbelievers_and_raises_a_creature(session: AsyncSession, world: CoreWorld) -> None:
    god = await old_god(session, world)
    flock = await settlement(session, "Tidemoor", world, world.regions[0])
    await bond(session, flock.id, god.id, BondKind.WORSHIPS)
    ctx = await manual_context(session, "old_gods", rules=tuned_rules(foreign_gods=DEEDS_CERTAIN))
    tally = await old_gods_act(ctx)
    assert (tally.miracles, tally.avatars, tally.creatures) == (1, 1, 1)
    miracle = await session.scalar(select(MiracleRecordRow).where(MiracleRecordRow.god_node_id == god.id))
    assert miracle is not None and miracle.target_entity_id == flock.id
    avatar = await session.scalar(select(AvatarRow).where(AvatarRow.god_node_id == god.id))
    assert avatar is not None
    walked = await session.get(EntityRow, avatar.avatar_entity_id)
    assert walked is not None and walked.location_id != flock.id
    again = await old_gods_act(ctx)
    assert (again.avatars, again.creatures) == (0, 0)


async def test_an_old_god_rewards_its_creature_for_a_deed_done(session: AsyncSession, world: CoreWorld) -> None:
    god = await old_god(session, world)
    flock = await settlement(session, "Tidemoor", world, world.regions[0])
    await bond(session, flock.id, god.id, BondKind.WORSHIPS)
    ctx = await manual_context(session, "old_gods", rules=tuned_rules(foreign_gods=DEEDS_CERTAIN))
    await old_gods_act(ctx)
    row = await session.scalar(select(DivineCreatureRow).where(DivineCreatureRow.god_node_id == god.id))
    assert row is not None
    beast = await session.get(EntityRow, row.creature_entity_id)
    assert beast is not None
    before = row.weights[CreatureDeed.TEND_FIELDS.value]
    await tended_by_old_god(ctx, row, beast, CreatureDeed.TEND_FIELDS)
    lesson = await session.scalar(select(CreatureLessonRow).where(CreatureLessonRow.creature_entity_id == beast.id))
    assert lesson is not None and lesson.lesson is CreatureLesson.REWARD and row.weights[CreatureDeed.TEND_FIELDS.value] > before
