from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.thin_sections import JourneyEncounterRow
from aerona.db.write_guard import held
from aerona.domain.enums.travel import ArrivalOutcome, EncounterEffect, JourneyEventKind, JourneyIntent, RouteEnvironment, TravelMethod
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import add_event
from aerona.engine.primitives.numbers import clamp_percent

E = RouteEnvironment
M = TravelMethod
ENVIRONMENTS: Mapping[TravelMethod, RouteEnvironment] = total(
    TravelMethod,
    {
        M.ANCIENT_GATE: E.LAND,
        M.SPACE_FOLD: E.SPACE,
        M.LIGHT_SAIL: E.SPACE,
        M.CARRIER_MOUNT: E.AIR,
        M.DREAM_JOURNEY: E.NETWORK,
        M.DEATH_CURRENT: E.SEA,
        M.DIVINE_BRIDGE: E.AIR,
        M.SLINGSHOT_ORBIT: E.SPACE,
        M.CARRIED_WITHIN: E.LAND,
        M.WORMHOLE: E.SPACE,
        M.VOID_ARK: E.SPACE,
        M.GALACTIC_GATE: E.SPACE,
        M.FILAMENT_LANE: E.SPACE,
        M.DIMENSIONAL_RIFT: E.RIFT,
        M.PLANAR_DOOR: E.RIFT,
        M.ROCKETRY: E.SPACE,
    },
)
HARMING = frozenset({EncounterEffect.ATTACK, EncounterEffect.HAZARD, EncounterEffect.SICKNESS, EncounterEffect.DESERTION})
DEFAULT_LOSS: Mapping[EncounterEffect, int] = total(
    EncounterEffect,
    {
        EncounterEffect.ATTACK: 15,
        EncounterEffect.HAZARD: 10,
        EncounterEffect.DELAY: 0,
        EncounterEffect.STRAYING: 0,
        EncounterEffect.FIND: 0,
        EncounterEffect.TOLL: 0,
        EncounterEffect.SICKNESS: 8,
        EncounterEffect.DESERTION: 5,
    },
)
ARRIVALS: Mapping[JourneyIntent, ArrivalOutcome] = total(
    JourneyIntent,
    {
        JourneyIntent.COLONY: ArrivalOutcome.SETTLERS,
        JourneyIntent.TRADE: ArrivalOutcome.SETTLERS,
        JourneyIntent.EXPLORATION: ArrivalOutcome.SETTLERS,
        JourneyIntent.CONQUEST: ArrivalOutcome.INVADERS,
        JourneyIntent.PILGRIMAGE: ArrivalOutcome.SETTLERS,
    },
)


@dataclass(frozen=True)
class JourneyCounts:
    supplies: int | None = None
    births: int | None = None
    deaths: int | None = None
    arrival: ArrivalOutcome | None = None

    def values(self) -> dict[str, object]:
        return {
            key: value
            for key, value in (("supplies", self.supplies), ("births", self.births), ("deaths", self.deaths), ("arrival", self.arrival))
            if value is not None
        }


async def seed_encounters(ctx: TickContext) -> int:
    known = {(row.environment, row.effect) for row in await ctx.session.scalars(select(JourneyEncounterRow).where(JourneyEncounterRow.world_id.is_(None)))}
    added = 0
    for environment in RouteEnvironment:
        for effect in EncounterEffect:
            if (environment, effect) in known:
                continue
            ctx.session.add(JourneyEncounterRow(environment=environment, effect=effect, weight=PERCENT // 2, loss_pct=DEFAULT_LOSS[effect], locked=[]))
            added += 1
    return added


async def draw(ctx: TickContext, route: RouteRow, world_id: int, rng: SeededRandom) -> JourneyEncounterRow | None:
    environment = ENVIRONMENTS[route.method]
    rows = list(
        await ctx.session.scalars(
            select(JourneyEncounterRow)
            .where(JourneyEncounterRow.environment == environment, or_(JourneyEncounterRow.world_id.is_(None), JourneyEncounterRow.world_id == world_id))
            .order_by(JourneyEncounterRow.id)
        )
    )
    weighted = [row for row in rows if row.weight > 0]
    if not weighted:
        return None
    mark = rng.integer(1, sum(row.weight for row in weighted))
    for row in weighted:
        mark -= row.weight
        if mark <= 0:
            return row
    return weighted[-1]


def told(row: JourneyEncounterRow) -> str:
    return row.name or row.effect.value.replace("_", " ")


async def meet(ctx: TickContext, journey: JourneyRow, row: JourneyEncounterRow) -> int:
    table = ctx.rules.journeys
    lost = journey.population * row.loss_pct // PERCENT if row.effect in HARMING else 0
    if row.effect in {EncounterEffect.DELAY, EncounterEffect.STRAYING} and "epochs_left" not in journey.locked:
        journey.epochs_left += 1
    elif row.effect is EncounterEffect.FIND and "supplies" not in journey.locked:
        journey.supplies = clamp_percent(journey.supplies + table.find_supplies)
    elif row.effect is EncounterEffect.TOLL and "supplies" not in journey.locked:
        journey.supplies = clamp_percent(journey.supplies - table.toll_supplies)
    if lost and "population" not in journey.locked:
        journey.population = max(0, journey.population - lost)
        if "deaths" not in journey.locked:
            journey.deaths += lost
    add_event(journey, ctx.epoch, JourneyEventKind.ENCOUNTER, f"they met {told(row)} on the way", loss=lost)
    return lost


async def provision(ctx: TickContext, journey: JourneyRow) -> None:
    table = ctx.rules.journeys
    if "supplies" not in journey.locked:
        journey.supplies = max(0, journey.supplies - table.supply_use)
    if journey.supplies == 0 and journey.population and "population" not in journey.locked:
        starved = max(1, journey.population * table.starve_pct // PERCENT)
        journey.population -= starved
        journey.deaths += starved
        add_event(journey, ctx.epoch, JourneyEventKind.DEATH, "some died on the way with nothing left to eat", loss=starved)
    if ctx.epoch - journey.start_epoch >= table.birth_after and journey.population and "population" not in journey.locked:
        born = journey.population * table.birth_pct // PERCENT
        if born:
            journey.population += born
            journey.births += born
            add_event(journey, ctx.epoch, JourneyEventKind.BIRTH, "children were born on the way")


async def arrive(ctx: TickContext, journey: JourneyRow, market: EntityRow | None) -> ArrivalOutcome:
    table = ctx.rules.journeys
    outcome = ARRIVALS[journey.intent]
    started = journey.population + journey.deaths - journey.births
    if outcome is ArrivalOutcome.SETTLERS and started and journey.deaths * PERCENT > started * table.refugee_share:
        outcome = ArrivalOutcome.REFUGEES
    if "arrival" not in journey.locked:
        journey.arrival = outcome
    if journey.arrival is ArrivalOutcome.REFUGEES and market is not None and not held(market.id):
        profile = await ctx.session.get(SettlementProfileRow, market.id)
        if profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_percent(profile.unrest + table.refugee_unrest)
    return outcome
