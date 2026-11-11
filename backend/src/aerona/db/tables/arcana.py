from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.arcana import LawSource, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

GRAMMAR_FIELDS = ("technique", "form", "range", "duration", "target", "paradigm_entity_id", "myth_entity_id")
LAB_TEXT_FIELDS = ("fidelity", "rite_entity_id")
WARPING_FIELDS = ("value", "stage")
LONGEVITY_FIELDS = ("form", "dose", "dependence", "years_gained", "lapsed_epochs")
UPKEEP_FIELDS = ("caster_node_id", "source", "essence_upkeep", "vis_form", "vis_upkeep", "dispel_resistance", "unpaid_epochs")


class RiteGrammarRow(Base):
    __tablename__ = "rite_grammar"
    __table_args__ = (at_least("difficulty", 0),)

    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[SpellTechnique] = mapped_column(enum_type(SpellTechnique, "technique"))
    form: Mapped[SpellForm] = mapped_column(enum_type(SpellForm, "form"))
    range: Mapped[SpellRange] = mapped_column(enum_type(SpellRange, "range"), default=SpellRange.SIGHT)
    duration: Mapped[SpellDuration] = mapped_column(enum_type(SpellDuration, "duration"), default=SpellDuration.INSTANT)
    target: Mapped[SpellTarget] = mapped_column(enum_type(SpellTarget, "target"), default=SpellTarget.ONE)
    difficulty: Mapped[int] = mapped_column(default=0)
    paradigm_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    myth_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LabTextRow(Base):
    __tablename__ = "lab_texts"
    __table_args__ = (between("fidelity", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_lab_texts_rite", "rite_entity_id"))

    book_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    author_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fidelity: Mapped[int] = mapped_column(default=80)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VisStockRow(Base):
    __tablename__ = "vis_stocks"
    __table_args__ = (at_least("amount", 0),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[SpellForm] = mapped_column(enum_type(SpellForm, "form"), primary_key=True)
    amount: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WarpingRow(Base):
    __tablename__ = "warping"
    __table_args__ = (between("value", PERCENT_MIN, PERCENT_MAX), at_least("stage", 0), at_least("updated_epoch", 0))

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    stage: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LongevityRow(Base):
    __tablename__ = "longevity"
    __table_args__ = (
        at_least("dose", 0),
        between("dependence", PERCENT_MIN, PERCENT_MAX),
        at_least("years_gained", 0),
        at_least("lapsed_epochs", 0),
        at_least("since_epoch", 0),
    )

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[SpellForm] = mapped_column(enum_type(SpellForm, "form"), default=SpellForm.BODY)
    dose: Mapped[int] = mapped_column(default=1)
    dependence: Mapped[int] = mapped_column(default=0)
    years_gained: Mapped[int] = mapped_column(default=0)
    lapsed_epochs: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LawUpkeepRow(Base):
    __tablename__ = "law_upkeep"
    __table_args__ = (
        at_least("essence_upkeep", 0),
        at_least("vis_upkeep", 0),
        between("dispel_resistance", PERCENT_MIN, PERCENT_MAX),
        at_least("unpaid_epochs", 0),
        Index("ix_law_upkeep_caster", "caster_node_id"),
    )

    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    caster_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    source: Mapped[LawSource] = mapped_column(enum_type(LawSource, "source"), default=LawSource.AUTHORED)
    essence_upkeep: Mapped[int] = mapped_column(default=0)
    vis_form: Mapped[SpellForm | None] = mapped_column(enum_type(SpellForm, "vis_form"))
    vis_upkeep: Mapped[int] = mapped_column(default=0)
    dispel_resistance: Mapped[int] = mapped_column(default=50)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
