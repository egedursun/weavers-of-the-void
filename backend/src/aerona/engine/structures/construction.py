from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.structures import STRUCTURE_ENGINE_KINDS
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import ConstructionRow, StructureDesignRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialFamily
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.domain.enums.structure import BuildScale, ConstructionState, ConstructionStatus, StructureKind
from aerona.domain.models.entity_stats import LegendStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import sanctity_splendour
from aerona.engine.economy.stocks import goods_of
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, connect
from aerona.engine.primitives.records import RecordSpec, indefinite, open_record
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.engine.structures.profiles import aesthetic_for, durability_from, ensure_profile, fire_resistance_from, host_for, material_props, refresh
from aerona.engine.structures.spec import build_cost, resolve, scale_index
from aerona.engine.structures.workshops import link_workshop
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

STONE_FAMILIES = frozenset({MaterialFamily.STONE, MaterialFamily.METAL})
LEGEND_POWER = 3


@dataclass(frozen=True)
class Commission:
    site: EntityRow
    kind: StructureKind
    level: int = 1
    design: StructureDesignRow | None = None
    builder: EntityRow | SonRow | None = None
    architect_id: int | None = None
    son_id: int | None = None
    material: MaterialKind | None = None
    world_material_id: int | None = None
    name: str | None = None
    player: bool = False
    funds: int = 0


def power_of(rules: Rules, builder: EntityRow | SonRow) -> int:
    life = rules.deep_life
    base = builder.power_level if isinstance(builder, EntityRow) else life.structure_max_power
    return clamp_int(round_half_up(base * life.structure_power_share_pct / PERCENT) + 1, life.derived_min_power, life.structure_max_power)


async def charge_builder(ctx: TickContext, builder: EntityRow | SonRow) -> None:
    if not isinstance(builder, EntityRow) or builder.entity_type not in COMMUNITY_TYPES:
        return
    life = ctx.rules.deep_life
    if stat(builder, "prosperity") is not None:
        shift_stat(builder, "prosperity", -life.structure_prosperity_cost)
    await shift_stock(ctx.session, ctx.rules, builder.id, Commodity.GOODS, -life.structure_goods_cost, epoch=ctx.epoch, flow=GoodsFlow.CONSTRUCTION)


def completion_gift(rules: Rules, kind: StructureKind, host: EntityRow | None) -> None:
    if host is None:
        return
    if kind is StructureKind.TEMPLE and stat(host, "piety") is not None:
        shift_stat(host, "piety", rules.deep_life.temple_piety_gain)
    if kind is StructureKind.WALL and host.entity_type is EntityType.SETTLEMENT:
        shift_stat(host, "defense", rules.deep_life.wall_defense_gain, rules.deep_life.wall_default_defense)


async def default_material(ctx: TickContext, site: EntityRow, knowledge: KnowledgeMap | None = None) -> MaterialKind:
    knowledge = knowledge or await KnowledgeMap.load(ctx.session)
    return MaterialKind.STONE if knowledge.level(site.id, KnowledgeBranch.ARCHITECTURE) >= ctx.rules.construction.stone_architecture else MaterialKind.WOOD


async def best_architect(ctx: TickContext, site: EntityRow) -> EntityRow | None:
    row = await ctx.session.execute(
        select(EntityRow, SkillRow.level)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == site.id,
            SkillRow.skill == SkillKind.ENGINEERING,
            SkillRow.subject_node_id.is_(None),
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
        .limit(1)
    )
    found = row.first()
    return found[0] if found is not None else None


