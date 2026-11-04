from sqlalchemy import func, select

from aerona.catalog.lore import ITEM_CLASSES, ITEM_WORDS, KNOWLEDGE_ITEMS, REGALIA, WEAPONS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow, ConditionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemHistoryRow, ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind, ItemClass, ItemDeed
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.conditions import end_condition
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import MaterialBook, MaterialProps, battle_wear, node_material, rust_wear, worth_factor
from aerona.engine.lore.arms import GUARDS
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat

HALF = 2
CURABLE = frozenset({ConditionKind.CHRONIC_ILLNESS, ConditionKind.MELANCHOLY, ConditionKind.PARANOIA, ConditionKind.AGE_BLINDNESS, ConditionKind.WITHERED_LIMB})


def class_of(item: EntityRow) -> ItemClass:
    text = f"{item.name} {item.subtype or ''}".lower()
    for item_class, words in ITEM_WORDS.items():
        if any(word in text for word in words):
            return item_class
    if (stat(item, "damage") or 0) > 0:
        return ItemClass.BLADE
    if (stat(item, "protection") or 0) > 0:
        return ItemClass.ARMOUR
    return ItemClass.JEWEL


async def owner_of(ctx: TickContext, item_id: int) -> int | None:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(statement.order_by(BondRow.id.desc()).limit(1))


def record(ctx: TickContext, item_id: int, deed: ItemDeed, actor: int | None, note: str) -> None:
    ctx.session.add(ItemHistoryRow(item_entity_id=item_id, epoch=ctx.epoch, deed=deed, actor_entity_id=actor, note=note[:480]))


C = ItemClass
CURSES = (
    (WEAPONS, CurseKind.BLOODTHIRST),
    (frozenset({C.CROWN, C.SCEPTRE, C.SEAL, C.RING, C.STANDARD, C.KEY}), CurseKind.BETRAYAL),
    (frozenset({C.MIRROR, C.JEWEL, C.IDOL, C.INSTRUMENT, C.ASTROLABE, C.BOOK, C.SCROLL, C.PRAYER_BOOK}), CurseKind.MADNESS),
    (frozenset({C.ARMOUR, C.SHIELD, C.HELMET, C.PROSTHESIS, C.HOLY_RELIC}), CurseKind.WASTING),
)


def curse_for(item_class: ItemClass) -> CurseKind:
    return next((kind for classes, kind in CURSES if item_class in classes), CurseKind.MISFORTUNE)


