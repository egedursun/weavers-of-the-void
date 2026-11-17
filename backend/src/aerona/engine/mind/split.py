from collections.abc import Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind_split import ATTRIBUTES, CONDITION_ATTRIBUTES, FACETS, IDEAS, SKILL_ATTRIBUTES, SUMMARIES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.fast_session import rows_by_prefix
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import ATTRIBUTE_MAX, ATTRIBUTE_MIN, FACET_MAX, FACET_MIN, AttributeRow, FacetRow, IdeaRow, SkillRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import IdeaStrain
from aerona.domain.enums.made import EffectTarget
from aerona.domain.enums.mind import Attribute, Facet, IdeaState, SkillKind, TraitKind, TraitSource, ValueHolder
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR
from aerona.engine.body.customs import people_of
from aerona.engine.folkways.fed import healing_charm, underfed
from aerona.engine.mind.book import Values, add_trait, is_locked, mind_of, stored_values, traits_of
from aerona.engine.primitives.augment_bonus import lifts_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import base_stat, set_base_stats, stat
from aerona.rules.registry import Rules

ATTRIBUTE_LOCK = "attributes"
FACET_LOCK = "facets"
TRAIT_LOCK = "traits"
ATTRIBUTES_KEY = "attributes"
FACETS_KEY = "facets"
MIDPOINT = 50
FED_ATTRIBUTES = (Attribute.DISEASE_RESISTANCE, Attribute.RECUPERATION)
STRAIN_EFFECTS: dict[IdeaStrain, tuple[tuple[Attribute, int], ...]] = {
    IdeaStrain.NONE: (),
    IdeaStrain.DISTRACTION: ((Attribute.FOCUS, -1),),
    IdeaStrain.FOCUS_LOSS: ((Attribute.FOCUS, -1), (Attribute.PATIENCE, -1)),
    IdeaStrain.OBSESSION: ((Attribute.FOCUS, 1), (Attribute.WILLPOWER, -1)),
}
NEUTRAL_FACET = 0

Bodied = EntityRow | SonRow | ForeignGodRow
Attributes = dict[Attribute, int]
Facets = dict[Facet, int]

MORTAL_SUMMARIES = {name: name for name in SUMMARIES}
BEAST_SUMMARIES = {"strength": "strength", "agility": "agility", "intellect": "cunning"}
DIVINE_SUMMARIES = {
    "strength": "strength",
    "endurance": "endurance",
    "agility": "agility",
    "wisdom": "wisdom",
    "willpower": "will",
    "intellect": "cunning",
    "creativity": "creativity",
    "charisma": "charisma",
}
ATTRIBUTE_TYPES = frozenset({EntityType.MORTAL, EntityType.BEAST})


def has_attributes(node: object) -> bool:
    if isinstance(node, EntityRow):
        return node.entity_type in ATTRIBUTE_TYPES
    return isinstance(node, SonRow | ForeignGodRow)


def has_facets(node: object) -> bool:
    if isinstance(node, EntityRow):
        return node.entity_type is EntityType.MORTAL
    return isinstance(node, SonRow | ForeignGodRow)


def summary_fields(node: Bodied) -> dict[str, str]:
    if isinstance(node, SonRow | ForeignGodRow):
        return DIVINE_SUMMARIES
    return BEAST_SUMMARIES if node.entity_type is EntityType.BEAST else MORTAL_SUMMARIES


def read_summary(node: Bodied, name: str) -> int | None:
    field = summary_fields(node).get(name)
    if field is None:
        return None
    if isinstance(node, EntityRow):
        return base_stat(node, field)
    value = getattr(node, field, None)
    return value if isinstance(value, int) else None


def write_summary(node: Bodied, name: str, value: int) -> None:
    field = summary_fields(node).get(name)
    if field is None:
        return
    if isinstance(node, EntityRow):
        set_base_stats(node, **{field: clamp_int(value, ATTRIBUTE_MIN, ATTRIBUTE_MAX)})
    else:
        setattr(node, field, clamp_int(value, STAT_FLOOR, STAT_CEILING))


