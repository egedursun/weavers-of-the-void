from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.materials import MATERIALS
from aerona.constants.bond_texts import ITS_MIRROR
from aerona.constants.cosmos import RECENT_DEATH_EPOCHS
from aerona.constants.units import PERCENT
from aerona.constants.warfare import MULTI_WORLD_COSMOS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.record_context import current_scope
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import SkyEventRow, WorldRow
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.society import ArchiveHoldingRow, SoulRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import InstrumentKind, StepAction, StepLocus, StepOutcome
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import JourneyStatus, TravelMethod
from aerona.domain.enums.world import Discovery, SkyEventKind
from aerona.domain.models.entity_stats import MortalStats, SpeciesStats, SpiritStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.quests import abandon_quest, legendary_quests, live_archive, worlds_known
from aerona.engine.cosmos.routes import sever_route
from aerona.engine.cosmos.world_types import is_living, is_mirror, is_realm_of_dead
from aerona.engine.faith.judgement import judge
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent, fraction, scaled_cap
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import BondIndex, canon, count_communities, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import FOLLOWERS_KEY, POPULATION_KEY, scale_stat, shift_bounded, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.profiles import ensure_profile
from aerona.rules.registry import Rules

BINDABLE_TYPES = frozenset({EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})
MIGHT_KEY = "might"
STRANGENESS_KEY = "strangeness"
ZEAL_KEY = "zeal"
INFLUENCE_KEY = "influence"
DANGER_KEY = "danger"
SPREAD_KEY = "spread"
MIRROR_STATS = ("strength", "agility", "intellect", "charisma")


async def _require(session: AsyncSession, entity_id: int, label: str) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError(label)
    return entity


async def soul_bind(ctx: TickContext, soul_id: int, target_id: int, binder_id: int | None = None) -> EntityRow:
    soul = await ctx.session.get(EntityRow, soul_id)
    if soul is None or soul.status is not EntityStatus.CANON or soul.entity_type is not EntityType.SPIRIT:
        raise NotFoundError("No such free soul.")
    target = await _require(ctx.session, target_id, "No such work.")
    if target.entity_type not in BINDABLE_TYPES:
        raise ValidationFailedError("A soul binds only to an item, a vehicle or a work.")
    await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: bound to {target.name}.", close_bonds=True)
    await BondRepository(ctx.session).connect(BondDraft(soul.id, target.id, BondKind.INSIDE, ctx.epoch, "soul binding", role=BondRole.SPIRIT_BINDING))
    soul_row = await ctx.session.get(SoulRow, soul.id)
    if soul_row is not None:
        soul_row.bound_to_entity_id = target.id
    result = await _animate(ctx, soul, target, binder_id) if target.entity_type is EntityType.STRUCTURE else await _bind_object(ctx, target)
    await record(
        ctx,
        "beyond.soul_bound",
        roles={
            IncidentRole.SUBJECT: soul.id,
            IncidentRole.INSTRUMENT: target.id,
            IncidentRole.ACTOR: binder_id,
            IncidentRole.PRODUCT: result.id if result.id != target.id else None,
        },
        facts={"animated": 1 if result.id != target.id else 0},
        steps=(StepDraft(StepAction.BIND, actor=binder_id, target=soul.id, instrument_kind=InstrumentKind.ITEM, instrument_node=target.id),),
        place=target.location_id,
        world_id=target.world_id,
    )
    return result


async def hard_bodied(ctx: TickContext, work: EntityRow) -> bool:
    kind = await ctx.session.scalar(select(NodeMaterialRow.material).where(NodeMaterialRow.node_id == work.id, NodeMaterialRow.slot == MaterialSlot.BODY))
    return kind is not None and MATERIALS[kind].hardness >= ctx.rules.beyond.animated_work_hard_from


async def _animate(ctx: TickContext, soul: EntityRow, work: EntityRow, binder_id: int | None) -> EntityRow:
    beyond = ctx.rules.beyond
    rng = ctx.rng("animated_work")
    animated = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Animated {work.name}",
            entity_type=EntityType.SPECIES,
            body=f"{soul.name} was bound to {work.name}, and the work began to move.",
            stats=SpeciesStats(
                hp=beyond.animated_work_hp,
                strength=clamp_percent(beyond.animated_work_strength_base + rng.die(beyond.animated_work_strength_die)),
                agility=beyond.animated_work_agility,
                intelligence=clamp_percent(beyond.animated_work_intelligence_base + rng.die(beyond.animated_work_intelligence_die)),
                danger=clamp_percent(beyond.animated_work_danger_base + rng.die(beyond.animated_work_danger_die)),
            ),
            power=max(beyond.animated_work_min_power, work.power_level),
            world_id=work.world_id,
            location_id=work.location_id,
            subtype="animated work",
            engine_kind=EngineKind.ANIMATED_WORK,
            traits=(CreatureTrait.STONESKIN,) if await hard_bodied(ctx, work) else (),
        ),
    )
    if binder_id is not None:
        await BondRepository(ctx.session).connect(BondDraft(binder_id, animated.id, BondKind.TAMED, ctx.epoch, "the work it bound a spirit into"))
    return animated


