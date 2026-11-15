from aerona.constants.randomness import UINT32_MASK
from aerona.language.corpus import CorpusSources
from aerona.language.generator import NameKind, NamingVoice, generate_name
from aerona.language.phonology import Phonology
from aerona.language.similarity import NamePool, letter_distance, normalize_name, roman_numeral
from aerona.language.ugliness import is_ugly_name
from aerona.language.voice import build_voice, phonology_for
from aerona.rules.registry import Rules

RULES = Rules()
CORPUS = ["velar", "tirun", "amoth", "kessa", "orvael", "lumira", "sethan", "navor", "ithil", "marun", "doravel", "quenya"]
TURKISH_LETTERS = {chr(code) for code in (0x011F, 0x011E, 0x0131, 0x0130, 0x015F, 0x015E, 0x00E7, 0x00C7, 0x00F6, 0x00D6, 0x00FC, 0x00DC)}


def voice(words: list[str] = CORPUS, key: str = "11") -> NamingVoice:
    return build_voice(key, phonology_for(CorpusSources(world_name="Aerona", lexicon_words=words), None, RULES), RULES)


def test_ugly_names_are_detected() -> None:
    assert is_ugly_name("Ovvir", RULES)
    assert is_ugly_name("Mama", RULES)
    assert is_ugly_name("Hehahe", RULES)
    assert is_ugly_name("Toti", RULES)
    assert not is_ugly_name("Orvael", RULES)
    assert not is_ugly_name("Lumira", RULES)


def test_generation_is_deterministic() -> None:
    pool = NamePool([], RULES)
    first = [generate_name(voice(), f"seed{index}", NameKind.PERSON, pool, RULES) for index in range(10)]
    second = [generate_name(voice(), f"seed{index}", NameKind.PERSON, pool, RULES) for index in range(10)]
    assert first == second
    assert any(first)


def test_generated_names_pass_every_quality_filter() -> None:
    settings = RULES.language
    pool = NamePool(["Marun"], RULES)
    for kind in NameKind:
        for index in range(30):
            name = generate_name(voice(), f"{kind}:{index}", kind, pool, RULES)
            if name is None:
                continue
            assert settings.name_min_letters <= len(name) <= settings.name_max_letters
            assert name[0].isupper()
            assert not is_ugly_name(name, RULES)
            assert not pool.is_taken(name)
            pool.add(name)


def test_names_from_a_foreign_lexicon_contain_no_turkish_letters() -> None:
    lexicon = [
        "\u015fahin",
        "\u00e7a\u011flar",
        "\u0131rmak",
        "g\u00f6k",
        "\u00fcz\u00fcm",
        "da\u011f",
        "\u00e7i\u00e7ek",
        "y\u0131ld\u0131z",
        "deniz",
        "ate\u015f",
    ]
    pool = NamePool([], RULES)
    names = [generate_name(voice(lexicon, "tr"), f"n{index}", NameKind.PLACE, pool, RULES) for index in range(20)]
    produced = [name for name in names if name]
    assert produced
    assert all(not (set(name) & TURKISH_LETTERS) for name in produced)


def test_empty_phonology_yields_no_name() -> None:
    assert generate_name(NamingVoice(language_key="0", phonology=Phonology()), "x", NameKind.GENERAL, NamePool([], RULES), RULES) is None


def test_taken_names_are_never_returned() -> None:
    pool = NamePool([], RULES)
    name = generate_name(voice(), "fixed", NameKind.GENERAL, pool, RULES)
    assert name is not None
    pool.add(name)
    assert generate_name(voice(), "fixed", NameKind.GENERAL, pool, RULES) != name


def test_letter_distance_and_normalization() -> None:
    assert normalize_name("  V\u00e2lar ") == "valar"
    assert letter_distance("Lemir", "Lesir") == 1
    assert letter_distance("Lemir", "Lemirandos") == 2
    assert letter_distance("Orvael", "orvael") == 0


def test_name_pool_similarity_and_family_cap() -> None:
    pool = NamePool(["Lemir", "Lenmas", "Lenmur", "Lenmor", "Great Lemir"], RULES)
    assert pool.is_taken("lemir")
    assert pool.similar_to("Lesir") == "Lemir"
    assert pool.similar_to("Lenmaro") == "Lenmas"
    assert pool.similar_to("Lenmaro", family=False) is None
    assert pool.similar_to("Two Words") is None


def test_unique_names_take_roman_numerals() -> None:
    pool = NamePool(["Orvael", "Orvael II"], RULES)
    assert pool.unique("Orvael") == "Orvael III"
    assert pool.unique("Velar") == "Velar"
    assert roman_numeral(1994) == "MCMXCIV"
    assert roman_numeral(UINT32_MASK) == roman_numeral(3999)


def test_a_copied_name_pool_answers_exactly_as_the_original_and_grows_on_its_own() -> None:
    rules = Rules()
    names = ["Arvel", "Arvelin", "Borrow Deep", "Corvan", "Corvane", "Dask", "Arvex", "Arvon"]
    original = NamePool(names, rules)
    twin = original.copy()
    for probe in ["Arvek", "Corvan", "Daska", "Borrow Deep", "Arvelo", "Zim"]:
        assert twin.similar_to(probe) == original.similar_to(probe) and twin.is_taken(probe) == original.is_taken(probe)
        assert twin.unique(probe) == original.unique(probe)
    twin.add("Zimra")
    assert twin.is_taken("Zimra") and not original.is_taken("Zimra")
