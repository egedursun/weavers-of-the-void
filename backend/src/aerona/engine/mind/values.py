from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import AGENDA_VALUES, DOCTRINE_BASE, DOMAIN_VALUES, PASSION_VALUES, PEOPLE_STAT_VALUES, TRAITS, VALUE_LABELS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.mind import MemoryKind, TraitEffect, TraitKind, ValueAxis, ValueHolder
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.enums.son import Passion
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import TOTAL_LOSS_KINDS
from aerona.engine.context import TickContext
from aerona.engine.mind.book import (
    Holder,
    ValueIndex,
    Values,
    clamp_value,
    holder_kind,
    is_locked,
    mind_of,
    scaled_by,
    stored_values,
    trait_effect,
    traits_of,
    values_for,
    write_values,
)
from aerona.engine.mind.drift_causes import (
    Causes,
    add_shift,
    cohesion_of,
    empty,
    famine_shift,
    ideology_shift,
    impositions_of,
    lost_war_sign,
    pull_shift,
    record_causes,
    spend_impositions,
)
from aerona.engine.mind.space import blend
from aerona.engine.mortal.kin import parents_of
from aerona.engine.notes import note
from aerona.engine.primitives.faith import foreign_patron, living_patron
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

VALUE_LOCK = "values"
STAT_MIDPOINT = 50
SECONDARY_DOMAIN_PCT = 50
PASSION_MIDPOINT = 50


def add_into(target: dict[ValueAxis, float], source: Mapping[ValueAxis, int], scale: float) -> None:
    for axis, weight in source.items():
        target[axis] += weight * scale


def finished(raw: Mapping[ValueAxis, float]) -> Values:
    return {axis: clamp_value(raw.get(axis, 0)) for axis in ValueAxis}


def domain_values(domains: tuple[Domain | None, ...], scale_pct: float) -> dict[ValueAxis, float]:
    raw: dict[ValueAxis, float] = defaultdict(float)
    for index, domain in enumerate(domains):
        if domain is None:
            continue
        share = scale_pct / PERCENT * (1 if index == 0 else SECONDARY_DOMAIN_PCT / PERCENT)
        add_into(raw, DOMAIN_VALUES[domain], share)
    return raw


async def patron_domains(session: AsyncSession, entity: EntityRow) -> tuple[Domain | None, ...]:
    son = await living_patron(session, entity)
    if son is not None:
        return son.domains
    god = await foreign_patron(session, entity)
    return (god.domain_primary, god.domain_secondary) if god is not None else ()


async def war_count(session: AsyncSession, entity_id: int) -> int:
    return len(list(await session.scalars(select(WarSideRow.war_id).where(WarSideRow.entity_id == entity_id))))


async def seed_people(session: AsyncSession, rules: Rules, people: EntityRow, rng: SeededRandom) -> Values:
    table = rules.culture_drift
    raw: dict[ValueAxis, float] = defaultdict(float)
    for name, weights in PEOPLE_STAT_VALUES.items():
        value = stat(people, name)
        if value is not None:
            add_into(raw, weights, (value - STAT_MIDPOINT) / PERCENT * table.stat_weight_pct / PERCENT * 2)
    for axis, weight in domain_values(await patron_domains(session, people), table.domain_weight_pct).items():
        raw[axis] += weight
    raw[ValueAxis.MARTIAL] += min(table.history_cap, await war_count(session, people.id) * table.history_war_martial)
    trade = len(await active_bonds(session, [BondKind.TRADES_WITH], sources=[people.id])) + len(
        await active_bonds(session, [BondKind.TRADES_WITH], targets=[people.id])
    )
    raw[ValueAxis.XENOPHILIA] += min(table.history_cap, trade * table.history_trade)
    raw[ValueAxis.WEALTH] += min(table.history_cap, trade * table.history_trade)
    for axis in ValueAxis:
        raw[axis] += rng.integer(-table.seed_jitter, table.seed_jitter)
    return finished(raw)


async def seed_doctrine(session: AsyncSession, rules: Rules, cult: EntityRow, rng: SeededRandom) -> Values:
    table = rules.culture_drift
    raw: dict[ValueAxis, float] = defaultdict(float)
    add_into(raw, DOCTRINE_BASE, 1)
    for axis, value in domain_values(await patron_domains(session, cult), table.domain_weight_pct * table.doctrine_domain_pct / PERCENT).items():
        raw[axis] += value
    zeal = stat(cult, "zeal")
    if zeal is not None:
        raw[ValueAxis.PIETY] += (zeal - STAT_MIDPOINT) * table.stat_weight_pct / PERCENT
    for axis in ValueAxis:
        raw[axis] += rng.integer(-table.seed_jitter, table.seed_jitter)
    return finished(raw)


