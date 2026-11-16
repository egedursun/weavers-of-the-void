from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.son import PowerEffect

DIVINE_POWER_FIELDS = ("name", "verb", "object", "object_key", "scope", "mode", "cost", "cost_amount", "cooldown", "strength")


class DivinePowerRow(Base):
    __tablename__ = "divine_powers"
    __table_args__ = (
        between("strength", 0, PERCENT_MAX),
        at_least("cost_amount", 0),
        at_least("cooldown", 0),
        Index("ix_divine_powers_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    verb: Mapped[DivineVerb] = mapped_column(enum_type(DivineVerb, "verb"))
    object: Mapped[DivineObject] = mapped_column(enum_type(DivineObject, "object"))
    object_key: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    scope: Mapped[DivineScope] = mapped_column(enum_type(DivineScope, "scope"), default=DivineScope.COMMUNITY)
    mode: Mapped[DivineMode] = mapped_column(enum_type(DivineMode, "mode"), default=DivineMode.PASSIVE)
    cost: Mapped[DivineCost] = mapped_column(enum_type(DivineCost, "cost"), default=DivineCost.ESSENCE)
    cost_amount: Mapped[int] = mapped_column(default=5)
    cooldown: Mapped[int] = mapped_column(default=0)
    strength: Mapped[int] = mapped_column(default=20)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    son_preset: Mapped[PowerEffect | None] = mapped_column(enum_type(PowerEffect, "son_preset"))
    foreign_preset: Mapped[ForeignGodPowerEffect | None] = mapped_column(enum_type(ForeignGodPowerEffect, "foreign_preset"))
    last_used_epoch: Mapped[int | None]
    granted_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
