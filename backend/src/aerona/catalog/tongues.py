from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.chronicle import PartOfSpeech, WritingSystem
from aerona.domain.enums.couplings import SignCause, SociolectKind
from aerona.domain.enums.nature import SenseKind
from aerona.domain.enums.tongues import (
    LanguageModality,
    LanguagePolicy,
    LanguageStage,
    MorphologyType,
    NumberSystem,
    NumeralBase,
    ScriptChangeCause,
    SenseShift,
    SoundChangeKind,
    WordOrder,
    WordRegister,
)
from aerona.domain.enums.world import LanguageTexture

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

WRITABLE = total(
    LanguageModality,
    {
        M.VOCAL: True,
        M.SIGN: True,
        M.SCENT: False,
        M.COLOUR: True,
        M.TELEPATHIC: False,
        M.DATA: True,
        M.CHEMICAL: False,
        M.TACTILE: True,
        M.VIBRATION: False,
        M.ELECTRIC: False,
        M.WHISTLED: False,
        M.DRUMMED: False,
    },
)

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
        M.TACTILE: frozenset({BodyFunction.GRASP}),
        M.VIBRATION: frozenset({BodyFunction.PRESENCE}),
        M.ELECTRIC: frozenset({BodyFunction.PRESENCE}),
        M.WHISTLED: frozenset({BodyFunction.SPEECH}),
        M.DRUMMED: frozenset({BodyFunction.GRASP}),
    },
)

MODALITY_SENSE: Mapping[LanguageModality, SenseKind | None] = total(
    LanguageModality,
    {
        M.VOCAL: SenseKind.HEARING,
        M.SIGN: SenseKind.SIGHT,
        M.SCENT: SenseKind.SMELL,
        M.COLOUR: SenseKind.SIGHT,
        M.TELEPATHIC: None,
        M.DATA: None,
        M.CHEMICAL: SenseKind.SMELL,
        M.TACTILE: None,
        M.VIBRATION: SenseKind.VIBRATION,
        M.ELECTRIC: SenseKind.ELECTRIC,
        M.WHISTLED: SenseKind.HEARING,
        M.DRUMMED: SenseKind.HEARING,
    },
)

MODALITY_RANGE: Mapping[LanguageModality, str | None] = total(
    LanguageModality,
    {
        M.VOCAL: None,
        M.SIGN: None,
        M.SCENT: None,
        M.COLOUR: None,
        M.TELEPATHIC: None,
        M.DATA: None,
        M.CHEMICAL: None,
        M.TACTILE: None,
        M.VIBRATION: "vibration_range",
        M.ELECTRIC: "electric_range",
        M.WHISTLED: "whistle_range",
        M.DRUMMED: "drum_range",
    },
)

MODALITY_ORDER = (M.VOCAL, M.SIGN, M.COLOUR, M.SCENT, M.TACTILE, M.TELEPATHIC)
FIELD_MODALITIES = (M.ELECTRIC, M.VIBRATION)
BASE_SENSES = frozenset({SenseKind.SIGHT, SenseKind.HEARING, SenseKind.SMELL})

KIND_WEIGHTS = total(
    SoundChangeKind,
    {
        SoundChangeKind.SHIFT: 3,
        SoundChangeKind.LENITION: 3,
        SoundChangeKind.VOWEL_SHIFT: 3,
        SoundChangeKind.MERGER: 1,
        SoundChangeKind.LOSS: 2,
        SoundChangeKind.METATHESIS: 1,
        SoundChangeKind.EPENTHESIS: 2,
        SoundChangeKind.ASSIMILATION: 2,
        SoundChangeKind.PALATALISATION: 2,
        SoundChangeKind.TONOGENESIS: 1,
    },
)

TEXTURE_LEAN: Mapping[LanguageTexture, SoundChangeKind | None] = total(
    LanguageTexture,
    {
        LanguageTexture.FLOWING: SoundChangeKind.LENITION,
        LanguageTexture.HARD: SoundChangeKind.SHIFT,
        LanguageTexture.GUTTURAL: SoundChangeKind.MERGER,
        LanguageTexture.SIBILANT: SoundChangeKind.PALATALISATION,
        LanguageTexture.LONG: SoundChangeKind.EPENTHESIS,
        LanguageTexture.FREE: None,
        LanguageTexture.TONAL: SoundChangeKind.TONOGENESIS,
        LanguageTexture.CLICKING: SoundChangeKind.ASSIMILATION,
        LanguageTexture.WHISTLED: SoundChangeKind.LENITION,
        LanguageTexture.NON_VOCAL: None,
    },
)
TEXTURE_MODALITY: Mapping[LanguageTexture, LanguageModality] = {LanguageTexture.NON_VOCAL: LanguageModality.SIGN}
TEXTURE_LEAN_WEIGHT = 3

