from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.agentless_conditions import ConditionCause, ConditionCourse
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

ONSET_SEVERITY_MIN = 1
ONSET_SEVERITY_MAX = 5


class AgentlessConditionRow(Base):
    __tablename__ = "agentless_conditions"
    __table_args__ = (
        between("onset_pct", PERCENT_MIN, PERCENT_MAX),
        between("severity", ONSET_SEVERITY_MIN, ONSET_SEVERITY_MAX),
        between("weight", PERCENT_MIN, PERCENT_MAX),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    cause: Mapped[ConditionCause] = mapped_column(enum_type(ConditionCause, "cause"))
    system: Mapped[BodySystem] = mapped_column(enum_type(BodySystem, "system"))
    manifests: Mapped[ConditionKind] = mapped_column(enum_type(ConditionKind, "manifests"), default=ConditionKind.CHRONIC_ILLNESS)
    course: Mapped[ConditionCourse] = mapped_column(enum_type(ConditionCourse, "course"), default=ConditionCourse.STABLE)
    onset_pct: Mapped[int] = mapped_column(default=0)
    severity: Mapped[int] = mapped_column(default=1)
    weight: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
