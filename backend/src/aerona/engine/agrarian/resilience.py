from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.ethics import HONOUR_MODELS
from aerona.catalog.life_traits import REBUILD_CAUSE_TRAITS, having
from aerona.catalog.rebuilding import REBUILD_PLANS
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.core.dispatch import Handlers
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.agrarian import PreparednessRow, ReconstructionRow, ReliefAidRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import AidKind, PreparednessKind, RebuildPlan
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.life_traits import RebuildCauseTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial, SizeTier, TreasuryEntry
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.statecraft import MandateKind, MandateState
from aerona.domain.enums.structure import ConstructionState
from aerona.domain.enums.urban import Morphology
from aerona.engine.agrarian.rebuilding_ways import abandon_town, choose_way, rebuilt
from aerona.engine.agrarian.rings import put
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.gifts import give
from aerona.engine.cycles.standing import regard
from aerona.engine.divine.standing import standing_row
from aerona.engine.economy.purse import coin_of, give_coin, held_coin, take_coin
from aerona.engine.economy.stocks import goods_of
from aerona.engine.faith.book import FaithBook
from aerona.engine.intrigue.favours import owe
from aerona.engine.lore.research import steal_technique
from aerona.engine.mind.ethics import honour_of
from aerona.engine.mortal.standing import add_honour
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import top_region
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import relation
from aerona.engine.settlement.book import ledger, town_of
from aerona.engine.structures.construction import best_architect
from aerona.rules.registry import Rules

K = PreparednessKind
TIERS = tuple(SizeTier)
MOST_LEVEL = 5
RELIEVED = frozenset(
    {
        EngineKind.EARTHQUAKE,
        EngineKind.FLOOD,
        EngineKind.PLAGUE,
        EngineKind.DROUGHT,
        EngineKind.STORM,
        EngineKind.ERUPTION,
        EngineKind.FIRE,
        EngineKind.FAMINE,
        EngineKind.MAGIC_STORM,
    }
)
SEIZING = having(REBUILD_CAUSE_TRAITS, RebuildCauseTrait.SEIZING)


@dataclass
class ResilienceTally:
    works: int = 0
    raised: int = 0
    aid: int = 0
    refused: int = 0
    rebuilding: int = 0
    rebuilt: int = 0
    seized: int = 0


def wishes(kinds: Counter[EngineKind], land: RegionEnvironmentRow | None, fire_risk: int, fire_at: int) -> Counter[PreparednessKind]:
    coastal = land is not None and land.coast_kind is not CoastKind.NONE
    river = land is not None and land.river_class is not RiverClass.NONE
    wanted: Counter[PreparednessKind] = Counter()
    wanted[K.SEAWALL if coastal and not river else K.LEVEE] += kinds[EngineKind.FLOOD]
    wanted[K.SEAWALL if coastal else K.WATCHTOWER] += kinds[EngineKind.STORM]
    wanted[K.DRILL] += kinds[EngineKind.EARTHQUAKE] + kinds[EngineKind.ERUPTION]
    wanted[K.STOCKPILE] += kinds[EngineKind.DROUGHT] + kinds[EngineKind.FAMINE]
    wanted[K.FIREBREAK] += kinds[EngineKind.FIRE] + (1 if fire_risk >= fire_at else 0)
    wanted[K.QUARANTINE_PLAN] += kinds[EngineKind.PLAGUE]
    wanted[K.SHELTERS] += kinds[EngineKind.EARTHQUAKE] + kinds[EngineKind.STORM]
    wanted[K.EVACUATION_ROUTES] += kinds[EngineKind.ERUPTION] + kinds[EngineKind.FLOOD] // 2
    wanted[K.WARNING_NETWORK] += kinds[EngineKind.STORM] // 2 + kinds[EngineKind.ERUPTION] // 2
    wanted[K.RESERVES_OF_ENERGY] += kinds[EngineKind.DROUGHT] // 2
    wanted[K.WARD] += kinds[EngineKind.MAGIC_STORM]
    return wanted


async def harms_by_region(ctx: TickContext, atlas: RegionAtlas) -> dict[int, Counter[EngineKind]]:
    since = ctx.epoch - ctx.rules.resilience.memory_epochs
    rows = await ctx.session.execute(
        select(EntityRow.id, EntityRow.engine_kind).where(
            EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind.in_(list(RELIEVED)), EntityRow.birth_epoch >= since
        )
    )
    found: dict[int, Counter[EngineKind]] = defaultdict(Counter)
    for event_id, kind in rows.all():
        region = atlas.top_region(event_id)
        if region is not None and kind is not None:
            found[region][kind] += 1
    return found