async def _bind_object(ctx: TickContext, target: EntityRow) -> EntityRow:
    beyond = ctx.rules.beyond
    shift_bounded(ctx.rules, target, MIGHT_KEY, beyond.spirit_cloak_item_might)
    if target.entity_type is EntityType.VESSEL:
        shift_bounded(ctx.rules, target, STRANGENESS_KEY, beyond.spirit_cloak_vessel_strangeness)
    await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.SOUL_BOUND, ctx.epoch)
    return target


async def realm_regions(session: AsyncSession, world: WorldRow) -> list[EntityRow]:
    regions = await canon(session, [EntityType.REGION], world.id)
    if is_realm_of_dead(world.world_type):
        return regions
    return [region for region in regions if region.is_underworld]


async def descend_soul(ctx: TickContext, dead: EntityRow, region: EntityRow) -> EntityRow:
    beyond = ctx.rules.beyond
    rng = ctx.rng("descent")
    await EntityRepository(ctx.session).add_flag(dead.id, EntityFlag.SOUL_DESCENDED, ctx.epoch)
    realm = await ctx.session.get(WorldRow, region.world_id)
    soul = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Shadow of {dead.name}",
            entity_type=EntityType.SPIRIT,
            body=f"{dead.name} died and their soul descended to {realm.name if realm else region.name}.",
            stats=SpiritStats(
                strength=clamp_percent(beyond.descended_spirit_strength_base + rng.die(beyond.descended_spirit_strength_die)),
                unrest=clamp_percent(beyond.descended_spirit_unrest_base + rng.die(beyond.descended_spirit_unrest_die)),
            ),
            power=beyond.descended_spirit_power,
            world_id=region.world_id,
            location_id=region.id,
            subtype="descended soul",
            engine_kind=EngineKind.DESCENDED_SOUL,
        ),
    )
    ctx.session.add(
        SoulRow(spirit_entity_id=soul.id, mortal_entity_id=dead.id, origin_world_id=dead.world_id, realm_entity_id=region.id, descended_epoch=ctx.epoch)
    )
    await BondRepository(ctx.session).connect(BondDraft(dead.id, region.id, BondKind.SOUL_DESCENDED_TO, ctx.epoch, "the soul's descent"))
    verdict = await judge(ctx, soul, dead, region)
    ctx.count("souls_judged")
    if verdict.stratum is None:
        ctx.count("souls_wandering")
    return soul


async def soul_descent(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    descended = await flags_by_entity(ctx.session, EntityFlag.SOUL_DESCENDED)
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch >= ctx.epoch - RECENT_DEATH_EPOCHS
    )
    dead = [item for item in await ctx.session.scalars(statement.order_by(EntityRow.end_epoch, EntityRow.id)) if item.id not in descended]
    rng = ctx.rng("souls")
    per_realm: dict[int, int] = {}
    count = 0
    for mortal in dead:
        world = await ctx.session.get(WorldRow, mortal.world_id)
        regions = await realm_regions(ctx.session, world) if world is not None else []
        if not regions:
            continue
        realm_world = regions[0].world_id
        if per_realm.get(realm_world, 0) >= beyond.soul_descent_cap or not rng.chance(beyond.soul_descent_chance):
            continue
        await descend_soul(ctx, mortal, rng.pick(regions))
        per_realm[realm_world] = per_realm.get(realm_world, 0) + 1
        count += 1
    return count


