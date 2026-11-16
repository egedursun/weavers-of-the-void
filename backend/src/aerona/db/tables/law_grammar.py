from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_grammar import LawExceptionKind, LawOperator

EXCEPTION_FIELDS = ("kind", "node_id", "entity_type")
THEORY_FIELDS = ("believed_operator", "believed_value", "confidence", "adapted_epochs")


class LawExceptionRow(Base):
    __tablename__ = "natural_law_exceptions"
    __table_args__ = (Index("ix_natural_law_exceptions_law", "law_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[LawExceptionKind] = mapped_column(enum_type(LawExceptionKind, "kind"))
    node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    entity_type: Mapped[EntityType | None] = mapped_column(enum_type(EntityType, "entity_type"))
    note: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LawTheoryRow(Base):
    __tablename__ = "law_theories"
    __table_args__ = (Index("ix_law_theories_holder", "holder_node_id"), Index("ix_law_theories_law", "law_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    believed_operator: Mapped[LawOperator] = mapped_column(enum_type(LawOperator, "believed_operator"))
    believed_value: Mapped[int] = mapped_column(default=100)
    confidence: Mapped[int] = mapped_column(default=20)
    adapted_epochs: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