async def begin(ctx: TickContext, order: Commission) -> tuple[EntityRow, ConstructionRow]:
    resolved = resolve(order.kind, order.design)
    rules = ctx.rules
    builder = order.builder or order.site
    rng = ctx.rng(seed_of("construction", order.site.id, order.kind.value, ctx.epoch))
    if order.name:
        name = order.name
    else:
        speaker = builder.id if isinstance(builder, EntityRow) else order.site.id
        place = await Namer(ctx.session, rules).from_speaker(speaker, seed_of(order.site.id, ctx.epoch, order.kind.value), NameKind.PLACE)
        name = f"{place or order.site.name} {resolved.label}"
    work = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.STRUCTURE,
            name=name,
            body=f"{order.site.name} began to raise {indefinite(resolved.label.lower())}.",
            stats=StructureStats(
                splendor=0, function=clamp_int(rules.deep_life.structure_function_base + rng.die(rules.deep_life.structure_function_die), 0, PERCENT)
            ),
            power=power_of(rules, builder),
            location_id=order.site.id,
            world_id=order.site.world_id,
            subtype=resolved.label.lower(),
            engine_kind=STRUCTURE_ENGINE_KINDS.get(order.kind),
            creator_son_id=builder.id if isinstance(builder, SonRow) else None,
            maker_entity_id=builder.id if isinstance(builder, EntityRow) else None,
            pending=not order.player,
        ),
    )
    architect = await ctx.session.get(EntityRow, order.architect_id) if order.architect_id is not None else await best_architect(ctx, order.site)
    material = order.material if order.material is not None or order.world_material_id is not None else await default_material(ctx, order.site)
    profile = await ensure_profile(
        ctx.session,
        rules,
        ctx.epoch,
        work,
        order.kind,
        state=ConstructionState.BUILDING,
        level=order.level,
        design_id=order.design.id if order.design is not None else None,
        builder=builder,
        architect_id=architect.id if architect is not None else None,
        son_id=order.son_id,
        material=material,
        world_material_id=order.world_material_id,
    )
    profile.progress = 0
    construction = ConstructionRow(
        structure_entity_id=work.id,
        site_entity_id=order.site.id,
        builder_entity_id=builder.id,
        kind=order.kind,
        design_id=order.design.id if order.design is not None else None,
        status=ConstructionStatus.ACTIVE,
        cost=build_cost(rules, resolved, order.level),
        progress=0,
        funds=max(0, order.funds),
        workers=0,
        materials_pct=0,
        stalled_epochs=0,
        generations=0,
        player=order.player,
        started_epoch=ctx.epoch,
        finished_epoch=None,
        locked=[],
    )
    ctx.session.add(construction)
    await charge_builder(ctx, builder)
    if isinstance(builder, EntityRow):
        await connect(ctx.session, builder.id, work.id, BondKind.BUILT, ctx.epoch)
    if order.son_id is not None:
        await connect(ctx.session, work.id, order.son_id, BondKind.WORSHIPS, ctx.epoch, description="dedicated to")
    await ctx.session.flush()
    await note(
        ctx,
        f"{order.site.name} began to raise {work.name}, {indefinite(resolved.label.lower())}.",
        key="structures.begun",
        ids=[order.site.id, work.id],
        kind=ChronicleKind.CONSTRUCTION,
    )
    ctx.count("constructions_begun")
    return work, construction


async def builders_at(ctx: TickContext, site_id: int, active: int) -> int:
    table = ctx.rules.construction
    hands = await ctx.session.scalar(
        select(func.coalesce(func.sum(LabourRow.workers), 0)).where(LabourRow.community_entity_id == site_id, LabourRow.job == Job.BUILDING)
    )
    share = round_half_up(int(hands or 0) * table.worker_share_pct / PERCENT / max(1, active))
    return max(table.builder_floor, share)


def material_commodity(family: MaterialFamily | None) -> CommodityKind:
    return CommodityKind.TIMBER if family is MaterialFamily.ORGANIC else CommodityKind.STONE


async def spend_treasury(ctx: TickContext, site_id: int, amount: int, label: str) -> int:
    town = await ctx.session.get(SettlementProfileRow, site_id)
    if town is None or amount <= 0 or held(site_id):
        return 0
    paid = min(amount, max(0, town.treasury))
    if paid:
        town.treasury -= paid
        ctx.session.add(
            SettlementTreasuryRow(
                settlement_entity_id=site_id, epoch=ctx.epoch, entry=TreasuryEntry.BUILDING, amount=-paid, balance=town.treasury, note=label[:120]
            )
        )
    return paid


async def pay(ctx: TickContext, construction: ConstructionRow, amount: int, label: str) -> int:
    from_funds = min(construction.funds, amount)
    construction.funds -= from_funds
    rest = await spend_treasury(ctx, construction.site_entity_id, amount - from_funds, label) if construction.site_entity_id is not None else 0
    return from_funds + rest


async def engineering(ctx: TickContext, site_id: int, profile: StructureProfileRow, knowledge: KnowledgeMap) -> float:
    table = ctx.rules.construction
    architect = 0
    if profile.architect_entity_id is not None:
        row = await ctx.session.scalar(
            select(SkillRow.level).where(
                SkillRow.holder_node_id == profile.architect_entity_id, SkillRow.skill == SkillKind.ENGINEERING, SkillRow.subject_node_id.is_(None)
            )
        )
        architect = int(row or 0)
    level = knowledge.level(site_id, KnowledgeBranch.ARCHITECTURE)
    return 1 + level * table.engineering_pct_per_level / PERCENT + architect * table.architect_pct_per_level / PERCENT


