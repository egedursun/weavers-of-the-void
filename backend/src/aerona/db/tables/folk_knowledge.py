from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.folk_knowledge import FolkDomain, FolkTaking, LoreHolders, LoreTransmission
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class FolkKnowledgeRow(Base):
    __tablename__ = "folk_knowledge"
    __table_args__ = (
        UniqueConstraint("people_entity_id", "domain", name="uq_folk_knowledge_people_domain"),
        between("depth", PERCENT_MIN, PERCENT_MAX),
        between("accuracy", PERCENT_MIN, PERCENT_MAX),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    domain: Mapped[FolkDomain] = mapped_column(enum_type(FolkDomain, "domain"))
    depth: Mapped[int] = mapped_column(default=20)
    accuracy: Mapped[int] = mapped_column(default=40)
    holders: Mapped[LoreHolders] = mapped_column(enum_type(LoreHolders, "holders"), default=LoreHolders.ELDERS)
    transmission: Mapped[LoreTransmission] = mapped_column(enum_type(LoreTransmission, "transmission"), default=LoreTransmission.ORAL)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FolkClassRow(Base):
    __tablename__ = "folk_classes"
    __table_args__ = (
        at_least("learned_epoch", 0),
        Index("ix_folk_classes_people", "people_entity_id", "domain"),
        Index("ix_folk_classes_grouped", "grouped_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    domain: Mapped[FolkDomain] = mapped_column(enum_type(FolkDomain, "domain"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    grouped_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="CASCADE"))
    taken_as: Mapped[FolkTaking] = mapped_column(enum_type(FolkTaking, "taken_as"), default=FolkTaking.HARMLESS)
    misclassified: Mapped[bool] = mapped_column(default=False)
    learned_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
