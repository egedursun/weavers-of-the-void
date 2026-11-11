from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.arcana import SCHOOL_GRAMMAR, TRAIT_FORMS
from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import VisStockRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.dominion import MagicSiteKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import receive_coin, take_coin
from aerona.engine.faith.book import faith_tenets
from aerona.engine.gods.queries import community_of
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon


@dataclass
class VisTally:
    gathered: int = 0
    traded: int = 0
    smuggled: int = 0


def site_form(site: MagicSiteRow) -> SpellForm:
    return SCHOOL_GRAMMAR[site.school][1]


async def stock(ctx: TickContext, holder_id: int, form: SpellForm) -> VisStockRow:
    row = await ctx.session.get(VisStockRow, (holder_id, form))
    if row is None:
        row = VisStockRow(holder_node_id=holder_id, form=form, amount=0, locked=[])
        ctx.session.add(row)
    return row


async def vis_of(ctx: TickContext, holder_id: int, form: SpellForm) -> int:
    row = await ctx.session.get(VisStockRow, (holder_id, form))
    return row.amount if row is not None else 0


async def give_vis(ctx: TickContext, holder_id: int, form: SpellForm, amount: int) -> int:
    if amount <= 0 or held(holder_id):
        return 0
    row = await stock(ctx, holder_id, form)
    if "amount" in row.locked:
        return 0
    row.amount = max(0, (row.amount or 0) + amount)
    return amount


async def take_vis(ctx: TickContext, holder_id: int, form: SpellForm, amount: int) -> bool:
    row = await ctx.session.get(VisStockRow, (holder_id, form))
    if amount <= 0:
        return True
    if row is None or row.amount < amount or held(holder_id) or "amount" in row.locked:
        return False
    row.amount -= amount
    return True


ORDER_TYPES = frozenset({EntityType.FACTION, EntityType.CULT})


async def orders_of(ctx: TickContext, caster: EntityRow) -> list[int]:
    if caster.entity_type is EntityType.MORTAL:
        joined = select(BondRow.target_node_id).where(
            BondRow.source_node_id == caster.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE
        )
        found = select(EntityRow.id).where(EntityRow.id.in_(joined), EntityRow.entity_type.in_(ORDER_TYPES)).order_by(EntityRow.id)
        return list(await ctx.session.scalars(found))
    if caster.entity_type in ORDER_TYPES:
        members = select(BondRow.source_node_id).where(
            BondRow.target_node_id == caster.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE
        )
        mages = select(EntityRow.id).where(EntityRow.id.in_(members), EntityRow.entity_type == EntityType.MORTAL).order_by(EntityRow.id)
        return list(await ctx.session.scalars(mages))
    return []


async def purse_of(ctx: TickContext, mortal: EntityRow) -> list[int]:
    community = await community_of(ctx.session, mortal) if mortal.entity_type is EntityType.MORTAL else None
    orders = [order for order in await orders_of(ctx, mortal) if community is None or order != community.id]
    return [mortal.id, *orders, *([community.id] if community is not None else [])]


async def burn_for(ctx: TickContext, caster: EntityRow, form: SpellForm | None, amount: int) -> bool:
    for holder in await purse_of(ctx, caster):
        forms = [form] if form is not None else await richest_forms(ctx, holder, amount)
        for each in forms:
            if await take_vis(ctx, holder, each, amount):
                return True
    return False


async def richest_forms(ctx: TickContext, holder_id: int, amount: int) -> list[SpellForm]:
    rows = await ctx.session.scalars(
        select(VisStockRow.form)
        .where(VisStockRow.holder_node_id == holder_id, VisStockRow.amount >= amount)
        .order_by(VisStockRow.amount.desc(), VisStockRow.form)
    )
    return list(rows)


async def from_sites(ctx: TickContext, tally: VisTally) -> None:
    table = ctx.rules.vis
    sites = await ctx.session.scalars(
        select(MagicSiteRow).where(MagicSiteRow.kind == MagicSiteKind.SOURCE, MagicSiteRow.found_epoch.is_not(None), MagicSiteRow.holder_node_id.is_not(None))
    )
    for site in list(sites):
        if site.holder_node_id is None or held(site.place_entity_id):
            continue
        tally.gathered += await give_vis(ctx, site.holder_node_id, site_form(site), round_half_up(table.site_yield * site.strength / PERCENT))


