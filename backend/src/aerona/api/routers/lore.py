from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.lore import (
    AdherentView,
    AnomalyView,
    ArtFormCard,
    ArtworkCard,
    BannedWorkView,
    BlueprintView,
    BookPage,
    BoostView,
    BranchSpec,
    CapabilitySpecView,
    CapabilityView,
    CastingView,
    CustomKinds,
    CustomKindView,
    CustomTechniqueView,
    DeedView,
    EnchantmentView,
    EpithetView,
    EraDeedView,
    ExonymView,
    FocusView,
    GateNeed,
    GreatPersonView,
    GreatPointsView,
    IdeologyCard,
    IncidentView,
    InstitutionView,
    ItemCard,
    LearningCard,
    LevelView,
    LoreCard,
    NameCard,
    NameView,
    PractitionerView,
    ProphecyCard,
    RealmEraView,
    RiteCard,
    RiteEffectView,
    RumourBoard,
    RumourView,
    ShiftView,
    StudyView,
    TechGraph,
    TechniqueSpecView,
    TechniqueView,
    TheoryAdherentView,
    TheoryCard,
    TongueAtlas,
    TongueRank,
    TriggerSpecView,
    WorldEraView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.api.views.culture_cards import language_card, legend_card, registers_of_languages, tradition_card
from aerona.catalog.civics import CAPABILITIES, TRIGGERS
from aerona.catalog.discovery import AGES, BLUEPRINT_KINDS, BLUEPRINT_SOURCES, DEEDS, FIELDS, INCIDENTS, era_name
from aerona.catalog.rumours import is_alarm, is_atrocity
from aerona.catalog.techniques import BRANCH_GRAPH, INSTITUTIONS, TECHNIQUES, Gate
from aerona.catalog.theories import ANOMALIES, DISCIPLINES, DOMAINS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import (
    ArtworkProfileRow,
    BookContentRow,
    CastingRow,
    CustomKindRow,
    HolderCustomTechniqueRow,
    HolderLevelRow,
    HolderTechniqueRow,
    IdeologyAdherentRow,
    IdeologyCustomTenetRow,
    IdeologyProfileRow,
    IdeologyTenetRow,
    InstitutionRow,
    ItemEnchantmentRow,
    ItemHistoryRow,
    ItemProfileRow,
    LanguageIntelligibilityRow,
    LanguageStandingRow,
    ProphecyConditionRow,
    ResearchBoostRow,
    ResearchFocusRow,
    ResearchProgressRow,
    RiteEffectRow,
    RiteProfileRow,
    RumourRow,
)
from aerona.db.tables.discovery import (
    ArtFormPractitionerRow,
    ArtFormProfileRow,
    ArtifactStudyRow,
    BannedWorkRow,
    BlueprintRow,
    EpithetRow,
    EraDeedRow,
    GreatPersonRow,
    GreatPointsRow,
    NameExonymRow,
    NameMeaningRow,
    ParadigmShiftRow,
    PolityEraRow,
    ResearchIncidentRow,
    TheoryAdherentRow,
    TheoryAnomalyRow,
    TheoryProfileRow,
    WorldEraRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CustomCatalog, Technique
from aerona.domain.enums.discovery import AgeKind
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.economy.materials import MaterialBook, node_material
from aerona.engine.lore.eras import leaders_share
from aerona.engine.lore.great_people import great_threshold
from aerona.engine.lore.kinds import kinds_in
from aerona.engine.lore.research import gate_open
from aerona.engine.lore.research_depth import capabilities_of
from aerona.engine.lore.rumours import heard_by
from aerona.engine.lore.theories import weight_against
from aerona.engine.primitives.knowledge import raw_level
from aerona.rules.registry import Rules

router = APIRouter(tags=["lore"])
Id = Annotated[int, Path(ge=1)]
Refs = dict[int, NodeRef]
SAME = 100


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def ideology_card(session: AsyncSession, entity_id: int) -> IdeologyCard | None:
    row = await session.get(IdeologyProfileRow, entity_id)
    if row is None:
        return None
    tenets = list(
        await session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == entity_id).order_by(IdeologyTenetRow.tenet))
    )
    adherents = list(
        await session.scalars(
            select(IdeologyAdherentRow)
            .where(IdeologyAdherentRow.ideology_entity_id == entity_id)
            .order_by(IdeologyAdherentRow.strength.desc(), IdeologyAdherentRow.adherent_entity_id)
        )
    )
    refs = await node_refs(session, [*(item.adherent_entity_id for item in adherents), *row.texts, *([row.founder_entity_id] if row.founder_entity_id else [])])
    customs = list(await session.scalars(select(IdeologyCustomTenetRow.kind_id).where(IdeologyCustomTenetRow.ideology_entity_id == entity_id)))
    return IdeologyCard(
        founder=ref(refs, row.founder_entity_id),
        tenets=tenets,
        appeal=row.appeal,
        values=row.value_delta,
        adherents=[
            AdherentView(community=ref(refs, item.adherent_entity_id), strength=item.strength, state=item.state, since_epoch=item.since_epoch)
            for item in adherents
        ],
        texts=[refs[item] for item in row.texts if item in refs],
        custom_tenets=customs,
        locked=row.locked,
    )


