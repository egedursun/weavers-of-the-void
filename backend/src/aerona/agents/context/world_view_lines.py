from aerona.agents.context.scope import Scope
from aerona.catalog.settle_modes import SETTLE_MODES
from aerona.catalog.war_grounds import WAR_GROUNDS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight
from aerona.engine.cosmos.world_views import WorldView, view_of

SHARES = (
    ("timber_pct", "timber"),
    ("ore_yield_pct", "ore"),
    ("ship_pct", "hulls its shipyards launch"),
    ("food_need_pct", "the food its people need"),
    ("capacity_pct", "room for life"),
    ("storm_pct", "storms"),
    ("quake_pct", "quakes"),
    ("flood_pct", "floods"),
    ("drought_pct", "droughts"),
    ("plague_pct", "plagues"),
)


def view_lines(view: WorldView) -> list[str]:
    found = []
    if view.light is not WorldLight.STAR:
        found.append(f"its light comes from {spoken(view.light.value)}")
    if view.need is not BindingNeed.NONE:
        found.append(f"its towns are bound to {spoken(view.need)}")
    if view.settle is not SettleMode.GROUND:
        found.append(f"its towns are settled {SETTLE_MODES[view.settle].label.lower()}")
    if view.war is not WarTerrain.LAND:
        found.append(f"its wars are fought {WAR_GROUNDS[view.war].label.lower()}")
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
    if view.sea_roads:
        found.append("every road between its lands goes by sea")
    found.extend(f"{label} at {getattr(view, key)}% of an ordinary world" for key, label in SHARES if getattr(view, key) != PERCENT)
    if view.sea_pct != WorldView().sea_pct:
        found.append(f"the sea gives {view.sea_pct}% of the food of its coasts")
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
