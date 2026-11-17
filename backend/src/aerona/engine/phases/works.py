from sqlalchemy import select

from aerona.catalog.structures import ENGINE_KIND_STRUCTURES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import STANDING_STATES, ConstructionState, ConstructionStatus, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.hooks import judged
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import active_bonds, canon, count_communities, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.structures.construction import Commission, active_at, advance, begin
from aerona.engine.structures.needs import facts_for, wanted
from aerona.engine.structures.spec import resolve, slots_for, tier_allows
from aerona.rules.registry import Rules

BUILDER_TYPES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
OWNER_BOND_KINDS = (BondKind.BUILT, BondKind.OWNS, BondKind.RULES)


def prosperity_of(rules: Rules, community: EntityRow) -> int:
    prosperity = stat(community, "prosperity")
    if prosperity is not None:
        return prosperity
    if community.entity_type is EntityType.PEOPLE:
        life = rules.deep_life
        return life.structure_people_prosperity_base + round_half_up((stat(community, "craft") or 0) / life.structure_people_craft_divisor)
    return 0


async def craft_ready(ctx: TickContext, community: EntityRow, knowledge: KnowledgeMap) -> bool:
    life = ctx.rules.deep_life
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    return (
        shares[SocialClass.ARTISAN] >= life.structure_min_artisan_pct
        or (stat(community, "craft") or 0) >= life.structure_min_craft
        or knowledge.knows(community.id, KnowledgeBranch.ARCHITECTURE)
    )


def can_build(rules: Rules, community: EntityRow) -> bool:
    life = rules.deep_life
    population = stat(community, "population") or 0
    minimum = life.structure_settlement_min_population if community.entity_type is EntityType.SETTLEMENT else life.structure_people_min_population
    return population >= minimum and prosperity_of(rules, community) >= rules.deep_world.structure_min_prosperity


async def used_slots(ctx: TickContext, host_id: int) -> int:
    rows = await ctx.session.scalars(
        select(StructureProfileRow.structure_entity_id).where(
            StructureProfileRow.host_entity_id == host_id,
            StructureProfileRow.construction_state != ConstructionState.RUINED,
        )
    )
    return len(list(rows))


async def free_slots(ctx: TickContext, site: EntityRow) -> int:
    town = await ctx.session.get(SettlementProfileRow, site.id)
    if town is None:
        return ctx.rules.construction.slots_base - await used_slots(ctx, site.id)
    return slots_for(ctx.rules, town.size_tier) - await used_slots(ctx, site.id)


async def plan_work(ctx: TickContext, site: EntityRow, knowledge: KnowledgeMap, atlas: RegionAtlas) -> EntityRow | None:
    if await free_slots(ctx, site) <= 0 or len(await active_at(ctx, site.id)) >= ctx.rules.construction.active_per_site:
        return None
    facts = await facts_for(ctx, site, knowledge, atlas)
    tier = facts.town.size_tier if facts.town is not None else None
    for kind in wanted(ctx.rules, facts):
        if tier is not None and not tier_allows(tier, resolve(kind)):
            continue
        work, _ = await begin(ctx, Commission(site=site, kind=kind))
        if kind is StructureKind.TEMPLE:
            await judged(ctx, site.id, site.id, ActKind.BUILDING_TEMPLES, note=work.name)
        return work
    return None


async def advance_all(ctx: TickContext, knowledge: KnowledgeMap) -> int:
    rows = list(await ctx.session.scalars(select(ConstructionRow).where(ConstructionRow.status == ConstructionStatus.ACTIVE).order_by(ConstructionRow.id)))
    sites: dict[int | None, int] = {}
    for row in rows:
        sites[row.site_entity_id] = sites.get(row.site_entity_id, 0) + 1
    advanced = 0
    for row in rows:
        advanced += 1 if await advance(ctx, row, active=sites[row.site_entity_id], knowledge=knowledge) else 0
    return advanced


