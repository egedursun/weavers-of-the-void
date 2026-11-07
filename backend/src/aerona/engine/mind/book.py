from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import SKILLS, TRAITS
from aerona.constants.units import PERCENT
from aerona.db.fast_session import rows_by_prefix
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import (
    SKILL_MAX,
    SKILL_MIN,
    VALUE_MAX,
    VALUE_MIN,
    CultureValueRow,
    MindRow,
    NeedRow,
    PersonalityValueRow,
    PressureRow,
    SkillRow,
    TraitRow,
)
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import NeedKind, PressureKind, SkillKind, SkillSource, TraitEffect, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.engine.body.book import factor
from aerona.engine.body.customs import people_of
from aerona.engine.mortal.variants import strength, variants_by_id
from aerona.engine.primitives.numbers import clamp_int

Holder = EntityRow | SonRow | ForeignGodRow

ENTITY_HOLDERS: dict[EntityType, ValueHolder] = {
    EntityType.MORTAL: ValueHolder.PERSONAL,
    EntityType.PEOPLE: ValueHolder.CULTURE,
    EntityType.CULT: ValueHolder.DOCTRINE,
    EntityType.FACTION: ValueHolder.AGENDA,
    EntityType.SETTLEMENT: ValueHolder.COMMUNITY,
}
CULTURE_HOLDERS = frozenset({ValueHolder.CULTURE, ValueHolder.DOCTRINE, ValueHolder.AGENDA})
PERSONAL_HOLDERS = frozenset({ValueHolder.PERSONAL, ValueHolder.DIVINE})
PRESSURE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
NEUTRAL = 0

Values = dict[ValueAxis, int]


VALUES_KEY = "values"
TRAITS_KEY = "traits"
NEEDS_KEY = "needs"
PRESSURES_KEY = "pressures"
SKILLS_KEY = "skills"
MEMORIES_KEY = "memories"


def holder_kind(node: object) -> ValueHolder | None:
    if isinstance(node, EntityRow):
        return ENTITY_HOLDERS.get(node.entity_type)
    if isinstance(node, SonRow | ForeignGodRow):
        return ValueHolder.DIVINE
    return None


def has_mind(node: object) -> bool:
    return holder_kind(node) is not None


def clamp_value(value: float) -> int:
    return clamp_int(value, VALUE_MIN, VALUE_MAX)


def clamp_skill(value: float) -> int:
    return clamp_int(value, SKILL_MIN, SKILL_MAX)


async def mind_of(session: AsyncSession, node_id: int) -> MindRow | None:
    return await session.get(MindRow, node_id)


async def ensure_mind_row(session: AsyncSession, node: Holder, epoch: int) -> tuple[MindRow, bool]:
    kind = holder_kind(node)
    if kind is None:
        raise ValueError(f"node {node.id} holds no mind")
    row = await session.get(MindRow, node.id)
    if row is not None:
        return row, False
    row = MindRow(node_id=node.id, holder=kind, updated_epoch=epoch, locked=[])
    session.add(row)
    await session.flush()
    return row, True


def is_locked(mind: MindRow | None, key: str) -> bool:
    return mind is not None and key in (mind.locked or [])


async def locked_for(session: AsyncSession, node_id: int, key: str) -> bool:
    return is_locked(await mind_of(session, node_id), key)


async def stored_values(session: AsyncSession, holder: ValueHolder, node_id: int) -> Values:
    if holder in CULTURE_HOLDERS:
        rows = await rows_by_prefix(session, CultureValueRow, node_id)
        return {row.axis: row.value for row in rows}
    if holder in PERSONAL_HOLDERS:
        found = await rows_by_prefix(session, PersonalityValueRow, node_id)
        return {row.axis: row.value for row in found}
    return {}


