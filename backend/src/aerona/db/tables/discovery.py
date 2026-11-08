from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import (
    AgeKind,
    AnomalyKind,
    ArtDiscipline,
    BlueprintKind,
    BlueprintSource,
    EraDeed,
    GreatField,
    ResearchIncident,
    TheoryDomain,
)
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


class TheoryProfileRow(Base):
    __tablename__ = "theory_profiles"
    __table_args__ = (between("correctness", 0, PERCENT_MAX), between("explanatory_power", 0, PERCENT_MAX))

    theory_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    domain: Mapped[TheoryDomain] = mapped_column(enum_type(TheoryDomain, "domain"))
    claim: Mapped[str] = mapped_column(Text, default="")
    correctness: Mapped[int] = mapped_column(default=50)
    explanatory_power: Mapped[int] = mapped_column(default=30)
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founding_book_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    rival_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    endorsed_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    condemned_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    revealed_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TheoryAdherentRow(Base):
    __tablename__ = "theory_adherents"
    __table_args__ = (between("strength", 0, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_theory_adherents_adherent", "adherent_entity_id"))

    theory_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    adherent_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=30)
    orthodox: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TheoryAnomalyRow(Base):
    __tablename__ = "theory_anomalies"
    __table_args__ = (at_least("weight", 0), at_least("epoch", 0), Index("ix_theory_anomalies_theory", "theory_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    theory_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[AnomalyKind] = mapped_column(enum_type(AnomalyKind, "kind"))
    weight: Mapped[int] = mapped_column(default=1)
    witness_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)


class ParadigmShiftRow(Base):
    __tablename__ = "paradigm_shifts"
    __table_args__ = (at_least("epoch", 0), Index("ix_paradigm_shifts_community", "community_entity_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    domain: Mapped[TheoryDomain] = mapped_column(enum_type(TheoryDomain, "domain"))
    old_theory_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    new_theory_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)


class ArtFormProfileRow(Base):
    __tablename__ = "art_form_profiles"
    __table_args__ = (between("difficulty", 0, PERCENT_MAX), between("prestige", 0, PERCENT_MAX))

    art_form_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    discipline: Mapped[ArtDiscipline] = mapped_column(enum_type(ArtDiscipline, "discipline"))
    structure: Mapped[dict[str, str | int]] = mapped_column(JSON, default=dict)
    origin_culture_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    difficulty: Mapped[int] = mapped_column(default=40)
    prestige: Mapped[int] = mapped_column(default=30)
    sacred: Mapped[bool] = mapped_column(default=False)
    notation: Mapped[bool] = mapped_column(default=False)
    occasions: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArtFormPractitionerRow(Base):
    __tablename__ = "art_form_practitioners"
    __table_args__ = (between("mastery", 0, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_art_form_practitioners_who", "practitioner_entity_id"))

    art_form_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    practitioner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mastery: Mapped[int] = mapped_column(default=20)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NameMeaningRow(Base):
    __tablename__ = "name_meanings"
    __table_args__ = (at_least("epoch", 0),)

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    gloss: Mapped[str] = mapped_column(Text, default="")
    morphemes: Mapped[list[str]] = mapped_column(JSON, default=list)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NameExonymRow(Base):
    __tablename__ = "name_exonyms"
    __table_args__ = (at_least("epoch", 0), Index("ix_name_exonyms_language", "language_entity_id"))

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    language_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    gloss: Mapped[str] = mapped_column(Text, default="")
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EpithetRow(Base):
    __tablename__ = "epithets"
    __table_args__ = (at_least("epoch", 0),)

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epithet: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    gloss: Mapped[str] = mapped_column(Text, default="")
    deed: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="")
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
