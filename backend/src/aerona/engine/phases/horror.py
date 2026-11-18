from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import RouteClosure
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import OuterBeingStats, revised
from aerona.engine.context import TickContext
from aerona.engine.cosmos.horror_model import HorrorSpec, drawn_spec, horror_event, keep_horrors, raise_horror, unleash
from aerona.engine.cosmos.leak import apply_leak, leak_cap, leak_delta, record_breakdown
from aerona.engine.cosmos.phenomena import phenomenon_sanity
from aerona.engine.cosmos.placement import world_pull
from aerona.engine.cosmos.sanity import sanity_of, shift_sanity
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.cosmos.worldlife import hot_regions
from aerona.engine.divine.outer import breach_pressure, found_outer_cult, open_breaches, outer_profile
from aerona.engine.divine.wounds import sanity_ceiling
from aerona.engine.environment.book import scar_region
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.doom import doom_share
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import BondIndex, canon, connect, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat, stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.storyteller.pace import paced_key
from aerona.rules.registry import Rules

SANITY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.CULT, EntityType.FACTION})
LAND_COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
OUTER_PREY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.SPECIES})
MADNESS_DOMAINS = frozenset({Domain.MADNESS, Domain.DREAM, Domain.SLEEP, Domain.SHADOW, Domain.LIES})
INTEREST_KEY = "interest"


class SanityBand(StrEnum):
    CLEAR = "clear"
    CLOUDED = "clouded"
    MAD = "mad"


async def reopen_severed(ctx: TickContext) -> int:
    forgotten = set(await ctx.session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))
    statement = select(RouteRow).where(RouteRow.temp_closed_until_epoch.is_not(None), RouteRow.temp_closed_until_epoch <= ctx.epoch).order_by(RouteRow.id)
    reopened = 0
    for route in list(await ctx.session.scalars(statement)):
        if route.world_a_id in forgotten or route.world_b_id in forgotten:
            continue
        scorched = route.closure is RouteClosure.SCORCHED
        route.active = True
        route.temp_closed_until_epoch = None
        route.closure = None
        reopened += 1
        if scorched:
            await record(
                ctx, "horror.route_cooled", roles={IncidentRole.ORIGIN: route.world_a_id, IncidentRole.DESTINATION: route.world_b_id}, feed=FeedCategory.GATE
            )
        else:
            await record(
                ctx, "horror.route_reopened", roles={IncidentRole.ORIGIN: route.world_a_id, IncidentRole.DESTINATION: route.world_b_id}, feed=FeedCategory.GATE
            )
    return reopened


async def reseal_temporary(ctx: TickContext) -> int:
    statement = select(RouteRow).where(RouteRow.temp_open_until_epoch.is_not(None), RouteRow.temp_open_until_epoch <= ctx.epoch).order_by(RouteRow.id)
    resealed = 0
    for route in list(await ctx.session.scalars(statement)):
        route.active = False
        route.temp_open_until_epoch = None
        route.temp_closed_until_epoch = None
        route.closure = RouteClosure.SEALED
        resealed += 1
        await record(
            ctx, "horror.route_resealed", roles={IncidentRole.ORIGIN: route.world_a_id, IncidentRole.DESTINATION: route.world_b_id}, feed=FeedCategory.GATE
        )
    return resealed


WARNINGS = (
    ("warning_1", "horror.warning_first"),
    ("warning_2", "horror.warning_geometry"),
    ("outer_being_threshold", "horror.warning_tear"),
)


async def tear_land(ctx: TickContext, world_id: int, before: int, after: int) -> None:
    settings = ctx.rules.scars
    gained = after - max(before, settings.leak_wound_threshold)
    if gained <= 0:
        return
    grounds = list(await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world_id)))
    if not grounds:
        return
    torn = max(grounds, key=lambda ground: (ground.magic_density, -ground.entity_id))
    await scar_region(ctx.session, ctx.rules, torn, ScarKind.LEAK_WOUND, round(gained * settings.leak_wound_pct / PERCENT))