async def seed_agenda(session: AsyncSession, rules: Rules, faction: EntityRow, rng: SeededRandom) -> Values:
    table = rules.culture_drift
    raw: dict[ValueAxis, float] = defaultdict(float)
    people = await people_of(session, faction)
    if people is not None:
        add_into(raw, await stored_values(session, ValueHolder.CULTURE, people.id), table.agenda_culture_pct / PERCENT)
    kind = faction.engine_kind
    if isinstance(kind, EngineKind) and kind in AGENDA_VALUES:
        add_into(raw, AGENDA_VALUES[kind], 1)
    for axis in ValueAxis:
        raw[axis] += rng.integer(-table.seed_jitter, table.seed_jitter)
    return finished(raw)


async def seed_personal(session: AsyncSession, rules: Rules, mortal: EntityRow, rng: SeededRandom) -> Values:
    table = rules.culture_drift
    people = await people_of(session, mortal)
    culture = await stored_values(session, ValueHolder.CULTURE, people.id) if people is not None else {}
    raw: dict[ValueAxis, float] = defaultdict(float)
    upbringing = [
        (await mean_of(session, ValueHolder.PERSONAL, await parents_of(session, mortal.id)), table.parent_value_pct),
        (await mean_of(session, ValueHolder.DOCTRINE, await bonded(session, mortal.id, BondKind.MEMBER_OF, EntityType.CULT)), table.cult_value_pct),
        (await mean_of(session, ValueHolder.PERSONAL, await bonded(session, mortal.id, BondKind.APPRENTICE_OF, EntityType.MORTAL)), table.teacher_value_pct),
    ]
    remaining = 1.0
    for source, share_pct in upbringing:
        if source:
            share = remaining * share_pct / PERCENT
            add_into(raw, source, share)
            remaining -= share
    add_into(raw, culture, remaining)
    for trait in await traits_of(session, mortal.id):
        add_into(raw, TRAITS[trait].values, table.trait_value_pct / PERCENT)
    for axis in ValueAxis:
        raw[axis] += rng.integer(-table.personal_deviation, table.personal_deviation)
    return finished(raw)


async def mean_of(session: AsyncSession, holder: ValueHolder, node_ids: list[int]) -> Values:
    vectors = [vector for node_id in node_ids if (vector := await stored_values(session, holder, node_id))]
    return {axis: round(sum(vector.get(axis, 0) for vector in vectors) / len(vectors)) for axis in ValueAxis} if vectors else {}


async def bonded(session: AsyncSession, node_id: int, kind: BondKind, target_type: EntityType) -> list[int]:
    found: list[int] = []
    for bond in await active_bonds(session, [kind], sources=[node_id]):
        target = await living_entity(session, bond.target_node_id)
        if target is not None and target.entity_type is target_type:
            found.append(target.id)
    return found


async def drift_divine(ctx: TickContext, god: SonRow | ForeignGodRow, index: ValueIndex) -> bool:
    mind = await mind_of(ctx.session, god.id)
    if mind is None or is_locked(mind, VALUE_LOCK):
        return False
    current = index.of(god.id)
    derived = seed_divine(ctx.rules, god, SeededRandom.for_epoch(god.id, 0, "divine_values"))
    moved = blend(current, derived, ctx.rules.culture_drift.divine_drift_pct) if current else derived
    if moved == current:
        return False
    await write_values(ctx.session, ValueHolder.DIVINE, god.id, moved)
    index.vectors[god.id] = moved
    return True


def seed_divine(rules: Rules, god: SonRow | ForeignGodRow, rng: SeededRandom) -> Values:
    table = rules.culture_drift
    domains: tuple[Domain | None, ...] = god.domains if isinstance(god, SonRow) else (god.domain_primary, god.domain_secondary)
    raw = domain_values(domains, table.divine_domain_pct)
    if isinstance(god, SonRow):
        for passion, weights in PASSION_VALUES.items():
            level = getattr(god, passion.value, None)
            if isinstance(level, int):
                add_into(raw, weights, (level - PASSION_MIDPOINT) / PASSION_MIDPOINT * table.passion_weight_pct / PERCENT)
    for axis in ValueAxis:
        raw[axis] += rng.integer(-table.seed_jitter, table.seed_jitter)
    return finished(raw)


