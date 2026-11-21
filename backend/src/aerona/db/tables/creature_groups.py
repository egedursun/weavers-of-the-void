from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.creature_groups import GroupAim, GroupForm
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

RANKS_MAX = 10


class CreatureGroupRow(Base):
    __tablename__ = "creature_groups"
    __table_args__ = (
        at_least("size", 0),
        between("ranks", 0, RANKS_MAX),
        between("hunger", PERCENT_MIN, PERCENT_MAX),
        Index("ix_creature_groups_region", "region_entity_id"),
        Index("ix_creature_groups_species", "species_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    lair_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    form: Mapped[GroupForm] = mapped_column(enum_type(GroupForm, "form"), default=GroupForm.SOLITARY_RANGE)
    size: Mapped[int] = mapped_column(default=0)
    leader_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    leader_since_epoch: Mapped[int] = mapped_column(default=0)
    ranks: Mapped[int] = mapped_column(default=1)
    territory: Mapped[list[int]] = mapped_column(JSON, default=list)
    rivals: Mapped[list[int]] = mapped_column(JSON, default=list)
    hunger: Mapped[int] = mapped_column(default=30)
    aim: Mapped[GroupAim | None] = mapped_column(enum_type(GroupAim, "aim"))
    aim_until_epoch: Mapped[int] = mapped_column(default=0)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