def clamp_attribute(value: float) -> int:
    return clamp_int(value, ATTRIBUTE_MIN, ATTRIBUTE_MAX)


def clamp_facet(value: float) -> int:
    return clamp_int(value, FACET_MIN, FACET_MAX)


async def attributes_of(session: AsyncSession, node_id: int) -> Attributes:
    rows = await rows_by_prefix(session, AttributeRow, node_id)
    return {row.attribute: row.value for row in rows}


async def stored_attribute(session: AsyncSession, node: Bodied, which: Attribute) -> int:
    stored = await attributes_of(session, node.id)
    return stored[which] if which in stored else estimate(node).get(which, MIDPOINT)


async def facets_of(session: AsyncSession, node_id: int) -> Facets:
    stored = {row.facet: row.value for row in await rows_by_prefix(session, FacetRow, node_id)}
    return {facet: stored.get(facet, NEUTRAL_FACET) for facet in Facet} if stored else {}


async def write_attributes(session: AsyncSession, node_id: int, values: Mapping[Attribute, int]) -> None:
    if write_blocked(node_id, ATTRIBUTES_KEY):
        return
    existing = {row.attribute: row for row in await rows_by_prefix(session, AttributeRow, node_id)}
    for attribute, value in values.items():
        row = existing.get(attribute)
        if row is None:
            session.add(AttributeRow(node_id=node_id, attribute=attribute, value=clamp_attribute(value)))
        else:
            row.value = clamp_attribute(value)
    await session.flush()


async def write_facets(session: AsyncSession, node_id: int, values: Mapping[Facet, int]) -> None:
    if write_blocked(node_id, FACETS_KEY):
        return
    existing = {row.facet: row for row in await rows_by_prefix(session, FacetRow, node_id)}
    for facet, value in values.items():
        row = existing.get(facet)
        if row is None:
            session.add(FacetRow(node_id=node_id, facet=facet, value=clamp_facet(value)))
        else:
            row.value = clamp_facet(value)
    await session.flush()


def estimate(node: Bodied) -> Attributes:
    found: Attributes = {}
    for attribute, spec in ATTRIBUTES.items():
        seeds = [value for name in spec.seeds if (value := read_summary(node, name)) is not None]
        found[attribute] = clamp_attribute(sum(seeds) / len(seeds)) if seeds else MIDPOINT
    return found


def seed_attributes(rules: Rules, node: Bodied, rng: SeededRandom) -> Attributes:
    jitter = rules.mind_split.seed_jitter
    return {attribute: clamp_attribute(value + rng.integer(-jitter, jitter)) for attribute, value in estimate(node).items()}


def derived_summaries(node: Bodied, attributes: Mapping[Attribute, int]) -> dict[str, int]:
    fields = summary_fields(node)
    return {
        name: round(sum(attributes.get(attribute, MIDPOINT) for attribute in members) / len(members)) for name, members in SUMMARIES.items() if name in fields
    }


def sync_summaries(node: Bodied, attributes: Attributes) -> bool:
    shifted = False
    for name, members in SUMMARIES.items():
        current = read_summary(node, name)
        if current is None:
            continue
        derived = round(sum(attributes.get(attribute, MIDPOINT) for attribute in members) / len(members))
        if current == derived:
            continue
        for attribute in members:
            attributes[attribute] = clamp_attribute(attributes.get(attribute, MIDPOINT) + current - derived)
        shifted = True
    for name, value in derived_summaries(node, attributes).items():
        if read_summary(node, name) != value:
            write_summary(node, name, value)
    return shifted


async def store_attributes(session: AsyncSession, node: Bodied, attributes: Attributes) -> None:
    await write_attributes(session, node.id, attributes)
    for name, value in derived_summaries(node, attributes).items():
        if read_summary(node, name) != value:
            write_summary(node, name, value)


