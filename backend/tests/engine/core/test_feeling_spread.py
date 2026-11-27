from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import CrowdMoodRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import ThoughtRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import CrowdFeeling
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.mind import Emotion, ThoughtKind
from aerona.engine.collective.feelings import feelings_of
from aerona.engine.context import TickContext
from aerona.engine.feeling_spread.lean import mood_lean
from aerona.engine.feeling_spread.moods import MoodTally, blended, measured_by_place, spread_along_bonds, spread_in_households, spread_in_places, tend_moods
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
    assert (await feelings_of(session, town.id))[CrowdFeeling.FEAR] > 0
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


async def test_a_household_mood_is_told_of_its_head_never_of_the_node_sharing_its_number(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "hearth", tuned_rules(feeling_spread={"told_at": 5}))
    town = await settlement(session, "Hearthmere", world, world.regions[0], population=500)
    head = await mortal(session, "Ilse Varn", world, town.id)
    home = HouseholdRow(name="House Varn", head_node_id=head.id, settlement_node_id=town.id, locked=[])
    session.add(home)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=head.id, household_id=home.id, role=next(iter(HouseholdRole))))
    await think(session, ctx.rules, head.id, ThoughtKind.MARRIED, ctx.epoch, intensity=70, forced=True)
    await spread_in_households(ctx, MoodTally())
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "mood.spread_household"))
    assert told is not None
    subjects = set(await session.scalars(select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == told.id)))
    assert subjects == {head.id}
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "mood.spread")) is None


async def test_a_place_mood_is_the_mean_of_each_residents_strongest_feeling(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "measure", tuned_rules())
    town = await settlement(session, "Fearwick", world, world.regions[0], population=500)
    afraid, calm = await mortal(session, "Afraid One", world, town.id), await mortal(session, "Calm Two", world, town.id)
    for intensity in (90, 80, 70):
        await think(session, ctx.rules, afraid.id, ThoughtKind.FELT_UNSAFE, ctx.epoch, intensity=intensity, forced=True)
    measured, counts = await measured_by_place(ctx)
    strongest = await session.scalar(select(func.max(ThoughtRow.intensity)).where(ThoughtRow.holder_node_id == afraid.id))
    assert counts[town.id] == 2 and calm.id != afraid.id
    assert measured[town.id][Emotion.FEAR] == float(strongest or 0) / 2 < 100


def test_a_mood_fades_by_its_share_and_a_weaker_feeling_never_lifts_it() -> None:
    mixed = blended(20, {"fear": 100}, {Emotion.FEAR: 30.0, Emotion.JOY: 60.0})
    assert mixed == {"fear": 80, "joy": 60}
