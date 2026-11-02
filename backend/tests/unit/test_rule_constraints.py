from aerona.rules.constraints import ASCENDING_CHAINS
from aerona.rules.registry import Rules
from aerona.rules.snapshot import constraint_violations, value_at


def test_default_rules_satisfy_every_constraint() -> None:
    assert constraint_violations(Rules()) == []


def test_every_constraint_path_exists() -> None:
    for chain in ASCENDING_CHAINS:
        for path in chain.paths:
            value_at(Rules(), path)
