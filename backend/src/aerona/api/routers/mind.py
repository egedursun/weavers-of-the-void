from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.mind import (
    AttributeShiftView,
    AttributeView,
    BeliefShiftView,
    CareerView,
    DreamLogView,
    EmotionKindView,
    EmotionTotalView,
    FacetShiftView,
    FacetView,
    FeelingsView,
    FormativeView,
    GriefView,
    IdeaSpecView,
    IdeaView,
    LabelView,
    MemoryView,
    MindSplitView,
    MindView,
    NeedView,
    OpinionComponentView,
    OpinionMemoryView,
    OpinionTermView,
    OpinionView,
    PressureView,
    SkillView,
    SummaryView,
    ThoughtKindView,
    ThoughtView,
    TraitCapacityView,
    TraitEffectView,
    TraitView,
    ValueView,
)
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.mind import FIXED_ROLES, MEMORIES, NEED_LABELS, PRESSURE_LABELS, SKILLS, TRAITS, VALUE_LABELS
from aerona.catalog.mind_split import ATTRIBUTES, FACETS, IDEAS, SKILL_ATTRIBUTES
from aerona.catalog.thoughts import DREAM_LABELS, EMOTIONS, NEEDS, READING_LABELS, THOUGHTS
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import MIND_LOCKS, DreamRow, GriefRow, MemoryRow, TraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion, IdeaKind, MemoryKind, ValueAxis, ValueHolder
from aerona.engine.body.book import factor
from aerona.engine.body.customs import people_of
from aerona.engine.mind.book import Holder, holder_kind, load_holder, mind_of, needs_of, pressures_of, skills_of, stored_values, values_of
from aerona.engine.mind.ideas import fit, ideas_of
from aerona.engine.mind.memories import memories_of, strength_of
from aerona.engine.mind.opinion import Opinion, opinion
from aerona.engine.mind.skills import level_cost
from aerona.engine.mind.split import Bodied, attributes_of, culture_mean, derived_summaries, effective_attributes, facets_of, has_attributes, has_facets
from aerona.engine.mind.thoughts import need_importance, thoughts_of
from aerona.engine.mind.thoughts import strength_of as thought_strength
from aerona.engine.primitives.faith import living_patron
from aerona.engine.services.community_relations import cosmos_epoch
from aerona.rules.registry import Rules

router = APIRouter(tags=["mind"])
NO_MIND = "No mind lives there."
COMMUNITY_LOCKS = frozenset({"values", "memories", "needs"})
LOCKS_BY_HOLDER = {
    ValueHolder.PERSONAL: frozenset(MIND_LOCKS) - {"thoughts", "griefs", "dreams", "attributes", "facets", "ideas"},
    ValueHolder.DIVINE: frozenset({"values", "traits", "memories", "attributes", "facets"}),
    ValueHolder.CULTURE: COMMUNITY_LOCKS,
    ValueHolder.COMMUNITY: frozenset({"memories", "needs"}),
    ValueHolder.DOCTRINE: frozenset({"values", "memories"}),
    ValueHolder.AGENDA: frozenset({"values", "memories"}),
}


async def reference_of(session: AsyncSession, node: Holder) -> Holder | None:
    if not isinstance(node, EntityRow):
        return None
    if node.entity_type in {EntityType.MORTAL, EntityType.FACTION, EntityType.SETTLEMENT}:
        people = await people_of(session, node)
        return people if people is not None and people.id != node.id else None
    if node.entity_type in {EntityType.PEOPLE, EntityType.CULT}:
        return await living_patron(session, node)
    return None


async def opinion_view(session: AsyncSession, found: Opinion) -> OpinionView:
    return OpinionView(
        holder=await node_ref(session, found.holder_id),
        subject=await node_ref(session, found.subject_id),
        value=found.value,
        alignment=found.alignment,
        components=[OpinionComponentView(component=component, value=value) for component, value in found.components.items()],
        terms=[OpinionTermView(key=term.key, value=term.value) for term in found.terms],
        memories=[
            OpinionMemoryView(
                id=item.row.id,
                kind=item.row.kind,
                label=MEMORIES[item.row.kind].label,
                epoch=item.row.epoch,
                strength=item.strength,
                weight_pct=item.weight_pct,
                contribution=item.contribution,
                note=item.row.note,
            )
            for item in found.memories
        ],
    )


