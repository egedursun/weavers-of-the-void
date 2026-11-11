from enum import StrEnum
from typing import Annotated

from pydantic import Field

from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN
from aerona.domain.enums.arcana import SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import ArtMedium, IdeologyTenet, MagicSchool, MagicSource, RiteEffectKind, SummonForm
from aerona.tools.framework.inputs import ToolInput

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
MAX_EFFECTS = 4
MAX_TENETS = 3


class WorkingInput(ToolInput):
    effect: RiteEffectKind
    magnitude: Annotated[int, Field(ge=1, le=100)]
    damage_type: DamageType | None = None
    summon_form: SummonForm | None = None


class CommissionInput(ToolInput):
    name: Name
    medium: ArtMedium
    subject_id: int | None = None
    author_id: int | None = None
    patron_id: int | None = None


class DesignRiteInput(ToolInput):
    name: Name
    school: MagicSchool
    source: MagicSource | None = None
    power: Annotated[int, Field(ge=1, le=10)]
    workings: Annotated[list[WorkingInput], Field(min_length=1, max_length=MAX_EFFECTS)]
    technique: SpellTechnique | None = None
    form: SpellForm | None = None
    range: SpellRange = SpellRange.SIGHT
    duration: SpellDuration = SpellDuration.INSTANT
    target: SpellTarget = SpellTarget.ONE
    paradigm_id: int | None = None
    myth_id: int | None = None
    holder_id: int | None = None


class CastRiteInput(ToolInput):
    rite_id: int
    target_id: int | None = None
    vessel_id: int | None = None


class FoundSchoolInput(ToolInput):
    name: Name
    tenets: Annotated[list[IdeologyTenet], Field(min_length=1, max_length=MAX_TENETS)]
    founder_id: int | None = None


class LoreToolResult(StrEnum):
    COMMISSIONED = "#{{ id }} {{ name }} is begun; it will press its message on those who keep it."
    DESIGNED = "#{{ id }} {{ name }} is devised: {{ workings }}."
    CAST = "{{ name }} was worked: {{ effect }}."
    REFUSED = "{{ name }} would not answer: {{ reason }}."
    FOUNDED = "#{{ id }} {{ name }} is taught: {{ tenets }}."
    NOT_A_RITE = "#{{ id }} is no living rite."
    NO_VESSEL = "Name a worshipping community to work it through (vessel_id)."
    NO_FOUNDER = "Name a living mortal to found the school (founder_id)."
    NO_PATRON = "Name a living patron for the work (patron_id)."
    UNABLE = "{{ reason }}"
