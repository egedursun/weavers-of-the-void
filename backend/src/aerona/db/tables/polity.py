from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import (
    ClaimBasis,
    ClauseKind,
    DecisionRule,
    GovernmentKind,
    Jurisdiction,
    LawArea,
    LawKind,
    LegitimacyBasis,
    OathKind,
    OathStatus,
    OfficeKind,
    PartyRole,
    RegionalStanding,
    TreatyKind,
    TreatyStatus,
)
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.statecraft import CouncilTask, SubjectKind


class PolityProfileRow(Base):
    __tablename__ = "polity_profiles"
    __table_args__ = (
        between("legitimacy", PERCENT_MIN, PERCENT_MAX),
        between("stability", PERCENT_MIN, PERCENT_MAX),
        between("war_weariness", PERCENT_MIN, PERCENT_MAX),
        between("overextension", PERCENT_MIN, PERCENT_MAX * 10),
        at_least("administration", 0),
        at_least("debt", 0),
        at_least("war_chest", 0),
        at_least("tier", 0),
        between("corruption", PERCENT_MIN, PERCENT_MAX),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    government: Mapped[GovernmentKind] = mapped_column(enum_type(GovernmentKind, "government"))
    decision_rule: Mapped[DecisionRule] = mapped_column(enum_type(DecisionRule, "decision_rule"))
    legitimacy: Mapped[int] = mapped_column(default=50)
    stability: Mapped[int] = mapped_column(default=50)
    treasury: Mapped[int] = mapped_column(default=0)
    debt: Mapped[int] = mapped_column(default=0)
    war_chest: Mapped[int] = mapped_column(default=0)
    administration: Mapped[int] = mapped_column(default=0)
    overextension: Mapped[int] = mapped_column(default=0)
    war_weariness: Mapped[int] = mapped_column(default=0)
    corruption: Mapped[int] = mapped_column(default=0, server_default="0")
    tier: Mapped[int] = mapped_column(default=0)
    tier_strain: Mapped[int] = mapped_column(default=0)
    standing: Mapped[RegionalStanding] = mapped_column(enum_type(RegionalStanding, "standing"), default=RegionalStanding.MINOR_POWER)
    core_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    capital_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    state_religion_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ideology_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    patron_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    emblem: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    legitimacy_parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PolityMemberRow(Base):
    __tablename__ = "polity_members"
    __table_args__ = (Index("ix_polity_members_member", "member_entity_id"),)

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    member_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    autonomy: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PolityTerritoryRow(Base):
    __tablename__ = "polity_territories"
    __table_args__ = (between("control", PERCENT_MIN, PERCENT_MAX), Index("ix_polity_territories_region", "region_entity_id"))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    control: Mapped[int] = mapped_column(default=0)
    province: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OfficeRow(Base):
    __tablename__ = "offices"
    __table_args__ = (
        Index("ix_offices_polity", "polity_entity_id", "kind"),
        Index("ix_offices_holder", "holder_entity_id"),
        between("diligence", PERCENT_MIN, PERCENT_MAX),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[OfficeKind] = mapped_column(enum_type(OfficeKind, "kind"))
    holder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    appointed_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    since_epoch: Mapped[int] = mapped_column(default=0)
    powers: Mapped[list[str]] = mapped_column(JSON, default=list)
    task: Mapped[CouncilTask | None] = mapped_column(enum_type(CouncilTask, "task"))
    task_target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    diligence: Mapped[int] = mapped_column(default=50, server_default="50")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OfficeHistoryRow(Base):
    __tablename__ = "office_history"
    __table_args__ = (Index("ix_office_history_office", "office_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    office_id: Mapped[int] = mapped_column(ForeignKey("offices.id", ondelete="CASCADE"))
    holder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    from_epoch: Mapped[int]
    to_epoch: Mapped[int | None]
    reason: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class PolityTreasuryRow(Base):
    __tablename__ = "polity_treasury"
    __table_args__ = (Index("ix_polity_treasury_polity", "polity_entity_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    entry: Mapped[TreasuryEntry] = mapped_column(enum_type(TreasuryEntry, "entry"))
    amount: Mapped[int]
    balance: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class VassalageRow(Base):
    __tablename__ = "vassalages"
    __table_args__ = (
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        between("tribute_pct", PERCENT_MIN, PERCENT_MAX),
        between("levy_pct", PERCENT_MIN, PERCENT_MAX),
        between("liberty", PERCENT_MIN, PERCENT_MAX),
    )

    vassal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    overlord_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    treaty_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    tribute_pct: Mapped[int] = mapped_column(default=10)
    levy_pct: Mapped[int] = mapped_column(default=10)
    loyalty: Mapped[int] = mapped_column(default=50)
    kind: Mapped[SubjectKind] = mapped_column(enum_type(SubjectKind, "kind"), default=SubjectKind.VASSAL, server_default=SubjectKind.VASSAL.value)
    liberty: Mapped[int] = mapped_column(default=20, server_default="20")
    private_war: Mapped[bool] = mapped_column(default=False, server_default="0")
    coinage: Mapped[bool] = mapped_column(default=False, server_default="0")
    confirm_succession: Mapped[bool] = mapped_column(default=True, server_default="1")
    confirmed_ruler_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LawProfileRow(Base):
    __tablename__ = "law_profiles"
    __table_args__ = (between("enforcement", PERCENT_MIN, PERCENT_MAX), between("conflict", PERCENT_MIN, PERCENT_MAX), Index("ix_law_profiles_kind", "kind"))

    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[LawKind] = mapped_column(enum_type(LawKind, "kind"))
    area: Mapped[LawArea] = mapped_column(enum_type(LawArea, "area"))
    params: Mapped[dict[str, int | str | bool]] = mapped_column(JSON, default=dict)
    enforcement: Mapped[int] = mapped_column(default=50)
    legitimacy_basis: Mapped[LegitimacyBasis] = mapped_column(enum_type(LegitimacyBasis, "legitimacy_basis"), default=LegitimacyBasis.CUSTOM)
    conflict: Mapped[int] = mapped_column(default=0)
    enacted_epoch: Mapped[int] = mapped_column(default=0)
    enacted_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LawJurisdictionRow(Base):
    __tablename__ = "law_jurisdictions"
    __table_args__ = (Index("ix_law_jurisdictions_node", "node_entity_id"),)

    law_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    node_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    jurisdiction: Mapped[Jurisdiction] = mapped_column(enum_type(Jurisdiction, "jurisdiction"))


class HouseProfileRow(Base):
    __tablename__ = "house_profiles"
    __table_args__ = (between("prestige", PERCENT_MIN, PERCENT_MAX), at_least("wealth", 0))

    house_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    founder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    head_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    parent_house_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    divine_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    prestige: Mapped[int] = mapped_column(default=20)
    wealth: Mapped[int] = mapped_column(default=0)
    motto: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    emblem: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    seats: Mapped[list[int]] = mapped_column(JSON, default=list)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    extinct_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HouseMemberRow(Base):
    __tablename__ = "house_members"
    __table_args__ = (Index("ix_house_members_mortal", "mortal_entity_id"),)

    house_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    by_marriage: Mapped[bool] = mapped_column(default=False)


class ClaimRow(Base):
    __tablename__ = "claims"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        Index("ix_claims_polity", "polity_entity_id"),
        Index("ix_claims_claimant", "claimant_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claimant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    house_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    office: Mapped[OfficeKind] = mapped_column(enum_type(OfficeKind, "office"), default=OfficeKind.RULER)
    title_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    strength: Mapped[int] = mapped_column(default=50)
    basis: Mapped[ClaimBasis] = mapped_column(enum_type(ClaimBasis, "basis"))
    pressed: Mapped[bool] = mapped_column(default=False)
    backer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HeirloomRow(Base):
    __tablename__ = "heirlooms"

    item_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    house_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)


class OathRow(Base):
    __tablename__ = "oaths"
    __table_args__ = (Index("ix_oaths_swearer", "swearer_entity_id", "status"), Index("ix_oaths_recipient", "recipient_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    swearer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    recipient_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[OathKind] = mapped_column(enum_type(OathKind, "kind"))
    witness_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    status: Mapped[OathStatus] = mapped_column(enum_type(OathStatus, "status"), default=OathStatus.SWORN)
    sworn_epoch: Mapped[int]
    deadline_epoch: Mapped[int | None]
    ended_epoch: Mapped[int | None]
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class TreatyProfileRow(Base):
    __tablename__ = "treaty_profiles"
    __table_args__ = (Index("ix_treaty_profiles_status", "status"),)

    treaty_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[TreatyKind] = mapped_column(enum_type(TreatyKind, "kind"))
    status: Mapped[TreatyStatus] = mapped_column(enum_type(TreatyStatus, "status"), default=TreatyStatus.IN_FORCE)
    signed_epoch: Mapped[int]
    until_epoch: Mapped[int | None]
    ended_epoch: Mapped[int | None]
    witness_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    oath_id: Mapped[int | None] = mapped_column(ForeignKey("oaths.id", ondelete="SET NULL"))
    source_bond_id: Mapped[int | None] = mapped_column(ForeignKey("bonds.id", ondelete="SET NULL"), index=True)
    proposed_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    renewals: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TreatyPartyRow(Base):
    __tablename__ = "treaty_parties"
    __table_args__ = (Index("ix_treaty_parties_party", "party_node_id"),)

    treaty_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    party_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[PartyRole] = mapped_column(enum_type(PartyRole, "role"), default=PartyRole.SIGNATORY)


class TreatyClauseRow(Base):
    __tablename__ = "treaty_clauses"
    __table_args__ = (Index("ix_treaty_clauses_treaty", "treaty_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treaty_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[ClauseKind] = mapped_column(enum_type(ClauseKind, "kind"))
    obligor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    beneficiary_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    params: Mapped[dict[str, int | str | bool]] = mapped_column(JSON, default=dict)
    last_kept_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TreatyBreachRow(Base):
    __tablename__ = "treaty_breaches"
    __table_args__ = (Index("ix_treaty_breaches_treaty", "treaty_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treaty_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    clause_id: Mapped[int | None] = mapped_column(ForeignKey("treaty_clauses.id", ondelete="SET NULL"))
    breaker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class SentenceRow(Base):
    __tablename__ = "sentences"
    __table_args__ = (Index("ix_sentences_settlement", "settlement_entity_id", "epoch"), Index("ix_sentences_mortal", "mortal_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    law_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    crime: Mapped[CrimeKind] = mapped_column(enum_type(CrimeKind, "crime"))
    penalty: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    epoch: Mapped[int]
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"), index=True)
