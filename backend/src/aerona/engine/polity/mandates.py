from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PER_MILLE, PERCENT
from aerona.core.grammar import spoken
from aerona.db.read_memo import memoized
from aerona.db.tables.affairs import MandateRow, NobleDemandRow
from aerona.db.tables.agrarian import CommonsRow, PreparednessRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import CommonsRule
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.mind import MemoryKind, PressureKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateKind, MandateState, NobleWant
from aerona.engine.agrarian.book import unready
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.memories import remember
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.levies import levy
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.war import ongoing_wars
from aerona.engine.settlement.book import town_of
from aerona.engine.structures.construction import active_at, hasten
from aerona.engine.urban.housing import clear_slums

GRAIN = CommodityKind.GRAIN
WANTS = tuple(NobleWant)
MANDATE_REASON = "a mandate of the realm"
STATE = "state"
LEGITIMACY = "legitimacy"


@dataclass
class MandateTally:
    issued: int = 0
    met: int = 0
    failed: int = 0
    demands: int = 0
    soured: int = 0


async def units_of(ctx: TickContext, community_id: int, commodity: CommodityKind) -> int:
    found = await ctx.session.scalar(
        select(func.coalesce(func.sum(CommunityStockRow.quantity), 0)).where(
            CommunityStockRow.community_entity_id == community_id, CommunityStockRow.commodity == commodity
        )
    )
    return int(found or 0)


@memoized(MandateRow)
async def active_mandates(session: AsyncSession, realm_id: int) -> tuple[MandateRow, ...]:
    return tuple(
        await session.scalars(
            select(MandateRow).where(MandateRow.polity_entity_id == realm_id, MandateRow.state == MandateState.ACTIVE).order_by(MandateRow.id)
        )
    )


async def active(ctx: TickContext, realm: Realm) -> list[MandateRow]:
    return list(await active_mandates(ctx.session, realm.entity.id))


async def issue(
    ctx: TickContext,
    realm: Realm,
    kind: MandateKind,
    *,
    settlement_id: int | None,
    commodity: CommodityKind | None = None,
    district: DistrictKind | None = None,
    amount: int = 0,
) -> MandateRow | None:
    if held(realm.entity.id) or (settlement_id is not None and held(settlement_id)):
        return None
    if any(row.kind is kind and row.settlement_entity_id == settlement_id for row in await active(ctx, realm)):
        return None
    row = MandateRow(
        polity_entity_id=realm.entity.id,
        issuer_node_id=realm.ruler_id,
        kind=kind,
        settlement_entity_id=settlement_id,
        commodity=commodity,
        district=district,
        amount=amount,
        issued_epoch=ctx.epoch,
        until_epoch=ctx.epoch + ctx.rules.affairs.mandate_epochs,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "mandate.issued",
        roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.SUBJECT: settlement_id, IncidentRole.ACTOR: realm.ruler_id},
        facts={"mandate": kind, "until": row.until_epoch},
        place=settlement_id,
    )
    await begin(ctx, realm, row)
    return row


async def ration_share(ctx: TickContext, community_id: int) -> float:
    return 1 - ctx.rules.mandates.ration_death_cut_pct / PERCENT if await rationed(ctx.session, community_id) else 1.0


@memoized(MandateRow)
async def rationed(session: AsyncSession, community_id: int) -> bool:
    found = await session.scalar(
        select(MandateRow.id)
        .where(MandateRow.settlement_entity_id == community_id, MandateRow.kind == MandateKind.RATION, MandateRow.state == MandateState.ACTIVE)
        .limit(1)
    )
    return found is not None


async def begin(ctx: TickContext, realm: Realm, row: MandateRow) -> None:
    if row.kind is MandateKind.EXPORT_BAN and row.commodity is not None:
        ctx.session.add(
            TradePolicyRow(
                issuer_node_id=realm.entity.id, kind=TradePolicyKind.EMBARGO, commodity=row.commodity, since_epoch=ctx.epoch, reason=MANDATE_REASON, locked=[]
            )
        )
    elif row.kind is MandateKind.FAMINE_RELIEF and row.settlement_entity_id is not None and realm.profile.capital_entity_id is not None:
        stocks = goods_of(ctx.session, ctx.epoch)
        lots = await stocks.take(realm.profile.capital_entity_id, GRAIN, row.amount, GoodsFlow.AID)
        moved = sum(lot.quantity for lot in lots)
        if moved > 0:
            await stocks.add(row.settlement_entity_id, GRAIN, moved, GoodsFlow.AID)
        row.state = MandateState.MET if moved > 0 else MandateState.FAILED
    elif row.kind is MandateKind.SLUM_CLEARANCE and row.settlement_entity_id is not None:
        settlement = await ctx.session.get(EntityRow, row.settlement_entity_id)
        if settlement is not None and not held(settlement.id):
            await clear_slums(ctx, await town_of(ctx, settlement, await KnowledgeMap.load(ctx.session)))
    await ctx.session.flush()


