from aerona.language.alphabet import fold_word, is_vowel


def _next_vowel(word: str, start: int) -> int:
    index = start
    while index < len(word) and not is_vowel(word[index]):
        index += 1
    return index


def syllabify(word: str) -> list[str]:
    letters = fold_word(word)
    syllables: list[str] = []
    index = 0
    while index < len(letters):
        start = index
        while index < len(letters) and not is_vowel(letters[index]):
            index += 1
        while index < len(letters) and is_vowel(letters[index]):
            index += 1
        syllable = letters[start:index]
        following = _next_vowel(letters, index)
        cluster = letters[index:following]
        if following >= len(letters):
            syllable += cluster
            index = following
        elif len(cluster) >= 2:
            syllable += cluster[0]
            index += 1
        if syllable:
            syllables.append(syllable)
    return syllables
