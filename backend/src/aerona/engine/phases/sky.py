from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.worlds import SKY_EVENT_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.storyteller import SpontaneousKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.war import WarEnding
from aerona.domain.enums.world import Discovery, SkyEventKind
from aerona.domain.models.entity_stats import CelestialStats, MortalStats, ProphecyStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import eclipse_period, next_epoch, transit_pairs, transit_phase
from aerona.engine.cosmos.placement import cosmography_of, hidden_sky
from aerona.engine.cosmos.routes import number_word, open_alignment, sever_route, touches
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.cosmos.starlife import flare_weight_pct
from aerona.engine.cosmos.stars import black_sun, flare, require_star, supernova, worlds_of_star
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.cosmos.worlds import align_moons
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import has_technique
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, connect, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import shift_bounded, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.engine.services.war_resolution import settle_peace
from aerona.engine.storyteller.pace import paced
from aerona.engine.structures.readers import strength_at, working
from aerona.rules.registry import Rules

INHABITANT_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL})
RELATED_PLACE_TYPES = frozenset({EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT})
STAR_EVENTS = frozenset({SkyEventKind.SUPERNOVA, SkyEventKind.BLACK_SUN, SkyEventKind.FLARE})
COLLAPSE_EVENTS = frozenset({SkyEventKind.SUPERNOVA, SkyEventKind.BLACK_SUN})
PIETY_KEY = "piety"
CHARISMA_KEY = "charisma"
FERTILITY_KEY = "fertility"


@dataclass(frozen=True)
class SkyOrder:
    world_id: int | None = None
    star_id: int | None = None
    route_id: int | None = None
    duration: int | None = None
    by: str | None = None
    by_id: int | None = None


@dataclass(frozen=True)
class SkyOutcome:
    text: str
    roles: dict[IncidentRole, RoleValue] = field(default_factory=dict)
    facts: dict[str, FactInput] = field(default_factory=dict)


@dataclass(frozen=True)
class SkyEventResult:
    kind: SkyEventKind
    world_id: int | None
    star_id: int | None
    text: str


async def _resolve_world(ctx: TickContext, order: SkyOrder) -> WorldRow | None:
    session = ctx.session
    if order.world_id is not None:
        return await session.get(WorldRow, order.world_id)
    if order.star_id is not None:
        worlds = await worlds_of_star(session, order.star_id)
        if worlds:
            return worlds[0]
    if order.route_id is not None:
        route = await session.get(RouteRow, order.route_id)
        if route is not None:
            return await session.get(WorldRow, route.world_a_id)
    reachable = await WorldRepository(session).reachable_worlds()
    if reachable:
        return ctx.rng("sky_target").pick(reachable)
    first = await CosmosRepository(session).first_world_id()
    return await session.get(WorldRow, first) if first is not None else None


async def eclipse_seers(ctx: TickContext, prophecy: EntityRow, world: WorldRow) -> list[EntityRow]:
    communities = await canon(ctx.session, COMMUNITY_TYPES, world.id)
    ranked = sorted(communities, key=lambda entity: (entity.entity_type is not EntityType.CULT, -(entity.importance or 0), entity.id))
    seers = ranked[: ctx.rules.sky.eclipse_prophet_communities]
    for seer in seers:
        await connect(ctx.session, seer.id, prophecy.id, BondKind.PROPHESIES, ctx.epoch, description="foretold it during the eclipse")
    return seers


async def sky_clarity(ctx: TickContext, world: WorldRow, slot: str) -> float:
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    return ground.clarity(ctx.environment.world_seed, ctx.epoch, world.id, slot) * (1 - await hidden_sky(ctx.session, ctx.rules, world.id))


async def omen_bonus(ctx: TickContext, world_id: int) -> int:
    found = await working(ctx.session, [StructureKind.OBSERVATORY], world_id=world_id)
    return round(max((item.strength for item in found), default=0.0) * ctx.rules.structure_functions.observatory_omen_certainty)


