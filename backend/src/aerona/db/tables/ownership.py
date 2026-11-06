from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least

LEDGER_COLUMNS = ("revenue", "inputs", "wages", "upkeep", "taxes", "invested")


class SiteProfitRow(Base):
    __tablename__ = "site_profits"
    __table_args__ = (
        at_least("epoch", 0),
        *(at_least(column, 0) for column in LEDGER_COLUMNS),
        Index("ix_site_profits_owner", "owner_node_id"),
        Index("ix_site_profits_community", "community_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    workshop_id: Mapped[int | None] = mapped_column(ForeignKey("workshops.id", ondelete="SET NULL"))
    resource_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    site: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    revenue: Mapped[int] = mapped_column(default=0)
    inputs: Mapped[int] = mapped_column(default=0)
    wages: Mapped[int] = mapped_column(default=0)
    upkeep: Mapped[int] = mapped_column(default=0)
    taxes: Mapped[int] = mapped_column(default=0)
    profit: Mapped[int] = mapped_column(default=0)
    invested: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