async def update_leaks(ctx: TickContext, knowledge: KnowledgeMap) -> None:
    share = await doom_share(ctx.session, ctx.rules)
    horror = ctx.rules.cosmic_horror
    for world in await WorldRepository(ctx.session).all_worlds():
        if held(world.id):
            continue
        change = await leak_delta(ctx.session, ctx.rules, world, ctx.epoch, share, knowledge=knowledge)
        record_breakdown(ctx.session, ctx.epoch, world.id, change)
        before = world.leakage
        after = apply_leak(world, change.delta, leak_cap(ctx.rules, world, ctx.epoch))
        await tear_land(ctx, world.id, before, after)
        for field_name, key in WARNINGS:
            threshold = getattr(horror, field_name)
            if before < threshold <= after:
                await record(
                    ctx,
                    key,
                    roles={IncidentRole.SUBJECT: world.id},
                    facts={"threshold": threshold, "leakage": after},
                    feed=FeedCategory.LEAK,
                    world_id=world.id,
                )
    await ctx.session.flush()


@dataclass(frozen=True)
class SanityContext:
    leaks: dict[int, int]
    outer_worlds: set[int]
    void_erosion: dict[int, int]
    worshipping: set[int]
    knowledge: KnowledgeMap
    breaches: dict[int, int] = field(default_factory=dict)
    haunting: dict[int, int] = field(default_factory=dict)


async def _sanity_context(ctx: TickContext, knowledge: KnowledgeMap) -> SanityContext:
    worlds = await WorldRepository(ctx.session).all_worlds()
    stars = {star.id: star.star_type for star in await ctx.session.scalars(select(StarRow))}
    outer = {entity.world_id for entity in await canon(ctx.session, [EntityType.OUTER_BEING])}
    index = await BondIndex.load(ctx.session, [BondKind.WORSHIPS])
    return SanityContext(
        leaks={world.id: world.leakage for world in worlds},
        outer_worlds=outer,
        void_erosion={
            world.id: (await view_of(ctx.session, ctx.rules, world.id)).sanity_erosion
            + (star_mechanics(stars[world.star_id]).sanity_erosion(ctx.rules) if world.star_id in stars else 0)
            + (await world_pull(ctx.session, ctx.rules, world)).sanity
            for world in worlds
        },
        worshipping={bond.source_node_id for bond in index.bonds},
        knowledge=knowledge,
        breaches=await breach_pressure(ctx),
        haunting=await phenomenon_sanity(ctx),
    )


async def sanity_drift(ctx: TickContext, entity: EntityRow, scene: SanityContext) -> int:
    horror = ctx.rules.cosmic_horror
    erosion = scene.leaks.get(entity.world_id, 0) / horror.leak_erosion_divisor + scene.void_erosion.get(entity.world_id, 0)
    erosion += horror.forbidden_erosion if scene.knowledge.knows(entity.id, KnowledgeBranch.FORBIDDEN) else 0
    erosion += horror.outer_being_erosion if entity.world_id in scene.outer_worlds else 0
    erosion += scene.breaches.get(entity.location_id or entity.id, 0) * ctx.rules.outer_beings.breach_sanity_pct / PERCENT
    erosion += scene.haunting.get(entity.location_id or entity.id, 0)
    erosion *= await ctx.hook_easing(entity.id, DomainHook.SANITY_WARD) * await ctx.hook_factor(entity.id, DomainHook.FRENZY)
    repair: float = horror.medicine_repair if scene.knowledge.knows(entity.id, KnowledgeBranch.MEDICINE) else 0
    if entity.entity_type in LAND_COMMUNITIES:
        repair += (await class_shares(ctx.session, ctx.rules, entity.id))[SocialClass.PRIEST] / horror.priest_repair_divisor
    repair += horror.worship_repair if entity.id in scene.worshipping else 0
    repair += horror.sanity_self_repair
    return round_half_up(sanity_of(ctx.rules, entity) - erosion + repair)


async def _whisperers_born(ctx: TickContext, entity: EntityRow) -> bool:
    if await EntityRepository(ctx.session).has_flag(entity.id, EntityFlag.WHISPER_SOURCE):
        return True
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    bonds = BondRepository(ctx.session)
    related = [*await bonds.incoming(entity.id, BondKind.RELATED), *await bonds.incoming(entity.id, BondKind.DESCENDS_FROM)]
    for bond in related:
        cult = await ctx.session.get(EntityRow, bond.source_node_id)
        if cult is not None and cult.id in cults and cult.status is EntityStatus.CANON:
            return True
    return False