async def _eclipse(ctx: TickContext, world: WorldRow) -> SkyOutcome:
    sky = ctx.rules.sky
    seen = await sky_clarity(ctx, world, "sky.eclipse")
    for entity in await canon(ctx.session, INHABITANT_TYPES, world.id):
        dread = seen * (
            1 - ctx.rules.technique_effects.eclipse_calm_pct / PERCENT if await has_technique(ctx.session, entity.id, Technique.ECLIPSE_PREDICTION) else 1
        )
        dread *= (
            1 - await strength_at(ctx.session, entity.id, [StructureKind.OBSERVATORY]) * ctx.rules.structure_functions.observatory_eclipse_calm_pct / PERCENT
        )
        shift_sanity(ctx.rules, entity, -round(sky.eclipse_sanity_loss * dread))
        shift_bounded(ctx.rules, entity, PIETY_KEY, round(sky.eclipse_piety_gain * dread))
    rng = ctx.rng("eclipse")
    prophecy = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{world.name} Eclipse Prophecy",
            entity_type=EntityType.PROPHECY,
            body=f"A prophecy foretold during the long eclipse over {world.name}.",
            stats=ProphecyStats(certainty=clamp_percent(sky.eclipse_certainty_base + rng.die(sky.eclipse_certainty_die) + await omen_bonus(ctx, world.id))),
            power=sky.eclipse_prophecy_power,
            world_id=world.id,
            subtype="eclipse prophecy",
            engine_kind=EngineKind.ECLIPSE_PROPHECY,
        ),
    )
    seers = await eclipse_seers(ctx, prophecy, world)
    return SkyOutcome(
        f"In {world.name} an eclipse lasted the whole epoch, and a prophecy was made under it.",
        {IncidentRole.PRODUCT: prophecy.id, IncidentRole.TELLER: [seer.id for seer in seers]},
        {"clarity": seen * PERCENT},
    )


async def _comet(ctx: TickContext, world: WorldRow) -> SkyOutcome:
    sky = ctx.rules.sky
    rng = ctx.rng("comet")
    comet = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The Comet in {world.name}'s Sky",
            entity_type=EntityType.CELESTIAL,
            body=f"A comet crossed {world.name}'s sky.",
            stats=CelestialStats(
                brightness=clamp_percent(sky.comet_brightness_base + rng.die(sky.comet_brightness_die)),
                influence=clamp_percent(sky.comet_influence_base + rng.die(sky.comet_influence_die)),
            ),
            power=sky.comet_power,
            world_id=world.id,
            subtype="comet",
            engine_kind=EngineKind.COMET,
            flags=(EntityFlag.OMEN,),
        ),
    )
    local = select(EntityRow.id).where(EntityRow.world_id == world.id)
    statement = select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(local))
    enmities = list(await ctx.session.scalars(statement.order_by(BondRow.id)))
    bond = rng.pick_or_none(enmities)
    if bond is None or not rng.chance(sky.comet_peace_chance * await sky_clarity(ctx, world, "sky.comet")):
        return SkyOutcome(f"A comet appeared in {world.name}'s sky.", {IncidentRole.PRODUCT: comet.id})
    first, second = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
    await settle_peace(ctx, bond.source_node_id, bond.target_node_id, WarEnding.PEACE, "the comet's omen")
    for side in (bond.source_node_id, bond.target_node_id):
        await connect(ctx.session, comet.id, side, BondKind.CAUSED, ctx.epoch, description="its omen was read as peace")
    names = (first.name if first else "one side", second.name if second else "the other")
    return SkyOutcome(
        f"A comet appeared in {world.name}'s sky. Reading the omen as peace, {names[0]} and {names[1]} laid down arms.",
        {IncidentRole.PRODUCT: comet.id, IncidentRole.MEMBER: [bond.source_node_id, bond.target_node_id]},
        {"peace": 1},
    )