async def plan(ctx: TickContext, book: RealmBook, realm: Realm, tally: MandateTally) -> None:
    table = ctx.rules.affairs
    capital = realm.profile.capital_entity_id
    fighting = bool(await ongoing_wars(ctx.session, realm.profile.core_entity_id)) if realm.profile.core_entity_id is not None else False
    for member in book.members(realm):
        town = await ctx.session.get(SettlementProfileRow, member.id)
        hunger = (await pressures_of(ctx.session, member.id)).get(PressureKind.HUNGER, 0)
        issued: MandateRow | None = None
        stores = await units_of(ctx, capital, GRAIN) if capital is not None else 0
        if hunger >= table.famine_hunger and (capital is None or member.id == capital or stores <= 0):
            issued = await issue(ctx, realm, MandateKind.RATION, settlement_id=member.id, commodity=GRAIN)
        elif hunger >= table.famine_hunger and capital is not None and member.id != capital:
            amount = round_half_up(table.relief_food * stat_or(member, "population", 0) / PER_MILLE)
            issued = await issue(ctx, realm, MandateKind.FAMINE_RELIEF, settlement_id=member.id, commodity=GRAIN, amount=amount)
        elif town is not None and await sick_near(ctx, member.id):
            issued = await issue(ctx, realm, MandateKind.QUARANTINE, settlement_id=member.id)
        elif town is not None and town.unrest >= table.curfew_unrest:
            issued = await issue(ctx, realm, MandateKind.CURFEW, settlement_id=member.id)
        elif fighting and town is not None and town.militia < stat_or(member, "population", 0) * ctx.rules.mandates.conscript_share_pct // PERCENT // 10:
            issued = await issue(ctx, realm, MandateKind.CONSCRIPTION, settlement_id=member.id)
        elif fighting and town is not None:
            amount = round_half_up(table.produce_amount * stat_or(member, "population", 0) / PER_MILLE)
            issued = await issue(ctx, realm, MandateKind.PRODUCE, settlement_id=member.id, commodity=CommodityKind.WEAPONS, amount=amount)
        elif town is not None and town.crime >= PERCENT // 2 and await has_district(ctx, member.id, DistrictKind.SLUMS):
            issued = await issue(ctx, realm, MandateKind.SLUM_CLEARANCE, settlement_id=member.id)
        elif town is not None and town.crime >= PERCENT // 2 and not await has_district(ctx, member.id, DistrictKind.CITADEL):
            issued = await issue(ctx, realm, MandateKind.BUILD, settlement_id=member.id, district=DistrictKind.CITADEL)
        elif town is not None and await unready(ctx.session, ctx.rules, book.atlas, member.id, ctx.epoch):
            issued = await issue(ctx, realm, MandateKind.PREPARE, settlement_id=member.id)
        elif town is not None and town.unrest < table.curfew_unrest // 2 and await active_at(ctx, member.id):
            issued = await issue(ctx, realm, MandateKind.CORVEE, settlement_id=member.id)
        tally.issued += issued is not None
    seat = await ctx.session.get(EntityRow, capital) if capital is not None else None
    if capital is not None and await units_of(ctx, capital, GRAIN) < table.ban_below * (stat_or(seat, "population", 0) if seat is not None else 0) // PER_MILLE:
        tally.issued += await issue(ctx, realm, MandateKind.EXPORT_BAN, settlement_id=None, commodity=GRAIN) is not None


async def has_district(ctx: TickContext, town_id: int, kind: DistrictKind) -> bool:
    found = await ctx.session.scalar(select(DistrictRow.id).where(DistrictRow.settlement_entity_id == town_id, DistrictRow.kind == kind).limit(1))
    return found is not None