async def prepare(ctx: TickContext, atlas: RegionAtlas, tally: ResilienceTally) -> None:
    table = ctx.rules.resilience
    harms = await harms_by_region(ctx, atlas)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    works: dict[int, dict[PreparednessKind, PreparednessRow]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(PreparednessRow)):
        works[row.settlement_entity_id][row.kind] = row
        if not held(row.settlement_entity_id):
            shift(row, "condition", -table.decay)
            tally.works += 1
    rows = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    ordered = set(
        await ctx.session.scalars(
            select(MandateRow.settlement_entity_id).where(MandateRow.kind == MandateKind.PREPARE, MandateRow.state == MandateState.ACTIVE)
        )
    )
    for town, profile in rows.all():
        region = atlas.top_region(town.id)
        if region is None or held(town.id) or "investment_pool" in profile.locked:
            continue
        wanted = wishes(harms.get(region, Counter()), lands.get(region), profile.fire_risk, table.fire_risk_at)
        if town.id in ordered and not +wanted:
            wanted[K.WATCHTOWER] = 1
        own = works[town.id]
        people = stat_or(town, "population", 0)
        top = most_level(ctx.rules, people)
        options = [(count, kind) for kind, count in wanted.items() if count > 0 and (own.get(kind) is None or own[kind].level < top)]
        chosen = sorted(options, key=lambda item: (-item[0], item[1].value))[: 1 + max(0, people) // ctx.rules.scale.preparedness_works_people]
        for _, kind in chosen:
            if not await raise_work(ctx, town, profile, own, kind, paid_by_realm=town.id in ordered):
                break
            tally.raised += 1


def most_level(rules: Rules, population: int) -> int:
    return MOST_LEVEL + max(0, population) // rules.scale.preparedness_level_people


async def raise_work(
    ctx: TickContext,
    town: EntityRow,
    profile: SettlementProfileRow,
    own: dict[PreparednessKind, PreparednessRow],
    kind: PreparednessKind,
    *,
    paid_by_realm: bool,
) -> bool:
    table = ctx.rules.resilience
    work = own.get(kind)
    level = (work.level if work is not None else 0) + 1
    cost = table.cost * level
    if work is not None and "level" in work.locked:
        return False
    if profile.investment_pool >= cost:
        profile.investment_pool -= cost
    elif paid_by_realm and profile.treasury >= cost and "treasury" not in profile.locked:
        profile.treasury -= cost
        ctx.session.add(
            SettlementTreasuryRow(
                settlement_entity_id=town.id,
                epoch=ctx.epoch,
                entry=TreasuryEntry.BUILDING,
                amount=-cost,
                balance=profile.treasury,
                note="works against disaster",
            )
        )
    else:
        return False
    if work is None:
        work = PreparednessRow(settlement_entity_id=town.id, kind=kind, level=0, built_epoch=ctx.epoch, locked=[])
        ctx.session.add(work)
        own[kind] = work
    work.level = level
    put(work, "condition", PERCENT)
    work.built_epoch = ctx.epoch
    await record(ctx, "resilience.built", roles={IncidentRole.SUBJECT: town.id}, facts={"work": kind, "level": level}, place=town.id)
    return True


async def struck_towns(ctx: TickContext) -> list[tuple[EntityRow, EntityRow]]:
    events = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind.in_(list(RELIEVED)), EntityRow.birth_epoch == ctx.epoch)
            .order_by(EntityRow.id)
        )
    )
    found: list[tuple[EntityRow, EntityRow]] = []
    seen: set[int] = set()
    for event in events:
        targets = await ctx.session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == event.id, BondRow.kind == BondKind.CAUSED, BondRow.state == BondState.ACTIVE)
        )
        for target_id in [event.location_id, *targets]:
            town = await ctx.session.get(EntityRow, target_id) if target_id is not None else None
            if town is not None and town.entity_type is EntityType.SETTLEMENT and town.status is EntityStatus.CANON and town.id not in seen:
                seen.add(town.id)
                found.append((event, town))
    return found


