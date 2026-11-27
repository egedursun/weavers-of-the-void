from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.chronicle import EPOCH_CLOSE, record_line
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeBirthRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.gathering import GatheringKind, GatheringStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.models.calendar import epoch_end_year
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import AgingState, TickContext
from aerona.engine.cycles.lineage import breeds
from aerona.engine.gatherings.hold import rite_floor
from aerona.engine.lifecycle.mortal_death import age_at_death, death_moment
from aerona.engine.phases.births import bear_child
from aerona.engine.phases.mortals import mortal_aging, years_lived
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal


async def sexed(session: AsyncSession, name: str, world: CoreWorld, sex: SexKind) -> EntityRow:
    stats = MortalStats(hp=60, strength=40, agility=40, intellect=40, charisma=40, age=25, lifespan=70, sex=sex.value)
    return await entity(session, name, EntityType.MORTAL, stats, world_id=world.world.id, location_id=world.regions[0].id)


async def test_two_begetters_conceive_nothing_but_a_bearer_and_a_begetter_do(session: AsyncSession, world: CoreWorld) -> None:
    first = await sexed(session, "First Begetter", world, SexKind.BEGETTER)
    second = await sexed(session, "Second Begetter", world, SexKind.BEGETTER)
    bearer = await sexed(session, "The Bearer", world, SexKind.BEARER)
    assert not await breeds(session, first, second)
    assert await breeds(session, first, bearer)
    assert await breeds(session, bearer, second)


async def test_a_mortal_born_late_in_the_age_lives_only_the_years_left_of_it(ctx: TickContext, world: CoreWorld) -> None:
    child = await mortal(ctx.session, "Late Child", world, world.regions[0].id, age=0)
    end = epoch_end_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    assert years_lived(ctx, child, end - 4) == 4
    assert years_lived(ctx, child, None) == ctx.rules.world_engine.first_epoch_years_son


async def test_a_child_is_born_before_anything_is_told_of_it(ctx: TickContext, world: CoreWorld) -> None:
    first = await sexed(ctx.session, "Blessed Begetter", world, SexKind.BEGETTER)
    first.creator_son_id = world.son.id
    second = await sexed(ctx.session, "Blessed Bearer", world, SexKind.BEARER)
    child = await bear_child(ctx, first, second)
    await ctx.session.flush()
    birth = await ctx.session.get(NodeBirthRow, child.id)
    assert birth is not None
    told = select(IncidentRow.kind, IncidentRow.year).join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
    rows = (await ctx.session.execute(told.where(IncidentParticipantRow.node_id == child.id))).all()
    assert rows
    assert all(year is not None and year >= birth.year for _, year in rows), rows
    assert ("births.child", birth.year) in rows


async def test_the_first_record_of_a_new_thing_dates_its_coming_into_being(ctx: TickContext, world: CoreWorld) -> None:
    newcomer = await mortal(ctx.session, "Newcomer", world, world.regions[0].id)
    await record(ctx, "lifecycle.affairs_closed", roles={IncidentRole.SUBJECT: newcomer.id}, facts={"affairs": 1, "ties": 0})
    await ctx.session.flush()
    first = await ctx.session.scalar(
        select(IncidentRow)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id == newcomer.id)
    )
    birth = await ctx.session.get(NodeBirthRow, newcomer.id)
    assert first is not None and birth is not None
    assert birth.year == first.year


async def test_a_child_dead_in_its_birth_year_dies_at_no_age(ctx: TickContext, world: CoreWorld) -> None:
    child = await mortal(ctx.session, "Short Life", world, world.regions[0].id, age=6)
    end = epoch_end_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    born = await record(ctx, "lifecycle.affairs_closed", roles={IncidentRole.SUBJECT: child.id}, facts={"affairs": 1, "ties": 0})
    ctx.session.add(IncidentParticipantRow(incident_id=born.incident_id, node_id=child.id, role=IncidentRole.CHILD, position=1))
    birth = await ctx.session.get(NodeBirthRow, child.id)
    assert birth is not None
    birth.year = end - 6
    await ctx.session.flush()
    after = in_phase(ctx, EpochPhase.ENGINE, AgingState(done=True))
    assert await age_at_death(after, child, end - 6) == 0
    assert await age_at_death(after, child, end - 3) == 3


def in_phase(ctx: TickContext, phase: EpochPhase, aging: AgingState | None = None) -> TickContext:
    return TickContext(replace(ctx.environment, phase=phase, aging=aging), ctx.session, ctx.phase)


