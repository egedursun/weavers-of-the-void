from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.death_work import DeathRole

DEATH_ROLE = total(
    DeathRole,
    {
        DeathRole.WASHER: Defined("Washer", checked_by=(), used_by=("engine.death_work.seed.HANDLING",)),
        DeathRole.PREPARER: Defined("Preparer", checked_by=(), used_by=("engine.death_work.handling.TENDING", "engine.death_work.seed.HANDLING")),
        DeathRole.KEEPER_OF_REMAINS: Defined("Keeper of remains", checked_by=(), used_by=("engine.death_work.seed.SACRED",)),
        DeathRole.OFFICIANT: Defined("Officiant", checked_by=(), used_by=("engine.death_work.seed.SACRED",)),
        DeathRole.MOURNER: Defined("Mourner", checked_by=("engine.death_work.seed.purity_of",), used_by=()),
        DeathRole.RECORD_KEEPER: Defined("Record keeper", checked_by=("engine.death_work.seed.seed_death_work",), used_by=()),
        DeathRole.CARRIER: Defined("Carrier", checked_by=(), used_by=("engine.death_work.handling.TENDING", "engine.death_work.seed.HANDLING")),
    },
)