async def theory_card(session: AsyncSession, entity_id: int) -> TheoryCard | None:
    row = await session.get(TheoryProfileRow, entity_id)
    if row is None:
        return None
    adherents = list(
        await session.scalars(
            select(TheoryAdherentRow)
            .where(TheoryAdherentRow.theory_entity_id == entity_id)
            .order_by(TheoryAdherentRow.orthodox.desc(), TheoryAdherentRow.strength.desc())
        )
    )
    anomalies = list(
        await session.scalars(
            select(TheoryAnomalyRow).where(TheoryAnomalyRow.theory_entity_id == entity_id).order_by(TheoryAnomalyRow.epoch.desc(), TheoryAnomalyRow.id.desc())
        )
    )
    shifts = list(
        await session.scalars(
            select(ParadigmShiftRow)
            .where((ParadigmShiftRow.old_theory_id == entity_id) | (ParadigmShiftRow.new_theory_id == entity_id))
            .order_by(ParadigmShiftRow.epoch.desc(), ParadigmShiftRow.id.desc())
        )
    )
    ids = [
        *(item.adherent_entity_id for item in adherents),
        *(item.witness_entity_id for item in anomalies if item.witness_entity_id is not None),
        *(node for item in shifts for node in (item.community_entity_id, item.old_theory_id, item.new_theory_id) if node is not None),
        *row.endorsed_by,
        *row.condemned_by,
        *(node for node in (row.founder_entity_id, row.founding_book_id, row.rival_entity_id) if node is not None),
    ]
    refs = await node_refs(session, ids)
    rules = Rules()
    pressure = await weight_against(session, rules, entity_id, max((item.epoch for item in anomalies), default=0))
    return TheoryCard(
        domain=row.domain,
        domain_label=DOMAINS[row.domain].label,
        subject=DOMAINS[row.domain].subject,
        claim=row.claim,
        correctness=row.correctness,
        explanatory_power=row.explanatory_power,
        pressure=pressure,
        founder=ref(refs, row.founder_entity_id),
        founding_book=ref(refs, row.founding_book_id),
        rival=ref(refs, row.rival_entity_id),
        endorsed_by=[refs[item] for item in row.endorsed_by if item in refs],
        condemned_by=[refs[item] for item in row.condemned_by if item in refs],
        revealed_by_son_id=row.revealed_by_son_id,
        adherents=[
            TheoryAdherentView(
                holder=refs[item.adherent_entity_id], strength=item.strength, orthodox=item.orthodox, since_epoch=item.since_epoch, locked=item.locked
            )
            for item in adherents
            if item.adherent_entity_id in refs
        ],
        anomalies=[
            AnomalyView(id=item.id, kind=item.kind, label=ANOMALIES[item.kind], weight=item.weight, epoch=item.epoch, witness=ref(refs, item.witness_entity_id))
            for item in anomalies
        ],
        shifts=[
            ShiftView(
                id=item.id,
                community=ref(refs, item.community_entity_id),
                old=ref(refs, item.old_theory_id),
                new=ref(refs, item.new_theory_id),
                epoch=item.epoch,
            )
            for item in shifts
        ],
        locked=row.locked,
    )