async def belief_source(session: AsyncSession, node: Bodied) -> Values:
    if isinstance(node, SonRow | ForeignGodRow):
        return await stored_values(session, ValueHolder.DIVINE, node.id)
    people = await people_of(session, node)
    return await stored_values(session, ValueHolder.CULTURE, people.id) if people is not None else {}


def facet_mean(rules: Rules, beliefs: Values) -> Facets:
    scale = rules.mind_split.culture_facet_pct / PERCENT
    return {
        facet: clamp_facet(sum(beliefs.get(axis, 0) * weight for axis, weight in spec.leanings.items()) / PERCENT * scale) for facet, spec in FACETS.items()
    }


async def culture_mean(session: AsyncSession, rules: Rules, node: Bodied) -> Facets:
    return facet_mean(rules, await belief_source(session, node))


def seed_facets(rules: Rules, mean: Facets, traits: set[TraitKind], rng: SeededRandom) -> Facets:
    table = rules.mind_split
    seeded: Facets = {}
    for facet, spec in FACETS.items():
        value = mean.get(facet, NEUTRAL_FACET) + rng.integer(-table.facet_jitter, table.facet_jitter)
        if spec.high is not None and spec.high in traits:
            value += table.trait_facet
        if spec.low is not None and spec.low in traits:
            value -= table.trait_facet
        seeded[facet] = clamp_facet(value)
    return seeded


async def seed_split(session: AsyncSession, rules: Rules, node: Bodied, rng: SeededRandom) -> int:
    seeded = 0
    if has_attributes(node) and not await attributes_of(session, node.id):
        await store_attributes(session, node, seed_attributes(rules, node, rng))
        seeded += 1
    if has_facets(node) and not await facets_of(session, node.id):
        mean = await culture_mean(session, rules, node)
        await write_facets(session, node.id, seed_facets(rules, mean, await traits_of(session, node.id), rng))
        seeded += 1
    return seeded


async def incubating(session: AsyncSession, node_id: int) -> list[IdeaRow]:
    rows = await session.scalars(select(IdeaRow).where(IdeaRow.holder_node_id == node_id, IdeaRow.state == IdeaState.INCUBATING).order_by(IdeaRow.id))
    return list(rows)


async def effective_attributes(session: AsyncSession, rules: Rules, node: Bodied) -> Attributes:
    found = dict(await attributes_of(session, node.id) or estimate(node))
    for row in await incubating(session, node.id):
        cost = IDEAS[row.idea].distraction * rules.ideas.distraction_pct / PERCENT
        for member, sign in STRAIN_EFFECTS[row.strain]:
            found[member] = clamp_attribute(found.get(member, MIDPOINT) + sign * cost)
    mending = await healing_charm(session, rules, node.id)
    if mending:
        found[Attribute.RECUPERATION] = clamp_attribute(found.get(Attribute.RECUPERATION, MIDPOINT) + mending)
    hunger = await underfed(session, rules, node.id)
    if hunger:
        for member in FED_ATTRIBUTES:
            found[member] = clamp_attribute(found.get(member, MIDPOINT) - hunger * rules.nutrition.immunity_pct / PERCENT)
    for key, lift in (await lifts_of(session, node.id, EffectTarget.ATTRIBUTE)).items():
        if key in Attribute:
            member = Attribute(key)
            found[member] = clamp_attribute(found.get(member, MIDPOINT) + lift)
    return found


async def attribute(session: AsyncSession, rules: Rules, node: Bodied | None, which: Attribute) -> int:
    if node is None or not has_attributes(node):
        return MIDPOINT
    return (await effective_attributes(session, rules, node)).get(which, MIDPOINT)


def governing(attributes: Mapping[Attribute, int], skill: SkillKind) -> float:
    members = SKILL_ATTRIBUTES[skill]
    return sum(attributes.get(member, MIDPOINT) for member in members) / len(members)


def talent(rules: Rules, attributes: Mapping[Attribute, int], skill: SkillKind) -> float:
    return max(0.0, 1 + (governing(attributes, skill) - MIDPOINT) / PERCENT * rules.mind_split.talent_pct / PERCENT)


