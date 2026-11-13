from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

DISH_FIELDS = ("name", "description", "world_id", "origin_node_id", "method", "course", "nourishment", "delight", "keeps", "prestige", "technique", "retired")


class DishRow(Base):
    __tablename__ = "dishes"
    __table_args__ = (
        between("nourishment", PERCENT_MIN, PERCENT_MAX),
        between("delight", PERCENT_MIN, PERCENT_MAX),
        at_least("keeps", 0),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        Index("ix_dishes_world", "world_id"),
        Index("ix_dishes_origin", "origin_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    method: Mapped[CookingMethod] = mapped_column(enum_type(CookingMethod, "method"))
    course: Mapped[DishCourse] = mapped_column(enum_type(DishCourse, "course"), default=DishCourse.STAPLE)
    nourishment: Mapped[int] = mapped_column(default=40)
    delight: Mapped[int] = mapped_column(default=30)
    keeps: Mapped[int] = mapped_column(default=1)
    prestige: Mapped[int] = mapped_column(default=10)
    technique: Mapped[Technique | None] = mapped_column(enum_type(Technique, "technique"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    retired: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DishIngredientRow(Base):
    __tablename__ = "dish_ingredients"
    __table_args__ = (between("share", 1, PERCENT_MAX),)

    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    share: Mapped[int] = mapped_column(default=50)


class CommunityDishRow(Base):
    __tablename__ = "community_dishes"
    __table_args__ = (
        between("popularity", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        at_least("cooked", 0),
        Index("ix_community_dishes_dish", "dish_id"),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True)
    popularity: Mapped[int] = mapped_column(default=50)
    cooked: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
