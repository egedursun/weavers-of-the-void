from pydantic import Field

from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.son import ExistenceMode, PowerEffect, Stat
from aerona.prompts.schemas.base import OutputModel

PERCENT_MAX = 100
POWERS_PER_SON = 3
STRENGTHS_PER_SON = 2
MOTIFS_MIN = 1
MOTIFS_MAX = 5

IMAGE_PROMPT = "An English, photorealistic image-generation prompt: subject, material, light, setting, camera and lens. {{ image_prompt_rules }}"
MOTIFS = "2 to 5 motif keys for the core images of this record: short lowercase English keys (e.g. salt, bone_bell), reused whenever the same image returns, whatever the lore language."


class PowerOutput(OutputModel):
    name: str = Field(description="The power's own name, e.g. \"The Salt's Memory\"")
    description: str = Field(description="Mythic description of the power, 1 to 2 sentences")
    effect: PowerEffect = Field(description="{{ power_effects }}")
    param: str = Field(
        default="",
        description="If effect is cheap_creation: an entity type ({{ entity_type_keys }}); if duel_master: a stat (strength, wisdom, cunning, charisma, will); empty for the others",
    )


class ExistenceOutput(OutputModel):
    nature: str = Field(description="What it is made of, its essential nature (1 sentence)")
    state: ExistenceMode
    manifestation: str = Field(description="How it appears to mortals, by which sign it shows itself")
    true_name: str = Field(description="Its true name, which nobody knows; fits the naming language")


class PassionsOutput(OutputModel):
    loyalty: int = Field(ge=0, le=PERCENT_MAX)
    ambition: int = Field(ge=0, le=PERCENT_MAX)
    wrath: int = Field(ge=0, le=PERCENT_MAX)
    mercy: int = Field(ge=0, le=PERCENT_MAX)


class SonProfileOutput(OutputModel):
    name: str = Field(description="Proper name, fitting the naming language")
    title: str = Field(description='Epithet or title, e.g. "Who Makes the Salt Weep", "Warden of the Seven Oaths"')
    domain_1: Domain
    domain_2: Domain
    appearance: str = Field(description="Detailed physical appearance: body, face, material, clothing, marks (3 to 4 sentences)")
    temperament: str
    obsession: str
    fear: str
    speech_style: str = Field(description="How they speak: word choice, rhythm, tics")
    secret: str = Field(description="A secret nobody knows; a seed that will produce lore later")
    strengths: list[Stat] = Field(min_length=STRENGTHS_PER_SON, max_length=STRENGTHS_PER_SON)
    weakness: Stat
    passions: PassionsOutput
    powers: list[PowerOutput] = Field(
        min_length=POWERS_PER_SON,
        max_length=POWERS_PER_SON,
        description="Three powers fitting their personality and domains; the first is the most basic, the third the deepest. All three must have DIFFERENT effects.",
    )
    existence: ExistenceOutput
    image_prompt: str = Field(
        description="English, photorealistic, detailed full-length portrait prompt: body, face, material, clothing, lighting, background, camera and lens. {{ image_prompt_rules }}"
    )


class CreatorGodOutput(OutputModel):
    title: str
    appearance: str = Field(description="The god's appearance or manifestation, 3 to 4 sentences")
    temperament: str = Field(description="His attitude towards his sons and his creation, 2 sentences")
    image_prompt: str = Field(
        description="English, photorealistic, epic-scale god portrait prompt: scale, material, light, atmosphere, camera. {{ image_prompt_rules }}"
    )


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
    image_prompt: str = Field(description="English photoreal prompt. {{ image_prompt_rules }}")
    motifs: list[str] = Field(min_length=MOTIFS_MIN, max_length=MOTIFS_MAX, description=MOTIFS)


class WordOutput(OutputModel):
    word: str
    meaning: str
    kind: PartOfSpeech | None = None
    origin: str = Field(default="", description="Etymology: from which event or which words it derives")
