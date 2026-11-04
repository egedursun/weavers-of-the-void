from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.lore import (
    AdherentView,
    ArtworkCard,
    BranchSpec,
    CastingView,
    DeedView,
    EnchantmentView,
    GateNeed,
    IdeologyCard,
    ItemCard,
    KeeperView,
    KinView,
    LanguageCard,
    LearningCard,
    LegendCard,
    LevelView,
    LoreCard,
    ProphecyCard,
    RiteCard,
    RiteEffectView,
    SpeakerView,
    TechGraph,
    TechniqueSpecView,
    TechniqueView,
    TongueAtlas,
    TongueRank,
    TraditionCard,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.techniques import BRANCH_GRAPH, TECHNIQUES, Gate
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import (
    ArtworkProfileRow,
    BookContentRow,
    CastingRow,
    HolderLevelRow,
    HolderTechniqueRow,
    IdeologyAdherentRow,
    IdeologyProfileRow,
    IdeologyTenetRow,
    ItemEnchantmentRow,
    ItemHistoryRow,
    ItemProfileRow,
    LanguageIntelligibilityRow,
    LanguageStandingRow,
    LegendProfileRow,
    ProphecyConditionRow,
    RiteEffectRow,
    RiteProfileRow,
    SpeakerCohortRow,
    TraditionParticipationRow,
    TraditionProfileRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.economy.materials import MaterialBook, node_material
from aerona.engine.lore.research import gate_open

router = APIRouter(tags=["lore"])
Id = Annotated[int, Path(ge=1)]
Refs = dict[int, NodeRef]
SAME = 100


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def language_card(session: AsyncSession, entity_id: int) -> LanguageCard | None:
    row = await session.get(LanguageStandingRow, entity_id)
    if row is None:
        return None
    cohorts = list(
        await session.scalars(select(SpeakerCohortRow).where(SpeakerCohortRow.language_entity_id == entity_id).order_by(SpeakerCohortRow.community_entity_id))
    )
    kin = list(
        await session.scalars(
            select(LanguageIntelligibilityRow)
            .where((LanguageIntelligibilityRow.first_entity_id == entity_id) | (LanguageIntelligibilityRow.second_entity_id == entity_id))
            .order_by(LanguageIntelligibilityRow.value.desc())
        )
    )
    others = [item.second_entity_id if item.first_entity_id == entity_id else item.first_entity_id for item in kin]
    refs = await node_refs(session, [*(item.community_entity_id for item in cohorts), *others])
    return LanguageCard(
        prestige=row.prestige,
        prestige_parts=row.prestige_parts,
        standardisation=row.standardisation,
        liturgical=row.liturgical,
        lingua_franca=row.lingua_franca,
        speakers=[
            SpeakerView(community=ref(refs, item.community_entity_id), kind=item.kind, share=item.share, since_epoch=item.since_epoch) for item in cohorts
        ],
        kin=[KinView(language=ref(refs, other), value=item.value) for item, other in zip(kin, others, strict=True)],
        locked=row.locked,
    )


async def legend_card(session: AsyncSession, entity_id: int) -> LegendCard | None:
    row = await session.get(LegendProfileRow, entity_id)
    if row is None:
        return None
    refs = await node_refs(session, [*row.tellers, *(item for item in (row.subject_node_id, row.fixed_in_entity_id) if item is not None)])
    return LegendCard(
        archetype=row.archetype,
        credence=row.credence,
        distortion=row.distortion,
        subject=ref(refs, row.subject_node_id),
        moral=row.moral,
        tellers=[refs[item] for item in row.tellers if item in refs],
        fixed_in=ref(refs, row.fixed_in_entity_id),
        locked=row.locked,
    )


async def tradition_card(session: AsyncSession, entity_id: int) -> TraditionCard | None:
    row = await session.get(TraditionProfileRow, entity_id)
    if row is None:
        return None
    keepers = list(
        await session.scalars(
            select(TraditionParticipationRow)
            .where(TraditionParticipationRow.tradition_entity_id == entity_id)
            .order_by(TraditionParticipationRow.community_entity_id)
        )
    )
    refs = await node_refs(session, [*(item.community_entity_id for item in keepers), *([row.origin_entity_id] if row.origin_entity_id else [])])
    return TraditionCard(
        kind=row.kind,
        calendar_slot=row.calendar_slot,
        season_position=row.season_position,
        calendar_entity_id=row.calendar_entity_id,
        notable_year_id=row.notable_year_id,
        in_season=row.in_season,
        cost=row.cost,
        effects=row.effects,
        taboo_target=row.taboo_target,
        origin=ref(refs, row.origin_entity_id),
        keepers=[
            KeeperView(
                community=ref(refs, item.community_entity_id),
                participation=item.participation,
                skipped=item.skipped,
                last_celebrated_epoch=item.last_celebrated_epoch,
            )
            for item in keepers
        ],
        locked=row.locked,
    )


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
    refs = await node_refs(session, [*(item.adherent_entity_id for item in adherents), *([row.founder_entity_id] if row.founder_entity_id else [])])
    return IdeologyCard(
        founder=ref(refs, row.founder_entity_id),
        tenets=tenets,
        appeal=row.appeal,
        values=row.value_delta,
        adherents=[
            AdherentView(community=ref(refs, item.adherent_entity_id), strength=item.strength, state=item.state, since_epoch=item.since_epoch)
            for item in adherents
        ],
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
    refs = await node_refs(session, [*ids, *([row.inventor_entity_id] if row.inventor_entity_id else [])])
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
        effects=[RiteEffectView(effect=item.effect, magnitude=item.magnitude, detail=item.detail) for item in effects],
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
    refs = await node_refs(session, [*row.audience, *([row.seer_entity_id] if row.seer_entity_id else [])])
    return ProphecyCard(
        predicate=row.predicate,
        args=row.args,
        deadline_epoch=row.deadline_epoch,
        seer=ref(refs, row.seer_entity_id),
        audience=[refs[item] for item in row.audience if item in refs],
        pressure=row.pressure,
        state=row.state,
        resolved_epoch=row.resolved_epoch,
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
    contents = list(await session.scalars(select(BookContentRow.knowledge_entity_id).where(BookContentRow.book_entity_id == entity_id)))
    owner = await session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    extra = [item for item in (row.maker_entity_id, row.regalia_of_entity_id, owner) if item is not None]
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
        history=[DeedView(epoch=item.epoch, deed=item.deed, actor=ref(refs, item.actor_entity_id), note=item.note) for item in history],
        enchantments=[
            EnchantmentView(effect=item.effect, strength=item.strength, rite=ref(refs, item.rite_entity_id), since_epoch=item.since_epoch) for item in spells
        ],
        contents=[refs[item] for item in contents if item in refs],
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
        )