ORDERS = tuple(order for order in WordOrder if order is not WordOrder.FREE)
HEAD_FIRST: Mapping[WordOrder, bool] = total(
    WordOrder,
    {
        WordOrder.SOV: False,
        WordOrder.SVO: True,
        WordOrder.VSO: True,
        WordOrder.VOS: True,
        WordOrder.OVS: False,
        WordOrder.OSV: False,
        WordOrder.FREE: False,
    },
)

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


@dataclass(frozen=True)
class BaseSpec:
    label: str
    radix: int
    divisors: int
    fine_division: bool
    needs_writing: bool
    rule: str


BASES = total(
    NumeralBase,
    {
        NumeralBase.DECIMAL: BaseSpec("Tens", 10, 2, False, False, "decimal_reckoning_pct"),
        NumeralBase.VIGESIMAL: BaseSpec("Twenties", 20, 4, False, False, "vigesimal_reckoning_pct"),
        NumeralBase.DUODECIMAL: BaseSpec("Twelves", 12, 4, True, False, "duodecimal_reckoning_pct"),
        NumeralBase.SEXAGESIMAL: BaseSpec("Sixties", 60, 10, True, False, "sexagesimal_reckoning_pct"),
        NumeralBase.OCTAL: BaseSpec("Eights", 8, 2, False, False, "octal_reckoning_pct"),
        NumeralBase.BODY_TALLY: BaseSpec("Counting along the body", 27, 0, False, True, "body_tally_reckoning_pct"),
        NumeralBase.QUINARY: BaseSpec("Fives", 5, 2, False, False, "quinary_reckoning_pct"),
        NumeralBase.BINARY: BaseSpec("Twos", 2, 1, False, True, "binary_reckoning_pct"),
    },
)


@dataclass(frozen=True)
class StageSpec:
    label: str
    inherits_sounds: bool
    taught: bool


STAGES = total(
    LanguageStage,
    {
        LanguageStage.NATURAL: StageSpec("A natural tongue", True, False),
        LanguageStage.PIDGIN: StageSpec("A pidgin", False, False),
        LanguageStage.CREOLE: StageSpec("A creole", True, False),
        LanguageStage.DIVINE: StageSpec("A divine tongue", False, False),
        LanguageStage.CONSTRUCTED: StageSpec("A made tongue", False, True),
        LanguageStage.REVIVED: StageSpec("A revived tongue", True, True),
        LanguageStage.ENDANGERED: StageSpec("A tongue near its end", True, False),
    },
)


@dataclass(frozen=True)
class ShiftSpec:
    label: str
    rule: str | None


SHIFTS = total(
    SenseShift,
    {
        SenseShift.BROADENED: ShiftSpec("Broadened", "broadened_rate"),
        SenseShift.NARROWED: ShiftSpec("Narrowed", "narrowed_rate"),
        SenseShift.PEJORATIVE: ShiftSpec("Grew darker", "pejorative_rate"),
        SenseShift.AMELIORATIVE: ShiftSpec("Grew kinder", "ameliorative_rate"),
        SenseShift.EUPHEMISM: ShiftSpec("Said instead of a name", None),
        SenseShift.RESTORED: ShiftSpec("Restored", "restored_rate"),
        SenseShift.EXTENDED: ShiftSpec("Carried over by likeness", "extended_rate"),
        SenseShift.ASSOCIATED: ShiftSpec("Carried over by nearness", "associated_rate"),
        SenseShift.REVERSED: ShiftSpec("Turned to its opposite", "reversed_rate"),
    },
)
DRIFTS = tuple(shift for shift, spec in SHIFTS.items() if spec.rule is not None)


@dataclass(frozen=True)
class RegisterSpec:
    label: str
    drifts: bool
    insult_rule: str | None
    marks_members: bool


REGISTERS = total(
    WordRegister,
    {
        WordRegister.COMMON: RegisterSpec("Common speech", True, None, False),
        WordRegister.SACRED: RegisterSpec("Sacred speech", False, None, False),
        WordRegister.POETIC: RegisterSpec("Poetry", False, None, False),
        WordRegister.ARCHAIC: RegisterSpec("Archaic", False, None, False),
        WordRegister.TABOO: RegisterSpec("Not to be said", False, "taboo_insult", False),
        WordRegister.TECHNICAL: RegisterSpec("Words of a craft", False, None, True),
        WordRegister.HONORIFIC: RegisterSpec("Speech to superiors", False, "honorific_insult", False),
        WordRegister.SLANG: RegisterSpec("Slang", True, None, True),
        WordRegister.LEGAL: RegisterSpec("Words of the law", False, None, True),
    },
)


