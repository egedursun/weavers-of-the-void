from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.labour import STANDING_COVERAGE_PCT
from aerona.catalog.life.labour import UNION_TRADES
from aerona.catalog.life_traits import FACTION_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import Job
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.labour import LegalStanding, WorkerBodyForm
from aerona.domain.enums.life_traits import FactionKindTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

BODY_KINDS = having(FACTION_KIND_TRAITS, FactionKindTrait.BODY_KINDS)
SOLIDARITY_REST = 50
COVERED = (SocialClass.WORKER, SocialClass.ARTISAN)


@dataclass(frozen=True)
class Parties:
    body: WorkerBodyRow
    hirer: EntityRow
    community: EntityRow
    trade: Job


@dataclass
class LabourTally:
    founded: int = 0
    banned: int = 0
    prosecuted: int = 0
    agreed: int = 0
    broken: int = 0
    expired: int = 0
    strikes: int = 0
    lockouts: int = 0
    ended: int = 0
    spread: int = 0
    claimed: int = 0


def trades_of(body: WorkerBodyRow) -> list[Job]:
    known = {job.value: job for job in Job}
    return [known[value] for value in body.trades or [] if value in known]


async def body_of(session: AsyncSession, node_id: int | None) -> WorkerBodyRow | None:
    return await session.get(WorkerBodyRow, node_id) if node_id is not None else None


async def home_of(session: AsyncSession, body: WorkerBodyRow) -> EntityRow | None:
    profile = await session.get(FactionProfileRow, body.faction_node_id)
    return await living_entity(session, profile.home_entity_id) if profile is not None else None


async def place_of(session: AsyncSession, town_id: int | None, *parties: int | None) -> int | None:
    if town_id is not None:
        return town_id
    for node in parties:
        if node is None:
            continue
        profile = await session.get(FactionProfileRow, node)
        if profile is not None and profile.home_entity_id is not None:
            return profile.home_entity_id
        entity = await session.get(EntityRow, node)
        if entity is not None and entity.location_id is not None:
            return entity.location_id
    return None


async def standing_at(session: AsyncSession, place_id: int) -> LegalStanding:
    unions = await law_param(session, place_id, LawKind.LABOUR_LAW, "unions")
    if unions is None:
        return LegalStanding.TOLERATED
    if not unions:
        return LegalStanding.BANNED
    return LegalStanding(str(await law_param(session, place_id, LawKind.LABOUR_LAW, "bodies")))


async def max_hours_at(session: AsyncSession, place_id: int) -> int | None:
    value = await law_param(session, place_id, LawKind.LABOUR_LAW, "max_hours")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


async def trade_workers(session: AsyncSession, community_id: int, trades: list[Job]) -> int:
    if not trades:
        return 0
    rows = await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community_id, LabourRow.job.in_(trades)))
    return sum(row.workers for row in rows)


async def bodies_at(session: AsyncSession, community_id: int) -> list[WorkerBodyRow]:
    query = (
        select(WorkerBodyRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == WorkerBodyRow.faction_node_id)
        .where(FactionProfileRow.home_entity_id == community_id)
        .order_by(WorkerBodyRow.faction_node_id)
    )
    return list(await session.scalars(query))


async def body_covering(session: AsyncSession, community_id: int, trade: Job) -> WorkerBodyRow | None:
    return next((body for body in await bodies_at(session, community_id) if trade in trades_of(body)), None)


def new_body(ctx: TickContext, faction_id: int, form: WorkerBodyForm, trades: list[Job], standing: LegalStanding) -> WorkerBodyRow:
    body = WorkerBodyRow(
        faction_node_id=faction_id,
        form=form,
        trades=sorted({trade.value for trade in trades}),
        works=[],
        members=0,
        dues=ctx.rules.labour.fund_per_member,
        fund=0,
        solidarity=SOLIDARITY_REST,
        standing=standing,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(body)
    return body


async def ensure_rows(ctx: TickContext) -> int:
    query = select(FactionProfileRow).where(
        FactionProfileRow.kind.in_(sorted(BODY_KINDS)), FactionProfileRow.faction_entity_id.not_in(select(WorkerBodyRow.faction_node_id))
    )
    made = 0
    for profile in await ctx.session.scalars(query.order_by(FactionProfileRow.faction_entity_id)):
        if held(profile.faction_entity_id):
            continue
        union = profile.kind is FactionKind.WORKERS_UNION
        place = profile.home_entity_id
        standing = await standing_at(ctx.session, place) if place is not None else LegalStanding.TOLERATED
        new_body(ctx, profile.faction_entity_id, WorkerBodyForm.INDUSTRIAL_UNION if union else WorkerBodyForm.GENERAL_UNION, list(UNION_TRADES), standing)
        made += 1
    await ctx.session.flush()
    return made


async def prosecute(ctx: TickContext, body: WorkerBodyRow, home: EntityRow, tally: LabourTally) -> None:
    table = ctx.rules.labour
    if not ctx.rng(f"labour.prosecute.{body.faction_node_id}.{ctx.epoch}").chance(table.banned_body_prosecution_pct):
        return
    seized = round_half_up(body.fund * table.prosecution_fund_pct / PERCENT)
    if "fund" not in (body.locked or []):
        body.fund -= seized
    if "members" not in (body.locked or []):
        body.members //= 2
    tally.prosecuted += 1
    await record(
        ctx,
        "labour.body_banned",
        roles={IncidentRole.SUBJECT: body.faction_node_id, IncidentRole.PLACE: home.id},
        facts={"seized": seized, "standing": LegalStanding.BANNED},
        place=home.id,
    )


async def discontent(session: AsyncSession, community_id: int) -> int:
    society = await session.get(CommunitySocietyRow, community_id)
    if society is None:
        return SOLIDARITY_REST
    content = sum(society.satisfaction(social) for social in COVERED) / len(COVERED)
    return clamp_int(round_half_up(PERCENT - content), 0, PERCENT)


async def tend_body(ctx: TickContext, body: WorkerBodyRow, tally: LabourTally) -> None:
    home = await home_of(ctx.session, body)
    if home is None or held(body.faction_node_id) or held(home.id):
        return
    locked = body.locked or []
    standing = await standing_at(ctx.session, home.id)
    if standing is not body.standing and "standing" not in locked:
        body.standing = standing
        if standing is LegalStanding.BANNED:
            tally.banned += 1
            await record(
                ctx,
                "labour.body_banned",
                roles={IncidentRole.SUBJECT: body.faction_node_id, IncidentRole.PLACE: home.id},
                facts={"seized": 0, "standing": standing},
                place=home.id,
            )
    workers = await trade_workers(ctx.session, home.id, trades_of(body))
    coverage = PERCENT if body.standing is LegalStanding.COMPULSORY else STANDING_COVERAGE_PCT[body.standing] + (body.solidarity - SOLIDARITY_REST) // 2
    if "members" not in locked:
        body.members = round_half_up(workers * clamp_int(coverage, 0, PERCENT) / PERCENT)
    if "fund" not in locked:
        body.fund += body.members * body.dues
    if "solidarity" not in locked:
        aim = await discontent(ctx.session, home.id)
        body.solidarity = clamp_int(body.solidarity + round_half_up((aim - body.solidarity) * ctx.rules.labour.solidarity_drift_pct / PERCENT), 0, PERCENT)
    if body.standing is LegalStanding.BANNED:
        await prosecute(ctx, body, home, tally)
