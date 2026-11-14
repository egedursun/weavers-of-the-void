from collections.abc import Callable
from dataclasses import dataclass

from aerona.core.grammar import agree, several
from aerona.domain.enums.meta import AchievementKey
from aerona.rules.registry import Rules

ORDINAL_WORDS = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth")
TEEN_LOW = 11
TEEN_HIGH = 13
HUNDRED = 100
TEN = 10
SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal_word(number: int) -> str:
    if 1 <= number <= len(ORDINAL_WORDS):
        return ORDINAL_WORDS[number - 1]
    if TEEN_LOW <= number % HUNDRED <= TEEN_HIGH:
        return f"{number}th"
    return f"{number}{SUFFIXES.get(number % TEN, 'th')}"


@dataclass(frozen=True)
class AchievementSpec:
    key: AchievementKey
    name: Callable[[Rules], str]
    description: Callable[[Rules], str]
    points: Callable[[Rules], int]


def _fixed(text: str) -> Callable[[Rules], str]:
    return lambda rules: text


ACHIEVEMENTS: dict[AchievementKey, AchievementSpec] = {
    spec.key: spec
    for spec in (
        AchievementSpec(
            AchievementKey.SECOND_SKY,
            lambda rules: f"{ordinal_word(rules.goals.ach_worlds)} sky",
            lambda rules: f"There are {several(rules.goals.ach_worlds, 'world', 'worlds')} in the cosmos.",
            lambda rules: rules.goals.ach_worlds_points,
        ),
        AchievementSpec(
            AchievementKey.CONSTELLATION,
            _fixed("Constellation"),
            lambda rules: f"A cosmos of {several(rules.goals.ach_stars, 'star', 'stars')}.",
            lambda rules: rules.goals.ach_stars_points,
        ),
        AchievementSpec(
            AchievementKey.PROPHECY_FULFILLED, _fixed("The word came true"), _fixed("A prophecy was fulfilled."), lambda rules: rules.goals.ach_prophecy_points
        ),
        AchievementSpec(
            AchievementKey.RETURN_FROM_DEATH,
            _fixed("Return from death"),
            _fixed("A dead son was resurrected."),
            lambda rules: rules.goals.ach_resurrection_points,
        ),
        AchievementSpec(
            AchievementKey.FATHERS_HAND, _fixed("The Creator's hand"), _fixed("A rebellion was suppressed."), lambda rules: rules.goals.ach_revolt_points
        ),
        AchievementSpec(
            AchievementKey.BABEL,
            _fixed("Babel"),
            lambda rules: f"{several(rules.goals.ach_languages, 'language', 'languages')} {agree(rules.goals.ach_languages, 'is', 'are')} spoken.",
            lambda rules: rules.goals.ach_languages_points,
        ),
        AchievementSpec(
            AchievementKey.CROWDED_WORLD,
            _fixed("Crowded world"),
            lambda rules: f"Total population of peoples exceeded {rules.goals.ach_population}.",
            lambda rules: rules.goals.ach_population_points,
        ),
        AchievementSpec(
            AchievementKey.FIRST_PRAYER,
            _fixed("Someone called you"),
            _fixed("A mortal prayed directly to you."),
            lambda rules: rules.goals.ach_first_prayer_points,
        ),
        AchievementSpec(
            AchievementKey.CREATORS_CULT,
            _fixed("The creator's cult"),
            lambda rules: f"{several(rules.goals.ach_cult, 'community', 'communities')} worship you directly.",
            lambda rules: rules.goals.ach_cult_points,
        ),
        AchievementSpec(
            AchievementKey.INTERSTELLAR_TRAVELLER,
            _fixed("Interstellar traveller"),
            _fixed("A journey reached another world."),
            lambda rules: rules.goals.ach_voyager_points,
        ),
        AchievementSpec(
            AchievementKey.SAGA_COMPLETED,
            _fixed("Saga completed"),
            _fixed("A legendary expedition ended successfully."),
            lambda rules: rules.goals.ach_epic_points,
        ),
        AchievementSpec(
            AchievementKey.GOD_OF_EPOCHS,
            lambda rules: f"God of {several(rules.goals.ach_epochs, 'epoch', 'epochs')}",
            lambda rules: f"The world left {several(rules.goals.ach_epochs, 'epoch', 'epochs')} behind.",
            lambda rules: rules.goals.ach_epochs_points,
        ),
        AchievementSpec(
            AchievementKey.ANCIENT,
            _fixed("Ancient"),
            lambda rules: f"The world left {several(rules.goals.ach_ancient_epochs, 'epoch', 'epochs')} behind.",
            lambda rules: rules.goals.ach_ancient_points,
        ),
        AchievementSpec(
            AchievementKey.CROWDED_PANTHEON,
            _fixed("Crowded pantheon"),
            lambda rules: f"{several(rules.goals.ach_sons, 'son', 'sons')} {agree(rules.goals.ach_sons, 'lives', 'live')} at once.",
            lambda rules: rules.goals.ach_sons_points,
        ),
        AchievementSpec(
            AchievementKey.FIRST_EXPLORERS,
            _fixed("First explorers"),
            _fixed("Mortals found a land not on the map."),
            lambda rules: rules.goals.ach_explorers_points,
        ),
        AchievementSpec(
            AchievementKey.SENSED_WORLD,
            _fixed("Sensed world"),
            _fixed("A world sensed by sky-watching mortals came to light."),
            lambda rules: rules.goals.ach_sensed_world_points,
        ),
        AchievementSpec(
            AchievementKey.WEAPONS_SILENT,
            _fixed("The weapons fell silent"),
            lambda rules: f"An epoch ended without any war (with at least {several(rules.goals.ach_peace_min_peoples, 'people', 'peoples')}).",
            lambda rules: rules.goals.ach_peace_points,
        ),
    )
}
