from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.agent import CouncilVote
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import CouncilMotion, PenanceDeed, SonPunishment, VotingRule
from aerona.prompts.schemas.base import OutputModel


class SpeechOutput(OutputModel):
    son_id: int
    words: str = Field(description="1 to 3 sentences in their own manner of speech; they may answer one another")


class VoteOutput(OutputModel):
    son_id: int
    vote: CouncilVote
    reason: str


class AllianceChange(StrEnum):
    COVENANT = "covenant"
    BREAK = "break"


class AllianceOutput(OutputModel):
    a: int
    b: int
    kind: AllianceChange
    reason: str


class CouncilOutput(OutputModel):
    speeches: list[SpeechOutput]
    motion: str = Field(description="The single concrete motion the council votes on")
    votes: list[VoteOutput]
    alliances: list[AllianceOutput]
    decision: CouncilMotion = Field(description="The typed effect on the world if the motion passes")
    target_id: int | None = Field(default=None, description="The id of the son, foreign god or mortal the decision names")
    world_id: int | None = Field(default=None, description="The id of the world the decision names")
    school: MagicSchool | None = Field(default=None, description="The school of rites an outlaw decision forbids")
    punishment: SonPunishment | None = Field(default=None, description="How a punished son is punished")
    penance_deed: PenanceDeed | None = Field(default=None, description="The deed a son bound to penance must do by the day the council sets")
    voting_rule: VotingRule | None = Field(default=None, description="How the council decides from now on, when the decision changes its rules")
    minutes: str = Field(
        description="A 3 to 5 sentence summary of the council as the mortals of this world came to know it, told in a way that suits this world; {{ attendance | several('son', 'sons') }} attended the council (write no other number)"
    )
    agenda: str = Field(
        description="One-sentence, third-person summary of the agenda for the chronicle (do not repeat the god's question verbatim in the first person: e.g. \"the fate of <the subject's name>\")"
    )


class WordGlossOutput(OutputModel):
    word: str
    meaning: str


class NewWordOutput(OutputModel):
    word: str
    meaning: str
    kind: PartOfSpeech
    origin: str


class TranslationOutput(OutputModel):
    translation: str = Field(description="The sentence's equivalent in this language")
    pronunciation: str = Field(description="Its pronunciation in Latin letters, syllable by syllable")
    word_by_word: list[WordGlossOutput]
    new_words: list[NewWordOutput]
    note: str = Field(description="A grammar or culture note, one sentence")
