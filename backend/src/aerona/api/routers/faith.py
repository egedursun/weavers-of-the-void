from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.faith import (
    ClergyView,
    DoctrineView,
    HeresyView,
    HoldingView,
    JudgementView,
    PossessionView,
    RealmOfDeadView,
    RealmPopulation,
    RelicView,
    SoulCard,
    StratumView,
    TenetKindSpec,
    TenetView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.tenets import OPPOSED, TARGETED, TENET_EFFECTS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
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
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import AfterlifeState, HoldingKind, JudgementDoctrine, RebirthPath, TenetKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.faith import StratumCriteria
from aerona.engine.cosmos.world_types import is_realm_of_dead
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.church import sway_of
from aerona.engine.faith.doctrine import spoken_by
from aerona.engine.faith.souls import realm_population
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
        locked=list(row.locked or []),
    )


def stratum_view(row: AfterlifeStratumRow, souls: list[NodeRef], refs: Refs | None = None, sons: dict[int, str] | None = None) -> StratumView:
    known = refs or {}
    return StratumView(
        id=row.id,
        kind=row.kind,
        valence=row.valence,
        permanence=row.permanence,
        admission=row.admission,
        activity=row.activity,
        contact=row.contact,
        ruler=ref(known, row.ruler_node_id),
        name=row.name,
        criteria=StratumCriteria.read(row.criteria),
        population=row.population,
        souls=souls,
        realm=ref(known, row.realm_entity_id),
        closed=row.closed,
        son_id=row.son_id,
        son_name=(sons or {}).get(row.son_id or 0),
        cult=ref(known, row.cult_entity_id),
        dimension=ref(known, row.dimension_id),
    )


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


async def state_of(session: AsyncSession, church: Church) -> tuple[PolityProfileRow | None, int | None]:
    realm = await session.scalar(
        select(PolityProfileRow).where(PolityProfileRow.state_religion_id == church.cult.id).order_by(PolityProfileRow.polity_entity_id).limit(1)
    )
    if realm is None or not church.holds(TenetKind.DIVINE_RULE):
        return realm, None
    ruler = await session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.polity_entity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return realm, ruler


async def reach_of(session: AsyncSession, church: Church, doctrine: CultDoctrineRow) -> int:
    if doctrine.liturgical_language_id is None or not church.members:
        return PERCENT
    speaking = 0
    for member in church.members:
        if doctrine.liturgical_language_id in await spoken_by(session, [member.id]):
            speaking += 1
    return speaking * PERCENT // len(church.members)


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
        realm, king = await state_of(session, church)
        refs = await node_refs(
            session,
            [
                entity_id,
                *(member.id for member in church.members),
                *([church.god.id] if church.god is not None else []),
                *(item.holding_entity_id for item in holdings),
                *(item.holder_entity_id for item in clergy if item.holder_entity_id),
                *(node for item in heresies for node in (item.heresy_entity_id, item.parent_entity_id)),
                *(node for item in relics for node in (item.item_entity_id, item.saint_entity_id, item.shrine_entity_id, item.cult_entity_id) if node),
                *(row.excommunicated if row is not None else []),
                *(node for node in (row.liturgical_language_id if row is not None else None, row.parent_cult_id if row is not None else None) if node),
                *([realm.polity_entity_id] if realm is not None else []),
                *([king] if king is not None else []),
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
                rebirth_path=RebirthPath.PEOPLE,
                liturgical_language=None,
                liturgy_reach=PERCENT,
                parent_cult=None,
                devotion=stat(church.cult, "devotion") or 0,
                state_realm=None,
                clergy_sway=0,
                god_king=None,
                tithe_base=[],
                realm_population=0,
            )
        lands = {item.holding_entity_id for item in holdings if item.kind is HoldingKind.LAND}
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
                    name=item.name,
                    effect=TENET_EFFECTS[item.tenet],
                    target=item.target,
                    target_name=refs[int(item.target)].name if item.target and item.target.isdigit() and int(item.target) in refs else item.target,
                    since_epoch=item.since_epoch,
                    revealed_by_son_id=item.revealed_by_son_id,
                )
                for item in tenets
            ],
            holdings=[HoldingView(kind=item.kind, holding=ref(refs, item.holding_entity_id), since_epoch=item.since_epoch) for item in holdings],
            clergy=[ClergyView(kind=item.kind, holder=ref(refs, item.holder_entity_id), since_epoch=item.since_epoch, locked=item.locked) for item in clergy],
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
                    cult=ref(refs, item.cult_entity_id),
                    locked=list(item.locked or []),
                )
                for item in relics
            ],
            rebirth_path=row.rebirth_path,
            liturgical_language=ref(refs, row.liturgical_language_id),
            liturgy_reach=await reach_of(session, church, row),
            parent_cult=ref(refs, row.parent_cult_id),
            devotion=stat(church.cult, "devotion") or 0,
            state_realm=ref(refs, realm.polity_entity_id) if realm is not None else None,
            clergy_sway=sway_of(services.rules.current, row, stat(church.cult, "zeal") or 0) if realm is not None and king is None else 0,
            god_king=ref(refs, king),
            tithe_base=[refs[member.id] for member in church.members if member.id in lands and member.id in refs],
            realm_population=await realm_population(session, church.god.id) if church.god is not None else 0,
        )


