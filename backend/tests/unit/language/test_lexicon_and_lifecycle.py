from aerona.domain.enums.chronicle import PartOfSpeech, WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.language.corpus import CorpusSources
from aerona.language.dialect import dialect_name, dialect_should_split, founded_dialect_subtype, plan_engine_dialect
from aerona.language.epoch_words import EpochWordSource, epoch_word_meaning, plan_epoch_words
from aerona.language.lexicon import LexiconEntry, admissible_entries, cognates
from aerona.language.primitive import plan_primitive_language, primitive_language_name
from aerona.language.similarity import NamePool
from aerona.language.succession import SpokenNearby, local_language, nearest_language
from aerona.language.titles import HolderTitle, community_phrase, from_among, holder_title, holder_title_of, possessive
from aerona.language.vitality import VitalityChange, assess_vitality, death_notes_allowed, vitality_note
from aerona.language.voice import build_voice, phonology_for
from aerona.language.writing import ScriptChoiceInputs, choose_writing_system, complexity_after_script, script_note, writing_system_weights
from aerona.rules.registry import Rules

RULES = Rules()


def entries(*words: str) -> list[LexiconEntry]:
    return [LexiconEntry(word=word, meaning=f"meaning of {word}") for word in words]


def test_admissible_entries_skip_empty_duplicate_and_meaningless_words() -> None:
    raw = [*entries("Velar", "velar", " "), LexiconEntry(word="tirun", meaning=""), *entries("amoth")]
    admitted = admissible_entries(raw, ["AMOTH"])
    assert [entry.word for entry in admitted] == ["Velar"]


def test_cognates_match_equal_words_and_shared_roots() -> None:
    found = cognates(entries("velar", "tirun", "amothar"), entries("Velar", "amothen", "zek"), RULES)
    assert [(item.first_word, item.second_word) for item in found] == [("velar", "Velar"), ("amothar", "amothen")]


def test_cognates_are_capped() -> None:
    many = entries(*[f"word{index}" for index in range(50)])
    assert len(cognates(many, many, RULES)) == RULES.language.max_cognates


def test_writing_system_choice_follows_weights() -> None:
    inputs = ScriptChoiceInputs(merchant_share=40, farmer_share=0, priest_share=0, complexity=0, sacredness=0)
    weights = writing_system_weights(inputs, RULES)
    assert weights[WritingSystem.ALPHABET] == RULES.deep_life.script_alphabet_base + 40 / RULES.deep_life.script_alphabet_divisor
    assert choose_writing_system(inputs, lambda: 0.0, RULES) is WritingSystem.ALPHABET
    assert choose_writing_system(inputs, lambda: 0.999999, RULES) is WritingSystem.NOTCH
    assert complexity_after_script(None, RULES) == RULES.deep_life.script_default_complexity + RULES.deep_life.script_complexity_gain
    assert complexity_after_script(99, RULES) == 100
    assert "a syllabary" in script_note("Velar", "Tirun", WritingSystem.SYLLABARY)


def test_dialect_split_conditions() -> None:
    age = RULES.world_effects.dialect_min_settlement_age
    assert dialect_should_split(age, 2, False, lambda: 0.0, RULES)
    assert not dialect_should_split(age - 1, 2, False, lambda: 0.0, RULES)
    assert not dialect_should_split(age, 0, False, lambda: 0.0, RULES)
    assert not dialect_should_split(age, 2, True, lambda: 0.0, RULES)
    assert not dialect_should_split(age, 2, False, lambda: 0.999, RULES)


def test_engine_dialect_carries_words_from_the_parent() -> None:
    plan = plan_engine_dialect("Tirun", "Velar", entries(*[f"w{index}" for index in range(10)]), lambda: 0.3, RULES)
    assert plan.name == dialect_name("Velar") == "Velar Dialect"
    assert len(plan.inherited_words) == RULES.world_effects.dialect_inherited_words
    assert all(entry.origin.endswith("in the Tirun language") for entry in plan.inherited_words)
    assert plan.spread == RULES.world_effects.dialect_spread
    assert founded_dialect_subtype("Tirun", None) == "Tirun dialect"
    assert founded_dialect_subtype("Tirun", "river cant") == "Tirun dialect: river cant"


