from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import MandateRow, NobleDemandRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.mind import MemoryKind, PressureKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateKind, MandateState, NobleWant
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.services.war import ongoing_wars

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


async def active(ctx: TickContext, realm: Realm) -> list[MandateRow]:
    return list(
        await ctx.session.scalars(
            select(MandateRow).where(MandateRow.polity_entity_id == realm.entity.id, MandateRow.state == MandateState.ACTIVE).order_by(MandateRow.id)
        )
    )


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
    await begin(ctx, realm, row)
    return row


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
    await ctx.session.flush()


async def plan(ctx: TickContext, book: RealmBook, realm: Realm, tally: MandateTally) -> None:
    table = ctx.rules.affairs
    capital = realm.profile.capital_entity_id
    fighting = bool(await ongoing_wars(ctx.session, realm.profile.core_entity_id)) if realm.profile.core_entity_id is not None else False
    for member in book.members(realm):
        town = await ctx.session.get(SettlementProfileRow, member.id)
        hunger = (await pressures_of(ctx.session, member.id)).get(PressureKind.HUNGER, 0)
        issued: MandateRow | None = None
        if hunger >= table.famine_hunger and capital is not None and member.id != capital:
            issued = await issue(ctx, realm, MandateKind.FAMINE_RELIEF, settlement_id=member.id, commodity=GRAIN, amount=table.relief_food)
        elif town is not None and town.unrest >= table.curfew_unrest:
            issued = await issue(ctx, realm, MandateKind.CURFEW, settlement_id=member.id)
        elif fighting and town is not None:
            issued = await issue(ctx, realm, MandateKind.PRODUCE, settlement_id=member.id, commodity=CommodityKind.WEAPONS, amount=table.produce_amount)
        elif town is not None and town.crime >= PERCENT // 2 and not await has_district(ctx, member.id, DistrictKind.CITADEL):
            issued = await issue(ctx, realm, MandateKind.BUILD, settlement_id=member.id, district=DistrictKind.CITADEL)
        tally.issued += issued is not None
    if capital is not None and await units_of(ctx, capital, GRAIN) < table.ban_below:
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


async def met(ctx: TickContext, row: MandateRow) -> bool:
    if row.kind is MandateKind.PRODUCE and row.settlement_entity_id is not None and row.commodity is not None:
        return await units_of(ctx, row.settlement_entity_id, row.commodity) >= row.amount
    if row.kind is MandateKind.BUILD and row.settlement_entity_id is not None and row.district is not None:
        return await has_district(ctx, row.settlement_entity_id, row.district)
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
    place = await ctx.session.get(EntityRow, row.settlement_entity_id or -1)
    await note(
        ctx,
        f"{place.name if place is not None else realm.entity.name} failed the {row.kind.value.replace('_', ' ')} mandate of {realm.entity.name}.",
        key="affairs.mandate_failed",
        ids=[realm.entity.id, *([place.id] if place is not None else [])],
        kind=ChronicleKind.CIVILIZATION,
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
                note=f"a demand for {want.value.replace('_', ' ')} left unmet",
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
