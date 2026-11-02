from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


def sanity_of(rules: Rules, entity: EntityRow) -> int:
    return entity.sanity if entity.sanity is not None else rules.cosmic_horror.default_sanity


def shift_sanity(rules: Rules, entity: EntityRow, delta: float) -> int:
    entity.sanity = max(PERCENT_MIN, min(PERCENT_MAX, round_half_up(sanity_of(rules, entity) + delta)))
    return entity.sanity
