from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.ecology import Aversion, AwakeningTrigger, BreathKind, GazeKind, Habitat, Temperament, TissueMaterial
from aerona.domain.enums.material import MaterialKind


class CreatureAnatomyRow(Base):
    __tablename__ = "creature_anatomy"
    __table_args__ = (at_least("limbs", 0), at_least("heads", 1), at_least("wings", 0), at_least("tails", 0))

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    limbs: Mapped[int] = mapped_column(default=4)
    heads: Mapped[int] = mapped_column(default=1)
    wings: Mapped[int] = mapped_column(default=0)
    tails: Mapped[int] = mapped_column(default=0)
    skin: Mapped[TissueMaterial] = mapped_column(enum_type(TissueMaterial, "skin"), default=TissueMaterial.HIDE)
    bone: Mapped[TissueMaterial] = mapped_column(enum_type(TissueMaterial, "bone"), default=TissueMaterial.BONE)
    breath: Mapped[BreathKind | None] = mapped_column(enum_type(BreathKind, "breath"))
    bite: Mapped[PackageKind | None] = mapped_column(enum_type(PackageKind, "bite"))
    gaze: Mapped[GazeKind | None] = mapped_column(enum_type(GazeKind, "gaze"))
    temperament: Mapped[Temperament] = mapped_column(enum_type(Temperament, "temperament"), default=Temperament.PLACID)
    hoards: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "hoards"))
    hates: Mapped[Aversion | None] = mapped_column(enum_type(Aversion, "hates"))
    awakening: Mapped[AwakeningTrigger | None] = mapped_column(enum_type(AwakeningTrigger, "awakening"))
    habitat: Mapped[Habitat] = mapped_column(enum_type(Habitat, "habitat"), default=Habitat.LAND)
    generated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


register_profile_table(CreatureAnatomyRow.__tablename__, "node_id")
