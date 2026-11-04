from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.faith import (
    ClergyView,
    DoctrineView,
    HeresyView,
    HoldingView,
    JudgementView,
    RealmOfDeadView,
    RelicView,
    SoulCard,
    StratumView,
    TenetKindSpec,
    TenetView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.tenets import OPPOSED, TARGETED, TENET_EFFECTS
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import (
    AfterlifeStratumRow,
    CultDoctrineRow,
    CultHoldingRow,
    CultOfficeRow,
    CultTenetRow,
    HeresyRow,
    PossessionRow,
    ReincarnationRow,
    RelicRow,
    SoulJudgementRow,
    SpiritProfileRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import JudgementDoctrine, TenetKind
from aerona.engine.faith.book import FaithBook
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["faith"])
Id = Annotated[int, Path(ge=1)]
Refs = dict[int, NodeRef]


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def heresy_view(row: HeresyRow, refs: Refs) -> HeresyView:
    return HeresyView(
        heresy=ref(refs, row.heresy_entity_id),
        parent=ref(refs, row.parent_entity_id),
        distance=row.distance,
        declared_epoch=row.declared_epoch,
        suppressed=row.suppressed,
        tolerated=row.tolerated,
    )


def stratum_view(row: AfterlifeStratumRow, souls: list[NodeRef]) -> StratumView:
    return StratumView(id=row.id, kind=row.kind, name=row.name, criteria=dict(row.criteria or {}), population=row.population, souls=souls)


@router.get("/tenets/kinds", response_model=list[TenetKindSpec])
async def tenet_kinds() -> list[TenetKindSpec]:
    return [
        TenetKindSpec(
            tenet=tenet,
            effect=TENET_EFFECTS[tenet],
            targeted=tenet in TARGETED,
            opposed=sorted(other for pair in OPPOSED if tenet in pair for other in pair if other is not tenet),
        )
        for tenet in TenetKind
    ]


@router.get("/entities/{entity_id}/doctrine", response_model=DoctrineView)
async def doctrine(services: ServicesDep, entity_id: Id) -> DoctrineView:
    async with reader(services) as session:
        book = await FaithBook.load(session)
        church = book.churches.get(entity_id)
        if church is None:
            raise NotFoundError("No such living cult.")
        row = await session.get(CultDoctrineRow, entity_id)
        tenets = list(await session.scalars(select(CultTenetRow).where(CultTenetRow.cult_entity_id == entity_id).order_by(CultTenetRow.tenet)))
        holdings = list(
            await session.scalars(
                select(CultHoldingRow).where(CultHoldingRow.cult_entity_id == entity_id).order_by(CultHoldingRow.kind, CultHoldingRow.holding_entity_id)
            )
        )
        clergy = list(await session.scalars(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == entity_id).order_by(CultOfficeRow.kind)))
        heresies = list(await session.scalars(select(HeresyRow).where(or_(HeresyRow.parent_entity_id == entity_id, HeresyRow.heresy_entity_id == entity_id))))
        relics = list(await session.scalars(select(RelicRow).where(RelicRow.cult_entity_id == entity_id).order_by(RelicRow.item_entity_id)))
        targets = [int(item.target) for item in tenets if item.target and item.target.isdigit()]
        refs = await node_refs(
            session,
            [
                entity_id,
                *(member.id for member in church.members),
                *([church.god.id] if church.god is not None else []),
                *(item.holding_entity_id for item in holdings),
                *(item.holder_entity_id for item in clergy if item.holder_entity_id),
                *(node for item in heresies for node in (item.heresy_entity_id, item.parent_entity_id)),
                *(node for item in relics for node in (item.item_entity_id, item.saint_entity_id, item.shrine_entity_id) if node),
                *(row.excommunicated if row is not None else []),
                *targets,
            ],
        )
        if row is None:
            return DoctrineView(
                cult=ref(refs, entity_id),
                god=ref(refs, church.god.id if church.god is not None else None),
                judgement=JudgementDoctrine.DEEDS,
                orthodoxy=50,
                tithe_rate=0,
                treasury=0,
                clergy_count=0,
                clergy_quality=0,
                zeal=stat(church.cult, "zeal") or 0,
                zeal_parts={},
                fanaticism=None,
                fanaticism_epoch=None,
                doctrinal_distance=0,
                excommunicated=[],
                members=[refs[member.id] for member in church.members if member.id in refs],
                locked=[],
                tenets=[],
                holdings=[],
                clergy=[],
                heresies=[],
                mother=None,
                relics=[],
            )
        return DoctrineView(
            cult=ref(refs, entity_id),
            god=ref(refs, church.god.id if church.god is not None else None),
            judgement=row.judgement,
            orthodoxy=row.orthodoxy,
            tithe_rate=row.tithe_rate,
            treasury=row.treasury,
            clergy_count=row.clergy_count,
            clergy_quality=row.clergy_quality,
            zeal=stat(church.cult, "zeal") or 0,
            zeal_parts=dict(row.zeal_parts or {}),
            fanaticism=row.fanaticism,
            fanaticism_epoch=row.fanaticism_epoch,
            doctrinal_distance=row.doctrinal_distance,
            excommunicated=[refs[item] for item in row.excommunicated if item in refs],
            members=[refs[member.id] for member in church.members if member.id in refs],
            locked=list(row.locked or []),
            tenets=[
                TenetView(
                    tenet=item.tenet,
                    effect=TENET_EFFECTS[item.tenet],
                    target=item.target,
                    target_name=refs[int(item.target)].name if item.target and item.target.isdigit() and int(item.target) in refs else item.target,
                    since_epoch=item.since_epoch,
                    revealed_by_son_id=item.revealed_by_son_id,
                )
                for item in tenets
            ],
            holdings=[HoldingView(kind=item.kind, holding=ref(refs, item.holding_entity_id), since_epoch=item.since_epoch) for item in holdings],
            clergy=[ClergyView(kind=item.kind, holder=ref(refs, item.holder_entity_id), since_epoch=item.since_epoch) for item in clergy],
            heresies=[heresy_view(item, refs) for item in heresies if item.parent_entity_id == entity_id],
            mother=next((heresy_view(item, refs) for item in heresies if item.heresy_entity_id == entity_id), None),
            relics=[
                RelicView(
                    item=ref(refs, item.item_entity_id),
                    saint=ref(refs, item.saint_entity_id),
                    shrine=ref(refs, item.shrine_entity_id),
                    sanctity=item.sanctity,
                    pilgrims=item.pilgrims,
                    canonised_epoch=item.canonised_epoch,
                )
                for item in relics
            ],
        )