async def soul_buildup(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if not is_realm_of_dead(world.world_type):
            continue
        souls = [item for item in await canon(ctx.session, [EntityType.SPIRIT], world.id) if item.engine_kind is EngineKind.DESCENDED_SOUL]
        if len(souls) >= beyond.soul_buildup_threshold:
            world.leakage = min(PERCENT, world.leakage + beyond.soul_buildup_leak)


async def harvest_soul(ctx: TickContext, cult: EntityRow, soul: EntityRow) -> None:
    beyond = ctx.rules.beyond
    await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: harvested by {cult.name}.")
    soul_row = await ctx.session.get(SoulRow, soul.id)
    if soul_row is not None:
        soul_row.harvested_by_entity_id = cult.id
    with flowing(FlowCategory.CONVERSION):
        scale_stat(ctx.rules, cult, FOLLOWERS_KEY, beyond.soul_harvest_follower_mult_pct / PERCENT, default=beyond.cult_default_followers)
    shift_bounded(ctx.rules, cult, INFLUENCE_KEY, beyond.soul_harvest_influence_gain, default=beyond.cult_default_influence)
    await EntityRepository(ctx.session).add_flag(cult.id, EntityFlag.SOUL_HARVESTER, ctx.epoch)
    await record(
        ctx,
        "beyond.soul_harvest",
        roles={IncidentRole.ACTOR: cult.id, IncidentRole.SUBJECT: soul.id},
        facts={"follower_pct": beyond.soul_harvest_follower_mult_pct, "influence_gain": beyond.soul_harvest_influence_gain},
        steps=(StepDraft(StepAction.DRAW_POWER, actor=cult.id, target=soul.id, outcome=StepOutcome.SUCCESS),),
        place=soul.location_id,
        world_id=cult.world_id,
    )


async def soul_harvest(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    rng = ctx.rng("harvest")
    harvested = 0
    for cult in unheld(await canon(ctx.session, [EntityType.CULT])):
        if stat_or(cult, ZEAL_KEY, 0) < beyond.soul_harvest_min_zealotry:
            continue
        souls = unheld(await canon(ctx.session, [EntityType.SPIRIT], cult.world_id))
        if souls and rng.chance(beyond.soul_harvest_chance):
            await harvest_soul(ctx, cult, souls[0])
            harvested += 1
    return harvested


async def planet_acts(ctx: TickContext, world: WorldRow) -> str | None:
    beyond = ctx.rules.beyond
    rng = ctx.rng(f"planet.{world.id}")
    knowledge = await KnowledgeMap.load(ctx.session)
    communities = await canon(ctx.session, COMMUNITY_TYPES, world.id)
    cursed = await flags_by_entity(ctx.session, EntityFlag.CURSED)
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_PLANET)
    polluter = next((item for item in communities if knowledge.knows(item.id, KnowledgeBranch.FORBIDDEN) or item.id in cursed), None)
    protected = next((item for item in communities if item.id in devoted), None)
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    if polluter is not None and rng.chance(beyond.planet_punish_chance):
        shaken = (
            polluter
            if polluter.entity_type is EntityType.SETTLEMENT
            else await ctx.session.get(EntityRow, polluter.location_id)
            if polluter.location_id
            else polluter
        )
        place = shaken or polluter
        await apply_disaster(ctx, place, Disaster.EARTHQUAKE, fraction(beyond.planet_quake_severity))
        written = await record(
            ctx,
            "beyond.planet_shook",
            roles={IncidentRole.ACTOR: world.id, IncidentRole.TARGET: polluter.id, IncidentRole.PLACE: place.id},
            facts={"severity": beyond.planet_quake_severity},
            steps=(StepDraft(StepAction.QUAKE, actor=world.id, target=polluter.id, locus_kind=StepLocus.SETTLEMENT, locus_node=place.id),),
            place=place.id,
            world_id=world.id,
        )
        return written.text
    if protected is not None:
        add_prosperity(ctx.rules, protected, beyond.planet_worshipper_prosperity)
        scale_stat(ctx.rules, protected, POPULATION_KEY, beyond.planet_worshipper_population_pct / PERCENT)
        written = await record(
            ctx,
            "beyond.planet_fed",
            roles={IncidentRole.ACTOR: world.id, IncidentRole.BENEFICIARY: protected.id},
            facts={"prosperity_gain": beyond.planet_worshipper_prosperity, "population_pct": beyond.planet_worshipper_population_pct},
            steps=(StepDraft(StepAction.BLOOM, actor=world.id, target=protected.id),),
            world_id=world.id,
        )
        return written.text
    region = rng.pick_or_none(regions)
    if region is None:
        return None
    return await _toggle_skin(ctx, world, region)


async def _toggle_skin(ctx: TickContext, world: WorldRow, region: EntityRow) -> str:
    beyond = ctx.rules.beyond
    repository = EntityRepository(ctx.session)
    danger = stat_or(region, DANGER_KEY, beyond.region_default_danger)
    opening = await repository.has_flag(region.id, EntityFlag.PLANET_CLOSED)
    if opening:
        await repository.remove_flag(region.id, EntityFlag.PLANET_CLOSED)
    else:
        await repository.add_flag(region.id, EntityFlag.PLANET_CLOSED, ctx.epoch)
    shift_bounded(ctx.rules, region, DANGER_KEY, -beyond.planet_close_skin_danger if opening else beyond.planet_close_skin_danger, default=danger)
    action = StepAction.OPEN if opening else StepAction.CLOSE
    written = await record(
        ctx,
        "beyond.planet_opened" if opening else "beyond.planet_closed",
        roles={IncidentRole.ACTOR: world.id, IncidentRole.PLACE: region.id},
        facts={"danger_before": danger, "danger_after": stat_or(region, DANGER_KEY, danger)},
        steps=(StepDraft(action, actor=world.id, locus_kind=StepLocus.REGION, locus_node=region.id),),
        place=region.id,
        world_id=world.id,
    )
    return written.text


async def planet_worship(ctx: TickContext, world: WorldRow) -> int:
    beyond = ctx.rules.beyond
    rng = ctx.rng(f"planet_worship.{world.id}")
    index = await BondIndex.load(ctx.session, [BondKind.WORSHIPS])
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_PLANET)
    godless = [
        item for item in await canon(ctx.session, COMMUNITY_TYPES, world.id) if not index.outgoing(item.id, BondKind.WORSHIPS) and item.id not in devoted
    ]
    turned = 0
    for community in godless[: beyond.planet_worship_candidates]:
        if rng.chance(beyond.planet_worship_chance):
            await EntityRepository(ctx.session).add_flag(community.id, EntityFlag.WORSHIPS_PLANET, ctx.epoch)
            await record(
                ctx,
                "beyond.planet_worship",
                roles={IncidentRole.ACTOR: community.id, IncidentRole.TARGET: world.id},
                steps=(StepDraft(StepAction.PRAY, actor=community.id, target=world.id),),
                world_id=world.id,
            )
            turned += 1
    return turned


