from aerona.constants.units import PERCENT
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.rules.registry import Rules

TENTHS = 10


def dose_mutation(rules: Rules, field: WorldFieldRow | None) -> float:
    if field is None:
        return 0.0
    return field.surface_dose // TENTHS * rules.space_weather.mutation_per_dose_pct / PERCENT


def compass_error_of(field: WorldFieldRow | None) -> int:
    return field.compass_error if field is not None else 0
