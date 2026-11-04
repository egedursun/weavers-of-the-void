from dataclasses import dataclass

from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.society import KnowledgeBranch


@dataclass(frozen=True)
class DisasterSpec:
    disaster: Disaster
    label: str
    effect: str
    mitigating_branches: frozenset[KnowledgeBranch]
    death_phrase: str


@dataclass(frozen=True)
class MiracleSpec:
    miracle: Miracle
    label: str
    effect: str


DISASTERS: dict[Disaster, DisasterSpec] = {
    spec.disaster: spec
    for spec in (
        DisasterSpec(
            Disaster.EARTHQUAKE,
            "Earthquake",
            "Kills part of the population and cracks structures; weak structures collapse.",
            frozenset({KnowledgeBranch.ARCHITECTURE, KnowledgeBranch.ASTRONOMY}),
            "was buried under the rubble",
        ),
        DisasterSpec(
            Disaster.FLOOD,
            "Flood",
            "Drowns prosperity and people, then leaves fertile silt behind.",
            frozenset({KnowledgeBranch.ASTRONOMY}),
            "drowned in the flood",
        ),
        DisasterSpec(
            Disaster.PLAGUE,
            "Plague",
            "Kills population and followers alike.",
            frozenset({KnowledgeBranch.MEDICINE, KnowledgeBranch.ASTRONOMY}),
            "died of the plague",
        ),
        DisasterSpec(
            Disaster.DROUGHT,
            "Drought",
            "Dries the land and thins the population.",
            frozenset({KnowledgeBranch.AGRICULTURE, KnowledgeBranch.ASTRONOMY}),
            "starved in the drought",
        ),
        DisasterSpec(
            Disaster.STORM,
            "Storm",
            "Breaks defences and scatters prosperity.",
            frozenset({KnowledgeBranch.ASTRONOMY}),
            "perished in the storm",
        ),
        DisasterSpec(
            Disaster.ERUPTION,
            "Eruption",
            "Buries towns under fire and ash; the ash later weathers into rich volcanic soil.",
            frozenset({KnowledgeBranch.ASTRONOMY}),
            "was buried under the burning ash",
        ),
        DisasterSpec(
            Disaster.VOLCANIC_QUAKE,
            "Volcanic earthquake",
            "A stronger earthquake of a volcanic land; it can wake the mountain into eruption.",
            frozenset({KnowledgeBranch.ARCHITECTURE, KnowledgeBranch.ASTRONOMY}),
            "was crushed when the burning mountain shook",
        ),
    )
}

MIRACLES: dict[Miracle, MiracleSpec] = {
    spec.miracle: spec
    for spec in (
        MiracleSpec(Miracle.HEALING, "Healing", "Grows population and followers, lifts curses and heals mortals."),
        MiracleSpec(Miracle.BOUNTY, "Bounty", "Raises fertility, prosperity or a resource's abundance."),
        MiracleSpec(Miracle.PEACE, "Peace", "Ends every hostility and ongoing war of the target."),
        MiracleSpec(Miracle.PROTECTION, "Protection", "Raises defence and shields against the next disaster."),
    )
}