async def realm_ids(session: AsyncSession, entity: EntityRow) -> list[int]:
    if entity.entity_type is EntityType.REGION:
        return [entity.id]
    regions = list(
        await session.scalars(
            select(EntityRow).where(EntityRow.world_id == entity.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        )
    )
    world = await session.get(WorldRow, entity.world_id) if entity.world_id is not None else None
    if world is not None and is_realm_of_dead(world.world_type):
        return [region.id for region in regions]
    return [region.id for region in regions if region.is_underworld] or [region.id for region in regions]


@router.get("/entities/{entity_id}/afterlife", response_model=RealmOfDeadView)
async def realm_of_dead(services: ServicesDep, entity_id: Id) -> RealmOfDeadView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        realms = await realm_ids(session, entity)
        strata = list(
            await session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.realm_entity_id.in_(realms)).order_by(AfterlifeStratumRow.id))
        )
        souls = list(
            await session.scalars(
                select(SpiritProfileRow).where(SpiritProfileRow.stratum_id.in_([row.id for row in strata]), SpiritProfileRow.state == AfterlifeState.IN_REALM)
            )
        )
        sons = {son.id: son.name for son in await session.scalars(select(SonRow).order_by(SonRow.id))}
        counts: dict[int, int] = {}
        for soul in souls:
            if soul.patron_son_id is not None:
                counts[soul.patron_son_id] = counts.get(soul.patron_son_id, 0) + 1
        refs = await node_refs(
            session,
            [
                entity_id,
                *realms,
                *(soul.spirit_entity_id for soul in souls),
                *(row.cult_entity_id for row in strata if row.cult_entity_id),
                *(row.dimension_id for row in strata if row.dimension_id),
                *(row.ruler_node_id for row in strata if row.ruler_node_id),
            ],
        )
        return RealmOfDeadView(
            realm=ref(refs, entity_id),
            strata=[
                stratum_view(row, [refs[soul.spirit_entity_id] for soul in souls if soul.stratum_id == row.id and soul.spirit_entity_id in refs], refs, sons)
                for row in strata
            ],
            realms=[refs[realm] for realm in realms if realm in refs],
            gods=[RealmPopulation(son_id=son, name=sons.get(son, f"#{son}"), souls=total) for son, total in sorted(counts.items(), key=lambda item: -item[1])],
        )


