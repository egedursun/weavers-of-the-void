from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import (
    ClimateOscillationRow,
    CosmopolitanCultureRow,
    CosmopolitanMemberRow,
    LaunchWindowRow,
    MonsoonSeasonRow,
    RegionWindRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.climes import DIRECTIONS, OscillationPhase
from aerona.engine.primitives.distance import RegionAtlas

LIST_LINES = 3


async def world_lines(scope: Scope, world_id: int) -> list[str]:
    session = scope.session
    found: list[str] = []
    season = await session.scalar(select(MonsoonSeasonRow).where(MonsoonSeasonRow.world_id == world_id).order_by(MonsoonSeasonRow.epoch.desc()).limit(1))
    if season is not None:
        found.append("the monsoon failed this year" if season.failed else f"the monsoon came at {season.strength}% of its usual strength")
    swing = await session.get(ClimateOscillationRow, world_id)
    if swing is not None and swing.phase is not OscillationPhase.NEUTRAL:
        found.append(f"the world is in {an(spoken(swing.phase) + ' swing')} of its climate")
    windows = await session.scalars(
        select(LaunchWindowRow)
        .where(LaunchWindowRow.open.is_(True), or_(LaunchWindowRow.from_world_id == world_id, LaunchWindowRow.to_world_id == world_id))
        .order_by(LaunchWindowRow.from_world_id, LaunchWindowRow.to_world_id)
        .limit(LIST_LINES)
    )
    for window in windows:
        other = await session.get(WorldRow, window.to_world_id if window.from_world_id == world_id else window.from_world_id)
        if other is not None:
            found.append(f"the window for crossing to {other.name} is open")
    return found


async def wind_line(scope: Scope, region_id: int) -> list[str]:
    wind = await scope.session.get(RegionWindRow, region_id)
    if wind is None:
        return []
    marks = [
        *(["it falls on the windward side"] if wind.windward else []),
        *([f"it lies in a rain shadow ({wind.shadow}%)"] if wind.shadow else []),
        *(["cold water rises off its coast"] if wind.upwelling else []),
    ]
    told = f"the {words(wind.band.value)} wind of your land blows from the {DIRECTIONS[wind.wind_from]}"
    return [f"{told}{(', ' + ', '.join(marks)) if marks else ''}"]


async def mortal_climes_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    region = (await RegionAtlas.load(session)).top_region(me.id)
    if region is not None:
        found += await wind_line(scope, region)
    if me.world_id is not None:
        found += await world_lines(scope, me.world_id)
    homes = [item for item in (me.location_id, me.id) if item is not None]
    joined: set[int] = set()
    cultures = await session.execute(
        select(CosmopolitanCultureRow, CosmopolitanMemberRow.share)
        .join(CosmopolitanMemberRow, CosmopolitanMemberRow.culture_id == CosmopolitanCultureRow.id)
        .where(CosmopolitanMemberRow.community_entity_id.in_(homes))
        .order_by(CosmopolitanCultureRow.id)
        .limit(LIST_LINES)
    )
    for culture, share in cultures:
        joined.add(culture.id)
        tongue = f", speaking {await named(scope, culture.lingua_franca_entity_id)}" if culture.lingua_franca_entity_id is not None else ""
        found.append(f"you belong to {culture.name} (#{culture.id}), the culture of a road between worlds ({share}% of your ways){tongue}")
    if me.world_id is not None:
        roads = select(RouteRow.id).where(or_(RouteRow.world_a_id == me.world_id, RouteRow.world_b_id == me.world_id))
        for culture in await session.scalars(
            select(CosmopolitanCultureRow).where(CosmopolitanCultureRow.route_id.in_(roads)).order_by(CosmopolitanCultureRow.id).limit(LIST_LINES)
        ):
            if culture.id not in joined:
                found.append(f"{culture.name} (#{culture.id}) is the culture of a road between worlds that reaches your world")
    return found


async def son_climes_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    return await world_lines(scope, son.current_world_id)
