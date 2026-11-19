from aerona.domain.enums.domain import Domain
from aerona.domain.enums.happening import LandAct

LAND_DOMAINS: dict[LandAct, frozenset[Domain]] = {
    LandAct.SHIFT_RIVER: frozenset({Domain.SEA, Domain.STORM, Domain.EARTH, Domain.STONE}),
    LandAct.PARCH: frozenset({Domain.SUN, Domain.FIRE, Domain.HUNGER, Domain.SALT, Domain.ASH}),
    LandAct.GREEN: frozenset({Domain.PLANTS, Domain.HARVEST, Domain.LIFE, Domain.SEA}),
    LandAct.MAKE_SALINE: frozenset({Domain.SALT, Domain.SEA, Domain.DEATH}),
    LandAct.ENRICH_SOIL: frozenset({Domain.EARTH, Domain.FIRE, Domain.ASH, Domain.HARVEST, Domain.PLANTS, Domain.STONE}),
    LandAct.RAISE_LAND: frozenset({Domain.EARTH, Domain.STONE}),
    LandAct.LOWER_LAND: frozenset({Domain.EARTH, Domain.STONE, Domain.SEA}),
    LandAct.CARVE_VALLEY: frozenset({Domain.EARTH, Domain.STONE, Domain.STORM, Domain.SEA}),
    LandAct.FILL_VALLEY: frozenset({Domain.EARTH, Domain.STONE, Domain.ASH}),
    LandAct.OPEN_SPRING: frozenset({Domain.SEA, Domain.LIFE, Domain.EARTH, Domain.PLANTS}),
    LandAct.CALL_LAVA: frozenset({Domain.FIRE, Domain.EARTH, Domain.ASH, Domain.STONE}),
    LandAct.SINK_COAST: frozenset({Domain.SEA, Domain.STORM, Domain.EARTH}),
}
TAINTING = frozenset({Domain.DEATH, Domain.PLAGUE, Domain.MADNESS, Domain.SHADOW, Domain.BLOOD, Domain.HUNGER})


def domain_words(domains: frozenset[Domain]) -> str:
    return ", ".join(domain.value for domain in Domain if domain in domains)


LAND_DOMAIN_WORDS = "; ".join(f"{act.value}: {domain_words(domains)}" for act, domains in LAND_DOMAINS.items())
TAINTING_WORDS = domain_words(TAINTING)