async def keep_curfew(ctx: TickContext, row: MandateRow) -> None:
    table = ctx.rules.affairs
    town = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id or -1)
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest - table.curfew_calm, 0, PERCENT)
    society = await ctx.session.get(CommunitySocietyRow, row.settlement_entity_id or -1)
    if society is not None:
        for social_class in SocialClass:
            key = f"satisfaction_{social_class.value}"
            setattr(society, key, clamp_int(getattr(society, key) - table.curfew_mood, 0, PERCENT))


async def keep_ration(ctx: TickContext, realm: Realm, row: MandateRow) -> None:
    town = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id or -1)
    if town is None or "unrest" in (town.locked or []):
        return
    unfair = realm.profile.corruption / PERCENT * ctx.rules.mandates.ration_grievance_pct / PERCENT
    town.unrest = clamp_int(town.unrest + round_half_up(ctx.rules.urban.ration_unrest * unfair), 0, PERCENT)


async def sick_near(ctx: TickContext, town_id: int) -> bool:
    town = await ctx.session.get(EntityRow, town_id)
    if town is None or town.location_id is None:
        return False
    found = await ctx.session.scalar(
        select(OutbreakRow.id).where(OutbreakRow.region_entity_id == town.location_id, OutbreakRow.status != OutbreakStatus.ENDED).limit(1)
    )
    return found is not None


async def keep_quarantine(ctx: TickContext, row: MandateRow) -> None:
    town = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id or -1)
    if town is None or held(town.settlement_entity_id):
        return
    if "sanitation" not in town.locked:
        town.sanitation = clamp_int(town.sanitation + ctx.rules.mandates.quarantine_health, 0, PERCENT)
    place = await ctx.session.get(EntityRow, town.settlement_entity_id)
    if place is not None:
        shift_stat(place, "prosperity", -ctx.rules.mandates.quarantine_trade_cost)


async def keep_conscription(ctx: TickContext, row: MandateRow) -> None:
    town = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id or -1)
    place = await ctx.session.get(EntityRow, row.settlement_entity_id or -1)
    if town is None or place is None or held(place.id) or "militia" in town.locked:
        return
    raised = levy(ctx.rules, place, round_half_up(stat_or(place, "population", 0) * ctx.rules.mandates.conscript_share_pct / PERCENT / 10))
    town.militia += raised


async def keep_corvee(ctx: TickContext, row: MandateRow) -> None:
    if row.settlement_entity_id is None:
        return
    await hasten(ctx, row.settlement_entity_id, ctx.rules.mandates.corvee_progress_pct)
    town = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id)
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + ctx.rules.mandates.corvee_grievance, 0, PERCENT)


async def met(ctx: TickContext, row: MandateRow) -> bool:
    if row.kind is MandateKind.PRODUCE and row.settlement_entity_id is not None and row.commodity is not None:
        return await units_of(ctx, row.settlement_entity_id, row.commodity) >= row.amount
    if row.kind is MandateKind.BUILD and row.settlement_entity_id is not None and row.district is not None:
        return await has_district(ctx, row.settlement_entity_id, row.district)
    if row.kind is MandateKind.SLUM_CLEARANCE and row.settlement_entity_id is not None:
        return not await has_district(ctx, row.settlement_entity_id, DistrictKind.SLUMS)
    if row.kind is MandateKind.PREPARE and row.settlement_entity_id is not None:
        raised = select(PreparednessRow.kind).where(
            PreparednessRow.settlement_entity_id == row.settlement_entity_id, PreparednessRow.built_epoch >= row.issued_epoch
        )
        return await ctx.session.scalar(raised.limit(1)) is not None
    return await met_on_land(ctx, row)


async def met_on_land(ctx: TickContext, row: MandateRow) -> bool:
    if row.kind is MandateKind.CORVEE and row.settlement_entity_id is not None:
        return not await active_at(ctx, row.settlement_entity_id)
    if row.kind is MandateKind.QUARANTINE and row.settlement_entity_id is not None:
        return not await sick_near(ctx, row.settlement_entity_id)
    if row.kind is MandateKind.ENCLOSURE and row.settlement_entity_id is not None:
        closed = select(CommonsRow.id).where(CommonsRow.steward_entity_id == row.settlement_entity_id, CommonsRow.rule == CommonsRule.ENCLOSED)
        return await ctx.session.scalar(closed.limit(1)) is not None
    return True


