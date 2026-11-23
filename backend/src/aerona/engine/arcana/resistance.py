from sqlalchemy import select

from aerona.catalog.arcana import IRON_DISRUPTED
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import LawUpkeepRow, RiteGrammarRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemEnchantmentRow, ItemProfileRow, RiteProfileRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.arcana import LawSource
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import Attribute
from aerona.engine.body.afflictions import cure
from aerona.engine.constructs.wards import unbind
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.faith.book import patron_node
from aerona.engine.mind.split import attribute
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat

DISPELLED_BY = frozenset({Transmission.RITE, Transmission.CURSE})


async def carries_iron(ctx: TickContext, target: EntityRow) -> bool:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == target.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.material == MaterialKind.IRON.value).limit(1)
    )
    return found is not None


async def sanctity_at(ctx: TickContext, target: EntityRow) -> int:
    place = await ctx.session.get(PlaceProfileRow, target.location_id or target.id)
    return place.sacredness if place is not None else 0


async def resistance_of(ctx: TickContext, target: EntityRow, *, caster_god: int | None, form_disrupted: bool, warded: float) -> int:
    table = ctx.rules.spell_resistance
    will = await attribute(ctx.session, ctx.rules, target, Attribute.WILLPOWER) if target.entity_type is EntityType.MORTAL else 0
    total = will * table.willpower_pct / PERCENT
    total += (warded - 1) * PERCENT * table.ward / PERCENT
    if form_disrupted and await carries_iron(ctx, target):
        total += table.iron
    total += await sanctity_at(ctx, target) * table.sanctity_pct / PERCENT
    atlas = await RegionAtlas.load(ctx.session)
    book = await DominionBook.load(ctx.session)
    region = atlas.top_region(target.id)
    ruler = book.ruler(ctx.rules, region)
    if ruler is not None and caster_god is not None and ruler != caster_god:
        total += book.share(region, ruler) * table.hostile_dominion_pct / PERCENT
    target_god = await patron_node(ctx.session, target.location_id or target.id)
    if target_god is not None and caster_god is not None and target_god != caster_god:
        total += (stat(target, "piety") or 0) * table.faith_pct / PERCENT
    return clamp_int(total, 0, PERCENT * 2)


def penetration_of(ctx: TickContext, row: RiteProfileRow, mastery: int) -> int:
    table = ctx.rules.spell_resistance
    return round_half_up(row.power * table.penetration_per_power + mastery * table.penetration_skill_pct / PERCENT)


def disrupted(grammar: RiteGrammarRow | None) -> bool:
    return grammar is not None and grammar.form in IRON_DISRUPTED


async def break_curses(ctx: TickContext, target: EntityRow, force: int) -> list[str]:
    broken: list[str] = []
    for row in list(await ctx.session.scalars(select(AfflictionRow).where(AfflictionRow.bearer_node_id == target.id, AfflictionRow.cured_epoch.is_(None)))):
        if row.transmission not in DISPELLED_BY or "stage" in row.locked or force < (row.stage + 1) * PERCENT // 4:
            continue
        await cure(ctx, target, row, None)
        broken.append(spoken(row.package))
    return broken


async def break_enchantments(ctx: TickContext, target: EntityRow, force: int) -> int:
    weakened = 0
    for row in list(await ctx.session.scalars(select(ItemEnchantmentRow).where(ItemEnchantmentRow.item_entity_id == target.id))):
        row.strength = clamp_int(row.strength - force, 0, PERCENT)
        weakened += 1
    return weakened


async def break_laws(ctx: TickContext, caster_id: int, region_id: int | None, world_id: int | None, force: int) -> list[str]:
    ended: list[str] = []
    upkept = await ctx.session.execute(
        select(LawUpkeepRow, NaturalLawProfileRow).join(NaturalLawProfileRow, NaturalLawProfileRow.law_entity_id == LawUpkeepRow.law_entity_id)
    )
    for upkeep, law in list(upkept):
        if upkeep.source is not LawSource.ENCHANTMENT or upkeep.caster_node_id == caster_id or held(law.law_entity_id) or force <= upkeep.dispel_resistance:
            continue
        if law.region_entity_id not in {None, region_id} or law.world_id not in {None, world_id}:
            continue
        entity = await ctx.session.get(EntityRow, law.law_entity_id)
        if entity is None or entity.status is not EntityStatus.CANON:
            continue
        entity.status, entity.end_epoch = EntityStatus.DESTROYED, ctx.epoch
        ended.append(entity.name)
    return ended


async def dispel_force(ctx: TickContext, caster: EntityRow, target: EntityRow | None, power: int) -> str:
    force = power * ctx.rules.spell_resistance.dispel_per_power
    aim = target if target is not None else caster
    parts: list[str] = []
    curses = await break_curses(ctx, aim, force)
    if curses:
        parts.append(f"lifted {', '.join(curses)} from {aim.name}")
    if aim.entity_type is EntityType.ITEM and await break_enchantments(ctx, aim, force):
        parts.append(f"weakened the enchantments of {aim.name}")
    unbound = await unbind(ctx, aim, force)
    if unbound:
        parts.append(unbound)
    laws = await break_laws(ctx, caster.id, (await RegionAtlas.load(ctx.session)).top_region(aim.id), aim.world_id, force)
    if laws:
        parts.append(f"unmade {', '.join(laws)}")
    return "; ".join(parts) or f"found nothing to dispel on {aim.name}"
