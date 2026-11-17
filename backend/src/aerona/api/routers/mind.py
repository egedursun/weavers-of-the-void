from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.mind import (
    AspirationsView,
    AttributeShiftView,
    AttributeView,
    BeliefShiftView,
    CareerView,
    CultureMindView,
    DreamLogView,
    EmotionKindView,
    EmotionTotalView,
    EthicView,
    FacetShiftView,
    FacetView,
    FearView,
    FeelingsView,
    FormativeView,
    GriefView,
    IdeaSpecView,
    IdeaView,
    InspirationView,
    LabelView,
    LifeDreamView,
    MemoryView,
    MilestoneView,
    MindNeedView,
    MindPressureView,
    MindSplitView,
    MindView,
    OpinionComponentView,
    OpinionMemoryView,
    OpinionTermView,
    OpinionView,
    PerkView,
    PreferenceKindView,
    PreferenceView,
    SkillView,
    SummaryView,
    ThoughtKindView,
    ThoughtView,
    TraitCapacityView,
    TraitEffectView,
    TraitView,
    ValueView,
    WantView,
)
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.aspirations import FEARS, FOCUSES, GOALS, INSPIRATION_LABELS, PERKS, WANTS
from aerona.catalog.ethics import ACT_LABELS, HONOUR_MODELS, STANCE_LABELS, STANCE_ORDER, STANCE_READINGS
from aerona.catalog.mind import FIXED_ROLES, MEMORIES, NEED_LABELS, PRESSURE_LABELS, SKILLS, TRAIT_FAMILY, TRAITS, VALUE_LABELS
from aerona.catalog.mind_split import ATTRIBUTES, FACETS, IDEAS, SKILL_ATTRIBUTES
from aerona.catalog.preferences import PREFERENCE_LABELS, SPECIES_KINDS, STATIC_TARGETS, target_label
from aerona.catalog.thoughts import DREAM_LABELS, EMOTIONS, NEEDS, READING_LABELS, THOUGHTS
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.culture_kinds import AimKindRow, FearKindRow, ReadingKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import (
    MIND_LOCKS,
    CultureHonourRow,
    DreamRow,
    FearRow,
    GriefRow,
    InspirationRow,
    LifeDreamRow,
    MemoryRow,
    PerkRow,
    TraitRow,
    WantRow,
)
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Emotion, IdeaKind, MemoryKind, PreferenceKind, ValueAxis, ValueHolder
from aerona.engine.body.book import factor
from aerona.engine.body.customs import people_of
from aerona.engine.mind.aspirations import focus_level
from aerona.engine.mind.book import Holder, holder_kind, load_holder, mind_of, needs_of, pressures_of, skills_of, stored_values, values_of
from aerona.engine.mind.ethics import culture_of, ethics_of
from aerona.engine.mind.ideas import fit, ideas_of
from aerona.engine.mind.memories import memories_of, strength_of
from aerona.engine.mind.opinion import Opinion, opinion
from aerona.engine.mind.preferences import rows_of
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
SECTION_LOCKS = frozenset({"thoughts", "griefs", "dreams", "attributes", "facets", "ideas", "preferences", "ethics", "aspirations", "relations", "passions"})
LOCKS_BY_HOLDER = {
    ValueHolder.PERSONAL: frozenset(MIND_LOCKS) - SECTION_LOCKS,
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
            family=TRAIT_FAMILY[row.trait],
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
                MindPressureView(pressure=kind_, label=PRESSURE_LABELS[kind_], value=value)
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
                    strain=row.strain,
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


async def need_views(session: AsyncSession, rules: Rules, node: Holder, node_id: int) -> list[MindNeedView]:
    facets = await facets_of(session, node_id)
    values = await values_of(session, node)
    return [
        MindNeedView(need=need, label=NEED_LABELS[need], value=value, group=NEEDS[need].group, importance=need_importance(rules, need, facets, values))
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
        reading_ids = [row.reading_kind_id for row in dreams if row.reading_kind_id is not None]
        reading_names = {row.id: row.name for row in await session.scalars(select(ReadingKindRow).where(ReadingKindRow.id.in_(reading_ids)))}
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
                    content=[refs[node] for node in dict.fromkeys(row.content) if node in refs],
                    sender=refs.get(row.sender_node_id) if row.sender_node_id is not None else None,
                    partner=refs.get(row.partner_node_id) if row.partner_node_id is not None else None,
                    world=refs.get(row.world_id) if row.world_id is not None else None,
                    reading=row.reading,
                    reading_name=reading_names.get(row.reading_kind_id) if row.reading_kind_id is not None else None,
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


@router.get("/minds/{node_id}/culture", response_model=CultureMindView)
async def culture_mind_view(services: ServicesDep, node_id: int = Path(ge=1)) -> CultureMindView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_MIND)
        entity = await session.get(EntityRow, node_id)
        kind = entity.entity_type if entity is not None else None
        has_preferences = kind in {EntityType.MORTAL, EntityType.PEOPLE}
        culture = await culture_of(session, node_id) if entity is not None else None
        has_ethics = culture is not None
        rows = await rows_of(session, node_id) if has_preferences else []
        targets = await node_refs(session, [row.target_node_id for row in rows if row.target_node_id is not None])
        ethics = await ethics_of(session, culture.id) if culture is not None else {}
        honour = await session.get(CultureHonourRow, culture.id) if culture is not None and culture.entity_type is EntityType.PEOPLE else None
        totem = await totem_species(session, node_id) if kind is EntityType.PEOPLE else None
        return CultureMindView(
            node_id=node_id,
            name=ref.name,
            has_preferences=has_preferences,
            has_ethics=has_ethics,
            ethics_holder=await node_ref(session, culture.id) if culture is not None else None,
            ethics_own=culture is not None and culture.id == node_id,
            preferences=[
                PreferenceView(
                    id=row.id,
                    kind=row.kind,
                    kind_label=PREFERENCE_LABELS[row.kind],
                    target=row.target,
                    target_label=targets[row.target_node_id].name if row.target_node_id in targets else target_label(row.kind, row.target),
                    target_node=targets.get(row.target_node_id) if row.target_node_id is not None else None,
                    strength=row.strength,
                    held="strength" in (row.locked or []),
                )
                for row in sorted(rows, key=lambda item: (list(PreferenceKind).index(item.kind), -item.strength))
            ],
            totem=await node_ref(session, totem) if totem is not None else None,
            ethics=[
                EthicView(
                    act=act,
                    label=ACT_LABELS[act],
                    stance=row.stance,
                    reading=STANCE_READINGS[row.stance],
                    since_epoch=row.since_epoch,
                    held="stance" in (row.locked or []),
                )
                for act, row in sorted(ethics.items(), key=lambda item: (STANCE_ORDER.index(item[1].stance), item[0].value))
            ],
            honour_model=honour.model if honour is not None else None,
            honour_label=HONOUR_MODELS[honour.model].label if honour is not None else None,
            honour_held=honour is not None and "model" in (honour.locked or []),
            preference_kinds=[
                PreferenceKindView(kind=pref, label=PREFERENCE_LABELS[pref], targets=list(STATIC_TARGETS.get(pref, ())), from_records=pref in SPECIES_KINDS)
                for pref in PreferenceKind
            ]
            if has_preferences
            else [],
            stances=[LabelView(key=stance.value, label=STANCE_LABELS[stance]) for stance in STANCE_ORDER],
            honour_models=[LabelView(key=model.value, label=spec.label) for model, spec in HONOUR_MODELS.items()],
        )


async def totem_species(session: AsyncSession, people_id: int) -> int | None:
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == people_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    origins = select(TraditionProfileRow.origin_entity_id).where(TraditionProfileRow.tradition_entity_id.in_(kept))
    return await session.scalar(select(EntityRow.id).where(EntityRow.id.in_(origins), EntityRow.entity_type == EntityType.SPECIES).limit(1))


@router.get("/minds/{node_id}/aspirations", response_model=AspirationsView)
async def aspirations_view(services: ServicesDep, node_id: int = Path(ge=1)) -> AspirationsView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_MIND)
        mortal = await session.get(EntityRow, node_id)
        applies = mortal is not None and mortal.entity_type is EntityType.MORTAL
        dream = await session.get(LifeDreamRow, node_id) if applies else None
        wants = (
            list(await session.scalars(select(WantRow).where(WantRow.holder_node_id == node_id).order_by(WantRow.epoch.desc(), WantRow.id))) if applies else []
        )
        fears = list(await session.scalars(select(FearRow).where(FearRow.holder_node_id == node_id).order_by(FearRow.strength.desc()))) if applies else []
        fear_ids = [row.fear_kind_id for row in fears if row.fear_kind_id is not None]
        fear_names = {row.id: row.name for row in await session.scalars(select(FearKindRow).where(FearKindRow.id.in_(fear_ids)))}
        aim = await session.get(AimKindRow, dream.aim_kind_id) if dream is not None and dream.aim_kind_id is not None else None
        sparks = (
            list(await session.scalars(select(InspirationRow).where(InspirationRow.holder_node_id == node_id).order_by(InspirationRow.started_epoch.desc())))
            if applies
            else []
        )
        owned = set(await session.scalars(select(PerkRow.perk).where(PerkRow.holder_node_id == node_id)))
        profile = await session.get(MortalProfileRow, node_id)
        mind = await mind_of(session, node_id)
        focus = profile.focus if profile is not None else None
        wanted_refs = [
            *(row.target_node_id for row in wants),
            *(row.target_node_id for row in fears),
            *(row.result_node_id for row in sparks),
            dream.target_node_id if dream else None,
        ]
        refs = await node_refs(session, [node for node in wanted_refs if node is not None])
        shown = [perk for perk, spec in PERKS.items() if spec.focus is focus or perk in owned]
        return AspirationsView(
            node_id=node_id,
            name=ref.name,
            applies=applies,
            locked=mind is not None and "aspirations" in (mind.locked or []),
            dream=LifeDreamView(
                goal=dream.goal,
                label=aim.name if aim is not None else GOALS[dream.goal].label,
                target=refs.get(dream.target_node_id) if dream.target_node_id is not None else None,
                milestones=[
                    MilestoneView(label=label, at=mark, reached=mark in dream.milestones)
                    for label, mark in zip(GOALS[dream.goal].milestones, (33, 66, 100), strict=True)
                ],
                progress=dream.progress,
                state=dream.state,
                started_epoch=dream.started_epoch,
                ended_epoch=dream.ended_epoch,
                held="progress" in (dream.locked or []),
            )
            if dream is not None
            else None,
            wants=[
                WantView(
                    id=row.id,
                    kind=row.kind,
                    label=WANTS[row.kind].label,
                    target=refs.get(row.target_node_id) if row.target_node_id is not None else None,
                    epoch=row.epoch,
                    fulfilled_epoch=row.fulfilled_epoch,
                    held="kind" in (row.locked or []),
                )
                for row in wants
            ],
            fears=[
                FearView(
                    id=row.id,
                    kind=row.kind,
                    label=fear_names.get(row.fear_kind_id, FEARS[row.kind].label) if row.fear_kind_id is not None else FEARS[row.kind].label,
                    strength=row.strength,
                    target=refs.get(row.target_node_id) if row.target_node_id is not None else None,
                    since_epoch=row.since_epoch,
                )
                for row in fears
            ],
            focus=focus,
            focus_held=profile is not None and "focus" in (profile.locked or []),
            focus_level=await focus_level(session, node_id, focus) if focus is not None else 0,
            perks=[
                PerkView(
                    perk=perk,
                    label=PERKS[perk].label,
                    focus=PERKS[perk].focus,
                    stat=PERKS[perk].stat,
                    amount=PERKS[perk].amount,
                    level=PERKS[perk].level,
                    owned=perk in owned,
                )
                for perk in shown
            ],
            inspirations=[
                InspirationView(
                    id=row.id,
                    kind=row.kind,
                    label=INSPIRATION_LABELS[row.kind],
                    material=row.material,
                    started_epoch=row.started_epoch,
                    deadline_epoch=row.deadline_epoch,
                    state=row.state,
                    result=refs.get(row.result_node_id) if row.result_node_id is not None else None,
                )
                for row in sparks
            ],
            conviction=profile.conviction if profile is not None else 50,
            conviction_held=profile is not None and "conviction" in (profile.locked or []),
            goals=[LabelView(key=goal.value, label=spec.label) for goal, spec in GOALS.items()],
            want_kinds=[LabelView(key=kind.value, label=spec.label) for kind, spec in WANTS.items()],
            fear_kinds=[LabelView(key=kind.value, label=spec.label) for kind, spec in FEARS.items()],
            focuses=[LabelView(key=kind.value, label=spec.label) for kind, spec in FOCUSES.items()],
            inspiration_kinds=[LabelView(key=kind.value, label=label) for kind, label in INSPIRATION_LABELS.items()],
        )
