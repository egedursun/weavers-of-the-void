from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fortune import FortuneProfileRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import AccusationOutcome
from aerona.domain.enums.gathering import AttendanceReason, GatheringKind, GuestRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import MortalStats, PolityStats
from aerona.engine.agentless_conditions.arise import ConditionTally
from aerona.engine.agentless_conditions.course import tend_courses
from aerona.engine.feeling_spread.moods import household_head
from aerona.engine.fortune.profiles import keep_fortune
from aerona.engine.gatherings.hold import invite
from aerona.engine.gatherings.occasions import Guest
from aerona.engine.recording.record import record
from aerona.engine.restoration.rise import standing_claimant
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, seed_core_world
from tests.engine.cosmos.factories import tick, tuned

ACCUSED = 12
OUTCOME = next(iter(AccusationOutcome))


async def bearer(session: AsyncSession, world: CoreWorld, name: str, *, dead: bool) -> EntityRow:
    mortal = await entity(session, name, EntityType.MORTAL, MortalStats(age=60, death_year=10 if dead else None), world_id=world.world.id)
    if dead:
        mortal.status, mortal.end_epoch = EntityStatus.DEAD, 1
    session.add(
        ConditionRow(
            bearer_node_id=mortal.id,
            kind=next(iter(ConditionKind)),
            severity=2,
            source=next(iter(HarmCause)),
            since_epoch=1,
            cause=ConditionCause.AGE,
        )
    )
    await session.flush()
    return mortal


async def told_of(session: AsyncSession, node_id: int) -> list[str]:
    told = select(IncidentRow.kind).join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
    return list(await session.scalars(told.where(IncidentParticipantRow.node_id == node_id, IncidentRow.kind.like("body.condition%"))))


async def test_a_condition_of_the_dead_neither_heals_nor_worsens(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    living = await bearer(session, world, "Still Breathing", dead=False)
    dead = await bearer(session, world, "Long Buried", dead=True)
    await tend_courses(tick(session, tuned(rules, "agentless_conditions", ease_pct=100)), ConditionTally())
    assert await told_of(session, living.id)
    assert await told_of(session, dead.id) == []
    still = await session.scalar(select(ConditionRow.severity).where(ConditionRow.bearer_node_id == dead.id))
    assert still == 2


async def test_the_mood_of_a_household_is_never_told_of_a_dead_head(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    head = await entity(session, "Late Head", EntityType.MORTAL, MortalStats(age=70), world_id=world.world.id)
    household = HouseholdRow(name="Late Head's hearth", head_node_id=head.id, formed_epoch=1, debts={}, locked=[])
    session.add(household)
    await session.flush()
    assert await household_head(tick(session, Rules()), household) == head
    head.status, head.end_epoch = EntityStatus.DEAD, 1
    assert await household_head(tick(session, Rules()), household) is None


async def test_a_dead_claimant_never_leads_a_restoration(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    fallen = await entity(session, "Fallen Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    claimant = await entity(session, "Old Pretender", EntityType.MORTAL, MortalStats(age=50), world_id=world.world.id)
    row = RestorationRow(fallen_polity_id=fallen.id, claimant_node_id=claimant.id, territories=[], bases=[])
    session.add(row)
    await session.flush()
    ctx = tick(session, rules)
    assert await standing_claimant(ctx, row) == claimant.id
    claimant.status, claimant.end_epoch = EntityStatus.DEAD, 1
    assert await standing_claimant(ctx, row) is None


async def test_a_record_naming_the_dead_in_a_living_role_stands_no_later_than_the_death(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    died = epoch_start_year(ctx.epoch, rules.time.years_per_epoch) + 3
    town = world.regions[0].id
    for index in range(ACCUSED):
        accused = await entity(session, f"Accused {index}", EntityType.MORTAL, MortalStats(age=40, death_year=died), world_id=world.world.id)
        accused.status, accused.end_epoch = EntityStatus.DEAD, ctx.epoch
        await session.flush()
        written = await record(
            ctx, "hunt.accusation", roles={IncidentRole.ACCUSED: accused.id, IncidentRole.PLACE: town}, facts={"outcome": OUTCOME}, place=town
        )
        told = await session.get(IncidentRow, written.incident_id)
        assert told is not None and told.year is not None and told.year <= died


async def test_the_dead_are_never_asked_to_a_gathering_and_keep_no_fortune(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    host = await entity(session, "Living Host", EntityType.MORTAL, MortalStats(age=40), world_id=world.world.id)
    friend = await entity(session, "Living Friend", EntityType.MORTAL, MortalStats(age=40), world_id=world.world.id)
    gone = await entity(session, "Gone Friend", EntityType.MORTAL, MortalStats(age=70, death_year=2), world_id=world.world.id)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1
    held_away = await entity(session, "Held Friend", EntityType.MORTAL, MortalStats(age=40), world_id=world.world.id)
    session.add(CaptiveRow(captive_entity_id=held_away.id, captor_entity_id=world.regions[1].id, taken_epoch=1, locked=[]))
    session.add(FortuneProfileRow(node_id=gone.id, fortune=3, streak=1, updated_epoch=1, locked=[]))
    gathering = GatheringRow(host_node_id=host.id, kind=next(iter(GatheringKind)), epoch=ctx.epoch, locked=[])
    session.add(gathering)
    await session.flush()
    await invite(ctx, gathering, [Guest(being.id, GuestRole.GUEST, AttendanceReason.FRIEND) for being in (friend, gone, held_away)])
    asked = set(await session.scalars(select(GatheringGuestRow.node_id).where(GatheringGuestRow.gathering_id == gathering.id)))
    assert friend.id in asked and gone.id not in asked and held_away.id not in asked
    await keep_fortune(ctx)
    kept = await session.get(FortuneProfileRow, gone.id)
    assert kept is not None and (kept.fortune, kept.updated_epoch) == (3, 1)
