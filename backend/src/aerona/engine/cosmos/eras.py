from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.world import ClimateEra
from aerona.rules.registry import Rules


def emergent_era(rules: Rules, physics: WorldPhysicsRow) -> ClimateEra | None:
    table = rules.planetary_climate
    if physics.cryosphere >= table.ice_age_cryosphere:
        return ClimateEra.ICE_AGE
    if physics.heat_shift >= table.scorching_heat:
        return ClimateEra.SCORCHING
    return None
