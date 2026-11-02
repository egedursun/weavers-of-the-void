from itertools import pairwise

from aerona.constants.language import UGLY_PAIR_SYLLABLES, UGLY_SHORT_SYLLABLE_LETTERS
from aerona.language.alphabet import fold_word, is_vowel, leading_consonants
from aerona.language.syllables import syllabify
from aerona.rules.registry import Rules


def _has_doubled_consonant(word: str) -> bool:
    return any(left == right and not is_vowel(left) for left, right in pairwise(word))


def is_ugly_name(name: str, rules: Rules) -> bool:
    word = fold_word(name)
    if _has_doubled_consonant(word):
        return True
    syllables = syllabify(word)
    if any(current == previous for previous, current in pairwise(syllables)):
        return True
    onsets: dict[str, int] = {}
    for syllable in syllables:
        onset = leading_consonants(syllable)
        if onset:
            onsets[onset] = onsets.get(onset, 0) + 1
    if any(count >= rules.language.ugly_same_onset_syllables for count in onsets.values()):
        return True
    return (
        len(syllables) == UGLY_PAIR_SYLLABLES
        and syllables[0][:1] == syllables[1][:1]
        and all(len(syllable) <= UGLY_SHORT_SYLLABLE_LETTERS for syllable in syllables)
    )