async def art_form_card(session: AsyncSession, entity_id: int) -> ArtFormCard | None:
    row = await session.get(ArtFormProfileRow, entity_id)
    if row is None:
        return None
    practitioners = list(
        await session.scalars(
            select(ArtFormPractitionerRow).where(ArtFormPractitionerRow.art_form_entity_id == entity_id).order_by(ArtFormPractitionerRow.mastery.desc())
        )
    )
    artworks = list(await session.scalars(select(ArtworkProfileRow.artwork_entity_id).where(ArtworkProfileRow.art_form_entity_id == entity_id)))
    banned = list(await session.scalars(select(BannedWorkRow.polity_entity_id).where(BannedWorkRow.work_entity_id == entity_id)))
    children = [item.art_form_entity_id for item in await session.scalars(select(ArtFormProfileRow)) if entity_id in (item.parent_ids or [])]
    ids = [
        *(item.practitioner_entity_id for item in practitioners),
        *artworks,
        *banned,
        *row.parent_ids,
        *children,
        *(node for node in (row.origin_culture_id, row.founder_entity_id, row.language_entity_id) if node is not None),
    ]
    refs = await node_refs(session, ids)
    return ArtFormCard(
        discipline=row.discipline,
        discipline_label=DISCIPLINES[row.discipline].label,
        structure=row.structure,
        parts=list(DISCIPLINES[row.discipline].structure),
        origin=ref(refs, row.origin_culture_id),
        founder=ref(refs, row.founder_entity_id),
        language=ref(refs, row.language_entity_id),
        difficulty=row.difficulty,
        prestige=row.prestige,
        sacred=row.sacred,
        notation=row.notation,
        occasions=row.occasions,
        parents=[refs[item] for item in row.parent_ids if item in refs],
        children=[refs[item] for item in children if item in refs],
        practitioners=[
            PractitionerView(holder=refs[item.practitioner_entity_id], mastery=item.mastery, since_epoch=item.since_epoch, locked=item.locked)
            for item in practitioners
            if item.practitioner_entity_id in refs
        ],
        artworks=[refs[item] for item in artworks if item in refs],
        banned_in=[refs[item] for item in banned if item in refs],
        locked=row.locked,
    )


async def rite_card(session: AsyncSession, entity_id: int) -> RiteCard | None:
    row = await session.get(RiteProfileRow, entity_id)
    if row is None:
        return None
    effects = list(await session.scalars(select(RiteEffectRow).where(RiteEffectRow.rite_entity_id == entity_id).order_by(RiteEffectRow.effect)))
    castings = list(
        await session.scalars(select(CastingRow).where(CastingRow.rite_entity_id == entity_id).order_by(CastingRow.epoch.desc(), CastingRow.id.desc()))
    )
    ids = [*(item.caster_entity_id for item in castings if item.caster_entity_id), *(item.target_entity_id for item in castings if item.target_entity_id)]
    refs = await node_refs(session, [*ids, *row.forbidden_by, *([row.inventor_entity_id] if row.inventor_entity_id else [])])
    return RiteCard(
        school=row.school,
        source=row.source,
        requirements=row.requirements,
        cost=row.cost,
        power=row.power,
        backlash_chance=row.backlash_chance,
        backlash=row.backlash,
        holy=row.holy,
        heretical=row.heretical,
        inventor=ref(refs, row.inventor_entity_id),
        effects=[
            RiteEffectView(
                effect=item.effect,
                magnitude=item.magnitude,
                detail=item.detail,
                damage_type=item.damage_type,
                summon_form=item.summon_form,
                custom_kind_id=item.custom_kind_id,
            )
            for item in effects
        ],
        forbidden_by=[refs[item] for item in row.forbidden_by if item in refs],
        castings=[
            CastingView(
                id=item.id,
                caster=ref(refs, item.caster_entity_id),
                target=ref(refs, item.target_entity_id),
                epoch=item.epoch,
                succeeded=item.succeeded,
                backlash=item.backlash,
                effect=item.effect,
            )
            for item in castings
        ],
        locked=row.locked,
    )


async def prophecy_card(session: AsyncSession, entity_id: int) -> ProphecyCard | None:
    row = await session.get(ProphecyConditionRow, entity_id)
    if row is None:
        return None
    refs = await node_refs(session, [*row.audience, *(item for item in (row.seer_entity_id, row.consequence_entity_id) if item)])
    return ProphecyCard(
        predicate=row.predicate,
        args=row.args,
        deadline_epoch=row.deadline_epoch,
        seer=ref(refs, row.seer_entity_id),
        audience=[refs[item] for item in row.audience if item in refs],
        pressure=row.pressure,
        state=row.state,
        resolved_epoch=row.resolved_epoch,
        consequence_kind=row.consequence_kind,
        consequence=ref(refs, row.consequence_entity_id),
        locked=row.locked,
    )


