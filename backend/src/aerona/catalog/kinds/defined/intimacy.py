from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.intimacy import BirthComplication, RelationContext

BIRTH_COMPLICATION = total(
    BirthComplication,
    {
        BirthComplication.POSITION: Defined("Position", checked_by=(), used_by=("catalog.life.intimacy.SINGLE_COMPLICATIONS",)),
        BirthComplication.BLEEDING: Defined("Bleeding", checked_by=(), used_by=("catalog.life.intimacy.SINGLE_COMPLICATIONS",)),
        BirthComplication.FEVER: Defined("Fever", checked_by=(), used_by=("catalog.life.intimacy.SINGLE_COMPLICATIONS",)),
        BirthComplication.EARLY: Defined("Early", checked_by=(), used_by=("catalog.life.intimacy.SINGLE_COMPLICATIONS",)),
        BirthComplication.LATE: Defined("Late", checked_by=(), used_by=("catalog.life.intimacy.SINGLE_COMPLICATIONS",)),
        BirthComplication.MULTIPLE: Defined("Multiple", checked_by=(), used_by=("engine.intimacy.course.complication_kind",)),
        BirthComplication.NONE: Defined(
            "None", checked_by=("engine.intimacy.course.complication_kind",), used_by=("db.tables.intimacy.ReproductiveCourseRow",)
        ),
        BirthComplication.STILLBIRTH: Defined("Stillbirth", checked_by=(), used_by=()),
        BirthComplication.BIRTH_INJURY: Defined("Birth injury", checked_by=(), used_by=()),
    },
)

RELATION_CONTEXT = total(
    RelationContext,
    {
        RelationContext.BEFORE_UNION: Defined(
            "Before union", checked_by=(), used_by=("engine.fertility_means.tend.first_stance", "engine.intimacy.norms.contexts_of")
        ),
        RelationContext.WITHIN_UNION: Defined(
            "Within union", checked_by=(), used_by=("engine.fertility_means.tend.first_stance", "engine.intimacy.norms.contexts_of")
        ),
        RelationContext.OUTSIDE_UNION: Defined(
            "Outside union",
            checked_by=(),
            used_by=("catalog.life.intimacy.ACT_CONTEXTS", "engine.intimacy.norms.contexts_of", "engine.intimacy.norms.outside_union_weight"),
        ),
        RelationContext.BETWEEN_ANY_SEXES: Defined(
            "Between any sexes",
            checked_by=("engine.intimacy.seed.seed_norms", "services.integrity.life_links.sexless_norms"),
            used_by=("engine.intimacy.norms.contexts_of", "services.integrity.life_links.drop_sexless_norm"),
        ),
        RelationContext.WITH_KIN: Defined(
            "With kin", checked_by=("engine.intimacy.seed.seed_norms",), used_by=("catalog.life.intimacy.ACT_CONTEXTS", "engine.intimacy.norms.ruling_norm")
        ),
        RelationContext.WITH_MADE_MINDS: Defined("With made minds", checked_by=(), used_by=("engine.intimacy.norms.contexts_of",)),
        RelationContext.WITH_OTHER_KINDS: Defined("With other kinds", checked_by=(), used_by=("engine.intimacy.norms.contexts_of",)),
        RelationContext.WITH_SPIRITS_OR_GODS: Defined("With spirits or gods", checked_by=(), used_by=()),
    },
)
