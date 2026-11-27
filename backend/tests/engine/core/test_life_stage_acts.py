from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mortal import LifeStage, StressBreak
from aerona.domain.enums.sacred import SacramentKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.mortal.course import foster_orphan
from aerona.engine.mortal.life import young
from aerona.engine.primitives.manual import manual_context
from aerona.engine.sacred.rites import due_rites
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def test_only_infants_children_and_youths_count_as_young() -> None:
    assert {stage for stage in LifeStage if young(stage)} == {LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH}


async def test_an_ancient_whose_parents_are_gone_is_never_taken_in_as_an_orphan(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "foster", tuned_rules(kinship={"foster_chance": 100}))
    town = await settlement(session, "Wardhold", world, world.regions[0])
    noble = await mortal(session, "Lord Avel", world, town.id, age=40)
    noble.social_class = SocialClass.NOBLE
    elder = await mortal(session, "Etsem", world, town.id, age=160, lifespan=120)
    child = await mortal(session, "Kesi", world, town.id, age=6)
    for one, stage in ((noble, LifeStage.ADULT), (elder, LifeStage.ANCIENT), (child, LifeStage.CHILD)):
        session.add(MortalProfileRow(entity_id=one.id, life_stage=stage, locked=[]))
    await session.flush()
    elder_profile = await session.get(MortalProfileRow, elder.id)
    child_profile = await session.get(MortalProfileRow, child.id)
    assert elder_profile is not None and child_profile is not None
    assert not await foster_orphan(ctx, elder, elder_profile)
    assert await foster_orphan(ctx, child, child_profile)
    wards = set(await session.scalars(select(BondRow.source_node_id).where(BondRow.kind == BondKind.FOSTERED_BY)))
    assert wards == {child.id}


async def test_a_birth_blessing_goes_to_the_newborn_and_not_to_a_grown_one_made_this_age(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "bless")
    town = await settlement(session, "Cradle", world, world.regions[0])
    baby = await mortal(session, "Nima", world, town.id, age=0)
    commander = await mortal(session, "Ymsamren", world, town.id, age=40)
    for one in (baby, commander):
        one.birth_epoch = ctx.epoch
    session.add(MortalProfileRow(entity_id=baby.id, life_stage=LifeStage.INFANT, locked=[]))
    session.add(MortalProfileRow(entity_id=commander.id, life_stage=LifeStage.ADULT, locked=[]))
    await session.flush()
    blessed = {row.id for row, kind in await due_rites(ctx) if kind is SacramentKind.BIRTH_BLESSING}
    assert blessed == {baby.id}


async def test_a_withdrawn_noble_never_takes_in_an_orphan(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "foster.away", tuned_rules(kinship={"foster_chance": 100}))
    town = await settlement(session, "Stillhold", world, world.regions[0])
    noble = await mortal(session, "Lady Vasa", world, town.id, age=40)
    noble.social_class = SocialClass.NOBLE
    child = await mortal(session, "Etsi", world, town.id, age=6)
    session.add(MortalProfileRow(entity_id=noble.id, life_stage=LifeStage.ADULT, last_break=StressBreak.WITHDRAWAL, last_break_epoch=1, locked=[]))
    session.add(MortalProfileRow(entity_id=child.id, life_stage=LifeStage.CHILD, locked=[]))
    await session.flush()
    child_profile = await session.get(MortalProfileRow, child.id)
    assert child_profile is not None
    assert not await foster_orphan(ctx, child, child_profile)
