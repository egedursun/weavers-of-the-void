from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.renown import ENTITY_LORE, FACTION_LORE
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderTechniqueRow, ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.region import PolityMapKnowledgeRow
from aerona.db.tables.renown import LoreTradeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.renown import LoreKind, LorePrice, ReputationAxis
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.relations.book import ensure_relation, shift
from aerona.engine.renown.book import acclaim
from aerona.engine.renown.lore_kinds import WIDER_LORE, HeldIndex, by_holder

Item = tuple[LoreKind, str, int | None]
SEEKERS = frozenset({EntityType.FACTION, EntityType.CULT, EntityType.BEAST, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.POLITY})


@dataclass
class LoreTally:
    trades: int = 0
    value: int = 0


async def wants_of(session: AsyncSession, seeker: EntityRow) -> frozenset[LoreKind]:
    if seeker.entity_type is EntityType.FACTION:
        profile = await session.get(FactionProfileRow, seeker.id)
        return FACTION_LORE.get(profile.kind, frozenset()) if profile is not None else frozenset()
    if seeker.entity_type is EntityType.POLITY:
        return frozenset({LoreKind.MAP})
    return ENTITY_LORE.get(seeker.entity_type, frozenset())


@memoized(HolderTechniqueRow)
async def technique_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for holder, technique in await session.execute(select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique)):
        found.setdefault(holder, set()).add((technique.value, None))
    return by_holder(found)


@memoized(HolderTechniqueRow)
async def technique_counts(session: AsyncSession) -> Counter[Technique]:
    return Counter(await session.scalars(select(HolderTechniqueRow.technique)))


@memoized(PolityMapKnowledgeRow)
async def map_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for polity, region in await session.execute(
        select(PolityMapKnowledgeRow.polity_entity_id, PolityMapKnowledgeRow.region_entity_id).where(PolityMapKnowledgeRow.level > 0)
    ):
        found.setdefault(polity, set()).add(("region", region))
    return by_holder(found)


@memoized(PolityMapKnowledgeRow)
async def map_counts(session: AsyncSession) -> Counter[int]:
    return Counter(await session.scalars(select(PolityMapKnowledgeRow.region_entity_id).where(PolityMapKnowledgeRow.level > 0)))


@memoized(ProphecyConditionRow)
async def prophecy_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for prophecy, audience in await session.execute(select(ProphecyConditionRow.prophecy_entity_id, ProphecyConditionRow.audience)):
        for holder in audience or []:
            found.setdefault(holder, set()).add(("prophecy", prophecy))
    return by_holder(found)


async def holdings(session: AsyncSession, holder_id: int, kind: LoreKind) -> set[tuple[str, int | None]]:
    if kind in WIDER_LORE:
        return await WIDER_LORE[kind].holdings(session, holder_id)
    if kind is LoreKind.TECHNIQUE:
        return set((await technique_index(session)).get(holder_id, frozenset()))
    if kind is LoreKind.SITE:
        places = select(EntityRow.id).where(EntityRow.entity_type == EntityType.PLACE)
        bonds = select(BondRow.target_node_id).where(
            BondRow.source_node_id == holder_id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(places)
        )
        return {("site", place) for place in await session.scalars(bonds)}
    if kind is LoreKind.MAP:
        return set((await map_index(session)).get(holder_id, frozenset()))
    return set((await prophecy_index(session)).get(holder_id, frozenset()))


