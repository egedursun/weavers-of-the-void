from collections.abc import Sequence
from dataclasses import dataclass

from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SpokenNearby:
    language_id: int
    same_cell: bool


def local_language(
    spoken: int | None,
    maker_language: int | None,
    location_chain_languages: Sequence[int | None],
    rules: Rules,
) -> int | None:
    if spoken is not None:
        return spoken
    if maker_language is not None:
        return maker_language
    for language in location_chain_languages[: rules.language.local_language_depth]:
        if language is not None:
            return language
    return None


def nearest_language(
    location_language: int | None,
    ancestor_languages: Sequence[int | None],
    world_speakers: Sequence[SpokenNearby],
    rules: Rules,
) -> int | None:
    if location_language is not None:
        return location_language
    for language in ancestor_languages:
        if language is not None:
            return language
    weights: dict[int, int] = {}
    region_weight = rules.deep_life.nearest_language_region_weight
    for speaker in world_speakers:
        weights[speaker.language_id] = weights.get(speaker.language_id, 0) + (region_weight if speaker.same_cell else 1)
    if not weights:
        return None
    return min(weights, key=lambda language: (-weights[language], language))