EVENT_AID: Mapping[EngineKind, AidKind] = {
    EngineKind.PLAGUE: AidKind.HEALERS,
    EngineKind.FAMINE: AidKind.FOOD,
    EngineKind.DROUGHT: AidKind.FOOD,
    EngineKind.EARTHQUAKE: AidKind.SHELTER,
    EngineKind.FLOOD: AidKind.SHELTER,
    EngineKind.STORM: AidKind.SHELTER,
    EngineKind.MAGIC_STORM: AidKind.SHELTER,
    EngineKind.FIRE: AidKind.SHELTER,
    EngineKind.ERUPTION: AidKind.SHELTER,
    EngineKind.WAR: AidKind.SOLDIERS,
    EngineKind.BATTLE: AidKind.SOLDIERS,
    EngineKind.SIEGE: AidKind.SOLDIERS,
    EngineKind.WARRIOR_BAND: AidKind.SOLDIERS,
    EngineKind.ROUTE_RAIDERS: AidKind.SOLDIERS,
}


def aid_kind(event: EntityRow | None, rebuilding: bool, *, coin: bool) -> AidKind:
    chosen = EVENT_AID.get(event.engine_kind) if event is not None and event.engine_kind is not None else None
    if chosen is AidKind.HEALERS and coin:
        return AidKind.MEDICINE
    if chosen is not None:
        return chosen
    if rebuilding:
        return AidKind.LABOUR
    if not coin:
        return AidKind.KNOWLEDGE if event is None else AidKind.CREDIT
    return AidKind.MONEY if event is None else AidKind.GOODS


async def refuse_aid(ctx: TickContext, giver: EntityRow, town: EntityRow, receiver: Realm | None) -> None:
    table = ctx.rules.relief
    await regard(ctx, (giver.id, town.id), -table.face_loss, MemoryKind.HUMILIATED_ME, "turned away our aid")
    ruler_id = receiver.ruler_id if receiver is not None else None
    if ruler_id is not None and not held(ruler_id):
        people = await people_of(ctx.session, town)
        model = await honour_of(ctx.session, people.id if people is not None else None)
        await add_honour(ctx.session, ruler_id, -table.face_loss * HONOUR_MODELS[model].face_loss_pct // PERCENT, ctx.epoch)
    await record(ctx, "relief.refused", roles={IncidentRole.SUBJECT: town.id, IncidentRole.GIVER: giver.id}, facts={"face": table.face_loss}, place=town.id)


@dataclass(frozen=True)
class Aid:
    giver: EntityRow
    town: EntityRow
    amount: int
    rebuild: ReconstructionRow | None
    capital: int | None


def per_thousand(amount: int, town: EntityRow) -> int:
    return round_half_up(amount * max(0, stat_or(town, "population", 0)) / PER_MILLE)


async def send_grain(ctx: TickContext, aid: Aid) -> None:
    if aid.capital is not None and aid.capital != aid.town.id:
        stocks = goods_of(ctx.session, ctx.epoch)
        wanted = per_thousand(ctx.rules.relief.grain, aid.town)
        moved = sum(lot.quantity for lot in await stocks.take(aid.capital, CommodityKind.GRAIN, wanted, GoodsFlow.AID))
        if moved > 0:
            await stocks.add(aid.town.id, CommodityKind.GRAIN, moved, GoodsFlow.AID)


AID_EFFECTS: Handlers[AidKind, Callable[[TickContext, Aid], Awaitable[None]]] = Handlers(AidKind)


@AID_EFFECTS.on(AidKind.GOODS)
async def aid_goods(ctx: TickContext, aid: Aid) -> None:
    table = ctx.rules.relief
    shift_stat(aid.town, "prosperity", min(table.prosperity_cap, aid.amount / table.coin_per_prosperity))
    await send_grain(ctx, aid)


@AID_EFFECTS.on(AidKind.FOOD)
async def aid_food(ctx: TickContext, aid: Aid) -> None:
    await send_grain(ctx, aid)
    await send_grain(ctx, aid)


async def ease_land(ctx: TickContext, aid: Aid, amount: int) -> None:
    region = await top_region(ctx.session, aid.town)
    land = await ctx.session.get(RegionEnvironmentRow, region.id) if region is not None and not held(region.id) else None
    if land is not None:
        shift(land, "disease_load", -amount)


@AID_EFFECTS.on(AidKind.HEALERS)
async def aid_healers(ctx: TickContext, aid: Aid) -> None:
    await ease_land(ctx, aid, ctx.rules.relief.healer_disease)


@AID_EFFECTS.on(AidKind.MEDICINE)
async def aid_medicine(ctx: TickContext, aid: Aid) -> None:
    await ease_land(ctx, aid, ctx.rules.relief.healer_disease * 2)


@AID_EFFECTS.on(AidKind.TRANSPORT)
async def aid_transport(ctx: TickContext, aid: Aid) -> None:
    await send_grain(ctx, aid)
    if aid.rebuild is not None:
        shift(aid.rebuild, "progress", ctx.rules.relief.transport_progress)


@AID_EFFECTS.on(AidKind.LABOUR)
async def aid_labour(ctx: TickContext, aid: Aid) -> None:
    if aid.rebuild is not None:
        shift(aid.rebuild, "progress", ctx.rules.relief.labour_progress)


async def town_profile(ctx: TickContext, aid: Aid) -> SettlementProfileRow | None:
    profile = await ctx.session.get(SettlementProfileRow, aid.town.id)
    return profile if profile is not None and not held(aid.town.id) else None


@AID_EFFECTS.on(AidKind.MONEY)
async def aid_money(ctx: TickContext, aid: Aid) -> None:
    profile = await town_profile(ctx, aid)
    if profile is not None and "treasury" not in profile.locked:
        profile.treasury += aid.amount


@AID_EFFECTS.on(AidKind.CREDIT)
async def aid_credit(ctx: TickContext, aid: Aid) -> None:
    await aid_money(ctx, aid)
    row = RegistryRow(
        holder_entity_id=aid.giver.id, kind=RegistryKind.DEBT, owner_entity_id=aid.giver.id, counterparty_entity_id=aid.town.id, amount=aid.amount
    )
    row.registered_epoch, row.locked = ctx.epoch, []
    ctx.session.add(row)


@AID_EFFECTS.on(AidKind.SHELTER)
async def aid_shelter(ctx: TickContext, aid: Aid) -> None:
    profile = await town_profile(ctx, aid)
    if profile is not None and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest - ctx.rules.relief.shelter_relief, 0, PERCENT)


