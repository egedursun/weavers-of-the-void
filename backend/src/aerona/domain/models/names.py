from pydantic import Field

from aerona.domain.models.base import ValueObject


class NameSimilarityPolicy(ValueObject):
    similar_max_length: int = Field(ge=0)
    family_cap: int = Field(ge=1)
    root_letters: int = Field(ge=1)
