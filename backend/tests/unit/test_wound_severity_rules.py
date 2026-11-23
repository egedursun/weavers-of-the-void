import dataclasses
import re

from aerona.db.tables.body import SEVERITY_MAX
from aerona.rules.model import RULE_METADATA_KEY, RuleMeta
from aerona.rules.registry import Rules

GOD_SCALES = frozenset({"divine_wounds", "outer_beings"})
RELATIVE = re.compile(r"per step|each step|%|chance|against|force|share|\bhp\b", re.IGNORECASE)
ABSOLUTE = re.compile(r"\bseverity\b", re.IGNORECASE)
MORTAL_WOUND = re.compile(r"\bwounds?\b|\binjur", re.IGNORECASE)


def severity_rules() -> list[tuple[str, str, RuleMeta]]:
    found: list[tuple[str, str, RuleMeta]] = []
    rules = Rules()
    for namespace in dataclasses.fields(rules):
        table = getattr(rules, namespace.name)
        if namespace.name in GOD_SCALES or not dataclasses.is_dataclass(table):
            continue
        for item in dataclasses.fields(table):
            meta = item.metadata.get(RULE_METADATA_KEY)
            if meta is not None and ABSOLUTE.search(meta.label) and MORTAL_WOUND.search(meta.label) and not RELATIVE.search(meta.label):
                found.append((namespace.name, item.name, meta))
    return found


def test_every_rule_that_sets_a_wound_severity_stays_on_the_severity_scale() -> None:
    found = severity_rules()
    assert ("places", "hot_spring_heal") in {(space, name) for space, name, _ in found}
    wrong = [f"{space}.{name} reaches {meta.maximum}" for space, name, meta in found if meta.maximum > SEVERITY_MAX]
    assert not wrong, wrong
