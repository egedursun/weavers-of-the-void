from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.domain.enums.society import KnowledgeBranch


class PlaceProfileRow(Base):
    __tablename__ = "place_profiles"
    __table_args__ = (between("sacredness", PERCENT_MIN, PERCENT_MAX), at_least("pilgrims", 0))

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[PlaceKind] = mapped_column(enum_type(PlaceKind, "kind"), index=True)
    sacredness: Mapped[int] = mapped_column(default=0)
    pilgrims: Mapped[int] = mapped_column(default=0)
    secrets_seeded: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PlaceSecretRow(Base):
    __tablename__ = "place_secrets"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        Index("ix_place_secrets_place", "place_entity_id", "revealed_epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SecretKind] = mapped_column(enum_type(SecretKind, "kind"))
    strength: Mapped[int]
    sealed: Mapped[bool] = mapped_column(default=False)
    held: Mapped[bool] = mapped_column(default=False)
    origin: Mapped[SecretOrigin] = mapped_column(enum_type(SecretOrigin, "origin"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    school: Mapped[MagicSchool | None] = mapped_column(enum_type(MagicSchool, "school"))
    branch: Mapped[KnowledgeBranch | None] = mapped_column(enum_type(KnowledgeBranch, "branch"))
    hidden_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    subject_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    created_epoch: Mapped[int]
    revealed_epoch: Mapped[int | None]
    revealed_by: Mapped[DiscoveryMode | None] = mapped_column(enum_type(DiscoveryMode, "revealed_by"))
    revealed_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    released_epoch: Mapped[int | None]
    result_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
