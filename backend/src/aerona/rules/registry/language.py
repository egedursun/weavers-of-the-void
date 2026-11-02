from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class LanguageRules:
    similar_name_max_length: int = rule(7, 0, 20, RuleGroup.LANGUAGE_AND_NAMES, "Longest name for which a single-letter difference is forbidden (letters)")
    name_family_cap: int = rule(3, 1, 50, RuleGroup.LANGUAGE_AND_NAMES, "Maximum names starting with the same root (first letters, see root letters)")
    motif_threshold_pct: int = rule(18, 1, 100, RuleGroup.LANGUAGE_AND_NAMES, "Tired motif: if it appears in this percentage of recent descriptions")
    motifs_in_prompt: int = rule(14, 0, 60, RuleGroup.LANGUAGE_AND_NAMES, "Tired motifs shown in the prompt")
    motif_window: int = rule(120, 15, 2000, RuleGroup.LANGUAGE_AND_NAMES, "Recent descriptions examined for tired motifs")
    motif_pair_threshold_pct: int = rule(
        15, 1, 100, RuleGroup.LANGUAGE_AND_NAMES, "Tired image: if a two-word image appears in this percentage of recent deepenings and epoch narratives"
    )
    motif_root_min_letters: int = rule(
        3, 1, 20, RuleGroup.LANGUAGE_AND_NAMES, "Tired motif and piled names: minimum letters of a word root that is counted; shorter words are not counted"
    )
    motif_min_repeats: int = rule(6, 1, 1000, RuleGroup.LANGUAGE_AND_NAMES, "Tired motif: minimum repetitions")
    motif_min_records: int = rule(15, 1, 2000, RuleGroup.LANGUAGE_AND_NAMES, "Tired motif: minimum descriptions before checking starts")
    root_letters: int = rule(4, 1, 20, RuleGroup.LANGUAGE_AND_NAMES, "Name family and common root: letters compared from the start")
    motif_cache_per_world: int = rule(16, 1, 1000, RuleGroup.LANGUAGE_AND_NAMES, "Tired motif: measurements cached per world")
    motif_recent_epochs: int = rule(1, 1, 50, RuleGroup.LANGUAGE_AND_NAMES, "Rising image: closed epochs measured (the epoch being written is not counted)")
    motif_previous_epochs: int = rule(4, 1, 200, RuleGroup.LANGUAGE_AND_NAMES, "Rising image: earlier epochs it is compared against")
    motif_rising_min_pct: int = rule(
        8,
        0,
        100,
        RuleGroup.LANGUAGE_AND_NAMES,
        "Rising image: share of the recent epochs' creations a tag must reach (%; the family drifted to when another is banned)",
    )
    motif_rising_ratio_pct: int = rule(140, 100, 10000, RuleGroup.LANGUAGE_AND_NAMES, "Rising image: growth over the earlier epochs that makes a tag tired (%)")
    motif_spread_world_pct: int = rule(
        50, 1, 100, RuleGroup.LANGUAGE_AND_NAMES, "Cosmos-wide image: a tag tired in this share of the worlds is banned in every world (%)"
    )
    dialect_root_min_letters: int = rule(3, 1, 20, RuleGroup.LANGUAGE_AND_NAMES, "Dialect check: minimum letters of an invented root examined")
    signature_consonant_pct: int = rule(62, 10, 100, RuleGroup.LANGUAGE_AND_NAMES, "Language signature: share chosen from the world's consonants (%)")
    signature_ending_pct: int = rule(50, 0, 100, RuleGroup.LANGUAGE_AND_NAMES, "Chance names end with the language's own ending (%)")
    signature_cluster_pct: int = rule(30, 0, 100, RuleGroup.LANGUAGE_AND_NAMES, "Chance the language's favourite consonant cluster appears in names (%)")
    name_attempts: int = rule(24, 1, 200, RuleGroup.LANGUAGE_AND_NAMES, "Maximum attempts in one name generation")
    epoch_words_per_language: int = rule(3, 0, 50, RuleGroup.LANGUAGE_AND_NAMES, "Epoch words: maximum per language")
    epoch_words_total: int = rule(12, 0, 200, RuleGroup.LANGUAGE_AND_NAMES, "Epoch words: maximum in total")
    alphabet_min_samples: int = rule(60, 1, 100000, RuleGroup.LANGUAGE_AND_NAMES, "World alphabet: minimum letter samples before filtering starts")
    alphabet_min_per_mille: int = rule(
        5, 0, 1000, RuleGroup.LANGUAGE_AND_NAMES, "World alphabet: minimum frequency for a letter to count in the alphabet (per mille)"
    )
    dialect_sample_names: int = rule(30, 0, 500, RuleGroup.LANGUAGE_AND_NAMES, "Maximum sample names taken from the dialect text")
    ancestry_depth: int = rule(3, 0, 20, RuleGroup.LANGUAGE_AND_NAMES, "Ancestor-language generations included in the phonology")
    phonology_min_words: int = rule(8, 0, 200, RuleGroup.LANGUAGE_AND_NAMES, "Minimum sample words for the phonology (if fewer, filled from names)")
    phonology_fallback_names: int = rule(60, 0, 2000, RuleGroup.LANGUAGE_AND_NAMES, "Maximum world names read to top up a thin phonology corpus")
    phonology_max_syllables: int = rule(6, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Maximum syllables of a word entering the phonology")
    default_avg_syllables: int = rule(24, 10, 100, RuleGroup.LANGUAGE_AND_NAMES, "Average syllables if there are no samples (tenths)")
    signature_min_consonants: int = rule(3, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Minimum consonants for a language signature")
    signature_kept_consonants: int = rule(2, 0, 30, RuleGroup.LANGUAGE_AND_NAMES, "Most frequent consonants always kept in the language signature")
    signature_consonant_floor: int = rule(5, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Minimum consonants in the language signature")
    signature_ending_max_letters: int = rule(4, 1, 20, RuleGroup.LANGUAGE_AND_NAMES, "Maximum letters of the language signature's ending")
    inherited_shift_min_consonants: int = rule(3, 0, 30, RuleGroup.LANGUAGE_AND_NAMES, "Minimum consonants for a consonant shift in an inherited signature")
    signature_length_bias_weight: int = rule(
        5, 0, 50, RuleGroup.LANGUAGE_AND_NAMES, "Effect of the language signature's length bias on name syllables (tenths)"
    )
    ugly_same_onset_syllables: int = rule(3, 2, 20, RuleGroup.LANGUAGE_AND_NAMES, "Ugly name: number of syllables starting with the same consonant")
    name_min_syllables: int = rule(2, 1, 10, RuleGroup.LANGUAGE_AND_NAMES, "Minimum syllables of a generated name")
    name_max_syllables: int = rule(4, 1, 20, RuleGroup.LANGUAGE_AND_NAMES, "Maximum syllables of a generated name")
    person_syllable_bias: int = rule(-3, -50, 50, RuleGroup.LANGUAGE_AND_NAMES, "Syllable tendency in person names (tenths)")
    place_syllable_bias: int = rule(4, -50, 50, RuleGroup.LANGUAGE_AND_NAMES, "Syllable tendency in place and people names (tenths)")
    syllable_repeat_retries: int = rule(4, 0, 50, RuleGroup.LANGUAGE_AND_NAMES, "Re-picks to avoid the same syllable twice in a row")
    name_min_letters: int = rule(3, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Minimum letters of a generated name")
    name_max_letters: int = rule(12, 1, 60, RuleGroup.LANGUAGE_AND_NAMES, "Maximum letters of a generated name")
    max_cognates: int = rule(30, 0, 1000, RuleGroup.LANGUAGE_AND_NAMES, "Maximum common roots (cognates) shown between two languages")
    local_language_depth: int = rule(6, 1, 50, RuleGroup.LANGUAGE_AND_NAMES, "Depth of the location chain searched for a local language for the epoch word")
    epoch_word_min_letters: int = rule(3, 1, 30, RuleGroup.LANGUAGE_AND_NAMES, "Minimum letters of an epoch word")
