from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, or_, select

from aerona.catalog.arcana import RECHARGES, SCHOOL_GRAMMAR, SKY_SIGNS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow, ItemProfileRow, RiteProfileRow
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import RechargeRule, SpellForm
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.engine.arcana.vis import take_vis
from aerona.engine.arcana.warping import expose
from aerona.engine.body.afflictions import first_moon
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import set_stats, stat_or

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


@dataclass(frozen=True)
class Filling:
    ctx: TickContext
    atlas: RegionAtlas
    spell: ItemEnchantmentRow
    item: EntityRow


async def by_site(fill: Filling) -> bool:
    return await near_site(fill.ctx, fill.atlas, fill.item)


async def by_vis(fill: Filling) -> bool:
    owner = await owner_of(fill.ctx, fill.item.id)
    return owner is not None and await take_vis(fill.ctx, owner, await form_of(fill.ctx, fill.spell), fill.ctx.rules.enchanted_items.vis_recharge_cost)


async def by_moon(fill: Filling) -> bool:
    return await full_moon(fill.ctx, fill.item.world_id)


async def never(fill: Filling) -> bool:
    return False


async def by_sky(fill: Filling) -> bool:
    if fill.item.world_id is None:
        return False
    sign = await fill.ctx.session.scalar(
        select(SkyEventRow.id)
        .where(
            SkyEventRow.world_id == fill.item.world_id,
            SkyEventRow.kind.in_(sorted(SKY_SIGNS)),
            SkyEventRow.epoch <= fill.ctx.epoch,
            or_(SkyEventRow.until_epoch.is_(None), SkyEventRow.until_epoch >= fill.ctx.epoch),
        )
        .limit(1)
    )
    return sign is not None


async def by_offering(fill: Filling) -> bool:
    owner_id = await owner_of(fill.ctx, fill.item.id)
    owner = await living_entity(fill.ctx.session, owner_id) if owner_id is not None else None
    if owner is None or owner.entity_type is not EntityType.MORTAL or held(owner.id) or stat_or(owner, "hp", 0) <= fill.ctx.rules.arcana.bodily_offering_harm:
        return False
    set_stats(owner, hp=stat_or(owner, "hp", 0) - fill.ctx.rules.arcana.bodily_offering_harm)
    await judged(fill.ctx, owner.id, owner.id, ActKind.BLOOD_MAGIC, note="gave of its body to an enchanted thing")
    return True


async def by_rest(fill: Filling) -> bool:
    owner_id = await owner_of(fill.ctx, fill.item.id)
    if owner_id is None:
        return False
    worked = await fill.ctx.session.scalar(select(CastingRow.id).where(CastingRow.caster_entity_id == owner_id, CastingRow.epoch == fill.ctx.epoch).limit(1))
    return worked is None


async def by_worship(fill: Filling) -> bool:
    owner_id = await owner_of(fill.ctx, fill.item.id)
    if owner_id is None:
        return False
    praying = await fill.ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.target_node_id == owner_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    return int(praying or 0) > 0


FILLERS: Mapping[RechargeRule, Callable[[Filling], Awaitable[bool]]] = total(
    RechargeRule,
    {
        RechargeRule.SITE: by_site,
        RechargeRule.VIS: by_vis,
        RechargeRule.MOON: by_moon,
        RechargeRule.NONE: never,
        RechargeRule.SKY_EVENT: by_sky,
        RechargeRule.BODILY_OFFERING: by_offering,
        RechargeRule.REST: by_rest,
        RechargeRule.WORSHIP: by_worship,
    },
)


async def worship_scale(ctx: TickContext, spell: ItemEnchantmentRow, item: EntityRow) -> int:
    if spell.recharge is not RechargeRule.WORSHIP:
        return 1
    owner_id = await owner_of(ctx, item.id)
    praying = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.target_node_id == owner_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    return max(1, int(praying or 0) // PERCENT)


async def recharge(ctx: TickContext, atlas: RegionAtlas, spell: ItemEnchantmentRow, item: EntityRow) -> int:
    room = spell.capacity - spell.charges
    if room <= 0 or not await FILLERS[spell.recharge](Filling(ctx, atlas, spell, item)):
        return 0
    gained = min(room, RECHARGES[spell.recharge].fill(ctx.rules) * await worship_scale(ctx, spell, item))
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
