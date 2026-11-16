from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.creator import (
    ChosenFavour,
    CovenantDuty,
    CovenantState,
    CreatorHeresy,
    CreatorNature,
    CreatorPromise,
    CreatorSignKind,
    CreatorStance,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.limits import PERCENT_MAX

STANDING_FIELDS = ("awe", "love", "dread", "gratitude", "resentment", "ignorance", "stance", "heresy")
COVENANT_FIELDS = ("duty", "promise", "seal_sign", "state", "until_epoch", "breaches")
CHOSEN_FIELDS = ("favour",)
DEPICTION_FIELDS = ("name", "nature", "aspect")


class CreatorStandingRow(Base):
    __tablename__ = "creator_standing"
    __table_args__ = tuple(between(name, 0, PERCENT_MAX) for name in ("awe", "love", "dread", "gratitude", "resentment", "ignorance"))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    awe: Mapped[int] = mapped_column(default=20)
    love: Mapped[int] = mapped_column(default=10)
    dread: Mapped[int] = mapped_column(default=10)
    gratitude: Mapped[int] = mapped_column(default=10)
    resentment: Mapped[int] = mapped_column(default=0)
    ignorance: Mapped[int] = mapped_column(default=50)
    stance: Mapped[CreatorStance] = mapped_column(enum_type(CreatorStance, "stance"), default=CreatorStance.INDIFFERENCE)
    heresy: Mapped[CreatorHeresy] = mapped_column(enum_type(CreatorHeresy, "heresy"), default=CreatorHeresy.NONE)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CovenantRow(Base):
    __tablename__ = "covenants"
    __table_args__ = (at_least("breaches", 0), Index("ix_covenants_people", "people_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    duty: Mapped[CovenantDuty] = mapped_column(enum_type(CovenantDuty, "duty"))
    promise: Mapped[CreatorPromise] = mapped_column(enum_type(CreatorPromise, "promise"))
    seal_sign: Mapped[CreatorSignKind] = mapped_column(enum_type(CreatorSignKind, "seal_sign"), default=CreatorSignKind.COVENANT_OFFER)
    state: Mapped[CovenantState] = mapped_column(enum_type(CovenantState, "state"), default=CovenantState.OFFERED)
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    breaches: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CreatorChosenRow(Base):
    __tablename__ = "creator_chosen"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    favour: Mapped[ChosenFavour] = mapped_column(enum_type(ChosenFavour, "favour"), default=ChosenFavour.RENOWN)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CreatorDepictionRow(Base):
    __tablename__ = "creator_depictions"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    nature: Mapped[CreatorNature] = mapped_column(enum_type(CreatorNature, "nature"), default=CreatorNature.MAKER)
    aspect: Mapped[Domain | None] = mapped_column(enum_type(Domain, "aspect"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