async def _alignment(ctx: TickContext, world: WorldRow, star_id: int | None, ordered: bool) -> SkyOutcome:
    sky = ctx.rules.sky
    session = ctx.session
    star_worlds = {item.id for item in await worlds_of_star(session, star_id)} if star_id is not None else {world.id}
    routes = list(await session.scalars(select(RouteRow).order_by(RouteRow.id)))
    forgotten = set(await session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))
    usable = [route for route in routes if route.world_a_id not in forgotten and route.world_b_id not in forgotten]
    slingshots = sum(1 for route in usable if route.method is TravelMethod.SLINGSHOT_ORBIT)
    near = [route for route in usable if route.active and any(touches(route, item) for item in star_worlds)]
    hidden = sum(1 for route in usable if not route.known)
    if ordered and not (slingshots or near or hidden):
        raise ValidationFailedError(
            "There is no route for the alignment to open, shorten or reveal: "
            "no slingshot orbit in the cosmos, no open route to this star's worlds, and no hidden route."
        )
    revealed = await open_alignment(ctx, [TravelMethod.SLINGSHOT_ORBIT])
    for route in near:
        route.danger = max(sky.alignment_danger_floor, route.danger - sky.alignment_danger_drop)
    star = await session.get(StarRow, star_id) if star_id is not None else None
    around = f" (around {star.name})" if star is not None else ""
    parts = []
    if near:
        parts.append("routes shortened")
    if slingshots:
        parts.append(f"slingshot orbits opened for {number_word(sky.alignment_open_epochs)} epochs")
    if revealed:
        parts.append(f"in the aligned light {number_word(revealed)} hidden routes were revealed")
    counts: dict[str, FactInput] = {"shortened": len(near), "opened": slingshots, "revealed": revealed}
    if not parts:
        return SkyOutcome(f"The planets aligned{around}; but there was no route for the alignment to open.", {}, counts)
    return SkyOutcome(f"The planets aligned{around}: {'; '.join(parts)}.", {}, counts)


async def _void_storm(ctx: TickContext, world: WorldRow, order: SkyOrder, by: str) -> SkyOutcome:
    route = await ctx.session.get(RouteRow, order.route_id) if order.route_id is not None else None
    if route is None:
        statement = select(RouteRow).where(
            RouteRow.active.is_(True), RouteRow.method != TravelMethod.DIVINE_BRIDGE, or_(RouteRow.world_a_id == world.id, RouteRow.world_b_id == world.id)
        )
        route = ctx.rng("storm_route").pick_or_none(list(await ctx.session.scalars(statement.order_by(RouteRow.id))))
    if route is None:
        raise ValidationFailedError(f"There is no open route to sever in {world.name}'s sky.")
    duration = order.duration or ctx.rules.sky.god_storm_epochs
    result = await sever_route(ctx, route.id, duration=duration, by=by, write=False)
    other = route.world_b_id if route.world_a_id == world.id else route.world_a_id
    return SkyOutcome(result.text, {IncidentRole.DESTINATION: other}, {"duration": duration})


async def _star_event(ctx: TickContext, kind: SkyEventKind, star_id: int | None) -> SkyOutcome:
    if star_id is None:
        raise ValidationFailedError(f"{an(SKY_EVENT_LABELS[kind].lower(), capital=True)} needs a star.")
    star = await require_star(ctx.session, star_id)
    if kind is SkyEventKind.SUPERNOVA:
        return SkyOutcome(await supernova(ctx, star))
    if kind is SkyEventKind.FLARE:
        return SkyOutcome(await flare(ctx, star))
    return SkyOutcome(await black_sun(ctx, star))


