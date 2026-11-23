from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.constants.units import PERCENT
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.body import (
    BodyBuild,
    BodyPart,
    BodyPlan,
    BodyReading,
    ConditionKind,
    Consciousness,
    DamageType,
    Handedness,
    HarmCause,
    HeightClass,
    InjuryKind,
    InjuryState,
    MaimedKind,
    NerveDamage,
    TissueKind,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.records import InstrumentKind

SEVERITY_MIN = 1
SEVERITY_MAX = 5

CAPACITY_COLUMNS = ("melee", "missile", "command", "craft", "scholarship", "presence", "mobility", "fertility")
FUNCTION_COLUMNS = ("vital", "cognition", "hearing", "sight", "venom", "horn", "tail")
ARMOUR_COLUMNS = ("armour_head", "armour_torso", "armour_limbs")


class BodyRow(Base):
    __tablename__ = "bodies"
    __table_args__ = (
        *(at_least(column, 0) for column in CAPACITY_COLUMNS),
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in (*ARMOUR_COLUMNS, *FUNCTION_COLUMNS, "pain")),
        at_least("fingers", 0),
        at_least("toes", 0),
        at_least("teeth", 0),
        between("blood", PERCENT_MIN, PERCENT_MAX),
        between("exertion", PERCENT_MIN, PERCENT_MAX),
        at_least("hp_max", 0),
        at_least("patients_healed", 0),
        at_least("patients_lost", 0),
        at_least("updated_epoch", 0),
    )

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    plan: Mapped[BodyPlan] = mapped_column(enum_type(BodyPlan, "plan"))
    height_class: Mapped[HeightClass] = mapped_column(enum_type(HeightClass, "height_class"), default=HeightClass.AVERAGE)
    build: Mapped[BodyBuild] = mapped_column(enum_type(BodyBuild, "build"), default=BodyBuild.AVERAGE)
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    fingers: Mapped[int]
    toes: Mapped[int] = mapped_column(default=10, server_default="10")
    teeth: Mapped[int] = mapped_column(default=32, server_default="32")
    blood: Mapped[int] = mapped_column(default=PERCENT, server_default="100")
    exertion: Mapped[int] = mapped_column(default=0, server_default="0")
    consciousness: Mapped[Consciousness] = mapped_column(enum_type(Consciousness, "consciousness"), default=Consciousness.AWAKE, server_default="awake")
    lost_digits: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    handedness: Mapped[Handedness] = mapped_column(enum_type(Handedness, "handedness"), default=Handedness.RIGHT, server_default="right")
    pain: Mapped[int] = mapped_column(default=0)
    hp_max: Mapped[int] = mapped_column(default=0)
    melee: Mapped[int] = mapped_column(default=PERCENT)
    missile: Mapped[int] = mapped_column(default=PERCENT)
    command: Mapped[int] = mapped_column(default=PERCENT)
    craft: Mapped[int] = mapped_column(default=PERCENT)
    scholarship: Mapped[int] = mapped_column(default=PERCENT)
    presence: Mapped[int] = mapped_column(default=PERCENT)
    mobility: Mapped[int] = mapped_column(default=PERCENT)
    fertility: Mapped[int] = mapped_column(default=PERCENT)
    endurance: Mapped[int] = mapped_column(default=PERCENT, server_default="100")
    perception: Mapped[int] = mapped_column(default=PERCENT, server_default="100")
    armour_head: Mapped[int] = mapped_column(default=0)
    armour_torso: Mapped[int] = mapped_column(default=0)
    armour_limbs: Mapped[int] = mapped_column(default=0)
    vital: Mapped[int] = mapped_column(default=PERCENT)
    cognition: Mapped[int] = mapped_column(default=PERCENT)
    hearing: Mapped[int] = mapped_column(default=PERCENT)
    sight: Mapped[int] = mapped_column(default=PERCENT)
    venom: Mapped[int] = mapped_column(default=0)
    horn: Mapped[int] = mapped_column(default=0)
    tail: Mapped[int] = mapped_column(default=0)
    patients_healed: Mapped[int] = mapped_column(default=0)
    patients_lost: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InjuryRow(CreatedAtMixin, Base):
    __tablename__ = "injuries"
    __table_args__ = (
        between("severity", SEVERITY_MIN, SEVERITY_MAX),
        between("function_loss", PERCENT_MIN, PERCENT_MAX),
        between("bleeding", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        at_least("infected_epochs", 0),
        Index("ix_injuries_bearer_state", "bearer_node_id", "state"),
        Index("ix_injuries_state", "state"),
        Index("ix_injuries_cause", "cause_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    part: Mapped[BodyPart] = mapped_column(enum_type(BodyPart, "part"))
    kind: Mapped[InjuryKind] = mapped_column(enum_type(InjuryKind, "kind"))
    damage_type: Mapped[DamageType] = mapped_column(enum_type(DamageType, "damage_type"))
    severity: Mapped[int]
    state: Mapped[InjuryState] = mapped_column(enum_type(InjuryState, "state"))
    function_loss: Mapped[int]
    cause_kind: Mapped[HarmCause] = mapped_column(enum_type(HarmCause, "cause_kind"))
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    year: Mapped[int | None]
    treated_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    visible: Mapped[bool] = mapped_column(default=True)
    infected_epochs: Mapped[int] = mapped_column(default=0)
    healed_epoch: Mapped[int | None]
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    tissue: Mapped[TissueKind | None] = mapped_column(enum_type(TissueKind, "tissue"))
    bleeding: Mapped[int] = mapped_column(default=0, server_default="0")
    nerve: Mapped[NerveDamage] = mapped_column(enum_type(NerveDamage, "nerve"), default=NerveDamage.NONE, server_default="none")
    treatments: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    misdiagnosed: Mapped[bool] = mapped_column(default=False, server_default="0")
    digits: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    step_id: Mapped[int | None] = mapped_column(ForeignKey("incident_steps.id", ondelete="SET NULL"), index=True)
    instrument_kind: Mapped[InstrumentKind | None] = mapped_column(enum_type(InstrumentKind, "instrument_kind"))
    instrument_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    instrument_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))


class ConditionRow(CreatedAtMixin, Base):
    __tablename__ = "conditions"
    __table_args__ = (
        between("severity", SEVERITY_MIN, SEVERITY_MAX),
        at_least("since_epoch", 0),
        Index("ix_conditions_bearer", "bearer_node_id", "ended_epoch"),
        Index("ix_conditions_kind", "kind", "ended_epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[ConditionKind] = mapped_column(enum_type(ConditionKind, "kind"))
    severity: Mapped[int]
    part: Mapped[BodyPart | None] = mapped_column(enum_type(BodyPart, "part"))
    source: Mapped[HarmCause] = mapped_column(enum_type(HarmCause, "source"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    visible: Mapped[bool] = mapped_column(default=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("kind_variants.id", ondelete="SET NULL"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    cause: Mapped[ConditionCause | None] = mapped_column(enum_type(ConditionCause, "cause"))
    kind_id: Mapped[int | None] = mapped_column(ForeignKey("agentless_conditions.id", ondelete="SET NULL"), index=True)


class ProsthesisRow(CreatedAtMixin, Base):
    __tablename__ = "prostheses"
    __table_args__ = (
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("restored_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        Index("ix_prostheses_bearer", "bearer_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    injury_id: Mapped[int] = mapped_column(ForeignKey("injuries.id", ondelete="CASCADE"), unique=True)
    part: Mapped[BodyPart] = mapped_column(enum_type(BodyPart, "part"))
    material: Mapped[MaterialKind] = mapped_column(enum_type(MaterialKind, "material"))
    quality: Mapped[int]
    restored_pct: Mapped[int]
    item_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    maker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int]


class MaimedCohortRow(Base):
    __tablename__ = "maimed_cohorts"
    __table_args__ = (at_least("count", 0), at_least("veterans", 0), at_least("updated_epoch", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[MaimedKind] = mapped_column(enum_type(MaimedKind, "kind"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    veterans: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)


class BodyCustomRow(Base):
    __tablename__ = "body_customs"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    reading: Mapped[BodyReading] = mapped_column(enum_type(BodyReading, "reading"))
    wholeness_required: Mapped[bool] = mapped_column(default=False)
    seer_eye: Mapped[bool] = mapped_column(default=False)
    scar_festivals: Mapped[bool] = mapped_column(default=False)
    pension: Mapped[bool] = mapped_column(default=False)
    tradition_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
