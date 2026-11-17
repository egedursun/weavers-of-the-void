from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.kind_crafts import (
    ColourFocus,
    ColourMeaning,
    EmblemSystem,
    EnsembleRole,
    FurnishingCategory,
    GarmentCategory,
    InstrumentCategory,
    MusicForm,
    ScentUse,
    SubstanceCategory,
    ToolCategory,
    WearingRule,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import SkillKind

VALUE_MAX = 1000


def percent(*columns: str) -> tuple[object, ...]:
    return tuple(between(column, PERCENT_MIN, PERCENT_MAX) for column in columns)


class GarmentKindRow(KindRow):
    __tablename__ = "garment_kinds"
    __table_args__ = (
        *percent("warmth", "protection", "status_signal", "modesty", "prestige", "fashion", "novelty"),
        between("layer", 0, 5),
        between("cost", 0, VALUE_MAX),
        at_least("created_epoch", 0),
    )

    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("garment_kinds.id", ondelete="SET NULL"))
    category: Mapped[GarmentCategory] = mapped_column(enum_type(GarmentCategory, "category"))
    wearing_rule: Mapped[WearingRule] = mapped_column(enum_type(WearingRule, "wearing_rule"), default=WearingRule.ANYONE)
    layer: Mapped[int] = mapped_column(default=1)
    warmth: Mapped[int] = mapped_column(default=30)
    protection: Mapped[int] = mapped_column(default=10)
    cost: Mapped[int] = mapped_column(default=20)
    status_signal: Mapped[int] = mapped_column(default=10)
    modesty: Mapped[int] = mapped_column(default=50)
    prestige: Mapped[int] = mapped_column(default=10)
    fashion: Mapped[int] = mapped_column(default=50)
    novelty: Mapped[int] = mapped_column(default=80)


class ColourTermRow(KindRow):
    __tablename__ = "colour_terms"
    __table_args__ = (*percent("rarity", "prestige"), between("stage", 1, 11), at_least("created_epoch", 0))

    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("colour_terms.id", ondelete="SET NULL"))
    category: Mapped[ColourFocus] = mapped_column(enum_type(ColourFocus, "category"))
    stage: Mapped[int] = mapped_column(default=1)
    rarity: Mapped[int] = mapped_column(default=10)
    prestige: Mapped[int] = mapped_column(default=10)


class ColourMeaningRow(Base):
    __tablename__ = "colour_meanings"
    __table_args__ = (
        UniqueConstraint("colour_term_id", "culture_node_id", "meaning", name="uq_colour_meanings_term_culture_meaning"),
        between("weight", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_colour_meanings_culture", "culture_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    colour_term_id: Mapped[int] = mapped_column(ForeignKey("colour_terms.id", ondelete="CASCADE"), index=True)
    culture_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    meaning: Mapped[ColourMeaning] = mapped_column(enum_type(ColourMeaning, "meaning"), default=ColourMeaning.NONE)
    weight: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ScentKindRow(KindRow):
    __tablename__ = "scent_kinds"
    __table_args__ = (*percent("prestige", "rite_weight"), between("trade_value", 0, VALUE_MAX), at_least("created_epoch", 0))

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("scent_kinds.id", ondelete="SET NULL"))
    category: Mapped[ScentUse] = mapped_column(enum_type(ScentUse, "category"))
    prestige: Mapped[int] = mapped_column(default=10)
    rite_weight: Mapped[int] = mapped_column(default=20)
    trade_value: Mapped[int] = mapped_column(default=10)


class EmblemSystemRow(KindRow):
    __tablename__ = "emblem_systems"
    __table_args__ = (*percent("complexity", "legibility", "prestige"), at_least("created_epoch", 0))

    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("emblem_systems.id", ondelete="SET NULL"))
    category: Mapped[EmblemSystem] = mapped_column(enum_type(EmblemSystem, "category"))
    complexity: Mapped[int] = mapped_column(default=40)
    legibility: Mapped[int] = mapped_column(default=60)
    prestige: Mapped[int] = mapped_column(default=20)


class FurnishingKindRow(KindRow):
    __tablename__ = "furnishing_kinds"
    __table_args__ = (*percent("comfort", "prestige"), between("cost", 0, VALUE_MAX), at_least("created_epoch", 0))

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("furnishing_kinds.id", ondelete="SET NULL"))
    category: Mapped[FurnishingCategory] = mapped_column(enum_type(FurnishingCategory, "category"))
    comfort: Mapped[int] = mapped_column(default=30)
    prestige: Mapped[int] = mapped_column(default=10)
    cost: Mapped[int] = mapped_column(default=20)


class ToolKindRow(KindRow):
    __tablename__ = "tool_kinds"
    __table_args__ = (*percent("craft_bonus", "quality", "wear"), at_least("created_epoch", 0))

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("tool_kinds.id", ondelete="SET NULL"))
    category: Mapped[ToolCategory] = mapped_column(enum_type(ToolCategory, "category"))
    skill: Mapped[SkillKind | None] = mapped_column(enum_type(SkillKind, "skill"))
    craft_bonus: Mapped[int] = mapped_column(default=10)
    quality: Mapped[int] = mapped_column(default=40)
    wear: Mapped[int] = mapped_column(default=20)


class InstrumentKindRow(KindRow):
    __tablename__ = "instrument_kinds"
    __table_args__ = (*percent("range_span", "loudness", "prestige"), at_least("created_epoch", 0))

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("instrument_kinds.id", ondelete="SET NULL"))
    category: Mapped[InstrumentCategory] = mapped_column(enum_type(InstrumentCategory, "category"))
    ensemble_role: Mapped[EnsembleRole] = mapped_column(enum_type(EnsembleRole, "ensemble_role"), default=EnsembleRole.ACCOMPANIMENT)
    range_span: Mapped[int] = mapped_column(default=40)
    loudness: Mapped[int] = mapped_column(default=40)
    prestige: Mapped[int] = mapped_column(default=10)


class MusicTraditionRow(KindRow):
    __tablename__ = "music_traditions"
    __table_args__ = (
        *percent("rhythm_complexity", "rite_weight", "prestige"),
        between("scale_steps", 2, 48),
        between("ensemble_size", 1, 500),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("music_traditions.id", ondelete="SET NULL"))
    category: Mapped[MusicForm] = mapped_column(enum_type(MusicForm, "category"))
    scale_steps: Mapped[int] = mapped_column(default=7)
    rhythm_complexity: Mapped[int] = mapped_column(default=40)
    ensemble_size: Mapped[int] = mapped_column(default=4)
    rite_weight: Mapped[int] = mapped_column(default=30)
    prestige: Mapped[int] = mapped_column(default=10)


class SubstanceKindRow(KindRow):
    __tablename__ = "substance_kinds"
    __table_args__ = (*percent("potency", "dependence", "harm", "rite_weight"), between("trade_value", 0, VALUE_MAX), at_least("created_epoch", 0))

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("substance_kinds.id", ondelete="SET NULL"))
    category: Mapped[SubstanceCategory] = mapped_column(enum_type(SubstanceCategory, "category"))
    potency: Mapped[int] = mapped_column(default=30)
    dependence: Mapped[int] = mapped_column(default=20)
    harm: Mapped[int] = mapped_column(default=10)
    rite_weight: Mapped[int] = mapped_column(default=10)
    trade_value: Mapped[int] = mapped_column(default=20)
