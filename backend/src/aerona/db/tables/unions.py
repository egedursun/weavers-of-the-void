from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.unions import (
    KinMatch,
    PartnerScope,
    PluralSide,
    UnionArrangement,
    UnionDescent,
    UnionDissolution,
    UnionExchange,
    UnionForm,
    UnionPurpose,
    UnionResidence,
)

UNION_TERM_MAX = 100
UNION_FIELDS = (
    "form",
    "plural_side",
    "purpose",
    "residence",
    "descent",
    "exchange",
    "exchange_value",
    "arrangement",
    "dissolution",
    "endogamy",
    "exogamy",
    "kin_match",
    "term_epochs",
)


class UnionCustomRow(Base):
    __tablename__ = "union_customs"
    __table_args__ = (between("term_epochs", 1, UNION_TERM_MAX), at_least("exchange_value", 0))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[UnionForm] = mapped_column(enum_type(UnionForm, "form"), default=UnionForm.PAIR)
    plural_side: Mapped[PluralSide] = mapped_column(enum_type(PluralSide, "plural_side"), default=PluralSide.EITHER, server_default=PluralSide.EITHER.value)
    purpose: Mapped[UnionPurpose] = mapped_column(enum_type(UnionPurpose, "purpose"), default=UnionPurpose.KINSHIP)
    residence: Mapped[UnionResidence] = mapped_column(enum_type(UnionResidence, "residence"), default=UnionResidence.NEW_HOUSEHOLD)
    descent: Mapped[UnionDescent] = mapped_column(enum_type(UnionDescent, "descent"), default=UnionDescent.THROUGH_BOTH)
    exchange: Mapped[UnionExchange] = mapped_column(enum_type(UnionExchange, "exchange"), default=UnionExchange.NONE)
    exchange_value: Mapped[int] = mapped_column(default=10, server_default="10")
    arrangement: Mapped[UnionArrangement] = mapped_column(enum_type(UnionArrangement, "arrangement"), default=UnionArrangement.BOTH_CONSENT)
    dissolution: Mapped[UnionDissolution] = mapped_column(enum_type(UnionDissolution, "dissolution"), default=UnionDissolution.BY_CUSTOM)
    endogamy: Mapped[PartnerScope] = mapped_column(enum_type(PartnerScope, "endogamy"), default=PartnerScope.NONE)
    exogamy: Mapped[PartnerScope] = mapped_column(enum_type(PartnerScope, "exogamy"), default=PartnerScope.NONE)
    kin_match: Mapped[KinMatch] = mapped_column(enum_type(KinMatch, "kin_match"), default=KinMatch.NONE, server_default=KinMatch.NONE.value)
    term_epochs: Mapped[int] = mapped_column(default=4)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
