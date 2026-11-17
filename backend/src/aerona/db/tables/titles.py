from sqlalchemy import JSON, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.titles import TitleTenure, TitleTier

TITLE_FIELDS = ("rank", "de_jure_liege_entity_id", "holder_node_id", "prestige", "capital_entity_id", "emblem")


class TitleProfileRow(Base):
    __tablename__ = "title_profiles"
    __table_args__ = (between("prestige", PERCENT_MIN, PERCENT_MAX), at_least("created_epoch", 0), Index("ix_title_profiles_holder", "holder_node_id"))

    title_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    rank: Mapped[TitleTier] = mapped_column(enum_type(TitleTier, "rank"))
    de_jure_liege_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    succession_law_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    capital_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    emblem: Mapped[str | None] = mapped_column(Text)
    prestige: Mapped[int] = mapped_column(default=30)
    regalia: Mapped[list[int]] = mapped_column(JSON, default=list)
    drift: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    created_epoch: Mapped[int] = mapped_column(default=0)
    destroyed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TitleHolderRow(Base):
    __tablename__ = "title_holders"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_title_holders_title", "title_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    title_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    tenure: Mapped[TitleTenure] = mapped_column(enum_type(TitleTenure, "tenure"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]


class DeJureLinkRow(Base):
    __tablename__ = "de_jure_links"
    __table_args__ = (at_least("since_epoch", 0),)

    title_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    member_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)