async def advance(ctx: TickContext, construction: ConstructionRow, *, active: int, knowledge: KnowledgeMap) -> int:
    table = ctx.rules.construction
    work = await ctx.session.get(EntityRow, construction.structure_entity_id)
    profile = await ctx.session.get(StructureProfileRow, construction.structure_entity_id)
    site = await ctx.session.get(EntityRow, construction.site_entity_id) if construction.site_entity_id is not None else None
    if work is None or profile is None:
        return 0
    if site is None or site.status is not EntityStatus.CANON:
        await abandon(ctx, construction, "its builders are gone")
        return 0
    if "progress" in construction.locked:
        return 0
    workers = await builders_at(ctx, site.id, active)
    wanted = round_half_up(workers * table.worker_output * await engineering(ctx, site.id, profile, knowledge))
    props = await material_props(ctx.session, work)
    commodity = material_commodity(props.family if props is not None else None)
    needed = round_half_up(wanted * table.materials_per_100_work / PERCENT)
    delivered = await goods_of(ctx.session, ctx.epoch).take_units(site.id, commodity, needed, GoodsFlow.CONSTRUCTION) if needed else 0
    short = needed - delivered
    if short > 0 and table.funds_buy_materials > 0:
        bought = await pay(ctx, construction, short * table.funds_buy_materials, f"materials for {work.name}") // table.funds_buy_materials
        delivered += bought
    coin = round_half_up(wanted * table.funds_per_100_work / PERCENT)
    paid = await pay(ctx, construction, coin, f"wages for {work.name}") if coin else 0
    supplied = min(delivered / needed if needed else 1.0, paid / coin if coin else 1.0)
    added = round_half_up(wanted * supplied)
    construction.workers = workers
    construction.materials_pct = clamp_int(supplied * PERCENT, 0, PERCENT)
    if added <= 0:
        construction.stalled_epochs += 1
        limit = table.wonder_stall_epochs if resolve(construction.kind).scale is BuildScale.WONDER else table.stall_epochs
        if construction.stalled_epochs >= limit and "status" not in construction.locked:
            await abandon(ctx, construction, "the work stood still for too long")
        return 0
    construction.stalled_epochs = 0
    construction.progress = min(construction.cost, construction.progress + added)
    profile.progress = clamp_int(construction.progress * PERCENT / construction.cost, 0, PERCENT)
    generations = (ctx.epoch - construction.started_epoch) // max(1, table.generation_epochs)
    if generations > construction.generations:
        construction.generations = generations
        await note(
            ctx,
            f"Another generation of {site.name} carries stones to {work.name}; it is {profile.progress}% raised.",
            key="structures.generation",
            ids=[site.id, work.id],
            kind=ChronicleKind.CONSTRUCTION,
        )
    if construction.progress >= construction.cost:
        await finish(ctx, construction)
    return added


async def splendor_for(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, site: EntityRow | None, knowledge: KnowledgeMap) -> int:
    table = ctx.rules.construction
    rng = ctx.rng(seed_of("splendor", work.id))
    props = await material_props(ctx.session, work)
    value = props.base_value * table.splendor_value_pct / PERCENT + sanctity_splendour(ctx.rules, props) if props is not None else 0
    architect = 0
    if profile.architect_entity_id is not None:
        level = await ctx.session.scalar(
            select(SkillRow.level).where(
                SkillRow.holder_node_id == profile.architect_entity_id, SkillRow.skill == SkillKind.ENGINEERING, SkillRow.subject_node_id.is_(None)
            )
        )
        architect = int(level or 0) * table.splendor_architect_per_level
    builder = profile.builder_entity_id if profile.builder_entity_id is not None else site.id if site is not None else None
    craft = knowledge.effect(ctx.rules, builder, KnowledgeBranch.ARCHITECTURE) * ctx.rules.deep_life.structure_architecture_bonus if builder is not None else 0
    local = await aesthetic_for(ctx.session, await host_for(ctx.session, work))
    fit = 0 if profile.aesthetic is None or local is None else table.aesthetic_fit if profile.aesthetic is local else -table.aesthetic_clash
    return clamp_int(
        ctx.rules.deep_life.structure_splendor_base + rng.die(ctx.rules.deep_life.structure_splendor_die) + value + architect + craft + fit, 0, PERCENT
    )


