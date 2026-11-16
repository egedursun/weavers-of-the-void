from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperResponse, KeeperRole, SeekerAim, TruthAttitude


class HiddenTruthRow(Base):
    __tablename__ = "hidden_truths"
    __table_args__ = (between("strength", 0, 100), between("sanity_cost", 0, 100), Index("ix_hidden_truths_subject", "subject_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text, default="")
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[HiddenTruthKind] = mapped_column(enum_type(HiddenTruthKind, "kind"))
    hidden_from: Mapped[ConcealScope] = mapped_column(enum_type(ConcealScope, "hidden_from"), default=ConcealScope.EVERYONE)
    scope_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=60)
    by_oath: Mapped[bool] = mapped_column(default=False)
    by_law: Mapped[bool] = mapped_column(default=False)
    by_memory_removal: Mapped[bool] = mapped_column(default=False)
    by_cover_story: Mapped[bool] = mapped_column(default=False)
    by_discrediting: Mapped[bool] = mapped_column(default=False)
    by_isolation: Mapped[bool] = mapped_column(default=False)
    by_passing: Mapped[bool] = mapped_column(default=False)
    by_silencing: Mapped[bool] = mapped_column(default=False)
    by_neglect: Mapped[bool] = mapped_column(default=False)
    by_nature: Mapped[bool] = mapped_column(default=False)
    sanity_cost: Mapped[int] = mapped_column(default=0)
    accord_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    revealed: Mapped[bool] = mapped_column(default=False)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    tended_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TruthKeeperRow(Base):
    __tablename__ = "truth_keepers"
    __table_args__ = (UniqueConstraint("truth_id", "keeper_node_id", name="uq_truth_keepers"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    truth_id: Mapped[int] = mapped_column(ForeignKey("hidden_truths.id", ondelete="CASCADE"), index=True)
    keeper_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    role: Mapped[KeeperRole] = mapped_column(enum_type(KeeperRole, "role"), default=KeeperRole.MEMBER)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TruthSeekerRow(Base):
    __tablename__ = "truth_seekers"
    __table_args__ = (between("progress", 0, 100), UniqueConstraint("truth_id", "seeker_node_id", name="uq_truth_seekers"))

    id: Mapped[int] = mapped_column(primary_key=True)
    truth_id: Mapped[int] = mapped_column(ForeignKey("hidden_truths.id", ondelete="CASCADE"), index=True)
    seeker_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    aim: Mapped[SeekerAim] = mapped_column(enum_type(SeekerAim, "aim"), default=SeekerAim.UNDERSTAND)
    progress: Mapped[int] = mapped_column(default=0)
    began_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PublicKnowledgeRow(Base):
    __tablename__ = "public_knowledge"
    __table_args__ = (
        between("know_pct", 0, 100),
        between("believe_pct", 0, 100),
        UniqueConstraint("truth_id", "population_node_id", name="uq_public_knowledge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    truth_id: Mapped[int] = mapped_column(ForeignKey("hidden_truths.id", ondelete="CASCADE"), index=True)
    population_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    know_pct: Mapped[int] = mapped_column(default=0)
    believe_pct: Mapped[int] = mapped_column(default=0)
    attitude: Mapped[TruthAttitude] = mapped_column(enum_type(TruthAttitude, "attitude"), default=TruthAttitude.UNKNOWN)
    revealed_epoch: Mapped[int | None]
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BreachRow(Base):
    __tablename__ = "breaches"
    __table_args__ = (at_least("witnesses", 0), between("spread", 0, 100), Index("ix_breaches_truth", "truth_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    truth_id: Mapped[int] = mapped_column(ForeignKey("hidden_truths.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    cause: Mapped[BreachCause] = mapped_column(enum_type(BreachCause, "cause"))
    witnesses: Mapped[int] = mapped_column(default=0)
    witness_node_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    place_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    spread: Mapped[int] = mapped_column(default=0)
    response: Mapped[KeeperResponse] = mapped_column(enum_type(KeeperResponse, "response"), default=KeeperResponse.NONE)