async def write_values(session: AsyncSession, holder: ValueHolder, node_id: int, values: Values) -> None:
    if write_blocked(node_id, VALUES_KEY):
        return
    if holder in CULTURE_HOLDERS:
        culture = {row.axis: row for row in await rows_by_prefix(session, CultureValueRow, node_id)}
        for axis in ValueAxis:
            known = culture.pop(axis, None)
            if known is None:
                session.add(CultureValueRow(entity_id=node_id, axis=axis, value=clamp_value(values.get(axis, NEUTRAL))))
            elif known.value != clamp_value(values.get(axis, NEUTRAL)):
                known.value = clamp_value(values.get(axis, NEUTRAL))
        for stale in culture.values():
            await session.delete(stale)
    elif holder in PERSONAL_HOLDERS:
        personal = {row.axis: row for row in await rows_by_prefix(session, PersonalityValueRow, node_id)}
        for axis in ValueAxis:
            mine = personal.pop(axis, None)
            if mine is None:
                session.add(PersonalityValueRow(node_id=node_id, axis=axis, value=clamp_value(values.get(axis, NEUTRAL))))
            elif mine.value != clamp_value(values.get(axis, NEUTRAL)):
                mine.value = clamp_value(values.get(axis, NEUTRAL))
        for gone in personal.values():
            await session.delete(gone)


@dataclass
class ValueIndex:
    vectors: dict[int, Values] = field(default_factory=dict)
    borrowed: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "ValueIndex":
        index = cls()
        for culture in await session.scalars(select(CultureValueRow)):
            index.vectors.setdefault(culture.entity_id, {})[culture.axis] = culture.value
        for personal in await session.scalars(select(PersonalityValueRow)):
            index.vectors.setdefault(personal.node_id, {})[personal.axis] = personal.value
        return index

    def lend(self, node_id: int, owner_id: int) -> None:
        self.borrowed[node_id] = owner_id

    def of(self, node_id: int) -> Values:
        found = self.vectors.get(node_id)
        if found is not None:
            return found
        owner = self.borrowed.get(node_id)
        return self.vectors.get(owner, {}) if owner is not None else {}


async def values_of(session: AsyncSession, node: Holder) -> Values:
    kind = holder_kind(node)
    if kind is None:
        return {}
    if kind is ValueHolder.COMMUNITY and isinstance(node, EntityRow):
        people = await people_of(session, node)
        return await stored_values(session, ValueHolder.CULTURE, people.id) if people is not None else {}
    return await stored_values(session, kind, node.id)


async def values_for(session: AsyncSession, node_id: int) -> Values:
    node = await load_holder(session, node_id)
    return await values_of(session, node) if node is not None else {}


async def load_holder(session: AsyncSession, node_id: int) -> Holder | None:
    entity = await session.get(EntityRow, node_id)
    if entity is not None:
        return entity if has_mind(entity) else None
    son = await session.get(SonRow, node_id)
    if son is not None:
        return son
    return await session.get(ForeignGodRow, node_id)


async def traits_of(session: AsyncSession, node_id: int) -> set[TraitKind]:
    return {row.trait for row in await rows_by_prefix(session, TraitRow, node_id)}


async def add_trait(session: AsyncSession, node_id: int, trait: TraitKind, source: TraitSource, epoch: int, *, source_node_id: int | None = None) -> bool:
    if write_blocked(node_id, TRAITS_KEY) or await session.get(TraitRow, (node_id, trait)) is not None:
        return False
    opposite = TRAITS[trait].opposite
    if opposite is not None:
        existing = await session.get(TraitRow, (node_id, opposite))
        if existing is not None:
            await session.delete(existing)
    session.add(TraitRow(node_id=node_id, trait=trait, source=source, epoch=epoch, source_node_id=source_node_id))
    await session.flush()
    return True


async def remove_trait(session: AsyncSession, node_id: int, trait: TraitKind) -> bool:
    row = await session.get(TraitRow, (node_id, trait))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


def trait_effect(traits: Iterable[TraitKind], effect: TraitEffect, scale_pct: int = PERCENT) -> int:
    return round(sum(TRAITS[trait].effects.get(effect, 0) for trait in traits) * scale_pct / PERCENT)


def trait_capacity(traits: Iterable[TraitKind], capacity: Capacity, scale_pct: int = PERCENT) -> int:
    return round(sum(TRAITS[trait].capacities.get(capacity, 0) for trait in traits) * scale_pct / PERCENT)


async def effect_of(session: AsyncSession, node_id: int, effect: TraitEffect, scale_pct: int = PERCENT) -> int:
    rows = await rows_by_prefix(session, TraitRow, node_id)
    variants = await variants_by_id(session, (row.variant_id for row in rows))
    total = sum(TRAITS[row.trait].effects.get(effect, 0) * strength(variants, row.variant_id) for row in rows)
    return round(total * scale_pct / PERCENT)


