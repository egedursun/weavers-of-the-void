from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import (
    AppealKind,
    CircleKind,
    ContestEnd,
    ContestKind,
    ContestStake,
    GroupKind,
    PassionKind,
    PassionSource,
    PersuasionAim,
    RelationType,
)


class RelationshipRow(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        between("friendship", RELATION_MIN, RELATION_MAX),
        between("romance", PERCENT_MIN, PERCENT_MAX),
        between("familiarity", PERCENT_MIN, PERCENT_MAX),
        between("rivalry", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        UniqueConstraint("holder_node_id", "subject_node_id", name="uq_relationships_pair"),
        Index("ix_relationships_subject", "subject_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    friendship: Mapped[int] = mapped_column(default=0)
    romance: Mapped[int] = mapped_column(default=0)
    familiarity: Mapped[int] = mapped_column(default=0)
    rivalry: Mapped[int] = mapped_column(default=0)
    kinds: Mapped[list[str]] = mapped_column(JSON, default=list)
    affair: Mapped[bool] = mapped_column(default=False)
    affair_known: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int]
    last_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)

    @validates("kinds")
    def _typed_kinds(self, _key: str, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - set(RelationType))
        if unknown:
            raise ValueError(f"A relationship can only be of a known kind, not {', '.join(unknown)}.")
        return value


class SocialCircleRow(Base):
    __tablename__ = "social_circles"
    __table_args__ = (at_least("founded_epoch", 0), Index("ix_social_circles_place", "meeting_place_id"))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[CircleKind] = mapped_column(enum_type(CircleKind, "kind"))
    taste_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "axis"))
    meeting_place_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ideology_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PassionRow(Base):
    __tablename__ = "passions"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        UniqueConstraint("holder_node_id", "kind", "object_node_id", name="uq_passions_holder_kind_object"),
        Index("ix_passions_object", "object_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[PassionKind] = mapped_column(enum_type(PassionKind, "kind"))
    object_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    strength: Mapped[int]
    source: Mapped[PassionSource] = mapped_column(enum_type(PassionSource, "source"))
    since_epoch: Mapped[int]
    invoked_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GroupRankRow(Base):
    __tablename__ = "group_ranks"
    __table_args__ = (at_least("rank", 1), between("dominance", PERCENT_MIN, PERCENT_MAX), Index("ix_group_ranks_member", "member_node_id"))

    group_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    group_kind: Mapped[GroupKind] = mapped_column(enum_type(GroupKind, "group_kind"))
    rank: Mapped[int]
    dominance: Mapped[int]
    since_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ContestRow(Base):
    __tablename__ = "contests"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("wager", 0),
        Index("ix_contests_challenger", "challenger_node_id"),
        Index("ix_contests_defender", "defender_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ContestKind] = mapped_column(enum_type(ContestKind, "kind"))
    stake: Mapped[ContestStake] = mapped_column(enum_type(ContestStake, "stake"))
    challenger_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    defender_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    judge_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    stake_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    place_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    wager: Mapped[int] = mapped_column(default=0)
    rounds: Mapped[list[list[float]]] = mapped_column(JSON, default=list)
    outcome: Mapped[ContestEnd] = mapped_column(enum_type(ContestEnd, "outcome"))
    famous: Mapped[bool] = mapped_column(default=False)
    work_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class PersuasionRow(Base):
    __tablename__ = "persuasions"
    __table_args__ = (at_least("epoch", 0), Index("ix_persuasions_target", "target_node_id"), Index("ix_persuasions_speaker", "speaker_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    speaker_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    appeal: Mapped[AppealKind] = mapped_column(enum_type(AppealKind, "appeal"))
    aim: Mapped[PersuasionAim] = mapped_column(enum_type(PersuasionAim, "aim"))
    axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "axis"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    score: Mapped[int]
    success: Mapped[bool]
    epoch: Mapped[int]
