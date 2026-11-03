from collections.abc import Callable
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import judged
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import active_bonds, canon, connect, count_communities, living_entity
from aerona.engine.primitives.records import RecordSpec, indefinite, open_record
from aerona.engine.primitives.society import class_shares, set_stock, stock
from aerona.engine.primitives.stats import set_stats, stat
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

BUILDER_TYPES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
OWNER_BOND_KINDS = (BondKind.BUILT, BondKind.OWNS, BondKind.RULES)


@dataclass(frozen=True)
class Site:
    builder: EntityRow
    shares: dict[SocialClass, float]
    knows_architecture: bool
    knows_writing: bool
    at_war: bool
    has_patron: bool
    architecture_effect: float = 0.0


@dataclass(frozen=True)
class WorkKind:
    kind: EngineKind
    subtype: str
    suffix: str
    eligible: Callable[[Rules, Site], bool]
    effect: Callable[[Rules, EntityRow], None]


def prosperity_of(rules: Rules, community: EntityRow) -> int:
    prosperity = stat(community, "prosperity")
    if prosperity is not None:
        return prosperity
    if community.entity_type is EntityType.PEOPLE:
        life = rules.deep_life
        return life.structure_people_prosperity_base + round_half_up((stat(community, "craft") or 0) / life.structure_people_craft_divisor)
    return 0


def _temple_ok(rules: Rules, site: Site) -> bool:
    piety = stat(site.builder, "piety")
    life = rules.deep_life
    return (
        site.has_patron
        and (piety if piety is not None else rules.society.default_stat) >= life.temple_min_piety
        and site.shares[SocialClass.PRIEST] >= life.temple_min_priest_pct
    )


def _walls_ok(rules: Rules, site: Site) -> bool:
    defense = stat(site.builder, "defense")
    life = rules.deep_life
    return site.builder.entity_type is EntityType.SETTLEMENT and (
        (defense if defense is not None else life.wall_default_defense) < life.wall_defense_threshold or site.at_war
    )


def _library_ok(rules: Rules, site: Site) -> bool:
    return site.shares[SocialClass.SCRIBE] >= rules.deep_life.library_min_scribe_pct or site.knows_writing


def _raise_piety(rules: Rules, builder: EntityRow) -> None:
    piety = stat(builder, "piety")
    if piety is not None:
        set_stats(builder, piety=clamp_int(piety + rules.deep_life.temple_piety_gain, 0, PERCENT))


def _raise_walls(rules: Rules, builder: EntityRow) -> None:
    defense = stat(builder, "defense")
    base = defense if defense is not None else rules.deep_life.wall_default_defense
    set_stats(builder, defense=clamp_int(base + rules.deep_life.wall_defense_gain, 0, PERCENT))


def _no_effect(rules: Rules, builder: EntityRow) -> None:
    del rules, builder


WORK_KINDS = (
    WorkKind(EngineKind.TEMPLE, "temple", "Temple", _temple_ok, _raise_piety),
    WorkKind(EngineKind.WALL, "wall", "Walls", _walls_ok, _raise_walls),
    WorkKind(EngineKind.LIBRARY, "library", "Library", _library_ok, _no_effect),
)


async def site_of(ctx: TickContext, builder: EntityRow, knowledge: KnowledgeMap) -> Site:
    at_war = bool(
        await active_bonds(ctx.session, [BondKind.ENEMY], sources=[builder.id]) or await active_bonds(ctx.session, [BondKind.ENEMY], targets=[builder.id])
    )
    return Site(
        builder=builder,
        shares=await class_shares(ctx.session, ctx.rules, builder.id),
        knows_architecture=knowledge.knows(builder.id, KnowledgeBranch.ARCHITECTURE),
        architecture_effect=knowledge.effect(ctx.rules, builder.id, KnowledgeBranch.ARCHITECTURE),
        knows_writing=knowledge.knows(builder.id, KnowledgeBranch.WRITING),
        at_war=at_war,
        has_patron=await living_patron(ctx.session, builder) is not None,
    )


async def existing_kinds(ctx: TickContext, builder: EntityRow, place_id: int | None) -> set[EngineKind]:
    works = list(await EntityRepository(ctx.session).contents(place_id)) if place_id is not None else []
    for bond in await active_bonds(ctx.session, [BondKind.BUILT], sources=[builder.id]):
        work = await living_entity(ctx.session, bond.target_node_id)
        if work is not None:
            works.append(work)
    return {work.engine_kind for work in works if work.entity_type is EntityType.STRUCTURE and work.engine_kind is not None}


