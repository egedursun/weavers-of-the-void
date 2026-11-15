from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.prehistory import PrehistoryKind
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight


class WorldNatureView(ApiModel):
    light: WorldLight
    need: BindingNeed
    settle: SettleMode
    war: WarTerrain
    prehistory_kind: PrehistoryKind
    seasons: bool
    nights: bool
    fire: bool
    soil: bool
    timber_pct: int
    food_need_pct: int
    capacity_pct: int
    ore_yield_pct: int
    storm_pct: int
    quake_pct: int
    flood_pct: int
    drought_pct: int
    plague_pct: int
    route_danger: int
    leak: int
    leak_repair: int
    sanity_erosion: int
    fertility_decay: int
    sea_pct: int


class WorldViewNodeView(ApiModel):
    node: NodeRef
    world: NodeRef | None
    world_type: WorldType | None
    nature: WorldNatureView | None
    kind_nature: WorldNatureView | None
    seeded: bool
    updated_epoch: int | None
    locked: list[str]
    absent_reason: str | None
