from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.bond_texts import ITS_MIRROR
from aerona.constants.cosmos import RECENT_DEATH_EPOCHS
from aerona.constants.units import PERCENT
from aerona.constants.warfare import MULTI_WORLD_COSMOS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import SkyEventRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.society import ArchiveHoldingRow, SoulRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyStatus, TravelMethod
from aerona.domain.enums.world import Discovery, SkyEventKind
from aerona.domain.models.entity_stats import MortalStats, SpeciesStats, SpiritStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.quests import abandon_quest, legendary_quests, live_archive, worlds_known
from aerona.engine.cosmos.routes import sever_route
from aerona.engine.cosmos.world_types import is_living, is_mirror, is_realm_of_dead
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.notes import note
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
from aerona.engine.services.community_relations import change_relation
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


async def soul_bind(ctx: TickContext, soul_id: int, target_id: int, by: str, binder_id: int | None = None) -> EntityRow:
    soul = await ctx.session.get(EntityRow, soul_id)
    if soul is None or soul.status is not EntityStatus.CANON or soul.entity_type is not EntityType.SPIRIT:
        raise NotFoundError("No such free soul.")
    target = await _require(ctx.session, target_id, "No such work.")
    if target.entity_type not in BINDABLE_TYPES:
        raise ValidationFailedError("A soul binds only to an item, a vehicle or a work.")
    await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: bound to {target.name}.", close_bonds=True)
    await BondRepository(ctx.session).connect(BondDraft(soul.id, target.id, BondKind.INSIDE, ctx.epoch, "soul binding", role=BondRole.SPIRIT_BINDING))
    record = await ctx.session.get(SoulRow, soul.id)
    if record is not None:
        record.bound_to_entity_id = target.id
    result = await _golem(ctx, soul, target, binder_id) if target.entity_type is EntityType.STRUCTURE else await _bind_object(ctx, target)
    walked = "; the stone began to walk" if result.id != target.id else ""
    await ctx.chronicle(
        ChronicleKind.SPIRIT, f"{by} bound {soul.name} to {target.name}{walked}.", template_key="beyond.soul_bound", entity_ids=[soul.id, target.id]
    )
    return result


async def _golem(ctx: TickContext, soul: EntityRow, work: EntityRow, binder_id: int | None) -> EntityRow:
    beyond = ctx.rules.beyond
    rng = ctx.rng("golem")
    golem = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{work.name} Golem",
            entity_type=EntityType.SPECIES,
            body=f"{soul.name} was bound to the stone of {work.name} and the stone began to walk.",
            stats=SpeciesStats(
                hp=beyond.golem_hp,
                strength=clamp_percent(beyond.golem_strength_base + rng.die(beyond.golem_strength_die)),
                agility=beyond.golem_agility,
                intelligence=clamp_percent(beyond.golem_intelligence_base + rng.die(beyond.golem_intelligence_die)),
                danger=clamp_percent(beyond.golem_danger_base + rng.die(beyond.golem_danger_die)),
            ),
            power=max(beyond.golem_min_power, work.power_level),
            world_id=work.world_id,
            location_id=work.location_id,
            subtype="golem",
            engine_kind=EngineKind.GOLEM,
            traits=(CreatureTrait.STONESKIN,),
        ),
    )
    if binder_id is not None:
        await BondRepository(ctx.session).connect(BondDraft(binder_id, golem.id, BondKind.TAMED, ctx.epoch, "its own golem"))
    return golem


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
    record = await ctx.session.get(SoulRow, soul.id)
    if record is not None:
        record.harvested_by_entity_id = cult.id
    with flowing(FlowCategory.CONVERSION):
        scale_stat(ctx.rules, cult, FOLLOWERS_KEY, beyond.soul_harvest_follower_mult_pct / PERCENT, default=beyond.cult_default_followers)
    shift_bounded(ctx.rules, cult, INFLUENCE_KEY, beyond.soul_harvest_influence_gain, default=beyond.cult_default_influence)
    await EntityRepository(ctx.session).add_flag(cult.id, EntityFlag.SOUL_HARVESTER, ctx.epoch)
    await note(ctx, f"{cult.name} harvested {soul.name}; the cult's power grew, the dead are restless.", key="beyond.soul_harvest", ids=[cult.id, soul.id])


