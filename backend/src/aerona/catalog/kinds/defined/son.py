from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.son import SonDeathCause

SON_DEATH_CAUSE = total(
    SonDeathCause,
    {
        SonDeathCause.FADING: Defined("Fading", checked_by=(), used_by=("engine.divine.wounds.death_cause",)),
        SonDeathCause.KILLED_BY_SIBLING: Defined("Killed by sibling", checked_by=(), used_by=("engine.divine.wounds.death_cause",)),
        SonDeathCause.KILLED_BY_CREATOR: Defined(
            "Killed by creator", checked_by=(), used_by=("engine.divine.wounds.death_cause", "engine.gods.god_death.creator_kills_son")
        ),
        SonDeathCause.DEVOURED: Defined("Devoured", checked_by=(), used_by=("engine.gods.power.devour_son",)),
        SonDeathCause.FOREIGN_GOD: Defined("Foreign god", checked_by=(), used_by=("engine.divine.wounds.death_cause",)),
        SonDeathCause.COSMIC_HORROR: Defined(
            "Cosmic horror", checked_by=(), used_by=("engine.divine.wounds.death_cause", "engine.gods.god_death.leave_cosmos", "engine.transform.gods.corrupt")
        ),
        SonDeathCause.OTHER: Defined("Other", checked_by=(), used_by=("engine.gods.god_death.fallen_body_died", "tools.mortal.heroes._slay")),
    },
)