async def trait_views(session: AsyncSession, node_id: int) -> list[TraitView]:
    rows = list(await session.scalars(select(TraitRow).where(TraitRow.node_id == node_id).order_by(TraitRow.epoch, TraitRow.trait)))
    sources = await node_refs(session, [row.source_node_id for row in rows if row.source_node_id is not None])
    return [
        TraitView(
            trait=row.trait,
            label=TRAITS[row.trait].label,
            source=row.source,
            epoch=row.epoch,
            source_node=sources.get(row.source_node_id) if row.source_node_id is not None else None,
            opposite=TRAITS[row.trait].opposite,
            heritable=TRAITS[row.trait].heritable,
            variant_id=row.variant_id,
            effects=[TraitEffectView(effect=effect, value=value) for effect, value in TRAITS[row.trait].effects.items()],
            capacities=[TraitCapacityView(capacity=capacity, value=value) for capacity, value in TRAITS[row.trait].capacities.items()],
        )
        for row in rows
    ]


async def skill_views(session: AsyncSession, rules: Rules, node_id: int, epoch: int) -> list[SkillView]:
    rows = sorted((await skills_of(session, node_id)).values(), key=lambda row: (-row.level, row.skill))
    subjects = await node_refs(session, [row.subject_node_id for row in rows if row.subject_node_id is not None])
    views: list[SkillView] = []
    for row in rows:
        spec = SKILLS[row.skill]
        views.append(
            SkillView(
                id=row.id,
                skill=row.skill,
                label=spec.label,
                family=spec.family,
                capacity=spec.capacity,
                level=row.level,
                effective=round(row.level * await factor(session, node_id, spec.capacity)),
                peak=row.peak,
                xp=row.xp,
                next_level_xp=level_cost(rules, row.level),
                last_used_epoch=row.last_used_epoch,
                rusting=epoch - row.last_used_epoch >= rules.skills.rust_epochs,
                source=row.source,
                subject=subjects.get(row.subject_node_id) if row.subject_node_id is not None else None,
                variant_id=row.variant_id,
            )
        )
    return views


async def memory_views(session: AsyncSession, node_id: int, epoch: int) -> list[MemoryView]:
    rows = await memories_of(session, node_id)
    refs = await node_refs(session, [row.subject_node_id for row in rows] + [row.inherited_from_node_id for row in rows if row.inherited_from_node_id])
    ordered = sorted(rows, key=lambda row: (-abs(strength_of(row, epoch)), -row.epoch, row.id))
    return [
        MemoryView(
            id=row.id,
            subject=refs.get(row.subject_node_id),
            kind=row.kind,
            label=MEMORIES[row.kind].label,
            magnitude=row.magnitude,
            strength=round(strength_of(row, epoch)),
            decay_pct=row.decay_pct,
            epoch=row.epoch,
            note=row.note,
            inherited_from=refs.get(row.inherited_from_node_id) if row.inherited_from_node_id is not None else None,
        )
        for row in ordered
    ]


