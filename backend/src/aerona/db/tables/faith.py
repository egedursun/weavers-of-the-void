from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.faith import (
    AfterlifeState,
    BindingKind,
    ClergyFunction,
    FanaticismKind,
    HoldingKind,
    JudgementDoctrine,
    RebirthPath,
    ReincarnationGate,
    SpiritAlignment,
    StratumActivity,
    StratumAdmission,
    StratumContact,
    StratumKind,
    StratumPermanence,
    StratumValence,
    TenetKind,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.living import LivingCraftStance
from aerona.domain.enums.made import MadeMindStance, RelicStance
from aerona.domain.enums.powers import GiftedStance


class CultDoctrineRow(Base):
    __tablename__ = "cult_doctrines"
    __table_args__ = (
        between("orthodoxy", PERCENT_MIN, PERCENT_MAX),
        between("tithe_rate", PERCENT_MIN, PERCENT_MAX),
        between("clergy_quality", PERCENT_MIN, PERCENT_MAX),
        at_least("clergy_count", 0),
        at_least("treasury", 0),
    )

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    judgement: Mapped[JudgementDoctrine] = mapped_column(enum_type(JudgementDoctrine, "judgement"), default=JudgementDoctrine.DEEDS)
    orthodoxy: Mapped[int] = mapped_column(default=50)
    tithe_rate: Mapped[int] = mapped_column(default=10)
    treasury: Mapped[int] = mapped_column(default=0)
    clergy_count: Mapped[int] = mapped_column(default=0)
    clergy_quality: Mapped[int] = mapped_column(default=0)
    liturgical_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    parent_cult_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    doctrinal_distance: Mapped[int] = mapped_column(default=0)
    zeal_parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    fanaticism: Mapped[FanaticismKind | None] = mapped_column(enum_type(FanaticismKind, "fanaticism"))
    fanaticism_epoch: Mapped[int | None]
    excommunicated: Mapped[list[int]] = mapped_column(JSON, default=list)
    rebirth_path: Mapped[RebirthPath] = mapped_column(enum_type(RebirthPath, "rebirth_path"), default=RebirthPath.PEOPLE)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    made_mind_stance: Mapped[MadeMindStance] = mapped_column(enum_type(MadeMindStance, "made_mind_stance"), default=MadeMindStance.SILENT)
    copy_stance: Mapped[MadeMindStance] = mapped_column(enum_type(MadeMindStance, "copy_stance"), default=MadeMindStance.SILENT)
    augment_stance: Mapped[MadeMindStance] = mapped_column(enum_type(MadeMindStance, "augment_stance"), default=MadeMindStance.SILENT)
    made_afterlife_stance: Mapped[MadeMindStance] = mapped_column(enum_type(MadeMindStance, "made_afterlife_stance"), default=MadeMindStance.SILENT)
    relic_stance: Mapped[RelicStance] = mapped_column(enum_type(RelicStance, "relic_stance"), default=RelicStance.HERITAGE)
    power_stance: Mapped[GiftedStance] = mapped_column(enum_type(GiftedStance, "power_stance"), default=GiftedStance.SILENT, server_default="silent")
    living_craft_stance: Mapped[LivingCraftStance] = mapped_column(
        enum_type(LivingCraftStance, "living_craft_stance"), default=LivingCraftStance.SILENT, server_default="silent"
    )
    germline_stance: Mapped[LivingCraftStance] = mapped_column(
        enum_type(LivingCraftStance, "germline_stance"), default=LivingCraftStance.SILENT, server_default="silent"
    )
    clone_stance: Mapped[LivingCraftStance] = mapped_column(
        enum_type(LivingCraftStance, "clone_stance"), default=LivingCraftStance.SILENT, server_default="silent"
    )
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CultTenetRow(Base):
    __tablename__ = "cult_tenets"

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    tenet: Mapped[TenetKind] = mapped_column(enum_type(TenetKind, "tenet"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    target: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    since_epoch: Mapped[int] = mapped_column(default=0)
    revealed_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))


class CultHoldingRow(Base):
    __tablename__ = "cult_holdings"
    __table_args__ = (Index("ix_cult_holdings_holding", "holding_entity_id"),)

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holding_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[HoldingKind] = mapped_column(enum_type(HoldingKind, "kind"))
    since_epoch: Mapped[int] = mapped_column(default=0)


class CultOfficeRow(Base):
    __tablename__ = "cult_offices"
    __table_args__ = (Index("ix_cult_offices_cult", "cult_entity_id", "kind"), Index("ix_cult_offices_holder", "holder_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ClergyFunction] = mapped_column(enum_type(ClergyFunction, "kind"))
    holder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class HeresyRow(Base):
    __tablename__ = "heresies"
    __table_args__ = (between("distance", PERCENT_MIN, PERCENT_MAX),)

    heresy_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    parent_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    distance: Mapped[int] = mapped_column(default=0)
    declared_epoch: Mapped[int]
    suppressed: Mapped[bool] = mapped_column(default=False)
    tolerated: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RelicRow(Base):
    __tablename__ = "relics"
    __table_args__ = (between("sanctity", PERCENT_MIN, PERCENT_MAX), at_least("pilgrims", 0))

    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    saint_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    shrine_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sanctity: Mapped[int] = mapped_column(default=50)
    pilgrims: Mapped[int] = mapped_column(default=0)
    canonised_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpiritProfileRow(Base):
    __tablename__ = "spirit_profiles"
    __table_args__ = (
        between("memory_strength", PERCENT_MIN, PERCENT_MAX),
        between("veneration", PERCENT_MIN, PERCENT_MAX),
        between("seal_strength", PERCENT_MIN, PERCENT_MAX),
    )

    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    origin_mortal_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    imprint: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    deeds: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    binding: Mapped[BindingKind] = mapped_column(enum_type(BindingKind, "binding"), default=BindingKind.NONE)
    bound_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    memory_strength: Mapped[int] = mapped_column(default=100)
    veneration: Mapped[int] = mapped_column(default=0)
    alignment: Mapped[SpiritAlignment] = mapped_column(enum_type(SpiritAlignment, "alignment"), default=SpiritAlignment.NEUTRAL)
    state: Mapped[AfterlifeState] = mapped_column(enum_type(AfterlifeState, "state"), default=AfterlifeState.WANDERING)
    stratum_id: Mapped[int | None] = mapped_column(ForeignKey("afterlife_strata.id", ondelete="SET NULL"), index=True)
    rite: Mapped[FuneralCustom] = mapped_column(enum_type(FuneralCustom, "rite"), default=FuneralCustom.NONE)
    patron_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    sealed: Mapped[bool] = mapped_column(default=False)
    seal_strength: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AfterlifeStratumRow(Base):
    __tablename__ = "afterlife_strata"
    __table_args__ = (Index("ix_afterlife_strata_realm", "realm_entity_id"), at_least("population", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    realm_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[StratumKind] = mapped_column(enum_type(StratumKind, "kind"))
    valence: Mapped[StratumValence] = mapped_column(enum_type(StratumValence, "valence"), default=StratumValence.NEUTRAL, server_default="neutral")
    permanence: Mapped[StratumPermanence] = mapped_column(
        enum_type(StratumPermanence, "permanence"), default=StratumPermanence.ETERNAL, server_default="eternal"
    )
    admission: Mapped[StratumAdmission] = mapped_column(enum_type(StratumAdmission, "admission"), default=StratumAdmission.ALL, server_default="all")
    activity: Mapped[StratumActivity] = mapped_column(enum_type(StratumActivity, "activity"), default=StratumActivity.REST, server_default="rest")
    contact: Mapped[StratumContact] = mapped_column(enum_type(StratumContact, "contact"), default=StratumContact.BY_RITE, server_default="by_rite")
    ruler_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    population: Mapped[int] = mapped_column(default=0)
    closed: Mapped[bool] = mapped_column(default=False)
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)


class SoulJudgementRow(Base):
    __tablename__ = "soul_judgements"
    __table_args__ = (Index("ix_soul_judgements_spirit", "spirit_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    doctrine: Mapped[JudgementDoctrine] = mapped_column(enum_type(JudgementDoctrine, "doctrine"))
    stratum_id: Mapped[int | None] = mapped_column(ForeignKey("afterlife_strata.id", ondelete="SET NULL"))
    score: Mapped[int] = mapped_column(default=0)
    rite: Mapped[FuneralCustom] = mapped_column(enum_type(FuneralCustom, "rite"), default=FuneralCustom.NONE)
    reason: Mapped[str] = mapped_column(Text, default="")
    epoch: Mapped[int]


class PossessionRow(Base):
    __tablename__ = "possessions"
    __table_args__ = (between("stress", PERCENT_MIN, PERCENT_MAX),)

    host_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    since_epoch: Mapped[int]
    stress: Mapped[int] = mapped_column(default=0)
    host_values: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReincarnationRow(Base):
    __tablename__ = "reincarnations"

    id: Mapped[int] = mapped_column(primary_key=True)
    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    past_mortal_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    newborn_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    gate: Mapped[ReincarnationGate] = mapped_column(enum_type(ReincarnationGate, "gate"))
    path: Mapped[RebirthPath] = mapped_column(enum_type(RebirthPath, "path"), default=RebirthPath.PEOPLE)
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    memory_pct: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int]