async def finish(ctx: TickContext, construction: ConstructionRow, *, by_hand: bool = False) -> EntityRow | None:
    work = await ctx.session.get(EntityRow, construction.structure_entity_id)
    profile = await ctx.session.get(StructureProfileRow, construction.structure_entity_id)
    if work is None or profile is None:
        return None
    site = await ctx.session.get(EntityRow, construction.site_entity_id) if construction.site_entity_id is not None else None
    knowledge = await KnowledgeMap.load(ctx.session)
    props = await material_props(ctx.session, work)
    construction.progress = construction.cost
    construction.status = ConstructionStatus.FINISHED
    construction.finished_epoch = ctx.epoch
    durability = clamp_int(
        durability_from(ctx.rules, props) + ctx.rng(seed_of("durability", work.id)).die(ctx.rules.deep_life.structure_durability_die), 1, PERCENT
    )
    set_stats(work, durability=durability, splendor=await splendor_for(ctx, work, profile, site, knowledge))
    if "construction_state" not in profile.locked:
        profile.construction_state = ConstructionState.COMPLETE
    profile.progress = PERCENT
    if "condition" not in profile.locked:
        profile.condition = durability
    if "fire_resistance" not in profile.locked:
        profile.fire_resistance = fire_resistance_from(ctx.rules, props)
    profile.built_epoch = ctx.epoch
    resolved = await refresh(ctx.session, ctx.rules, work, profile)
    completion_gift(ctx.rules, construction.kind, site)
    if resolved.workshop is not None and profile.host_entity_id is not None:
        await link_workshop(ctx, profile.host_entity_id, resolved.workshop, work.id)
    hand = " at the Creator's word" if by_hand else ""
    await note(
        ctx,
        f"{work.name} stands finished{hand}: {indefinite(resolved.label.lower())} for {site.name if site else 'its builders'}.",
        key="structures.finished",
        ids=[*([site.id] if site else []), work.id],
        kind=ChronicleKind.CONSTRUCTION,
    )
    ctx.count("constructions_finished")
    return work


async def abandon(ctx: TickContext, construction: ConstructionRow, reason: str) -> None:
    work = await ctx.session.get(EntityRow, construction.structure_entity_id)
    profile = await ctx.session.get(StructureProfileRow, construction.structure_entity_id)
    construction.status = ConstructionStatus.ABANDONED
    construction.finished_epoch = ctx.epoch
    if work is None:
        return
    if profile is not None:
        profile.construction_state = ConstructionState.RUINED
        profile.effect_pct = 0
    await add_flag(ctx.session, work.id, EntityFlag.RUIN, ctx.epoch)
    resolved = resolve(construction.kind)
    percent = clamp_int(construction.progress * PERCENT / max(1, construction.cost), 0, PERCENT)
    legend = None
    if scale_index(resolved.scale) >= ctx.rules.construction.legend_scale:
        legend = await open_record(
            ctx.session,
            ctx.epoch,
            RecordSpec(
                entity_type=EntityType.LEGEND,
                name=f"The Unfinished {resolved.label} of {work.name}",
                body=f"They say {work.name} was left {percent}% raised because {reason}, and that whoever finishes it will be remembered forever.",
                stats=LegendStats(spread=clamp_int(percent // 2 + scale_index(resolved.scale) * 10, 0, PERCENT)),
                power=LEGEND_POWER,
                location_id=work.location_id,
                world_id=work.world_id,
                subtype="legend of a ruin",
            ),
        )
        await connect(ctx.session, legend.id, work.id, BondKind.TELLS_OF, ctx.epoch, description="tells of the unfinished work")
    tail = f"; a legend of {legend.name} spreads" if legend is not None else ""
    await note(
        ctx,
        f"{work.name} was abandoned {percent}% raised: {reason}{tail}.",
        key="structures.abandoned",
        ids=[work.id, *([legend.id] if legend is not None else [])],
        kind=ChronicleKind.CONSTRUCTION,
    )
    ctx.count("constructions_abandoned")


async def active_at(ctx: TickContext, site_id: int) -> list[ConstructionRow]:
    return list(
        await ctx.session.scalars(
            select(ConstructionRow)
            .where(ConstructionRow.site_entity_id == site_id, ConstructionRow.status == ConstructionStatus.ACTIVE)
            .order_by(ConstructionRow.id)
        )
    )


async def construction_of(ctx: TickContext, structure_id: int) -> ConstructionRow:
    row = await ctx.session.scalar(
        select(ConstructionRow)
        .where(ConstructionRow.structure_entity_id == structure_id, ConstructionRow.status == ConstructionStatus.ACTIVE)
        .order_by(ConstructionRow.id.desc())
        .limit(1)
    )
    if row is None:
        raise ValidationFailedError("That structure is not under construction.")
    return row