def test_language_vitality_transitions() -> None:
    grace = RULES.deep_life.language_death_grace
    assert assess_vitality(grace, 0, False, False, RULES) is None
    died = assess_vitality(grace + 1, 0, False, True, RULES)
    assert died is not None
    assert died.change is VitalityChange.DIED
    assert died.decipherable
    assert "script survives" in vitality_note("Tirun", died)
    revived = assess_vitality(grace + 1, 3, True, False, RULES)
    assert revived is not None
    assert revived.change is VitalityChange.REVIVED
    assert vitality_note("Tirun", revived) == "Tirun is spoken again."
    assert assess_vitality(grace + 1, 3, False, False, RULES) is None
    assert death_notes_allowed(0, RULES)
    assert not death_notes_allowed(RULES.deep_life.language_death_note_cap, RULES)


def test_nearest_language_prefers_location_then_ancestors_then_weighted_majority() -> None:
    assert nearest_language(5, [6], [], RULES) == 5
    assert nearest_language(None, [None, 6], [], RULES) == 6
    speakers = [SpokenNearby(9, False), SpokenNearby(9, False), SpokenNearby(4, True)]
    assert nearest_language(None, [], speakers, RULES) == 4
    assert nearest_language(None, [], [SpokenNearby(9, False), SpokenNearby(4, False)], RULES) == 4
    assert nearest_language(None, [], [], RULES) is None


def test_primitive_language_plan() -> None:
    voice = build_voice("21", phonology_for(CorpusSources(world_name="Aerona", lexicon_words=["velar", "tirun", "amoth", "kessa"]), None, RULES), RULES)
    plan = plan_primitive_language(voice, "Velar Folk", NamePool([], RULES), RULES)
    assert plan.name == primitive_language_name("Velar Folk") == "Velar Language"
    assert [entry.meaning for entry in plan.words] == ["water", "fire", "earth", "mother", "sky", "road", "dead", "bread"]
    assert all(entry.word and entry.word == entry.word.lower() for entry in plan.words)
    assert plan.complexity == RULES.deep_life.primitive_language_complexity


def test_epoch_words_respect_caps_and_part_of_speech() -> None:
    sources = [
        EpochWordSource(
            entity_id=index, entity_type=EntityType.SETTLEMENT if index % 2 else EntityType.ITEM, name=f"Name{index} Hold", subtype=None, language_id=1
        )
        for index in range(10)
    ]
    sources.append(
        EpochWordSource(entity_id=99, entity_type=EntityType.PLACE, name="Velar Falls", subtype="waterfall", language_id=2, named_from_language=True)
    )
    sources.append(EpochWordSource(entity_id=98, entity_type=EntityType.LANGUAGE, name="Ignored", subtype=None, language_id=2))
    words = plan_epoch_words(sources, 4, lambda language, seed: f"wd{seed.split(':')[-1]}x", {1: {"WD0X"}}, RULES)
    per_language: dict[int, int] = {}
    for word in words:
        per_language[word.language_id] = per_language.get(word.language_id, 0) + 1
    assert per_language[1] == RULES.language.epoch_words_per_language
    assert "wd0x" not in [word.entry.word for word in words]
    falls = next(word for word in words if word.entity_id == 99)
    assert falls.entry.word == "velar"
    assert falls.entry.part_of_speech is PartOfSpeech.PROPER_NAME
    assert falls.entry.meaning == "waterfall: Velar Falls"
    assert "Epoch 4" in falls.entry.origin
    assert epoch_word_meaning(EntityType.LEGEND, "Ash", None) == "the tale of Ash"


def test_titles_and_community_phrases() -> None:
    assert holder_title(EntityType.ITEM) is HolderTitle.BEARER
    assert holder_title(EntityType.SETTLEMENT) is HolderTitle.RULER
    assert holder_title_of(EntityType.LEGEND, "Ash") == "Teller of Ash"
    assert community_phrase(EntityType.MORTAL, "Kessa") == "around Kessa"
    assert community_phrase(EntityType.PEOPLE, "Velar Folk") == "among the Velar Folk"
    assert community_phrase(EntityType.PEOPLE, "Velar") == "among the Velar people"
    assert community_phrase(EntityType.CULT, "Ash Order") == "within Ash Order"
    assert community_phrase(EntityType.SETTLEMENT, "Tirun") == "in Tirun"
    assert possessive("Moros") == "Moros'"
    assert from_among("Tirun", "peasants") == "from among Tirun's peasants"


def test_local_language_walks_the_location_chain_within_depth() -> None:
    assert local_language(3, 4, [5], RULES) == 3
    assert local_language(None, 4, [5], RULES) == 4
    assert local_language(None, None, [None, 5], RULES) == 5
    depth = RULES.language.local_language_depth
    assert local_language(None, None, [*([None] * depth), 5], RULES) is None