async def item_card(session: AsyncSession, entity_id: int) -> ItemCard | None:
    row = await session.get(ItemProfileRow, entity_id)
    if row is None:
        return None
    history = list(
        await session.scalars(select(ItemHistoryRow).where(ItemHistoryRow.item_entity_id == entity_id).order_by(ItemHistoryRow.epoch, ItemHistoryRow.id))
    )
    spells = list(await session.scalars(select(ItemEnchantmentRow).where(ItemEnchantmentRow.item_entity_id == entity_id).order_by(ItemEnchantmentRow.effect)))
    pages = list(await session.scalars(select(BookContentRow).where(BookContentRow.book_entity_id == entity_id)))
    contents = [page.knowledge_entity_id for page in pages]
    owner = await session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    extra = [item for item in (row.maker_entity_id, row.regalia_of_entity_id, owner, row.bound_spirit_entity_id) if item is not None]
    refs = await node_refs(
        session,
        [
            *extra,
            *(item.actor_entity_id for item in history if item.actor_entity_id),
            *(item.rite_entity_id for item in spells if item.rite_entity_id),
            *contents,
        ],
    )
    body = await node_material(session, entity_id, MaterialSlot.BODY)
    item = await session.get(EntityRow, entity_id)
    props = (await MaterialBook.load(session)).props(item.world_id if item is not None else None, body.material, body.world_material_id) if body else None
    return ItemCard(
        item_class=row.item_class,
        material=props.label if props is not None else None,
        quality=row.quality,
        condition=row.condition,
        damage_type=row.damage_type,
        reach=row.reach,
        coverage=row.coverage,
        weight=row.weight,
        curse=row.curse,
        value=row.value,
        renown=row.renown,
        maker=ref(refs, row.maker_entity_id),
        owner=ref(refs, owner),
        regalia_of=ref(refs, row.regalia_of_entity_id),
        symbol=row.symbol,
        history=[DeedView(id=item.id, epoch=item.epoch, deed=item.deed, actor=ref(refs, item.actor_entity_id), note=item.note) for item in history],
        enchantments=[
            EnchantmentView(effect=item.effect, strength=item.strength, rite=ref(refs, item.rite_entity_id), since_epoch=item.since_epoch) for item in spells
        ],
        contents=[refs[item] for item in contents if item in refs],
        secondary_materials=row.secondary_materials,
        bound_spirit=ref(refs, row.bound_spirit_entity_id),
        prosthesis_for=row.prosthesis_for,
        custom_class_id=row.custom_class_id,
        book_contents=[BookPage(knowledge=ref(refs, page.knowledge_entity_id), fidelity=page.fidelity) for page in pages],
        locked=row.locked,
    )


async def artwork_card(session: AsyncSession, entity_id: int) -> ArtworkCard | None:
    row = await session.get(ArtworkProfileRow, entity_id)
    if row is None:
        return None
    ids = [item for item in (row.author_entity_id, row.patron_entity_id, row.subject_node_id, row.language_entity_id) if item is not None]
    refs = await node_refs(session, [*ids, *row.translations])
    return ArtworkCard(
        medium=row.medium,
        performed=row.performed,
        author=ref(refs, row.author_entity_id),
        patron=ref(refs, row.patron_entity_id),
        subject=ref(refs, row.subject_node_id),
        message=row.message,
        quality=row.quality,
        copies=row.copies,
        language=ref(refs, row.language_entity_id),
        translations=[refs[item] for item in row.translations if item in refs],
        propaganda=row.propaganda,
        canon=row.canon,
        locked=row.locked,
    )


CARDS: dict[EntityType, tuple[str, Callable[[AsyncSession, int], Awaitable[object]]]] = {
    EntityType.LANGUAGE: ("language", language_card),
    EntityType.LEGEND: ("legend", legend_card),
    EntityType.TRADITION: ("tradition", tradition_card),
    EntityType.IDEOLOGY: ("ideology", ideology_card),
    EntityType.RITE: ("rite", rite_card),
    EntityType.PROPHECY: ("prophecy", prophecy_card),
    EntityType.ITEM: ("item", item_card),
    EntityType.ARTWORK: ("artwork", artwork_card),
    EntityType.THEORY: ("theory", theory_card),
    EntityType.ART_FORM: ("art_form", art_form_card),
}


