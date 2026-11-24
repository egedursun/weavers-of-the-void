from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import IngredientRole, MealSlot
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

FLAVOURS = ("sweet", "sour", "saline", "bitter", "savoury", "pungent", "cooling", "numbing", "smoky", "fermented", "astringent", "rich")
DISH_FIELDS = (
    "name",
    "description",
    "world_id",
    "origin_node_id",
    "method",
    "course",
    "category",
    "nourishment",
    "delight",
    "keeps",
    "prestige",
    "prep_skill",
    "technique",
    "retired",
    *FLAVOURS,
    "derived_from_id",
    "built_in",
)
STEP_FIELDS = ("method", "duration")


class DishRow(KindRow):
    __tablename__ = "dishes"
    __table_args__ = (
        *(between(flavour, PERCENT_MIN, PERCENT_MAX) for flavour in FLAVOURS),
        between("prep_skill", PERCENT_MIN, PERCENT_MAX),
        between("nourishment", PERCENT_MIN, PERCENT_MAX),
        between("delight", PERCENT_MIN, PERCENT_MAX),
        at_least("keeps", 0),
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        Index("ix_dishes_world", "world_id"),
        Index("ix_dishes_origin", "origin_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
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
    built_in: Mapped[bool] = mapped_column(default=False, server_default=false())
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("dishes.id", ondelete="SET NULL"))
    category: Mapped[MealSlot] = mapped_column(enum_type(MealSlot, "category"), default=MealSlot.DAILY_MEAL, server_default=MealSlot.DAILY_MEAL.value)
    prep_skill: Mapped[int] = mapped_column(default=20, server_default="20")
    sweet: Mapped[int] = mapped_column(default=0, server_default="0")
    sour: Mapped[int] = mapped_column(default=0, server_default="0")
    saline: Mapped[int] = mapped_column(default=0, server_default="0")
    bitter: Mapped[int] = mapped_column(default=0, server_default="0")
    savoury: Mapped[int] = mapped_column(default=0, server_default="0")
    pungent: Mapped[int] = mapped_column(default=0, server_default="0")
    cooling: Mapped[int] = mapped_column(default=0, server_default="0")
    numbing: Mapped[int] = mapped_column(default=0, server_default="0")
    smoky: Mapped[int] = mapped_column(default=0, server_default="0")
    fermented: Mapped[int] = mapped_column(default=0, server_default="0")
    astringent: Mapped[int] = mapped_column(default=0, server_default="0")
    rich: Mapped[int] = mapped_column(default=0, server_default="0")


class DishIngredientRow(Base):
    __tablename__ = "dish_ingredients"
    __table_args__ = (between("share", 1, PERCENT_MAX),)

    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    share: Mapped[int] = mapped_column(default=50)
    role: Mapped[IngredientRole] = mapped_column(enum_type(IngredientRole, "role"), default=IngredientRole.BASE, server_default=IngredientRole.BASE.value)
    good_kind_id: Mapped[int | None] = mapped_column(ForeignKey("good_kinds.id", ondelete="SET NULL"))


class DishStepRow(Base):
    __tablename__ = "dish_steps"
    __table_args__ = (
        UniqueConstraint("dish_id", "step", name="uq_dish_steps_dish_step"),
        at_least("step", 1),
        between("duration", 0, 1000),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), index=True)
    step: Mapped[int] = mapped_column(default=1)
    method: Mapped[CookingMethod] = mapped_column(enum_type(CookingMethod, "method"))
    duration: Mapped[int] = mapped_column(default=1)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CommunityDishRow(Base):
    __tablename__ = "community_dishes"
    __table_args__ = (
        between("popularity", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        at_least("cooked", 0),
        at_least("short_epochs", 0),
        Index("ix_community_dishes_dish", "dish_id"),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True)
    popularity: Mapped[int] = mapped_column(default=50)
    cooked: Mapped[int] = mapped_column(default=0)
    short_epochs: Mapped[int] = mapped_column(default=0, server_default="0")
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
