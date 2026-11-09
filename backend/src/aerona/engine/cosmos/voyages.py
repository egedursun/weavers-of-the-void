from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import RouteScope
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.travel import JourneyEventKind
from aerona.domain.models.records import CargoLine
from aerona.engine.context import TickContext
from aerona.engine.cosmos.commerce import market_of
from aerona.engine.cosmos.routes import add_event
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import disease_for, open_outbreak
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.rules.registry import Rules

DARK_SCOPES = frozenset({RouteScope.INTERGALACTIC, RouteScope.INTERCLUSTER, RouteScope.INTERDIMENSIONAL})
OUTER_LEAK = PERCENT // 2


def escort_share(rules: Rules, journey: JourneyRow) -> float:
    table = rules.journeys
    spared = min(table.escort_cap_pct, journey.escorts * table.escort_loss_pct)
    return (PERCENT - spared) / PERCENT


async def voyage_epoch(ctx: TickContext, journey: JourneyRow, traveller: EntityRow, route: RouteRow) -> None:
    table = ctx.rules.journeys
    rng = ctx.rng(f"voyage.{journey.id}")
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
        add_event(journey, ctx.epoch, JourneyEventKind.DERELICT, "they came upon a derelict and took what it held")
    origin = await ctx.session.get(WorldRow, journey.origin_world_id)
    dark = journey.scope in DARK_SCOPES or (origin is not None and origin.leakage >= OUTER_LEAK)
    if dark and rng.chance(table.outer_touch_chance):
        if not held(traveller.id):
            shift_sanity(ctx.rules, traveller, -table.outer_touch_sanity)
        add_event(journey, ctx.epoch, JourneyEventKind.OUTER_TOUCH, "something from outside touched them on the way")
    if route.toll_controller_entity_id is not None and route.toll_pct and journey.cargo and "cargo" not in journey.locked:
        journey.cargo = [line.model_copy(update={"amount": line.amount - line.amount * route.toll_pct // PERCENT}) for line in journey.cargo]
        add_event(journey, ctx.epoch, JourneyEventKind.TOLL, "they paid the toll of the route")


async def unload(ctx: TickContext, journey: JourneyRow, traveller: EntityRow) -> None:
    table = ctx.rules.journeys
    if journey.scope in DARK_SCOPES:
        add_event(
            journey,
            ctx.epoch,
            JourneyEventKind.CROSSING,
            f"they crossed {journey.scope.value.replace('_', ' ')} space" if journey.scope is not None else "they crossed",
        )
    market = await market_of(ctx, journey.destination_world_id, {})
    if market is not None and journey.cargo and not held(market.id):
        for line in journey.cargo:
            stock = await ctx.session.scalar(
                select(CommunityStockRow).where(
                    CommunityStockRow.community_entity_id == market.id,
                    CommunityStockRow.commodity == line.commodity,
                    CommunityStockRow.material == line.material,
                )
            )
            if stock is None:
                stock = CommunityStockRow(
                    community_entity_id=market.id, commodity=line.commodity, material=line.material, quantity=0, quality=PERCENT // 2, preserved=0
                )
                ctx.session.add(stock)
            if not stock.held:
                stock.quantity += line.amount
        await note(ctx, f"{traveller.name}'s convoy brought its goods to {market.name}.", key="travel.cargo_delivered", ids=[traveller.id, market.id])
        journey.cargo = []
    if any(line.sick for line in journey.passengers) and ctx.rng(f"voyage_sickness.{journey.id}").chance(table.sick_spread_chance):
        book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
        region = await ctx.session.get(EntityRow, market.location_id) if market is not None and market.location_id is not None else None
        if region is not None and not held(region.id):
            disease = await disease_for(ctx, book, region)
            await open_outbreak(ctx, book, disease, region.id, path=SpreadPath.JOURNEY, severity=PERCENT // 3)
            await note(
                ctx, f"Sick travellers of {traveller.name} brought {disease.name} to {region.name}.", key="travel.sick_arrival", ids=[traveller.id, region.id]
            )
