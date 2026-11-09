from aerona.core.random import SeededRandom
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.son import Stat
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR, StatBlock
from aerona.rules.registry import Rules


def inherited_stats(rules: Rules, rng: SeededRandom, rolled: StatBlock, parents: list[SonRow]) -> StatBlock:
    if not parents:
        return rolled
    spread = rules.avatars.inheritance_deviation
    values: dict[str, int] = {}
    for stat in Stat:
        sources = [parent.stat(stat) for parent in parents] if len(parents) > 1 else [parents[0].stat(stat), rolled.get(stat)]
        mean = sum(sources) / len(sources)
        values[stat.value] = max(STAT_FLOOR, min(STAT_CEILING, round(mean + rng.integer(-spread, spread))))
    return StatBlock(**values)


def inherited_domains(rng: SeededRandom, chosen: tuple[Domain, Domain], parents: list[SonRow]) -> tuple[Domain, Domain]:
    if not parents:
        return chosen
    first = rng.pick(list(parents[0].domains))
    if len(parents) > 1:
        options = [domain for domain in parents[1].domains if domain is not first]
        second = rng.pick(options) if options else chosen[1]
    else:
        second = chosen[0] if chosen[0] is not first else chosen[1]
    if second is first:
        second = next(domain for domain in (*chosen, *Domain) if domain is not first)
    return first, second
