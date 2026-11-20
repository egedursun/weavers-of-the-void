from pydantic import Field

from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.son import ExistenceMode, PowerEffect, Stat
from aerona.prompts.schemas.base import OutputModel

PERCENT_MAX = 100
POWERS_PER_SON = 3
STRENGTHS_PER_SON = 2
MOTIFS_MIN = 1
MOTIFS_MAX = 5

IMAGE_PROMPT = "An English image-generation prompt of the subject as its account gives it. {{ image_prompt_rules }}"
MOTIFS = "2 to 5 motif keys for the core images of this record: short lowercase English keys, each naming one concrete image taken from this record itself (an object, material, creature, colour, sound or phenomenon; one word, or two joined by an underscore), reused whenever the same image returns, whatever the lore language."


class PowerOutput(OutputModel):
    name: str = Field(description="The power's own name, drawn from what it does")
    description: str = Field(description="What the power is and does, 1 to 2 sentences")
    effect: PowerEffect = Field(description="{{ power_effects }}")
    param: str = Field(
        default="",
        description="If effect is cheap_creation: an entity type ({{ entity_type_keys }}); if duel_master: a stat (strength, wisdom, cunning, charisma, will); empty for the others",
    )


class ExistenceOutput(OutputModel):
    nature: str = Field(description="What it is made of, its essential nature (1 sentence)")
    state: ExistenceMode
    manifestation: str = Field(description="How it appears to mortals, by which sign it shows itself")


class PassionsOutput(OutputModel):
    loyalty: int = Field(ge=0, le=PERCENT_MAX)
    ambition: int = Field(ge=0, le=PERCENT_MAX)
    wrath: int = Field(ge=0, le=PERCENT_MAX)
    mercy: int = Field(ge=0, le=PERCENT_MAX)


class ScaleOutput(OutputModel):
    scale: DivineScale
    value: int = Field(ge=-3, le=3, description="Where this god pulls the land it rules on this scale, from -3 to 3; 0 leaves it untouched")


class DesignOutput(OutputModel):
    dominion_strength: int = Field(
        default=30, ge=0, le=PERCENT_MAX, description="How strongly this god's presence spreads over the land it is worshipped in, 0 to 100"
    )
    magic_aptitude: int = Field(default=30, ge=0, le=PERCENT_MAX, description="How gifted this god is in magic, 0 to 100")
    manifestation_strength: int = Field(default=30, ge=0, le=PERCENT_MAX, description="How mighty this god's body is when it walks the world, 0 to 100")
    scales: list[ScaleOutput] = Field(
        default_factory=list,
        max_length=6,
        description="The scales this god pulls in the land it rules, each at most once; the favoured end of a scale costs design budget and the other end gives some back. {{ design_budget }}",
    )


class SonProfileOutput(OutputModel):
    name: str = Field(description="Proper name, fitting the naming language")
    title: str = Field(
        description="Epithet or title drawn from this god's own domains, deeds or nature; vary its grammatical shape from god to god (a noun phrase, a deed, a place, a bond) and never reuse the shape of a sibling's title"
    )
    domain_1: Domain
    domain_2: Domain
    appearance: str = Field(description="Detailed appearance of this god, 3 to 4 sentences")
    temperament: str
    obsession: str
    fear: str = Field(description="What this god fears, if anything")
    speech_style: str = Field(description="How they speak")
    secret: str = Field(description="What this god keeps to itself, if anything, from its own nature and history")
    strengths: list[Stat] = Field(min_length=STRENGTHS_PER_SON, max_length=STRENGTHS_PER_SON)
    weakness: Stat
    passions: PassionsOutput
    powers: list[PowerOutput] = Field(
        min_length=POWERS_PER_SON,
        max_length=POWERS_PER_SON,
        description="Three powers fitting their personality and domains; the first is the most basic, the third the deepest. All three must have DIFFERENT effects.",
    )
    existence: ExistenceOutput
    design: DesignOutput = Field(default_factory=DesignOutput, description="How this god spends its design budget across its dominion, magic, body and scales")
    image_prompt: str = Field(description="English, detailed full-length portrait prompt of this god as its appearance gives it. {{ image_prompt_rules }}")


class CreatorGodOutput(OutputModel):
    title: str
    appearance: str = Field(description="The god's appearance or manifestation, 3 to 4 sentences")
    temperament: str = Field(description="The god's attitude towards their children and their creation, 2 sentences")
    image_prompt: str = Field(description="English, epic-scale portrait prompt of this god as its appearance gives it. {{ image_prompt_rules }}")


class NamingRuleOutput(OutputModel):
    vowels: str = Field(description="Every vowel letter this naming language uses, written together, e.g. aeio")
    consonants: str = Field(description="Every consonant letter this naming language uses, written together, e.g. klmnrstv")
    forbidden_sounds: list[str] = Field(default_factory=list, description="Sounds or letter clusters that never appear")
    syllable_patterns: list[str] = Field(description="Syllable shapes with C for consonant and V for vowel, e.g. CV, CVC")
    endings: list[str] = Field(default_factory=list, description="Favoured word endings or suffixes")
    sample_names: list[str] = Field(min_length=1, description="Six example names built with these sounds")


class NamingItemOutput(OutputModel):
    id: int
    name: str
    subtype: str
    description: str = Field(
        description="3 to 5 sentences, tell what happened in the world's lore language; describe the record ITSELF. Do NOT write record numbers, stat names or values (morale 78, 565 soldiers, military strength 34); express magnitude in words"
    )
    image_prompt: str = Field(description="English image prompt. {{ image_prompt_rules }}")
    motifs: list[str] = Field(min_length=MOTIFS_MIN, max_length=MOTIFS_MAX, description=MOTIFS)


class WordOutput(OutputModel):
    word: str
    meaning: str
    kind: PartOfSpeech | None = None
    origin: str = Field(default="", description="Etymology: from which event or which words it derives")
