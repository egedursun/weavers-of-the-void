from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CONDITION_TRAITS, DIVINE_TRAITS, FAMILY_LIMIT, TRAIT_FAMILY, TRAITS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.mind import TraitKind, TraitSource, ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.mind.book import add_trait, locked_for, traits_of
from aerona.engine.mortal.kin import parents_of
from aerona.rules.registry import Rules

TRAIT_LOCK = "traits"
WEIGHT_FLOOR = 1.0


def affinity(trait: TraitKind, values: Mapping[ValueAxis, int], scale_pct: int) -> float:
    lift = sum(values.get(axis, 0) * weight for axis, weight in TRAITS[trait].values.items()) / PERCENT
    return max(WEIGHT_FLOOR, PERCENT + lift * scale_pct / PERCENT)


def open_choices(choices: Iterable[TraitKind], held: set[TraitKind]) -> list[TraitKind]:
    blocked = held | {TRAITS[trait].opposite for trait in held if TRAITS[trait].opposite is not None}
    filled = Counter(TRAIT_FAMILY[trait] for trait in held)
    return [trait for trait in choices if trait not in blocked and filled[TRAIT_FAMILY[trait]] < FAMILY_LIMIT[TRAIT_FAMILY[trait]]]


def pick_traits(rng: SeededRandom, choices: Sequence[TraitKind], values: Mapping[ValueAxis, int], count: int, scale_pct: int) -> list[TraitKind]:
    chosen: list[TraitKind] = []
    for _ in range(count):
        pool = open_choices(choices, set(chosen))
        if not pool:
            break
        chosen.append(rng.weighted(pool, [affinity(trait, values, scale_pct) for trait in pool]))
    return chosen


async def parent_traits(session: AsyncSession, mortal_id: int) -> list[tuple[int, TraitKind]]:
    found: list[tuple[int, TraitKind]] = []
    for parent in await parents_of(session, mortal_id):
        for trait in sorted(await traits_of(session, parent)):
            if TRAITS[trait].heritable:
                found.append((parent, trait))
    return found


async def seed_traits(
    session: AsyncSession, rules: Rules, node_id: int, values: Mapping[ValueAxis, int], *, rng: SeededRandom, epoch: int, divine: bool
) -> int:
    table = rules.traits
    if await traits_of(session, node_id):
        return 0
    added = 0
    if not divine:
        for parent, trait in await parent_traits(session, node_id):
            if (
                added < table.max_traits
                and rng.chance(table.inherit_pct)
                and await add_trait(session, node_id, trait, TraitSource.INHERITED, epoch, source_node_id=parent)
            ):
                added += 1
    count = rng.integer(table.birth_min, table.birth_max)
    choices = list(DIVINE_TRAITS) if divine else list(TRAITS)
    held = await traits_of(session, node_id)
    for trait in pick_traits(rng, open_choices(choices, held), values, max(0, count - added), table.value_affinity_pct):
        if added >= table.max_traits:
            break
        if await add_trait(session, node_id, trait, TraitSource.DIVINE if divine else TraitSource.BIRTH, epoch):
            added += 1
    return added


async def gain_trait(
    ctx: TickContext,
    node_id: int,
    choices: Sequence[TraitKind],
    chance_pct: int,
    source: TraitSource,
    *,
    values: Mapping[ValueAxis, int] | None = None,
    source_node_id: int | None = None,
    stream: str = "trait",
) -> TraitKind | None:
    table = ctx.rules.traits
    if await locked_for(ctx.session, node_id, TRAIT_LOCK):
        return None
    held = await traits_of(ctx.session, node_id)
    if len(held) >= table.max_traits:
        return None
    rng = ctx.rng(f"{stream}.{node_id}")
    if not rng.chance(chance_pct):
        return None
    pool = open_choices(choices, held)
    if not pool:
        return None
    picked = rng.weighted(pool, [affinity(trait, values or {}, table.value_affinity_pct) for trait in pool])
    if await add_trait(ctx.session, node_id, picked, source, ctx.epoch, source_node_id=source_node_id):
        ctx.count("traits_gained")
        return picked
    return None


async def condition_trait(ctx: TickContext, node_id: int, condition: ConditionKind) -> TraitKind | None:
    trait = CONDITION_TRAITS.get(condition)
    if trait is None:
        return None
    return await gain_trait(ctx, node_id, (trait,), ctx.rules.traits.condition_chance, TraitSource.CONDITION, stream="condition_trait")


async def teach_trait(ctx: TickContext, student_id: int, master_id: int) -> TraitKind | None:
    taught = sorted(await traits_of(ctx.session, master_id))
    if not taught:
        return None
    return await gain_trait(ctx, student_id, taught, ctx.rules.traits.education_pct, TraitSource.EDUCATION, source_node_id=master_id, stream="taught_trait")
