from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.conditions import CURABLE_CONDITIONS
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.lore import ITEM_CLASSES, KNOWLEDGE_ITEMS, REGALIA, WEAPONS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.record_context import Term
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, ProsthesisRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import HolderLevelRow, ItemEnchantmentRow, ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import RelicRow, SpiritProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind, CustomCatalog, ItemClass, ItemDeed, RiteEffectKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialFamily, MaterialSlot
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import AfterlifeState, BindingKind, SpiritAlignment
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind, SkillKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.engine.arcana.items import use_charge
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.conditions import end_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import WORLD_KEY_PREFIX, MaterialBook, MaterialProps, battle_wear, enchantment_cap, node_material, slot_key, worth_factor
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.environment.harvest_harm import shift_harvest
from aerona.engine.faith.book import patron_node
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.arms import GUARDS
from aerona.engine.lore.history import record
from aerona.engine.lore.intel import gain_intel
from aerona.engine.lore.kinds import ItemClassParams, kind_of, params_of
from aerona.engine.mind.memories import remember
from aerona.engine.mind.thoughts import mood_factor, mood_of, think
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, close, connect, flags_by_entity, living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.primitives.threads import open_story
from aerona.engine.recording.record import StepDraft
from aerona.engine.recording.record import record as record_incident

HALF = 2
TEN = 10
WORLD_PREFIX = WORLD_KEY_PREFIX
CURABLE = CURABLE_CONDITIONS
C = ItemClass
E = RiteEffectKind
WAYFINDERS = frozenset({C.MAP, C.ASTROLABE})
ORGANIC_CLOTH = frozenset(materials_with(MaterialTrait.ORGANIC_CLOTH))
FAMILY_STOCK = {
    MaterialFamily.METAL: CommodityKind.ORE,
    MaterialFamily.PRECIOUS: CommodityKind.ORE,
    MaterialFamily.EXOTIC: CommodityKind.ORE,
    MaterialFamily.STONE: CommodityKind.STONE,
    MaterialFamily.ORGANIC: CommodityKind.TIMBER,
}


def fallback_class(item: EntityRow) -> ItemClass:
    if item.engine_kind is not None and item.engine_kind.value == "currency":
        return C.CURRENCY
    if (stat(item, "damage") or 0) > 0:
        return C.BLADE
    if (stat(item, "protection") or 0) > 0:
        return C.ARMOUR
    return C.JEWEL


async def owner_of(ctx: TickContext, item_id: int) -> int | None:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(statement.order_by(BondRow.id.desc()).limit(1))


CURSES = (
    (WEAPONS, CurseKind.BLOODTHIRST),
    (frozenset({C.CROWN, C.SCEPTRE, C.SEAL, C.STANDARD, C.KEY}), CurseKind.BETRAYAL),
    (frozenset({C.JEWEL}), CurseKind.MADNESS),
    (frozenset({C.ARMOUR, C.SHIELD, C.HELMET, C.PROSTHESIS}), CurseKind.WASTING),
    (frozenset({C.RING}), CurseKind.COMPULSION),
    (frozenset({C.MIRROR}), CurseKind.AGING),
    (frozenset({C.IDOL, C.HOLY_RELIC}), CurseKind.LINE_CURSE),
    (frozenset({C.INSTRUMENT}), CurseKind.SILENCE),
    (frozenset({C.BOOK, C.SCROLL, C.PRAYER_BOOK}), CurseKind.FORGETTING),
    (frozenset({C.ASTROLABE, C.MAP}), CurseKind.RESTLESSNESS),
    (frozenset({C.CLOAK, C.PADDING}), CurseKind.SLEEP),
    (frozenset({C.VESSEL_OBJECT}), CurseKind.HUNGER),
    (frozenset({C.IMPLANT, C.DRUG}), CurseKind.TRANSFORMATION),
    (frozenset({C.COMMUNICATOR, C.COMPUTER, C.DEVICE}), CurseKind.EXPOSURE),
    (frozenset({C.TOOL}), CurseKind.BARRENNESS),
    (frozenset({C.CURRENCY}), CurseKind.PLACE_CURSE),
)


def curse_for(item_class: ItemClass) -> CurseKind:
    return next((kind for classes, kind in CURSES if item_class in classes), CurseKind.MISFORTUNE)


def material_key(row: NodeMaterialRow | None) -> str | None:
    return slot_key(row.material, row.world_material_id) if row is not None else None


def props_of(book: MaterialBook, world_id: int | None, key: str | None) -> MaterialProps | None:
    if not key:
        return None
    if key.startswith(WORLD_PREFIX):
        number = key.removeprefix(WORLD_PREFIX)
        return book.props(world_id, None, int(number)) if number.isdigit() else None
    try:
        return book.props(world_id, MaterialKind(key))
    except ValueError:
        return None