async def build(ctx: TickContext, site: Site, kind: WorkKind) -> EntityRow:
    rules = ctx.rules
    life = rules.deep_life
    builder = site.builder
    rng = ctx.rng(seed_of("work", builder.id, kind.kind.value))
    place_id = builder.id if builder.entity_type is EntityType.SETTLEMENT else builder.location_id
    place_name = await Namer(ctx.session, rules).from_speaker(builder.id, seed_of(builder.id, ctx.epoch, kind.kind.value), NameKind.PLACE)
    work = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.STRUCTURE,
            name=f"{place_name or builder.name} {kind.suffix}",
            body=f"The masters of prosperous {builder.name} built {indefinite(kind.subtype)}.",
            stats=StructureStats(
                splendor=clamp_int(
                    life.structure_splendor_base
                    + rng.die(life.structure_splendor_die)
                    + round_half_up(life.structure_architecture_bonus * site.architecture_effect),
                    0,
                    PERCENT,
                ),
                durability=clamp_int(life.structure_durability_base + rng.die(life.structure_durability_die), 0, PERCENT),
                function=clamp_int(life.structure_function_base + rng.die(life.structure_function_die), 0, PERCENT),
            ),
            power=clamp_int(
                round_half_up(builder.power_level * life.structure_power_share_pct / PERCENT) + 1, life.derived_min_power, life.structure_max_power
            ),
            location_id=place_id,
            world_id=builder.world_id,
            subtype=kind.subtype,
            engine_kind=kind.kind,
        ),
    )
    await connect(ctx.session, builder.id, work.id, BondKind.BUILT, ctx.epoch)
    if kind.kind is EngineKind.TEMPLE:
        await judged(ctx, builder.id, builder.id, ActKind.BUILDING_TEMPLES, note=work.name)
    kind.effect(rules, builder)
    prosperity = stat(builder, "prosperity")
    if prosperity is not None:
        set_stats(builder, prosperity=clamp_int(prosperity - life.structure_prosperity_cost, 0, PERCENT))
    goods = await stock(ctx.session, rules, builder.id, Commodity.GOODS)
    await set_stock(ctx.session, builder.id, Commodity.GOODS, clamp_int(goods - life.structure_goods_cost, 0, rules.society.stockpile_cap))
    await note(ctx, f"The masters of {builder.name} built {indefinite(kind.subtype)}.", key="works.built", ids=[builder.id, work.id])
    ctx.count("built")
    return work


def craft_ready(rules: Rules, site: Site) -> bool:
    life = rules.deep_life
    return (
        site.shares[SocialClass.ARTISAN] >= life.structure_min_artisan_pct
        or (stat(site.builder, "craft") or 0) >= life.structure_min_craft
        or site.knows_architecture
    )


def can_build(rules: Rules, community: EntityRow) -> bool:
    life = rules.deep_life
    population = stat(community, "population") or 0
    minimum = life.structure_settlement_min_population if community.entity_type is EntityType.SETTLEMENT else life.structure_people_min_population
    return population >= minimum and prosperity_of(rules, community) >= rules.deep_world.structure_min_prosperity


async def engine_works(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    knowledge = await KnowledgeMap.load(ctx.session)
    built = 0
    cap = scaled_cap(rules.deep_world.structure_cap, rules.deep_world.structure_cap_community_divisor, await count_communities(ctx.session))
    for builder in await canon(ctx.session, BUILDER_TYPES):
        if built >= cap:
            break
        if not can_build(rules, builder):
            continue
        site = await site_of(ctx, builder, knowledge)
        if not craft_ready(rules, site) or not rng.chance(rules.deep_world.structure_chance):
            continue
        present = await existing_kinds(ctx, builder, builder.id if builder.entity_type is EntityType.SETTLEMENT else builder.location_id)
        kind = next((item for item in WORK_KINDS if item.kind not in present and item.eligible(rules, site)), None)
        if kind is None:
            continue
        await build(ctx, site, kind)
        built += 1


async def owner_of(ctx: TickContext, work: EntityRow) -> EntityRow | None:
    location = await living_entity(ctx.session, work.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    bonds = sorted(await active_bonds(ctx.session, OWNER_BOND_KINDS, targets=[work.id]), key=lambda bond: bond.id)
    owner = await living_entity(ctx.session, bonds[0].source_node_id) if bonds else None
    return owner if owner is not None and owner.entity_type in COMMUNITY_TYPES else None


async def splendor_growth(ctx: TickContext) -> None:
    rules = ctx.rules
    life = rules.deep_life
    knowledge = await KnowledgeMap.load(ctx.session)
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        splendor = stat(work, "splendor")
        if splendor is not None and splendor >= PERCENT:
            continue
        owner = await owner_of(ctx, work)
        if owner is None or prosperity_of(rules, owner) < life.adorn_min_prosperity:
            continue
        shares = await class_shares(ctx.session, rules, owner.id)
        gain = rules.deep_world.splendor_gain
        gain += life.adorn_artisan_bonus if shares[SocialClass.ARTISAN] >= life.adorn_min_artisan_pct else 0
        gain += round_half_up(life.adorn_architecture_bonus * knowledge.effect(rules, owner.id, KnowledgeBranch.ARCHITECTURE))
        set_stats(work, splendor=clamp_int((splendor if splendor is not None else life.adorn_default_splendor) + gain, 0, PERCENT))


async def commission_work(ctx: TickContext, community_id: int, kind: EngineKind | None = None) -> EntityRow:
    builder = await living_entity(ctx.session, community_id)
    if builder is None or builder.entity_type not in BUILDER_TYPES:
        raise ValidationFailedError("Only a living people or settlement can raise a work.")
    site = await site_of(ctx, builder, await KnowledgeMap.load(ctx.session))
    present = await existing_kinds(ctx, builder, builder.id if builder.entity_type is EntityType.SETTLEMENT else builder.location_id)
    candidates = [item for item in WORK_KINDS if item.kind not in present and (kind is None or item.kind is kind)]
    if kind is None:
        candidates = [item for item in candidates if item.eligible(ctx.rules, site)] or candidates
    if not candidates:
        raise ValidationFailedError(f"{builder.name} already has every work it could build.")
    return await build(ctx, site, candidates[0])


BUILD_PHASES = (Phase("engine_works", engine_works),)
SPLENDOR_PHASES = (Phase("splendor_growth", splendor_growth),)
PHASES = BUILD_PHASES + SPLENDOR_PHASES