async def planetary_consciousness(ctx: TickContext) -> None:
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if not is_living(world.world_type):
            continue
        if not ctx.rng(f"planet_roll.{world.id}").chance(ctx.rules.beyond.planet_acts_chance):
            continue
        await planet_acts(ctx, world)
        await planet_worship(ctx, world)


async def raise_archive(ctx: TickContext) -> EntityRow | None:
    beyond = ctx.rules.beyond
    worlds = [world for world in await WorldRepository(ctx.session).reachable_worlds() if not held(world.id)]
    regions = [region for world in worlds for region in unheld(await canon(ctx.session, [EntityType.REGION], world.id))]
    if not regions:
        return None
    region = max(regions, key=lambda item: (stat_or(item, "magic", 0), -item.id))
    archive = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name="Cosmic Archive",
            entity_type=EntityType.STRUCTURE,
            body="A place that gathers the knowledge of all worlds by itself. Nobody knows who made it; what it holds grows every epoch.",
            stats=StructureStats(splendor=beyond.archive_splendor, durability=beyond.archive_durability, function=beyond.archive_function),
            power=beyond.archive_power,
            world_id=region.world_id,
            location_id=region.id,
            subtype="cosmic archive",
            engine_kind=EngineKind.COSMIC_ARCHIVE,
            flags=(EntityFlag.WONDER,),
        ),
    )
    await ensure_profile(ctx.session, ctx.rules, ctx.epoch, archive, StructureKind.COSMIC_ARCHIVE)
    await record(
        ctx,
        "beyond.archive_appeared",
        roles={IncidentRole.PRODUCT: archive.id, IncidentRole.PLACE: region.id},
        facts={"worlds_known": await worlds_known(ctx.session)},
        place=region.id,
        world_id=region.world_id,
    )
    return archive


async def read_archive(ctx: TickContext, archive: EntityRow, community: EntityRow) -> EntityRow | None:
    lost = await flags_by_entity(ctx.session, EntityFlag.LOST)
    knowledge = await KnowledgeMap.load(ctx.session)
    known_ids = {bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(community.id, BondKind.KNOWS)}
    techs = [item for item in unheld(await canon(ctx.session, [EntityType.KNOWLEDGE])) if item.id not in lost and item.id not in known_ids]
    if not techs or not knowledge.knows(community.id, KnowledgeBranch.WRITING):
        return None
    tech = techs[0]
    await BondRepository(ctx.session).connect(BondDraft(community.id, tech.id, BondKind.KNOWS, ctx.epoch, "From the Cosmic Archive"))
    shift_bounded(ctx.rules, tech, SPREAD_KEY, ctx.rules.intervention_effects.knowledge_spread_gain)
    if await ctx.session.get(ArchiveHoldingRow, (archive.id, tech.id)) is None:
        ctx.session.add(ArchiveHoldingRow(archive_entity_id=archive.id, knowledge_entity_id=tech.id, reader_entity_id=community.id, epoch=ctx.epoch))
    await record(
        ctx,
        "beyond.archive_read",
        roles={IncidentRole.LEARNER: community.id, IncidentRole.PRODUCT: tech.id, IncidentRole.PLACE: archive.id},
        facts={"spread_gain": ctx.rules.intervention_effects.knowledge_spread_gain},
        steps=(
            StepDraft(
                StepAction.READ,
                actor=community.id,
                target=archive.id,
                instrument_kind=InstrumentKind.TEXT,
                instrument_node=archive.id,
                record_table=ArchiveHoldingRow.__tablename__,
                record_key=f"{archive.id}.{tech.id}",
            ),
            StepDraft(StepAction.LEARN, actor=community.id, target=tech.id),
        ),
        place=archive.id,
        world_id=archive.world_id,
    )
    return tech