async def lasting_until(ctx: TickContext, kind: SkyEventKind, order: SkyOrder) -> int | None:
    sky = ctx.rules.sky
    if kind is SkyEventKind.BLACK_SUN:
        return None
    if kind is SkyEventKind.ALIGNMENT:
        cosmos = await CosmosRepository(ctx.session).get()
        until = cosmos.alignment_until_epoch if cosmos is not None else None
        return max(ctx.epoch, until - 1) if until is not None else ctx.epoch
    if kind is SkyEventKind.VOID_STORM:
        span = order.duration if order.duration is not None and order.duration > 0 else sky.god_storm_epochs
        return ctx.epoch + span - 1
    lasting = {
        SkyEventKind.ECLIPSE: sky.eclipse_lasting_epochs,
        SkyEventKind.FLARE: sky.flare_lasting_epochs,
        SkyEventKind.COMET: sky.comet_lasting_epochs,
        SkyEventKind.SUPERNOVA: sky.supernova_lasting_epochs,
        SkyEventKind.AURORA: 0,
        SkyEventKind.TRANSIT: 0,
    }
    return ctx.epoch + lasting[kind]


async def sky_event(ctx: TickContext, kind: SkyEventKind, order: SkyOrder) -> SkyEventResult:
    world = await _resolve_world(ctx, order)
    if world is None:
        raise NotFoundError("No such world.")
    if kind not in STAR_EVENTS and world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} was forgotten; no event can be ordered in its sky.")
    star_id = order.star_id if order.star_id is not None else await WorldRepository(ctx.session).root_star_id(world)
    if kind is SkyEventKind.ECLIPSE:
        outcome = await _eclipse(ctx, world)
    elif kind is SkyEventKind.COMET:
        outcome = await _comet(ctx, world)
    elif kind is SkyEventKind.ALIGNMENT:
        outcome = await _alignment(ctx, world, star_id, ordered=order.by is not None)
    elif kind is SkyEventKind.VOID_STORM:
        outcome = await _void_storm(ctx, world, order, order.by or "The Creator")
    elif kind is SkyEventKind.TRANSIT:
        outcome = await _transit(ctx, world)
    else:
        outcome = await _star_event(ctx, kind, order.star_id if order.star_id is not None else star_id)
    text = outcome.text
    until = await lasting_until(ctx, kind, order)
    ctx.session.add(SkyEventRow(kind=kind, epoch=ctx.epoch, until_epoch=until, world_id=world.id, star_id=star_id, route_id=order.route_id, text=text))
    await record(
        ctx,
        f"sky.{kind.value}",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: star_id, IncidentRole.AUTHORITY: order.by_id, **outcome.roles},
        facts={"event": kind, "lasting": max(0, until - ctx.epoch + 1) if until is not None else 0, **outcome.facts},
        steps=(StepDraft(StepAction.APPEAR, actor=star_id, locus_kind=StepLocus.SKY, locus_node=world.id),),
        world_id=world.id,
    )
    ctx.count(f"event.{kind.value}")
    return SkyEventResult(kind, world.id, star_id, text)


def spontaneous_bag(rules: Rules) -> list[SkyEventKind]:
    sky = rules.sky
    return [
        *[SkyEventKind.COMET] * sky.event_weight_comet,
        *[SkyEventKind.ALIGNMENT] * sky.event_weight_alignment,
        *[SkyEventKind.SUPERNOVA] * sky.event_weight_supernova,
        *[SkyEventKind.BLACK_SUN] * sky.event_weight_black_sun,
        *[SkyEventKind.FLARE] * sky.event_weight_flare,
    ]


def star_event_weight(rules: Rules, kind: SkyEventKind, star: StarRow) -> int:
    mechanics = star_mechanics(star.star_type)
    return mechanics.collapse_weight(rules) if kind in COLLAPSE_EVENTS else round(mechanics.flare_weight(rules) * flare_weight_pct(rules, star))


async def sky_rows(session: AsyncSession) -> dict[int, WorldPhysicsRow]:
    return {row.world_id: row for row in await session.scalars(select(WorldPhysicsRow))}


