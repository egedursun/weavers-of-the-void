from aerona.catalog.urban import FIRE_RULE, HAULING_RULE, TALL_HOMES
from aerona.constants.units import PERCENT
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.urban import HousingLevel, Morphology
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


def modern_form(
    rules: Rules, profile: SettlementProfileRow, homes: list[HousingLevel], *, architecture: int, metallurgy: int, population: int
) -> Morphology | None:
    table = rules.morphology
    tall = sum(1 for home in homes if home in TALL_HOMES) * PERCENT / max(1, len(homes))
    if homes and tall >= table.vertical_share:
        return Morphology.VERTICAL
    if metallurgy >= table.sprawl_level and population >= table.sprawl_population and profile.morphology is not Morphology.VERTICAL:
        return Morphology.SPRAWL
    if architecture >= table.grid_level and population >= table.grid_population and profile.morphology in {Morphology.ORGANIC, Morphology.PLANNED}:
        return Morphology.GRID
    return None


def modernise(rules: Rules, profile: SettlementProfileRow, homes: list[HousingLevel], *, architecture: int, metallurgy: int, population: int) -> bool:
    form = modern_form(rules, profile, homes, architecture=architecture, metallurgy=metallurgy, population=population)
    if "morphology" in profile.locked or form is None or form is profile.morphology:
        return False
    profile.morphology = form
    return True


def grow_rings(rules: Rules, profile: SettlementProfileRow, infrastructure: SettlementInfrastructureRow | None) -> bool:
    if "morphology" in profile.locked or profile.morphology is not Morphology.ORGANIC or infrastructure is None:
        return False
    if infrastructure.walls_level < rules.morphology.rings_at:
        return False
    profile.morphology = Morphology.CONCENTRIC
    return True