def lean_factor(value: int, scale_pct: int) -> float:
    return (value - MIDPOINT) / PERCENT * scale_pct / PERCENT


def facet_weight(facets: Mapping[Facet, int], weights: Mapping[Facet, int]) -> float:
    return sum(facets.get(facet, NEUTRAL_FACET) * sign for facet, sign in weights.items()) / FACET_MAX / max(1, len(weights))


async def facets_for(session: AsyncSession, node_id: int | None) -> Facets:
    return await facets_of(session, node_id) if node_id is not None else {}


def used_skills(rows: Iterable[SkillRow], epoch: int) -> set[Attribute]:
    return {member for row in rows if row.last_used_epoch == epoch for member in SKILL_ATTRIBUTES[row.skill]}


async def weather_attributes(session: AsyncSession, rules: Rules, node: Bodied, epoch: int) -> bool:
    if not has_attributes(node) or write_blocked(node.id, ATTRIBUTES_KEY) or is_locked(await mind_of(session, node.id), ATTRIBUTE_LOCK):
        return False
    stored = await attributes_of(session, node.id)
    if not stored:
        return False
    table = rules.mind_split
    current = dict(stored)
    changed = sync_summaries(node, current)
    if isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL:
        skills = await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == node.id))
        for member in used_skills(skills, epoch):
            if current[member] < table.use_ceiling:
                current[member] = min(table.use_ceiling, current[member] + table.use_gain)
        age = stat(node, "age") or 0
        lifespan = stat(node, "lifespan") or 0
        for member, spec in ATTRIBUTES.items():
            start = table.physical_decline_pct if spec.physical else table.mental_decline_pct
            if lifespan and age > lifespan * start / PERCENT:
                current[member] = clamp_attribute(current[member] - table.age_decline)
    if isinstance(node, EntityRow):
        conditions = await session.scalars(select(ConditionRow.kind).where(ConditionRow.bearer_node_id == node.id, ConditionRow.ended_epoch.is_(None)))
        for kind in sorted(set(conditions)):
            for member in CONDITION_ATTRIBUTES[kind]:
                if current[member] > table.condition_floor:
                    current[member] = max(table.condition_floor, current[member] - table.condition_loss)
    if current == stored and not changed:
        return False
    await store_attributes(session, node, current)
    return True


async def temper_facets(session: AsyncSession, rules: Rules, node: Bodied, epoch: int) -> list[TraitKind]:
    if not has_facets(node):
        return []
    mind = await mind_of(session, node.id)
    facets = await facets_of(session, node.id)
    if not facets:
        return []
    table = rules.mind_split
    traits = await traits_of(session, node.id)
    if not is_locked(mind, FACET_LOCK) and not write_blocked(node.id, FACETS_KEY):
        pulled = dict(facets)
        for facet, spec in FACETS.items():
            if spec.high is not None and spec.high in traits and pulled[facet] < table.trait_threshold:
                pulled[facet] = min(table.trait_threshold, pulled[facet] + table.trait_pull)
            if spec.low is not None and spec.low in traits and pulled[facet] > -table.trait_threshold:
                pulled[facet] = max(-table.trait_threshold, pulled[facet] - table.trait_pull)
        if pulled != facets:
            await write_facets(session, node.id, pulled)
            facets = pulled
    if is_locked(mind, TRAIT_LOCK):
        return []
    gained: list[TraitKind] = []
    for facet, spec in FACETS.items():
        value = facets.get(facet, NEUTRAL_FACET)
        wanted = spec.high if value >= table.trait_threshold else spec.low if value <= -table.trait_threshold else None
        if wanted is None or wanted in traits or len(traits) >= rules.traits.max_traits:
            continue
        if await add_trait(session, node.id, wanted, TraitSource.FACET, epoch):
            traits.add(wanted)
            gained.append(wanted)
    return gained