async def _transit(ctx: TickContext, world: WorldRow) -> SkyOutcome:
    worlds = await WorldRepository(ctx.session).reachable_worlds()
    pairs = [pair for pair in transit_pairs(ctx.rules, worlds, await sky_rows(ctx.session)) if pair[0].id == world.id]
    due = [inner for _outer, inner, period in pairs if next_epoch(ctx.epoch, period, transit_phase(world, inner)) == ctx.epoch]
    inner = due[0] if due else pairs[0][1] if pairs else None
    for community in await canon(ctx.session, COMMUNITY_TYPES, world.id):
        if not held(community.id):
            shift_bounded(ctx.rules, community, PIETY_KEY, ctx.rules.orbits.transit_piety)
    if inner is None:
        return SkyOutcome(f"A dark body crossed in front of the star in {world.name}'s sky.", {}, {"piety": ctx.rules.orbits.transit_piety})
    return SkyOutcome(
        f"{inner.name} crossed in front of the star in {world.name}'s sky.", {IncidentRole.CO_ACTOR: inner.id}, {"piety": ctx.rules.orbits.transit_piety}
    )


async def calendar_signs(ctx: TickContext) -> int:
    skies = await sky_rows(ctx.session)
    worlds = sorted((world for world in await WorldRepository(ctx.session).reachable_worlds() if not held(world.id)), key=lambda row: row.id)
    stars = {star.id: star for star in await ctx.session.scalars(select(StarRow).order_by(StarRow.id))}
    signs = 0
    for world in worlds:
        star = stars.get(world.star_id) if world.star_id is not None else None
        period = eclipse_period(ctx.rules, skies.get(world.id), star)
        if period is not None and next_epoch(ctx.epoch, period, world.id) == ctx.epoch:
            await sky_event(ctx, SkyEventKind.ECLIPSE, SkyOrder(world_id=world.id))
            signs += 1
    for outer, inner, period in transit_pairs(ctx.rules, worlds, skies):
        if next_epoch(ctx.epoch, period, transit_phase(outer, inner)) == ctx.epoch:
            await sky_event(ctx, SkyEventKind.TRANSIT, SkyOrder(world_id=outer.id))
            signs += 1
    return signs


async def spontaneous_order(ctx: TickContext, kind: SkyEventKind, stars: dict[int, StarRow]) -> SkyOrder | None:
    if kind not in STAR_EVENTS:
        return SkyOrder()
    candidates = [star for star in stars.values() if star_event_weight(ctx.rules, kind, star) > 0]
    if not candidates or not ctx.rng("spontaneous_star").chance(ctx.rules.sky.star_event_chance):
        return None
    ladder = await cosmography_of(ctx.session)
    weights = [max(1, round(star_event_weight(ctx.rules, kind, star) * ladder.pull(ctx.rules, ladder.place_star(star)).density)) for star in candidates]
    return SkyOrder(star_id=ctx.rng("spontaneous_star").weighted(candidates, weights).id)


async def spontaneous_sky_event(ctx: TickContext) -> SkyEventResult | None:
    rng = ctx.rng("spontaneous")
    stars = {star.id: star for star in await ctx.session.scalars(select(StarRow).order_by(StarRow.id))}
    bag = spontaneous_bag(ctx.rules)
    if not bag or not rng.chance(await paced(ctx, None, SpontaneousKind.COMET, ctx.rules.sky.over_epoch(ctx.rules.sky.sky_event_chance))):
        return None
    kind = bag[rng.die(len(bag)) - 1]
    order = await spontaneous_order(ctx, kind, stars)
    if order is None:
        return None
    world = await _resolve_world(ctx, order)
    if held(world.id if world is not None else None, order.star_id):
        return None
    try:
        return await sky_event(ctx, kind, order)
    except ValidationFailedError:
        return None


async def _thread_place(session: AsyncSession, thread_id: int) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .join(ThreadLinkRow, ThreadLinkRow.entity_id == EntityRow.id)
        .where(ThreadLinkRow.thread_id == thread_id, EntityRow.entity_type.in_(list(RELATED_PLACE_TYPES)))
        .order_by(ThreadLinkRow.epoch, EntityRow.id)
    )
    found: EntityRow | None = await session.scalar(statement.limit(1))
    return found


