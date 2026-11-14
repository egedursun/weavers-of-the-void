from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.belonging import FugitiveKind, IdentityLayer, PlayKind, SalienceDriver, SanctuaryKind, SanctuaryState, SatireSource
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.society import SocialClass

IDENTITY_FIELDS = ("value_node_id", "value_label", "strength", "salience", "driver")
PEER_GROUP_FIELDS = ("settlement_entity_id", "social_class", "play", "children", "cohesion", "deprived", "dissolved_epoch")
PEER_MEMBER_FIELDS = ("deprived_epochs",)
SANCTUARY_FIELDS = ("host_entity_id", "kind", "fugitive_kind", "pursuer_entity_id", "state", "fee", "siege_epochs")
SANCTUARY_LAW_FIELDS = ("restricted", "fee_pct")
SATIRE_FIELDS = ("satirist_entity_id", "target_entity_id", "polity_entity_id", "work_entity_id", "source", "bite", "tolerated", "punished", "judged")


class HeldIdentityRow(Base):
    __tablename__ = "held_identities"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("salience", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
        Index("ix_held_identities_value", "value_node_id"),
    )

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    layer: Mapped[IdentityLayer] = mapped_column(enum_type(IdentityLayer, "layer"), primary_key=True)
    value_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    value_label: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    strength: Mapped[int] = mapped_column(default=50)
    salience: Mapped[int] = mapped_column(default=30)
    driver: Mapped[SalienceDriver] = mapped_column(enum_type(SalienceDriver, "driver"), default=SalienceDriver.BASELINE)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PeerGroupRow(Base):
    __tablename__ = "peer_groups"
    __table_args__ = (
        at_least("children", 0),
        between("cohesion", PERCENT_MIN, PERCENT_MAX),
        at_least("formed_epoch", 0),
        Index("ix_peer_groups_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"))
    play: Mapped[PlayKind] = mapped_column(enum_type(PlayKind, "play"), default=PlayKind.GAMES)
    children: Mapped[int] = mapped_column(default=0)
    cohesion: Mapped[int] = mapped_column(default=40)
    deprived: Mapped[bool] = mapped_column(default=False)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    dissolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PeerMemberRow(Base):
    __tablename__ = "peer_members"
    __table_args__ = (at_least("joined_epoch", 0), at_least("deprived_epochs", 0))

    group_id: Mapped[int] = mapped_column(ForeignKey("peer_groups.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    deprived_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SanctuaryRow(Base):
    __tablename__ = "sanctuaries"
    __table_args__ = (
        at_least("fee", 0),
        at_least("granted_epoch", 0),
        at_least("siege_epochs", 0),
        Index("ix_sanctuaries_fugitive", "fugitive_entity_id"),
        Index("ix_sanctuaries_host", "host_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fugitive_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    host_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SanctuaryKind] = mapped_column(enum_type(SanctuaryKind, "kind"))
    fugitive_kind: Mapped[FugitiveKind] = mapped_column(enum_type(FugitiveKind, "fugitive_kind"))
    pursuer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    state: Mapped[SanctuaryState] = mapped_column(enum_type(SanctuaryState, "state"), default=SanctuaryState.SHELTERED)
    fee: Mapped[int] = mapped_column(default=0)
    granted_epoch: Mapped[int] = mapped_column(default=0)
    siege_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SanctuaryLawRow(Base):
    __tablename__ = "sanctuary_laws"
    __table_args__ = (between("fee_pct", PERCENT_MIN, PERCENT_MAX),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    restricted: Mapped[bool] = mapped_column(default=False)
    fee_pct: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SatireRow(Base):
    __tablename__ = "satires"
    __table_args__ = (
        between("bite", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_satires_target", "target_entity_id"),
        Index("ix_satires_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    satirist_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    work_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    source: Mapped[SatireSource] = mapped_column(enum_type(SatireSource, "source"), default=SatireSource.MORTAL)
    bite: Mapped[int] = mapped_column(default=20)
    tolerated: Mapped[bool] = mapped_column(default=True)
    punished: Mapped[bool] = mapped_column(default=False)
    judged: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