@router.get("/minds/{node_id}", response_model=MindView)
async def mind_view(services: ServicesDep, node_id: int = Path(ge=1)) -> MindView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        node = await load_holder(session, node_id)
        kind = holder_kind(node) if node is not None else None
        mind = await mind_of(session, node_id)
        if node is None or kind is None or mind is None:
            raise NotFoundError(NO_MIND)
        epoch = await cosmos_epoch(session)
        reference = await reference_of(session, node)
        reference_values = await values_of(session, reference) if reference is not None else {}
        values = await values_of(session, node)
        memories = await memory_views(session, node_id, epoch)
        subjects = list(dict.fromkeys(memory.subject.id for memory in memories if memory.subject is not None))
        opinions = [await opinion_view(session, await opinion(session, rules, epoch, node_id, subject)) for subject in subjects]
        opinions.sort(key=lambda item: -abs(item.value))
        mortal = isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL
        borrowed = reference if kind is ValueHolder.COMMUNITY and reference is not None else None
        return MindView(
            node_id=node_id,
            name=node.name,
            holder=kind,
            locked=list(mind.locked or []),
            lockable=[field for field in MIND_LOCKS if field in LOCKS_BY_HOLDER[kind]],
            borrowed_from=await node_ref(session, borrowed.id) if borrowed is not None else None,
            reference=await node_ref(session, reference.id) if reference is not None else None,
            values=[
                ValueView(
                    axis=axis,
                    value=values.get(axis, 0),
                    low_label=VALUE_LABELS[axis][0],
                    high_label=VALUE_LABELS[axis][1],
                    reference=reference_values.get(axis) if reference_values else None,
                )
                for axis in ValueAxis
            ]
            if values
            else [],
            traits=await trait_views(session, node_id),
            skills=await skill_views(session, rules, node_id, epoch),
            needs=await need_views(session, rules, node, node_id),
            pressures=[
                PressureView(pressure=kind_, label=PRESSURE_LABELS[kind_], value=value)
                for kind_, value in sorted((await pressures_of(session, node_id)).items())
            ],
            memories=memories,
            opinions=opinions,
            career=CareerView(role=node.mortal_role, ended_epoch=mind.career_ended_epoch, fixed=node.mortal_role in FIXED_ROLES)
            if mortal and isinstance(node, EntityRow)
            else None,
            max_traits=rules.traits.max_traits,
        )


def idea_spec_view(idea: IdeaKind) -> IdeaSpecView:
    spec = IDEAS[idea]
    return IdeaSpecView(
        idea=idea,
        label=spec.label,
        beliefs=[BeliefShiftView(axis=axis, label=VALUE_LABELS[axis][1 if shift > 0 else 0], value=shift) for axis, shift in spec.beliefs.items()],
        gains=[AttributeShiftView(attribute=member, label=ATTRIBUTES[member].label, value=gain) for member, gain in spec.gains.items()],
        costs=[AttributeShiftView(attribute=member, label=ATTRIBUTES[member].label, value=cost) for member, cost in spec.costs.items()],
        facets=[FacetShiftView(facet=facet, label=FACETS[facet].label, value=shift) for facet, shift in spec.facets.items()],
        distraction=spec.distraction,
    )


async def bodied(session: AsyncSession, node_id: int) -> Bodied | None:
    entity = await session.get(EntityRow, node_id)
    if entity is not None:
        return entity
    son = await session.get(SonRow, node_id)
    if son is not None:
        return son
    return await session.get(ForeignGodRow, node_id)


SPLIT_LOCKS = ("attributes", "facets", "ideas")


