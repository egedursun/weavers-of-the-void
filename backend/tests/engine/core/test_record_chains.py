from dataclasses import replace

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.sequence import AFTER_KINDS, FOLLOWS, matching
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.node import NodeBirthRow
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import ProcessClock
from aerona.domain.enums.settlement import DistrictHarm, DistrictKind
from aerona.domain.enums.statecraft import MandateKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import MortalStats, SettlementStats
from aerona.domain.models.moment import Moment
from aerona.engine.context import TickContext
from aerona.engine.recording.chains import anchor_at, happening_clock
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import recording
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, seed_core_world
from tests.engine.cosmos.factories import tick

TOWNS = 12


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