def possession_view(row: PossessionRow, refs: Refs) -> PossessionView:
    return PossessionView(
        host=ref(refs, row.host_entity_id),
        spirit=ref(refs, row.spirit_entity_id),
        since_epoch=row.since_epoch,
        stress=row.stress,
        host_values=dict(row.host_values or {}),
        locked=list(row.locked or []),
    )


@router.get("/entities/{entity_id}/possession", response_model=PossessionView | None)
async def possession(services: ServicesDep, entity_id: Id) -> PossessionView | None:
    async with reader(services) as session:
        row = await session.get(PossessionRow, entity_id)
        if row is None:
            return None
        refs = await node_refs(session, [row.host_entity_id, row.spirit_entity_id])
        return possession_view(row, refs)


@router.get("/entities/{entity_id}/soul", response_model=SoulCard)
async def soul_card(services: ServicesDep, entity_id: Id) -> SoulCard:
    async with reader(services) as session:
        profile = await session.get(SpiritProfileRow, entity_id)
        if profile is None:
            raise NotFoundError("This spirit has no soul record.")
        spirit = await session.get(EntityRow, entity_id)
        stratum = await session.get(AfterlifeStratumRow, profile.stratum_id) if profile.stratum_id is not None else None
        judgements = list(await session.scalars(select(SoulJudgementRow).where(SoulJudgementRow.spirit_entity_id == entity_id).order_by(SoulJudgementRow.id)))
        strata = {
            row.id: row.name
            for row in await session.scalars(
                select(AfterlifeStratumRow).where(AfterlifeStratumRow.id.in_([item.stratum_id for item in judgements if item.stratum_id]))
            )
        }
        held = await session.scalar(select(PossessionRow).where(PossessionRow.spirit_entity_id == entity_id).limit(1))
        reborn = await session.scalar(
            select(ReincarnationRow).where(ReincarnationRow.spirit_entity_id == entity_id).order_by(ReincarnationRow.id.desc()).limit(1)
        )
        patron = await session.get(SonRow, profile.patron_son_id) if profile.patron_son_id is not None else None
        refs = await node_refs(
            session,
            [
                node
                for node in (
                    entity_id,
                    profile.origin_mortal_id,
                    profile.bound_entity_id,
                    held.host_entity_id if held is not None else None,
                    reborn.newborn_entity_id if reborn is not None else None,
                    reborn.species_entity_id if reborn is not None else None,
                    stratum.realm_entity_id if stratum is not None else None,
                    stratum.dimension_id if stratum is not None else None,
                )
                if node
            ],
        )
        return SoulCard(
            spirit=ref(refs, entity_id),
            origin=ref(refs, profile.origin_mortal_id),
            patron_son_id=profile.patron_son_id,
            patron_name=patron.name if patron is not None else None,
            state=profile.state,
            alignment=profile.alignment,
            binding=profile.binding,
            bound=ref(refs, profile.bound_entity_id),
            rite=profile.rite,
            sealed=profile.sealed,
            seal_strength=profile.seal_strength,
            memory_strength=profile.memory_strength,
            veneration=profile.veneration,
            unrest=(stat(spirit, "unrest") or 0) if spirit is not None else 0,
            imprint=dict(profile.imprint or {}),
            traits=list(profile.traits or []),
            deeds=dict(profile.deeds or {}),
            stratum=stratum_view(stratum, [], refs) if stratum is not None else None,
            judgements=[
                JudgementView(
                    epoch=item.epoch, doctrine=item.doctrine, stratum=strata.get(item.stratum_id or 0), score=item.score, rite=item.rite, reason=item.reason
                )
                for item in judgements
            ],
            possession=possession_view(held, refs) if held is not None else None,
            reborn_as=ref(refs, reborn.newborn_entity_id) if reborn is not None else None,
            reborn_kind=ref(refs, reborn.species_entity_id) if reborn is not None else None,
            rebirth_path=reborn.path if reborn is not None else None,
            gate=reborn.gate if reborn is not None else None,
            locked=list(profile.locked or []),
        )