async def cosmic_archive(ctx: TickContext) -> None:
    beyond = ctx.rules.beyond
    rng = ctx.rng("archive")
    archive = await live_archive(ctx.session)
    existing = await ctx.session.scalar(
        select(EntityRow.id).where(EntityRow.engine_kind == EngineKind.COSMIC_ARCHIVE, EntityRow.status == EntityStatus.CANON).limit(1)
    )
    if existing is None and await worlds_known(ctx.session) >= beyond.archive_min_worlds and rng.chance(beyond.archive_appear_chance):
        archive = await raise_archive(ctx)
    if archive is not None:
        knowledge = await KnowledgeMap.load(ctx.session)
        readers = [item for item in unheld(await canon(ctx.session, COMMUNITY_TYPES, archive.world_id)) if knowledge.knows(item.id, KnowledgeBranch.WRITING)]
        for community in readers[: beyond.archive_seekers_cap]:
            if rng.chance(beyond.archive_knowledge_chance):
                await read_archive(ctx, archive, community)
    await archive_burned(ctx)


async def archive_burned(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    burned = await flags_by_entity(ctx.session, EntityFlag.BURNED)
    statement = select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_ARCHIVE, EntityRow.status != EntityStatus.CANON).order_by(EntityRow.id)
    lost = 0
    for archive in list(await ctx.session.scalars(statement)):
        if archive.id in burned:
            continue
        await EntityRepository(ctx.session).add_flag(archive.id, EntityFlag.BURNED, ctx.epoch)
        with explaining():
            burned_works = await _burn_holdings(ctx, archive)
            lost += burned_works
            await record(
                ctx,
                "beyond.archive_burned",
                roles={IncidentRole.SUBJECT: archive.id},
                facts={"loss_pct": beyond.archive_burn_loss_pct, "works_lost": burned_works},
                place=archive.location_id,
                world_id=archive.world_id,
            )
    return lost


