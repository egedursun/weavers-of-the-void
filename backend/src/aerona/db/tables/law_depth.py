from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, MoleHuntOutcome, RegistryKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mortal import CrimeKind

SYSTEM_FIELDS = ("system",)
PRECEDENT_FIELDS = ("verdict", "authority", "overturned")
APPEAL_FIELDS = ("to_court", "fee", "reversed")
REGISTRY_FIELDS = ("amount", "owner_entity_id", "counterparty_entity_id")
JURISDICTION_FIELDS = ("strength",)
OUTLAW_FIELDS = ("bounty", "renown")
PRISON_FIELDS = ("food", "crowding", "cruelty", "gang_strength")
PRISONER_FIELDS = ("term", "gang_rank")
CELL_FIELDS = ("handler_entity_id", "safe_house_entity_id", "dead_drops")
DEFECTION_FIELDS = ("secrets", "protected")
KILLING_FIELDS = ("method", "recognised")


class LegalSystemRow(Base):
    __tablename__ = "legal_systems"
    __table_args__ = (at_least("since_epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    system: Mapped[LegalSystem] = mapped_column(enum_type(LegalSystem, "system"), default=LegalSystem.CUSTOMARY)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PrecedentRow(Base):
    __tablename__ = "precedents"
    __table_args__ = (between("authority", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0), Index("ix_precedents_holder", "holder_entity_id", "crime"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    crime: Mapped[CrimeKind] = mapped_column(enum_type(CrimeKind, "crime"))
    verdict: Mapped[Verdict] = mapped_column(enum_type(Verdict, "verdict"))
    court: Mapped[CourtLevel] = mapped_column(enum_type(CourtLevel, "court"), default=CourtLevel.LOCAL)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"))
    authority: Mapped[int] = mapped_column(default=30)
    overturned: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AppealRow(Base):
    __tablename__ = "appeals"
    __table_args__ = (at_least("fee", 0), at_least("filed_epoch", 0))

    case_id: Mapped[int] = mapped_column(ForeignKey("crime_cases.id", ondelete="CASCADE"), primary_key=True)
    from_court: Mapped[CourtLevel] = mapped_column(enum_type(CourtLevel, "from_court"), default=CourtLevel.LOCAL)
    to_court: Mapped[CourtLevel] = mapped_column(enum_type(CourtLevel, "to_court"), default=CourtLevel.PROVINCIAL)
    fee: Mapped[int] = mapped_column(default=0)
    filed_epoch: Mapped[int] = mapped_column(default=0)
    decided_epoch: Mapped[int | None]
    reversed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RegistryRow(Base):
    __tablename__ = "registries"
    __table_args__ = (at_least("amount", 0), at_least("registered_epoch", 0), Index("ix_registries_holder", "holder_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[RegistryKind] = mapped_column(enum_type(RegistryKind, "kind"))
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    counterparty_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    subject_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    amount: Mapped[int] = mapped_column(default=0)
    registered_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class JurisdictionRow(Base):
    __tablename__ = "jurisdictions"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    claimant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    claim: Mapped[JurisdictionClaim] = mapped_column(enum_type(JurisdictionClaim, "claim"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=40)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PardonRow(Base):
    __tablename__ = "pardons"
    __table_args__ = (at_least("epoch", 0), Index("ix_pardons_granter", "granter_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    granter_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    pardoned_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"))
    amnesty: Mapped[bool] = mapped_column(default=False)
    corrupt: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)


class OutlawRow(Base):
    __tablename__ = "outlaws"
    __table_args__ = (at_least("bounty", 0), between("renown", PERCENT_MIN, PERCENT_MAX), at_least("declared_epoch", 0))

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    bounty: Mapped[int] = mapped_column(default=0)
    renown: Mapped[int] = mapped_column(default=0)
    declared_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PrisonRow(Base):
    __tablename__ = "prisons"
    __table_args__ = tuple(between(name, PERCENT_MIN, PERCENT_MAX) for name in ("food", "crowding", "cruelty", "gang_strength"))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    food: Mapped[int] = mapped_column(default=50)
    crowding: Mapped[int] = mapped_column(default=30)
    cruelty: Mapped[int] = mapped_column(default=30)
    gang_strength: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PrisonerRow(Base):
    __tablename__ = "prisoners"
    __table_args__ = (
        at_least("term", 0),
        between("gang_rank", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_prisoners_prison", "prison_entity_id"),
    )

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    prison_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("crime_cases.id", ondelete="SET NULL"))
    term: Mapped[int] = mapped_column(default=2)
    gang_rank: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpyCellRow(Base):
    __tablename__ = "spy_cells"
    __table_args__ = (at_least("dead_drops", 0), Index("ix_spy_cells_network", "network_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("spy_networks.id", ondelete="CASCADE"))
    handler_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    safe_house_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    dead_drops: Mapped[int] = mapped_column(default=1)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MoleHuntRow(Base):
    __tablename__ = "mole_hunts"
    __table_args__ = (at_least("epoch", 0), Index("ix_mole_hunts_polity", "polity_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    spymaster_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    suspect_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    mole: Mapped[bool] = mapped_column(default=False)
    outcome: Mapped[MoleHuntOutcome] = mapped_column(enum_type(MoleHuntOutcome, "outcome"))
    epoch: Mapped[int] = mapped_column(default=0)


class DefectionRow(Base):
    __tablename__ = "defections"
    __table_args__ = (at_least("secrets", 0), at_least("epoch", 0), Index("ix_defections_defector", "defector_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    defector_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    from_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    to_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    secrets: Mapped[int] = mapped_column(default=0)
    protected: Mapped[bool] = mapped_column(default=True)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KillingRow(Base):
    __tablename__ = "assassinations"
    __table_args__ = (at_least("epoch", 0), Index("ix_assassinations_victim", "victim_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    victim_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    killer_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    method: Mapped[KillMethod] = mapped_column(enum_type(KillMethod, "method"))
    recognised: Mapped[bool] = mapped_column(default=False)
    examiner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