@router.get("/minds/{node_id}/split", response_model=MindSplitView)
async def mind_split_view(services: ServicesDep, node_id: int = Path(ge=1)) -> MindSplitView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        node = await bodied(session, node_id)
        if node is None:
            ref = await node_ref(session, node_id)
            if ref is None:
                raise NotFoundError(NO_MIND)
            return MindSplitView(
                node_id=node_id,
                name=ref.name,
                has_attributes=False,
                has_facets=False,
                turns_ideas=False,
                locked=[],
                lockable=[],
                attributes=[],
                summaries=[],
                facets=[],
                ideas=[],
                catalogue=[],
                trait_threshold=rules.mind_split.trait_threshold,
                idea_slots=rules.ideas.slots,
            )
        attributes = await attributes_of(session, node_id) if has_attributes(node) else {}
        effective = await effective_attributes(session, rules, node) if attributes else {}
        facets = await facets_of(session, node_id) if has_facets(node) else {}
        mean = await culture_mean(session, rules, node) if has_facets(node) else {}
        mind = await mind_of(session, node_id)
        minded = mind is not None
        values = await stored_values(session, ValueHolder.PERSONAL if isinstance(node, EntityRow) else ValueHolder.DIVINE, node_id)
        rows = await ideas_of(session, node_id)
        sources = await node_refs(session, [row.source_node_id for row in rows if row.source_node_id is not None])
        turns = isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL
        return MindSplitView(
            node_id=node_id,
            name=node.name,
            has_attributes=has_attributes(node),
            has_facets=has_facets(node),
            turns_ideas=turns,
            locked=[field for field in (mind.locked or []) if field in SPLIT_LOCKS] if mind is not None else [],
            lockable=[field for field in SPLIT_LOCKS if minded and (field != "ideas" or turns) and (field != "facets" or has_facets(node))],
            attributes=[
                AttributeView(
                    attribute=member,
                    label=spec.label,
                    physical=spec.physical,
                    value=attributes[member],
                    effective=effective.get(member, attributes[member]),
                    governs=[skill for skill, members in SKILL_ATTRIBUTES.items() if member in members],
                )
                for member, spec in ATTRIBUTES.items()
                if member in attributes
            ],
            summaries=[SummaryView(name=name, value=value) for name, value in derived_summaries(node, attributes).items()] if attributes else [],
            facets=[
                FacetView(
                    facet=facet,
                    label=spec.label,
                    group=spec.group,
                    value=facets[facet],
                    mean=mean.get(facet, 0),
                    high_trait=spec.high,
                    low_trait=spec.low,
                )
                for facet, spec in FACETS.items()
                if facet in facets
            ],
            ideas=[
                IdeaView(
                    id=row.id,
                    idea=row.idea,
                    label=IDEAS[row.idea].label,
                    source=row.source,
                    source_node=sources.get(row.source_node_id) if row.source_node_id is not None else None,
                    progress=row.progress,
                    state=row.state,
                    started_epoch=row.started_epoch,
                    finished_epoch=row.finished_epoch,
                    fit=fit(values, row.idea),
                )
                for row in rows
            ],
            catalogue=[idea_spec_view(idea) for idea in IdeaKind] if turns else [],
            trait_threshold=rules.mind_split.trait_threshold,
            idea_slots=rules.ideas.slots,
        )


async def need_views(session: AsyncSession, rules: Rules, node: Holder, node_id: int) -> list[NeedView]:
    facets = await facets_of(session, node_id)
    values = await values_of(session, node)
    return [
        NeedView(need=need, label=NEED_LABELS[need], value=value, group=NEEDS[need].group, importance=need_importance(rules, need, facets, values))
        for need, value in sorted((await needs_of(session, node_id)).items(), key=lambda item: (list(NEEDS).index(item[0]), item[0]))
    ]


FEELING_LOCKS = ("thoughts", "griefs", "dreams")