async def birth_whisperers(ctx: TickContext, entity: EntityRow) -> EntityRow:
    await EntityRepository(ctx.session).add_flag(entity.id, EntityFlag.WHISPER_SOURCE, ctx.epoch)
    cult = await found_outer_cult(ctx, entity)
    await record(ctx, "horror.whisperers", roles={IncidentRole.SUBJECT: [entity.id, cult.id]}, feed=FeedCategory.LEAK)
    return cult


async def _madness(ctx: TickContext, entity: EntityRow, outer_cults: set[int]) -> None:
    horror = ctx.rules.cosmic_horror
    rng = ctx.rng("madness")
    if not rng.chance(horror.madness_chance):
        return
    eligible = entity.entity_type in LAND_COMMUNITIES and entity.id not in outer_cults and not await _whisperers_born(ctx, entity)
    if eligible and rng.chance(horror.whisperers_chance):
        await birth_whisperers(ctx, entity)
        return
    if stat(entity, POPULATION_KEY) is not None:
        scale_stat(ctx.rules, entity, POPULATION_KEY, (PERCENT - horror.madness_population_loss_pct) / PERCENT)
        await record(ctx, "horror.madness_epidemic", roles={IncidentRole.SUBJECT: entity.id})


async def update_sanity(ctx: TickContext, knowledge: KnowledgeMap) -> None:
    horror = ctx.rules.cosmic_horror
    scene = await _sanity_context(ctx, knowledge)
    outer_cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    for entity in await canon(ctx.session, SANITY_TYPES):
        if held(entity.id):
            continue
        before = sanity_of(ctx.rules, entity)
        after = clamp_percent(await sanity_drift(ctx, entity, scene))
        if entity.sanity != after:
            entity.sanity = after
        if before >= horror.clouding_threshold > after:
            await record(ctx, "horror.clouding", roles={IncidentRole.SUBJECT: entity.id})
        if after < horror.madness_threshold:
            await _madness(ctx, entity, outer_cults)
    await ctx.session.flush()


async def feed_madness_sons(ctx: TickContext) -> int:
    horror = ctx.rules.cosmic_horror
    worlds = await WorldRepository(ctx.session).all_worlds()
    average = sum(world.leakage for world in worlds) / len(worlds) if worlds else 0
    gain = round(average / horror.madness_son_essence_divisor)
    if not gain:
        return 0
    fed = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        if not set(son.domains) & MADNESS_DOMAINS:
            continue
        son.essence += gain
        son.existence = min(PERCENT_MAX, son.existence + horror.madness_son_existence_gain)
        fed += 1
    return fed


def son_sanity(rules: Rules, son: SonRow) -> int:
    return son.sanity if son.sanity is not None else rules.cosmic_horror.son_default_sanity


def son_sanity_band(rules: Rules, son: SonRow) -> SanityBand:
    value = son_sanity(rules, son)
    if value < rules.cosmic_horror.son_madness_threshold:
        return SanityBand.MAD
    if value < rules.cosmic_horror.son_clouding_threshold:
        return SanityBand.CLOUDED
    return SanityBand.CLEAR


async def _son_erosion(ctx: TickContext, son: SonRow, scene: SanityContext) -> float:
    horror = ctx.rules.cosmic_horror
    world_id = son.current_world_id
    erosion = scene.leaks.get(world_id, 0) / horror.son_leak_erosion_divisor if world_id is not None else 0.0
    erosion += horror.son_outer_erosion if world_id in scene.outer_worlds else 0
    bargains = list(await ctx.session.scalars(select(OuterBargainRow.son_id).where(OuterBargainRow.son_id == son.id)))
    erosion += len(bargains) * horror.son_bargain_erosion
    believers = [bond.source_node_id for bond in await BondRepository(ctx.session).incoming(son.id, BondKind.WORSHIPS)]
    erosion += sum(1 for believer in believers if scene.knowledge.knows(believer, KnowledgeBranch.FORBIDDEN)) * horror.son_forbidden_erosion
    if set(son.domains) & MADNESS_DOMAINS:
        erosion *= horror.son_madness_resistance_pct / PERCENT
    return erosion


