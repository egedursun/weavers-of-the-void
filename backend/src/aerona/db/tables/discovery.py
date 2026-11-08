from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, BlueprintKind, BlueprintSource, EraDeed, GreatField, ResearchIncident
from aerona.domain.enums.society import KnowledgeBranch

PERCENT_MAX = 100


class GreatPointsRow(Base):
    __tablename__ = "great_person_points"
    __table_args__ = (at_least("points", 0), at_least("updated_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    field: Mapped[GreatField] = mapped_column(enum_type(GreatField, "field"), primary_key=True)
    points: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GreatPersonRow(Base):
    __tablename__ = "great_people"
    __table_args__ = (at_least("promoted_epoch", 0), Index("ix_great_people_holder", "holder_entity_id"))

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    field: Mapped[GreatField] = mapped_column(enum_type(GreatField, "field"))
    holder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    promoted_epoch: Mapped[int] = mapped_column(default=0)
    deed_done: Mapped[bool] = mapped_column(default=False)
    deed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PolityEraRow(Base):
    __tablename__ = "polity_eras"
    __table_args__ = (between("score", -1000, 1000), at_least("since_epoch", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[int] = mapped_column(default=0)
    age: Mapped[AgeKind] = mapped_column(enum_type(AgeKind, "age"), default=AgeKind.NORMAL)
    since_epoch: Mapped[int] = mapped_column(default=0)
    lowest: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EraDeedRow(Base):
    __tablename__ = "era_deeds"
    __table_args__ = (at_least("epoch", 0), Index("ix_era_deeds_polity", "polity_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    deed: Mapped[EraDeed] = mapped_column(enum_type(EraDeed, "deed"))
    points: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))


class WorldEraRow(Base):
    __tablename__ = "world_eras"
    __table_args__ = (at_least("era", 1), at_least("since_epoch", 0))

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    era: Mapped[int] = mapped_column(default=1)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ResearchIncidentRow(Base):
    __tablename__ = "research_incidents"
    __table_args__ = (
        between("severity", 0, PERCENT_MAX),
        at_least("dead", 0),
        at_least("epoch", 0),
        Index("ix_research_incidents_holder", "holder_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ResearchIncident] = mapped_column(enum_type(ResearchIncident, "kind"))
    technique: Mapped[Technique | None] = mapped_column(enum_type(Technique, "technique"))
    branch: Mapped[KnowledgeBranch | None] = mapped_column(enum_type(KnowledgeBranch, "branch"))
    severity: Mapped[int] = mapped_column(default=0)
    dead: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class ArtifactStudyRow(Base):
    __tablename__ = "artifact_studies"
    __table_args__ = (between("progress", 0, PERCENT_MAX), at_least("epoch", 0), Index("ix_artifact_studies_item", "item_entity_id"))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"))
    progress: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BannedWorkRow(Base):
    __tablename__ = "banned_works"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_banned_works_work", "work_entity_id"))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    work_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BlueprintRow(Base):
    __tablename__ = "blueprints"
    __table_args__ = (between("quality", 0, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_blueprints_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    kind: Mapped[BlueprintKind] = mapped_column(enum_type(BlueprintKind, "kind"))
    subject: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    book_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    source: Mapped[BlueprintSource] = mapped_column(enum_type(BlueprintSource, "source"), default=BlueprintSource.DRAWN)
    licensed_to: Mapped[list[int]] = mapped_column(JSON, default=list)
    quality: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
