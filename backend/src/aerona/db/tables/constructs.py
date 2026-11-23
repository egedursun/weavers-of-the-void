from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.constructs import CommandToken, InstructionBinding, OrderCondition, OrderKind, OrderTime
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind

CONSTRUCT_FIELDS = ("material", "power_source", "power", "upkeep", "maker_entity_id", "decay", "soul_entity_id")
SET_FIELDS = ("binding", "command_token", "token_entity_id", "holder_node_id", "kill_switch", "kill_token_entity_id", "literalness")
ORDER_FIELDS = ("kind", "target_node_id", "priority", "condition", "until_epoch", "times", "lapsed")
REMADE_FIELDS = ("lost_function", "forced_function", "sentenced_by_entity_id", "grievance", "bound_to_entity_id")


class ConstructRow(Base):
    __tablename__ = "constructs"
    __table_args__ = (
        between("power", PERCENT_MIN, PERCENT_MAX),
        at_least("upkeep", 0),
        between("decay", PERCENT_MIN, PERCENT_MAX),
        Index("ix_constructs_maker", "maker_entity_id"),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    material: Mapped[MaterialKind] = mapped_column(enum_type(MaterialKind, "material"), default=MaterialKind.STONE)
    power_source: Mapped[MagicSource] = mapped_column(enum_type(MagicSource, "power_source"), default=MagicSource.LEY)
    power: Mapped[int] = mapped_column(default=80)
    upkeep: Mapped[int] = mapped_column(default=5)
    maker_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    decay: Mapped[int] = mapped_column(default=0)
    soul_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    made_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InstructionSetRow(Base):
    __tablename__ = "instruction_sets"
    __table_args__ = (between("literalness", PERCENT_MIN, PERCENT_MAX), Index("ix_instruction_sets_owner", "owner_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    binding: Mapped[InstructionBinding] = mapped_column(enum_type(InstructionBinding, "binding"), default=InstructionBinding.ORDER)
    command_token: Mapped[CommandToken] = mapped_column(enum_type(CommandToken, "command_token"), default=CommandToken.NONE)
    token_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kill_switch: Mapped[bool] = mapped_column(default=False)
    kill_token_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    literalness: Mapped[int] = mapped_column(default=80)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InstructionOrderRow(Base):
    __tablename__ = "instruction_orders"
    __table_args__ = (at_least("priority", 0), Index("ix_instruction_orders_set", "set_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("instruction_sets.id", ondelete="CASCADE"))
    kind: Mapped[OrderKind] = mapped_column(enum_type(OrderKind, "kind"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    priority: Mapped[int] = mapped_column(default=1)
    condition: Mapped[OrderCondition] = mapped_column(enum_type(OrderCondition, "condition"), default=OrderCondition.ALWAYS)
    until_epoch: Mapped[int | None]
    times: Mapped[OrderTime | None] = mapped_column(enum_type(OrderTime, "times"))
    lapsed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RemadeRow(Base):
    __tablename__ = "remade"
    __table_args__ = (between("grievance", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_remade_sentenced_by", "sentenced_by_entity_id"))

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    lost_function: Mapped[BodyFunction | None] = mapped_column(enum_type(BodyFunction, "lost_function"))
    forced_function: Mapped[BodyFunction | None] = mapped_column(enum_type(BodyFunction, "forced_function"))
    sentenced_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"))
    bound_to_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    grievance: Mapped[int] = mapped_column(default=30)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
