from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.sacred import (
    DivinationSystemView,
    FaithClimateView,
    FaithCrisisView,
    FeedingView,
    ForecastModelView,
    ForesightView,
    GeniusView,
    HarvestView,
    MillenarianView,
    MysticView,
    OmenReadingView,
    PetitionView,
    SacramentView,
    SacredNodeView,
    SpiritOfficeView,
    TaughtAfterlifeView,
    TeachingView,
    VisionView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.sacred import (
    DivinationRow,
    DivinationSystemRow,
    DoctrineAfterlifeRow,
    DoctrineSacramentRow,
    EmotionHarvestRow,
    FaithClimateRow,
    ForecastModelRow,
    ForesightRow,
    GeniusLocusRow,
    GodFeedingRow,
    MillenarianRow,
    MysticRow,
    PetitionRow,
    SacramentRow,
    SpiritOfficeRow,
    TheodicyCrisisRow,
    VisionRow,
)
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.node import NodeKind

router = APIRouter(tags=["sacred"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def genius_view(row: GeniusLocusRow, refs: dict[int, NodeRef]) -> GeniusView:
    return GeniusView(
        spirit=ref(refs, row.spirit_entity_id),
        place=at(refs, row.place_entity_id),
        community=at(refs, row.community_entity_id),
        kind=row.kind,
        temperament=row.temperament,
        contentment=row.contentment,
        offerings=row.offerings,
        owed=row.owed,
        favour=row.favour,
        offended=row.offended,
        last_offering_epoch=row.last_offering_epoch,
        bound_epoch=row.bound_epoch,
        locked=row.locked,
    )


def office_view(row: SpiritOfficeRow, refs: dict[int, NodeRef]) -> SpiritOfficeView:
    return SpiritOfficeView(
        spirit=ref(refs, row.spirit_entity_id),
        rank=row.rank,
        superior=at(refs, row.superior_spirit_id),
        overseer=at(refs, row.overseer_node_id),
        jurisdiction=at(refs, row.jurisdiction_entity_id),
        merit=row.merit,
        corruption=row.corruption,
        resolved=row.resolved,
        neglected=row.neglected,
        dismissed=row.dismissed,
        appointed_epoch=row.appointed_epoch,
        locked=row.locked,
    )


def petition_view(row: PetitionRow, refs: dict[int, NodeRef]) -> PetitionView:
    return PetitionView(
        id=row.id,
        petitioner=ref(refs, row.petitioner_node_id),
        office=ref(refs, row.office_spirit_id),
        kind=row.kind,
        defendant=at(refs, row.defendant_spirit_id),
        bribe=row.bribe,
        status=row.status,
        filed_epoch=row.filed_epoch,
        due_epoch=row.due_epoch,
        resolved_epoch=row.resolved_epoch,
        appealed_to=at(refs, row.appealed_to_id),
        locked=row.locked,
    )


def mystic_view(row: MysticRow, visions: list[VisionRow], refs: dict[int, NodeRef]) -> MysticView:
    return MysticView(
        mortal=ref(refs, row.mortal_entity_id),
        state=row.state,
        visions=row.visions,
        genuine_visions=row.genuine_visions,
        followers=row.followers,
        answered_by=at(refs, row.answered_by_node_id),
        cult=at(refs, row.cult_entity_id),
        founded=at(refs, row.founded_entity_id),
        reverence=row.reverence,
        persecution=row.persecution,
        since_epoch=row.since_epoch,
        last_vision_epoch=row.last_vision_epoch,
        history=[
            VisionView(
                id=item.id, epoch=item.epoch, kind=item.kind, sender=at(refs, item.sender_node_id), genuine=item.genuine, awe=item.awe, locked=item.locked
            )
            for item in visions
            if item.mystic_entity_id == row.mortal_entity_id
        ],
        locked=row.locked,
    )


def movement_view(row: MillenarianRow, refs: dict[int, NodeRef]) -> MillenarianView:
    return MillenarianView(
        id=row.id,
        settlement=ref(refs, row.settlement_entity_id),
        cult=at(refs, row.cult_entity_id),
        prophet=at(refs, row.prophet_entity_id),
        prophecy=at(refs, row.prophecy_entity_id),
        movement_id=row.movement_id,
        stage=row.stage,
        end_epoch=row.end_epoch,
        members=row.members,
        conviction=row.conviction,
        given_up=row.given_up,
        idle_share=row.idle_share,
        attacks=row.attacks,
        dates_set=row.dates_set,
        sect=at(refs, row.sect_entity_id),
        since_epoch=row.since_epoch,
        ended_epoch=row.ended_epoch,
        locked=row.locked,
    )


def crisis_view(row: TheodicyCrisisRow, refs: dict[int, NodeRef]) -> FaithCrisisView:
    return FaithCrisisView(
        id=row.id,
        cult=ref(refs, row.cult_entity_id),
        community=ref(refs, row.community_entity_id),
        god=at(refs, row.god_node_id),
        cause=row.cause,
        suffering=row.suffering,
        answered=row.answered,
        resolution=row.resolution,
        theologian=at(refs, row.theologian_entity_id),
        started_epoch=row.started_epoch,
        resolved_epoch=row.resolved_epoch,
        locked=row.locked,
    )


def afterlife_view(row: DoctrineAfterlifeRow, refs: dict[int, NodeRef]) -> TaughtAfterlifeView:
    return TaughtAfterlifeView(
        cult=ref(refs, row.cult_entity_id),
        model=row.model,
        aligned=row.aligned,
        aligned_by=at(refs, row.aligned_by_node_id),
        shocks=row.shocks,
        testimonies=row.testimonies,
        doubt=row.doubt,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def climate_view(row: FaithClimateRow, refs: dict[int, NodeRef]) -> FaithClimateView:
    return FaithClimateView(
        community=ref(refs, row.community_entity_id),
        piety_drift=row.piety_drift,
        literacy_pull=row.literacy_pull,
        science_pull=row.science_pull,
        prosperity_pull=row.prosperity_pull,
        city_pull=row.city_pull,
        silence_pull=row.silence_pull,
        disaster_push=row.disaster_push,
        miracle_push=row.miracle_push,
        war_push=row.war_push,
        dominion_push=row.dominion_push,
        silent_epochs=row.silent_epochs,
        godless=row.godless,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def reading_view(row: DivinationRow, refs: dict[int, NodeRef]) -> OmenReadingView:
    return OmenReadingView(
        id=row.id,
        system_id=row.system_id,
        diviner=at(refs, row.diviner_entity_id),
        client=at(refs, row.client_entity_id),
        question=row.question,
        verdict=row.verdict,
        true_verdict=row.true_verdict,
        heeded=row.heeded,
        swayed_by=at(refs, row.swayed_by_node_id),
        epoch=row.epoch,
        locked=row.locked,
    )


def foresight_view(row: ForesightRow, refs: dict[int, NodeRef]) -> ForesightView:
    return ForesightView(
        id=row.id,
        seer=ref(refs, row.seer_node_id),
        subject=at(refs, row.subject_node_id),
        predicate=row.predicate,
        horizon=row.horizon,
        due_epoch=row.due_epoch,
        certainty=row.certainty,
        source=row.source,
        divination_id=row.divination_id,
        status=row.status,
        checked_epoch=row.checked_epoch,
        made_epoch=row.made_epoch,
        locked=row.locked,
    )


def model_view(row: ForecastModelRow, refs: dict[int, NodeRef]) -> ForecastModelView:
    return ForecastModelView(
        id=row.id,
        order=ref(refs, row.order_entity_id),
        subject=at(refs, row.subject_entity_id),
        archive=row.archive,
        accuracy=row.accuracy,
        forecast_psi=row.forecast_psi,
        actual_psi=row.actual_psi,
        plan_id=row.plan_id,
        disruption=row.disruption,
        disrupted_by=at(refs, row.disrupted_by_node_id),
        built_epoch=row.built_epoch,
        horizon=row.horizon,
        locked=row.locked,
    )


@router.get("/sacred/of/{node_id}", response_model=SacredNodeView)
async def node_sacred(services: ServicesDep, node_id: NodeId) -> SacredNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        spirits = list(
            await session.scalars(
                select(GeniusLocusRow)
                .where(
                    or_(GeniusLocusRow.spirit_entity_id == node_id, GeniusLocusRow.place_entity_id == node_id, GeniusLocusRow.community_entity_id == node_id)
                )
                .order_by(GeniusLocusRow.spirit_entity_id)
            )
        )
        offices = list(
            await session.scalars(
                select(SpiritOfficeRow)
                .where(
                    or_(
                        SpiritOfficeRow.spirit_entity_id == node_id,
                        SpiritOfficeRow.overseer_node_id == node_id,
                        SpiritOfficeRow.jurisdiction_entity_id == node_id,
                        SpiritOfficeRow.superior_spirit_id == node_id,
                    )
                )
                .order_by(SpiritOfficeRow.spirit_entity_id)
            )
        )
        office_ids = [row.spirit_entity_id for row in offices] or [0]
        petitions = list(
            await session.scalars(
                select(PetitionRow)
                .where(
                    or_(
                        PetitionRow.petitioner_node_id == node_id,
                        PetitionRow.office_spirit_id.in_(office_ids),
                        PetitionRow.defendant_spirit_id == node_id,
                    )
                )
                .order_by(PetitionRow.id.desc())
            )
        )
        mystic = await session.get(MysticRow, node_id)
        mystics = list(
            await session.scalars(
                select(MysticRow)
                .where(or_(MysticRow.cult_entity_id == node_id, MysticRow.answered_by_node_id == node_id, MysticRow.founded_entity_id == node_id))
                .order_by(MysticRow.mortal_entity_id)
            )
        )
        seen = [row.mortal_entity_id for row in mystics] + ([mystic.mortal_entity_id] if mystic is not None else [])
        visions = list(
            await session.scalars(select(VisionRow).where(VisionRow.mystic_entity_id.in_(seen or [0])).order_by(VisionRow.epoch.desc(), VisionRow.id.desc()))
        )
        movements = list(
            await session.scalars(
                select(MillenarianRow)
                .where(
                    or_(
                        MillenarianRow.settlement_entity_id == node_id,
                        MillenarianRow.cult_entity_id == node_id,
                        MillenarianRow.prophet_entity_id == node_id,
                        MillenarianRow.prophecy_entity_id == node_id,
                        MillenarianRow.sect_entity_id == node_id,
                    )
                )
                .order_by(MillenarianRow.id.desc())
            )
        )
        crises = list(
            await session.scalars(
                select(TheodicyCrisisRow)
                .where(
                    or_(
                        TheodicyCrisisRow.community_entity_id == node_id,
                        TheodicyCrisisRow.cult_entity_id == node_id,
                        TheodicyCrisisRow.god_node_id == node_id,
                        TheodicyCrisisRow.theologian_entity_id == node_id,
                    )
                )
                .order_by(TheodicyCrisisRow.id.desc())
            )
        )
        teachings = list(
            await session.scalars(select(DoctrineSacramentRow).where(DoctrineSacramentRow.cult_entity_id == node_id).order_by(DoctrineSacramentRow.kind))
        )
        sacraments = list(
            await session.scalars(
                select(SacramentRow)
                .where(or_(SacramentRow.mortal_entity_id == node_id, SacramentRow.priest_entity_id == node_id, SacramentRow.cult_entity_id == node_id))
                .order_by(SacramentRow.epoch.desc(), SacramentRow.id.desc())
            )
        )
        churches = select(BondRow.source_node_id).where(BondRow.target_node_id == node_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        afterlives = list(
            await session.scalars(
                select(DoctrineAfterlifeRow)
                .where(
                    or_(
                        DoctrineAfterlifeRow.cult_entity_id == node_id,
                        DoctrineAfterlifeRow.aligned_by_node_id == node_id,
                        DoctrineAfterlifeRow.cult_entity_id.in_(churches),
                    )
                )
                .order_by(DoctrineAfterlifeRow.cult_entity_id)
            )
        )
        climate = await session.get(FaithClimateRow, node_id)
        systems = list(
            await session.scalars(select(DivinationSystemRow).where(DivinationSystemRow.people_entity_id == node_id).order_by(DivinationSystemRow.id))
        )
        readings = list(
            await session.scalars(
                select(DivinationRow)
                .where(
                    or_(
                        DivinationRow.client_entity_id == node_id,
                        DivinationRow.diviner_entity_id == node_id,
                        DivinationRow.swayed_by_node_id == node_id,
                        DivinationRow.system_id.in_([row.id for row in systems] or [0]),
                    )
                )
                .order_by(DivinationRow.epoch.desc(), DivinationRow.id.desc())
            )
        )
        foresights = list(
            await session.scalars(
                select(ForesightRow)
                .where(or_(ForesightRow.seer_node_id == node_id, ForesightRow.subject_node_id == node_id))
                .order_by(ForesightRow.made_epoch.desc(), ForesightRow.id.desc())
            )
        )
        models = list(
            await session.scalars(
                select(ForecastModelRow)
                .where(
                    or_(
                        ForecastModelRow.order_entity_id == node_id,
                        ForecastModelRow.subject_entity_id == node_id,
                        ForecastModelRow.disrupted_by_node_id == node_id,
                    )
                )
                .order_by(ForecastModelRow.id)
            )
        )
        feedings = list(await session.scalars(select(GodFeedingRow).where(GodFeedingRow.god_node_id == node_id).order_by(GodFeedingRow.emotion)))
        harvests = list(
            await session.scalars(
                select(EmotionHarvestRow).where(EmotionHarvestRow.god_node_id == node_id).order_by(EmotionHarvestRow.epoch.desc(), EmotionHarvestRow.emotion)
            )
        )
        all_mystics = [*([mystic] if mystic is not None else []), *mystics]
        refs = await refs_of(
            session,
            [
                node_id,
                *(item for row in spirits for item in (row.spirit_entity_id, row.place_entity_id, row.community_entity_id)),
                *(item for row in offices for item in (row.spirit_entity_id, row.superior_spirit_id, row.overseer_node_id, row.jurisdiction_entity_id)),
                *(item for row in petitions for item in (row.petitioner_node_id, row.office_spirit_id, row.defendant_spirit_id, row.appealed_to_id)),
                *(item for row in all_mystics for item in (row.mortal_entity_id, row.answered_by_node_id, row.cult_entity_id, row.founded_entity_id)),
                *(row.sender_node_id for row in visions),
                *(
                    item
                    for row in movements
                    for item in (row.settlement_entity_id, row.cult_entity_id, row.prophet_entity_id, row.prophecy_entity_id, row.sect_entity_id)
                ),
                *(item for row in crises for item in (row.cult_entity_id, row.community_entity_id, row.god_node_id, row.theologian_entity_id)),
                *(row.cult_entity_id for row in teachings),
                *(item for row in sacraments for item in (row.mortal_entity_id, row.cult_entity_id, row.priest_entity_id)),
                *(item for row in afterlives for item in (row.cult_entity_id, row.aligned_by_node_id)),
                *(row.people_entity_id for row in systems),
                *(item for row in readings for item in (row.diviner_entity_id, row.client_entity_id, row.swayed_by_node_id)),
                *(item for row in foresights for item in (row.seer_node_id, row.subject_node_id)),
                *(item for row in models for item in (row.order_entity_id, row.subject_entity_id, row.disrupted_by_node_id)),
            ],
        )
        return SacredNodeView(
            node=own[node_id],
            spirits=[genius_view(row, refs) for row in spirits],
            offices=[office_view(row, refs) for row in offices],
            petitions=[petition_view(row, refs) for row in petitions],
            mystic=mystic_view(mystic, visions, refs) if mystic is not None else None,
            mystics=[mystic_view(row, visions, refs) for row in mystics if mystic is None or row.mortal_entity_id != mystic.mortal_entity_id],
            movements=[movement_view(row, refs) for row in movements],
            crises=[crisis_view(row, refs) for row in crises],
            teachings=[
                TeachingView(
                    cult=ref(refs, row.cult_entity_id),
                    kind=row.kind,
                    protection=row.protection,
                    strength=row.strength,
                    since_epoch=row.since_epoch,
                    locked=row.locked,
                )
                for row in teachings
            ],
            sacraments=[
                SacramentView(
                    id=row.id,
                    mortal=ref(refs, row.mortal_entity_id),
                    kind=row.kind,
                    cult=at(refs, row.cult_entity_id),
                    priest=at(refs, row.priest_entity_id),
                    epoch=row.epoch,
                    missed=row.missed,
                    locked=row.locked,
                )
                for row in sacraments
            ],
            afterlives=[afterlife_view(row, refs) for row in afterlives],
            climate=climate_view(climate, refs) if climate is not None else None,
            systems=[
                DivinationSystemView(
                    id=row.id,
                    people=ref(refs, row.people_entity_id),
                    kind=row.kind,
                    validity=row.validity,
                    trust=row.trust,
                    diviners=row.diviners,
                    founded_epoch=row.founded_epoch,
                    locked=row.locked,
                )
                for row in systems
            ],
            readings=[reading_view(row, refs) for row in readings],
            foresights=[foresight_view(row, refs) for row in foresights],
            models=[model_view(row, refs) for row in models],
            feedings=[FeedingView(emotion=row.emotion, weight=row.weight, harvested=row.harvested, epoch=row.epoch, locked=row.locked) for row in feedings],
            harvests=[HarvestView(id=row.id, epoch=row.epoch, emotion=row.emotion, count=row.count, essence=row.essence) for row in harvests],
        )