async def _burn_holdings(ctx: TickContext, archive: EntityRow) -> int:
    holdings = list(
        await ctx.session.scalars(
            select(ArchiveHoldingRow).where(ArchiveHoldingRow.archive_entity_id == archive.id).order_by(ArchiveHoldingRow.knowledge_entity_id)
        )
    )
    rng = ctx.rng("archive_burn")
    chosen = rng.sample(holdings, len(holdings) * ctx.rules.beyond.archive_burn_loss_pct // PERCENT)
    bonds = BondRepository(ctx.session)
    closed = 0
    for holding in chosen:
        if holding.reader_entity_id is None:
            continue
        closed += await bonds.close_between(holding.reader_entity_id, holding.knowledge_entity_id, [BondKind.KNOWS], ctx.epoch, "burned with the archive")
    return closed


async def cosmic_plague(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    rng = ctx.rng("plague")
    infected = await flags_by_entity(ctx.session, EntityFlag.COSMIC_PLAGUE)
    statement = select(JourneyRow).where(
        JourneyRow.status == JourneyStatus.ARRIVED, JourneyRow.result_entity_id.is_not(None), JourneyRow.start_epoch >= ctx.epoch - beyond.cosmic_plague_max_age
    )
    count = 0
    for journey in list(await ctx.session.scalars(statement.order_by(JourneyRow.id))):
        place = await ctx.session.get(EntityRow, journey.result_entity_id)
        if place is None or place.status is not EntityStatus.CANON or place.id in infected or held(place.id) or not rng.chance(beyond.cosmic_plague_chance):
            continue
        await infect(ctx, place, journey.origin_world_id, journey.incident_id)
        infected.add(place.id)
        count += 1
    return count


async def infect(ctx: TickContext, place: EntityRow, origin: int | None = None, cause: int | None = None) -> None:
    await apply_disaster(ctx, place, Disaster.PLAGUE, fraction(ctx.rules.beyond.cosmic_plague_severity))
    await EntityRepository(ctx.session).add_flag(place.id, EntityFlag.COSMIC_PLAGUE, ctx.epoch)
    await record(
        ctx,
        "beyond.cosmic_plague",
        roles={IncidentRole.PLACE: place.id, IncidentRole.ORIGIN: origin},
        facts={"severity": ctx.rules.beyond.cosmic_plague_severity},
        place=place.id,
        cause=cause,
        world_id=place.world_id,
    )


async def void_storm(ctx: TickContext) -> str | None:
    rng = ctx.rng("void_storm")
    if not rng.chance(ctx.rules.beyond.void_storm_chance):
        return None
    forgotten = set(await ctx.session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))
    statement = select(RouteRow).where(RouteRow.active.is_(True), RouteRow.method != TravelMethod.DIVINE_BRIDGE).order_by(RouteRow.id)
    routes = [
        route
        for route in await ctx.session.scalars(statement)
        if route.world_a_id not in forgotten and route.world_b_id not in forgotten and not held(route.world_a_id, route.world_b_id)
    ]
    route = rng.pick_or_none(routes)
    if route is None:
        return None
    result = await sever_route(ctx, route.id, write=False)
    for world_id in (route.world_a_id, route.world_b_id):
        ctx.session.add(
            SkyEventRow(
                kind=SkyEventKind.VOID_STORM, epoch=ctx.epoch, until_epoch=result.severed_until - 1, world_id=world_id, route_id=route.id, text=result.text
            )
        )
    written = await record(
        ctx,
        "beyond.void_storm",
        roles={IncidentRole.PLACE: [route.world_a_id, route.world_b_id]},
        facts={
            "opens_epoch": result.severed_until,
            "journeys_lost": result.lost,
            "journeys_waiting": result.waiting,
            "routes_revealed": 1 if result.revealed else 0,
        },
        steps=(StepDraft(StepAction.BLOW), StepDraft(StepAction.CLOSE), *((StepDraft(StepAction.REVEAL),) if result.revealed else ())),
    )
    return written.text


async def mirror_birth(ctx: TickContext, dead: EntityRow, region: EntityRow, twin: WorldRow, mirror: WorldRow) -> EntityRow:
    beyond = ctx.rules.beyond
    inverted = {key: PERCENT - stat_or(dead, key, beyond.mirror_default_stat) for key in MIRROR_STATS}
    same_epoch = dead.end_epoch is not None and dead.end_epoch >= ctx.epoch
    when = (
        f"the moment {dead.name} died in {twin.name}, their inverse was born in {mirror.name}"
        if same_epoch
        else f"{dead.name}, who died in {twin.name} in Epoch {dead.end_epoch}, was born inverted in {mirror.name}"
    )
    born = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{dead.name} (mirror)",
            entity_type=EntityType.MORTAL,
            body=f"{when[0].upper()}{when[1:]}. A mortal, not a son of a god.",
            stats=MortalStats(hp=beyond.mirror_hp, age=0, lifespan=stat_or(dead, "lifespan", beyond.mirror_default_lifespan), **inverted),
            power=dead.power_level,
            world_id=mirror.id,
            location_id=region.id,
            subtype="mirror birth",
            engine_kind=EngineKind.MIRROR_BIRTH,
            flags=(EntityFlag.MIRROR,),
        ),
    )
    await EntityRepository(ctx.session).add_flag(dead.id, EntityFlag.MIRROR_BORN, ctx.epoch)
    await BondRepository(ctx.session).connect(BondDraft(born.id, dead.id, BondKind.RELATED, ctx.epoch, ITS_MIRROR))
    await record(
        ctx,
        "beyond.mirror_birth",
        roles={IncidentRole.PREDECESSOR: dead.id, IncidentRole.CHILD: born.id, IncidentRole.PLACE: region.id, IncidentRole.ORIGIN: twin.id},
        facts={"death_epoch": dead.end_epoch if dead.end_epoch is not None else ctx.epoch},
        steps=(StepDraft(StepAction.GIVE_BIRTH, target=born.id, locus_kind=StepLocus.REGION, locus_node=region.id),),
        place=region.id,
        world_id=mirror.id,
    )
    return born


