from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.prehistory import PrehistoryKind
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight

SHARE_MAX = 500
WORLD_VIEW_FLAGS = ("seasons", "nights", "fire", "soil", "sea_roads")
WORLD_VIEW_SHARES = (
    "timber_pct",
    "food_need_pct",
    "capacity_pct",
    "ore_yield_pct",
    "ship_pct",
    "storm_pct",
    "quake_pct",
    "flood_pct",
    "drought_pct",
    "plague_pct",
)
WORLD_VIEW_NUMBERS = ("route_danger", "leak", "leak_repair", "sanity_erosion", "fertility_decay", "sea_pct")
WORLD_VIEW_KINDS = ("light", "need", "settle", "war", "prehistory_kind")
WORLD_VIEW_FIELDS = (*WORLD_VIEW_KINDS, *WORLD_VIEW_FLAGS, *WORLD_VIEW_SHARES, *WORLD_VIEW_NUMBERS)


class WorldViewRow(Base):
    __tablename__ = "world_type_profiles"
    __table_args__ = (
        *(between(column, 0, SHARE_MAX) for column in WORLD_VIEW_SHARES),
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in WORLD_VIEW_NUMBERS),
        at_least("updated_epoch", 0),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    light: Mapped[WorldLight] = mapped_column(enum_type(WorldLight, "light"), default=WorldLight.STAR)
    need: Mapped[BindingNeed] = mapped_column(enum_type(BindingNeed, "need"), default=BindingNeed.NONE)
    settle: Mapped[SettleMode] = mapped_column(enum_type(SettleMode, "settle"), default=SettleMode.GROUND)
    war: Mapped[WarTerrain] = mapped_column(enum_type(WarTerrain, "war"), default=WarTerrain.LAND)
    prehistory_kind: Mapped[PrehistoryKind] = mapped_column(enum_type(PrehistoryKind, "prehistory_kind"), default=PrehistoryKind.FULL)
    seasons: Mapped[bool] = mapped_column(default=True)
    nights: Mapped[bool] = mapped_column(default=True)
    fire: Mapped[bool] = mapped_column(default=True)
    soil: Mapped[bool] = mapped_column(default=True)
    sea_roads: Mapped[bool] = mapped_column(default=False)
    timber_pct: Mapped[int] = mapped_column(default=100)
    food_need_pct: Mapped[int] = mapped_column(default=100)
    capacity_pct: Mapped[int] = mapped_column(default=100)
    ore_yield_pct: Mapped[int] = mapped_column(default=100)
    ship_pct: Mapped[int] = mapped_column(default=100)
    storm_pct: Mapped[int] = mapped_column(default=100)
    quake_pct: Mapped[int] = mapped_column(default=100)
    flood_pct: Mapped[int] = mapped_column(default=100)
    drought_pct: Mapped[int] = mapped_column(default=100)
    plague_pct: Mapped[int] = mapped_column(default=100)
    route_danger: Mapped[int] = mapped_column(default=0)
    leak: Mapped[int] = mapped_column(default=0)
    leak_repair: Mapped[int] = mapped_column(default=0)
    sanity_erosion: Mapped[int] = mapped_column(default=0)
    fertility_decay: Mapped[int] = mapped_column(default=0)
    sea_pct: Mapped[int] = mapped_column(default=25)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
