from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.gathering import Milestone

MILESTONE = total(
    Milestone,
    {
        Milestone.BIRTH: Defined("A birth", checked_by=(), used_by=("engine.gatherings.occasions.milestones",)),
        Milestone.COMING_OF_AGE: Defined(
            "Coming of age", checked_by=(), used_by=("engine.customs.age_sets.hold_promotion", "engine.gatherings.occasions.milestones")
        ),
        Milestone.ANNIVERSARY: Defined("An anniversary", checked_by=(), used_by=("engine.gatherings.occasions.milestones",)),
    },
)
