from dataclasses import replace

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.sequence import AFTER_KINDS, FOLLOWS, RITE_YEARS, matching
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactUnit, ProcessClock
from aerona.domain.enums.settlement import DistrictHarm, DistrictKind
from aerona.domain.enums.statecraft import MandateKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import MortalStats, RegionStats, SettlementStats
from aerona.domain.models.moment import Moment
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.chains import anchor_at, happening_clock
from aerona.engine.recording.moments import moment_for
from aerona.engine.recording.record import FactInput, record
from aerona.engine.recording.scope import recording
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, mortal, seed_core_world
from tests.engine.cosmos.factories import tick

TOWNS = 12
DEED_YEARS = (30, 40, 45)
DIED_AFTER = 8
GENESIS_SEEN = 44
NEWCOMER_CAME = 39
NEWCOMER_AGE = 21
ACT_STEPS = 10
ACT_SHARE = 0.1
YEAR_DAYS = 360
SEASONS = 4
DAY_HOURS = 24
NAMED_FACTS: dict[str, FactInput] = {"name": "Second Elder", "living": "Elder", "taboo": 0}


def at_step(ctx: TickContext, step: float, phase: str) -> TickContext:
    return TickContext(replace(ctx.environment, step=step), ctx.session, phase)


async def moment(session: AsyncSession, incident_id: int | None) -> Moment:
    row = await session.get(IncidentRow, incident_id)
    assert row is not None and row.year is not None
    return Moment(row.year, row.season, row.day, row.hour)


def test_every_pattern_of_the_sequence_names_a_kind_on_record() -> None:
    keys = frozenset(INCIDENT_KINDS)
    for effects, causes in FOLLOWS:
        for pattern in (*effects, *causes):
            assert matching((pattern,), keys), f"{pattern} names no kind of happening"
    assert AFTER_KINDS


def test_a_told_happening_is_spread_over_the_years_while_a_steps_bare_writes_keep_its_moment() -> None:
    told = INCIDENT_KINDS["body.maimed"]
    assert told.clock is ProcessClock.PHASE
    assert happening_clock(told) is ProcessClock.INSTANT
    bare = next(spec for spec in INCIDENT_KINDS.values() if not spec.told and spec.clock is ProcessClock.PHASE)
    assert happening_clock(bare) is ProcessClock.PHASE