async def from_beasts(ctx: TickContext, atlas: RegionAtlas, tally: VisTally) -> None:
    table = ctx.rules.vis
    traits = await ctx.session.execute(
        select(EntityTraitRow.entity_id, EntityTraitRow.trait)
        .join(EntityRow, EntityRow.id == EntityTraitRow.entity_id)
        .where(EntityRow.entity_type == EntityType.BEAST)
    )
    by_beast: dict[int, list[SpellForm]] = {}
    for beast_id, trait in traits:
        form = TRAIT_FORMS.get(trait)
        if form is not None:
            by_beast.setdefault(int(beast_id), []).append(form)
    for beast_id, forms in sorted(by_beast.items()):
        region = atlas.top_region(beast_id)
        folk = [community for community in atlas.communities_in(region)] if region is not None else []
        if not folk or not ctx.rng(f"vis.beast.{beast_id}.{ctx.epoch}").chance(table.beast_pct):
            continue
        tally.gathered += await give_vis(ctx, folk[0], forms[0], table.beast_yield)


async def from_phenomena(ctx: TickContext, atlas: RegionAtlas, tally: VisTally) -> None:
    for phenomenon in await canon(ctx.session, [EntityType.PHENOMENON]):
        region = atlas.top_region(phenomenon.id)
        folk = list(atlas.communities_in(region)) if region is not None else []
        if folk:
            tally.gathered += await give_vis(ctx, folk[0], SpellForm.VOID, ctx.rules.vis.phenomenon_yield)


async def banned(ctx: TickContext, community_id: int) -> bool:
    if TenetKind.ANTI_MAGIC in await faith_tenets(ctx.session, community_id):
        return True
    return await law_param(ctx.session, community_id, LawKind.RITE_RESTRICTIONS, "level") is not None


async def sell(ctx: TickContext, seller: EntityRow, buyer: EntityRow, row: VisStockRow, tally: VisTally) -> bool:
    table = ctx.rules.vis
    units = min(table.trade_units, row.amount - table.surplus)
    if units <= 0 or not await take_coin(ctx.session, ctx.rules, buyer, units * table.price):
        return False
    row.amount -= units
    await give_vis(ctx, buyer.id, row.form, units)
    await receive_coin(ctx.session, ctx.rules, seller, units * table.price)
    tally.traded += units
    for side in (seller, buyer):
        town = await ctx.session.get(SettlementProfileRow, side.id)
        if town is not None and await banned(ctx, side.id) and "crime" not in town.locked:
            town.crime = clamp_int(town.crime + table.black_market_crime, 0, PERCENT)
            tally.smuggled += units
    return True


async def trade(ctx: TickContext, atlas: RegionAtlas, tally: VisTally) -> None:
    table = ctx.rules.vis
    rich = await ctx.session.scalars(select(VisStockRow).where(VisStockRow.amount > table.surplus).order_by(VisStockRow.holder_node_id, VisStockRow.form))
    for row in list(rich):
        seller = await ctx.session.get(EntityRow, row.holder_node_id)
        if seller is None or seller.entity_type not in COMMUNITY_TYPES or held(seller.id) or "amount" in row.locked:
            continue
        region = atlas.top_region(seller.id)
        near = {region, *atlas.neighbour_regions(region)} if region is not None else set()
        for other_id in sorted(community for place in near if place is not None for community in atlas.communities_in(place)):
            if other_id == seller.id or held(other_id) or await vis_of(ctx, other_id, row.form) > 0:
                continue
            buyer = await ctx.session.get(EntityRow, other_id)
            if buyer is not None and await sell(ctx, seller, buyer, row, tally):
                break


async def flow_vis(ctx: TickContext, tally: VisTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await from_sites(ctx, tally)
    await from_beasts(ctx, atlas, tally)
    await from_phenomena(ctx, atlas, tally)
    await trade(ctx, atlas, tally)
    await ctx.session.flush()
