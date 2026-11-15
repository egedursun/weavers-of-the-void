from aerona.agents.context.scope import Scope
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight
from aerona.engine.cosmos.world_views import WorldView, view_of

SHARES = (
    ("timber_pct", "timber"),
    ("ore_yield_pct", "ore"),
    ("food_need_pct", "the food its people need"),
    ("capacity_pct", "room for life"),
    ("storm_pct", "storms"),
    ("quake_pct", "quakes"),
    ("flood_pct", "floods"),
    ("drought_pct", "droughts"),
    ("plague_pct", "plagues"),
)


def spoken(value: str) -> str:
    return value.replace("_", " ")


def view_lines(view: WorldView) -> list[str]:
    found = []
    if view.light is not WorldLight.STAR:
        found.append(f"its light comes from {spoken(view.light.value)}")
    if view.need is not BindingNeed.NONE:
        found.append(f"its towns are bound to {view.need.value}")
    if view.settle is not SettleMode.GROUND:
        found.append(f"its towns stand {spoken(view.settle.value)}")
    if view.war is not WarTerrain.LAND:
        found.append(f"its wars are fought {view.war.value}")
    found.extend(
        text
        for flag, text in (
            (view.seasons, "it has no seasons"),
            (view.nights, "it has no nights"),
            (view.fire, "fire does not burn there"),
            (view.soil, "it has no soil"),
        )
        if not flag
    )
    found.extend(f"{label} at {getattr(view, key)}% of an ordinary world" for key, label in SHARES if getattr(view, key) != PERCENT)
    return found


async def mortal_world_lines(scope: Scope, me: EntityRow) -> list[str]:
    if me.world_id is None:
        return []
    return view_lines(await view_of(scope.session, scope.rules, me.world_id))


async def son_world_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    shown = view_lines(await view_of(scope.session, scope.rules, son.current_world_id))
    return [f"The nature of the world you walk: {'; '.join(shown)}."] if shown else []
