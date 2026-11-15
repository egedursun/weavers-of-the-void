from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import AgeRow, ArcRow, EcoTransformationRow, IrregularSeasonRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.ages import AgeCycle, ArcTemplate, SeasonSpell
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import LongPlanKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.models.entity_stats import MortalStats
from tests.tools.every_setup import second_mortal
from tests.tools.factories import Realm, connect, make_entity

Ids = dict[str, int]


async def long_winter(session: AsyncSession, realm: Realm) -> Ids:
    session.add(IrregularSeasonRow(world_id=realm.cosmos.world_id, spell=SeasonSpell.WINTER, spell_started_epoch=1, spell_length=3, severity=60, locked=[]))
    await session.flush()
    return {"world": realm.cosmos.world_id}


async def sky_scholar(session: AsyncSession, realm: Realm) -> Ids:
    found = await long_winter(session, realm)
    session.add(SkillRow(holder_node_id=realm.mortal_id, skill=SkillKind.ASTRONOMY, level=6, peak=6, last_used_epoch=1, source=SkillSource.PRACTICE))
    town = await session.get(EntityRow, realm.settlement_id)
    assert town is not None
    await connect(session, town.id, realm.people_id, BondKind.DESCENDS_FROM)
    await session.flush()
    return found


async def open_tale(session: AsyncSession, realm: Realm) -> Ids:
    row = ArcRow(subject_node_id=realm.mortal_id, template=ArcTemplate.QUEST, locked=[])
    session.add(row)
    await session.flush()
    return {"arc": row.id}


async def turning_cosmos(session: AsyncSession, realm: Realm) -> Ids:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.age_cycle = AgeCycle.CYCLIC
    session.add(AgeRow(number=1, began_epoch=0, locked=[]))
    found = await open_tale(session, realm)
    await session.flush()
    return found


async def remade_land(session: AsyncSession, realm: Realm) -> Ids:
    plan = LongPlanRow(
        holder_node_id=realm.son_id,
        target_node_id=realm.cosmos.region_id,
        kind=LongPlanKind.ECOLOGICAL_TRANSFORMATION,
        name="The Green Work",
        steps=10,
        progress=4,
        step_cost=0,
        secrecy=50,
        locked=[],
    )
    session.add(plan)
    await session.flush()
    session.add(EcoTransformationRow(plan_id=plan.id, locked=[]))
    await session.flush()
    return {"plan": plan.id}


async def slain_kin(session: AsyncSession, realm: Realm) -> Ids:
    kin = await second_mortal(session, realm)
    stats = MortalStats(hp=40, strength=30, agility=30, intellect=30, charisma=30, age=30, lifespan=70)
    killer = await make_entity(session, "Varek Hollow", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=stats)
    await connect(session, realm.mortal_id, kin["mortal"], BondKind.PARENT_OF)
    await connect(session, killer.id, kin["mortal"], BondKind.KILLED)
    await session.flush()
    return {"foe": killer.id, "kin": kin["mortal"]}
