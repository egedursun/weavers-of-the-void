from aerona.catalog.urban import FIRE_RULE, HAULING_RULE
from aerona.constants.units import PERCENT
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.urban import Morphology
from aerona.rules.registry import Rules


def spread_of(rules: Rules, morphology: Morphology) -> float:
    key = FIRE_RULE.get(morphology)
    return 1.0 if key is None else int(getattr(rules.morphology, key)) / PERCENT


def hauling_of(rules: Rules, morphology: Morphology) -> float:
    key = HAULING_RULE.get(morphology)
    return 1.0 if key is None else 1 + int(getattr(rules.morphology, key)) / PERCENT


def siege_of(rules: Rules, morphology: Morphology) -> int:
    return rules.morphology.concentric_siege if morphology is Morphology.CONCENTRIC else 0


def replan(profile: SettlementProfileRow) -> bool:
    if "morphology" in profile.locked or profile.morphology is Morphology.PLANNED:
        return False
    profile.morphology = Morphology.PLANNED
    return True


def grow_rings(rules: Rules, profile: SettlementProfileRow, infrastructure: SettlementInfrastructureRow | None) -> bool:
    if "morphology" in profile.locked or profile.morphology is not Morphology.ORGANIC or infrastructure is None:
        return False
    if infrastructure.walls_level < rules.morphology.rings_at:
        return False
    profile.morphology = Morphology.CONCENTRIC
    return True
