from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.life.forecasting import NEEDS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.environment import ForcedWeatherRow, WorldSeasonRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.body.customs import people_of
from aerona.engine.economy.purse import take_coin
from aerona.engine.environment.onsets import onset_of_year
from aerona.engine.forecasting.works import EPOCH_STRENGTH
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import top_region
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

AHEAD = 3


class ForecastInput(ToolInput):
    method: ObservationMethod
    season_position: int | None = Field(default=None, ge=0, le=7)


class WorkWeatherInput(ToolInput):
    aim: WeatherAim
    method: WeatherWorkMethod
    strength: int = Field(ge=1, le=100)


async def onset_reading(call: MortalCall, world_id: int, position: int, true_reading: bool) -> str:
    season = await call.session.scalar(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id, WorldSeasonRow.position == position).limit(1))
    if season is None:
        return "your world keeps no such season"
    year = epoch_start_year(call.tick.epoch + 1, call.tick.rules.time.years_per_epoch)
    onset = onset_of_year(call.tick.rules, call.tick.environment.world_seed, world_id, year, position)
    if not true_reading:
        return f"{season.name} will come as it always does"
    return f"{season.name} of year {year} will come {spoken(onset)}"


async def forecast(call: MortalCall, args: ForecastInput) -> str:
    region = await top_region(call.session, call.me)
    folk = await people_of(call.session, call.me)
    if region is None or folk is None:
        fail(MortalResult.FORECAST_REFUSED, why="you belong to no people that reads the weather")
    row = await call.session.scalar(
        select(ObservationMethodRow).where(ObservationMethodRow.people_entity_id == folk.id, ObservationMethodRow.method == args.method).limit(1)
    )
    if row is None:
        kept = await call.session.scalars(
            select(ObservationMethodRow.method).where(ObservationMethodRow.people_entity_id == folk.id).order_by(ObservationMethodRow.id)
        )
        fail(MortalResult.FORECAST_REFUSED, why=f"your people read the weather only by {', '.join(spoken(method) for method in kept) or 'nothing yet'}")
    coming = await call.session.scalar(
        select(ForcedWeatherRow)
        .where(
            ForcedWeatherRow.region_entity_id == region.id,
            ForcedWeatherRow.until_epoch >= call.tick.epoch,
            ForcedWeatherRow.from_epoch <= call.tick.epoch + AHEAD,
        )
        .order_by(ForcedWeatherRow.from_epoch, ForcedWeatherRow.id)
        .limit(1)
    )
    true_reading = call.tick.rng(seed_of("forecast", call.me.id, call.tick.epoch)).chance(row.accuracy)
    told = f"{spoken(coming.kind)} from epoch {coming.from_epoch}" if coming is not None and true_reading else "no turn of the weather out of the usual"
    if args.season_position is not None and region.world_id is not None:
        told += "; " + await onset_reading(call, region.world_id, args.season_position, true_reading)
    call.target(region.id)
    await call.record(
        "tools.mortal.forecast",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: region.id},
        facts={"method": args.method, "accuracy": row.accuracy, "told": told},
        place=region.id,
    )
    return result(MortalResult.FORECAST_READ, method=spoken(args.method), accuracy=row.accuracy, told=told)


async def work_weather(call: MortalCall, args: WorkWeatherInput) -> str:
    table = call.rules.forecasting
    region = await top_region(call.session, call.me)
    if region is None or held(region.id):
        fail(MortalResult.WEATHER_WORK_REFUSED, why="a god holds the sky of your land as it is")
    if not await knows(call.session, call.me.id, NEEDS[args.method]):
        fail(MortalResult.WEATHER_WORK_REFUSED, why=f"working the weather by {spoken(args.method)} needs {spoken(NEEDS[args.method])}")
    cost = table.weather_work_cost * args.strength // max(1, table.weather_work_strength)
    if not await take_coin(call.session, call.rules, call.me, cost):
        fail(MortalResult.WEATHER_WORK_REFUSED, why=f"it costs {cost} coin and you have less")
    atlas = await RegionAtlas.load(call.session)
    downwind = next(iter(sorted(atlas.neighbours(region.id))), None)
    row = WeatherWorkRow(
        holder_node_id=call.me.id,
        region_entity_id=region.id,
        downwind_region_id=downwind,
        method=args.method,
        aim=args.aim,
        strength=min(PERCENT, args.strength),
        cost=cost,
        epochs_left=1 + args.strength // EPOCH_STRENGTH,
        since_epoch=call.tick.epoch,
        locked=[],
    )
    call.session.add(row)
    await call.session.flush()
    call.target(region.id)
    await call.record(
        "tools.mortal.work_weather",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: region.id},
        facts={"aim": args.aim, "strength": row.strength, "cost": cost},
        place=region.id,
    )
    return result(MortalResult.WEATHER_WORK_BEGUN, aim=spoken(args.aim), strength=row.strength, epochs=row.epochs_left, cost=cost)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FORECAST, AgentKind.MORTAL, ForecastInput, meta, forecast),
        ToolSpec(MortalToolId.WORK_WEATHER, AgentKind.MORTAL, WorkWeatherInput, meta, work_weather),
    ]
