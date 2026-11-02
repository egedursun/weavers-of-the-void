import json

from aerona.language.lineage import ancestor_chain, phonology_lineage, resolve_signature
from aerona.language.phonology import Phonology, build_phonology
from aerona.language.signature import LanguageSignature, derive_signature
from aerona.rules.registry import Rules

RULES = Rules()
CORPUS = ["velar", "tirun", "amoth", "kessa", "orvael", "lumira", "sethan", "navor", "ithil", "marun"]


def phonology() -> Phonology:
    return build_phonology(CORPUS, None, RULES)


def test_signature_round_trips_losslessly() -> None:
    signature = derive_signature("7", phonology(), None, RULES)
    assert signature is not None
    assert signature.consonants
    data = signature.model_dump()
    assert LanguageSignature.model_validate(data) == signature
    assert LanguageSignature.model_validate_json(signature.model_dump_json()) == signature
    assert json.loads(signature.model_dump_json())["consonants"] == signature.consonants


def test_signature_is_deterministic_and_bounded() -> None:
    first = derive_signature("7", phonology(), None, RULES)
    second = derive_signature("7", phonology(), None, RULES)
    assert first == second
    assert first is not None
    assert len(first.consonants) >= min(RULES.language.signature_consonant_floor, len(set(first.consonants)))
    assert len(first.ending) <= RULES.language.signature_ending_max_letters
    assert first.length_bias in (-1, 0, 1)
    assert len(set(first.consonants)) == len(first.consonants)


def test_signature_needs_enough_consonants() -> None:
    assert derive_signature("1", build_phonology(["aia", "oea"], None, RULES), None, RULES) is None


def test_child_signature_inherits_cluster_and_length_bias() -> None:
    parent = LanguageSignature(consonants="lmnrv", cluster="rn", ending="ar", length_bias=1)
    child = derive_signature("8", phonology(), parent, RULES)
    assert child is not None
    assert child.cluster == "rn"
    assert child.length_bias == 1
    assert len(child.ending) == 2
    assert child.ending.endswith("r")
    assert len(child.consonants) <= len(parent.consonants)


def test_ancestor_chain_stops_on_cycles_and_depth() -> None:
    parents = {1: 2, 2: 3, 3: 1}
    assert ancestor_chain(1, parents, 10) == [2, 3]
    assert ancestor_chain(1, {1: 2, 2: 3, 3: 4}, 2) == [2, 3]
    assert ancestor_chain(5, {}, 3) == []


def test_resolve_signature_derives_through_the_lineage_with_cycle() -> None:
    stored = {2: LanguageSignature(consonants="lmnrv", cluster="rn", ending="ar", length_bias=-1)}
    resolved = resolve_signature(1, {1: 2, 2: 1}, stored, lambda _: phonology(), RULES)
    assert resolved is not None
    assert resolved.cluster == "rn"
    assert resolve_signature(2, {}, stored, lambda _: phonology(), RULES) == stored[2]
    cyclic = resolve_signature(3, {3: 4, 4: 3}, {}, lambda _: phonology(), RULES)
    assert cyclic is not None


def test_phonology_lineage_is_limited_by_ancestry_depth() -> None:
    parents = {index: index + 1 for index in range(1, 20)}
    assert phonology_lineage(1, parents, RULES) == list(range(1, RULES.language.ancestry_depth + 2))
