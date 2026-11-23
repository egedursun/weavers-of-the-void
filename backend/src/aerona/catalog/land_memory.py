from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.region import RegionMemoryKind
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class LandMemorySpec:
    label: str
    darkness: Callable[[Rules], int]
    holiness: Callable[[Rules], int]
    fade: Callable[[Rules], int]
    weight: Callable[[Rules], int] | None = None
    sources: frozenset[str] = frozenset()


LAND_MEMORIES: Mapping[RegionMemoryKind, LandMemorySpec] = total(
    RegionMemoryKind,
    {
        RegionMemoryKind.BATTLE: LandMemorySpec(
            "Battle", lambda rules: rules.terrain.battle_darkness, lambda rules: rules.terrain.battle_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.MASSACRE: LandMemorySpec(
            "Massacre", lambda rules: rules.terrain.massacre_darkness, lambda rules: rules.terrain.massacre_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.SACK: LandMemorySpec(
            "Sack", lambda rules: rules.terrain.sack_darkness, lambda rules: rules.terrain.sack_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.DISASTER: LandMemorySpec(
            "Disaster", lambda rules: rules.terrain.disaster_darkness, lambda rules: rules.terrain.disaster_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.PLAGUE: LandMemorySpec(
            "Plague", lambda rules: rules.terrain.plague_darkness, lambda rules: rules.terrain.plague_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.FAMINE: LandMemorySpec(
            "Famine", lambda rules: rules.terrain.famine_darkness, lambda rules: rules.terrain.famine_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.GOD_DEATH: LandMemorySpec(
            "God death", lambda rules: rules.terrain.god_death_darkness, lambda rules: rules.terrain.god_death_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.SAINT_BURIAL: LandMemorySpec(
            "Saint burial",
            lambda rules: rules.terrain.saint_burial_darkness,
            lambda rules: rules.terrain.saint_burial_holiness,
            lambda rules: rules.terrain.memory_fade,
        ),
        RegionMemoryKind.MIRACLE: LandMemorySpec(
            "Miracle", lambda rules: rules.terrain.miracle_darkness, lambda rules: rules.terrain.miracle_holiness, lambda rules: rules.terrain.memory_fade
        ),
        RegionMemoryKind.FOUNDING: LandMemorySpec(
            "Founding",
            lambda rules: rules.land_memory.founding_darkness,
            lambda rules: rules.land_memory.founding_holiness,
            lambda rules: rules.land_memory.founding_fade,
            lambda rules: rules.land_memory.founding_weight,
            frozenset({"births.village", "polity.founded", "nomads.settled"}),
        ),
        RegionMemoryKind.TREATY: LandMemorySpec(
            "Treaty",
            lambda rules: rules.land_memory.treaty_darkness,
            lambda rules: rules.land_memory.treaty_holiness,
            lambda rules: rules.land_memory.treaty_fade,
            lambda rules: rules.land_memory.treaty_weight,
            frozenset({"diplomacy.peace", "diplomacy.exhaustion_peace", "diplomacy.peace_decree", "diplomacy.marriage_pact", "civilization.treaty"}),
        ),
        RegionMemoryKind.EXPULSION: LandMemorySpec(
            "Expulsion",
            lambda rules: rules.land_memory.expulsion_darkness,
            lambda rules: rules.land_memory.expulsion_holiness,
            lambda rules: rules.land_memory.expulsion_fade,
            lambda rules: rules.land_memory.expulsion_weight,
            frozenset({"disease.expelled", "being.banished"}),
        ),
        RegionMemoryKind.DISCOVERY: LandMemorySpec(
            "Discovery",
            lambda rules: rules.land_memory.discovery_darkness,
            lambda rules: rules.land_memory.discovery_holiness,
            lambda rules: rules.land_memory.discovery_fade,
            lambda rules: rules.land_memory.discovery_weight,
            frozenset(
                {
                    "exploration.land_found",
                    "knowledge.discovered",
                    "disease.cure_found",
                    "extraction.deposit_found",
                    "pantheon.first_contact",
                    "cosmos.world_discovered",
                    "dominion.magic_site_found",
                    "discovery.breakthrough",
                }
            ),
        ),
        RegionMemoryKind.UPRISING: LandMemorySpec(
            "Uprising",
            lambda rules: rules.land_memory.uprising_darkness,
            lambda rules: rules.land_memory.uprising_holiness,
            lambda rules: rules.land_memory.uprising_fade,
            lambda rules: rules.land_memory.uprising_weight,
            frozenset(
                {"movements.revolt", "tribute.revolt", "manumission.revolt", "creatures.rebellion", "society.class_uprising", "society.poverty_uprising"}
            ),
        ),
        RegionMemoryKind.UNION: LandMemorySpec(
            "Union",
            lambda rules: rules.land_memory.union_darkness,
            lambda rules: rules.land_memory.union_holiness,
            lambda rules: rules.land_memory.union_fade,
            lambda rules: rules.land_memory.union_weight,
            frozenset({"institutions.people_union", "city.settlements_joined"}),
        ),
        RegionMemoryKind.ACCESSION: LandMemorySpec(
            "Accession",
            lambda rules: rules.land_memory.accession_darkness,
            lambda rules: rules.land_memory.accession_holiness,
            lambda rules: rules.land_memory.accession_fade,
            lambda rules: rules.land_memory.accession_weight,
            frozenset({"gathering.coronation"}),
        ),
    },
)
SOURCE_KINDS: Mapping[str, RegionMemoryKind] = {source: kind for kind, spec in LAND_MEMORIES.items() for source in sorted(spec.sources)}