async def mirror_worlds(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    born_flags = await flags_by_entity(ctx.session, EntityFlag.MIRROR_BORN)
    rng = ctx.rng("mirror")
    births = 0
    for mirror in await WorldRepository(ctx.session).reachable_worlds():
        if not is_mirror(mirror.world_type) or mirror.mirror_twin_id is None:
            continue
        twin = await ctx.session.get(WorldRow, mirror.mirror_twin_id)
        regions = await canon(ctx.session, [EntityType.REGION], mirror.id)
        if twin is None or not regions:
            continue
        statement = select(EntityRow).where(
            EntityRow.world_id == twin.id,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.end_epoch >= ctx.epoch - RECENT_DEATH_EPOCHS,
        )
        dead = [item for item in await ctx.session.scalars(statement.order_by(EntityRow.end_epoch, EntityRow.id)) if item.id not in born_flags]
        cap = scaled_cap(beyond.mirror_births_cap, beyond.mirror_births_community_divisor, await count_communities(ctx.session, twin.id))
        for mortal in dead[:cap]:
            await mirror_birth(ctx, mortal, rng.pick(regions), twin, mirror)
            births += 1
    return births


async def cosmic_court(ctx: TickContext, traitor_id: int, victim_id: int) -> str | None:
    beyond = ctx.rules.beyond
    if await worlds_known(ctx.session) < MULTI_WORLD_COSMOS:
        return None
    traitor = await _require(ctx.session, traitor_id, "No such oathbreaker.")
    victim = await ctx.session.get(EntityRow, victim_id)
    repository = EntityRepository(ctx.session)
    await repository.add_flag(traitor.id, EntityFlag.OATHBREAKER, ctx.epoch)
    await repository.add_flag(traitor.id, EntityFlag.CURSED, ctx.epoch)
    atlas = await RegionAtlas.load(ctx.session)
    neighbours = [
        item
        for item in await canon(ctx.session, COMMUNITY_TYPES, traitor.world_id)
        if item.id not in (traitor.id, victim_id) and atlas.distance(traitor.id, item.id) <= beyond.oathbreaker_neighbor_distance
    ]
    judged = neighbours[: beyond.oathbreaker_neighbors]
    for neighbour in judged:
        await change_relation(ctx, traitor.id, neighbour.id, -beyond.oathbreaker_relation_loss, MemoryKind.BROKE_OATH, note="broke an oath")
    written = await record(
        ctx,
        "beyond.cosmic_court",
        roles={
            IncidentRole.ACCUSED: traitor.id,
            IncidentRole.VICTIM: victim.id if victim is not None else None,
            IncidentRole.WITNESS: [item.id for item in judged],
        },
        facts={"neighbours": len(judged), "relation_loss": beyond.oathbreaker_relation_loss},
        steps=(StepDraft(StepAction.JUDGE, target=traitor.id, outcome=StepOutcome.SUCCESS), StepDraft(StepAction.CURSE, target=traitor.id)),
        world_id=traitor.world_id,
    )
    return written.text


async def pardon(ctx: TickContext, entity_id: int) -> str:
    entity = await _require(ctx.session, entity_id, "No such record.")
    repository = EntityRepository(ctx.session)
    lifted = 0
    for flag in (EntityFlag.OATHBREAKER, EntityFlag.EXILE, EntityFlag.CURSED):
        if await repository.has_flag(entity.id, flag):
            lifted += 1
        await repository.remove_flag(entity.id, flag)
    scope = current_scope()
    written = await record(
        ctx,
        "beyond.pardon",
        roles={IncidentRole.SUBJECT: entity.id, IncidentRole.AUTHORITY: scope.actor_node_id if scope is not None else None},
        facts={"lifted": lifted},
        steps=(StepDraft(StepAction.PARDON, target=entity.id),),
        world_id=entity.world_id,
    )
    return written.text


async def make_immortal(ctx: TickContext, mortal: EntityRow) -> None:
    await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.IMMORTAL, ctx.epoch)
    angered = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE)):
        son.wrath = min(PERCENT, son.wrath + ctx.rules.beyond.immortality_son_wrath)
        angered += 1
    await record(
        ctx,
        "beyond.immortal",
        roles={IncidentRole.SUBJECT: mortal.id},
        facts={"sons_angered": angered, "wrath_gain": ctx.rules.beyond.immortality_son_wrath},
        place=mortal.location_id,
        world_id=mortal.world_id,
    )