async def update_son_sanity(ctx: TickContext, knowledge: KnowledgeMap) -> int:
    horror = ctx.rules.cosmic_horror
    scene = await _sanity_context(ctx, knowledge)
    changed = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        before = son_sanity(ctx.rules, son)
        after = clamp_percent(before - await _son_erosion(ctx, son, scene) + horror.son_sanity_repair)
        after = min(after, await sanity_ceiling(ctx.session, son.id, ctx.rules.divine_wounds.void_floor_pct))
        if after == son.sanity:
            continue
        son.sanity = after
        changed += 1
        if before >= horror.son_madness_threshold > after:
            await record(ctx, "horror.son_mad", roles={IncidentRole.SUBJECT: son.id}, facts={"sanity": after}, kind=ChronicleKind.HORROR, son_id=son.id)
        elif before >= horror.son_clouding_threshold > after:
            await record(ctx, "horror.son_clouded", roles={IncidentRole.SUBJECT: son.id}, facts={"sanity": after}, kind=ChronicleKind.HORROR, son_id=son.id)
    return changed


async def summon_outer_being(ctx: TickContext, world: WorldRow) -> EntityRow | None:
    horror = ctx.rules.cosmic_horror
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    if not regions:
        return None
    hot = set(await hot_regions(ctx, world.id))
    region = max(regions, key=lambda item: (item.id in hot, stat_or(item, "danger", 0), -item.id))
    rng = ctx.rng("outer")
    being = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The outer being of {world.name}",
            entity_type=EntityType.OUTER_BEING,
            body=f"A being from outside the cosmos that entered {world.name}.",
            stats=OuterBeingStats(
                size=clamp_percent(horror.outer_being_size_base + rng.die(horror.outer_being_size_die)),
                interest=clamp_percent(horror.outer_being_interest_base + rng.die(horror.outer_being_interest_die)),
                influence=clamp_percent(horror.outer_being_influence_base + rng.die(horror.outer_being_influence_die)),
            ),
            power=horror.outer_being_power,
            world_id=world.id,
            location_id=region.id,
            subtype="the unnamed",
            flags=(EntityFlag.NAMELESS,),
        ),
    )
    world.leakage = max(0, world.leakage - horror.outer_being_entry_leak_drop)
    profile = await outer_profile(ctx, being)
    await open_breaches(ctx, being, profile)
    await record(
        ctx,
        "horror.outer_entered",
        roles={IncidentRole.SUBJECT: being.id, IncidentRole.DESTINATION: world.id, IncidentRole.PLACE: region.id},
        place=region.id,
        destination=region.id,
        kind=ChronicleKind.OUTER_BEING,
        world_id=world.id,
        feed=FeedCategory.LEAK,
    )
    return being


async def outer_arrivals(ctx: TickContext) -> int:
    horror = ctx.rules.cosmic_horror
    present = {entity.world_id for entity in await canon(ctx.session, [EntityType.OUTER_BEING])}
    rng = ctx.rng("outer_roll")
    arrived = 0
    for world in await WorldRepository(ctx.session).all_worlds():
        if world.leakage < horror.outer_being_threshold or world.id in present or not rng.chance(horror.outer_being_chance):
            continue
        if await summon_outer_being(ctx, world) is not None:
            arrived += 1
    return arrived