@dataclass(frozen=True)
class ScriptCauseSpec:
    label: str
    by_law: bool
    sacred: bool


SCRIPT_CAUSES = total(
    ScriptChangeCause,
    {
        ScriptChangeCause.INVENTION: ScriptCauseSpec("Invented", False, False),
        ScriptChangeCause.REFORM: ScriptCauseSpec("Reformed", False, False),
        ScriptChangeCause.SIMPLIFICATION: ScriptCauseSpec("Worn simpler", False, False),
        ScriptChangeCause.BORROWING: ScriptCauseSpec("Borrowed", False, False),
        ScriptChangeCause.IMPOSITION: ScriptCauseSpec("Imposed by law", True, False),
        ScriptChangeCause.REVELATION: ScriptCauseSpec("Revealed", False, True),
        ScriptChangeCause.TECHNOLOGY: ScriptCauseSpec("Changed by a new way of writing", False, False),
    },
)


@dataclass(frozen=True)
class PolicySpec:
    label: str
    teaches: bool
    shields: bool
    standardises: bool
    identity: int = 0
    driver: SalienceDriver = SalienceDriver.BASELINE


POLICIES = total(
    LanguagePolicy,
    {
        LanguagePolicy.OFFICIAL: PolicySpec("Official", True, False, False),
        LanguagePolicy.LITURGICAL: PolicySpec("Sacred", False, False, False),
        LanguagePolicy.SUPPRESSED: PolicySpec("Suppressed", False, False, False, 1, SalienceDriver.PERSECUTION),
        LanguagePolicy.REVIVAL: PolicySpec("Revived", True, False, False, 1, SalienceDriver.RHETORIC),
        LanguagePolicy.PROTECTED: PolicySpec("Protected", False, True, False, -1),
        LanguagePolicy.STANDARDISED: PolicySpec("Set by an academy", False, False, True),
        LanguagePolicy.BILINGUAL: PolicySpec("Two tongues kept side by side", True, True, False, -1),
    },
)


@dataclass(frozen=True)
class SociolectSpec:
    label: str
    layer: IdentityLayer
    prestige: int
    drift_rule: str
    carries_words: bool
    coins_technical: bool = False


SOCIOLECTS = total(
    SociolectKind,
    {
        SociolectKind.CLASS: SociolectSpec("Speech of a class", IdentityLayer.CLASS, 0, "class_drift", False),
        SociolectKind.CASTE: SociolectSpec("Speech of a caste", IdentityLayer.CLASS, 0, "caste_drift", False),
        SociolectKind.GUILD: SociolectSpec("Speech of a trade", IdentityLayer.PROFESSION, 20, "guild_drift", False, coins_technical=True),
        SociolectKind.COURT: SociolectSpec("Speech of a court", IdentityLayer.POLITY, 60, "court_drift", False),
        SociolectKind.CANT: SociolectSpec("Secret cant", IdentityLayer.CIRCLE, -50, "cant_drift", False),
        SociolectKind.SAILORS: SociolectSpec("Speech of sailors", IdentityLayer.PROFESSION, -10, "sailors_drift", False),
        SociolectKind.YOUTH: SociolectSpec("Speech of the young", IdentityLayer.GENERATION, -20, "youth_drift", False),
        SociolectKind.SOLDIERS: SociolectSpec("Speech of soldiers", IdentityLayer.PROFESSION, 0, "soldiers_drift", True),
        SociolectKind.CLERGY: SociolectSpec("Speech of the clergy", IdentityLayer.FAITH, 40, "clergy_drift", True),
        SociolectKind.SCHOLARS: SociolectSpec("Speech of scholars", IdentityLayer.PROFESSION, 30, "scholars_drift", True, coins_technical=True),
    },
)


@dataclass(frozen=True)
class SignCauseSpec:
    label: str
    sacred: bool
    spreads_on_routes: bool


SIGN_CAUSES = total(
    SignCause,
    {
        SignCause.DEAFNESS: SignCauseSpec("Born of deafness", False, False),
        SignCause.SILENCE_VOW: SignCauseSpec("Born of a vow of silence", True, False),
        SignCause.HUNTING_SILENCE: SignCauseSpec("Born of silent hunting", False, False),
        SignCause.MUTILATION: SignCauseSpec("Born of maiming", False, False),
        SignCause.TRADE: SignCauseSpec("Born of trade between tongues", False, True),
        SignCause.NOISE: SignCauseSpec("Born of the din of the works", False, False),
    },
)
