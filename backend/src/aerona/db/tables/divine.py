from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import (
    CouncilMotion,
    DivineWoundKind,
    DomainActivity,
    DomainHook,
    GoalSource,
    GoalState,
    GodGoalKind,
    LawException,
    LawScope,
    OuterHunger,
    PenanceDeed,
    SonPunishment,
    VotingRule,
    WoundCause,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import PerceivedAlignment, WorshipMode
from aerona.domain.enums.law_grammar import LawCondition, LawOperator, LawTarget
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.outer import OuterFate
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import ExistenceMode

HOOK_PCT_MIN = -100
HOOK_PCT_MAX = 300


class WorldDomainHookRow(Base):
    __tablename__ = "world_domain_hooks"
    __table_args__ = (between("pct", HOOK_PCT_MIN, HOOK_PCT_MAX),)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    domain: Mapped[Domain] = mapped_column(enum_type(Domain, "domain"), primary_key=True)
    hook: Mapped[DomainHook] = mapped_column(enum_type(DomainHook, "hook"), primary_key=True)
    pct: Mapped[int] = mapped_column(default=100)


class DomainActivityRow(Base):
    __tablename__ = "domain_activity"
    __table_args__ = (at_least("count", 0), at_least("essence", 0), Index("ix_domain_activity_god_epoch", "god_node_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    domain: Mapped[Domain] = mapped_column(enum_type(Domain, "domain"))
    activity: Mapped[DomainActivity] = mapped_column(enum_type(DomainActivity, "activity"))
    count: Mapped[int] = mapped_column(default=0)
    essence: Mapped[int] = mapped_column(default=0)


class GodGoalRow(Base):
    __tablename__ = "son_goals"
    __table_args__ = (
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("amount", 0),
        Index("ix_son_goals_god_state", "god_node_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[GodGoalKind] = mapped_column(enum_type(GodGoalKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    domain: Mapped[Domain | None] = mapped_column(enum_type(Domain, "domain"))
    amount: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    state: Mapped[GoalState] = mapped_column(enum_type(GoalState, "state"), default=GoalState.ACTIVE)
    source: Mapped[GoalSource] = mapped_column(enum_type(GoalSource, "source"), default=GoalSource.ENGINE)
    since_epoch: Mapped[int] = mapped_column(default=0)
    closed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineStandingRow(Base):
    __tablename__ = "divine_standing"
    __table_args__ = (
        between("awe", PERCENT_MIN, PERCENT_MAX),
        between("love", PERCENT_MIN, PERCENT_MAX),
        between("fear", PERCENT_MIN, PERCENT_MAX),
        between("neglect", PERCENT_MIN, PERCENT_MAX),
        Index("ix_divine_standing_god", "god_node_id"),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    awe: Mapped[int] = mapped_column(default=0)
    love: Mapped[int] = mapped_column(default=0)
    fear: Mapped[int] = mapped_column(default=0)
    neglect: Mapped[int] = mapped_column(default=0)
    perceived: Mapped[PerceivedAlignment | None] = mapped_column(enum_type(PerceivedAlignment, "perceived"))
    mode: Mapped[WorshipMode | None] = mapped_column(enum_type(WorshipMode, "mode"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineWoundRow(Base):
    __tablename__ = "divine_wounds"
    __table_args__ = (
        between("severity", 1, PERCENT_MAX),
        between("healed", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("kind <> 'severed_domain' OR domain IS NOT NULL", name="severed_has_domain"),
        Index("ix_divine_wounds_god", "god_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[DivineWoundKind] = mapped_column(enum_type(DivineWoundKind, "kind"))
    domain: Mapped[Domain | None] = mapped_column(enum_type(Domain, "domain"))
    severity: Mapped[int] = mapped_column(default=50)
    healed: Mapped[int] = mapped_column(default=0)
    cause: Mapped[WoundCause] = mapped_column(enum_type(WoundCause, "cause"))
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    prior_mode: Mapped[ExistenceMode | None] = mapped_column(enum_type(ExistenceMode, "prior_mode"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AvatarRow(Base):
    __tablename__ = "avatars"
    __table_args__ = (Index("ix_avatars_god", "god_node_id"),)

    avatar_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    deeds: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CreatorTabooRow(Base):
    __tablename__ = "creator_taboos"
    __table_args__ = (between("severity", 1, PERCENT_MAX), at_least("broken", 0))

    act: Mapped[ActKind] = mapped_column(enum_type(ActKind, "act"), primary_key=True)
    creator_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    severity: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    broken: Mapped[int] = mapped_column(default=0)
    last_broken_epoch: Mapped[int | None]
    last_breaker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    answered_epoch: Mapped[int | None]


class WorldAttentionRow(Base):
    __tablename__ = "world_attention"
    __table_args__ = (between("attention", PERCENT_MIN, PERCENT_MAX),)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    attention: Mapped[int] = mapped_column(default=50)
    watched: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    far_epochs: Mapped[int] = mapped_column(default=0, server_default="0")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CouncilRulingRow(Base):
    __tablename__ = "council_rulings"
    __table_args__ = (Index("ix_council_rulings_active", "active", "motion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    council_id: Mapped[int | None] = mapped_column(ForeignKey("councils.id", ondelete="SET NULL"))
    motion: Mapped[CouncilMotion] = mapped_column(enum_type(CouncilMotion, "motion"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    school: Mapped[MagicSchool | None] = mapped_column(enum_type(MagicSchool, "school"))
    punishment: Mapped[SonPunishment | None] = mapped_column(enum_type(SonPunishment, "punishment"))
    penance_deed: Mapped[PenanceDeed | None] = mapped_column(enum_type(PenanceDeed, "penance_deed"))
    voting_rule: Mapped[VotingRule | None] = mapped_column(enum_type(VotingRule, "voting_rule"))
    epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    active: Mapped[bool] = mapped_column(default=True)
    enacted: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NaturalLawProfileRow(Base):
    __tablename__ = "natural_law_profiles"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("stability", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("scope = 'cosmos' OR world_id IS NOT NULL", name="scoped_has_world"),
        CheckConstraint("scope <> 'region' OR region_entity_id IS NOT NULL", name="region_has_region"),
    )

    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[NaturalLaw] = mapped_column(enum_type(NaturalLaw, "effect"))
    scope: Mapped[LawScope] = mapped_column(enum_type(LawScope, "scope"), default=LawScope.COSMOS)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=60)
    stability: Mapped[int] = mapped_column(default=80)
    author_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    exception: Mapped[LawException] = mapped_column(enum_type(LawException, "exception"), default=LawException.NONE)
    exempt_kind_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    contested: Mapped[bool] = mapped_column(default=False)
    target: Mapped[LawTarget | None] = mapped_column(enum_type(LawTarget, "target"))
    operator: Mapped[LawOperator | None] = mapped_column(enum_type(LawOperator, "operator"))
    key: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    value: Mapped[int] = mapped_column(default=100, server_default="100")
    condition: Mapped[LawCondition] = mapped_column(enum_type(LawCondition, "condition"), default=LawCondition.ALWAYS, server_default="always")
    until_epoch: Mapped[int | None]
    suspended: Mapped[bool] = mapped_column(default=False, server_default="0")
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OuterBeingProfileRow(Base):
    __tablename__ = "outer_being_profiles"
    __table_args__ = (at_least("fed", 0), at_least("reach", 0))

    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    hunger: Mapped[OuterHunger] = mapped_column(enum_type(OuterHunger, "hunger"))
    reach: Mapped[int] = mapped_column(default=1)
    fed: Mapped[int] = mapped_column(default=0)
    unfed_epochs: Mapped[int] = mapped_column(default=0, server_default="0")
    fate: Mapped[OuterFate] = mapped_column(enum_type(OuterFate, "fate"), default=OuterFate.ACTIVE, server_default="active")
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BreachPointRow(Base):
    __tablename__ = "breach_points"
    __table_args__ = (between("strength", 1, PERCENT_MAX), Index("ix_breach_points_outer", "outer_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    outer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=30)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