async def holders(session: AsyncSession, item: Item) -> int:
    kind, key, subject = item
    if kind in WIDER_LORE:
        return await WIDER_LORE[kind].holders(session, subject)
    if kind is LoreKind.TECHNIQUE:
        return (await technique_counts(session))[Technique(key)]
    if kind is LoreKind.SITE:
        query = (
            select(func.count())
            .select_from(BondRow)
            .where(BondRow.target_node_id == subject, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
        )
        return int(await session.scalar(query) or 0)
    if kind is LoreKind.MAP:
        return (await map_counts(session))[subject] if subject is not None else 0
    row = await session.get(ProphecyConditionRow, subject) if subject is not None else None
    return len(row.audience or []) if row is not None else 0


async def value_of(ctx: TickContext, item: Item) -> int:
    return round(ctx.rules.lore_trade.base_value * PERCENT / (PERCENT + PERCENT * await holders(ctx.session, item)))


async def grant(ctx: TickContext, holder: EntityRow, item: Item) -> bool:
    kind, key, subject = item
    if held(holder.id):
        return False
    if kind in WIDER_LORE:
        granted = await WIDER_LORE[kind].grant(ctx, holder, subject)
        await ctx.session.flush()
        return granted
    if kind is LoreKind.TECHNIQUE:
        if await ctx.session.get(HolderTechniqueRow, (holder.id, Technique(key))) is not None:
            return False
        ctx.session.add(HolderTechniqueRow(holder_entity_id=holder.id, technique=Technique(key), since_epoch=ctx.epoch, secret=False))
    elif kind is LoreKind.SITE and subject is not None:
        await connect(ctx.session, holder.id, subject, BondKind.KNOWS, ctx.epoch, description="told where it lies")
    elif kind is LoreKind.MAP and subject is not None:
        row = await ctx.session.get(PolityMapKnowledgeRow, (holder.id, subject))
        if row is None:
            ctx.session.add(PolityMapKnowledgeRow(polity_entity_id=holder.id, region_entity_id=subject, level=1, held=False, updated_epoch=ctx.epoch))
        elif not row.held:
            row.level, row.updated_epoch = row.level + 1, ctx.epoch
    elif kind is LoreKind.PROPHECY and subject is not None:
        prophecy = await ctx.session.get(ProphecyConditionRow, subject)
        if prophecy is None or holder.id in (prophecy.audience or []):
            return False
        prophecy.audience = [*(prophecy.audience or []), holder.id]
    await ctx.session.flush()
    return True


async def pay(ctx: TickContext, seller: EntityRow, buyer: EntityRow, value: int) -> LorePrice:
    table = ctx.rules.lore_trade
    cost = max(1, value // table.wealth_per_value)
    purse = await ctx.session.get(FactionProfileRow, buyer.id)
    if purse is not None and purse.treasury >= cost and "treasury" not in purse.locked:
        till = await ctx.session.get(FactionProfileRow, seller.id)
        if till is None:
            purse.treasury -= cost
            return LorePrice.WEALTH
        if move_amount(purse, till, "treasury", cost):
            return LorePrice.WEALTH
    home = buyer.location_id or buyer.id
    await acclaim(ctx.session, seller.id, home, ReputationAxis.WISDOM, amount=value / table.renown_per_value, epoch=ctx.epoch)
    return LorePrice.RENOWN


async def neighbours(ctx: TickContext, atlas: RegionAtlas, seeker: EntityRow) -> list[EntityRow]:
    home = atlas.top_region(seeker.id)
    if home is None:
        return []
    regions = [home, *atlas.neighbour_regions(home)]
    found = []
    for region in regions:
        for community_id in atlas.communities_in(region):
            entity = await living_entity(ctx.session, community_id)
            if entity is not None and entity.id != seeker.id:
                found.append(entity)
    return found


async def best_offer(ctx: TickContext, seeker: EntityRow, sellers: list[EntityRow], kinds: frozenset[LoreKind]) -> tuple[EntityRow, Item, int] | None:
    best: tuple[EntityRow, Item, int] | None = None
    for kind in sorted(kinds, key=lambda item: item.value):
        mine = await holdings(ctx.session, seeker.id, kind)
        for seller in sellers:
            for key, subject in sorted(await holdings(ctx.session, seller.id, kind) - mine, key=str):
                item = (kind, key, subject)
                value = await value_of(ctx, item)
                if best is None or value > best[2]:
                    best = (seller, item, value)
    return best


async def trade(ctx: TickContext, seller: EntityRow, buyer: EntityRow, item: Item, *, value: int, price: LorePrice | None = None) -> LoreTradeRow | None:
    if not await grant(ctx, buyer, item):
        return None
    paid = price or await pay(ctx, seller, buyer, value)
    row = LoreTradeRow(
        seller_node_id=seller.id, buyer_node_id=buyer.id, kind=item[0], key=item[1], subject_node_id=item[2], value=value, price=paid, epoch=ctx.epoch
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def market(ctx: TickContext, tally: LoreTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    seekers = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(SEEKERS)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for seeker in list(seekers):
        if held(seeker.id) or not ctx.rng(seed_of("lore", seeker.id, ctx.epoch)).chance(ctx.rules.lore_trade.trade_pct):
            continue
        kinds = await wants_of(ctx.session, seeker)
        if not kinds:
            continue
        offer = await best_offer(ctx, seeker, await neighbours(ctx, atlas, seeker), kinds)
        if offer is None:
            continue
        seller, item, value = offer
        if await trade(ctx, seller, seeker, item, value=value) is not None:
            tally.trades += 1
            tally.value += value


async def confide(ctx: TickContext, actor: EntityRow, target: EntityRow) -> bool:
    table = ctx.rules.lore_trade
    source = actor.location_id
    keeper = await people_of(ctx.session, target)
    if source is None or keeper is None or not ctx.rng(seed_of("confide_lore", actor.id, target.id, ctx.epoch)).chance(table.confide_pct):
        return False
    secrets = await ctx.session.scalars(
        select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == source, HolderTechniqueRow.secret.is_(True))
    )
    known = await holdings(ctx.session, keeper.id, LoreKind.TECHNIQUE)
    for technique in secrets:
        item = (LoreKind.TECHNIQUE, technique.value, None)
        if (technique.value, None) in known:
            continue
        value = await value_of(ctx, item)
        if await trade(ctx, actor, keeper, item, value=value, price=LorePrice.FAVOUR) is None:
            return False
        bond = await ensure_relation(ctx.session, target.id, actor.id, ctx.epoch)
        if bond is not None:
            shift(ctx.rules, bond, ctx.epoch, friendship=table.favour_friendship * value / PERCENT)
        return True
    return False
