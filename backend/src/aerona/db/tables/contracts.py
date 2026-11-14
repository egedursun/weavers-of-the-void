from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

CONTRACT_FIELDS = ("community_entity_id", "beast_entity_id", "bounty", "hunter_entity_id", "status", "study")


class MonsterContractRow(Base):
    __tablename__ = "monster_contracts"
    __table_args__ = (
        at_least("bounty", 0),
        between("study", PERCENT_MIN, PERCENT_MAX),
        at_least("posted_epoch", 0),
        Index("ix_monster_contracts_beast", "beast_entity_id", "status"),
        Index("ix_monster_contracts_community", "community_entity_id"),
        Index("ix_monster_contracts_hunter", "hunter_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    beast_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    bounty: Mapped[int] = mapped_column(default=0)
    hunter_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    status: Mapped[ContractStatus] = mapped_column(enum_type(ContractStatus, "status"), default=ContractStatus.POSTED)
    study: Mapped[int] = mapped_column(default=0)
    posted_epoch: Mapped[int] = mapped_column(default=0)
    closed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
