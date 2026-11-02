from pydantic import Field

from aerona.prompts.schemas.base import OutputModel


class LocalisedLineOutput(OutputModel):
    id: int = Field(description="The line's number exactly as shown")
    text: str = Field(description="The translated line; every proper name kept exactly as written")


class LocalisedLinesOutput(OutputModel):
    lines: list[LocalisedLineOutput] = Field(description="One translation for EVERY line below")
