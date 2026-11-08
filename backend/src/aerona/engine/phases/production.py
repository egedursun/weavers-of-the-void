from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.commodities import commodity_label
from aerona.catalog.materials import SPECIES_GOODS, SPECIES_GROUNDS, SPECIES_YIELDS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.ecology import HerdRow
from aerona.db.tables.economy import CommunityStockRow, NodeMaterialRow, ResourceProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, MaterialOrigin
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, SkyEventKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.deposits import Deposit, backfill_physics, has_substance, new_substance, open_deposit
from aerona.engine.economy.materials import corruption_lure, curse_bonus, decay_loss, enchantment_cap, sanctity_splendour, sanctity_ward
from aerona.engine.economy.provenance import sweep_materials
from aerona.engine.economy.refining import RefiningTally, refine_community
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.economy.survey import depth_backfill, economy_backfill, profile_resources, seed_communities
from aerona.engine.environment.book import active_sky
from aerona.engine.industry.fuels import lay_coal_seams
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

ITEM_DECAY_KEYS = ("damage", "protection", "might")
CORRUPT_FROM = PERCENT // 2


@reads(
    "people.population",
    "settlement.population",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.war_production",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_industry",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.production_runs",
    "table.workshops",
)
async def refining(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = RefiningTally()
    for community in unheld(book.communities):
        await refine_community(ctx, book, community, tally)
        await sync_aggregates(ctx.session, ctx.rules, community)
    ctx.count("batches", tally.batches)
    ctx.count("workshops_built", tally.built)
    ctx.count("ships_launched", tally.ships)
    for commodity, count in sorted(tally.bottlenecks.items()):
        ctx.count(f"bottleneck_{commodity}", count)


async def _decay_item(ctx: TickContext, item: EntityRow, loss: int, cap: int, curse: int) -> bool:
    values = {key: max(0, (stat(item, key) or 0) - loss) for key in ITEM_DECAY_KEYS}
    values["might"] = min(values["might"], cap)
    if curse > 0 and ctx.rng(f"material.curse.{item.id}").chance(curse):
        values["curse"] = clamp_int((stat(item, "curse") or 0) + curse, 0, PERCENT)
    set_stats(item, **values)
    if loss > 0 and all(values[key] == 0 for key in ITEM_DECAY_KEYS):
        await retire_in(ctx, item, "crumbled away", status=EntityStatus.DESTROYED)
        await note(ctx, f"{item.name} crumbled away; its material could not outlast the years.", key="material.crumbled", ids=[item.id])
        return True
    return False


async def holy_and_tainted_stocks(ctx: TickContext, book: EconomyBook, lure: dict[int, int]) -> dict[int, int]:
    wards: dict[int, int] = defaultdict(int)
    for lot in await ctx.session.scalars(select(CommunityStockRow).where(CommunityStockRow.quantity > 0)):
        community = book.entities.get(lot.community_entity_id)
        if community is None:
            continue
        props = book.materials.props(community.world_id, lot.material, lot.world_material_id)
        if lot.commodity is CommodityKind.SACRED_GOODS:
            wards[community.id] = max(wards[community.id], sanctity_ward(ctx.rules, props) if props is not None else ctx.rules.materials.sanctity_ward_pct)
        if props is not None and props.corruption >= CORRUPT_FROM and community.world_id is not None:
            lure[community.world_id] += corruption_lure(ctx.rules, props)
    return wards


@reads(
    "item.curse",
    "item.damage",
    "item.might",
    "item.protection",
    "outer_being.interest",
    "spirit.unrest",
    "structure.durability",
    "structure.splendor",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.node_materials",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "item.curse",
    "item.damage",
    "item.might",
    "item.protection",
    "outer_being.interest",
    "spirit.unrest",
    "structure.durability",
    "structure.splendor",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def material_decay(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    rows = list(await ctx.session.scalars(select(NodeMaterialRow).order_by(NodeMaterialRow.node_id, NodeMaterialRow.slot)))
    lure: dict[int, int] = defaultdict(int)
    crumbled = 0
    for row in rows:
        entity = book.entities.get(row.node_id)
        if entity is None or entity.entity_type not in (EntityType.ITEM, EntityType.STRUCTURE):
            continue
        props = book.materials.props(entity.world_id, row.material, row.world_material_id)
        if props is None:
            continue
        loss = decay_loss(ctx.rules, props, book.temperature(entity.id))
        if entity.world_id is not None and props.corruption >= CORRUPT_FROM:
            lure[entity.world_id] += corruption_lure(ctx.rules, props)
        if entity.entity_type is EntityType.ITEM:
            crumbled += await _decay_item(ctx, entity, loss, enchantment_cap(ctx.rules, props), curse_bonus(ctx.rules, props))
            continue
        splendour = sanctity_splendour(ctx.rules, props) if entity.engine_kind is EngineKind.TEMPLE else 0
        set_stats(
            entity, durability=max(0, (stat(entity, "durability") or 0) - loss), splendor=clamp_int((stat(entity, "splendor") or 0) + splendour, 0, PERCENT)
        )
    wards = await holy_and_tainted_stocks(ctx, book, lure)
    for spirit in await canon(ctx.session, [EntityType.SPIRIT]):
        ward = wards.get(spirit.location_id or 0, 0)
        if ward:
            set_stats(spirit, unrest=max(0, (stat(spirit, "unrest") or 0) - ward))
    for being in await canon(ctx.session, [EntityType.OUTER_BEING]):
        drawn = lure.get(being.world_id or 0, 0) if being.world_id is not None else sum(lure.values())
        if drawn:
            set_stats(being, interest=clamp_int((stat(being, "interest") or 0) + drawn, 0, PERCENT))
    ctx.count("crumbled", crumbled)
    ctx.count("lured", sum(lure.values()))


async def _place_in(ctx: TickContext, world_id: int) -> EntityRow | None:
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
    regions = list(await ctx.session.scalars(statement.order_by(EntityRow.id)))
    return ctx.rng(f"place.{world_id}").pick(regions) if regions else None


async def _deposit_at(ctx: TickContext, place_id: int, material: MaterialKind) -> bool:
    statement = (
        select(ResourceProfileRow.resource_entity_id)
        .join(EntityRow, EntityRow.id == ResourceProfileRow.resource_entity_id)
        .where(EntityRow.location_id == place_id, ResourceProfileRow.material == material)
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def _god_remains(ctx: TickContext) -> int:
    made = 0
    for corpse in await canon(ctx.session, [EntityType.PLACE]):
        if corpse.engine_kind is not EngineKind.GOD_CORPSE or await _deposit_at(ctx, corpse.id, MaterialKind.GODFLESH):
            continue
        await open_deposit(
            ctx,
            Deposit(
                name=f"Godflesh of {corpse.name}",
                body=f"The flesh of the dead god at {corpse.name} can be cut and carried away.",
                place=corpse,
                commodity=CommodityKind.ORE,
                material=MaterialKind.GODFLESH,
                richness=80,
                quality=90,
            ),
        )
        made += 1
        if not await has_substance(ctx, corpse.id) and ctx.rng(f"substance.god.{corpse.id}").chance(ctx.rules.materials.world_material_god_chance):
            await new_substance(ctx, MaterialOrigin.GOD_REMAINS, corpse, source_node_id=corpse.id)
    return made


async def _dead_stars(ctx: TickContext) -> int:
    made = 0
    for star in await ctx.session.scalars(select(StarRow).where(StarRow.star_type.in_(list(EXTINGUISHED_STAR_TYPES))).order_by(StarRow.id)):
        if await has_substance(ctx, star.id):
            continue
        worlds = list(await ctx.session.scalars(select(WorldRow).where(WorldRow.star_id == star.id).order_by(WorldRow.id)))
        place = await _place_in(ctx, worlds[0].id) if worlds else None
        if place is None or not ctx.rng(f"substance.star.{star.id}").chance(ctx.rules.materials.world_material_star_chance):
            continue
        await new_substance(ctx, MaterialOrigin.DEAD_STAR, place, source_node_id=star.id)
        made += 1
    return made


async def _comets(ctx: TickContext) -> int:
    made = 0
    sky = await active_sky(ctx.session, ctx.epoch)
    for world_id, kinds in sky.items():
        if world_id is None or SkyEventKind.COMET not in kinds:
            continue
        place = await _place_in(ctx, world_id)
        if place is None or not ctx.rng(f"comet.{world_id}.{ctx.epoch}").chance(ctx.rules.materials.world_material_star_chance):
            continue
        await open_deposit(
            ctx,
            Deposit(
                name=f"Star Metal of {place.name}",
                body=f"A comet fell on {place.name} and left a crater of star metal.",
                place=place,
                commodity=CommodityKind.ORE,
                material=MaterialKind.STAR_METAL,
                reserve=ctx.rules.extraction.deposit_reserve // 3,
                richness=70,
                quality=85,
            ),
        )
        made += 1
    return made


async def _leak_crystals(ctx: TickContext, book: EconomyBook) -> int:
    made = 0
    for region in book.ground.regions.values():
        depth = region.scars.get(ScarKind.LEAK_WOUND.value, 0)
        place = book.entities.get(region.entity_id)
        if depth <= 0 or place is None or await _deposit_at(ctx, place.id, MaterialKind.VOID_GLASS):
            continue
        if not ctx.rng(f"substance.leak.{place.id}.{ctx.epoch}").chance(ctx.rules.materials.world_material_leak_chance):
            continue
        await open_deposit(
            ctx,
            Deposit(
                name=f"Void Glass of {place.name}",
                body=f"The leak wound in {place.name} has glazed into void glass.",
                place=place,
                commodity=CommodityKind.ORE,
                material=MaterialKind.VOID_GLASS,
                reserve=ctx.rules.extraction.deposit_reserve // 2,
                richness=55,
                quality=75,
            ),
        )
        if not await has_substance(ctx, place.id):
            await new_substance(ctx, MaterialOrigin.LEAK_CRYSTAL, place, source_node_id=place.id)
        made += 1
    return made


async def _research(ctx: TickContext, book: EconomyBook) -> int:
    table = ctx.rules.materials
    made = 0
    for community in book.communities:
        if book.level(community.id, KnowledgeBranch.METALLURGY) < table.world_material_research_level or await has_substance(ctx, community.id):
            continue
        if ctx.rng(f"substance.research.{community.id}.{ctx.epoch}").chance(table.world_material_research_chance):
            await new_substance(ctx, MaterialOrigin.RESEARCH, community, source_node_id=community.id)
            made += 1
    return made


async def _slain_beasts(ctx: TickContext) -> int:
    made = 0
    statement = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.EXTINCT, EntityFlagRow.epoch == ctx.epoch)
    megafauna = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    for species_id in sorted(await ctx.session.scalars(statement)):
        if await has_substance(ctx, species_id):
            continue
        species = await ctx.session.get(EntityRow, species_id)
        body = await ctx.session.get(BodyRow, species_id)
        great = species_id in megafauna or (body is not None and body.plan is BodyPlan.COLOSSAL)
        if species is None or not great:
            continue
        place = await ctx.session.get(EntityRow, species.location_id) if species.location_id is not None else None
        if place is not None and ctx.rng(f"substance.beast.{species_id}").chance(ctx.rules.materials.world_material_beast_chance):
            await new_substance(ctx, MaterialOrigin.BEAST, place, source_node_id=species_id)
            made += 1
    return made


@reads(
    "table.army_profiles",
    "table.bodies",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.entity_flags",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.nodes",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.stars",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.resource_profiles",
    "table.world_materials",
)
async def world_materials(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    ctx.count("god_remains", await _god_remains(ctx))
    ctx.count("dead_stars", await _dead_stars(ctx))
    ctx.count("comets", await _comets(ctx))
    ctx.count("leak_crystals", await _leak_crystals(ctx, book))
    ctx.count("alloys", await _research(ctx, book))
    ctx.count("beasts", await _slain_beasts(ctx))


async def _grounds(ctx: TickContext) -> dict[int, list[tuple[EntityRow, ResourceProfileRow]]]:
    statement = (
        select(EntityRow, ResourceProfileRow)
        .join(ResourceProfileRow, ResourceProfileRow.resource_entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.RESOURCE, EntityRow.maker_entity_id.is_not(None))
        .order_by(EntityRow.id)
    )
    found: dict[int, list[tuple[EntityRow, ResourceProfileRow]]] = defaultdict(list)
    for resource, profile in await ctx.session.execute(statement):
        if resource.maker_entity_id is not None:
            found[resource.maker_entity_id].append((resource, profile))
    return found


async def _herded(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(HerdRow.species_entity_id)))


def _wanted(plan: BodyPlan | None, abundance: int, rules: Rules, herded: bool) -> list[tuple[CommodityKind, MaterialKind | None]]:
    materials = SPECIES_YIELDS.get(plan, ()) if plan in (BodyPlan.COLOSSAL, BodyPlan.INSECTOID) else ()
    wanted: list[tuple[CommodityKind, MaterialKind | None]] = [(CommodityKind.ORE, materials[0])] if materials else []
    if plan is not None and not herded and abundance >= rules.extraction.species_ground_abundance:
        wanted.extend((good, None) for good in SPECIES_GOODS.get(plan, ()))
    return wanted


async def _open_ground(ctx: TickContext, species: EntityRow, place: EntityRow, ground: tuple[CommodityKind, MaterialKind | None], abundance: int) -> None:
    commodity, material = ground
    reserve = max(1, round_half_up(ctx.rules.extraction.deposit_reserve * abundance / PERCENT))
    if material is not None:
        name, body = f"Hunting Grounds of {species.name}", f"Hunters of {place.name} take {material.value.replace('_', ' ')} from the {species.name}."
    else:
        word = SPECIES_GROUNDS[commodity]
        name, body = f"{word} of {species.name}", f"The people of {place.name} take {commodity_label(commodity).lower()} from the wild {species.name}."
    resource = await open_deposit(
        ctx, Deposit(name=name, body=body, place=place, commodity=commodity, material=material, reserve=reserve, richness=60, quality=70)
    )
    resource.maker_entity_id = species.id


@reads("species.abundance", "table.bodies", "table.bonds", "table.entity_flags", "table.herds", "table.name_registry", "table.nodes", "table.resource_profiles")
@writes("resource.abundance", "table.bonds", "table.entities", "table.name_registry", "table.resource_profiles")
async def species_yields(ctx: TickContext) -> None:
    extinct = await flags_by_entity(ctx.session, EntityFlag.EXTINCT)
    megafauna = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    grounds = await _grounds(ctx)
    herded = await _herded(ctx)
    opened = 0
    for species_id, worked in grounds.items():
        if species_id in extinct:
            for _, profile in worked:
                if not profile.held:
                    profile.regeneration = 0
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        body = await ctx.session.get(BodyRow, species.id)
        plan = BodyPlan.COLOSSAL if species.id in megafauna else body.plan if body is not None else None
        abundance = stat(species, "abundance") or 0
        worked = grounds.get(species.id, [])
        for _, profile in worked:
            if not profile.held:
                profile.regeneration = round_half_up(profile.initial_reserve * ctx.rules.extraction.renewable_regen_pct / PERCENT * abundance / PERCENT)
        if species.location_id is None:
            continue
        have = {(profile.commodity, profile.material) for _, profile in worked}
        missing = [item for item in _wanted(plan, abundance, ctx.rules, species.id in herded) if item not in have]
        place = await ctx.session.get(EntityRow, species.location_id) if missing else None
        if place is None:
            continue
        for ground in missing:
            await _open_ground(ctx, species, place, ground, abundance)
            opened += 1
    ctx.count("hunting_grounds", opened)


@reads(
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.name_registry",
    "table.nodes",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.nodes",
    "table.resource_profiles",
)
async def deposit_finding(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    table = ctx.rules.extraction
    ctx.count("coal_seams_laid", await lay_coal_seams(ctx, book))
    book = await EconomyBook.load(ctx)
    found = 0
    hidden = [
        (resource, book.profiles[resource.id]) for resource in book.resources() if resource.id in book.profiles and not book.profiles[resource.id].revealed
    ]
    for resource, profile in hidden:
        region = book.ground.atlas.top_region(resource.id)
        finders = [community for community in book.communities if book.ground.atlas.top_region(community.id) == region]
        for community in finders:
            if book.level(community.id, KnowledgeBranch.METALLURGY) < table.deposit_reveal_level:
                continue
            if ctx.rng(f"reveal.{resource.id}.{community.id}.{ctx.epoch}").chance(table.deposit_reveal_chance):
                profile.revealed = True
                found += 1
                await ctx.chronicle(
                    ChronicleKind.RESOURCE,
                    f"The prospectors of {community.name} found {resource.name}.",
                    template_key="extraction.deposit_found",
                    entity_ids=[community.id, resource.id],
                )
                break
    ctx.count("deposits_found", found)


@reads(
    "resource.abundance",
    "resource.might",
    "resource.value",
    "table.applied_fixups",
    "table.armies",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.item_profiles",
    "table.name_registry",
    "table.node_materials",
    "table.nodes",
    "table.place_environment",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_infrastructure",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.treaty_parties",
    "table.vessel_profiles",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.entities",
    "table.goods_flows",
    "table.name_registry",
    "table.node_materials",
    "table.resource_profiles",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.workshops",
)
async def economy_survey(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    ctx.count("resources_profiled", await profile_resources(ctx, book))
    ctx.count("communities_seeded", await seed_communities(ctx, book))
    for key, value in (await economy_backfill(ctx, book)).items():
        ctx.count(f"backfilled_{key}", value)
    for key, value in (await depth_backfill(ctx)).items():
        ctx.count(f"depth_{key}", value)
    ctx.count("materials_assigned", await sweep_materials(ctx.session, ctx.rules))
    ctx.count("material_physics_backfilled", await backfill_physics(ctx.session))


PHASES = (
    Phase("economy_survey", economy_survey),
    Phase("refining", refining),
    Phase("material_decay", material_decay),
    Phase("world_materials", world_materials),
    Phase("species_yields", species_yields),
    Phase("deposit_finding", deposit_finding),
)