@AID_EFFECTS.on(AidKind.SOLDIERS)
async def aid_soldiers(ctx: TickContext, aid: Aid) -> None:
    profile = await town_profile(ctx, aid)
    if profile is not None and "militia" not in profile.locked:
        profile.militia += per_thousand(ctx.rules.relief.soldiers_sent, aid.town)


@AID_EFFECTS.on(AidKind.KNOWLEDGE)
async def aid_knowledge(ctx: TickContext, aid: Aid) -> None:
    if not held(aid.town.id):
        await steal_technique(ctx, aid.town.id, aid.giver.id)


AID_EFFECTS.seal()


async def aid_from(
    ctx: TickContext,
    giver: EntityRow,
    realm: Realm | None,
    *,
    event: EntityRow | None,
    town: EntityRow,
    receiver: Realm | None,
    tally: ResilienceTally,
    kind: AidKind | None = None,
    amount: int | None = None,
) -> ReliefAidRow | None:
    table = ctx.rules.relief
    rebuild = await ctx.session.scalar(
        select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == town.id, ReconstructionRow.finished_epoch.is_(None)).limit(1)
    )
    coin = realm is not None and realm.profile.treasury > 0
    kind = kind or aid_kind(event, rebuild is not None, coin=coin)
    most = per_thousand(table.cap, town)
    purse = held_coin(realm.profile.treasury) if realm is not None else held_coin(await coin_of(ctx.session, ctx.rules, giver))
    amount = amount if amount is not None else min(most, purse * table.share_pct // PERCENT)
    if amount <= 0:
        return None
    target = receiver.entity if receiver is not None else town
    rival = await relation(ctx.session, ctx.rules, target.id, giver.id) <= table.refuse_below
    gift = None if rival else await give(ctx, giver.id, target.id, amount, GiftOccasion.RELIEF, pay=False)
    refused = rival or gift is None or gift.state is GiftState.REFUSED
    god = await patron_node(ctx.session, giver)
    row = ReliefAidRow(
        event_entity_id=event.id if event is not None else None,
        giver_node_id=giver.id,
        receiver_entity_id=town.id,
        kind=kind,
        amount=amount,
        god_node_id=god,
        refused=refused,
        gift_id=gift.id if gift is not None else None,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    if refused:
        tally.refused += 1
        await refuse_aid(ctx, giver, town, receiver)
        return row
    if realm is not None:
        spend(ctx, realm, -amount, TreasuryEntry.RELIEF, f"aid to {town.name}")
    elif not await take_coin(ctx.session, ctx.rules, giver, amount):
        return row
    await AID_EFFECTS[kind](ctx, Aid(giver, town, amount, rebuild, realm.profile.capital_entity_id if realm is not None else None))
    debtor = receiver.ruler_id if receiver is not None and receiver.ruler_id is not None else town.id
    await owe(ctx, debtor, giver.id, FavourOrigin.RELIEF, table.favour)
    if god is not None:
        standing = await standing_row(ctx, town.id, god)
        shift(standing, "love", table.love)
    tally.aid += 1
    sent = {IncidentRole.GIVER: giver.id, IncidentRole.RECEIVER: town.id}
    if event is not None:
        await record(ctx, "relief.sent_after", roles={**sent, IncidentRole.SUBJECT: event.id}, facts={"aid": kind, "amount": amount}, place=town.id)
    else:
        await record(ctx, "relief.sent", roles=sent, facts={"aid": kind, "amount": amount}, place=town.id)
    return row


async def relieve(ctx: TickContext, atlas: RegionAtlas, tally: ResilienceTally) -> None:
    table = ctx.rules.relief
    struck = await struck_towns(ctx)
    if not struck:
        return
    book = await RealmBook.load(ctx.session)
    faith = await FaithBook.load(ctx.session)
    for event, town in struck:
        if held(town.id):
            continue
        own_id = book.member_of.get(town.id)
        receiver = book.realms.get(own_id) if own_id is not None else None
        givers: list[tuple[int, int, EntityRow, Realm | None]] = []
        for realm in book.realms.values():
            if realm.entity.id == own_id or realm.entity.world_id != town.world_id or held(realm.entity.id) or realm.profile.treasury <= 0:
                continue
            regard_of = await relation(ctx.session, ctx.rules, realm.entity.id, town.id)
            if regard_of >= table.regard_at:
                givers.append((-regard_of, realm.entity.id, realm.entity, realm))
        region = atlas.top_region(town.id)
        for church in faith.churches.values():
            if held(church.cult.id) or church.cult.world_id != town.world_id:
                continue
            if any(atlas.top_region(member.id) == region for member in church.members):
                givers.append((0, church.cult.id, church.cult, None))
        for _, giver_id, giver, purse in sorted(givers, key=lambda item: (item[0], item[1]))[: table.givers]:
            if ctx.rng(f"relief.{giver_id}.{town.id}.{ctx.epoch}").chance(table.chance_pct):
                await aid_from(ctx, giver, purse, event=event, town=town, receiver=receiver, tally=tally)


async def elite_of(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    houses = await ctx.session.execute(
        select(EntityRow, HouseProfileRow)
        .join(HouseProfileRow, HouseProfileRow.house_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(HouseProfileRow.wealth.desc(), EntityRow.id)
    )
    return next((house for house, profile in houses.all() if town.id in profile.seats and not held(house.id)), None)


async def seize(ctx: TickContext, row: ReconstructionRow, town: EntityRow, profile: SettlementProfileRow, tally: ResilienceTally) -> None:
    table = ctx.rules.reconstruction
    elite = await elite_of(ctx, town)
    if elite is None:
        return
    put(row, "seized_by_node_id", elite.id)
    put(row, "seized", round_half_up(stat_or(town, "population", 0) * table.seize_share / PERCENT))
    shift(profile, "homeless", row.seized, high=10**9)
    shift(profile, "unrest", table.seize_unrest)
    coin = round_half_up(table.seize_coin * row.seized / PERCENT)
    await give_coin(ctx.session, ctx.rules, elite, coin)
    tally.seized += 1
    await record(
        ctx,
        "reconstruction.seized",
        roles={IncidentRole.ACTOR: elite.id, IncidentRole.PLACE: town.id},
        facts={"seized": row.seized, "coin": coin},
        place=town.id,
    )


async def monuments_of(ctx: TickContext, town_id: int) -> list[StructureProfileRow]:
    rows = await ctx.session.scalars(
        select(StructureProfileRow)
        .where(StructureProfileRow.host_entity_id == town_id, StructureProfileRow.construction_state == ConstructionState.RUINED)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    return [row for row in rows if not held(row.structure_entity_id) and "construction_state" not in row.locked]


async def plan_rebuild(ctx: TickContext, row: ReconstructionRow, town: EntityRow, profile: SettlementProfileRow, knowledge: KnowledgeMap) -> None:
    table = ctx.rules.reconstruction
    hasty = table.cost * (TIERS.index(profile.size_tier) + 1)
    planned = hasty * table.planned_pct // PERCENT
    planner = await best_architect(ctx, town)
    able = planner is not None and knowledge.level(town.id, KnowledgeBranch.ARCHITECTURE) >= table.architecture_level
    if able and held_coin(profile.treasury) * 2 >= planned and "plan" not in row.locked:
        row.plan = RebuildPlan.PLANNED
    await choose_way(ctx, row, town)
    restored = hasty * ctx.rules.rebuilding.restored_cost_pct // PERCENT
    if row.plan is RebuildPlan.OPPORTUNISTIC and "plan" not in row.locked and held_coin(profile.treasury) * 2 >= restored and await monuments_of(ctx, town.id):
        row.plan = RebuildPlan.RESTORED
    put(row, "cost", planned if row.plan is RebuildPlan.PLANNED else restored if row.plan is RebuildPlan.RESTORED else hasty)
    put(row, "planner_entity_id", planner.id if planner is not None and row.plan is RebuildPlan.PLANNED else None)


async def finish(ctx: TickContext, row: ReconstructionRow, town: EntityRow, profile: SettlementProfileRow) -> None:
    table = ctx.rules.reconstruction
    knowledge = await KnowledgeMap.load(ctx.session)
    built = await town_of(ctx, town, knowledge)
    for district in await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)):
        shift(district, "condition", table.restore)
        if row.plan is RebuildPlan.PLANNED and district.material is BuildMaterial.TIMBER:
            put(district, "material", BuildMaterial.STONE)
    if row.plan is RebuildPlan.PLANNED:
        put(profile, "morphology", Morphology.PLANNED)
        shift(profile, "fire_risk", -table.fire_cut)
        shift(built.infrastructure, "roads", 1, high=MOST_LEVEL)
    if row.plan is RebuildPlan.RESTORED:
        for monument in await monuments_of(ctx, town.id):
            monument.construction_state = ConstructionState.RESTORED
        shift_stat(town, "piety", ctx.rules.rebuilding.restored_memory)
    row.finished_epoch = ctx.epoch
    await rebuilt(ctx, row, town)
    await record(
        ctx,
        f"reconstruction.{row.plan.value}",
        roles={IncidentRole.SUBJECT: town.id, IncidentRole.MAKER: row.planner_entity_id},
        facts={"cost": row.cost},
        place=town.id,
    )


async def rebuild(ctx: TickContext, tally: ResilienceTally) -> None:
    table = ctx.rules.reconstruction
    knowledge = await KnowledgeMap.load(ctx.session)
    rows = list(await ctx.session.scalars(select(ReconstructionRow).where(ReconstructionRow.finished_epoch.is_(None)).order_by(ReconstructionRow.id)))
    for row in rows:
        town = await ctx.session.get(EntityRow, row.settlement_entity_id)
        profile = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id)
        if town is not None and town.status is not EntityStatus.CANON and not held(town.id):
            row.finished_epoch = ctx.epoch
            continue
        if town is None or profile is None or held(town.id):
            continue
        tally.rebuilding += 1
        if not REBUILD_PLANS[row.plan].builds:
            await abandon_town(ctx, row, town)
            continue
        if row.cost == 0:
            await plan_rebuild(ctx, row, town, profile, knowledge)
            if not REBUILD_PLANS[row.plan].builds:
                await abandon_town(ctx, row, town)
                continue
            if row.cause in SEIZING and row.seized_by_node_id is None and ctx.rng(f"rebuild.seize.{row.id}").chance(table.seize_pct):
                await seize(ctx, row, town, profile, tally)
        due = max(0, row.cost - row.paid)
        built = await town_of(ctx, town, knowledge)
        paid = -ledger(ctx, built, TreasuryEntry.REBUILDING, -min(due, held_coin(profile.treasury) * table.pay_pct // PERCENT), "rebuilding") if due else 0
        put(row, "paid", row.paid + paid)
        step = table.planned_step if row.plan is RebuildPlan.PLANNED else table.hasty_step
        if row.plan is RebuildPlan.OPPORTUNISTIC or paid > 0 or due == 0:
            shift(row, "progress", step)
        if row.progress >= PERCENT:
            await finish(ctx, row, town, profile)
            tally.rebuilt += 1


async def keep_resilience(ctx: TickContext, tally: ResilienceTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await prepare(ctx, atlas, tally)
    await relieve(ctx, atlas, tally)
    await rebuild(ctx, tally)
    await ctx.session.flush()