async def lift_ban(ctx: TickContext, realm: Realm, row: MandateRow) -> None:
    if row.kind is not MandateKind.EXPORT_BAN:
        return
    for policy in await ctx.session.scalars(
        select(TradePolicyRow).where(
            TradePolicyRow.issuer_node_id == realm.entity.id,
            TradePolicyRow.kind == TradePolicyKind.EMBARGO,
            TradePolicyRow.commodity == row.commodity,
            TradePolicyRow.reason == MANDATE_REASON,
        )
    ):
        if not policy.locked:
            await ctx.session.delete(policy)


async def judge(ctx: TickContext, realm: Realm, row: MandateRow, tally: MandateTally) -> None:
    if row.kind is MandateKind.CURFEW:
        await keep_curfew(ctx, row)
    if row.kind is MandateKind.RATION:
        await keep_ration(ctx, realm, row)
    if row.kind is MandateKind.CORVEE:
        await keep_corvee(ctx, row)
    if row.kind is MandateKind.QUARANTINE:
        await keep_quarantine(ctx, row)
    if row.kind is MandateKind.CONSCRIPTION:
        await keep_conscription(ctx, row)
    if ctx.epoch < row.until_epoch or STATE in row.locked:
        return
    done = await met(ctx, row)
    row.state = MandateState.MET if done else MandateState.FAILED
    await lift_ban(ctx, realm, row)
    if done:
        tally.met += 1
        return
    tally.failed += 1
    if LEGITIMACY not in realm.profile.locked:
        realm.profile.legitimacy = clamp_int(realm.profile.legitimacy - ctx.rules.affairs.mandate_legitimacy, 0, PERCENT)
    await record(
        ctx,
        "affairs.mandate_failed",
        roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.SUBJECT: row.settlement_entity_id, IncidentRole.ACTOR: row.issuer_node_id},
        facts={"mandate": row.kind, "legitimacy_lost": ctx.rules.affairs.mandate_legitimacy},
        place=row.settlement_entity_id,
    )


async def satisfied(ctx: TickContext, noble: EntityRow, want: NobleWant) -> bool:
    if want is NobleWant.OFFICE:
        return await ctx.session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == noble.id).limit(1)) is not None
    if want is NobleWant.HONOUR:
        profile = await ctx.session.get(MortalProfileRow, noble.id)
        return profile is not None and profile.honour >= ctx.rules.affairs.honour_wanted
    if want is NobleWant.FINE_GOODS:
        return noble.location_id is not None and await units_of(ctx, noble.location_id, CommodityKind.LUXURIES) > 0
    quality = await ctx.session.scalar(
        select(DwellingRow.quality)
        .join(HouseholdMemberRow, HouseholdMemberRow.household_id == DwellingRow.household_id)
        .where(HouseholdMemberRow.member_node_id == noble.id)
    )
    return quality is not None and quality >= PERCENT // 2


async def weigh_demands(ctx: TickContext, realm: Realm, tally: MandateTally) -> None:
    members = list(realm.members)
    ruler = realm.ruler_id
    if not members or ruler is None:
        return
    nobles = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.social_class == SocialClass.NOBLE,
            await present_among(ctx.session, members),
        )
        .order_by(EntityRow.id)
    )
    for noble in nobles:
        if noble.id == ruler or held(noble.id):
            continue
        want = ctx.rng(seed_of("noble.want", noble.id)).pick(WANTS)
        row = await ctx.session.get(NobleDemandRow, (noble.id, want))
        if row is None:
            row = NobleDemandRow(mortal_entity_id=noble.id, want=want, since_epoch=ctx.epoch)
            ctx.session.add(row)
            tally.demands += 1
        if not row.locked:
            row.met = await satisfied(ctx, noble, want)
        if row.met:
            row.since_epoch = ctx.epoch
        elif ctx.epoch - row.since_epoch >= ctx.rules.affairs.demand_epochs:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=noble.id,
                subject_id=ruler,
                kind=MemoryKind.ILL_WILL,
                magnitude=-ctx.rules.affairs.demand_grudge,
                epoch=ctx.epoch,
                note=f"a demand for {spoken(want)} left unmet",
            )
            tally.soured += 1
    await ctx.session.flush()


async def tend_mandates(ctx: TickContext, tally: MandateTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        for row in await active(ctx, realm):
            if row.settlement_entity_id is None or not held(row.settlement_entity_id):
                await judge(ctx, realm, row, tally)
        await plan(ctx, book, realm, tally)
        await weigh_demands(ctx, realm, tally)
