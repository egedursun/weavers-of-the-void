from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.faction import FactionKind, FactionScale
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import Profession
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_kinds import (
    OrganisationGovernance,
    OrganisationLegalForm,
    OrganisationMembership,
    OrganisationOwnership,
    OrganisationPurpose,
    ProfessionCategory,
)


class ProfessionKindRow(KindRow):
    __tablename__ = "profession_kinds"
    __table_args__ = (
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        between("income", PERCENT_MIN, PERCENT_MAX),
        between("purity", PERCENT_MIN, PERCENT_MAX),
        between("mishap_exposure", PERCENT_MIN, PERCENT_MAX),
        between("skill_need", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("profession_kinds.id", ondelete="SET NULL"))
    category: Mapped[ProfessionCategory] = mapped_column(enum_type(ProfessionCategory, "category"))
    base: Mapped[Profession | None] = mapped_column(enum_type(Profession, "base"))
    job: Mapped[Job | None] = mapped_column(enum_type(Job, "job"))
    prestige: Mapped[int] = mapped_column(default=30)
    income: Mapped[int] = mapped_column(default=30)
    purity: Mapped[int] = mapped_column(default=50)
    mishap_exposure: Mapped[int] = mapped_column(default=10)
    skill_need: Mapped[int] = mapped_column(default=30)


class RankKindRow(KindRow):
    __tablename__ = "rank_kinds"
    __table_args__ = (
        between("standing", PERCENT_MIN, PERCENT_MAX),
        between("privilege", PERCENT_MIN, PERCENT_MAX),
        between("duty", PERCENT_MIN, PERCENT_MAX),
        between("mobility", PERCENT_MIN, PERCENT_MAX),
        between("purity", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("rank_kinds.id", ondelete="SET NULL"))
    category: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "category"))
    standing: Mapped[int] = mapped_column(default=50)
    privilege: Mapped[int] = mapped_column(default=30)
    duty: Mapped[int] = mapped_column(default=30)
    mobility: Mapped[int] = mapped_column(default=30)
    purity: Mapped[int] = mapped_column(default=50)


class OrganisationKindRow(KindRow):
    __tablename__ = "organisation_kinds"
    __table_args__ = (
        between("prestige", PERCENT_MIN, PERCENT_MAX),
        between("cohesion", PERCENT_MIN, PERCENT_MAX),
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("organisation_kinds.id", ondelete="SET NULL"))
    category: Mapped[OrganisationPurpose] = mapped_column(enum_type(OrganisationPurpose, "category"))
    base: Mapped[FactionKind | None] = mapped_column(enum_type(FactionKind, "base"))
    ownership: Mapped[OrganisationOwnership] = mapped_column(enum_type(OrganisationOwnership, "ownership"), default=OrganisationOwnership.MEMBERS)
    membership: Mapped[OrganisationMembership] = mapped_column(enum_type(OrganisationMembership, "membership"), default=OrganisationMembership.OPEN)
    scale: Mapped[FactionScale] = mapped_column(enum_type(FactionScale, "scale"), default=FactionScale.COMPANY)
    legal_form: Mapped[OrganisationLegalForm] = mapped_column(enum_type(OrganisationLegalForm, "legal_form"), default=OrganisationLegalForm.CUSTOMARY)
    governance: Mapped[OrganisationGovernance] = mapped_column(enum_type(OrganisationGovernance, "governance"), default=OrganisationGovernance.LEADER)
    prestige: Mapped[int] = mapped_column(default=30)
    cohesion: Mapped[int] = mapped_column(default=50)
    secrecy: Mapped[int] = mapped_column(default=0)
    foundable: Mapped[bool] = mapped_column(default=True)