async def soul_harvest(ctx: TickContext) -> int:
    beyond = ctx.rules.beyond
    rng = ctx.rng("harvest")
    harvested = 0
    for cult in await canon(ctx.session, [EntityType.CULT]):
        if stat_or(cult, ZEAL_KEY, 0) < beyond.soul_harvest_min_zealotry:
            continue
        souls = await canon(ctx.session, [EntityType.SPIRIT], cult.world_id)
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
        await apply_disaster(ctx, shaken or polluter, Disaster.EARTHQUAKE, fraction(beyond.planet_quake_severity))
        return f"{world.name} stirred: the planet shook {polluter.name}, who polluted it."
    if protected is not None:
        add_prosperity(ctx.rules, protected, beyond.planet_worshipper_prosperity)
        scale_stat(ctx.rules, protected, POPULATION_KEY, beyond.planet_worshipper_population_pct / PERCENT)
        return f"{world.name} fed {protected.name}, who worship it: the lands grew warm."
    region = rng.pick_or_none(regions)
    if region is None:
        return None
    return await _toggle_skin(ctx, world, region)


async def _toggle_skin(ctx: TickContext, world: WorldRow, region: EntityRow) -> str:
    beyond = ctx.rules.beyond
    repository = EntityRepository(ctx.session)
    danger = stat_or(region, DANGER_KEY, beyond.region_default_danger)
    if await repository.has_flag(region.id, EntityFlag.PLANET_CLOSED):
        await repository.remove_flag(region.id, EntityFlag.PLANET_CLOSED)
        shift_bounded(ctx.rules, region, DANGER_KEY, -beyond.planet_close_skin_danger, default=danger)
        return f"{world.name} opened {region.name} again."
    await repository.add_flag(region.id, EntityFlag.PLANET_CLOSED, ctx.epoch)
    shift_bounded(ctx.rules, region, DANGER_KEY, beyond.planet_close_skin_danger, default=danger)
    return f"{world.name} closed its skin over {region.name}; entering it is dangerous."


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
            await note(ctx, f"{community.name} began to worship the living planet beneath its feet.", key="beyond.planet_worship", ids=[community.id])
            turned += 1
    return turned


async def planetary_consciousness(ctx: TickContext) -> None:
    for world in await WorldRepository(ctx.session).reachable_worlds():
        if not is_living(world.world_type):
            continue
        if not ctx.rng(f"planet_roll.{world.id}").chance(ctx.rules.beyond.planet_acts_chance):
            continue
        text = await planet_acts(ctx, world)
        if text is not None:
            await note(ctx, text, key="beyond.planet_acts", feed=FeedCategory.WORLD)
        await planet_worship(ctx, world)


async def raise_archive(ctx: TickContext) -> EntityRow | None:
    beyond = ctx.rules.beyond
    regions = [region for world in await WorldRepository(ctx.session).reachable_worlds() for region in await canon(ctx.session, [EntityType.REGION], world.id)]
    if not regions:
        return None
    region = max(regions, key=lambda item: (stat_or(item, "magic", 0), -item.id))
    archive = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name="Cosmic Archive",
            entity_type=EntityType.STRUCTURE,
            body="A place that gathers the knowledge of all worlds by itself. Nobody knows who built it; the shelves grow a little longer every epoch.",
            stats=StructureStats(splendor=beyond.archive_splendor, durability=beyond.archive_durability, function=beyond.archive_function),
            power=beyond.archive_power,
            world_id=region.world_id,
            location_id=region.id,
            subtype="cosmic archive",
            engine_kind=EngineKind.COSMIC_ARCHIVE,
            flags=(EntityFlag.WONDER,),
        ),
    )
    world = await ctx.session.get(WorldRow, region.world_id)
    await note(
        ctx,
        f"In {world.name if world else region.name} an archive gathering the knowledge of all worlds appeared.",
        key="beyond.archive_appeared",
        ids=[archive.id],
    )
    return archive


