from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.genetics import GiftStance, Locus
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

GENOME_FIELDS = ("inbreeding", "beauty", "recognisability")


class GenomeRow(Base):
    __tablename__ = "genomes"
    __table_args__ = (
        between("inbreeding", PERCENT_MIN, PERCENT_MAX),
        between("beauty", PERCENT_MIN, PERCENT_MAX),
        between("recognisability", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
    )

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    genes: Mapped[dict[str, list[str]]] = mapped_column(JSON, default=dict)
    potential: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    divine_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    inbreeding: Mapped[int] = mapped_column(default=0)
    beauty: Mapped[int] = mapped_column(default=50)
    recognisability: Mapped[int] = mapped_column(default=30)
    likeness: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    marks: Mapped[list[str]] = mapped_column(JSON, default=list)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AllelePoolRow(Base):
    __tablename__ = "allele_pools"
    __table_args__ = (between("gifted_share", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0))

    people_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    frequencies: Mapped[dict[str, dict[str, int]]] = mapped_column(JSON, default=dict)
    gift_stance: Mapped[GiftStance] = mapped_column(enum_type(GiftStance, "gift_stance"), default=GiftStance.HONOURED)
    gifted_share: Mapped[int] = mapped_column(default=0)
    cohort_shares: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HouseResemblanceRow(Base):
    __tablename__ = "house_resemblances"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    house_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    locus: Mapped[Locus] = mapped_column(enum_type(Locus, "locus"))
    allele: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    share: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
