from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.agent import CouncilVote
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.prompts.schemas.base import OutputModel


class SpeechOutput(OutputModel):
    son_id: int
    words: str = Field(description="1 to 3 sentences in his own manner of speech; they may answer one another")


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


class CouncilDecision(StrEnum):
    NONE = "none"
    AGAINST_DOOMSDAY = "against_doomsday"
    JOINT_BLESSING = "joint_blessing"
    CONDEMN_REBEL = "condemn_rebel"
    CALL_FOR_PEACE = "call_for_peace"


class CouncilOutput(OutputModel):
    speeches: list[SpeechOutput]
    motion: str = Field(description="The single concrete motion the council votes on")
    votes: list[VoteOutput]
    alliances: list[AllianceOutput]
    decision: CouncilDecision = Field(description="The effect on the world if the motion passes")
    minutes: str = Field(
        description="A 3 to 5 sentence epic summary of the council, as a mortal seer saw it in a dream; {{ attendance }} sons attended the council (write no other number)"
    )
    agenda: str = Field(
        description="One-sentence, third-person summary of the agenda for the chronicle (do not repeat the god's question verbatim in the first person: e.g. \"the fate of <the subject's name>\")"
    )


class ChatAttitude(StrEnum):
    LOYAL = "loyal"
    DISTANT = "distant"
    REBELLIOUS = "rebellious"
    AFRAID = "afraid"
    GRATEFUL = "grateful"
    MOCKING = "mocking"


class SonChatOutput(OutputModel):
    reply: str = Field(description="1 to 4 sentences, fully in character, in his own manner of speech")
    attitude: ChatAttitude
    loyalty_change: int = Field(description="How the father's words affected his loyalty")


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
