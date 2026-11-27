from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.engine.phases.creator_mood import creator_mood
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, make_context, make_entity, make_son


async def test_a_creator_who_sends_a_sign_of_its_passion_is_not_also_told_silent(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    await make_son(session, "Tidekeeper", world.world.id)
    await make_entity(session, "Ledger Sage", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id, mortal_role=MortalRole.SAGE)
    world.creator.passions = [CreatorPassion.KNOWLEDGE]
    await session.flush()
    tuned = replace(
        rules,
        creator=replace(
            rules.creator,
            wrath_threshold=100,
            content_threshold=100,
            lonely_threshold=100,
            indifferent_threshold=100,
            silence_sign_chance=100,
            passion_sign_chance=100,
        ),
    )
    await creator_mood(make_context(session, tuned, 10))
    kinds = set(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.like("gods.mood.%"))))
    assert "gods.mood.loneliness" in kinds
    assert "gods.mood.silence" not in kinds
