from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.youth import YouthPlace, YouthPurpose

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

YOUTH_PURPOSE = total(
    YouthPurpose,
    {
        YouthPurpose.SPORT: Defined(
            "Sport",
            checked_by=("engine.youth.groups.MEMBER_AXES",),
            used_by=(
                "db.tables.youth.YouthGroupRow",
                "engine.youth.groups.PURPOSE_AXES",
                "engine.youth.groups.purpose_for",
                "tools.mortal.youth.MEASURE_PURPOSES",
                "tools.mortal.youth.reform_youth",
            ),
        ),
        YouthPurpose.SERVICE: Defined(
            "Service",
            checked_by=("engine.youth.groups.MEMBER_AXES", "engine.youth.groups.TOWN_EFFECTS"),
            used_by=("engine.youth.groups.PURPOSE_AXES", "engine.youth.groups.coopt", "tools.mortal.youth.MEASURE_PURPOSES"),
        ),
        YouthPurpose.COURTSHIP: Defined("Courtship", checked_by=("engine.youth.groups.MEMBER_AXES",), used_by=("engine.youth.groups.PURPOSE_AXES",)),
        YouthPurpose.DEFENCE: Defined(
            "Defence",
            checked_by=("engine.youth.groups.MEMBER_AXES", "engine.youth.groups.TOWN_EFFECTS"),
            used_by=("engine.youth.groups.PURPOSE_AXES", "tools.mortal.youth.MEASURE_PURPOSES"),
        ),
        YouthPurpose.FAITH: Defined("Faith", checked_by=("engine.youth.groups.MEMBER_AXES",), used_by=("engine.youth.groups.PURPOSE_AXES",)),
        YouthPurpose.MISCHIEF: Defined(
            "Mischief",
            checked_by=("engine.youth.groups.TOWN_EFFECTS", "engine.youth.groups.misbehave"),
            used_by=("engine.youth.groups.DELINQUENT", "engine.youth.groups.UNRULY"),
        ),
        YouthPurpose.CRIME: Defined(
            "Crime",
            checked_by=("engine.youth.groups.TOWN_EFFECTS", "engine.youth.groups.recruit"),
            used_by=("engine.youth.groups.DELINQUENT", "engine.youth.groups.UNRULY", "engine.youth.groups.misbehave"),
        ),
        YouthPurpose.POLITICS: Defined(
            "Politics", checked_by=("engine.youth.groups.TOWN_EFFECTS", "engine.youth.groups.recruit"), used_by=("engine.youth.groups.UNRULY",)
        ),
    },
)
