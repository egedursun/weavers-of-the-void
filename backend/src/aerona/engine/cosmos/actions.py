from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.outer_bargains import BARGAIN_PRICES
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.domain.enums.divine import BargainGain, BargainPrice
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import RouteClosure
from aerona.engine.context import TickContext
from aerona.engine.divine.outer import pay_price, take_gain
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import RoleValue, StepDraft, record

INFLUENCE_KEY = "influence"


async def seal_gate(ctx: TickContext, route_id: int, by: str, by_id: int) -> str:
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
    written = await record(
        ctx,
        "cosmos.gate_sealed",
        roles={
            IncidentRole.ACTOR: by_id,
            IncidentRole.ORIGIN: route.world_a_id,
            IncidentRole.DESTINATION: route.world_b_id,
            IncidentRole.VICTIM: vehicle.id if vehicle is not None else None,
        },
        facts={"leak": ctx.rules.pantheon.seal_leak_reduction},
        steps=(StepDraft(StepAction.CLOSE, actor=by_id, outcome=StepOutcome.SUCCESS),),
    )
    text = written.text
    await ctx.session.flush()
    return text


async def cleanse_leak(ctx: TickContext, world_id: int, by_id: int) -> str:
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
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: by_id, IncidentRole.SUBJECT: world.id}
    if expelled and being is not None:
        roles[IncidentRole.VICTIM] = being.id
    written = await record(
        ctx,
        "cosmos.leak_expelled" if expelled else "cosmos.leak_cleansed",
        roles=roles,
        facts={"leak": ctx.rules.pantheon.cleanse_leak_amount},
        steps=(StepDraft(StepAction.CLOSE, actor=by_id, outcome=StepOutcome.SUCCESS),),
        world_id=world.id,
    )
    text = written.text
    await ctx.session.flush()
    return text


@dataclass(frozen=True)
class BargainTerms:
    gain: BargainGain = BargainGain.ESSENCE
    price: BargainPrice = BargainPrice.WORLD_SANITY
    price_domain: Domain | None = None
    price_world_id: int | None = None


def asked_price(ctx: TickContext, son_id: int, outer_id: int) -> BargainPrice:
    prices = list(BARGAIN_PRICES)
    weights = [float(BARGAIN_PRICES[price].weight(ctx.rules)) for price in prices]
    if not any(weights):
        return BargainPrice.WORLD_SANITY
    return ctx.rng(f"outer_price.{son_id}.{outer_id}.{ctx.epoch}").weighted(prices, weights)


async def bargain_with_outer(ctx: TickContext, son_id: int, outer_id: int, request: str, terms: BargainTerms | None = None) -> int:
    pantheon = ctx.rules.pantheon
    deal = terms if terms is not None else BargainTerms(price=asked_price(ctx, son_id, outer_id))
    son = await SonRepository(ctx.session).require_son(son_id)
    being = await ctx.session.get(EntityRow, outer_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING or being.status is not EntityStatus.CANON:
        raise NotFoundError("No such outer being.")
    if deal.price is BargainPrice.DOMAIN and deal.price_domain is not None and deal.price_domain not in son.domains:
        raise ValidationFailedError(f"{son.name} cannot give up a domain they do not hold.")
    essence = pantheon.bargain_essence_base + round(stat_or(being, INFLUENCE_KEY, pantheon.outer_default_influence) / pantheon.bargain_influence_divisor)
    before = son.essence
    gained = await take_gain(ctx, son, being, deal.gain, essence)
    paid = await pay_price(ctx, son, being, deal.price, domain=deal.price_domain, world_id=deal.price_world_id)
    son.ambition = min(PERCENT_MAX, son.ambition + pantheon.bargain_ambition)
    son.loyalty = max(0, son.loyalty - pantheon.bargain_loyalty_loss)
    world = await ctx.session.get(WorldRow, being.world_id)
    if world is not None:
        world.leakage = min(PERCENT_MAX, world.leakage + pantheon.bargain_leak)
    repository = SonRepository(ctx.session)
    for sibling in await ctx.session.scalars(select(SonRow).where(SonRow.id != son.id, SonRow.status != SonStatus.DEAD)):
        await repository.change_relation(son.id, sibling.id, -pantheon.bargain_sibling_relation_loss)
    row = await ctx.session.get(OuterBargainRow, (being.id, son.id))
    if row is None:
        row = OuterBargainRow(outer_entity_id=being.id, son_id=son.id, epoch=ctx.epoch)
        ctx.session.add(row)
    row.terms, row.gain, row.price, row.price_domain, row.price_world_id, row.paid = (
        request,
        deal.gain,
        deal.price,
        deal.price_domain,
        deal.price_world_id,
        not BARGAIN_PRICES[deal.price].lasting,
    )
    thread = ThreadRow(epoch=ctx.epoch, text=f"{son.name} bargained with {being.name} ({request}): {gained}, and {paid}.", status=ThreadStatus.OPEN)
    ctx.session.add(thread)
    await ctx.session.flush()
    ctx.session.add(ThreadLinkRow(thread_id=thread.id, entity_id=being.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch))
    await record(
        ctx,
        "cosmos.outer_bargain",
        roles={IncidentRole.ACTOR: son.id, IncidentRole.TARGET: being.id},
        facts={"gain": deal.gain, "price": deal.price, "essence": max(0, son.essence - before), "leak": pantheon.bargain_leak},
        steps=(
            StepDraft(StepAction.NEGOTIATE, actor=son.id, target=being.id),
            StepDraft(StepAction.AGREE, actor=being.id, target=son.id, outcome=StepOutcome.ACCEPTED),
            StepDraft(StepAction.PAY, actor=son.id, target=being.id, outcome=StepOutcome.SUCCESS),
        ),
        son_id=son.id,
        world_id=being.world_id,
    )
    await ctx.session.flush()
    return max(0, son.essence - before)
