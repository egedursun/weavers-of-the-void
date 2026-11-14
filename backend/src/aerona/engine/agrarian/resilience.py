from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.agrarian import PreparednessRow, ReconstructionRow, ReliefAidRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow, SettlementTreasuryRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import AidKind, PreparednessKind, RebuildCause, RebuildPlan
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.mind import HonourModel, MemoryKind
from aerona.domain.enums.settlement import BuildMaterial, SizeTier, TreasuryEntry
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.statecraft import MandateKind, MandateState
from aerona.domain.enums.urban import Morphology
from aerona.engine.agrarian.rings import put
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.gifts import give
from aerona.engine.cycles.standing import regard
from aerona.engine.divine.standing import standing_row
from aerona.engine.economy.purse import give_coin
from aerona.engine.economy.stocks import goods_of
from aerona.engine.faith.book import FaithBook
from aerona.engine.intrigue.favours import owe
from aerona.engine.mind.ethics import honour_of
from aerona.engine.mortal.standing import add_honour
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import top_region
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.services.community_relations import relation
from aerona.engine.settlement.book import ledger, town_of
from aerona.engine.structures.construction import best_architect

K = PreparednessKind
TIERS = tuple(SizeTier)
MOST_LEVEL = 5
RELIEVED = frozenset(
    {EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.PLAGUE, EngineKind.DROUGHT, EngineKind.STORM, EngineKind.ERUPTION, EngineKind.FIRE, EngineKind.FAMINE}
)
SEIZING = frozenset({RebuildCause.FIRE, RebuildCause.SACK})


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
        options = [(count, kind) for kind, count in wanted.items() if count > 0 and (own.get(kind) is None or own[kind].level < MOST_LEVEL)]
        if not options:
            continue
        _, kind = max(options, key=lambda item: (item[0], item[1].value))
        work = own.get(kind)
        level = (work.level if work is not None else 0) + 1
        cost = table.cost * level
        if work is not None and "level" in work.locked:
            continue
        if profile.investment_pool >= cost:
            profile.investment_pool -= cost
        elif town.id in ordered and profile.treasury >= cost and "treasury" not in profile.locked:
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
            continue
        if work is None:
            work = PreparednessRow(settlement_entity_id=town.id, kind=kind, level=0, built_epoch=ctx.epoch, locked=[])
            ctx.session.add(work)
            own[kind] = work
        work.level = level
        put(work, "condition", PERCENT)
        work.built_epoch = ctx.epoch
        tally.raised += 1
        await note(
            ctx,
            f"{town.name} raised its {kind.value.replace('_', ' ')}s to level {level} against the disasters it remembers.",
            key="resilience.built",
            ids=[town.id],
        )


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


def aid_kind(event: EntityRow | None, rebuilding: bool, *, coin: bool) -> AidKind:
    if event is not None and event.engine_kind is EngineKind.PLAGUE:
        return AidKind.HEALERS
    if rebuilding or not coin:
        return AidKind.LABOUR
    return AidKind.GOODS


async def refuse_aid(ctx: TickContext, giver: EntityRow, town: EntityRow, receiver: Realm | None) -> None:
    table = ctx.rules.relief
    await regard(ctx, (giver.id, town.id), -table.face_loss, MemoryKind.HUMILIATED_ME, "turned away our aid")
    ruler_id = receiver.ruler_id if receiver is not None else None
    if ruler_id is not None and not held(ruler_id):
        people = await people_of(ctx.session, town)
        model = await honour_of(ctx.session, people.id if people is not None else None)
        await add_honour(ctx.session, ruler_id, -table.face_loss * (2 if model is HonourModel.FACE else 1), ctx.epoch)
    await note(ctx, f"{town.name} turned away the aid of {giver.name}, a rival it would not owe.", key="relief.refused", ids=[town.id, giver.id])


