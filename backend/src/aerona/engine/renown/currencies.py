from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.domain import OUTLAW_KINDS
from aerona.catalog.life_traits import ACT_KIND_TRAITS, having
from aerona.catalog.renown import GLORIOUS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.museums import MuseumPieceRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.renown import RulerCurrencyRow
from aerona.db.write_guard import held
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.life_traits import ActKindTrait
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.renown import Currency, ReputationAxis
from aerona.engine.context import TickContext
from aerona.engine.loops.delay import lagged
from aerona.engine.museums.reading import grandeur
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.renown.book import among

FEARSOME = having(ACT_KIND_TRAITS, ActKindTrait.FEARSOME)
PIOUS = frozenset({ReputationAxis.PIETY})


@dataclass
class CurrencyTally:
    rulers: int = 0
    clergy: int = 0
    silenced: int = 0
    laws: int = 0


@memoized(OfficeRow)
async def realm_ruled_by(session: AsyncSession, ruler_id: int) -> int | None:
    found = await session.scalar(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == ruler_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    return int(found) if found is not None else None


@memoized(OfficeRow)
async def ruler_of_realm(session: AsyncSession, polity_id: int) -> int | None:
    found = await session.scalar(select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    return int(found) if found is not None else None


@memoized(PolityMemberRow)
async def realm_of_community(session: AsyncSession, community_id: int) -> int | None:
    found = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return int(found) if found is not None else None


@memoized(PolityMemberRow)
async def member_ids(session: AsyncSession, polity_id: int) -> tuple[int, ...]:
    return tuple(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))


async def members_of(session: AsyncSession, polity_id: int) -> list[int]:
    return list(await member_ids(session, polity_id))


async def purse_of(session: AsyncSession, ruler_id: int, epoch: int) -> RulerCurrencyRow | None:
    if held(ruler_id):
        return None
    row = await session.get(RulerCurrencyRow, ruler_id)
    if row is None:
        row = RulerCurrencyRow(subject_node_id=ruler_id, prestige=0, piety=0, dread=0, tyranny=0, updated_epoch=epoch, locked=[])
        session.add(row)
        await session.flush()
    return row


def bump(row: RulerCurrencyRow, currency: Currency, amount: float) -> None:
    if currency.value in row.locked:
        return
    setattr(row, currency.value, clamp_int(getattr(row, currency.value) + amount, 0, PERCENT))


async def on_act(ctx: TickContext, actor_id: int, act: ActKind, reading: int, community_id: int) -> None:
    realm = await realm_ruled_by(ctx.session, actor_id)
    if realm is None:
        return
    row = await purse_of(ctx.session, actor_id, ctx.epoch)
    if row is None:
        return
    if act in FEARSOME:
        bump(row, Currency.DREAD, ctx.rules.currencies.dread_execution)
    if reading < 0 and community_id in await members_of(ctx.session, realm):
        bump(row, Currency.TYRANNY, ctx.rules.currencies.tyranny_act)


async def on_victory(ctx: TickContext, community_id: int) -> None:
    realm = await realm_of_community(ctx.session, community_id)
    ruler = await ruler_of_realm(ctx.session, realm) if realm is not None else None
    row = await purse_of(ctx.session, ruler, ctx.epoch) if ruler is not None else None
    if row is not None:
        bump(row, Currency.DREAD, ctx.rules.currencies.dread_victory)


async def hostile_factions(session: AsyncSession, members: list[int]) -> list[FactionProfileRow]:
    query = select(FactionProfileRow).where(FactionProfileRow.home_entity_id.in_(members), FactionProfileRow.kind.in_(list(OUTLAW_KINDS)))
    return list(await session.scalars(query.order_by(FactionProfileRow.faction_entity_id)))


async def court_clergy(ctx: TickContext, row: RulerCurrencyRow, members: list[int], tally: CurrencyTally) -> None:
    table = ctx.rules.currencies
    priests = await ctx.session.scalars(
        select(FactionProfileRow).where(FactionProfileRow.home_entity_id.in_(members), FactionProfileRow.kind == FactionKind.PRIESTHOOD)
    )
    for priesthood in priests:
        if row.piety < table.clergy_cost or priesthood.loyalty >= table.clergy_below or "loyalty" in priesthood.locked or held(priesthood.faction_entity_id):
            continue
        bump(row, Currency.PIETY, -table.clergy_cost)
        priesthood.loyalty = clamp_int(priesthood.loyalty + table.clergy_loyalty, 0, PERCENT)
        tally.clergy += 1


async def silence(ctx: TickContext, row: RulerCurrencyRow, members: list[int], tally: CurrencyTally) -> None:
    table = ctx.rules.currencies
    if row.dread < table.silence_cost or (row.silenced_until or -1) >= ctx.epoch or "silenced_until" in row.locked:
        return
    if len(await hostile_factions(ctx.session, members)) < table.silence_pressure:
        return
    bump(row, Currency.DREAD, -table.silence_cost)
    row.silenced_until = ctx.epoch + table.silence_epochs
    await record(
        ctx,
        "ruler.silenced",
        roles={IncidentRole.ACTOR: row.subject_node_id},
        facts={"dread_spent": table.silence_cost, "epochs": table.silence_epochs},
    )
    tally.silenced += 1


async def amends(ctx: TickContext, polity_id: int, members: list[int]) -> int:
    places = [polity_id, *members]
    mercy = await ctx.session.scalar(
        select(func.count())
        .select_from(CrimeCaseRow)
        .where(
            CrimeCaseRow.closed_epoch == ctx.epoch,
            CrimeCaseRow.verdict.in_([Verdict.ACQUITTED, Verdict.DROPPED]),
            or_(CrimeCaseRow.polity_entity_id.in_(places), CrimeCaseRow.settlement_entity_id.in_(places)),
        )
    )
    returned = await ctx.session.scalar(
        select(func.count()).select_from(MuseumPieceRow).where(MuseumPieceRow.returned_epoch == ctx.epoch, MuseumPieceRow.returned_by_entity_id.in_(places))
    )
    return int(mercy or 0) + int(returned or 0)


async def tend_currencies(ctx: TickContext, tally: CurrencyTally) -> None:
    table = ctx.rules.currencies
    rulers = await ctx.session.execute(
        select(OfficeRow.holder_entity_id, OfficeRow.polity_entity_id).where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
    )
    for ruler_id, polity_id in sorted(rulers.all(), key=lambda item: (item[1], item[0] or 0)):
        if ruler_id is None or held(polity_id):
            continue
        row = await purse_of(ctx.session, ruler_id, ctx.epoch)
        if row is None:
            continue
        members = await members_of(ctx.session, polity_id)
        if Currency.PRESTIGE.value not in row.locked:
            won = max(
                await among(ctx.session, ruler_id, members, GLORIOUS) * table.prestige_pct / PERCENT,
                float(await grandeur(ctx.session, ctx.rules, [polity_id, *members])),
            )
            row.prestige = clamp_int(max(row.prestige - table.prestige_fade, won), 0, PERCENT)
        if Currency.PIETY.value not in row.locked:
            row.piety = clamp_int(max(row.piety, await among(ctx.session, ruler_id, members, PIOUS) * table.piety_pct / PERCENT), 0, PERCENT)
        bump(row, Currency.DREAD, -table.dread_fade)
        bump(row, Currency.TYRANNY, -round_half_up(table.tyranny_fade * (1 + await amends(ctx, polity_id, members) * table.amends_pct / PERCENT)))
        row.updated_epoch = ctx.epoch
        await court_clergy(ctx, row, members, tally)
        await silence(ctx, row, members, tally)
        tally.rulers += 1
    await ctx.session.flush()


async def realm_purse(session: AsyncSession, polity_id: int | None) -> RulerCurrencyRow | None:
    ruler = await ruler_of_realm(session, polity_id) if polity_id is not None else None
    return await session.get(RulerCurrencyRow, ruler) if ruler is not None else None


async def restraint(ctx: TickContext, polity_id: int | None) -> tuple[float, float]:
    row = await realm_purse(ctx.session, polity_id)
    if row is None:
        return 1.0, 1.0
    if (row.silenced_until or -1) >= ctx.epoch:
        return 0.0, 1.0
    table = ctx.rules.currencies
    suppress = 1 - table.dread_suppress_pct / PERCENT * row.dread / PERCENT
    tyranny = await lagged(ctx, BalanceLoop.TYRANNY_CONCESSIONS, polity_id, row.tyranny)
    press = 1 + table.tyranny_pressure_pct / PERCENT * tyranny / PERCENT
    return max(0.0, suppress), press


async def spend_prestige(ctx: TickContext, ruler_id: int | None) -> float:
    table = ctx.rules.currencies
    row = await ctx.session.get(RulerCurrencyRow, ruler_id) if ruler_id is not None else None
    if row is None or held(ruler_id or 0) or row.prestige < table.law_cost or Currency.PRESTIGE.value in row.locked:
        return 1.0
    row.prestige -= table.law_cost
    return 1 + table.law_bonus_pct / PERCENT
