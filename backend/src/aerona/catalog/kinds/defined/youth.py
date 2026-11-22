from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.youth import YouthPlace

YOUTH_PLACE = total(
    YouthPlace,
    {
        YouthPlace.YOUTH_HOUSE: Defined("Youth house", checked_by=("engine.youth.groups.gather",), used_by=("engine.youth.seed.seed_standing",)),
        YouthPlace.HOUSEHOLD: Defined(
            "Household", checked_by=(), used_by=("db.tables.youth.YouthStandingRow", "engine.youth.groups.gather", "engine.youth.seed.seed_standing")
        ),
        YouthPlace.SCHOOL: Defined("School", checked_by=(), used_by=("engine.youth.seed.seed_standing",)),
        YouthPlace.SERVICE: Defined("Service", checked_by=("engine.youth.groups.coopt",), used_by=()),
        YouthPlace.APPRENTICESHIP: Defined("Apprenticeship", checked_by=(), used_by=("engine.youth.seed.seed_standing",)),
        YouthPlace.WANDERING: Defined("Wandering", checked_by=("engine.youth.groups.gather",), used_by=()),
    },
)