async def test_one_who_dies_after_the_years_were_added_dies_at_the_age_reached_that_year(ctx: TickContext, world: CoreWorld) -> None:
    elder = await mortal(ctx.session, "Aged Elder", world, world.regions[0].id, age=70)
    elder.birth_epoch = ctx.epoch - 1
    end = epoch_end_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    start = end - ctx.rules.time.years_per_epoch
    assert await age_at_death(in_phase(ctx, EpochPhase.ENGINE, AgingState(done=True)), elder, end - 20) == 50
    assert await age_at_death(in_phase(ctx, EpochPhase.FATE), elder, end - 5) == 65
    assert await age_at_death(in_phase(ctx, EpochPhase.ENGINE, AgingState()), elder, start + 10) == 80
    assert await age_at_death(in_phase(ctx, EpochPhase.GODS), elder, start + 4) == 74
    assert await age_at_death(ctx, elder, start + 4) == 70


async def test_deaths_of_old_age_spread_over_the_age_instead_of_its_last_year(ctx: TickContext, world: CoreWorld) -> None:
    years: set[int] = set()
    start = epoch_end_year(ctx.epoch, ctx.rules.time.years_per_epoch) - ctx.rules.time.years_per_epoch
    for index in range(12):
        elder = await mortal(ctx.session, f"Spent Elder {index}", world, world.regions[0].id, age=95)
        elder.birth_epoch = ctx.epoch - 1
        set_stats(elder, lifespan=30)
        await mortal_aging(in_phase(ctx, EpochPhase.ENGINE, AgingState()))
        if elder.status is EntityStatus.DEAD:
            died = stat_or(elder, "death_year", 0)
            years.add(died)
            assert stat_or(elder, "age", 0) == 95 + died - start
    assert len(years) > 1


async def test_a_death_given_a_year_happens_in_that_year(ctx: TickContext, world: CoreWorld) -> None:
    elder = await mortal(ctx.session, "Dated Elder", world, world.regions[0].id, age=60)
    end = epoch_end_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    moment = await death_moment(ctx, elder, None, None, end - 30)
    assert moment.year == end - 30


async def test_a_wake_is_never_held_before_the_death_it_honours(ctx: TickContext, world: CoreWorld) -> None:
    host = await mortal(ctx.session, "Mourning Host", world, world.regions[0].id)
    honoured = await mortal(ctx.session, "The Mourned", world, world.regions[0].id, death_year=40)
    honoured.status, honoured.end_epoch = EntityStatus.DEAD, ctx.epoch
    row = GatheringRow(host_node_id=host.id, kind=GatheringKind.WAKE, status=GatheringStatus.PLANNED, honoured_node_id=honoured.id, epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    floor = await rite_floor(ctx, row)
    assert floor is not None
    assert floor.year >= 40


async def test_a_wedding_of_one_who_died_later_keeps_its_own_year(ctx: TickContext, world: CoreWorld) -> None:
    host = await mortal(ctx.session, "Wedding Host", world, world.regions[0].id)
    honoured = await mortal(ctx.session, "Wed Then Gone", world, world.regions[0].id, death_year=40)
    honoured.status, honoured.end_epoch = EntityStatus.DEAD, ctx.epoch
    row = GatheringRow(
        host_node_id=host.id, kind=GatheringKind.WEDDING, status=GatheringStatus.PLANNED, honoured_node_id=honoured.id, epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    floor = await rite_floor(ctx, row)
    assert floor is None or floor.year < 40


async def test_the_fate_judgment_is_told_at_the_close_of_the_age(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    await record_line(
        session,
        rules,
        "fate.reward",
        roles={IncidentRole.BENEFICIARY: world.son.id},
        facts={"fame": 3, "xp": 3, "detail": "."},
        kind=ChronicleKind.FATE,
        son_id=world.son.id,
        progress=EPOCH_CLOSE,
    )
    line = await session.scalar(select(ChronicleRow).where(ChronicleRow.template_key == "fate.reward"))
    assert line is not None
    assert line.year == epoch_end_year(world.cosmos.epoch, rules.time.years_per_epoch) - 1


async def test_a_child_who_grows_up_over_the_age_is_no_longer_a_child_once_aged(ctx: TickContext, world: CoreWorld) -> None:
    grower = await mortal(ctx.session, "Quick Grower", world, world.regions[0].id, age=5)
    grower.birth_epoch = ctx.epoch - 1
    set_stats(grower, lifespan=300)
    profile = await ctx.session.get(MortalProfileRow, grower.id)
    if profile is None:
        profile = MortalProfileRow(entity_id=grower.id)
        ctx.session.add(profile)
    profile.life_stage = LifeStage.CHILD
    await ctx.session.flush()
    await mortal_aging(in_phase(ctx, EpochPhase.ENGINE, AgingState()))
    assert stat_or(grower, "age", 0) == 5 + ctx.rules.time.years_per_epoch
    assert profile.life_stage is not LifeStage.CHILD
