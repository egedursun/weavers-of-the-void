from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import CrowdMoodRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import ThoughtRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.mind import Emotion, ThoughtKind
from aerona.engine.context import TickContext
from aerona.engine.feeling_spread.lean import mood_lean
from aerona.engine.feeling_spread.moods import MoodTally, spread_along_bonds, spread_in_households, spread_in_places, tend_moods
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement, tuned_rules


async def caught(session: AsyncSession, holder: int) -> ThoughtRow | None:
    return await session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == holder, ThoughtRow.kind == ThoughtKind.CAUGHT_FEELING))


async def test_a_strong_feeling_passes_along_bonds(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Griefholm", world, world.regions[0], population=900)
    mourner, child = await mortal(session, "Ulla Venn", world, town.id, charisma=90), await mortal(session, "Pim Venn", world, town.id)
    await bond(session, mourner.id, child.id, BondKind.PARENT_OF)
    await think(session, ctx.rules, mourner.id, ThoughtKind.LOST_SPOUSE, ctx.epoch, intensity=80, forced=True)
    tally = MoodTally()
    await spread_along_bonds(ctx, tally)
    row = await caught(session, child.id)
    assert row is not None and row.emotion is Emotion.GRIEF and row.subject_node_id == mourner.id and tally.caught >= 1


async def test_a_place_gathers_a_mood_its_people_catch_that_feeds_its_crowd_and_leans_its_choices(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "dread", tuned_rules(feeling_spread={"spread_floor": 5, "told_at": 5}))
    town = await settlement(session, "Dreadmoor", world, world.regions[0], population=900)
    session.add(CrowdMoodRow(settlement_entity_id=town.id, locked=[]))
    afraid = [await mortal(session, f"Fearful {index}", world, town.id) for index in range(3)]
    for person in afraid:
        await think(session, ctx.rules, person.id, ThoughtKind.FELT_UNSAFE, ctx.epoch, intensity=90, forced=True)
    calm = await mortal(session, "Calm One", world, town.id)
    tally = MoodTally()
    await spread_in_places(ctx, tally)
    mood = await session.scalar(select(FeelingSpreadRow).where(FeelingSpreadRow.settlement_entity_id == town.id))
    assert mood is not None and mood.leading is Emotion.FEAR and tally.spread == 1
    crowd = await session.get(CrowdMoodRow, town.id)
    assert crowd is not None and crowd.anxiety > 0
    assert await caught(session, calm.id) is not None
    assert await mood_lean(session, town.id, BiasedDecision.PEACE) > 1 > await mood_lean(session, town.id, BiasedDecision.WAR)
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "mood.spread")) is not None


async def test_a_household_shares_its_members_feelings_and_moods_fade(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fade", tuned_rules(feeling_spread={"fade_per_epoch": 100}))
    town = await settlement(session, "Hearthold", world, world.regions[0], population=500)
    home = HouseholdRow(name="The Hearth", settlement_node_id=town.id, locked=[])
    session.add(home)
    await session.flush()
    joyful = await mortal(session, "Glad One", world, town.id)
    session.add(HouseholdMemberRow(member_node_id=joyful.id, household_id=home.id, role=next(iter(HouseholdRole))))
    await think(session, ctx.rules, joyful.id, ThoughtKind.MARRIED, ctx.epoch, intensity=70, forced=True)
    await spread_in_households(ctx, MoodTally())
    mood = await session.scalar(select(FeelingSpreadRow).where(FeelingSpreadRow.household_id == home.id))
    assert mood is not None and mood.feelings
    for thought in list(await session.scalars(select(ThoughtRow).where(ThoughtRow.holder_node_id == joyful.id))):
        await session.delete(thought)
    await session.flush()
    await tend_moods(ctx)
    assert not mood.feelings or max(mood.feelings.values()) < 10