async def seed_values(session: AsyncSession, rules: Rules, node: Holder, rng: SeededRandom) -> Values | None:
    if isinstance(node, SonRow | ForeignGodRow):
        return seed_divine(rules, node, rng)
    seeders = {
        ValueHolder.CULTURE: seed_people,
        ValueHolder.DOCTRINE: seed_doctrine,
        ValueHolder.AGENDA: seed_agenda,
        ValueHolder.PERSONAL: seed_personal,
    }
    kind = holder_kind(node)
    seeder = seeders.get(kind) if kind is not None else None
    if seeder is None or not isinstance(node, EntityRow):
        return None
    return await seeder(session, rules, node, rng)


def son_passion(son: SonRow, passion: Passion) -> int:
    value = getattr(son, passion.value, 0)
    return value if isinstance(value, int) else 0


async def ruler_values(session: AsyncSession, index: ValueIndex, community_id: int) -> Values | None:
    for bond in await active_bonds(session, [BondKind.RULES], targets=[community_id]):
        ruler = await living_entity(session, bond.source_node_id)
        if ruler is not None and ruler.entity_type is EntityType.MORTAL:
            found = index.of(ruler.id)
            if found:
                return found
    return None


async def neighbour_mean(session: AsyncSession, index: ValueIndex, community_id: int) -> Values | None:
    rows = await session.scalars(
        select(CommunityRelationRow).where((CommunityRelationRow.entity_a_id == community_id) | (CommunityRelationRow.entity_b_id == community_id))
    )
    vectors = []
    for row in rows:
        other = row.entity_b_id if row.entity_a_id == community_id else row.entity_a_id
        found = index.of(other)
        if found:
            vectors.append(found)
    if not vectors:
        return None
    return {axis: round(sum(vector.get(axis, 0) for vector in vectors) / len(vectors)) for axis in ValueAxis}


async def experience_shift(ctx: TickContext, community: EntityRow, index: ValueIndex, plagued: set[int]) -> tuple[Causes, Values | None]:
    table = ctx.rules.culture_drift
    causes = empty()
    conqueror: Values | None = None
    sign = lost_war_sign(ctx.rules, await cohesion_of(ctx.session, ctx.rules, community))
    fresh = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == community.id, MemoryRow.epoch == ctx.epoch))
    for memory in fresh:
        if memory.kind is MemoryKind.CONQUERED_US:
            add_shift(causes, DriftCause.WAR_LOST, ValueAxis.MARTIAL, sign * table.war_lost_martial)
            conqueror = index.of(memory.subject_node_id) or conqueror
        elif memory.kind is MemoryKind.FOUGHT_US:
            add_shift(causes, DriftCause.WAR_FOUGHT, ValueAxis.MARTIAL, table.war_martial)
        elif memory.kind is MemoryKind.TRADED_WITH:
            add_shift(causes, DriftCause.TRADE, ValueAxis.XENOPHILIA, table.trade_xenophilia)
            add_shift(causes, DriftCause.TRADE, ValueAxis.WEALTH, table.trade_wealth)
    victories = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.subject_node_id == community.id, MemoryRow.epoch == ctx.epoch, MemoryRow.kind == MemoryKind.CONQUERED_US)
    )
    for _ in victories:
        add_shift(causes, DriftCause.WAR_WON, ValueAxis.MARTIAL, table.war_won_martial)
    if community.id in plagued:
        add_shift(causes, DriftCause.PLAGUE, ValueAxis.PIETY, table.plague_piety)
        add_shift(causes, DriftCause.PLAGUE, ValueAxis.DEATH, table.plague_death)
    famine = await famine_shift(ctx.session, ctx.rules, community.id)
    if famine:
        add_shift(causes, DriftCause.FAMINE, ValueAxis.KINSHIP, famine)
    for axis, value in (await ideology_shift(ctx.session, ctx.rules, community.id)).items():
        add_shift(causes, DriftCause.IDEOLOGY, axis, value)
    return causes, conqueror


def pull_toward(target: dict[ValueAxis, float], current: Values, source: Values | None, share_pct: float) -> None:
    if not source:
        return
    for axis in ValueAxis:
        target[axis] += (source.get(axis, 0) - current.get(axis, 0)) * share_pct / PERCENT