async def apply_custom_class(ctx: TickContext, row: ItemProfileRow) -> None:
    custom = await kind_of(ctx.session, row.custom_class_id, CustomCatalog.ITEM_CLASS)
    if custom is None:
        return
    params = params_of(custom, ItemClassParams)
    row.item_class = C(custom.base)
    for key in ("damage_type", "reach", "coverage", "weight"):
        value = getattr(params, key)
        if value is not None and key not in row.locked:
            setattr(row, key, value.value if hasattr(value, "value") else value)


async def profile_of(ctx: TickContext, item: EntityRow, item_class: ItemClass | None = None) -> ItemProfileRow:
    row = await ctx.session.get(ItemProfileRow, item.id)
    if row is not None:
        return row
    chosen = item_class or fallback_class(item)
    spec = ITEM_CLASSES[chosen]
    might = stat(item, "might") or 0
    quality = clamp_int(PERCENT // 2 + might // 2 + (stat(item, "damage") or 0) // 4, 0, PERCENT)
    slots = list(await ctx.session.scalars(select(NodeMaterialRow).where(NodeMaterialRow.node_id == item.id).order_by(NodeMaterialRow.slot)))
    body = next((slot for slot in slots if slot.slot is MaterialSlot.BODY), slots[0] if slots else None)
    row = ItemProfileRow(
        item_entity_id=item.id,
        item_class=chosen,
        material=material_key(body),
        secondary_materials=[key for key in (material_key(slot) for slot in slots if slot is not body) if key],
        quality=quality,
        condition=PERCENT,
        damage_type=spec.damage_type,
        reach=spec.reach,
        coverage=spec.coverage,
        weight=spec.weight,
        curse=curse_for(chosen) if (stat(item, "curse") or 0) >= ctx.rules.item_curses.threshold else CurseKind.NONE,
        value=quality + might,
        renown=clamp_int(item.power_level * TEN, 0, PERCENT),
        maker_entity_id=item.maker_entity_id,
        symbol=False,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    owner = await owner_of(ctx, item.id)
    record(ctx, item.id, ItemDeed.MADE, owner, f"{item.name} first entered the record")
    return row


async def living_items(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.ITEM, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


async def ruler_of(ctx: TickContext, polity_id: int) -> int | None:
    return await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )


async def give(ctx: TickContext, item: EntityRow, receiver_id: int, deed: ItemDeed, note: str) -> None:
    for bond in await active_bonds(ctx.session, [BondKind.OWNS], targets=[item.id]):
        await close(ctx.session, bond, ctx.epoch, note)
    await connect(ctx.session, receiver_id, item.id, BondKind.OWNS, ctx.epoch, description=note)
    record(ctx, item.id, deed, receiver_id, note)


async def regalia(ctx: TickContext, item: EntityRow, row: ItemProfileRow) -> str | None:
    if row.item_class not in REGALIA:
        return None
    owner = await owner_of(ctx, item.id)
    if owner is None:
        return None
    office = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == owner, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if office is None or "regalia_of" in row.locked:
        return None
    if row.regalia_of_entity_id is None:
        row.regalia_of_entity_id = office.polity_entity_id
        row.renown = clamp_int(row.renown + ctx.rules.item_renown.coronation, 0, PERCENT)
        record(ctx, item.id, ItemDeed.CORONATION, owner, "worn at the crowning")
        return "crowned"
    return None


async def usurped(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> str | None:
    if row.regalia_of_entity_id is None or row.item_class not in REGALIA or "regalia_of" in row.locked:
        return None
    ruler = await living_entity(ctx.session, await ruler_of(ctx, row.regalia_of_entity_id))
    if ruler is None or ruler.id == owner:
        return None
    if not ctx.rng(f"regalia.seize.{item.id}.{ctx.epoch}").chance(ctx.rules.item_powers.seize_chance):
        return None
    await give(ctx, item, ruler.id, ItemDeed.CAPTURED, f"seized by {ruler.name}, who would rule without it no longer")
    return ruler.name


async def captured(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> int | None:
    if row.regalia_of_entity_id is None or owner is None or not row.symbol:
        return None
    holder = await living_entity(ctx.session, owner)
    home = holder.location_id if holder is not None and holder.entity_type is EntityType.MORTAL else owner
    conqueror = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == home, BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE, BondRow.epoch >= ctx.epoch - 1)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    if conqueror is None or conqueror == row.regalia_of_entity_id:
        return None
    enemy = await ctx.session.scalar(
        select(BondRow.id)
        .where(
            BondRow.kind == BondKind.ENEMY,
            BondRow.state == BondState.ACTIVE,
            ((BondRow.source_node_id == conqueror) & (BondRow.target_node_id == row.regalia_of_entity_id))
            | ((BondRow.target_node_id == conqueror) & (BondRow.source_node_id == row.regalia_of_entity_id)),
        )
        .limit(1)
    )
    if enemy is None:
        return None
    await give(ctx, item, conqueror, ItemDeed.CAPTURED, "carried off as a prize of war")
    return conqueror


async def body_props(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow) -> MaterialProps | None:
    node = await node_material(ctx.session, item.id, MaterialSlot.BODY)
    if node is not None:
        return book.props(item.world_id, node.material, node.world_material_id)
    return props_of(book, item.world_id, row.material)


def fought_wear(ctx: TickContext, row: ItemProfileRow, props: MaterialProps | None = None) -> int:
    return battle_wear(ctx.rules, props) if row.item_class in WEAPONS | GUARDS else 0


async def decayed(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow, land: RegionEnvironmentRow | None) -> int:
    props = await body_props(ctx, book, item, row)
    if land is None or land.moisture < ctx.rules.materials.rust_wet_moisture or props is None or props.decay <= 0:
        return 0
    return max(1, round_half_up(ctx.rules.item_wear.decay_wet * props.decay / (PERCENT // HALF)))


async def wear(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow, *, land: RegionEnvironmentRow | None, fought: bool) -> bool:
    before = row.condition
    loss = (fought_wear(ctx, row, await body_props(ctx, book, item, row)) if fought else 0) + await decayed(ctx, book, item, row, land)
    if loss and (await ctx.laws()).has(NaturalLaw.METAL_RUSTS_FAST, item.world_id):
        loss = round_half_up(loss * ctx.rules.natural_laws.rust_wear_pct / PERCENT)
    row.condition = clamp_int(row.condition - loss, 0, PERCENT)
    return before >= ctx.rules.item_wear.broken > row.condition


async def fought_this_epoch(ctx: TickContext, owner: int | None) -> bool:
    if owner is None:
        return False
    count = await ctx.session.scalar(
        select(func.count(BondRow.id)).where(BondRow.source_node_id == owner, BondRow.kind == BondKind.KILLED, BondRow.epoch == ctx.epoch)
    )
    return bool(count)


async def deeds(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> int:
    if owner is None or row.item_class not in WEAPONS:
        return 0
    kills = await ctx.session.scalar(
        select(func.count(BondRow.id)).where(BondRow.source_node_id == owner, BondRow.kind == BondKind.KILLED, BondRow.epoch == ctx.epoch)
    )
    count = int(kills or 0)
    if count:
        row.renown = clamp_int(row.renown + count * ctx.rules.item_renown.kill, 0, PERCENT)
        record(ctx, item.id, ItemDeed.KILL, owner, f"{count} slain by its bearer")
    return count


def worth(ctx: TickContext, row: ItemProfileRow, props: MaterialProps | None, enchanted: int) -> int:
    table = ctx.rules.item_powers
    material = (props.base_value if props is not None else 0) * table.value_material_pct / PERCENT
    base = row.quality * (1 + row.renown / PERCENT) * (row.condition / PERCENT + 1) / HALF
    return max(0, round_half_up(base + material + enchanted // TEN * table.value_enchant))


async def bound_cap(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow) -> int:
    props = await body_props(ctx, book, item, row)
    if props is None:
        return PERCENT
    return enchantment_cap(ctx.rules, props)


async def bounded_enchantments(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow) -> list[ItemEnchantmentRow]:
    cap = await bound_cap(ctx, book, item, row)
    spells = list(await ctx.session.scalars(select(ItemEnchantmentRow).where(ItemEnchantmentRow.item_entity_id == item.id).order_by(ItemEnchantmentRow.effect)))
    for spell in spells:
        spell.strength = min(spell.strength, cap)
    return spells


async def bearer_of(ctx: TickContext, owner: int | None) -> tuple[EntityRow | None, EntityRow | None]:
    holder = await living_entity(ctx.session, owner)
    if holder is None:
        return None, None
    home = await living_entity(ctx.session, holder.location_id) if holder.entity_type is EntityType.MORTAL else holder
    return holder, home


async def mend_bearer(ctx: TickContext, holder: EntityRow, amount: int) -> bool:
    wounds = list(
        await ctx.session.scalars(
            select(InjuryRow).where(InjuryRow.bearer_node_id == holder.id, InjuryRow.state != InjuryState.LETHAL, InjuryRow.function_loss > 0)
        )
    )
    for wound in wounds:
        wound.function_loss = max(0, wound.function_loss - amount)
    return bool(wounds)


async def nearest_foe(ctx: TickContext, community_id: int) -> int | None:
    return await ctx.session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == community_id, BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
        .limit(1)
    )


async def enchant_year(ctx: TickContext, atlas: RegionAtlas, item: EntityRow, spells: list[ItemEnchantmentRow], owner: int | None) -> int:
    table = ctx.rules.enchantments
    holder, home = await bearer_of(ctx, owner)
    if holder is None:
        return 0
    worked = 0
    for spell in spells:
        await use_charge(ctx, item, spell, holder)
        size = spell.strength
        effect = spell.effect
        if effect in {E.HEAL, E.RAISE_DEAD} and holder.entity_type is EntityType.MORTAL:
            worked += int(await mend_bearer(ctx, holder, round_half_up(size * table.heal_pct / PERCENT)))
        elif effect in {E.BLESS, E.FERTILITY} and home is not None and stat(home, "prosperity") is not None:
            shift_stat(home, "prosperity", size * table.bless_pct / PERCENT)
            worked += 1
        elif effect in {E.HARVEST_BLESSING, E.WEATHER_CHANGE}:
            land = await ctx.session.get(RegionEnvironmentRow, atlas.top_region(holder.id) or 0)
            if land is not None:
                shift_harvest(land, round_half_up(size * table.harvest_pct / PERCENT))
                worked += 1
        elif effect is E.CURSE and holder.entity_type is EntityType.MORTAL:
            harm = Harm(
                damage=size * table.curse_pct / PERCENT, cause=HarmCause.CURSE, death_cause=f"withered by the spell in {item.name}", source_node_id=item.id
            )
            await apply_hits(ctx, holder, harm, lethal=False)
            worked += 1
        elif effect is E.SCRY and home is not None:
            foe = await nearest_foe(ctx, home.id)
            if foe is not None:
                await gain_intel(ctx, home.id, foe, round_half_up(size * table.scry_pct / PERCENT))
                worked += 1
        elif effect in {E.DAMAGE, E.WARD, E.BIND, E.SUMMON, E.DISPEL, E.LONGEVITY}:
            worked += 1
    return worked


async def spirit_year(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> str | None:
    spirit = await ctx.session.get(SpiritProfileRow, row.bound_spirit_entity_id) if row.bound_spirit_entity_id is not None else None
    if spirit is None or spirit.state is AfterlifeState.CONSUMED:
        spirit = await ctx.session.scalar(
            select(SpiritProfileRow)
            .where(SpiritProfileRow.binding == BindingKind.ITEM, SpiritProfileRow.bound_entity_id == item.id)
            .order_by(SpiritProfileRow.spirit_entity_id)
            .limit(1)
        )
        if spirit is None:
            return None
        if "bound_spirit_entity_id" not in row.locked:
            row.bound_spirit_entity_id = spirit.spirit_entity_id
    holder, _ = await bearer_of(ctx, owner)
    if holder is None or spirit.alignment is not SpiritAlignment.VENGEFUL or holder.entity_type is not EntityType.MORTAL:
        return "guarding" if holder is not None else None
    harm = Harm(
        damage=ctx.rules.item_powers.spirit_curse, cause=HarmCause.CURSE, death_cause=f"haunted to death by the spirit in {item.name}", source_node_id=item.id
    )
    await apply_hits(ctx, holder, harm, lethal=False)
    return "haunting"


async def tools_of(ctx: TickContext, community_id: int | None) -> bool:
    if community_id is None:
        return False
    mortals = select(EntityRow.id).where(await present_among(ctx.session, [community_id]), EntityRow.entity_type == EntityType.MORTAL)
    owners = select(BondRow.target_node_id).where(
        (BondRow.source_node_id == community_id) | BondRow.source_node_id.in_(mortals), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE
    )
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.item_entity_id.in_(owners), ItemProfileRow.item_class == C.TOOL, ItemProfileRow.condition >= ctx.rules.item_wear.broken)
        .limit(1)
    )
    return found is not None


@dataclass(frozen=True)
class Holding:
    item: EntityRow
    row: ItemProfileRow
    holder: EntityRow
    home: EntityRow | None


async def music(ctx: TickContext, held: Holding) -> str | None:
    culture = await ctx.session.get(PeopleCultureRow, held.home.id) if held.home is not None else None
    if culture is None:
        return None
    culture.cohesion = clamp_int(culture.cohesion + ctx.rules.item_powers.instrument_cohesion, 0, PERCENT)
    return "music"


async def seeing(ctx: TickContext, held: Holding) -> str | None:
    foe = await nearest_foe(ctx, held.home.id) if held.home is not None else None
    if foe is None or held.home is None:
        return None
    await gain_intel(ctx, held.home.id, foe, ctx.rules.item_powers.mirror_intel)
    return "seen"


async def libation(ctx: TickContext, held: Holding) -> str | None:
    patron = await patron_node(ctx.session, held.home.id) if held.home is not None else None
    son = await ctx.session.get(SonRow, patron) if patron is not None else None
    if son is None:
        return None
    son.faith += ctx.rules.item_powers.vessel_faith
    return "libation"


async def gates(ctx: TickContext, held: Holding) -> str | None:
    home = held.home
    if home is None or home.entity_type is not EntityType.SETTLEMENT or stat(home, "defense") is None:
        return None
    shift_stat(home, "defense", ctx.rules.item_powers.key_defense)
    return "gates"


async def coin(ctx: TickContext, held: Holding) -> str | None:
    if held.home is None or stat(held.home, "prosperity") is None:
        return None
    shift_stat(held.home, "prosperity", ctx.rules.item_powers.currency_prosperity)
    return "coin"


async def worship(ctx: TickContext, held: Holding) -> str | None:
    if held.holder.entity_type is not EntityType.CULT:
        return None
    shift_stat(held.holder, "zeal", ctx.rules.item_powers.idol_zeal)
    return "worship"


async def prestige(ctx: TickContext, held: Holding) -> str | None:
    if held.holder.entity_type is not EntityType.MORTAL:
        return None
    house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == held.holder.id).limit(1))
    house = await ctx.session.get(HouseProfileRow, house_id) if house_id is not None else None
    if house is None:
        return None
    house.prestige = clamp_int(house.prestige + held.row.value // TEN * ctx.rules.item_powers.jewel_prestige // TEN, 0, PERCENT)
    return "prestige"


async def limb(ctx: TickContext, held: Holding) -> str | None:
    if held.holder.entity_type is not EntityType.MORTAL:
        return None
    fitted = await ctx.session.scalar(select(ProsthesisRow).where(ProsthesisRow.bearer_node_id == held.holder.id).order_by(ProsthesisRow.id).limit(1))
    if fitted is None:
        return None
    if "prosthesis_for" not in held.row.locked:
        held.row.prosthesis_for = fitted.part
    fitted.quality = clamp_int(max(fitted.quality, held.row.quality + ctx.rules.item_powers.prosthesis_quality), 0, PERCENT)
    return "limb"


async def enshrine(ctx: TickContext, held: Holding) -> str | None:
    if held.holder.entity_type is not EntityType.CULT or await ctx.session.get(RelicRow, held.item.id) is not None:
        return None
    ctx.session.add(
        RelicRow(
            item_entity_id=held.item.id,
            cult_entity_id=held.holder.id,
            shrine_entity_id=held.holder.location_id,
            sanctity=max(held.row.renown, PERCENT // HALF),
            pilgrims=0,
            canonised_epoch=ctx.epoch,
        )
    )
    return "enshrined"


async def dose(ctx: TickContext, held: Holding) -> str | None:
    if held.holder.entity_type is not EntityType.MORTAL:
        return None
    table = ctx.rules.item_powers
    await add_stress(ctx.session, held.holder.id, -table.drug_relief, ctx.epoch)
    if ctx.rng(f"dose.{held.item.id}.{ctx.epoch}").chance(table.drug_dependence_pct):
        await afflict(ctx, held.holder, PackageKind.DRUG_DEPENDENCE, Transmission.INGESTION, source_node_id=held.item.id)
        return "dependence"
    return "dose"


async def device(ctx: TickContext, held: Holding) -> str | None:
    if held.home is None or stat(held.home, "prosperity") is None:
        return None
    shift_stat(held.home, "prosperity", ctx.rules.item_powers.device_prosperity)
    return "device"


async def signal(ctx: TickContext, held: Holding) -> str | None:
    town = await ctx.session.get(SettlementProfileRow, held.home.id) if held.home is not None else None
    if town is None or "public_order" in town.locked:
        return None
    town.public_order = clamp_int(town.public_order + ctx.rules.item_powers.communicator_order, 0, PERCENT)
    return "signal"


async def spare(ctx: TickContext, held: Holding) -> str | None:
    vessel = await ctx.session.scalar(
        select(VesselProfileRow).where(VesselProfileRow.captain_entity_id == held.holder.id).order_by(VesselProfileRow.entity_id).limit(1)
    )
    if vessel is None or "condition" in vessel.locked:
        return None
    vessel.condition = clamp_int(vessel.condition + ctx.rules.item_powers.part_repair, 0, PERCENT)
    return "repaired"


POWERS: dict[ItemClass, Callable[[TickContext, Holding], Awaitable[str | None]]] = {
    C.INSTRUMENT: music,
    C.MIRROR: seeing,
    C.VESSEL_OBJECT: libation,
    C.KEY: gates,
    C.CURRENCY: coin,
    C.IDOL: worship,
    C.JEWEL: prestige,
    C.CROWN: prestige,
    C.RING: prestige,
    C.PROSTHESIS: limb,
    C.HOLY_RELIC: enshrine,
    C.IMPLANT: limb,
    C.DRUG: dose,
    C.DEVICE: device,
    C.COMMUNICATOR: signal,
    C.VEHICLE_PART: spare,
}


async def class_powers(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> str | None:
    power = POWERS.get(row.item_class)
    if power is None or row.condition < ctx.rules.item_wear.broken:
        return None
    holder, home = await bearer_of(ctx, owner)
    if holder is None:
        return None
    return await power(ctx, Holding(item, row, holder, home))


async def broke(ctx: TickContext, item: EntityRow, owner: int | None) -> None:
    deed = record(ctx, item.id, ItemDeed.BROKEN, owner, "broken in use")
    legendary = item.id in await flags_by_entity(ctx.session, EntityFlag.LEGENDARY)
    if legendary:
        await open_story(ctx.session, f"{item.name} lies broken and waits to be made whole.", [item.id, *([owner] if owner else [])], ctx.epoch)
    told = await record_incident(
        ctx, "item.reforge_quest" if legendary else "item.broken", roles={IncidentRole.SUBJECT: item.id, IncidentRole.OWNER: owner}, place=item.location_id
    )
    deed.incident_id = told.incident_id


async def humiliated(ctx: TickContext, item: EntityRow, row: ItemProfileRow, captor: int) -> None:
    realm = row.regalia_of_entity_id
    if realm is None:
        return
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=realm,
        subject_id=captor,
        kind=MemoryKind.HUMILIATED_ME,
        magnitude=-ctx.rules.regalia.humiliation,
        epoch=ctx.epoch,
        note=f"took {item.name}",
    )
    await record_incident(
        ctx,
        "item.regalia_seized",
        roles={IncidentRole.SUBJECT: item.id, IncidentRole.VICTIM: realm, IncidentRole.ACTOR: captor},
        facts={"shame": ctx.rules.regalia.humiliation},
        place=item.location_id,
    )


async def item_year(ctx: TickContext, atlas: RegionAtlas, item: EntityRow, book: MaterialBook | None = None) -> dict[str, int]:
    book = book or await MaterialBook.load(ctx.session)
    row = await profile_of(ctx, item)
    await apply_custom_class(ctx, row)
    owner = await owner_of(ctx, item.id)
    counts: dict[str, int] = {}
    region = atlas.top_region(owner) if owner is not None else atlas.top_region(item.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    fought = await fought_this_epoch(ctx, owner)
    if "condition" not in row.locked and await wear(ctx, book, item, row, land=land, fought=fought):
        await broke(ctx, item, owner)
        counts["broken"] = 1
    counts["repaired"] = int(await repair(ctx, book, item, row, owner))
    if row.curse is CurseKind.NONE and (stat(item, "curse") or 0) >= ctx.rules.item_curses.threshold and "curse" not in row.locked:
        row.curse = curse_for(row.item_class)
        counts["cursed"] = 1
    if fought and row.item_class in WEAPONS | GUARDS | {C.STANDARD}:
        record(ctx, item.id, ItemDeed.BATTLE, owner, "carried into battle")
        if "renown" not in row.locked:
            row.renown = clamp_int(row.renown + ctx.rules.item_renown.battle, 0, PERCENT)
    counts["kills"] = await deeds(ctx, item, row, owner)
    if await regalia(ctx, item, row):
        counts["regalia"] = 1
    taker = await captured(ctx, item, row, owner)
    if taker is not None:
        await humiliated(ctx, item, row, taker)
        counts["captured"] = 1
        owner = taker
    elif await usurped(ctx, item, row, owner) is not None:
        counts["usurped"] = 1
        owner = await owner_of(ctx, item.id)
    if not fought and "renown" not in row.locked:
        row.renown = clamp_int(row.renown - ctx.rules.item_renown.decay, 0, PERCENT)
    row.symbol = row.renown >= ctx.rules.item_renown.symbol
    spells = await bounded_enchantments(ctx, book, item, row)
    counts["enchanted"] = await enchant_year(ctx, atlas, item, spells, owner)
    spirit = await spirit_year(ctx, item, row, owner)
    if spirit:
        counts[f"spirit_{spirit}"] = 1
    power = await class_powers(ctx, item, row, owner)
    if power:
        counts[f"power_{power}"] = 1
    if "value" not in row.locked:
        props = await body_props(ctx, book, item, row)
        row.value = round_half_up(worth(ctx, row, props, sum(spell.strength for spell in spells)) * worth_factor(ctx.rules, props))
    row.updated_epoch = ctx.epoch
    return counts


async def regalia_holder(ctx: TickContext, polity_id: int, ruler_id: int) -> tuple[bool, bool]:
    rows = list(await ctx.session.scalars(select(ItemProfileRow).where(ItemProfileRow.regalia_of_entity_id == polity_id)))
    if not rows:
        return False, False
    held = False
    lost = False
    for row in rows:
        owner = await owner_of(ctx, row.item_entity_id)
        if owner == ruler_id:
            held = True
        elif owner is not None:
            lost = True
    return held, lost


async def standard_item(ctx: TickContext, owner_ids: list[int]) -> int | None:
    if not owner_ids:
        return None
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id.in_(owner_ids), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .where(
            ItemProfileRow.item_entity_id.in_(owned),
            ItemProfileRow.item_class == ItemClass.STANDARD,
            ItemProfileRow.symbol.is_(True),
            ItemProfileRow.condition >= ctx.rules.item_wear.broken,
        )
        .order_by(ItemProfileRow.item_entity_id)
        .limit(1)
    )


async def standard_of(ctx: TickContext, owner_ids: list[int]) -> int:
    return ctx.rules.item_renown.standard_morale if await standard_item(ctx, owner_ids) is not None else 0


def is_book(row: ItemProfileRow) -> bool:
    return row.item_class in KNOWLEDGE_ITEMS


async def wayfinder(session: AsyncSession, owner_id: int | None) -> bool:
    if owner_id is None:
        return False
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await session.scalar(
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_class.in_(list(WAYFINDERS))).limit(1)
    )
    return found is not None


async def relic_year(ctx: TickContext, atlas: RegionAtlas) -> dict[str, int]:
    table = ctx.rules.relics
    counts = {"healed": 0, "stolen": 0, "stirred": 0}
    cults = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON)))
    for relic in list(await ctx.session.scalars(select(RelicRow).order_by(RelicRow.item_entity_id))):
        cult = await ctx.session.get(EntityRow, relic.cult_entity_id) if relic.cult_entity_id is not None else None
        if cult is None or cult.status is not EntityStatus.CANON:
            continue
        shift_stat(cult, "zeal", table.zeal * relic.sanctity // PERCENT)
        counts["stirred"] += 1
        pilgrims_here = select(EntityRow.id).where(EntityRow.location_id == relic.shrine_entity_id, EntityRow.status == EntityStatus.CANON)
        sick = await ctx.session.scalars(
            select(ConditionRow)
            .where(ConditionRow.ended_epoch.is_(None), ConditionRow.kind.in_(list(CURABLE)), ConditionRow.bearer_node_id.in_(pilgrims_here))
            .order_by(ConditionRow.id)
            .limit(relic.pilgrims // table.pilgrims_per_cure + 1)
        )
        patron = await patron_node(ctx.session, cult.id)
        son = await ctx.session.get(SonRow, patron) if patron is not None else None
        for condition in list(sick):
            bearer = await ctx.session.get(EntityRow, condition.bearer_node_id)
            if bearer is None or frozen(bearer.id):
                continue
            potency = await ctx.hook_factor(cult.id, DomainHook.RELIC_POWER)
            if ctx.rng(f"relic_heal.{relic.item_entity_id}.{condition.id}.{ctx.epoch}").chance(table.healing_chance * potency):
                await end_condition(ctx, bearer, condition.kind)
                counts["healed"] += 1
                if son is not None:
                    son.faith += ctx.rules.item_powers.relic_faith
        region = atlas.top_region(relic.shrine_entity_id) if relic.shrine_entity_id is not None else None
        rivals = [other for other in cults if other.id != cult.id and region is not None and atlas.top_region(other.id) == region]
        if rivals and "cult_entity_id" not in relic.locked and ctx.rng(f"relic_theft.{relic.item_entity_id}.{ctx.epoch}").chance(table.theft_chance):
            thief = rivals[0]
            relic.cult_entity_id = thief.id
            record(ctx, relic.item_entity_id, ItemDeed.THEFT, thief.id, f"stolen by {thief.name} from {cult.name}")
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=cult.id,
                subject_id=thief.id,
                kind=MemoryKind.DESECRATED_HOLY,
                magnitude=-table.zeal * 5,
                epoch=ctx.epoch,
                note="relic theft",
            )
            counts["stolen"] += 1
    return counts


async def smith_of(ctx: TickContext, community_id: int | None) -> tuple[EntityRow, int] | None:
    if community_id is None:
        return None
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, [community_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    found = (
        await ctx.session.execute(
            select(SkillRow.holder_node_id, SkillRow.level)
            .where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill == SkillKind.SMITHING)
            .order_by(SkillRow.level.desc(), SkillRow.holder_node_id)
            .limit(1)
        )
    ).first()
    smith = await ctx.session.get(EntityRow, found[0]) if found is not None else None
    return (smith, int(found[1])) if smith is not None and found is not None else None


async def metallurgy(ctx: TickContext, community_id: int | None) -> int:
    if community_id is None:
        return 0
    row = await ctx.session.get(HolderLevelRow, (community_id, KnowledgeBranch.METALLURGY))
    return row.level if row is not None else 0


def masterwork_steps(smith_id: int | None, item_id: int, skill: int, quality: int) -> tuple[StepDraft, ...]:
    shaped = StepDraft(StepAction.WORK, actor=smith_id, target=item_id, amount=skill, unit=FactUnit.STRENGTH)
    finished = StepDraft(
        StepAction.FINISH_WORK,
        actor=smith_id,
        target=item_id,
        amount=quality,
        unit=FactUnit.PERCENT,
        outcome=StepOutcome.SUCCESS,
        record_table=ItemProfileRow.__tablename__,
        record_key=str(item_id),
    )
    if smith_id is None:
        return (shaped, finished)
    return (
        shaped,
        finished,
        StepDraft(StepAction.SIGN_WORK, actor=smith_id, target=item_id, record_table=ItemProfileRow.__tablename__, record_key=str(item_id)),
    )


async def craft(ctx: TickContext, item: EntityRow, community_id: int | None, material_quality: int, item_class: ItemClass | None = None) -> bool:
    table = ctx.rules.crafting
    powers = ctx.rules.item_powers
    row = await profile_of(ctx, item, item_class)
    found = await smith_of(ctx, community_id)
    hands = await ctx.session.get(BodyRow, found[0].id) if found is not None else None
    skill = found[1] * (hands.craft if hands is not None else PERCENT) / PERCENT if found is not None else 0
    skill *= mood_factor(await mood_of(ctx.session, found[0].id), ctx.rules.thoughts.mood_labour_pct) if found is not None else 1
    book = await MaterialBook.load(ctx.session)
    props = await body_props(ctx, book, item, row)
    workability = (props.toughness if props is not None else PERCENT // HALF) / PERCENT
    rest = max(0, PERCENT - table.skill_pct - table.material_pct) / PERCENT
    tools = powers.tool_quality if await tools_of(ctx, community_id) else 0
    knowledge = await metallurgy(ctx, community_id) * powers.knowledge_quality
    if "quality" not in row.locked:
        row.quality = clamp_int(
            round_half_up(
                skill * table.skill_pct / PERCENT
                + material_quality * (HALF * workability) * table.material_pct / PERCENT
                + PERCENT // HALF * rest
                + tools
                + knowledge
            ),
            0,
            PERCENT,
        )
    if found is not None:
        row.maker_entity_id = found[0].id
    if row.quality < table.masterwork:
        return False
    row.renown = clamp_int(row.renown + table.masterwork_renown, 0, PERCENT)
    if found is not None:
        found[0].importance = (found[0].importance or 0) + table.masterwork_renown
        await think(ctx.session, ctx.rules, found[0].id, ThoughtKind.MADE_MASTERWORK, ctx.epoch, subject_id=item.id)
    deed = record(ctx, item.id, ItemDeed.MADE, found[0].id if found is not None else community_id, "a masterwork")
    told = await record_incident(
        ctx,
        "item.masterwork",
        roles={IncidentRole.PRODUCT: item.id, IncidentRole.MAKER: found[0].id if found is not None else community_id},
        facts={"quality": row.quality, "renown_gain": table.masterwork_renown},
        terms=(
            Term("crafting.skill", skill * table.skill_pct / PERCENT, source_node_id=found[0].id if found is not None else None),
            Term("crafting.material", material_quality * (HALF * workability) * table.material_pct / PERCENT),
            Term("crafting.rest", PERCENT // HALF * rest),
            Term("item_powers.tool_quality", tools, source_node_id=community_id),
            Term("item_powers.knowledge_quality", knowledge, source_node_id=community_id),
        ),
        place=community_id,
        steps=masterwork_steps(found[0].id if found is not None else None, item.id, round_half_up(skill), row.quality),
    )
    deed.incident_id = told.incident_id
    return True


def stock_of(props: MaterialProps | None) -> CommodityKind:
    if props is None:
        return CommodityKind.ORE
    if props.kind in ORGANIC_CLOTH:
        return CommodityKind.CLOTH
    return FAMILY_STOCK.get(props.family, CommodityKind.ORE)


async def repair(ctx: TickContext, book: MaterialBook, item: EntityRow, row: ItemProfileRow, owner: int | None) -> bool:
    if row.condition >= PERCENT or "condition" in row.locked:
        return False
    holder = await ctx.session.get(EntityRow, owner) if owner is not None else None
    home = holder.location_id if holder is not None and holder.entity_type is EntityType.MORTAL else owner
    if home is None or await smith_of(ctx, home) is None:
        return False
    props = await body_props(ctx, book, item, row)
    units = ctx.rules.item_powers.repair_units
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    commodity = stock_of(props)
    taken = await ledger.take_units(home, commodity, units, GoodsFlow.CONSUMPTION) if units else 0
    if taken < units:
        return False
    was_broken = row.condition < ctx.rules.item_wear.broken
    row.condition = clamp_int(row.condition + ctx.rules.item_wear.repair_gain, 0, PERCENT)
    deed = record(ctx, item.id, ItemDeed.REPAIRED, owner, f"mended by a metalworker with {taken} {spoken(commodity)}")
    if was_broken and row.condition >= ctx.rules.item_wear.broken:
        told = await record_incident(
            ctx,
            "item.reforged",
            roles={IncidentRole.SUBJECT: item.id, IncidentRole.OWNER: owner},
            facts={"commodity": commodity, "units": taken, "condition": row.condition},
            place=home,
        )
        deed.incident_id = told.incident_id
    return True
