from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.couplings import (
    CarrionRest,
    FieldAgreementKind,
    FieldAgreementState,
    RestraintKind,
    RiteComponent,
    SealKind,
    SignCause,
    SociolectKind,
    TeachingState,
)
from aerona.domain.enums.knowledge import KnowledgeKind

SOCIOLECT_FIELDS = ("kind", "prestige", "secret", "salience", "faded_epoch")
SIGN_FIELDS = ("community_entity_id", "cause")
CARRION_FIELDS = ("carrion", "scavenged", "preserved", "rest", "kept")
TEACHING_FIELDS = ("kind", "fidelity", "state", "price")
FIELD_AGREEMENT_FIELDS = ("kind", "state", "term_epoch", "honour")
SEAL_FIELDS = ("kind", "strength", "decay", "pact_oath_id", "power_id", "living_line_id", "made_mind_id")
NOVELTY_FIELDS = ("novelty", "adoption", "revivals")


class RiteComponentRow(Base):
    __tablename__ = "rite_components"

    rite_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    component: Mapped[RiteComponent] = mapped_column(enum_type(RiteComponent, "component"), primary_key=True)


class CaptiveRestraintRow(Base):
    __tablename__ = "captive_restraints"

    captive_id: Mapped[int] = mapped_column(ForeignKey("captives.id", ondelete="CASCADE"), primary_key=True)
    restraint: Mapped[RestraintKind] = mapped_column(enum_type(RestraintKind, "restraint"), primary_key=True)


class SociolectRow(Base):
    __tablename__ = "sociolects"
    __table_args__ = (
        between("prestige", -100, 100),
        between("salience", 0, 100),
        at_least("since_epoch", 0),
        Index("ix_sociolects_language", "language_entity_id"),
        Index("ix_sociolects_holder", "holder_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SociolectKind] = mapped_column(enum_type(SociolectKind, "kind"))
    prestige: Mapped[int] = mapped_column(default=0)
    secret: Mapped[bool] = mapped_column(default=False)
    salience: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    faded_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SignOriginRow(Base):
    __tablename__ = "sign_origins"
    __table_args__ = (at_least("since_epoch", 0),)

    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    cause: Mapped[SignCause] = mapped_column(enum_type(SignCause, "cause"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CarrionPulseRow(Base):
    __tablename__ = "carrion_pulses"
    __table_args__ = (at_least("carrion", 0), at_least("scavenged", 0), at_least("epoch", 0))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    carrion: Mapped[int] = mapped_column(default=0)
    scavenged: Mapped[int] = mapped_column(default=0)
    preserved: Mapped[bool] = mapped_column(default=False)
    rest: Mapped[CarrionRest] = mapped_column(enum_type(CarrionRest, "rest"), default=CarrionRest.ROTTING)
    kept: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TeachingRow(Base):
    __tablename__ = "teachings"
    __table_args__ = (
        between("fidelity", 0, 100),
        at_least("price", 0),
        at_least("epoch", 0),
        Index("ix_teachings_teacher", "teacher_node_id"),
        Index("ix_teachings_learner", "learner_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    learner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[KnowledgeKind] = mapped_column(enum_type(KnowledgeKind, "kind"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    fidelity: Mapped[int] = mapped_column(default=80)
    state: Mapped[TeachingState] = mapped_column(enum_type(TeachingState, "state"), default=TeachingState.TAUGHT)
    price: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FieldAgreementRow(Base):
    __tablename__ = "field_agreements"
    __table_args__ = (between("honour", -100, 100), at_least("epoch", 0), Index("ix_field_agreements_war", "war_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    kind: Mapped[FieldAgreementKind] = mapped_column(enum_type(FieldAgreementKind, "kind"))
    state: Mapped[FieldAgreementState] = mapped_column(enum_type(FieldAgreementState, "state"), default=FieldAgreementState.KEPT)
    commander_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    counterpart_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    term_epoch: Mapped[int | None]
    honour: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeepSealRow(Base):
    __tablename__ = "deep_seals"
    __table_args__ = (between("strength", 0, 100), between("decay", 0, 100), at_least("epoch", 0), Index("ix_deep_seals_place", "place_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    passage_id: Mapped[int | None] = mapped_column(ForeignKey("deep_passages.id", ondelete="SET NULL"))
    kind: Mapped[SealKind] = mapped_column(enum_type(SealKind, "kind"))
    strength: Mapped[int] = mapped_column(default=60)
    decay: Mapped[int] = mapped_column(default=5)
    sealer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    pact_oath_id: Mapped[int | None] = mapped_column(ForeignKey("oaths.id", ondelete="SET NULL"))
    power_id: Mapped[int | None] = mapped_column(ForeignKey("powers.id", ondelete="SET NULL"))
    living_line_id: Mapped[int | None] = mapped_column(ForeignKey("living_lines.id", ondelete="SET NULL"))
    made_mind_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    broken_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NoveltyStockRow(Base):
    __tablename__ = "novelty_stocks"
    __table_args__ = (between("novelty", 0, 100), between("adoption", 0, 100), at_least("revivals", 0), at_least("updated_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    novelty: Mapped[int] = mapped_column(default=80)
    adoption: Mapped[int] = mapped_column(default=0)
    peak_epoch: Mapped[int | None]
    revivals: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