async def _time_traveller(ctx: TickContext, thread: ThreadRow, place: EntityRow) -> EntityRow:
    sky = ctx.rules.sky
    rng = ctx.rng("time_traveller")
    traveller = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The Traveller who came to {place.name}",
            entity_type=EntityType.MORTAL,
            body=("Someone who came from the future of this story; they seem to know how it will end."),
            stats=MortalStats(
                hp=sky.traveler_hp,
                strength=clamp_percent(sky.traveler_strength_base + rng.die(sky.traveler_strength_die)),
                agility=clamp_percent(sky.traveler_agility_base + rng.die(sky.traveler_agility_die)),
                intellect=clamp_percent(sky.traveler_intellect_base + rng.die(sky.traveler_intellect_die)),
                charisma=clamp_percent(sky.traveler_charisma_base + rng.die(sky.traveler_charisma_die)),
                age=sky.traveler_age_base + rng.die(sky.traveler_age_die),
                lifespan=sky.traveler_lifespan,
            ),
            power=sky.traveler_power,
            location_id=place.id,
            subtype="time traveller",
            flags=(EntityFlag.TIME_ECHO,),
            sanity=sky.traveler_sanity,
        ),
    )
    ctx.session.add(ThreadLinkRow(thread_id=thread.id, entity_id=traveller.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch))
    await record(
        ctx,
        "sky.time_traveller",
        roles={IncidentRole.ACTOR: traveller.id, IncidentRole.PLACE: place.id},
        facts={"age": stat_or(traveller, "age", 0)},
        place=place.id,
    )
    return traveller


async def _echo_prophecy(ctx: TickContext, thread: ThreadRow) -> EntityRow:
    sky = ctx.rules.sky
    rng = ctx.rng("echo_prophecy")
    prophecy = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The Word that Fell Back (story {thread.id})",
            entity_type=EntityType.PROPHECY,
            body="The word of something not yet lived fell into the past; it was found in an old record, as if written before this epoch.",
            stats=ProphecyStats(certainty=clamp_percent(sky.echo_certainty_base + rng.die(sky.echo_certainty_die))),
            power=sky.echo_prophecy_power,
            subtype="prophecy leaked into the past",
            flags=(EntityFlag.TIME_ECHO,),
        ),
    )
    ctx.session.add(ThreadLinkRow(thread_id=thread.id, entity_id=prophecy.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch))
    await record(ctx, "sky.echo_prophecy", roles={IncidentRole.PRODUCT: prophecy.id}, facts={"certainty": stat_or(prophecy, "certainty", 0)})
    return prophecy


async def time_echo(ctx: TickContext, thread_id: int | None = None) -> EntityRow | None:
    rng = ctx.rng("time_echo")
    if thread_id is not None:
        thread = await ctx.session.get(ThreadRow, thread_id)
        if thread is None or thread.status is not ThreadStatus.OPEN:
            raise ValidationFailedError("No such open story.")
    else:
        thread = rng.pick_or_none(list(await ctx.session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.id))))
    if thread is None:
        return None
    place = await _thread_place(ctx.session, thread.id)
    if thread_id is None and (place is None or held(place.id)):
        return None
    if place is not None and rng.chance(ctx.rules.sky.time_traveler_share_pct):
        return await _time_traveller(ctx, thread, place)
    return await _echo_prophecy(ctx, thread)


async def two_timed_hero(ctx: TickContext) -> EntityRow | None:
    tagged = await flags_by_entity(ctx.session, EntityFlag.TWO_TIMED)
    minimum = ctx.rules.sky.two_timed_min_charisma
    for mortal in unheld(await canon(ctx.session, [EntityType.MORTAL])):
        if mortal.id in tagged or stat_or(mortal, CHARISMA_KEY, 0) < minimum:
            continue
        await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.TWO_TIMED, ctx.epoch)
        await record(ctx, "sky.two_timed", roles={IncidentRole.SUBJECT: mortal.id}, facts={"charisma": stat_or(mortal, CHARISMA_KEY, 0)})
        return mortal
    return None