@router.get("/entities/{entity_id}/lore", response_model=LoreCard)
async def lore_card(entity_id: Id, services: ServicesDep) -> LoreCard:
    async with reader(services) as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        card = LoreCard(entity_id=entity_id)
        found = CARDS.get(entity.entity_type)
        if found is not None:
            setattr(card, found[0], await found[1](session, entity_id))
        return card


def needs(gate: Gate) -> tuple[list[GateNeed], list[GateNeed]]:
    return [GateNeed(branch=branch, level=level) for branch, level in gate.all_of], [GateNeed(branch=branch, level=level) for branch, level in gate.any_of]


@router.get("/techniques", response_model=TechGraph)
async def tech_graph() -> TechGraph:
    branches = []
    for branch, gate in BRANCH_GRAPH.items():
        every, some = needs(gate)
        branches.append(BranchSpec(branch=branch, all_of=every, any_of=some))
    techniques = []
    for spec in TECHNIQUES.values():
        every, some = needs(spec.gate)
        techniques.append(
            TechniqueSpecView(
                technique=spec.technique,
                branch=spec.branch,
                level=spec.level,
                label=spec.label,
                effect=spec.effect,
                all_of=every,
                any_of=some,
                institution=spec.technique in INSTITUTIONS,
            )
        )
    return TechGraph(
        branches=branches,
        techniques=techniques,
        triggers=[TriggerSpecView(trigger=trigger, label=spec.label, techniques=list(spec.techniques)) for trigger, spec in TRIGGERS.items()],
        capabilities=[
            CapabilitySpecView(
                capability=capability,
                label=spec.label,
                effect=spec.effect,
                branches=[GateNeed(branch=branch, level=level) for branch, level in spec.branches],
                all_of=list(spec.all_of),
                any_of=list(spec.any_of),
            )
            for capability, spec in CAPABILITIES.items()
        ],
    )


