from sqlalchemy import CheckConstraint, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.society import Commodity, SocialClass


class CommunitySocietyRow(Base):
    __tablename__ = "community_societies"
    __table_args__ = (
        *(CheckConstraint(f"share_{item.value} BETWEEN 0 AND 100", name=f"share_{item.value}_range") for item in SocialClass),
        *(between(f"satisfaction_{item.value}", PERCENT_MIN, PERCENT_MAX) for item in SocialClass),
        *(CheckConstraint(f"stock_{item.value} >= 0", name=f"stock_{item.value}_min") for item in Commodity),
        *(CheckConstraint(f"price_{item.value} >= 0", name=f"price_{item.value}_min") for item in Commodity),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    share_farmer: Mapped[float] = mapped_column(Float)
    share_artisan: Mapped[float] = mapped_column(Float)
    share_merchant: Mapped[float] = mapped_column(Float)
    share_priest: Mapped[float] = mapped_column(Float)
    share_warrior: Mapped[float] = mapped_column(Float)
    share_scribe: Mapped[float] = mapped_column(Float)
    satisfaction_farmer: Mapped[int]
    satisfaction_artisan: Mapped[int]
    satisfaction_merchant: Mapped[int]
    satisfaction_priest: Mapped[int]
    satisfaction_warrior: Mapped[int]
    satisfaction_scribe: Mapped[int]
    stock_food: Mapped[int]
    stock_ore: Mapped[int]
    stock_goods: Mapped[int]
    price_food: Mapped[int]
    price_ore: Mapped[int]
    price_goods: Mapped[int]
    golden_age_since_epoch: Mapped[int | None]
    currency_id: Mapped[int | None] = mapped_column(ForeignKey("currencies.id", ondelete="SET NULL"))

    def share(self, social_class: SocialClass) -> float:
        value: float = getattr(self, f"share_{social_class.value}")
        return value

    def satisfaction(self, social_class: SocialClass) -> int:
        value: int = getattr(self, f"satisfaction_{social_class.value}")
        return value

    def stock(self, commodity: Commodity) -> int:
        value: int = getattr(self, f"stock_{commodity.value}")
        return value

    def price(self, commodity: Commodity) -> int:
        value: int = getattr(self, f"price_{commodity.value}")
        return value


class CommunityRelationRow(Base):
    __tablename__ = "community_relations"
    __table_args__ = (CheckConstraint("entity_a_id < entity_b_id", name="ordered_pair"), between("value", RELATION_MIN, RELATION_MAX))

    entity_a_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    entity_b_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    value: Mapped[int] = mapped_column(default=0)
    blood_feud_since_epoch: Mapped[int | None]


class AddictionRow(Base):
    __tablename__ = "addictions"
    __table_args__ = (at_least("owned_epochs", 0),)

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    resource_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    owned_epochs: Mapped[int] = mapped_column(default=0)
    addicted_since_epoch: Mapped[int | None]
    withdrawal_since_epoch: Mapped[int | None]


class ReverenceRow(CreatedAtMixin, Base):
    __tablename__ = "reverences"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    since_epoch: Mapped[int]


class ResurrectionOrderRow(Base):
    __tablename__ = "resurrection_orders"

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"), index=True)
    completed_epoch: Mapped[int | None]


class SoulRow(Base):
    __tablename__ = "souls"

    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    origin_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    realm_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    descended_epoch: Mapped[int]
    bound_to_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    harvested_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class ArchiveHoldingRow(Base):
    __tablename__ = "archive_holdings"

    archive_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    knowledge_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    reader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
