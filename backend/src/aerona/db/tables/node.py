from types import MappingProxyType
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import enum_type
from aerona.domain.enums.node import NodeKind


class NodeRow(CreatedAtMixin, Base):
    __tablename__ = "nodes"
    __table_args__: tuple[Any, ...] = (Index("ix_nodes_kind_name", "kind", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[NodeKind] = mapped_column(enum_type(NodeKind, "node_kind"), index=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))

    __mapper_args__ = MappingProxyType({"polymorphic_on": "kind", "polymorphic_abstract": True})


class NameRegistryRow(Base):
    __tablename__ = "name_registry"

    normalized: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), unique=True)
    display: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    single_word: Mapped[bool]


class NodeBirthRow(Base):
    __tablename__ = "node_births"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    year: Mapped[int]
    season: Mapped[int | None]
    day: Mapped[int | None]
    hour: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
