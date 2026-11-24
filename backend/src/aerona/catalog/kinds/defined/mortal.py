from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.mortal import MarriageEnd

MARRIAGE_END = total(
    MarriageEnd,
    {
        MarriageEnd.DEATH: Defined(
            "Death",
            checked_by=("engine.collective.demography.bereaved_among", "engine.cycles.kinship.keep_kinship", "services.kinship.layout.partnerships_of"),
            used_by=("engine.mortal.kinship.backfill_kin", "engine.mortal.kinship.widow"),
        ),
        MarriageEnd.DIVORCE: Defined(
            "Divorce",
            checked_by=(),
            used_by=("engine.mortal.course.end_marriages", "engine.relations.affairs.consequences", "services.player.mortals.EndMarriage"),
        ),
        MarriageEnd.ANNULMENT: Defined("Annulment", checked_by=(), used_by=("engine.mortal.course.end_marriages",)),
        MarriageEnd.WAR: Defined("War", checked_by=(), used_by=("engine.mortal.course.end_marriages",)),
        MarriageEnd.TERM: Defined("Its term ended by custom", checked_by=(), used_by=("engine.unions.keep.end_terms",)),
    },
)