@router.get("/entities/{entity_id}/learning", response_model=LearningCard)
async def learning(entity_id: Id, services: ServicesDep) -> LearningCard:
    async with reader(services) as session:
        rows = list(await session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == entity_id).order_by(HolderLevelRow.branch)))
        held = {item.technique: item for item in await session.scalars(select(HolderTechniqueRow).where(HolderTechniqueRow.holder_entity_id == entity_id))}
        levels = {item.branch: item.level for item in rows}
        owned = select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        books = list(await session.scalars(select(BookContentRow.book_entity_id).where(BookContentRow.book_entity_id.in_(owned)).distinct()))
        refs = await node_refs(session, books)
        frontiers: dict[KnowledgeBranch, int] = {}
        for record in await session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON, EntityRow.knowledge_branch.is_not(None)
            )
        ):
            if record.knowledge_branch is not None:
                frontiers[record.knowledge_branch] = max(frontiers.get(record.knowledge_branch, 0), raw_level(record.stats))
        progress = {
            item.technique: item.progress
            for item in await session.scalars(select(ResearchProgressRow).where(ResearchProgressRow.holder_entity_id == entity_id))
        }
        focus = await session.get(ResearchFocusRow, entity_id)
        founded = await session.scalars(select(InstitutionRow).where(InstitutionRow.community_entity_id == entity_id).order_by(InstitutionRow.technique))
        boosts = await session.scalars(select(ResearchBoostRow).where(ResearchBoostRow.holder_entity_id == entity_id).order_by(ResearchBoostRow.id))
        able = set(await capabilities_of(session, entity_id))
        holder_row = await session.get(EntityRow, entity_id)
        needed = await great_threshold(session, await world_rules(services, session), holder_row.world_id if holder_row is not None else None)
        points = list(await session.scalars(select(GreatPointsRow).where(GreatPointsRow.holder_entity_id == entity_id).order_by(GreatPointsRow.field)))
        greats = list(await session.scalars(select(GreatPersonRow).where(GreatPersonRow.holder_entity_id == entity_id).order_by(GreatPersonRow.promoted_epoch)))
        incidents = list(
            await session.scalars(
                select(ResearchIncidentRow).where(ResearchIncidentRow.holder_entity_id == entity_id).order_by(ResearchIncidentRow.epoch.desc())
            )
        )
        studies = list(await session.scalars(select(ArtifactStudyRow).where(ArtifactStudyRow.holder_entity_id == entity_id).order_by(ArtifactStudyRow.epoch)))
        designs = list(await session.scalars(select(BlueprintRow).where(BlueprintRow.holder_node_id == entity_id).order_by(BlueprintRow.id)))
        linked = await node_refs(
            session,
            [row.mortal_entity_id for row in greats] + [row.item_entity_id for row in studies] + [node for row in designs for node in row.licensed_to or []],
        )
        customs = await session.execute(
            select(CustomKindRow, HolderCustomTechniqueRow.secret)
            .join(HolderCustomTechniqueRow, HolderCustomTechniqueRow.kind_id == CustomKindRow.id)
            .where(HolderCustomTechniqueRow.holder_entity_id == entity_id)
        )
        return LearningCard(
            holder_id=entity_id,
            levels=[
                LevelView(
                    branch=item.branch,
                    level=item.level,
                    practitioners=item.practitioners,
                    progress=item.progress,
                    secret=item.secret,
                    open=gate_open(BRANCH_GRAPH.get(item.branch, Gate()), levels),
                    frontier=frontiers.get(item.branch, item.level),
                    locked=item.locked,
                )
                for item in rows
            ],
            techniques=[
                TechniqueView(
                    technique=spec.technique,
                    branch=spec.branch,
                    level=spec.level,
                    label=spec.label,
                    effect=spec.effect,
                    known=spec.technique in held,
                    secret=spec.technique in held and held[spec.technique].secret,
                    reachable=levels.get(spec.branch, 0) >= spec.level and gate_open(spec.gate, levels),
                    institution=spec.technique in INSTITUTIONS,
                    progress=progress.get(spec.technique, 0),
                )
                for spec in TECHNIQUES.values()
            ],
            focus=FocusView(
                technique=focus.technique,
                chooser=focus.chooser,
                options=[Technique(item) for item in focus.options if item in Technique._value2member_map_],
                epoch=focus.epoch,
                locked=focus.locked,
            )
            if focus is not None
            else None,
            institutions=[
                InstitutionView(
                    technique=item.technique,
                    origin=item.origin,
                    embraced=item.embraced,
                    since_epoch=item.since_epoch,
                    refused_epochs=item.refused_epochs,
                    locked=item.locked,
                )
                for item in founded
            ],
            boosts=[BoostView(id=item.id, technique=item.technique, trigger=item.trigger, progress=item.progress, epoch=item.epoch) for item in boosts],
            capabilities=[
                CapabilityView(capability=capability, label=spec.label, effect=spec.effect, held=capability in able)
                for capability, spec in CAPABILITIES.items()
            ],
            great_points=[
                GreatPointsView(field=row.field, label=FIELDS[row.field].label, points=row.points, threshold=needed, locked=row.locked) for row in points
            ],
            great_people=[
                GreatPersonView(
                    mortal=linked[row.mortal_entity_id],
                    field=row.field,
                    label=FIELDS[row.field].label,
                    deed=FIELDS[row.field].deed,
                    promoted_epoch=row.promoted_epoch,
                    deed_done=row.deed_done,
                    deed_epoch=row.deed_epoch,
                    locked=row.locked,
                )
                for row in greats
                if row.mortal_entity_id in linked
            ],
            incidents=[
                IncidentView(
                    id=row.id,
                    kind=row.kind,
                    label=INCIDENTS[row.kind],
                    technique=row.technique,
                    branch=row.branch,
                    severity=row.severity,
                    dead=row.dead,
                    epoch=row.epoch,
                )
                for row in incidents
            ],
            studies=[
                StudyView(item=linked[row.item_entity_id], technique=row.technique, progress=row.progress, epoch=row.epoch, locked=row.locked)
                for row in studies
                if row.item_entity_id in linked
            ],
            designs=[
                BlueprintView(
                    id=row.id,
                    name=row.name,
                    kind=row.kind,
                    kind_label=BLUEPRINT_KINDS[row.kind],
                    subject=row.subject,
                    source=row.source,
                    source_label=BLUEPRINT_SOURCES[row.source],
                    quality=row.quality,
                    licensed_to=[linked[node] for node in row.licensed_to or [] if node in linked],
                    since_epoch=row.since_epoch,
                    locked=row.locked,
                )
                for row in designs
            ],
            books=[refs[item] for item in books if item in refs],
            custom_techniques=[
                CustomTechniqueView(kind_id=kind.id, name=kind.name, base=Technique(kind.base), secret=secret) for kind, secret in customs.all()
            ],
        )