@router.get("/entities/{entity_id}/afterlife", response_model=RealmOfDeadView)
async def realm_of_dead(services: ServicesDep, entity_id: Id) -> RealmOfDeadView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        realms = [entity.id]
        if entity.entity_type is not EntityType.REGION:
            realms = list(await session.scalars(select(EntityRow.id).where(EntityRow.world_id == entity.world_id, EntityRow.entity_type == EntityType.REGION)))
        strata = list(
            await session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.realm_entity_id.in_(realms)).order_by(AfterlifeStratumRow.id))
        )
        souls = list(await session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.stratum_id.in_([row.id for row in strata]))))
        refs = await node_refs(session, [entity_id, *(soul.spirit_entity_id for soul in souls)])
        return RealmOfDeadView(
            realm=ref(refs, entity_id),
            strata=[
                stratum_view(row, [refs[soul.spirit_entity_id] for soul in souls if soul.stratum_id == row.id and soul.spirit_entity_id in refs])
                for row in strata
            ],
        )


@router.get("/entities/{entity_id}/soul", response_model=SoulCard)
async def soul_card(services: ServicesDep, entity_id: Id) -> SoulCard:
    async with reader(services) as session:
        profile = await session.get(SpiritProfileRow, entity_id)
        if profile is None:
            raise NotFoundError("This spirit has no soul record.")
        stratum = await session.get(AfterlifeStratumRow, profile.stratum_id) if profile.stratum_id is not None else None
        judgements = list(await session.scalars(select(SoulJudgementRow).where(SoulJudgementRow.spirit_entity_id == entity_id).order_by(SoulJudgementRow.id)))
        strata = {
            row.id: row.name
            for row in await session.scalars(
                select(AfterlifeStratumRow).where(AfterlifeStratumRow.id.in_([item.stratum_id for item in judgements if item.stratum_id]))
            )
        }
        possession = await session.scalar(select(PossessionRow).where(PossessionRow.spirit_entity_id == entity_id).limit(1))
        reborn = await session.scalar(
            select(ReincarnationRow).where(ReincarnationRow.spirit_entity_id == entity_id).order_by(ReincarnationRow.id.desc()).limit(1)
        )
        refs = await node_refs(
            session,
            [
                node
                for node in (
                    entity_id,
                    profile.origin_mortal_id,
                    profile.bound_entity_id,
                    possession.host_entity_id if possession is not None else None,
                    reborn.newborn_entity_id if reborn is not None else None,
                )
                if node
            ],
        )
        return SoulCard(
            spirit=ref(refs, entity_id),
            origin=ref(refs, profile.origin_mortal_id),
            patron_son_id=profile.patron_son_id,
            state=profile.state,
            alignment=profile.alignment,
            binding=profile.binding,
            bound=ref(refs, profile.bound_entity_id),
            rite=profile.rite,
            sealed=profile.sealed,
            memory_strength=profile.memory_strength,
            veneration=profile.veneration,
            imprint=dict(profile.imprint or {}),
            traits=list(profile.traits or []),
            deeds=dict(profile.deeds or {}),
            stratum=stratum_view(stratum, []) if stratum is not None else None,
            judgements=[
                JudgementView(
                    epoch=item.epoch, doctrine=item.doctrine, stratum=strata.get(item.stratum_id or 0), score=item.score, rite=item.rite, reason=item.reason
                )
                for item in judgements
            ],
            possessing=ref(refs, possession.host_entity_id) if possession is not None else None,
            reborn_as=ref(refs, reborn.newborn_entity_id) if reborn is not None else None,
            gate=reborn.gate if reborn is not None else None,
            locked=list(profile.locked or []),
        )