async def test_what_one_step_tells_of_one_thing_follows_its_cause_while_repeats_stay_apart(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    world.world.year_length_days, world.world.season_count, world.world.day_length_hours = 360, 4, 24
    await session.flush()
    ctx = at_step(tick(session, rules), 0.4, "test_step")
    realm = world.regions[0].id
    issued = []
    for kind in [*MandateKind][:TOWNS]:
        mandate = await record(
            ctx, "mandate.issued", roles={IncidentRole.AUTHORITY: realm}, facts={"mandate": kind, "until": ctx.epoch + 1}, world_id=world.world.id
        )
        issued.append(await moment(session, mandate.incident_id))
        failed = await record(
            ctx, "affairs.mandate_failed", roles={IncidentRole.AUTHORITY: realm}, facts={"mandate": kind, "legitimacy_lost": 1}, world_id=world.world.id
        )
        assert not (await moment(session, failed.incident_id)).before(max(issued, key=Moment.key))
    assert len({told.year for told in issued}) > 1


async def test_what_follows_a_happening_of_another_step_never_stands_before_it(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    base = tick(session, rules)
    towns = [region.id for region in world.regions]
    for town in towns:
        ruined = await record(
            at_step(base, 0.1, "ruin"), "deepened.town_ruined", roles={IncidentRole.SUBJECT: town}, facts={"cause": RebuildCause.FIRE}, place=town
        )
        rebuilt = await record(
            at_step(base, 0.9, "rebuild"), "settlement.rebuilt", roles={IncidentRole.SUBJECT: town}, facts={"cause": RebuildCause.FIRE}, place=town
        )
        assert not (await moment(session, rebuilt.incident_id)).before(await moment(session, ruined.incident_id))
    realm = towns[0]
    for index, kind in enumerate([*MandateKind][:TOWNS]):
        issued = await record(
            at_step(base, 0.8, f"issue{index}"), "mandate.issued", roles={IncidentRole.AUTHORITY: realm}, facts={"mandate": kind, "until": base.epoch + 1}
        )
        failed = await record(
            at_step(base, 0.2, f"fail{index}"), "affairs.mandate_failed", roles={IncidentRole.AUTHORITY: realm}, facts={"mandate": kind, "legitimacy_lost": 1}
        )
        assert not (await moment(session, failed.incident_id)).before(await moment(session, issued.incident_id))


async def test_the_aftermath_of_a_battle_stands_at_the_battle_and_not_years_away(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = at_step(tick(session, rules), 0.95, "warfare")
    side = world.regions[1].id
    fought = Moment(ctx.epoch * rules.time.years_per_epoch + 7, 1)
    anchor_at(ctx, [side], fought)
    written = await record(ctx, "body.maimed", roles={IncidentRole.SUBJECT: side}, facts={"maim": MaimedKind.ONE_ARMED, "count": 3})
    after = await moment(session, written.incident_id)
    assert not after.before(fought)
    assert after.year == fought.year


async def test_a_grown_mortal_first_on_record_was_born_as_many_years_before_as_their_age(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    grown = await entity(session, "Grey Captain", EntityType.MORTAL, MortalStats(age=44), world_id=world.world.id, birth_epoch=ctx.epoch)
    await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == grown.id))
    written = await record(ctx, "body.maimed", roles={IncidentRole.SUBJECT: grown.id}, facts={"maim": MaimedKind.ONE_ARMED, "count": 1})
    told = await moment(session, written.incident_id)
    born = await session.get(NodeBirthRow, grown.id)
    assert born is not None and born.year == told.year - 44


async def test_what_a_happening_set_off_moves_with_it_when_the_happening_is_dated_later(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    region = world.regions[0].id
    late = Moment(epoch_start_year(ctx.epoch, rules.time.years_per_epoch) + rules.time.years_per_epoch - 1)
    newcomer = await entity(session, "Late Hamlet", EntityType.SETTLEMENT, SettlementStats(population=10), world_id=world.world.id, location_id=region)
    await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == newcomer.id))
    session.add(NodeBirthRow(node_id=newcomer.id, year=late.year, season=None, day=None, hour=None, locked=[]))
    town = await entity(session, "Old Town", EntityType.SETTLEMENT, SettlementStats(population=10), world_id=world.world.id, location_id=region)
    await session.flush()
    async with recording(ctx, "disasters.drought", place_id=region, world_id=world.world.id, moment=Moment(late.year - 20)) as scope:
        follower = await record(
            ctx,
            "settlement.district_drought",
            roles={IncidentRole.PLACE: town.id},
            facts={"harm": next(iter(DistrictHarm)), "districts": next(iter(DistrictKind)), "destroyed": 1},
            place=town.id,
        )
        await record(
            ctx,
            "disasters.drought",
            roles={IncidentRole.PLACE: region, IncidentRole.SUBJECT: newcomer.id},
            facts={"disaster": Disaster.DROUGHT, "severity": 3, "lost": 0, "dead": 0, "destroyed": 0},
            place=region,
        )
    assert not (await moment(session, follower.incident_id)).before(await moment(session, scope.incident_id))


async def test_a_death_keeps_its_own_year_and_the_deeds_written_later_in_the_epoch_move_before_it(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    elder = await mortal(session, "Old Keeper", world, world.regions[0].id, age=80)
    deeds = []
    for offset in DEED_YEARS:
        written = await record(
            ctx,
            "body.maimed",
            roles={IncidentRole.SUBJECT: elder.id},
            facts={"maim": MaimedKind.ONE_ARMED, "count": 1},
            at_moment=Moment(start + offset),
        )
        deeds.append(written.incident_id)
    follower = await record(
        ctx,
        "body.maimed",
        roles={IncidentRole.SUBJECT: world.regions[1].id},
        facts={"maim": MaimedKind.ONE_ARMED, "count": 2},
        cause=deeds[-1],
        at_moment=Moment(start + DEED_YEARS[-1] + 1),
    )
    died = start + DIED_AFTER
    await die(ctx, elder, natural=True, year=died, manner=DeathCause.OLD_AGE)
    assert stat(elder, "death_year") == died
    for incident_id in deeds:
        row = await session.get(IncidentRow, incident_id)
        assert row is not None and row.year is not None and row.year < died
        line = await session.get(ChronicleRow, row.chronicle_id)
        assert line is None or line.year == row.year
    assert not (await moment(session, follower.incident_id)).before(await moment(session, deeds[-1]))


async def test_a_deed_that_tells_its_own_year_holds_the_death_after_it(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    elder = await mortal(session, "Dated Keeper", world, world.regions[0].id, age=80)
    fixed = await record(
        ctx,
        "body.maimed",
        roles={IncidentRole.SUBJECT: elder.id},
        facts={"maim": MaimedKind.ONE_ARMED, "count": 1},
        at_moment=Moment(start + DEED_YEARS[-1]),
    )
    session.add(IncidentFactRow(incident_id=fixed.incident_id, key="year", position=0, number=start + DEED_YEARS[-1], unit=FactUnit.YEARS))
    await session.flush()
    await die(ctx, elder, natural=True, year=start + DIED_AFTER, manner=DeathCause.OLD_AGE)
    assert stat(elder, "death_year") == start + DEED_YEARS[-1]


async def test_the_rites_after_a_death_fall_close_to_it_and_never_decades_later(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = at_step(tick(session, rules), 0.95, "rites")
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    died = start + DIED_AFTER
    years = []
    for index in range(TOWNS):
        elder = await mortal(session, f"Elder {index}", world, world.regions[0].id, age=80)
        await die(ctx, elder, natural=True, year=died, manner=DeathCause.OLD_AGE)
        async with recording(ctx, "lifecycle.affairs_closed", participants=[elder.id]) as scope:
            await record(ctx, "lifecycle.affairs_closed", roles={IncidentRole.SUBJECT: elder.id}, facts={"affairs": 1, "ties": 1})
        years.append((await moment(session, scope.incident_id)).year)
        named = await record(ctx, "death.named", roles={IncidentRole.SUBJECT: elder.id}, facts=NAMED_FACTS)
        years.append((await moment(session, named.incident_id)).year)
    assert all(died <= year <= died + RITE_YEARS for year in years)


async def test_a_thing_made_in_a_step_is_born_when_it_was_made_and_not_at_its_later_first_record(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    async with recording(ctx, "disasters.drought", place_id=world.regions[0].id, world_id=world.world.id, moment=Moment(start + 3)):
        hamlet = await entity(
            session,
            "Early Hamlet",
            EntityType.SETTLEMENT,
            SettlementStats(population=10),
            world_id=world.world.id,
            location_id=world.regions[0].id,
            birth_epoch=ctx.epoch,
        )
        await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == hamlet.id))
        await session.flush()
    await record(
        ctx,
        "settlement.district_drought",
        roles={IncidentRole.PLACE: hamlet.id},
        facts={"harm": next(iter(DistrictHarm)), "districts": next(iter(DistrictKind)), "destroyed": 1},
        place=hamlet.id,
        at_moment=Moment(start + 40),
    )
    born = await session.get(NodeBirthRow, hamlet.id)
    assert born is not None and born.year <= start + 3


async def test_a_happening_held_back_to_a_bare_year_falls_through_that_year_and_not_on_its_first_hour(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    world.world.year_length_days, world.world.season_count, world.world.day_length_hours = 360, 4, 24
    await session.flush()
    ctx = tick(session, rules)
    late = epoch_start_year(ctx.epoch, rules.time.years_per_epoch) + rules.time.years_per_epoch - 1
    placed = [await moment_for(ctx, ProcessClock.INSTANT, key=f"held.{index}", cause_moment=Moment(late), world_id=world.world.id) for index in range(TOWNS)]
    assert all(moment.year == late for moment in placed)
    assert len({(moment.day, moment.hour) for moment in placed}) > 1


async def test_a_thing_the_creator_made_at_genesis_is_born_at_the_start_of_the_cosmos(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules, epoch=1)
    region = await entity(session, "First Vale", EntityType.REGION, RegionStats(), world_id=world.world.id, birth_epoch=1, origin=EntityOrigin.CREATOR)
    await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == region.id))
    session.add(
        StateChangeRow(
            epoch=1, table_name="entities", row_key=f'{{"id": {region.id}}}', node_id=region.id, operation=LedgerOperation.INSERT, actor_kind=ActorKind.SYSTEM
        )
    )
    await session.flush()
    await record(
        ctx,
        "disasters.drought",
        roles={IncidentRole.PLACE: region.id},
        facts={"disaster": Disaster.DROUGHT, "severity": 3, "lost": 0, "dead": 0, "destroyed": 0},
        place=region.id,
        at_moment=Moment(GENESIS_SEEN),
    )
    born = await session.get(NodeBirthRow, region.id)
    assert born is not None and born.year == 0


async def test_nothing_is_told_of_a_grown_newcomer_before_it_appeared(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    ctx = tick(session, rules)
    start = epoch_start_year(ctx.epoch, rules.time.years_per_epoch)
    came = start + NEWCOMER_CAME
    async with recording(ctx, "disasters.drought", place_id=world.regions[0].id, world_id=world.world.id, moment=Moment(came)):
        newcomer = await mortal(session, "Sudden Elder", world, world.regions[0].id, age=NEWCOMER_AGE)
        newcomer.birth_epoch = ctx.epoch
        await session.flush()
    await session.execute(delete(NodeBirthRow).where(NodeBirthRow.node_id == newcomer.id))
    session.add(NodeBirthRow(node_id=newcomer.id, year=came - NEWCOMER_AGE, season=None, day=None, hour=None, locked=[]))
    await session.flush()
    told = await record(
        ctx,
        "body.maimed",
        roles={IncidentRole.SUBJECT: newcomer.id},
        facts={"maim": MaimedKind.ONE_ARMED, "count": 1},
        at_moment=Moment(came - NEWCOMER_AGE // 2),
    )
    assert (await moment(session, told.incident_id)).year >= came


async def test_acts_placed_by_the_progress_of_an_epoch_fall_through_their_years_not_on_the_first_hour(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    world.world.year_length_days, world.world.season_count, world.world.day_length_hours = YEAR_DAYS, SEASONS, DAY_HOURS
    await session.flush()
    ctx = tick(session, rules)
    placed = [await moment_for(ctx, ProcessClock.INSTANT, key=f"act.{step}", progress=step * ACT_SHARE, world_id=world.world.id) for step in range(ACT_STEPS)]
    assert len({(moment.season, moment.day, moment.hour) for moment in placed}) > 1
    assert all((moment.season, moment.day, moment.hour) != (0, 0, 0) for moment in placed)
    assert [moment.year for moment in placed] == sorted(moment.year for moment in placed)
