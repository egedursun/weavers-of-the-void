from aerona.catalog.cosmography import SCOPE_LABELS
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import RouteScope
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction
from aerona.domain.enums.travel import JourneyEventKind
from aerona.domain.models.records import CargoLine
from aerona.engine.context import TickContext
from aerona.engine.cosmos.commerce import market_of
from aerona.engine.cosmos.encounters import arrive, provision
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.cosmos.routes import add_event
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import disease_for, open_outbreak
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

DARK_SCOPES = frozenset({RouteScope.INTERGALACTIC, RouteScope.INTERCLUSTER, RouteScope.INTERDIMENSIONAL})
FAR_SCOPES = frozenset({RouteScope.GALACTIC, *DARK_SCOPES})
OUTER_LEAK = PERCENT // 2


def escort_share(rules: Rules, journey: JourneyRow) -> float:
    table = rules.journeys
    spared = min(table.escort_cap_pct, journey.escorts * table.escort_loss_pct)
    return (PERCENT - spared) / PERCENT


async def voyage_epoch(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, route: RouteRow) -> None:
    table = ctx.rules.journeys
    rng = ctx.rng(f"voyage.{journey.id}")
    await provision(ctx, journey)
    if journey.passengers and "passengers" not in journey.locked:
        journey.passengers = [
            line.model_copy(
                update={
                    "condition": clamp_percent(line.condition - table.condition_loss),
                    "sick": line.sick or line.condition - table.condition_loss < PERCENT // 2,
                }
            )
            for line in journey.passengers
        ]
    if rng.chance(table.derelict_chance):
        found = CargoLine(commodity=CommodityKind.TOOLS, amount=table.derelict_goods)
        if "cargo" not in journey.locked:
            journey.cargo = [*journey.cargo, found]
        await add_event(ctx, journey, JourneyEventKind.DERELICT, "they came upon a derelict and took what it held")
    origin = await ctx.session.get(WorldRow, journey.origin_world_id)
    dark = journey.scope in DARK_SCOPES or (origin is not None and origin.leakage >= OUTER_LEAK)
    if dark and rng.chance(table.outer_touch_chance):
        if not held(traveller.id):
            shift_sanity(ctx.rules, traveller, -table.outer_touch_sanity)
        await add_event(ctx, journey, JourneyEventKind.OUTER_TOUCH, "something from outside touched them on the way")
    if route.toll_controller_entity_id is not None and route.toll_pct and journey.cargo and "cargo" not in journey.locked:
        journey.cargo = [line.model_copy(update={"amount": line.amount - line.amount * route.toll_pct // PERCENT}) for line in journey.cargo]
        await add_event(ctx, journey, JourneyEventKind.TOLL, "they paid the toll of the route")


async def crossing_text(ctx: TickContext, journey: JourneyRow) -> str:
    cosmography = await cosmography_of(ctx.session)
    origin, destination = cosmography.place_world_id(journey.origin_world_id), cosmography.place_world_id(journey.destination_world_id)
    scope = SCOPE_LABELS[journey.scope].lower() if journey.scope is not None else "far"
    if journey.scope is RouteScope.INTERDIMENSIONAL and origin.dimension is not None and destination.dimension is not None:
        return f"they crossed from {origin.dimension.name} into {destination.dimension.name} ({scope})"
    if origin.galaxy is not None and destination.galaxy is not None and origin.galaxy.id != destination.galaxy.id:
        return f"they crossed from {origin.galaxy.name} to {destination.galaxy.name} ({scope})"
    return f"they made a crossing {scope}"


async def unload(ctx: TickContext, journey: JourneyRow, traveller: EntityRow) -> None:
    table = ctx.rules.journeys
    if journey.scope in FAR_SCOPES:
        await add_event(ctx, journey, JourneyEventKind.CROSSING, await crossing_text(ctx, journey))
    if journey.scope is RouteScope.INTERDIMENSIONAL and not held(traveller.id):
        cosmography = await cosmography_of(ctx.session)
        dimension = cosmography.place_world_id(journey.destination_world_id).dimension
        if dimension is not None and dimension.sanity_drain:
            shift_sanity(ctx.rules, traveller, -dimension.sanity_drain * ctx.rules.dimensions.visitor_sanity_pct / PERCENT)
    market = await market_of(ctx, journey.destination_world_id, {})
    await arrive(ctx, journey, market)
    if market is not None and journey.cargo and not held(market.id):
        for line in journey.cargo:
            await goods_of(ctx.session, ctx.epoch).add(market.id, line.commodity, line.amount, GoodsFlow.TRADE, material=line.material)
        await record(
            ctx,
            "travel.cargo_delivered",
            roles={IncidentRole.ACTOR: traveller.id, IncidentRole.RECEIVER: market.id},
            facts={"goods": [line.commodity for line in journey.cargo], "amounts": [line.amount for line in journey.cargo]},
            steps=tuple(
                StepDraft(
                    StepAction.DELIVER,
                    actor=traveller.id,
                    target=market.id,
                    instrument_kind=InstrumentKind.SUBSTANCE,
                    instrument_key=line.commodity.value,
                    amount=line.amount,
                    unit=FactUnit.COUNT,
                )
                for line in journey.cargo
            ),
            place=market.id,
            cause=journey.incident_id,
        )
        journey.cargo = []
    if any(line.sick for line in journey.passengers) and ctx.rng(f"voyage_sickness.{journey.id}").chance(table.sick_spread_chance):
        book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
        region = await ctx.session.get(EntityRow, market.location_id) if market is not None and market.location_id is not None else None
        if region is not None and not held(region.id):
            disease = await disease_for(ctx, book, region)
            await open_outbreak(ctx, book, disease, region.id, path=SpreadPath.JOURNEY, severity=PERCENT // 3)
            await record(
                ctx,
                "travel.sick_arrival",
                roles={IncidentRole.ACTOR: traveller.id, IncidentRole.SUBJECT: disease.id, IncidentRole.PLACE: region.id},
                facts={"severity": PERCENT // 3},
                place=region.id,
                cause=journey.incident_id,
            )