async def pressure_causes(ctx: TickContext, community: EntityRow, index: ValueIndex, current: Values, plagued: set[int]) -> Causes:
    table = ctx.rules.culture_drift
    causes, conqueror = await experience_shift(ctx, community, index, plagued)
    pulls = (
        (
            DriftCause.NEIGHBOURS,
            await neighbour_mean(ctx.session, index, community.id),
            table.neighbour_pull_pct * scaled_by(current.get(ValueAxis.XENOPHILIA, 0)),
        ),
        (DriftCause.RULER, await ruler_values(ctx.session, index, community.id), table.ruler_pull_pct),
    )
    patron = await living_patron(ctx.session, community)
    god = index.of(patron.id) if patron is not None else {}
    for cause, source, share in (*pulls, (DriftCause.GOD, god, table.god_pull_pct * scaled_by(current.get(ValueAxis.PIETY, 0)))):
        for axis, value in pull_shift(current, source, share).items():
            add_shift(causes, cause, axis, value)
    if conqueror:
        resistance = (current.get(ValueAxis.KINSHIP, 0) + current.get(ValueAxis.TRADITION, 0) + current.get(ValueAxis.HONOUR, 0)) / 3
        sign = -1 if resistance >= table.conquest_resistance else 1
        for axis, value in pull_shift(current, conqueror, sign * table.conquest_pull_pct).items():
            add_shift(causes, DriftCause.CONQUEST, axis, value)
    return causes


async def pressure_target(ctx: TickContext, community: EntityRow, index: ValueIndex, current: Values, plagued: set[int]) -> dict[ValueAxis, float]:
    target: dict[ValueAxis, float] = {axis: float(current.get(axis, 0)) for axis in ValueAxis}
    for shift in (await pressure_causes(ctx, community, index, current, plagued)).values():
        for axis, value in shift.items():
            target[axis] += value
    return target


async def drift_culture(ctx: TickContext, community: EntityRow, index: ValueIndex, plagued: set[int]) -> bool:
    table = ctx.rules.culture_drift
    mind = await mind_of(ctx.session, community.id)
    current = index.of(community.id)
    holder = holder_kind(community)
    if mind is None or is_locked(mind, VALUE_LOCK) or not current or holder is None:
        return False
    causes = await pressure_causes(ctx, community, index, current, plagued)
    imposed = await impositions_of(ctx.session, community.id)
    for row in imposed:
        add_shift(causes, row.cause, row.axis, row.amount * PERCENT / max(1, table.drift_rate_pct))
    await spend_impositions(ctx.session, imposed)
    target: dict[ValueAxis, float] = {axis: float(current.get(axis, 0)) for axis in ValueAxis}
    for shift in causes.values():
        for axis, value in shift.items():
            target[axis] += value
    resist = scaled_by(-max(0, current.get(ValueAxis.TRADITION, 0)) * table.tradition_resist_pct // PERCENT)
    rate = table.drift_rate_pct * resist
    await record_causes(ctx, community.id, causes, rate)
    moved = blend(current, {axis: round(value) for axis, value in target.items()}, rate)
    if moved == current:
        return False
    await write_values(ctx.session, holder, community.id, moved)
    index.vectors[community.id] = moved
    await note_shift(ctx, community, current, moved)
    return True


async def note_shift(ctx: TickContext, community: EntityRow, before: Values, after: Values) -> None:
    mark = ctx.rules.culture_drift.notable_value
    for axis in ValueAxis:
        old, new = before.get(axis, 0), after.get(axis, 0)
        low, high = VALUE_LABELS[axis]
        if old < mark <= new:
            await note(ctx, f"{community.name} came to prize {high.lower()}.", key="culture.shift", ids=[community.id])
        elif old > -mark >= new:
            await note(ctx, f"{community.name} turned toward {low.lower()}.", key="culture.shift", ids=[community.id])


async def member_mean(ctx: TickContext, index: ValueIndex, body_id: int) -> Values | None:
    vectors = []
    for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF, BondKind.RULES, BondKind.WORSHIPS], targets=[body_id]):
        found = index.of(bond.source_node_id)
        if found:
            vectors.append(found)
    for bond in await active_bonds(ctx.session, [BondKind.RULES], sources=[body_id]):
        found = index.of(bond.target_node_id)
        if found:
            vectors.append(found)
    if not vectors:
        return None
    return {axis: round(sum(vector.get(axis, 0) for vector in vectors) / len(vectors)) for axis in ValueAxis}


