from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import RouteClosure
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import world_name
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import stat_or

INFLUENCE_KEY = "influence"


async def seal_gate(ctx: TickContext, route_id: int, by: str) -> str:
    route = await ctx.session.get(RouteRow, route_id)
    if route is None or not route.active:
        raise NotFoundError("No such open route.")
    route.active = False
    route.closure = RouteClosure.SEALED
    route.temp_closed_until_epoch = None
    route.temp_open_until_epoch = None
    for world_id in (route.world_a_id, route.world_b_id):
        world = await ctx.session.get(WorldRow, world_id)
        if world is not None:
            world.leakage = max(0, world.leakage - ctx.rules.pantheon.seal_leak_reduction)
    vehicle = await ctx.session.get(EntityRow, route.vehicle_entity_id) if route.vehicle_entity_id is not None else None
    if vehicle is not None and vehicle.status is EntityStatus.CANON:
        await retire(ctx.session, vehicle, ctx.epoch, f"Epoch {ctx.epoch}: sealed by {by}.")
    first, second = await world_name(ctx.session, route.world_a_id), await world_name(ctx.session, route.world_b_id)
    text = f"{by} sealed the route between {first} and {second}; the leak of both worlds decreased."
    await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="cosmos.gate_sealed", feed_category=FeedCategory.GATE)
    await ctx.session.flush()
    return text


async def cleanse_leak(ctx: TickContext, world_id: int, by: str) -> str:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    statement = select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON)
    being: EntityRow | None = await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))
    if world.leakage <= 0 and being is None:
        raise ValidationFailedError(f"There is nothing to cleanse in {world.name}.")
    world.leakage = max(0, world.leakage - ctx.rules.pantheon.cleanse_leak_amount)
    expelled = being is not None and ctx.rng("cleanse").chance(ctx.rules.pantheon.outer_expel_chance)
    if expelled and being is not None:
        await retire(ctx.session, being, ctx.epoch, f"Epoch {ctx.epoch}: the creator pushed it outside.", status=EntityStatus.DESTROYED)
    tail = " and the thing that had come in was pushed outside" if expelled else ""
    text = f"{by} sealed {world.name}'s leak; it receded{tail}."
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key="cosmos.leak_cleansed", world_id=world.id, feed_category=FeedCategory.LEAK)
    await ctx.session.flush()
    return text


async def bargain_with_outer(ctx: TickContext, son_id: int, outer_id: int, request: str) -> int:
    pantheon = ctx.rules.pantheon
    son = await SonRepository(ctx.session).require_son(son_id)
    being = await ctx.session.get(EntityRow, outer_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING or being.status is not EntityStatus.CANON:
        raise NotFoundError("No such thing. Or there is, and you cannot see it.")
    gain = pantheon.bargain_essence_base + round(stat_or(being, INFLUENCE_KEY, pantheon.outer_default_influence) / pantheon.bargain_influence_divisor)
    son.essence += gain
    son.ambition = min(PERCENT_MAX, son.ambition + pantheon.bargain_ambition)
    son.loyalty = max(0, son.loyalty - pantheon.bargain_loyalty_loss)
    world = await ctx.session.get(WorldRow, being.world_id)
    if world is not None:
        world.leakage = min(PERCENT_MAX, world.leakage + pantheon.bargain_leak)
    repository = SonRepository(ctx.session)
    for sibling in await ctx.session.scalars(select(SonRow).where(SonRow.id != son.id, SonRow.status != SonStatus.DEAD)):
        await repository.change_relation(son.id, sibling.id, -pantheon.bargain_sibling_relation_loss)
    if await ctx.session.get(OuterBargainRow, (being.id, son.id)) is None:
        ctx.session.add(OuterBargainRow(outer_entity_id=being.id, son_id=son.id, epoch=ctx.epoch, terms=request))
    thread = ThreadRow(
        epoch=ctx.epoch,
        text=f"{son.name} bargained with the thing outside ({request}). No one knows what they gave in return; but one day it will be paid.",
        status=ThreadStatus.OPEN,
    )
    ctx.session.add(thread)
    await ctx.session.flush()
    ctx.session.add(ThreadLinkRow(thread_id=thread.id, entity_id=being.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch))
    text = f"{son.name} bargained with the unnamed thing. Their siblings saw another shadow over them."
    await ctx.chronicle(ChronicleKind.PROHIBITION, text, template_key="cosmos.outer_bargain", son_id=son.id, world_id=being.world_id)
    await ctx.session.flush()
    return gain