async def outer_influence(ctx: TickContext) -> None:
    horror = ctx.rules.cosmic_horror
    rng = ctx.rng("outer_influence")
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    repository = EntityRepository(ctx.session)
    for being in await canon(ctx.session, [EntityType.OUTER_BEING]):
        interest = clamp_percent(stat_or(being, INTEREST_KEY, horror.default_interest) + rng.die(horror.interest_die) - horror.interest_decay)
        being.stats = revised(being.stats, {INTEREST_KEY: interest})
        neighbours = (
            [item for item in await repository.contents(being.location_id) if item.entity_type in OUTER_PREY_TYPES] if being.location_id is not None else []
        )
        reach = horror.outer_being_victims + (stat_or(being, "size", 0) // horror.outer_being_size_per_victim if horror.outer_being_size_per_victim else 0)
        for victim in neighbours[:reach]:
            shift_sanity(ctx.rules, victim, -round(interest / horror.outer_being_sanity_divisor))
            if victim.entity_type is EntityType.SPECIES and rng.probability(interest / horror.outer_being_mutation_divisor):
                await repository.add_flag(victim.id, EntityFlag.MUTATION, ctx.epoch)
        for cult in await canon(ctx.session, [EntityType.CULT], being.world_id):
            if cult.id in cults:
                await connect(ctx.session, cult.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="without speaking its name")
    await ctx.session.flush()


async def spontaneous_horror(ctx: TickContext) -> str | None:
    worlds = await WorldRepository(ctx.session).all_worlds()
    if not worlds:
        return None
    world = max(worlds, key=lambda item: (item.leakage, -item.id))
    if held(world.id):
        return None
    horror = ctx.rules.cosmic_horror
    chance = world.leakage / horror.horror_event_divisor + await doom_share(ctx.session, ctx.rules) / horror.apocalypse_event_divisor
    chance = await paced_key(ctx, world.id, "outer_horror", chance)
    rng = ctx.rng("horror_event")
    if not rng.probability(chance):
        return None
    return await horror_event(ctx, drawn_spec(ctx, world), world)


@reads(
    "people.population",
    "settlement.population",
    "table.addictions",
    "table.bonds",
    "table.breach_points",
    "table.community_societies",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.horror_events",
    "table.lexemes",
    "table.memories",
    "table.nodes",
    "table.outer_bargains",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.rifts",
    "table.routes",
    "table.sons",
    "table.stars",
    "table.storytellers",
    "table.world_domain_hooks",
    "table.world_type_profiles",
    "table.worlds",
)
@writes(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.horror_events",
    "table.incident_participants",
    "table.incidents",
    "table.lexemes",
    "table.memories",
    "table.mortal_profiles",
    "table.routes",
    "table.sons",
    "table.stars",
    "table.world_leak_items",
    "table.worlds",
)
async def horror_phase(ctx: TickContext) -> None:
    await reopen_severed(ctx)
    await reseal_temporary(ctx)
    knowledge = await KnowledgeMap.load(ctx.session)
    await update_leaks(ctx, knowledge)
    await update_sanity(ctx, knowledge)
    await feed_madness_sons(ctx)
    await update_son_sanity(ctx, knowledge)
    await outer_arrivals(ctx)
    await outer_influence(ctx)
    ctx.count("horror_lingering", await keep_horrors(ctx))
    await spontaneous_horror(ctx)
    await ctx.session.flush()


async def _world(session: AsyncSession, world_id: int) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} was forgotten; nothing can be ordered there.")
    return world


async def order_horror_event(session: AsyncSession, rules: Rules, world_id: int, spec: HorrorSpec) -> tuple[HorrorEventRow, str]:
    ctx = await manual_context(session, "horror_event", rules, key=f"{world_id}:{spec.target.value}:{spec.effect.value}")
    world = await _world(session, world_id)
    row = await raise_horror(ctx, world, spec)
    return row, await unleash(ctx, world, row)


async def order_outer_being(session: AsyncSession, rules: Rules, world_id: int) -> EntityRow:
    ctx = await manual_context(session, "summon_outer", rules, key=str(world_id))
    being = await summon_outer_being(ctx, await _world(session, world_id))
    if being is None:
        raise ValidationFailedError("A world without regions has nowhere for it to enter.")
    return being


async def spawn_outer_cult(session: AsyncSession, rules: Rules, entity_id: int) -> EntityRow:
    ctx = await manual_context(session, "outer_cult", rules, key=str(entity_id))
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in LAND_COMMUNITIES:
        raise NotFoundError("Only a living people or settlement can give birth to such a cult.")
    return await birth_whisperers(ctx, entity)


async def suppress_outer_cult(session: AsyncSession, rules: Rules, cult_id: int) -> EntityRow:
    ctx = await manual_context(session, "suppress_cult", rules, key=str(cult_id))
    cult = await session.get(EntityRow, cult_id)
    if cult is None or cult.status is not EntityStatus.CANON or not await EntityRepository(session).has_flag(cult_id, EntityFlag.OUTER_CULT):
        raise NotFoundError("No such outer cult.")
    return await retire(session, cult, ctx.epoch, f"Epoch {ctx.epoch}: scattered by the creator's hand.", status=EntityStatus.DESTROYED, close_bonds=True)


async def set_son_sanity(session: AsyncSession, son_id: int, value: int) -> SonRow:
    son = await session.get(SonRow, son_id)
    if son is None:
        raise NotFoundError("No such son.")
    son.sanity = clamp_percent(value)
    await session.flush()
    return son


async def run_horror_phase(session: AsyncSession, rules: Rules) -> None:
    await horror_phase(await manual_context(session, "horror", rules))


PHASES = (Phase("horror", horror_phase),)
