from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.arcana import SCHOOL_GRAMMAR
from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemEnchantmentRow, ItemProfileRow, RiteProfileRow
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import RechargeRule, SpellForm
from aerona.domain.enums.bond import BondKind, BondState
from aerona.engine.arcana.vis import take_vis
from aerona.engine.arcana.warping import expose
from aerona.engine.body.afflictions import first_moon
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or

FULL_MOON = PERCENT // 2


@dataclass
class ChargeTally:
    recharged: int = 0
    cracked: int = 0


async def use_charge(ctx: TickContext, item: EntityRow, spell: ItemEnchantmentRow, bearer: EntityRow | None) -> bool:
    if bearer is not None:
        await expose(ctx, bearer.id, ctx.rules.warping.item)
    if spell.charges > 0:
        spell.charges -= 1
        return True
    profile = await ctx.session.get(ItemProfileRow, item.id)
    spell.overuse += 1
    if profile is not None and "condition" not in profile.locked:
        profile.condition = clamp_int(profile.condition - ctx.rules.enchanted_items.crack, 0, PERCENT)
    return False


async def form_of(ctx: TickContext, spell: ItemEnchantmentRow) -> SpellForm:
    grammar = await ctx.session.get(RiteGrammarRow, spell.rite_entity_id) if spell.rite_entity_id is not None else None
    if grammar is not None:
        return grammar.form
    profile = await ctx.session.get(RiteProfileRow, spell.rite_entity_id) if spell.rite_entity_id is not None else None
    return SCHOOL_GRAMMAR[profile.school][1] if profile is not None else SpellForm.SPIRIT


async def owner_of(ctx: TickContext, item_id: int) -> int | None:
    return await ctx.session.scalar(
        select(BondRow.source_node_id).where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).limit(1)
    )


async def near_site(ctx: TickContext, atlas: RegionAtlas, item: EntityRow) -> bool:
    region = atlas.top_region(item.id)
    sites = await ctx.session.scalars(select(MagicSiteRow.place_entity_id).where(MagicSiteRow.found_epoch.is_not(None)))
    return any(atlas.top_region(place) == region for place in sites)


async def full_moon(ctx: TickContext, world_id: int | None) -> bool:
    moon = await first_moon(ctx, world_id)
    return moon is not None and stat_or(moon, "brightness", FULL_MOON) >= FULL_MOON


async def recharge(ctx: TickContext, atlas: RegionAtlas, spell: ItemEnchantmentRow, item: EntityRow) -> int:
    table = ctx.rules.enchanted_items
    room = spell.capacity - spell.charges
    if room <= 0 or spell.recharge is RechargeRule.NONE:
        return 0
    if spell.recharge is RechargeRule.SITE and await near_site(ctx, atlas, item):
        gained = min(room, table.site_recharge)
    elif spell.recharge is RechargeRule.MOON and await full_moon(ctx, item.world_id):
        gained = min(room, table.moon_recharge)
    elif spell.recharge is RechargeRule.VIS:
        owner = await owner_of(ctx, item.id)
        gained = 1 if owner is not None and await take_vis(ctx, owner, await form_of(ctx, spell), table.vis_recharge_cost) else 0
    else:
        gained = 0
    spell.charges += gained
    return gained


async def recharge_all(ctx: TickContext, tally: ChargeTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for spell in list(await ctx.session.scalars(select(ItemEnchantmentRow).order_by(ItemEnchantmentRow.item_entity_id, ItemEnchantmentRow.effect))):
        item = await ctx.session.get(EntityRow, spell.item_entity_id)
        if item is None or held(item.id):
            continue
        tally.recharged += await recharge(ctx, atlas, spell, item)
        tally.cracked += int(spell.overuse > 0)
    await ctx.session.flush()