async def pursuit_of_immortality(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    immortal = await flags_by_entity(ctx.session, EntityFlag.IMMORTAL)
    knowledge = await KnowledgeMap.load(ctx.session)
    rng = ctx.rng("immortality")
    count = 0
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if mortal.id in immortal or stat_or(mortal, "intellect", 0) + stat_or(mortal, "charisma", 0) < beyond.immortality_threshold:
            continue
        if not knowledge.knows(mortal.id, KnowledgeBranch.IMMORTALITY) and not (
            mortal.location_id and knowledge.knows(mortal.location_id, KnowledgeBranch.IMMORTALITY)
        ):
            continue
        if rng.chance(beyond.immortality_chance):
            await make_immortal(ctx, mortal)
            count += 1
    return count


@reads(
    "cult.followers",
    "cult.influence",
    "cult.zeal",
    "knowledge.spread",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.population",
    "table.archive_holdings",
    "table.bonds",
    "table.cosmos",
    "table.entities",
    "table.entity_flags",
    "table.holder_levels",
    "table.journeys",
    "table.legendary_quests",
    "table.name_registry",
    "table.nodes",
    "table.routes",
    "table.souls",
    "table.threads",
    "table.worlds",
)
@writes(
    "cult.followers",
    "cult.influence",
    "settlement.population",
    "table.archive_holdings",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.cosmos",
    "table.entities",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.legendary_quests",
    "table.name_registry",
    "table.routes",
    "table.sky_events",
    "table.souls",
    "table.threads",
    "table.worlds",
)
async def beyond_phase(ctx: TickContext) -> None:
    await soul_buildup(ctx)
    await soul_descent(ctx)
    await soul_harvest(ctx)
    await planetary_consciousness(ctx)
    await cosmic_archive(ctx)
    await cosmic_plague(ctx)
    await void_storm(ctx)
    await mirror_worlds(ctx)
    await legendary_quests(ctx)
    await pursuit_of_immortality(ctx)
    await ctx.session.flush()


async def force_soul_descent(session: AsyncSession, rules: Rules, mortal_id: int) -> EntityRow:
    ctx = await manual_context(session, "descent", rules, key=str(mortal_id))
    mortal = await session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.DEAD:
        raise NotFoundError("No such dead mortal.")
    world = await session.get(WorldRow, mortal.world_id)
    regions = await realm_regions(session, world) if world is not None else []
    if not regions:
        raise ValidationFailedError("This world has no realm of the dead for the soul to descend to.")
    return await descend_soul(ctx, mortal, ctx.rng("manual_descent").pick(regions))


async def order_soul_harvest(session: AsyncSession, rules: Rules, cult_id: int, soul_id: int) -> None:
    ctx = await manual_context(session, "harvest", rules, key=f"{cult_id}:{soul_id}")
    cult = await _require(session, cult_id, "No such cult.")
    soul = await _require(session, soul_id, "No such soul.")
    if cult.entity_type is not EntityType.CULT or soul.entity_type is not EntityType.SPIRIT:
        raise ValidationFailedError("Only a cult can harvest a soul.")
    await harvest_soul(ctx, cult, soul)


async def order_planet_act(session: AsyncSession, rules: Rules, world_id: int) -> str | None:
    ctx = await manual_context(session, "planet", rules, key=str(world_id))
    world = await session.get(WorldRow, world_id)
    if world is None or not is_living(world.world_type):
        raise ValidationFailedError("Only a living planet can stir.")
    return await planet_acts(ctx, world)


async def order_archive(session: AsyncSession, rules: Rules) -> EntityRow | None:
    ctx = await manual_context(session, "archive", rules)
    if await live_archive(session) is not None:
        raise ValidationFailedError("The Cosmic Archive already stands.")
    return await raise_archive(ctx)


async def order_archive_reading(session: AsyncSession, rules: Rules, community_id: int) -> EntityRow | None:
    ctx = await manual_context(session, "archive_reading", rules, key=str(community_id))
    archive = await live_archive(session)
    if archive is None:
        raise ValidationFailedError("There is no Cosmic Archive.")
    return await read_archive(ctx, archive, await _require(session, community_id, "No such community."))


async def order_cosmic_plague(session: AsyncSession, rules: Rules, place_id: int) -> None:
    await infect(await manual_context(session, "plague", rules, key=str(place_id)), await _require(session, place_id, "No such place."))


async def order_mirror_birth(session: AsyncSession, rules: Rules, mortal_id: int) -> EntityRow:
    ctx = await manual_context(session, "mirror", rules, key=str(mortal_id))
    dead = await session.get(EntityRow, mortal_id)
    if dead is None or dead.entity_type is not EntityType.MORTAL or dead.status is not EntityStatus.DEAD:
        raise NotFoundError("No such dead mortal.")
    mirror = await session.scalar(select(WorldRow).where(WorldRow.mirror_twin_id == dead.world_id).order_by(WorldRow.id).limit(1))
    twin = await session.get(WorldRow, dead.world_id)
    regions = await canon(session, [EntityType.REGION], mirror.id) if mirror is not None else []
    if mirror is None or twin is None or not regions:
        raise ValidationFailedError("No mirror world reflects this mortal's world.")
    return await mirror_birth(ctx, dead, ctx.rng("manual_mirror").pick(regions), twin, mirror)


async def abandon_legendary_quest(session: AsyncSession, rules: Rules, thread_id: int, by: str) -> str:
    return await abandon_quest(await manual_context(session, "abandon_quest", rules, key=str(thread_id)), thread_id, by)


async def set_immortal(session: AsyncSession, rules: Rules, mortal_id: int, *, immortal: bool) -> EntityRow:
    ctx = await manual_context(session, "immortal", rules, key=str(mortal_id))
    mortal = await _require(session, mortal_id, "No such mortal.")
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can be made immortal.")
    if immortal:
        await make_immortal(ctx, mortal)
    else:
        await EntityRepository(session).remove_flag(mortal.id, EntityFlag.IMMORTAL)
    return mortal


async def run_beyond_phase(session: AsyncSession, rules: Rules) -> None:
    await beyond_phase(await manual_context(session, "beyond", rules))


PHASES = (Phase("beyond", beyond_phase),)
