from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH
from aerona.db.authorship import HandAuthored
from aerona.db.base import Base, CreatedAtMixin, TimestampMixin
from aerona.db.columns import at_least, enum_type
from aerona.db.types import PydanticJSON
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.turn import TurnContext


class AgentTurnRow(TimestampMixin, Base):
    __tablename__ = "agent_turns"
    __table_args__ = (CheckConstraint("action_points_left IS NULL OR action_points_left >= 0", name="action_points_left_min"),)

    agent_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    agent_kind: Mapped[AgentKind] = mapped_column(enum_type(AgentKind, "agent_kind"))
    epoch: Mapped[int] = mapped_column(index=True)
    action_points_left: Mapped[int | None]
    context: Mapped[TurnContext] = mapped_column(PydanticJSON(TurnContext))
    finished: Mapped[bool] = mapped_column(default=False)


class TurnCounterRow(Base):
    __tablename__ = "turn_counters"
    __table_args__ = (at_least("value", 0),)

    agent_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    counter: Mapped[TurnCounter] = mapped_column(enum_type(TurnCounter, "counter"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)


class EpochAgentRow(Base):
    __tablename__ = "epoch_agents"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int]
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))


class ActionRecordRow(HandAuthored, CreatedAtMixin, Base):
    __tablename__ = "action_records"
    __table_args__ = (
        Index("ix_action_records_actor_epoch", "actor_node_id", "epoch"),
        Index("ix_action_records_kind_epoch", "kind", "epoch"),
        Index("ix_action_records_target", "target_node_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    actor_kind: Mapped[ActorKind] = mapped_column(enum_type(ActorKind, "actor_kind"))
    actor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[ActionKind] = mapped_column(enum_type(ActionKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id", ondelete="SET NULL"))
    essence_spent: Mapped[int] = mapped_column(default=0)
    summary: Mapped[str | None] = mapped_column(String(LEDGER_SUMMARY_MAX_LENGTH))
    detail: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)


class CreationRewardRow(Base):
    __tablename__ = "creation_rewards"
    __table_args__ = (
        at_least("xp", 0),
        at_least("renown", 0),
        at_least("essence", 0),
        at_least("cost", 0),
        CheckConstraint("taken_back_pct BETWEEN 0 AND 100", name="taken_back_range"),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), index=True)
    epoch: Mapped[int]
    xp: Mapped[int] = mapped_column(default=0)
    renown: Mapped[int] = mapped_column(default=0)
    essence: Mapped[int] = mapped_column(default=0)
    cost: Mapped[int] = mapped_column(default=0)
    land: Mapped[bool] = mapped_column(default=False)
    thread_id: Mapped[int | None] = mapped_column(ForeignKey("threads.id", ondelete="SET NULL"))
    thread_reverted: Mapped[bool] = mapped_column(default=False)
    fade_pct: Mapped[int] = mapped_column(default=100)
    repeats: Mapped[int] = mapped_column(default=0)
    partner_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    partner_xp: Mapped[int] = mapped_column(default=0)
    partner_renown: Mapped[int] = mapped_column(default=0)
    partner_cost: Mapped[int] = mapped_column(default=0)
    taken_back_pct: Mapped[int] = mapped_column(default=0)
    reason: Mapped[str | None] = mapped_column(String(LEDGER_SUMMARY_MAX_LENGTH))
