from collections.abc import Callable
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.domain.enums.chronicle import WritingSystem
from aerona.rules.registry import Rules

UnitRandom = Callable[[], float]

WRITING_SYSTEM_DESCRIPTIONS: dict[WritingSystem, str] = {
    WritingSystem.ALPHABET: "one sign per sound",
    WritingSystem.SYLLABARY: "one sign per syllable",
    WritingSystem.PICTOGRAPHIC: "signs born from pictures of objects",
    WritingSystem.KNOT: "records kept with knots tied in cords",
    WritingSystem.NOTCH: "notches carved into stone and bone",
}

WRITING_SYSTEM_PHRASES: dict[WritingSystem, str] = {
    WritingSystem.ALPHABET: "an alphabet",
    WritingSystem.SYLLABARY: "a syllabary",
    WritingSystem.PICTOGRAPHIC: "a pictographic script",
    WritingSystem.KNOT: "a knot script",
    WritingSystem.NOTCH: "a notch script",
}


@dataclass(frozen=True)
class ScriptChoiceInputs:
    merchant_share: float
    farmer_share: float
    priest_share: float
    complexity: float
    sacredness: float


def writing_system_weights(inputs: ScriptChoiceInputs, rules: Rules) -> dict[WritingSystem, float]:
    life = rules.deep_life
    return {
        WritingSystem.ALPHABET: life.script_alphabet_base + inputs.merchant_share / life.script_alphabet_divisor,
        WritingSystem.SYLLABARY: life.script_syllabary_base + inputs.complexity / life.script_syllabary_divisor,
        WritingSystem.PICTOGRAPHIC: life.script_pictographic_base + inputs.sacredness / life.script_pictographic_divisor,
        WritingSystem.KNOT: life.script_knot_base + inputs.farmer_share / life.script_knot_divisor,
        WritingSystem.NOTCH: life.script_notch_base + inputs.priest_share / life.script_notch_divisor,
    }


def choose_writing_system(inputs: ScriptChoiceInputs, random: UnitRandom, rules: Rules) -> WritingSystem:
    weights = writing_system_weights(inputs, rules)
    total = sum(weights.values())
    if total <= 0:
        return WritingSystem.ALPHABET
    remaining = random() * total
    for system, weight in weights.items():
        remaining -= weight
        if remaining <= 0:
            return system
    return next(iter(weights))


def complexity_after_script(complexity: int | None, rules: Rules) -> int:
    life = rules.deep_life
    base = complexity if complexity is not None else life.script_default_complexity
    return max(0, min(PERCENT, base + life.script_complexity_gain))


def script_note(writer_name: str, language_name: str, system: WritingSystem) -> str:
    return f"{writer_name}'s scribes developed {WRITING_SYSTEM_PHRASES[system]} for the {language_name} language; words are now permanent."
