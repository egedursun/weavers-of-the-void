from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.lore import (
    AdherentView,
    ArtworkCard,
    BookPage,
    BranchSpec,
    CastingView,
    CustomKinds,
    CustomKindView,
    CustomTechniqueView,
    DeedView,
    EnchantmentView,
    GateNeed,
    IdeologyCard,
    ItemCard,
    LearningCard,
    LevelView,
    LoreCard,
    ProphecyCard,
    RiteCard,
    RiteEffectView,
    RumourBoard,
    RumourView,
    TechGraph,
    TechniqueSpecView,
    TechniqueView,
    TongueAtlas,
    TongueRank,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.api.views.culture_cards import language_card, legend_card, registers_of_languages, tradition_card
from aerona.catalog.rumours import is_alarm, is_atrocity
from aerona.catalog.techniques import BRANCH_GRAPH, TECHNIQUES, Gate
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
    ItemEnchantmentRow,
    ItemHistoryRow,
    ItemProfileRow,
    LanguageIntelligibilityRow,
    LanguageStandingRow,
    ProphecyConditionRow,
    RiteEffectRow,
    RiteProfileRow,
    RumourRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CustomCatalog, Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.lore.kinds import kinds_in
from aerona.engine.lore.research import gate_open
from aerona.engine.lore.rumours import heard_by
from aerona.engine.primitives.knowledge import raw_level

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
    return ItemCard(
        item_class=row.item_class,
        material=row.material,
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
            TechniqueSpecView(technique=spec.technique, branch=spec.branch, level=spec.level, label=spec.label, effect=spec.effect, all_of=every, any_of=some)
        )
    return TechGraph(branches=branches, techniques=techniques)


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
                )
                for spec in TECHNIQUES.values()
            ],
            books=[refs[item] for item in books if item in refs],
            custom_techniques=[
                CustomTechniqueView(kind_id=kind.id, name=kind.name, base=Technique(kind.base), secret=secret) for kind, secret in customs.all()
            ],
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