async def apply_aid(ctx: TickContext, town: EntityRow, kind: AidKind, amount: int, *, rebuild: ReconstructionRow | None, capital: int | None) -> None:
    table = ctx.rules.relief
    if kind is AidKind.GOODS:
        shift_stat(town, "prosperity", min(table.prosperity_cap, amount / table.coin_per_prosperity))
        if capital is not None and capital != town.id:
            stocks = goods_of(ctx.session, ctx.epoch)
            moved = sum(lot.quantity for lot in await stocks.take(capital, CommodityKind.GRAIN, table.grain, GoodsFlow.AID))
            if moved > 0:
                await stocks.add(town.id, CommodityKind.GRAIN, moved, GoodsFlow.AID)
    elif kind is AidKind.HEALERS:
        region = await top_region(ctx.session, town)
        land = await ctx.session.get(RegionEnvironmentRow, region.id) if region is not None and not held(region.id) else None
        if land is not None:
            shift(land, "disease_load", -table.healer_disease)
    elif rebuild is not None:
        shift(rebuild, "progress", table.labour_progress)


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
    amount = amount if amount is not None else min(table.cap, realm.profile.treasury * table.share_pct // PERCENT) if realm is not None else 0
    target = receiver.entity if receiver is not None else town
    rival = await relation(ctx.session, ctx.rules, target.id, giver.id) <= table.refuse_below
    gift = None if rival else await give(ctx, giver.id, target.id, max(1, amount), GiftOccasion.RELIEF, pay=False)
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
    if realm is not None and amount > 0:
        spend(ctx, realm, -amount, TreasuryEntry.RELIEF, f"aid to {town.name}")
    await apply_aid(ctx, town, kind, amount, rebuild=rebuild, capital=realm.profile.capital_entity_id if realm is not None else None)
    debtor = receiver.ruler_id if receiver is not None and receiver.ruler_id is not None else town.id
    await owe(ctx, debtor, giver.id, FavourOrigin.RELIEF, table.favour)
    if god is not None:
        standing = await standing_row(ctx, town.id, god)
        shift(standing, "love", table.love)
    tally.aid += 1
    await note(
        ctx,
        f"{giver.name} sent {kind.value} to {town.name}{f' after the {event.name}' if event is not None else ''}.",
        key="relief.sent",
        ids=[giver.id, town.id, *([event.id] if event is not None else [])],
    )
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
    await give_coin(ctx.session, ctx.rules, elite, table.seize_coin)
    tally.seized += 1
    await note(
        ctx,
        f"{elite.name} seized the burned land of {town.name}; {several(row.seized, 'person', 'people')} lost their homes to it.",
        key="reconstruction.seized",
        ids=[elite.id, town.id],
    )


async def plan_rebuild(ctx: TickContext, row: ReconstructionRow, town: EntityRow, profile: SettlementProfileRow, knowledge: KnowledgeMap) -> None:
    table = ctx.rules.reconstruction
    hasty = table.cost * (TIERS.index(profile.size_tier) + 1)
    planned = hasty * table.planned_pct // PERCENT
    planner = await best_architect(ctx, town)
    able = planner is not None and knowledge.level(town.id, KnowledgeBranch.ARCHITECTURE) >= table.architecture_level
    if able and profile.treasury * 2 >= planned and "plan" not in row.locked:
        row.plan = RebuildPlan.PLANNED
    put(row, "cost", planned if row.plan is RebuildPlan.PLANNED else hasty)
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
    row.finished_epoch = ctx.epoch
    how = "on a new plan, in stone and with wider streets" if row.plan is RebuildPlan.PLANNED else "in haste, as it stood before"
    await note(ctx, f"{town.name} was rebuilt {how}.", key=f"reconstruction.{row.plan.value}", ids=[town.id])


async def rebuild(ctx: TickContext, tally: ResilienceTally) -> None:
    table = ctx.rules.reconstruction
    knowledge = await KnowledgeMap.load(ctx.session)
    rows = list(await ctx.session.scalars(select(ReconstructionRow).where(ReconstructionRow.finished_epoch.is_(None)).order_by(ReconstructionRow.id)))
    for row in rows:
        town = await ctx.session.get(EntityRow, row.settlement_entity_id)
        profile = await ctx.session.get(SettlementProfileRow, row.settlement_entity_id)
        if town is None or profile is None or held(town.id):
            continue
        tally.rebuilding += 1
        if row.cost == 0:
            await plan_rebuild(ctx, row, town, profile, knowledge)
            if row.cause in SEIZING and row.seized_by_node_id is None and ctx.rng(f"rebuild.seize.{row.id}").chance(table.seize_pct):
                await seize(ctx, row, town, profile, tally)
        due = max(0, row.cost - row.paid)
        built = await town_of(ctx, town, knowledge)
        paid = -ledger(ctx, built, TreasuryEntry.REBUILDING, -min(due, profile.treasury * table.pay_pct // PERCENT), "rebuilding") if due else 0
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