@router.get("/minds/{node_id}/feelings", response_model=FeelingsView)
async def feelings_view(services: ServicesDep, node_id: int = Path(ge=1)) -> FeelingsView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_MIND)
        mortal = await session.get(EntityRow, node_id)
        applies = mortal is not None and mortal.entity_type is EntityType.MORTAL
        epoch = await cosmos_epoch(session)
        thoughts = await thoughts_of(session, node_id) if applies else []
        mind = await mind_of(session, node_id)
        profile = await session.get(MortalProfileRow, node_id)
        formative = list(
            await session.scalars(
                select(MemoryRow).where(MemoryRow.holder_node_id == node_id, MemoryRow.kind == MemoryKind.FORMATIVE).order_by(MemoryRow.epoch.desc())
            )
        )
        griefs = list(await session.scalars(select(GriefRow).where(GriefRow.mourner_node_id == node_id).order_by(GriefRow.started_epoch.desc())))
        dreams = list(await session.scalars(select(DreamRow).where(DreamRow.dreamer_node_id == node_id).order_by(DreamRow.epoch.desc(), DreamRow.id.desc())))
        wanted = [
            *(row.subject_node_id for row in thoughts),
            *(row.subject_node_id for row in formative),
            *(row.deceased_node_id for row in griefs),
            *(node for row in dreams for node in (*row.content, row.sender_node_id, row.partner_node_id, row.world_id, row.reader_node_id)),
        ]
        refs = await node_refs(session, [node for node in wanted if node is not None])
        totals: dict[Emotion, float] = {}
        for row in thoughts:
            totals[row.emotion] = totals.get(row.emotion, 0.0) + thought_strength(row, epoch)
        return FeelingsView(
            node_id=node_id,
            name=ref.name,
            applies=applies,
            locked=[field for field in (mind.locked or []) if field in FEELING_LOCKS] if mind is not None else [],
            lockable=list(FEELING_LOCKS) if applies and mind is not None else [],
            mood=profile.mood if profile is not None and applies else None,
            mood_score=profile.mood_score if profile is not None else 0,
            mood_held=profile is not None and "mood" in (profile.locked or []),
            thoughts=[
                ThoughtView(
                    id=row.id,
                    kind=row.kind,
                    label=THOUGHTS[row.kind].label,
                    emotion=row.emotion,
                    emotion_label=EMOTIONS[row.emotion].label,
                    valence=EMOTIONS[row.emotion].valence,
                    intensity=row.intensity,
                    strength=round(thought_strength(row, epoch)),
                    epoch=row.epoch,
                    decay_pct=row.decay_pct,
                    subject=refs.get(row.subject_node_id) if row.subject_node_id is not None else None,
                    formative=row.memory_id is not None,
                )
                for row in thoughts
            ],
            emotions=[
                EmotionTotalView(emotion=emotion, label=EMOTIONS[emotion].label, valence=EMOTIONS[emotion].valence, strength=round(total))
                for emotion, total in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
            ],
            formative=[
                FormativeView(
                    id=row.id, label=row.note or MEMORIES[row.kind].label, magnitude=row.magnitude, epoch=row.epoch, subject=refs.get(row.subject_node_id)
                )
                for row in formative
            ],
            griefs=[
                GriefView(
                    id=row.id,
                    deceased=refs.get(row.deceased_node_id),
                    stage=row.stage,
                    strength=row.strength,
                    started_epoch=row.started_epoch,
                    stage_epoch=row.stage_epoch,
                    length_epochs=row.length_epochs,
                )
                for row in griefs
            ],
            dreams=[
                DreamLogView(
                    id=row.id,
                    kind=row.kind,
                    label=DREAM_LABELS[row.kind],
                    epoch=row.epoch,
                    intensity=row.intensity,
                    content=[refs[node] for node in row.content if node in refs],
                    sender=refs.get(row.sender_node_id) if row.sender_node_id is not None else None,
                    partner=refs.get(row.partner_node_id) if row.partner_node_id is not None else None,
                    world=refs.get(row.world_id) if row.world_id is not None else None,
                    reading=row.reading,
                    reading_label=READING_LABELS[row.reading],
                    reader=refs.get(row.reader_node_id) if row.reader_node_id is not None else None,
                    reading_true=row.reading_true,
                    recurring=row.recurring,
                )
                for row in dreams
            ],
            thought_kinds=[ThoughtKindView(kind=kind, label=spec.label, emotion=spec.emotion) for kind, spec in THOUGHTS.items()] if applies else [],
            emotion_kinds=[EmotionKindView(emotion=emotion, label=spec.label, valence=spec.valence) for emotion, spec in EMOTIONS.items()] if applies else [],
            dream_kinds=[LabelView(key=kind.value, label=label) for kind, label in DREAM_LABELS.items()] if applies else [],
            readings=[LabelView(key=reading.value, label=label) for reading, label in READING_LABELS.items()] if applies else [],
            long_term_threshold=rules.thoughts.long_term_threshold,
        )
