from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import BeliefStance, CreatureDeed, CreatureLesson, DivineScale, MagicSiteKind, Manifestation, PerceivedAlignment
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

SCALE_MIN = -3
SCALE_MAX = 3

DESIGN_FIELDS = ("budget", "dominion_strength", "magic_aptitude", "manifestation_strength", "rank")
IMAGE_FIELDS = ("believed_alignment", "believed_wrath", "believed_mercy", "believed_domain", "manifestation", "stance")
MIRACLE_FIELDS = ("magnitude", "witnesses", "need", "novelty", "legibility", "belief", "credited_node_id")
MAGIC_SITE_FIELDS = ("kind", "school", "strength", "found_epoch", "holder_node_id", "output", "target_world_id")
THRONE_FIELDS = ("power", "holder_node_id", "since_epoch")
CREATURE_FIELDS = ("hunger", "neglect_epochs", "last_deed")


class DominionRow(Base):
    __tablename__ = "dominions"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_dominions_region", "region_entity_id"),
    )

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=0)
    temples: Mapped[int] = mapped_column(default=0)
    holy_sites: Mapped[int] = mapped_column(default=0)
    prophets: Mapped[int] = mapped_column(default=0)
    miracles: Mapped[int] = mapped_column(default=0)
    worship: Mapped[int] = mapped_column(default=0)
    spread: Mapped[int] = mapped_column(default=0)
    trend: Mapped[int] = mapped_column(default=0, server_default="0")
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RegionDominionRow(Base):
    __tablename__ = "region_dominion"
    __table_args__ = (
        between("share", PERCENT_MIN, PERCENT_MAX),
        Index("ix_region_dominion_god", "god_node_id"),
    )

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    share: Mapped[int] = mapped_column(default=0)
    rivals: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class GodScaleRow(Base):
    __tablename__ = "god_scales"
    __table_args__ = (between("value", SCALE_MIN, SCALE_MAX),)

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    scale: Mapped[DivineScale] = mapped_column(enum_type(DivineScale, "scale"), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GodDesignRow(Base):
    __tablename__ = "god_designs"
    __table_args__ = (
        at_least("budget", 0),
        at_least("spent", 0),
        between("dominion_strength", PERCENT_MIN, PERCENT_MAX),
        between("magic_aptitude", PERCENT_MIN, PERCENT_MAX),
        between("manifestation_strength", PERCENT_MIN, PERCENT_MAX),
        at_least("rank", 0),
        between("stats_pct", PERCENT_MIN, PERCENT_MAX),
    )

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    budget: Mapped[int] = mapped_column(default=0)
    spent: Mapped[int] = mapped_column(default=0)
    dominion_strength: Mapped[int] = mapped_column(default=0)
    magic_aptitude: Mapped[int] = mapped_column(default=0)
    manifestation_strength: Mapped[int] = mapped_column(default=0)
    stats_pct: Mapped[int] = mapped_column(default=PERCENT_MAX)
    rank: Mapped[int] = mapped_column(default=0)
    checked_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GodImageRow(Base):
    __tablename__ = "god_images"
    __table_args__ = (
        between("believed_wrath", PERCENT_MIN, PERCENT_MAX),
        between("believed_mercy", PERCENT_MIN, PERCENT_MAX),
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("worship_share", PERCENT_MIN, PERCENT_MAX),
        between("crisis", PERCENT_MIN, PERCENT_MAX),
        between("malleability", PERCENT_MIN, PERCENT_MAX),
        at_least("pull", 0),
    )

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    believed_alignment: Mapped[PerceivedAlignment] = mapped_column(enum_type(PerceivedAlignment, "believed_alignment"), default=PerceivedAlignment.AMBIVALENT)
    believed_wrath: Mapped[int] = mapped_column(default=50)
    believed_mercy: Mapped[int] = mapped_column(default=50)
    believed_domain: Mapped[Domain | None] = mapped_column(enum_type(Domain, "believed_domain"))
    manifestation: Mapped[Manifestation] = mapped_column(enum_type(Manifestation, "manifestation"), default=Manifestation.SERENE)
    intensity: Mapped[int] = mapped_column(default=0)
    worship_share: Mapped[int] = mapped_column(default=0)
    crisis: Mapped[int] = mapped_column(default=0)
    malleability: Mapped[int] = mapped_column(default=0)
    pull: Mapped[int] = mapped_column(default=0)
    domain_pressure: Mapped[int] = mapped_column(default=0)
    stance: Mapped[BeliefStance] = mapped_column(enum_type(BeliefStance, "stance"), default=BeliefStance.YIELD)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MiracleRecordRow(Base):
    __tablename__ = "miracle_records"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("magnitude", 0),
        at_least("witnesses", 0),
        between("need", PERCENT_MIN, PERCENT_MAX),
        between("novelty", PERCENT_MIN, PERCENT_MAX),
        between("legibility", PERCENT_MIN, PERCENT_MAX),
        at_least("belief", 0),
        Index("ix_miracle_records_god", "god_node_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    epoch: Mapped[int] = mapped_column(default=0)
    magnitude: Mapped[int] = mapped_column(default=0)
    witnesses: Mapped[int] = mapped_column(default=0)
    need: Mapped[int] = mapped_column(default=0)
    novelty: Mapped[int] = mapped_column(default=PERCENT_MAX)
    legibility: Mapped[int] = mapped_column(default=PERCENT_MAX)
    belief: Mapped[int] = mapped_column(default=0)
    credited_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MagicSiteRow(Base):
    __tablename__ = "magic_sites"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("output", 0),
        Index("ix_magic_sites_place", "place_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[MagicSiteKind] = mapped_column(enum_type(MagicSiteKind, "kind"))
    school: Mapped[MagicSchool] = mapped_column(enum_type(MagicSchool, "school"))
    strength: Mapped[int] = mapped_column(default=50)
    found_epoch: Mapped[int | None]
    found_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    output: Mapped[int] = mapped_column(default=0)
    target_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ThroneRow(Base):
    __tablename__ = "thrones"
    __table_args__ = (
        between("power", PERCENT_MIN, PERCENT_MAX),
        Index("ix_thrones_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    power: Mapped[int] = mapped_column(default=50)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineCreatureRow(Base):
    __tablename__ = "divine_creatures"
    __table_args__ = (
        between("hunger", PERCENT_MIN, PERCENT_MAX),
        at_least("neglect_epochs", 0),
        at_least("deeds", 0),
        Index("ix_divine_creatures_god", "god_node_id"),
    )

    creature_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    weights: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    hunger: Mapped[int] = mapped_column(default=0)
    neglect_epochs: Mapped[int] = mapped_column(default=0)
    last_deed: Mapped[CreatureDeed | None] = mapped_column(enum_type(CreatureDeed, "last_deed"))
    deeds: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CreatureLessonRow(Base):
    __tablename__ = "creature_lessons"
    __table_args__ = (
        at_least("epoch", 0),
        between("strength", PERCENT_MIN, PERCENT_MAX),
        Index("ix_creature_lessons_creature", "creature_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    creature_entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("divine_creatures.creature_entity_id", ondelete="CASCADE"))
    deed: Mapped[CreatureDeed] = mapped_column(enum_type(CreatureDeed, "deed"))
    lesson: Mapped[CreatureLesson] = mapped_column(enum_type(CreatureLesson, "lesson"))
    strength: Mapped[int] = mapped_column(default=50)
    epoch: Mapped[int] = mapped_column(default=0)