async def profile_of(ctx: TickContext, item: EntityRow) -> ItemProfileRow:
    row = await ctx.session.get(ItemProfileRow, item.id)
    if row is not None:
        return row
    item_class = class_of(item)
    spec = ITEM_CLASSES[item_class]
    might = stat(item, "might") or 0
    quality = clamp_int(PERCENT // 2 + might // 2 + (stat(item, "damage") or 0) // 4, 0, PERCENT)
    row = ItemProfileRow(
        item_entity_id=item.id,
        item_class=item_class,
        quality=quality,
        condition=PERCENT,
        damage_type=spec.damage_type,
        reach=spec.reach,
        coverage=spec.coverage,
        weight=spec.weight,
        curse=curse_for(item_class) if (stat(item, "curse") or 0) >= ctx.rules.item_curses.threshold else CurseKind.NONE,
        value=quality + might,
        renown=clamp_int(item.power_level * 10, 0, PERCENT),
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


def wear(ctx: TickContext, row: ItemProfileRow, land: RegionEnvironmentRow | None, fought: bool, props: MaterialProps | None = None) -> bool:
    table = ctx.rules.item_wear
    before = row.condition
    if fought and row.item_class in WEAPONS | {ItemClass.ARMOUR, ItemClass.SHIELD, ItemClass.HELMET}:
        row.condition = clamp_int(row.condition - battle_wear(ctx.rules, props), 0, PERCENT)
    if land is not None and props is not None and land.moisture >= ctx.rules.materials.rust_wet_moisture:
        row.condition = clamp_int(row.condition - rust_wear(ctx.rules, props), 0, PERCENT)
    return before >= table.broken > row.condition


async def material_of(ctx: TickContext, item: EntityRow, book: MaterialBook | None = None) -> MaterialProps | None:
    node = await node_material(ctx.session, item.id, MaterialSlot.BODY)
    if node is None:
        return None
    materials = book if book is not None else await MaterialBook.load(ctx.session)
    return materials.props(item.world_id, node.material, node.world_material_id)


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


async def item_year(ctx: TickContext, atlas: RegionAtlas, item: EntityRow, book: MaterialBook | None = None) -> dict[str, int]:
    row = await profile_of(ctx, item)
    owner = await owner_of(ctx, item.id)
    counts: dict[str, int] = {}
    region = atlas.top_region(owner) if owner is not None else atlas.top_region(item.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    fought = await fought_this_epoch(ctx, owner)
    props = await material_of(ctx, item, book)
    if "condition" not in row.locked and wear(ctx, row, land, fought, props):
        record(ctx, item.id, ItemDeed.BROKEN, owner, "broken in use")
        counts["broken"] = 1
    counts["repaired"] = int(await repair(ctx, item, row, owner))
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
    if not fought and "renown" not in row.locked:
        row.renown = clamp_int(row.renown - ctx.rules.item_renown.decay, 0, PERCENT)
    row.symbol = row.renown >= ctx.rules.item_renown.symbol
    if "value" not in row.locked:
        row.value = round_half_up(row.quality * (1 + row.renown / PERCENT) * (row.condition / PERCENT + HALF) / HALF * worth_factor(ctx.rules, props))
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


async def standard_of(ctx: TickContext, owner_ids: list[int]) -> int:
    if not owner_ids:
        return 0
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id.in_(owner_ids), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_class == ItemClass.STANDARD, ItemProfileRow.symbol.is_(True))
        .limit(1)
    )
    return ctx.rules.item_renown.standard_morale if found is not None else 0


def is_book(row: ItemProfileRow) -> bool:
    return row.item_class in KNOWLEDGE_ITEMS


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
        for condition in list(sick):
            bearer = await ctx.session.get(EntityRow, condition.bearer_node_id)
            if bearer is None:
                continue
            if ctx.rng(f"relic_heal.{relic.item_entity_id}.{condition.id}.{ctx.epoch}").chance(table.healing_chance):
                await end_condition(ctx, bearer, condition.kind)
                counts["healed"] += 1
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
        EntityRow.location_id == community_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
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


async def craft(ctx: TickContext, item: EntityRow, community_id: int | None, material_quality: int) -> bool:
    table = ctx.rules.crafting
    row = await profile_of(ctx, item)
    found = await smith_of(ctx, community_id)
    hands = await ctx.session.get(BodyRow, found[0].id) if found is not None else None
    skill = found[1] * (hands.craft if hands is not None else PERCENT) / PERCENT if found is not None else 0
    rest = max(0, PERCENT - table.skill_pct - table.material_pct) / PERCENT
    if "quality" not in row.locked:
        row.quality = clamp_int(
            round_half_up(skill * table.skill_pct / PERCENT + material_quality * table.material_pct / PERCENT + PERCENT // 2 * rest), 0, PERCENT
        )
    if found is not None:
        row.maker_entity_id = found[0].id
    if row.quality < table.masterwork:
        return False
    row.renown = clamp_int(row.renown + table.masterwork_renown, 0, PERCENT)
    if found is not None:
        found[0].importance = (found[0].importance or 0) + table.masterwork_renown
    record(ctx, item.id, ItemDeed.MADE, found[0].id if found is not None else community_id, "a masterwork")
    return True


async def repair(ctx: TickContext, item: EntityRow, row: ItemProfileRow, owner: int | None) -> bool:
    if row.condition >= PERCENT or "condition" in row.locked:
        return False
    holder = await ctx.session.get(EntityRow, owner) if owner is not None else None
    home = holder.location_id if holder is not None and holder.entity_type is EntityType.MORTAL else owner
    if await smith_of(ctx, home) is None:
        return False
    row.condition = clamp_int(row.condition + ctx.rules.item_wear.repair_gain, 0, PERCENT)
    record(ctx, item.id, ItemDeed.REPAIRED, owner, "mended by a smith")
    return True