@reads(
    "people.craft",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "structure.durability",
    "structure.function",
    "table.blueprints",
    "table.bonds",
    "table.camps",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_societies",
    "table.community_stocks",
    "table.company_profiles",
    "table.constructions",
    "table.cosmos",
    "table.creator_taboos",
    "table.cuisines",
    "table.culture_ethics",
    "table.culture_values",
    "table.currencies",
    "table.deed_claims",
    "table.deeds",
    "table.designs",
    "table.dishes",
    "table.divine_wounds",
    "table.drink_kinds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.equipment_models",
    "table.geasa",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.item_profiles",
    "table.language_profiles",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_materials",
    "table.nodes",
    "table.number_systems",
    "table.offices",
    "table.outbreaks",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.region_environment",
    "table.reputations",
    "table.resource_profiles",
    "table.settlement_profiles",
    "table.skills",
    "table.structure_designs",
    "table.structure_profiles",
    "table.structure_sections",
    "table.structure_staff",
    "table.tradition_profiles",
    "table.traits",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.workshops",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
)
@writes(
    "people.piety",
    "people.prosperity",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "structure.durability",
    "structure.splendor",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.constructions",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.memories",
    "table.name_registry",
    "table.node_materials",
    "table.reputations",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.structure_designs",
    "table.structure_profiles",
    "table.structure_staff",
    "table.workshops",
)
async def engine_works(ctx: TickContext) -> None:
    rules = ctx.rules
    knowledge = await KnowledgeMap.load(ctx.session)
    ctx.count("advanced", await advance_all(ctx, knowledge))
    atlas = await RegionAtlas.load(ctx.session)
    rng = ctx.rng()
    begun = 0
    cap = scaled_cap(rules.deep_world.structure_cap, rules.deep_world.structure_cap_community_divisor, await count_communities(ctx.session))
    for builder in await canon(ctx.session, BUILDER_TYPES):
        if begun >= cap:
            break
        if not can_build(rules, builder) or not await craft_ready(ctx, builder, knowledge) or not rng.chance(rules.deep_world.structure_chance):
            continue
        site = builder if builder.entity_type is EntityType.SETTLEMENT else await living_entity(ctx.session, builder.location_id)
        if site is None or site.entity_type not in COMMUNITY_TYPES:
            site = builder
        if held(builder.id, site.id):
            continue
        if await plan_work(ctx, site, knowledge, atlas) is not None:
            begun += 1
            ctx.count("built")


async def owner_of(ctx: TickContext, work: EntityRow) -> EntityRow | None:
    location = await living_entity(ctx.session, work.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    bonds = sorted(await active_bonds(ctx.session, OWNER_BOND_KINDS, targets=[work.id]), key=lambda bond: bond.id)
    owner = await living_entity(ctx.session, bonds[0].source_node_id) if bonds else None
    return owner if owner is not None and owner.entity_type in COMMUNITY_TYPES else None


@reads(
    "people.craft",
    "people.prosperity",
    "settlement.prosperity",
    "structure.splendor",
    "table.bonds",
    "table.community_societies",
    "table.holder_levels",
    "table.structure_profiles",
)
@writes("structure.splendor", "table.entities")
async def splendor_growth(ctx: TickContext) -> None:
    rules = ctx.rules
    life = rules.deep_life
    knowledge = await KnowledgeMap.load(ctx.session)
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        profile = await ctx.session.get(StructureProfileRow, work.id)
        if profile is not None and profile.construction_state not in STANDING_STATES:
            continue
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
    knowledge = await KnowledgeMap.load(ctx.session)
    if kind is not None:
        if kind not in ENGINE_KIND_STRUCTURES:
            raise ValidationFailedError(f"{kind.value.replace('_', ' ')} is not a kind of work.")
        work, _ = await begin(ctx, Commission(site=builder, kind=ENGINE_KIND_STRUCTURES[kind], player=True))
        return work
    planned = await plan_work(ctx, builder, knowledge, await RegionAtlas.load(ctx.session))
    if planned is None:
        raise ValidationFailedError(f"{builder.name} has nothing it needs to build, or no room to build it.")
    return planned


BUILD_PHASES = (Phase("engine_works", engine_works),)
SPLENDOR_PHASES = (Phase("splendor_growth", splendor_growth),)
PHASES = BUILD_PHASES + SPLENDOR_PHASES
