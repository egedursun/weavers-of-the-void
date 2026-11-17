from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import MortalCasteRow, PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ReproductiveCaste
from aerona.domain.enums.demography import Sex
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import found
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

SEXES = tuple(sex.value for sex in Sex)


@dataclass
class AttractionTally:
    assigned: int = 0


def pattern_weights(rules: Rules) -> list[tuple[str, int]]:
    table = rules.attraction
    return [("other", table.other_pct), ("same", table.same_pct), ("any", table.any_pct), ("none", table.none_pct)]


def drawn_set(pattern: str, own: str) -> list[str]:
    if pattern == "none":
        return []
    if pattern == "any":
        return list(SEXES)
    if pattern == "same":
        return [own]
    return [sex for sex in SEXES if sex != own]


def drawn(profile: MortalProfileRow | None, sex: str) -> bool:
    return profile is not None and profile.attraction > 0 and sex in (profile.drawn_to or [])


def pull(profile: MortalProfileRow | None, sex: str) -> float:
    return profile.attraction / PERCENT if profile is not None and drawn(profile, sex) else 0.0


async def assign(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    table = ctx.rules.attraction
    rng = ctx.rng(f"attraction.{mortal.id}")
    weights = [(pattern, weight) for pattern, weight in pattern_weights(ctx.rules) if weight > 0] or [("other", 1)]
    roll = rng.below(sum(weight for _, weight in weights))
    chosen = weights[-1][0]
    for pattern, weight in weights:
        roll -= weight
        if roll < 0:
            chosen = pattern
            break
    own = mortal.stats.sex if isinstance(mortal.stats, MortalStats) and mortal.stats.sex is not None else sex_of(mortal)
    strength = rng.integer(min(table.strength_min, table.strength_max), max(table.strength_min, table.strength_max))
    caste = await ctx.session.get(MortalCasteRow, mortal.id)
    people = await people_of(ctx.session, mortal)
    system = await ctx.session.get(PeopleReproductionRow, people.id) if people is not None else None
    if caste is not None and caste.caste is not ReproductiveCaste.BREEDER and system is not None:
        strength = round_half_up(strength * (PERCENT - table.caste_cut_pct) / PERCENT)
    if "drawn_to" not in profile.locked:
        profile.drawn_to = drawn_set(chosen, own)
    if "attraction" not in profile.locked:
        profile.attraction = clamp_int(strength, 0, PERCENT)


async def assign_attraction(ctx: TickContext) -> AttractionTally:
    tally = AttractionTally()
    for profile in list(await ctx.session.scalars(select(MortalProfileRow).where(MortalProfileRow.drawn_to.is_(None)).order_by(MortalProfileRow.entity_id))):
        mortal = await ctx.session.get(EntityRow, profile.entity_id)
        if mortal is None or held(mortal.id):
            continue
        await assign(ctx, mortal, profile)
        tally.assigned += 1
    return tally


async def set_attraction(ctx: TickContext, mortal_id: int, drawn_to: list[Sex] | None, strength: int | None, *, hold: bool) -> MortalProfileRow:
    profile = await found(ctx, MortalProfileRow, mortal_id, "mortal")
    values: dict[str, object] = {}
    if drawn_to is not None:
        values["drawn_to"] = [sex.value for sex in dict.fromkeys(drawn_to)]
    if strength is not None:
        values["attraction"] = clamp_int(strength, 0, PERCENT)
    apply(profile, values, [] if hold else list(values))
    await ctx.session.flush()
    return profile