async def drift_body(ctx: TickContext, body: EntityRow, index: ValueIndex) -> bool:
    table = ctx.rules.culture_drift
    holder = holder_kind(body)
    mind = await mind_of(ctx.session, body.id)
    current = index.of(body.id)
    if holder not in (ValueHolder.AGENDA, ValueHolder.DOCTRINE) or mind is None or is_locked(mind, VALUE_LOCK) or not current:
        return False
    people = await people_of(ctx.session, body)
    culture = index.of(people.id) if people is not None else {}
    members = await member_mean(ctx, index, body.id)
    target: dict[ValueAxis, float] = dict(current)
    if culture:
        pull_toward(target, current, culture, PERCENT - table.leader_weight_pct)
    if members:
        pull_toward(target, current, members, table.leader_weight_pct)
    rate = table.agenda_drift_pct if holder is ValueHolder.AGENDA else table.doctrine_drift_pct
    moved = blend(current, {axis: round(value) for axis, value in target.items()}, rate)
    if moved == current:
        return False
    await write_values(ctx.session, holder, body.id, moved)
    index.vectors[body.id] = moved
    await note_shift(ctx, body, current, moved)
    return True


async def liege_of(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    if mortal.location_id is None:
        return None
    for bond in await active_bonds(session, [BondKind.RULES], targets=[mortal.location_id]):
        ruler = await living_entity(session, bond.source_node_id)
        if ruler is not None and ruler.id != mortal.id and ruler.entity_type is EntityType.MORTAL:
            return ruler
    return None


async def experiences(ctx: TickContext, mortal: EntityRow) -> dict[ValueAxis, float]:
    table = ctx.rules.culture_drift
    shifts: dict[ValueAxis, float] = defaultdict(float)
    maimed = await ctx.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.kind.in_(list(TOTAL_LOSS_KINDS)), InjuryRow.epoch >= ctx.epoch - 1).limit(1)
    )
    if maimed is not None:
        shifts[ValueAxis.DEATH] += table.maimed_shift
        shifts[ValueAxis.PIETY] += table.maimed_shift / 2
    fighting = mortal.location_id is not None and await ctx.session.scalar(
        select(WarSideRow.war_id).where(WarSideRow.entity_id == mortal.location_id, WarSideRow.left_epoch.is_(None)).limit(1)
    )
    if fighting:
        shifts[ValueAxis.MARTIAL] += table.war_shift
        shifts[ValueAxis.MERCY] -= table.war_shift / 2
    converted = await ctx.session.scalar(
        select(MemoryRow.id).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind == MemoryKind.CONVERTED_ME, MemoryRow.epoch >= ctx.epoch - 1).limit(1)
    )
    if converted is not None:
        shifts[ValueAxis.PIETY] += table.conversion_shift
        shifts[ValueAxis.TRADITION] -= table.conversion_shift / 2
    return shifts


async def drift_person(ctx: TickContext, mortal: EntityRow, index: ValueIndex, traits: set[TraitKind]) -> bool:
    table = ctx.rules.culture_drift
    mind = await mind_of(ctx.session, mortal.id)
    if mind is None or is_locked(mind, VALUE_LOCK):
        return False
    current = index.of(mortal.id)
    people = await people_of(ctx.session, mortal)
    culture = index.of(people.id) if people is not None else {}
    if not current or not culture:
        return False
    rate = table.mortal_pull_pct * scaled_by(trait_effect(traits, TraitEffect.DRIFT, ctx.rules.traits.effect_scale_pct))
    target: dict[ValueAxis, float] = {axis: float(culture.get(axis, 0)) for axis in ValueAxis}
    liege = await liege_of(ctx.session, mortal)
    if liege is not None:
        pull_toward(target, culture, index.of(liege.id) or await values_for(ctx.session, liege.id), table.person_ruler_pct)
    patron = await living_patron(ctx.session, mortal)
    if patron is not None:
        pull_toward(target, culture, index.of(patron.id) or await values_for(ctx.session, patron.id), table.person_god_pct)
    for axis, shift in (await experiences(ctx, mortal)).items():
        target[axis] = target.get(axis, 0.0) + shift
    moved = blend(current, {axis: round(value) for axis, value in target.items()}, rate)
    if moved == current:
        return False
    await write_values(ctx.session, ValueHolder.PERSONAL, mortal.id, moved)
    index.vectors[mortal.id] = moved
    return True