def time_gap_years(rules: Rules, origin: WorldRow | None, target: WorldRow | None, epochs: int) -> int | None:
    origin_factor = origin.time_factor if origin is not None else 1.0
    target_factor = target.time_factor if target is not None else 1.0
    gap = target_factor - origin_factor
    if abs(gap) < rules.sky.time_factor_diff_threshold_pct / PERCENT or target is None:
        return None
    return round(rules.time.years_per_epoch * max(1, epochs) * gap)


async def drift_worlds(ctx: TickContext) -> None:
    session = ctx.session
    stars = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
    rng = ctx.rng("drift")
    for world in await WorldRepository(session).reachable_worlds():
        mechanics = mechanics_of(world.world_type)
        decay = (await view_of(session, ctx.rules, world.id)).fertility_decay
        if decay:
            for region in await canon(session, [EntityType.REGION], world.id):
                shift_bounded(ctx.rules, region, FERTILITY_KEY, -decay)
        period = ctx.rules.world_physics.generation_ship_drift_epochs
        age = ctx.epoch - world.created_epoch
        if mechanics.drifts and period > 0 and age > 0 and age % period == 0 and world.parent_world_id is None:
            choices = [star for star in stars if star.id != world.star_id]
            destination = rng.pick_or_none(choices)
            if destination is not None:
                origin = world.star_id
                world.star_id = destination.id
                await align_moons(session)
                await record(
                    ctx,
                    "sky.world_drift",
                    roles={IncidentRole.SUBJECT: world.id, IncidentRole.ORIGIN: origin, IncidentRole.DESTINATION: destination.id},
                    facts={"period": period},
                    steps=(
                        StepDraft(StepAction.DEPART, actor=world.id),
                        StepDraft(StepAction.ARRIVE, actor=world.id, locus_kind=StepLocus.ORBIT, locus_node=destination.id),
                    ),
                    world_id=world.id,
                )
    await session.flush()


@reads(
    "mortal.charisma",
    "people.piety",
    "settlement.piety",
    "table.bonds",
    "table.calendars",
    "table.community_relations",
    "table.cosmos",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.personality_values",
    "table.place_environment",
    "table.region_environment",
    "table.sky_events",
    "table.sons",
    "table.stars",
    "table.storytellers",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.world_physics",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "people.piety",
    "settlement.piety",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.sky_events",
    "table.sons",
)
async def sky_phase(ctx: TickContext) -> None:
    ctx.count("calendar_signs", await calendar_signs(ctx))
    await spontaneous_sky_event(ctx)
    if ctx.rng("echo_roll").chance(ctx.rules.sky.time_echo_chance):
        await time_echo(ctx)
    if ctx.rng("two_timed_roll").chance(ctx.rules.sky.two_timed_hero_chance):
        await two_timed_hero(ctx)
    await drift_worlds(ctx)


async def order_sky_event(session: AsyncSession, rules: Rules, kind: SkyEventKind, order: SkyOrder) -> SkyEventResult:
    ctx = await manual_context(session, "sky_event", rules, key=kind.value)
    if order.world_id is None and order.star_id is None and order.route_id is None:
        raise ValidationFailedError("Choose a world, a star or a route for the sky event.")
    return await sky_event(ctx, kind, order)


async def order_time_echo(session: AsyncSession, rules: Rules, thread_id: int) -> EntityRow | None:
    return await time_echo(await manual_context(session, "time_echo", rules, key=str(thread_id)), thread_id)


async def run_sky_phase(session: AsyncSession, rules: Rules) -> None:
    await sky_phase(await manual_context(session, "sky", rules))


PHASES = (Phase("sky", sky_phase),)