@router.get("/nodes/{node_id}/name", response_model=NameCard)
async def name_card(node_id: Id, services: ServicesDep) -> NameCard:
    async with reader(services) as session:
        meaning = await session.get(NameMeaningRow, node_id)
        exonyms = list(await session.scalars(select(NameExonymRow).where(NameExonymRow.node_id == node_id).order_by(NameExonymRow.language_entity_id)))
        epithet = await session.get(EpithetRow, node_id)
        languages = [item.language_entity_id for item in exonyms] + [
            node for node in (meaning.language_entity_id if meaning else None, epithet.language_entity_id if epithet else None) if node is not None
        ]
        refs = await node_refs(session, languages)
        own = (await node_refs(session, [node_id])).get(node_id)
        entity = await session.get(EntityRow, node_id)
        return NameCard(
            node_id=node_id,
            current_name=own.name if own is not None else "",
            epithets_allowed=entity is not None,
            meaning=NameView(
                node_id=node_id,
                name=meaning.name,
                language=ref(refs, meaning.language_entity_id),
                gloss=meaning.gloss,
                morphemes=meaning.morphemes,
                epoch=meaning.epoch,
                locked=meaning.locked,
            )
            if meaning is not None
            else None,
            exonyms=[
                ExonymView(language=refs[item.language_entity_id], form=item.form, gloss=item.gloss, epoch=item.epoch, locked=item.locked)
                for item in exonyms
                if item.language_entity_id in refs
            ],
            epithet=EpithetView(
                epithet=epithet.epithet,
                gloss=epithet.gloss,
                deed=epithet.deed,
                language=ref(refs, epithet.language_entity_id),
                epoch=epithet.epoch,
                locked=epithet.locked,
            )
            if epithet is not None
            else None,
        )


@router.get("/polities/{polity_id}/era", response_model=RealmEraView)
async def realm_era(polity_id: Id, services: ServicesDep) -> RealmEraView:
    async with reader(services) as session:
        table = (await world_rules(services, session)).discovery
        row = await session.get(PolityEraRow, polity_id)
        deeds = list(
            await session.scalars(select(EraDeedRow).where(EraDeedRow.polity_entity_id == polity_id).order_by(EraDeedRow.epoch.desc(), EraDeedRow.id.desc()))
        )
        banned = list(await session.scalars(select(BannedWorkRow).where(BannedWorkRow.polity_entity_id == polity_id).order_by(BannedWorkRow.since_epoch)))
        refs = await node_refs(session, [deed.subject_node_id for deed in deeds if deed.subject_node_id is not None] + [item.work_entity_id for item in banned])
        age = row.age if row is not None else AgeKind.NORMAL
        return RealmEraView(
            polity_id=polity_id,
            score=row.score if row is not None else 0,
            age=age,
            age_label=AGES[age],
            since_epoch=row.since_epoch if row is not None else 0,
            lowest=row.lowest if row is not None else 0,
            golden_at=table.golden_at,
            dark_at=table.dark_at,
            locked=row.locked if row is not None else [],
            deeds=[
                EraDeedView(
                    id=deed.id,
                    deed=deed.deed,
                    label=DEEDS[deed.deed],
                    points=deed.points,
                    epoch=deed.epoch,
                    subject=refs.get(deed.subject_node_id) if deed.subject_node_id is not None else None,
                )
                for deed in deeds
            ],
            banned=[
                BannedWorkView(work=refs[item.work_entity_id], since_epoch=item.since_epoch, locked=item.locked)
                for item in banned
                if item.work_entity_id in refs
            ],
        )


