from pydantic import Field

from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.prompts.schemas.base import OutputModel


class PresenceAnswer(OutputModel):
    reply: str = Field(description="Your answer to the one who spoke, whole, in the asked language, with your own names and terms kept as they are")
    remember: str = Field(description="One short line in your own voice of what you keep of this exchange")
    feeling: int = Field(
        ge=RELATION_MIN,
        le=RELATION_MAX,
        description="How this exchange left you toward the one who spoke, from -100 (bitterly) through 0 (unmoved) to 100 (warmly)",
    )
