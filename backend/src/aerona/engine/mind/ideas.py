from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind_split import BRANCH_IDEAS, IDEAS, IDEOLOGY_IDEAS, TENET_IDEAS, idea_for_beliefs
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow, ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.mind import IdeaRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import IdeologyTenet, ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.folkways import IdeaStrain
from aerona.domain.enums.mind import Facet, IdeaKind, IdeaSource, IdeaState, ThoughtKind, ValueHolder
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Holder, Values, clamp_value, is_locked, mind_of, stored_values, write_values
from aerona.engine.mind.split import (
    ATTRIBUTE_LOCK,
    FACET_LOCK,
    attributes_of,
    clamp_facet,
    facets_of,
    has_attributes,
    incubating,
    store_attributes,
    write_facets,
)
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.values import VALUE_LOCK
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import seed_of
from aerona.rules.registry import Rules

IDEA_LOCK = "ideas"
TEXT_CLASSES = frozenset({ItemClass.BOOK, ItemClass.SCROLL, ItemClass.PRAYER_BOOK})
FULL = 100
STRAIN_FROM = 15


@dataclass(frozen=True)
class Encounter:
    idea: IdeaKind
    source: IdeaSource
    source_node_id: int | None


def fit(values: Values, idea: IdeaKind) -> int:
    weights = IDEAS[idea].beliefs
    total = sum(abs(weight) for weight in weights.values())
    if not total:
        return 0
    return round(sum(values.get(axis, 0) * weight for axis, weight in weights.items()) / total)


async def ideas_of(session: AsyncSession, node_id: int) -> list[IdeaRow]:
    return list(await session.scalars(select(IdeaRow).where(IdeaRow.holder_node_id == node_id).order_by(IdeaRow.started_epoch, IdeaRow.id)))


async def ideology_encounters(session: AsyncSession, holders: list[int]) -> list[Encounter]:
    found: list[Encounter] = []
    rows = await session.execute(
        select(IdeologyAdherentRow.ideology_entity_id, IdeologyProfileRow.tenets)
        .join(IdeologyProfileRow, IdeologyProfileRow.ideology_entity_id == IdeologyAdherentRow.ideology_entity_id)
        .where(IdeologyAdherentRow.adherent_entity_id.in_(holders))
    )
    for ideology_id, tenets in rows:
        for tenet in tenets or []:
            idea = IDEOLOGY_IDEAS.get(IdeologyTenet(tenet)) if tenet in IdeologyTenet._value2member_map_ else None
            if idea is not None:
                found.append(Encounter(idea, IdeaSource.IDEOLOGY, ideology_id))
    return found


async def doctrine_encounters(session: AsyncSession, mortal: EntityRow) -> list[Encounter]:
    cults = await session.scalars(
        select(BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.source_node_id == mortal.id,
            BondRow.kind == BondKind.MEMBER_OF,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.CULT,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    found: list[Encounter] = []
    for cult_id in list(cults):
        for tenet in await session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult_id)):
            idea = TENET_IDEAS.get(TenetKind(tenet))
            if idea is not None:
                found.append(Encounter(idea, IdeaSource.DOCTRINE, cult_id))
    return found


def theory_encounters(knowledge: KnowledgeMap, holders: list[int]) -> list[Encounter]:
    return [
        Encounter(BRANCH_IDEAS[branch], IdeaSource.THEORY, holder)
        for holder in holders
        for branch in sorted(knowledge.branches(holder))
        if branch in BRANCH_IDEAS
    ]


async def book_encounters(session: AsyncSession, mortal: EntityRow) -> list[Encounter]:
    owned = list(
        await session.scalars(
            select(ItemProfileRow.item_entity_id)
            .join(BondRow, BondRow.target_node_id == ItemProfileRow.item_entity_id)
            .where(
                BondRow.source_node_id == mortal.id,
                BondRow.kind == BondKind.OWNS,
                BondRow.state == BondState.ACTIVE,
                ItemProfileRow.item_class.in_(TEXT_CLASSES),
            )
        )
    )
    if not owned:
        return []
    found: list[Encounter] = []
    for profile in await session.scalars(select(IdeologyProfileRow)):
        for item_id in owned:
            if item_id in (profile.texts or []):
                for tenet in profile.tenets or []:
                    idea = IDEOLOGY_IDEAS.get(IdeologyTenet(tenet)) if tenet in IdeologyTenet._value2member_map_ else None
                    if idea is not None:
                        found.append(Encounter(idea, IdeaSource.BOOK, item_id))
    return found


async def teacher_encounters(session: AsyncSession, mortal: EntityRow) -> list[Encounter]:
    masters = list(
        await session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.APPRENTICE_OF, BondRow.state == BondState.ACTIVE)
        )
    )
    found: list[Encounter] = []
    for master in masters:
        for row in await ideas_of(session, master):
            if row.state is IdeaState.INTERNALISED:
                found.append(Encounter(row.idea, IdeaSource.TEACHER, master))
        dominant = idea_for_beliefs(await stored_values(session, ValueHolder.PERSONAL, master))
        if dominant is not None:
            found.append(Encounter(dominant, IdeaSource.TEACHER, master))
    return found


async def encounters(session: AsyncSession, mortal: EntityRow, knowledge: KnowledgeMap) -> tuple[list[Encounter], list[Encounter]]:
    people = await people_of(session, mortal)
    holders = [mortal.id, *([people.id] if people is not None else []), *([mortal.location_id] if mortal.location_id is not None else [])]
    taught = await teacher_encounters(session, mortal)
    met = [
        *await ideology_encounters(session, holders),
        *await doctrine_encounters(session, mortal),
        *theory_encounters(knowledge, holders),
        *await book_encounters(session, mortal),
    ]
    return taught, met


