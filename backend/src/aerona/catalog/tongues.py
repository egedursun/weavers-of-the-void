from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.chronicle import PartOfSpeech, WritingSystem
from aerona.domain.enums.tongues import LanguageModality, MorphologyType, NumberSystem, SoundChangeKind, WordOrder

W = WritingSystem
M = LanguageModality

LENITION = MappingProxyType({"p": "f", "b": "v", "t": "s", "d": "z", "k": "h", "g": "h", "c": "h", "q": "h"})

SCRIPT_CHAIN = total(
    WritingSystem,
    {
        W.PICTOGRAPHIC: W.LOGOGRAPHIC,
        W.LOGOGRAPHIC: W.MIXED,
        W.MIXED: W.SYLLABARY,
        W.SYLLABARY: W.ABJAD,
        W.ABJAD: W.ALPHABET,
        W.ALPHABET: None,
        W.KNOT: None,
        W.NOTCH: None,
    },
)

SCRIPT_SIGNS = total(
    WritingSystem,
    {
        W.PICTOGRAPHIC: 900,
        W.LOGOGRAPHIC: 2400,
        W.MIXED: 600,
        W.SYLLABARY: 80,
        W.ABJAD: 24,
        W.ALPHABET: 28,
        W.KNOT: 40,
        W.NOTCH: 20,
    },
)

WRITABLE = total(LanguageModality, {M.VOCAL: True, M.SIGN: True, M.SCENT: False, M.COLOUR: True, M.TELEPATHIC: False, M.DATA: True, M.CHEMICAL: False})

MODALITY_NEEDS = total(
    LanguageModality,
    {
        M.VOCAL: frozenset({BodyFunction.SPEECH}),
        M.SIGN: frozenset({BodyFunction.SIGHT, BodyFunction.GRASP}),
        M.COLOUR: frozenset({BodyFunction.SIGHT, BodyFunction.PRESENCE}),
        M.SCENT: frozenset({BodyFunction.PRESENCE}),
        M.TELEPATHIC: frozenset({BodyFunction.COGNITION}),
        M.DATA: frozenset({BodyFunction.COGNITION}),
        M.CHEMICAL: frozenset({BodyFunction.PRESENCE}),
    },
)

MODALITY_ORDER = (M.VOCAL, M.SIGN, M.COLOUR, M.SCENT, M.TELEPATHIC)

KIND_WEIGHTS = total(
    SoundChangeKind,
    {SoundChangeKind.SHIFT: 3, SoundChangeKind.LENITION: 3, SoundChangeKind.VOWEL_SHIFT: 3, SoundChangeKind.MERGER: 1, SoundChangeKind.LOSS: 2},
)

ORDERS = tuple(order for order in WordOrder if order is not WordOrder.FREE)

LOAN_RULES = total(
    MorphologyType,
    {
        MorphologyType.ISOLATING: "loan_isolating_pct",
        MorphologyType.AGGLUTINATIVE: None,
        MorphologyType.FUSIONAL: None,
        MorphologyType.POLYSYNTHETIC: "loan_polysynthetic_pct",
    },
)

COMPOUNDING = frozenset({MorphologyType.AGGLUTINATIVE, MorphologyType.POLYSYNTHETIC})

NUMBER_COUNTS = total(
    NumberSystem,
    {NumberSystem.NONE: 0, NumberSystem.SINGULAR_PLURAL: 2, NumberSystem.DUAL: 3, NumberSystem.TRIAL: 4, NumberSystem.PAUCAL: 4},
)

PART_OF_SPEECH_LABELS = total(
    PartOfSpeech,
    {
        PartOfSpeech.NOUN: "Noun",
        PartOfSpeech.VERB: "Verb",
        PartOfSpeech.ADJECTIVE: "Adjective",
        PartOfSpeech.AFFIX: "Affix",
        PartOfSpeech.TITLE: "Title",
        PartOfSpeech.PLACE_NAME: "Place name",
        PartOfSpeech.PROPER_NAME: "Proper name",
        PartOfSpeech.NUMBER: "Number",
        PartOfSpeech.INTERJECTION: "Interjection",
    },
)