def scaled_by(effect_pct: int) -> float:
    return max(0.0, (PERCENT + effect_pct) / PERCENT)


async def skills_of(session: AsyncSession, node_id: int) -> dict[SkillKind, SkillRow]:
    rows = await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == node_id, SkillRow.subject_node_id.is_(None)))
    return {row.skill: row for row in rows}


async def skill_level(session: AsyncSession, node_id: int, skill: SkillKind) -> int:
    row = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == node_id, SkillRow.skill == skill, SkillRow.subject_node_id.is_(None)).limit(1))
    return row.level if row is not None else 0


async def best_skill(session: AsyncSession, node_id: int, skills: Iterable[SkillKind]) -> int:
    wanted = tuple(skills)
    rows = await session.scalars(
        select(SkillRow.level).where(SkillRow.holder_node_id == node_id, SkillRow.skill.in_(wanted), SkillRow.subject_node_id.is_(None))
    )
    return max(rows, default=0)


async def effective_skill(session: AsyncSession, node_id: int, skill: SkillKind) -> int:
    level = await skill_level(session, node_id, skill)
    return round(level * await factor(session, node_id, SKILLS[skill].capacity))


async def best_effective(session: AsyncSession, node_id: int, skills: Iterable[SkillKind]) -> int:
    best = 0
    for skill in skills:
        best = max(best, await effective_skill(session, node_id, skill))
    return best


async def set_skill(
    session: AsyncSession, node_id: int, skill: SkillKind, level: int, *, epoch: int, source: SkillSource, subject_node_id: int | None = None
) -> SkillRow:
    statement = select(SkillRow).where(SkillRow.holder_node_id == node_id, SkillRow.skill == skill)
    statement = (
        statement.where(SkillRow.subject_node_id == subject_node_id) if subject_node_id is not None else statement.where(SkillRow.subject_node_id.is_(None))
    )
    row = await session.scalar(statement.limit(1))
    value = clamp_skill(level)
    if row is None:
        row = SkillRow(
            holder_node_id=node_id, skill=skill, subject_node_id=subject_node_id, level=value, xp=0, peak=value, last_used_epoch=epoch, source=source
        )
        session.add(row)
    else:
        row.level = value
        row.peak = max(row.peak, value)
        row.last_used_epoch = epoch
        row.source = source
    await session.flush()
    return row


async def needs_of(session: AsyncSession, node_id: int) -> dict[NeedKind, int]:
    rows = await rows_by_prefix(session, NeedRow, node_id)
    return {row.need: row.value for row in rows}


async def pressures_of(session: AsyncSession, entity_id: int) -> dict[PressureKind, int]:
    rows = await rows_by_prefix(session, PressureRow, entity_id)
    return {row.pressure: row.value for row in rows}


async def pressure(session: AsyncSession, entity_id: int, kind: PressureKind) -> int:
    row = await session.get(PressureRow, (entity_id, kind))
    return row.value if row is not None else 0


async def write_needs(session: AsyncSession, node_id: int, needs: dict[NeedKind, int]) -> None:
    if write_blocked(node_id, NEEDS_KEY):
        return
    existing = {row.need: row for row in await rows_by_prefix(session, NeedRow, node_id)}
    for need, value in needs.items():
        row = existing.get(need)
        if row is None:
            session.add(NeedRow(node_id=node_id, need=need, value=clamp_int(value, 0, PERCENT)))
        else:
            row.value = clamp_int(value, 0, PERCENT)
    await session.flush()


async def write_pressures(session: AsyncSession, entity_id: int, pressures: dict[PressureKind, int]) -> None:
    if write_blocked(entity_id, PRESSURES_KEY):
        return
    for kind, value in pressures.items():
        row = await session.get(PressureRow, (entity_id, kind))
        if row is None:
            session.add(PressureRow(entity_id=entity_id, pressure=kind, value=clamp_int(value, 0, PERCENT)))
        else:
            row.value = clamp_int(value, 0, PERCENT)
    await session.flush()


async def living_minds(session: AsyncSession) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(tuple(ENTITY_HOLDERS)))
    return list(await session.scalars(statement.order_by(EntityRow.id)))
