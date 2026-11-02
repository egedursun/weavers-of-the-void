from aerona.language.naming_rule import NamingRule, naming_violations
from aerona.rules.registry import Rules

RULES = Rules()


def test_naming_rule_round_trips() -> None:
    rule = NamingRule(vowels="aeo", consonants="lmnrstv", forbidden_sounds=("th",), sample_names=("Velar", "Moran"), endings=("ar",))
    assert NamingRule.model_validate_json(rule.model_dump_json()) == rule
    assert rule.alphabet() == frozenset("aeolmnrstv")
    assert NamingRule().alphabet() is None


def test_violations_list_forbidden_letters_and_sounds() -> None:
    rule = NamingRule(vowels="aeo", consonants="lmnrstvh", forbidden_sounds=("th",))
    violations = naming_violations("Velur Thoran", rule, [], RULES)
    assert [violation.word for violation in violations] == ["Velur", "Thoran"]
    assert violations[0].forbidden_letters == ("u",)
    assert violations[1].forbidden_sounds == ("th",)


def test_ordinary_words_and_short_roots_are_exempt() -> None:
    rule = NamingRule(vowels="ae")
    assert naming_violations("River of Velar", rule, ["river"], RULES) == []
    assert naming_violations("Rivers", rule, ["river"], RULES) == []
    assert naming_violations("Unconstrained", NamingRule(), [], RULES) == []
