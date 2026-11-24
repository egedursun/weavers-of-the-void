from dataclasses import dataclass

from aerona.domain.enums.domain import Domain
from aerona.domain.enums.rarity import Rarity


@dataclass(frozen=True)
class SonDesign:
    name: str | None = None
    title: str | None = None
    rarity: Rarity | None = None
    domain_1: Domain | None = None
    domain_2: Domain | None = None
    appearance: str | None = None
    temperament: str | None = None
    obsession: str | None = None
    fear: str | None = None
    speech_style: str | None = None
    secret: str | None = None
    loyalty: int | None = None
    ambition: int | None = None
    wrath: int | None = None
    mercy: int | None = None
    inspiration: str | None = None

    def given(self) -> list[str]:
        named = {
            "name": self.name,
            "title": self.title,
            "first domain": self.domain_1.value if self.domain_1 else None,
            "second domain": self.domain_2.value if self.domain_2 else None,
            "appearance": self.appearance,
            "temperament": self.temperament,
            "obsession": self.obsession,
            "fear": self.fear,
            "way of speaking": self.speech_style,
            "secret": self.secret,
        }
        return [f"{label}: {value.strip()}" for label, value in named.items() if value and value.strip()]