@router.get("/worlds/{world_id}/era", response_model=WorldEraView)
async def world_era(world_id: Id, services: ServicesDep) -> WorldEraView:
    async with reader(services) as session:
        table = (await world_rules(services, session)).discovery
        row = await session.get(WorldEraRow, world_id)
        era = row.era if row is not None else 1
        top = max(spec.level for spec in TECHNIQUES.values())
        share = await leaders_share(session, world_id, era + 1, table.era_leaders) if era < top else 1.0
        return WorldEraView(
            world_id=world_id,
            era=era,
            name=era_name(era),
            top=top,
            since_epoch=row.since_epoch if row is not None else 0,
            next_share=round(share * PERCENT),
            locked=row.locked if row is not None else [],
        )


@router.get("/worlds/{world_id}/tongues", response_model=TongueAtlas)
async def tongues(world_id: Id, services: ServicesDep) -> TongueAtlas:
    async with reader(services) as session:
        languages = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        ids = [item.id for item in languages]
        standings = {
            item.language_entity_id: item for item in await session.scalars(select(LanguageStandingRow).where(LanguageStandingRow.language_entity_id.in_(ids)))
        }
        pairs = {
            (item.first_entity_id, item.second_entity_id): item.value
            for item in await session.scalars(select(LanguageIntelligibilityRow).where(LanguageIntelligibilityRow.first_entity_id.in_(ids)))
        }
        voices: dict[int, int] = {}
        for target in await session.scalars(
            select(BondRow.target_node_id).where(BondRow.target_node_id.in_(ids), BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
        ):
            voices[target] = voices.get(target, 0) + 1
        refs = await node_refs(session, ids)
        ranked = sorted(languages, key=lambda item: (-(standings[item.id].prestige if item.id in standings else 0), item.id))
        order = [item.id for item in ranked]
        matrix = [[SAME if one == other else pairs.get((min(one, other), max(one, other)), 0) for other in order] for one in order]
        return TongueAtlas(
            ranking=[
                TongueRank(
                    language=refs[item.id],
                    prestige=standings[item.id].prestige if item.id in standings else 0,
                    lingua_franca=item.id in standings and standings[item.id].lingua_franca,
                    liturgical=item.id in standings and standings[item.id].liturgical,
                    speakers=voices.get(item.id, 0),
                )
                for item in ranked
                if item.id in refs
            ],
            matrix=matrix,
            registers=await registers_of_languages(session, ids),
        )


@router.get("/custom-kinds", response_model=CustomKinds)
async def custom_kinds(services: ServicesDep, catalog: Annotated[CustomCatalog, Query()], world_id: Annotated[int | None, Query(ge=1)] = None) -> CustomKinds:
    async with reader(services) as session:
        return CustomKinds(
            kinds=[
                CustomKindView(
                    id=row.id,
                    catalog=row.catalog,
                    base=row.base,
                    name=row.name,
                    description=row.description,
                    params=row.params,
                    world_id=row.world_id,
                    created_epoch=row.created_epoch,
                )
                for row in await kinds_in(session, catalog, world_id)
            ]
        )


@router.get("/entities/{entity_id}/rumours", response_model=RumourBoard)
async def rumours(entity_id: Id, services: ServicesDep) -> RumourBoard:
    async with reader(services) as session:
        heard = await heard_by(session, entity_id)
        incident_ids = sorted({incident.id for _, incident, _ in heard})
        spread: dict[int, int] = {}
        if incident_ids:
            for incident_id in await session.scalars(select(RumourRow.incident_id).where(RumourRow.incident_id.in_(incident_ids))):
                spread[incident_id] = spread.get(incident_id, 0) + 1
        refs = await node_refs(
            session,
            [item for rumour, _, _ in heard for item in (rumour.source_entity_id, rumour.legend_entity_id) if item is not None],
        )
        return RumourBoard(
            community_id=entity_id,
            rumours=[
                RumourView(
                    id=rumour.id,
                    incident_id=incident.id,
                    text=text,
                    kind=incident.kind,
                    happened_epoch=incident.epoch,
                    fidelity=rumour.fidelity,
                    channel=rumour.channel,
                    hops=rumour.hops,
                    heard_epoch=rumour.epoch,
                    lingered=rumour.lingered,
                    source=ref(refs, rumour.source_entity_id),
                    legend=ref(refs, rumour.legend_entity_id),
                    planted=rumour.planted,
                    atrocity=is_atrocity(incident.kind),
                    alarm=is_alarm(incident.kind),
                    carriers=spread.get(incident.id, 1),
                    locked=rumour.locked,
                )
                for rumour, incident, text in heard
            ],
        )
