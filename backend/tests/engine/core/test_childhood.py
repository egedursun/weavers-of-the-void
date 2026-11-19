from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.childhood import ChildStandingRow, InfantCareRow, PedagogyRow, SocializationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.childhood import InfantFeeding, PedagogyTheory
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.mortal import LifeStage, PunishmentKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.childhood.life import ChildhoodTally, keep_childhood, keep_infants
from aerona.engine.childhood.seed import seed_childhood
from aerona.engine.context import TickContext
from aerona.engine.customs.grades import too_young_to_wed
from aerona.engine.mind.book import stored_values
from aerona.engine.mortal.justice import softened
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def home_town(session: AsyncSession, world: CoreWorld) -> int:
    if "town" not in world.extra:
        world.extra["town"] = await settlement(session, "Ardun", world, world.regions[0])
        await bond(session, world.extra["town"].id, world.people.id, BondKind.DESCENDS_FROM)
    return world.extra["town"].id


async def young(session: AsyncSession, world: CoreWorld, name: str, stage: LifeStage, age: int, **profile: object) -> EntityRow:
    being = await mortal(session, name, world, await home_town(session, world), age=age)
    session.add(MortalProfileRow(entity_id=being.id, life_stage=stage, locked=[], **profile))
    await session.flush()
    return being


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("childhood.")).order_by(IncidentRow.id)))


async def test_infant_care_sets_survival_and_weaning(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(InfantCareRow(people_entity_id=world.people.id, feeding=InfantFeeding.ANIMAL_MILK, weaning_age=2, locked=[]))
    infant = await young(session, world, "Nim", LifeStage.INFANT, 2)
    lost = replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(childhood={"infant_survival_pct": 0, "feeding_survival_shift": 0})))
    kept = replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(childhood={"infant_survival_pct": 100, "feeding_survival_shift": 0})))
    tally = ChildhoodTally()
    await keep_infants(kept, infant, world.people.id, tally)
    assert infant.status is EntityStatus.CANON and tally.weaned == 1
    await keep_infants(lost, infant, world.people.id, tally)
    assert infant.status is EntityStatus.DEAD and tally.infants_lost == 1
    assert "childhood.weaned" in await kinds_of(session)


async def test_upbringing_moves_values_and_harsh_ways_leave_stress(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(
        SocializationRow(
            people_entity_id=world.people.id,
            example=0,
            instruction=0,
            praise=0,
            storytelling=0,
            play=0,
            apprenticeship=0,
            peer_group=0,
            shame=40,
            punishment=40,
            ritual_ordeal=20,
            aim_piety=100,
            locked=[],
        )
    )
    child = await young(session, world, "Tal", LifeStage.CHILD, 6, stress=10)
    tally = await keep_childhood(ctx)
    values = await stored_values(session, ValueHolder.PERSONAL, child.id)
    profile = await session.get(MortalProfileRow, child.id)
    assert tally.shaped == 1 and values.get(ValueAxis.PIETY, 0) > 0
    assert profile is not None and profile.stress > 10


async def test_child_labour_costs_schooling_and_a_school_teaches(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(ChildStandingRow(people_entity_id=world.people.id, work_age=5, labour_share=100, locked=[]))
    worker = await young(session, world, "Bren", LifeStage.CHILD, 7, education=40)
    await keep_childhood(ctx)
    hand = await session.get(MortalProfileRow, worker.id)
    assert hand is not None and hand.education < 40
    town = await home_town(session, world)
    school = await entity(session, "Hall of Letters", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town)
    session.add(StructureProfileRow(structure_entity_id=school.id, kind=StructureKind.SCHOOL, host_entity_id=town))
    session.add(PedagogyRow(holder_node_id=school.id, theory=PedagogyTheory.DISCOVERY, locked=[]))
    pupil = await young(session, world, "Ysa", LifeStage.CHILD, 4)
    await keep_childhood(ctx)
    learner = await session.get(MortalProfileRow, pupil.id)
    assert learner is not None and learner.education > 0
    assert "childhood.school_entered" in await kinds_of(session)


async def test_the_young_are_spared_marriage_and_full_punishment(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(ChildStandingRow(people_entity_id=world.people.id, marriage_age=18, responsibility_age=14, locked=[]))
    youth = await young(session, world, "Wen", LifeStage.YOUTH, 13)
    elder = await young(session, world, "Dar", LifeStage.YOUTH, 30)
    assert await too_young_to_wed(session, youth, elder)
    assert await softened(ctx, youth, PunishmentKind.FLOGGING) is PunishmentKind.PUBLIC_SHAMING
    assert await softened(ctx, elder, PunishmentKind.FLOGGING) is PunishmentKind.FLOGGING
    standing = await session.get(ChildStandingRow, world.people.id)
    assert standing is not None
    standing.protected = True
    assert await softened(ctx, youth, PunishmentKind.FLOGGING) is None


async def test_childhood_is_seeded_for_every_people(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    tally = await seed_childhood(ctx)
    assert tally.infant_care >= 1 and tally.standing >= 1 and tally.socialization >= 1
    upbringing = await session.get(SocializationRow, world.people.id)
    assert upbringing is not None
    weights = (upbringing.example + upbringing.instruction + upbringing.praise + upbringing.shame + upbringing.punishment + upbringing.ritual_ordeal) + (
        upbringing.storytelling + upbringing.play + upbringing.apprenticeship + upbringing.schooling + upbringing.peer_group + upbringing.age_set
    )
    assert weights == 100
