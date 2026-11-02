from aerona.core.errors import ValidationFailedError
from aerona.db.tables.rule_override import RuleOverrideRow
from aerona.migration.legacy.report import MigrationReport, RuleMapping
from aerona.migration.legacy.source import LegacyRow
from aerona.migration.legacy.values import as_dict, as_float
from aerona.migration.legacy.vocabulary import Vocabulary
from aerona.rules.registry import Rules
from aerona.rules.snapshot import OverrideMap, apply_overrides, catalog, coerce, constraint_violations, is_default

PATH_SEPARATOR = "."
APPLIED = "applied"
DEFAULT = "default"
UNMAPPED = "unmapped"
INVALID = "invalid"
REJECTED = "rejected by a rule constraint"


def resolve_target(vocabulary: Vocabulary, legacy_key: str, defaults: Rules) -> tuple[str, str] | None:
    target = vocabulary.rules.get(legacy_key)
    if not target or target not in {descriptor.path for descriptor in catalog(defaults)}:
        return None
    namespace, key = target.split(PATH_SEPARATOR, 1)
    return namespace, key


def map_overrides(vocabulary: Vocabulary, state: LegacyRow, report: MigrationReport) -> OverrideMap:
    defaults = Rules()
    overrides: OverrideMap = {}
    mappings: list[RuleMapping] = []
    for legacy_key, raw in sorted(as_dict(state.json("rule_overrides")).items()):
        value = as_float(raw)
        target = resolve_target(vocabulary, legacy_key, defaults)
        if target is None or value is None:
            mappings.append(RuleMapping(legacy_key=legacy_key, target=None, value=value, status=UNMAPPED))
            continue
        path = PATH_SEPARATOR.join(target)
        try:
            coerced = coerce(defaults, target[0], target[1], value)
        except ValidationFailedError as error:
            mappings.append(RuleMapping(legacy_key=legacy_key, target=path, value=value, status=f"{INVALID}: {error}"))
            continue
        if is_default(defaults, target[0], target[1], coerced):
            mappings.append(RuleMapping(legacy_key=legacy_key, target=path, value=float(coerced), status=DEFAULT))
            continue
        overrides[target] = float(coerced)
        mappings.append(RuleMapping(legacy_key=legacy_key, target=path, value=float(coerced), status=APPLIED))
    violations = constraint_violations(apply_overrides(defaults, overrides))
    if violations:
        for mapping in mappings:
            if mapping.status == APPLIED:
                mapping.status = REJECTED
        report.warn("rule constraint", "rule_overrides", " ".join(violations))
        overrides = {}
    report.rules.extend(mappings)
    return overrides


def override_rows(overrides: OverrideMap) -> list[RuleOverrideRow]:
    return [RuleOverrideRow(namespace=namespace, key=key, value=value) for (namespace, key), value in sorted(overrides.items())]
