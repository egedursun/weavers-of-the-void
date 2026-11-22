from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.structure import BuilderKind, BuildingForm, EffectTarget, StructureSection

BOUNDED = frozenset(
    {
        EffectTarget.PUBLIC_ORDER,
        EffectTarget.CRIME,
        EffectTarget.UNREST,
        EffectTarget.SANITATION,
        EffectTarget.FIRE_RISK,
        EffectTarget.PRESTIGE,
        EffectTarget.SIEGE_SUPPLIES,
        EffectTarget.SIEGE_WATER,
    }
)


LIVING_ADULTS = (CohortCondition.NONE, CohortCondition.VETERAN, CohortCondition.ENSLAVED)


BUILDER_CONDITION: Mapping[BuilderKind, int] = total(
    BuilderKind,
    {
        BuilderKind.COMMUNITY: 0,
        BuilderKind.POLITY: 0,
        BuilderKind.FACTION: 0,
        BuilderKind.CULT: 0,
        BuilderKind.PATRON: 0,
        BuilderKind.GOD: 20,
        BuilderKind.COMPANY: 5,
        BuilderKind.MADE_MIND: 10,
    },
)

STRIKE_ROWS_STRUCTURE_SECTIONS = frozenset({StructureSection.FOUNDATION, StructureSection.SPINE, StructureSection.PIERS})
CULTURAL_FORM_BUILDING_FORMS = frozenset({BuildingForm.TOWER, BuildingForm.HALL})