async def read_archive(ctx: TickContext, archive: EntityRow, community: EntityRow) -> EntityRow | None:
    lost = await flags_by_entity(ctx.session, EntityFlag.LOST)
    knowledge = await KnowledgeMap.load(ctx.session)
    known_ids = {bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(community.id, BondKind.KNOWS)}
    techs = [item for item in await canon(ctx.session, [EntityType.KNOWLEDGE]) if item.id not in lost and item.id not in known_ids]
    if not techs or not knowledge.knows(community.id, KnowledgeBranch.WRITING):
        return None
    tech = techs[0]
    await BondRepository(ctx.session).connect(BondDraft(community.id, tech.id, BondKind.KNOWS, ctx.epoch, "From the Cosmic Archive"))
    shift_bounded(ctx.rules, tech, SPREAD_KEY, ctx.rules.intervention_effects.knowledge_spread_gain)
    if await ctx.session.get(ArchiveHoldingRow, (archive.id, tech.id)) is None:
        ctx.session.add(ArchiveHoldingRow(archive_entity_id=archive.id, knowledge_entity_id=tech.id, reader_entity_id=community.id, epoch=ctx.epoch))
    await note(
        ctx,
        f"{community.name}'s scribes extracted the knowledge of {tech.name} from the Cosmic Archive.",
        key="beyond.archive_read",
        ids=[community.id, tech.id],
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
        readers = [item for item in await canon(ctx.session, COMMUNITY_TYPES, archive.world_id) if knowledge.knows(item.id, KnowledgeBranch.WRITING)]
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
        lost += await _burn_holdings(ctx, archive)
        text = f"The Cosmic Archive burned. {beyond.archive_burn_loss_pct}% of the knowledge it held turned to ash with it; this is the end of an age."
        await ctx.chronicle(ChronicleKind.AGE_CHANGE, text, template_key="beyond.archive_burned", entity_ids=[archive.id])
        await note(ctx, f"The Cosmic Archive burned; {beyond.archive_burn_loss_pct}% of its knowledge was lost.", key="beyond.archive_burned_note")
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
        if place is None or place.status is not EntityStatus.CANON or place.id in infected or not rng.chance(beyond.cosmic_plague_chance):
            continue
        await infect(ctx, place)
        infected.add(place.id)
        count += 1
    return count


async def infect(ctx: TickContext, place: EntityRow) -> None:
    await apply_disaster(ctx, place, Disaster.PLAGUE, fraction(ctx.rules.beyond.cosmic_plague_severity))
    await EntityRepository(ctx.session).add_flag(place.id, EntityFlag.COSMIC_PLAGUE, ctx.epoch)
    await note(
        ctx,
        f"A disease came to {place.name} from another world; no one knows its name.",
        key="beyond.cosmic_plague",
        ids=[place.id],
        feed=FeedCategory.DISASTER,
    )


async def void_storm(ctx: TickContext) -> str | None:
    rng = ctx.rng("void_storm")
    if not rng.chance(ctx.rules.beyond.void_storm_chance):
        return None
    forgotten = set(await ctx.session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))
    statement = select(RouteRow).where(RouteRow.active.is_(True), RouteRow.method != TravelMethod.DIVINE_BRIDGE).order_by(RouteRow.id)
    routes = [route for route in await ctx.session.scalars(statement) if route.world_a_id not in forgotten and route.world_b_id not in forgotten]
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
    text = "A void storm swallowed a hidden route but the route was revealed." if result.revealed else "A void storm swallowed a route."
    await note(ctx, f"{text} {result.text}", key="beyond.void_storm", feed=FeedCategory.GATE)
    return result.text


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
    text = (
        f"{dead.name} died; their mirror was born in {mirror.name}."
        if same_epoch
        else f"The mirror of {dead.name}, who died in Epoch {dead.end_epoch}, was born in {mirror.name}."
    )
    await note(ctx, text, key="beyond.mirror_birth", ids=[dead.id, born.id])
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
    for neighbour in neighbours[: beyond.oathbreaker_neighbors]:
        await change_relation(ctx, traitor.id, neighbour.id, -beyond.oathbreaker_relation_loss, MemoryKind.BROKE_OATH, note="broke an oath")
    victim_name = victim.name if victim is not None else "its ally"
    text = f"Cosmic court (Fate's voice): {traitor.name} broke the oath given to {victim_name}. Verdict: a curse and the distrust of its neighbours."
    await note(ctx, text, key="beyond.cosmic_court", ids=[traitor.id, victim_id], kind=ChronicleKind.COSMIC_LAW)
    return text


async def pardon(ctx: TickContext, entity_id: int, by: str) -> str:
    entity = await _require(ctx.session, entity_id, "No such record.")
    repository = EntityRepository(ctx.session)
    for flag in (EntityFlag.OATHBREAKER, EntityFlag.EXILE, EntityFlag.CURSED):
        await repository.remove_flag(entity.id, flag)
    text = f"{by} pardoned {entity.name}."
    await ctx.chronicle(ChronicleKind.COSMIC_LAW, text, template_key="beyond.pardon", entity_ids=[entity.id])
    return text


async def make_immortal(ctx: TickContext, mortal: EntityRow) -> None:
    await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.IMMORTAL, ctx.epoch)
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE)):
        son.wrath = min(PERCENT, son.wrath + ctx.rules.beyond.immortality_son_wrath)
    text = f"{mortal.name} defeated death: they no longer age. The gods saw this as a threat."
    await ctx.chronicle(ChronicleKind.IMMORTALITY, text, template_key="beyond.immortal", entity_ids=[mortal.id])


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
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.journeys",
    "table.name_registry",
    "table.nodes",
    "table.routes",
    "table.souls",
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
    "table.epoch_year_cursors",
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
)
@writes("cult.followers", "cult.influence", "settlement.population")
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


async def bind_soul(session: AsyncSession, rules: Rules, soul_id: int, target_id: int, by: str, *, binder_id: int | None = None) -> EntityRow:
    return await soul_bind(await manual_context(session, "soul_bind", rules, key=f"{soul_id}:{target_id}"), soul_id, target_id, by, binder_id)


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
