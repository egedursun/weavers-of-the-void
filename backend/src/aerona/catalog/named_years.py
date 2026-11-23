from collections.abc import Callable
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import NotableYearKind
from aerona.rules.registry import Rules

K = NotableYearKind


@dataclass(frozen=True)
class NamedYearSpec:
    label: str
    word: str
    sources: str
    remembered: Callable[[Rules], int]


NAMED_YEARS = total(
    NotableYearKind,
    {
        K.HUNGER: NamedYearSpec("Hunger", "Hunger", "famines and failed harvests", lambda rules: rules.named_years.remembered_magnitude_hunger),
        K.PLENTY: NamedYearSpec("Plenty", "Plenty", "harvests above the plenty threshold", lambda rules: rules.named_years.remembered_magnitude_plenty),
        K.WEATHER: NamedYearSpec(
            "Weather",
            "",
            "extreme weather and failed wet seasons",
            lambda rules: rules.named_years.remembered_magnitude_weather,
        ),
        K.PESTILENCE: NamedYearSpec("Pestilence", "Pestilence", "plagues", lambda rules: rules.named_years.remembered_magnitude_pestilence),
        K.DISASTER: NamedYearSpec(
            "Disaster",
            "Ruin",
            "quakes, floods, storms, fires, eruptions and impact winters",
            lambda rules: rules.named_years.remembered_magnitude_disaster,
        ),
        K.DISCOVERY: NamedYearSpec(
            "Discovery",
            "Finding",
            "discoveries and new ages of knowledge",
            lambda rules: rules.named_years.remembered_magnitude_discovery,
        ),
        K.CONTACT: NamedYearSpec("Contact", "Meeting", "first meetings of peoples", lambda rules: rules.named_years.remembered_magnitude_contact),
        K.OMEN: NamedYearSpec("Omen", "the Sign", "signs in the sky and stellar winters", lambda rules: rules.named_years.remembered_magnitude_omen),
        K.PEACE: NamedYearSpec("Peace", "Peace", "treaties that ended long wars", lambda rules: rules.named_years.remembered_magnitude_peace),
        K.FOUNDING: NamedYearSpec(
            "Founding",
            "Founding",
            "foundings of polities, cities and faiths",
            lambda rules: rules.named_years.remembered_magnitude_founding,
        ),
    },
)


def year_name(kind: NotableYearKind, place: str, weather: str = "") -> str:
    word = weather or NAMED_YEARS[kind].word or NAMED_YEARS[kind].label
    return f"the Year of {word} in {place}"
