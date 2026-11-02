import re

from aerona.domain.enums.entity import LegendCategory
from aerona.domain.enums.travel import JourneyEventKind
from aerona.migration.legacy.vocabulary import Vocabulary


class LegacyPatterns:
    def __init__(self, vocabulary: Vocabulary) -> None:
        patterns = vocabulary.patterns
        self._water = re.compile(patterns.water, re.IGNORECASE)
        self._dry = re.compile(patterns.dry, re.IGNORECASE)
        self._underworld = re.compile(patterns.underworld, re.IGNORECASE)
        self._temple = re.compile(patterns.temple, re.IGNORECASE)
        self._legends = [(LegendCategory(name), re.compile(pattern, re.IGNORECASE)) for name, pattern in patterns.legend_categories]
        self._journeys = [(JourneyEventKind(name), re.compile(pattern, re.IGNORECASE)) for name, pattern in patterns.journey_events]

    def is_water(self, text: str) -> bool:
        return bool(self._water.search(text)) and not self._dry.search(text)

    def is_underworld(self, text: str) -> bool:
        return bool(self._underworld.search(text))

    def is_temple(self, text: str) -> bool:
        return bool(self._temple.search(text))

    def legend_category(self, text: str) -> LegendCategory | None:
        return next((category for category, pattern in self._legends if pattern.search(text)), None)

    def journey_event(self, text: str) -> JourneyEventKind:
        return next((kind for kind, pattern in self._journeys if pattern.search(text)), JourneyEventKind.OTHER)