def strain_of(facets: Mapping[Facet, int], threshold: int) -> IdeaStrain:
    if facets.get(Facet.PERSEVERANCE, 0) >= threshold:
        return IdeaStrain.OBSESSION
    if facets.get(Facet.DISCIPLINE, 0) <= -threshold:
        return IdeaStrain.FOCUS_LOSS
    return IdeaStrain.DISTRACTION


async def take_up(
    session: AsyncSession, holder_id: int, encounter: Encounter, epoch: int, *, progress: int = 0, strain_from: int = STRAIN_FROM
) -> IdeaRow | None:
    if await session.scalar(select(IdeaRow.id).where(IdeaRow.holder_node_id == holder_id, IdeaRow.idea == encounter.idea)) is not None:
        return None
    row = IdeaRow(
        holder_node_id=holder_id,
        idea=encounter.idea,
        source=encounter.source,
        source_node_id=encounter.source_node_id,
        progress=max(0, min(FULL, progress)),
        state=IdeaState.INCUBATING,
        strain=strain_of(await facets_of(session, holder_id), strain_from),
        started_epoch=epoch,
    )
    session.add(row)
    await session.flush()
    return row


async def internalise(session: AsyncSession, rules: Rules, node: Holder, row: IdeaRow, epoch: int) -> None:
    spec = IDEAS[row.idea]
    mind = await mind_of(session, node.id)
    row.state, row.progress, row.finished_epoch = IdeaState.INTERNALISED, FULL, epoch
    await think(session, rules, node.id, ThoughtKind.TOOK_IDEA_TO_HEART, epoch)
    if not is_locked(mind, VALUE_LOCK):
        values = await stored_values(session, ValueHolder.PERSONAL, node.id)
        scale = rules.ideas.belief_scale_pct / PERCENT
        for axis, shift in spec.beliefs.items():
            values[axis] = clamp_value(values.get(axis, 0) + shift * scale)
        await write_values(session, ValueHolder.PERSONAL, node.id, values)
    if has_attributes(node) and not is_locked(mind, ATTRIBUTE_LOCK):
        attributes = await attributes_of(session, node.id)
        if attributes:
            for member, gain in spec.gains.items():
                attributes[member] = attributes.get(member, 0) + gain
            for member, cost in spec.costs.items():
                attributes[member] = attributes.get(member, 0) - cost
            await store_attributes(session, node, attributes)
    if not is_locked(mind, FACET_LOCK):
        facets = await facets_of(session, node.id)
        if facets:
            await write_facets(session, node.id, {facet: clamp_facet(facets.get(facet, 0) + shift) for facet, shift in spec.facets.items()})
    await session.flush()


async def obsess(ctx: TickContext, mortal: EntityRow) -> None:
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is not None and not is_held(profile, "stress"):
        profile.stress = min(FULL, profile.stress + ctx.rules.ideas.obsession_stress)


def reject(row: IdeaRow, epoch: int) -> None:
    row.state, row.finished_epoch = IdeaState.REJECTED, epoch


@dataclass
class IdeaTally:
    taken: int = 0
    internalised: int = 0
    rejected: int = 0


async def turn_over(ctx: TickContext, mortal: EntityRow, knowledge: KnowledgeMap) -> IdeaTally:
    tally = IdeaTally()
    if is_locked(await mind_of(ctx.session, mortal.id), IDEA_LOCK):
        return tally
    table = ctx.rules.ideas
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    curiosity = (await facets_of(ctx.session, mortal.id)).get(Facet.CURIOSITY, 0)
    eager = max(0.0, 1 + curiosity / FULL * table.curiosity_pct / PERCENT)
    for row in await incubating(ctx.session, mortal.id):
        rng = ctx.rng(seed_of("idea", mortal.id, row.id, ctx.epoch))
        suits = fit(values, row.idea)
        if suits < table.reject_below and rng.chance(table.reject_pct):
            reject(row, ctx.epoch)
            tally.rejected += 1
            continue
        rate = table.incubation_rate * eager * max(0.0, 1 + suits / FULL * table.fit_pct / PERCENT)
        if row.strain is IdeaStrain.OBSESSION:
            rate *= 1 + table.obsession_speed_pct / PERCENT
            await obsess(ctx, mortal)
        row.progress = min(FULL, row.progress + max(1, round(rate)))
        if row.progress >= FULL:
            await internalise(ctx.session, ctx.rules, mortal, row, ctx.epoch)
            tally.internalised += 1
    if len(await incubating(ctx.session, mortal.id)) >= table.slots:
        return tally
    rng = ctx.rng(seed_of("idea.meet", mortal.id, ctx.epoch))
    if not rng.chance(min(PERCENT, table.encounter_pct * eager)):
        return tally
    held = {row.idea for row in await ideas_of(ctx.session, mortal.id)}
    taught, met = await encounters(ctx.session, mortal, knowledge)
    taught = [item for item in taught if item.idea not in held]
    met = [item for item in met if item.idea not in held]
    pool = taught if taught and (not met or rng.chance(table.teacher_pct)) else met
    if pool and await take_up(ctx.session, mortal.id, rng.pick(pool), ctx.epoch, strain_from=table.strain_from) is not None:
        tally.taken += 1
    return tally
