from aerona.language.alphabet import fold_word, leading_consonants
from aerona.language.corpus import CorpusSources, assemble_corpus, is_language_label, world_alphabet
from aerona.language.phonology import build_phonology, restrict_to_consonants, weighted_pick
from aerona.language.syllables import syllabify
from aerona.rules.registry import Rules

RULES = Rules()


def test_syllabifier_splits_onset_nucleus_coda() -> None:
    assert syllabify("Orvaelith") == ["or", "vae", "lith"]
    assert syllabify("Kessandra") == ["kes", "san", "dra"]
    assert syllabify("brr") == ["brr"]
    assert syllabify("") == []


def test_folding_maps_foreign_letters_onto_the_conlang_alphabet() -> None:
    assert fold_word("Da\u015fbu\u015f\u00e7a") == "dasbusca"
    assert fold_word("\u0131\u011f\u00f6\u00fc") == "igou"
    assert fold_word("V\u00e2l-ar!") == "v\u00e2lar"
    assert leading_consonants("str\u00e2") == "str"


def test_phonology_counts_initial_medial_and_final_syllables() -> None:
    phonology = build_phonology(["velar", "tirun", "amoth lumira"], None, RULES)
    assert dict(phonology.initial) == {"ve": 1, "ti": 1, "a": 1, "lu": 1}
    assert dict(phonology.medial) == {"mi": 1}
    assert dict(phonology.final) == {"lar": 1, "run": 1, "moth": 1, "ra": 1}
    assert phonology.average_syllables == 9 / 4
    assert phonology.word_count == 3


def test_empty_phonology_uses_default_average() -> None:
    phonology = build_phonology([], None, RULES)
    assert phonology.is_empty
    assert phonology.average_syllables == RULES.language.default_avg_syllables / 10


def test_phonology_respects_alphabet_and_syllable_limit() -> None:
    phonology = build_phonology(["velar", "xyzzy", "valavalavalavala", "ka1"], frozenset("velar"), RULES)
    assert set(phonology.initial) == {"ve"}


def test_weighted_pick_is_deterministic_and_handles_empty() -> None:
    counts = {"a": 1, "b": 3}
    assert weighted_pick(counts, lambda: 0.0) == "a"
    assert weighted_pick(counts, lambda: 0.99) == "b"
    assert weighted_pick({}, lambda: 0.5) == ""


def test_signature_filter_keeps_unfiltered_when_too_few_remain() -> None:
    counts = {"ka": 1, "ra": 1, "zo": 1}
    assert set(restrict_to_consonants(counts, "kr")) == {"ka", "ra"}
    assert restrict_to_consonants(counts, "k") == counts
    assert restrict_to_consonants(counts, "") == counts


def test_language_labels_are_excluded_from_the_corpus() -> None:
    assert is_language_label("Elvish", "Aerona", RULES)
    assert is_language_label("Speechcraft", "Aerona", RULES)
    assert is_language_label("Aeronan", "Aerona", RULES)
    assert not is_language_label("Velar", "Aerona", RULES)


def test_corpus_is_topped_up_in_order_until_the_minimum() -> None:
    sources = CorpusSources(
        world_name="Aerona",
        lexicon_words=["velar"],
        language_name="Tirun Tongue",
        naming_samples=["Kessa", "Orvael"],
        speaker_names=["Amoth the Wise"],
        world_names=["Lumira Coast", "Elvish", "Sethan"],
    )
    assert assemble_corpus(sources, RULES) == ["velar", "Tirun", "Kessa", "Orvael", "Amoth", "Lumira", "Sethan"]
    full = CorpusSources(world_name="Aerona", lexicon_words=[f"word{index}" for index in range(10)], naming_samples=["Kessa"])
    assert "Kessa" not in assemble_corpus(full, RULES)


def test_world_alphabet_needs_enough_samples_and_drops_rare_letters() -> None:
    assert world_alphabet(["velar"], RULES) is None
    words = ["velar"] * 40 + ["q"]
    alphabet = world_alphabet(words, RULES)
    assert alphabet == frozenset("velar")
