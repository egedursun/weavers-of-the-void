from pydantic import Field

from aerona.prompts.schemas.base import OutputModel


class WillAnswerInLanguage(OutputModel):
    text: str = Field(description="The whole answer in the asked language, with its markdown, names, ids and numbers kept as they are")
