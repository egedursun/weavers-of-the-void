from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.tales import (
    AgeView,
    ArcBeatView,
    ArcFigureView,
    ArcView,
    EchoView,
    ForecastView,
    FormationView,
    LongSeasonView,
    SetupView,
    TalesNodeView,
    TransformationView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import (
    AgeEchoRow,
    AgeRow,
    ArcBeatRow,
    ArcFigureRow,
    ArcRow,
    EcoTransformationRow,
    FormationHistoryRow,
    IrregularSeasonRow,
    SetupRow,
    WinterForecastRow,
)
from aerona.db.tables.cycles import LongPlanRow
from aerona.domain.enums.node import NodeKind

router = APIRouter(tags=["tales"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def arc_view(row: ArcRow, figures: list[ArcFigureRow], beats: list[ArcBeatRow], refs: dict[int, NodeRef]) -> ArcView:
    return ArcView(
        id=row.id,
        subject=ref(refs, row.subject_node_id),
        template=row.template,
        stage=row.stage,
        outcome=row.outcome,
        beats=row.beats,
        drama=row.drama,
        echo_id=row.echo_id,
        started_epoch=row.started_epoch,
        last_beat_epoch=row.last_beat_epoch,
        ended_epoch=row.ended_epoch,
        figures=[ArcFigureView(node=ref(refs, figure.node_id), role=figure.role, locked=figure.locked) for figure in figures if figure.arc_id == row.id],
        history=[ArcBeatView(id=beat.id, stage=beat.stage, text=beat.text, epoch=beat.epoch, locked=beat.locked) for beat in beats if beat.arc_id == row.id],
        locked=row.locked,
    )


async def arcs_of(session: AsyncSession, node_id: int) -> tuple[list[ArcRow], list[ArcFigureRow], list[ArcBeatRow]]:
    touching = select(ArcFigureRow.arc_id).where(ArcFigureRow.node_id == node_id)
    arcs = list(await session.scalars(select(ArcRow).where(or_(ArcRow.subject_node_id == node_id, ArcRow.id.in_(touching))).order_by(ArcRow.id.desc())))
    ids = [row.id for row in arcs] or [0]
    figures = list(await session.scalars(select(ArcFigureRow).where(ArcFigureRow.arc_id.in_(ids)).order_by(ArcFigureRow.node_id)))
    beats = list(await session.scalars(select(ArcBeatRow).where(ArcBeatRow.arc_id.in_(ids)).order_by(ArcBeatRow.epoch.desc(), ArcBeatRow.id.desc())))
    return arcs, figures, beats


async def plans_of(session: AsyncSession, node_id: int) -> list[tuple[EcoTransformationRow, LongPlanRow]]:
    rows = await session.execute(
        select(EcoTransformationRow, LongPlanRow)
        .join(LongPlanRow, LongPlanRow.id == EcoTransformationRow.plan_id)
        .where(or_(LongPlanRow.holder_node_id == node_id, LongPlanRow.target_node_id == node_id))
        .order_by(LongPlanRow.id)
    )
    return [(work, plan) for work, plan in rows]


@router.get("/tales/of/{node_id}", response_model=TalesNodeView)
async def node_tales(services: ServicesDep, node_id: NodeId) -> TalesNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        cosmos = await CosmosRepository(session).require_cosmos()
        formation = await session.get(FormationHistoryRow, node_id)
        seasons = list(
            await session.scalars(
                select(IrregularSeasonRow)
                .where(
                    or_(IrregularSeasonRow.world_id == node_id, IrregularSeasonRow.source_region_id == node_id, IrregularSeasonRow.source_star_id == node_id)
                )
                .order_by(IrregularSeasonRow.id)
            )
        )
        forecasts = list(
            await session.scalars(
                select(WinterForecastRow)
                .where(
                    or_(WinterForecastRow.world_id == node_id, WinterForecastRow.people_entity_id == node_id, WinterForecastRow.scholar_entity_id == node_id)
                )
                .order_by(WinterForecastRow.id)
            )
        )
        plans = await plans_of(session, node_id)
        ages = list(await session.scalars(select(AgeRow).order_by(AgeRow.number)))
        touching = or_(AgeEchoRow.source_node_id == node_id, AgeEchoRow.echo_node_id == node_id)
        echo_query = select(AgeEchoRow) if own[node_id].kind is NodeKind.CREATOR else select(AgeEchoRow).where(touching)
        echoes = list(await session.scalars(echo_query.order_by(AgeEchoRow.id)))
        arcs, figures, beats = await arcs_of(session, node_id)
        setups = list(await session.scalars(select(SetupRow).where(SetupRow.subject_node_id == node_id).order_by(SetupRow.id.desc())))
        refs = await refs_of(
            session,
            [
                node_id,
                *(item for season in seasons for item in (season.world_id, season.by_node_id, season.source_region_id, season.source_star_id)),
                *(item for row in forecasts for item in (row.world_id, row.people_entity_id, row.scholar_entity_id)),
                *(item for _, plan in plans for item in (plan.holder_node_id, plan.target_node_id)),
                *(item for row in echoes for item in (row.source_node_id, row.echo_node_id)),
                *(row.subject_node_id for row in arcs),
                *(row.node_id for row in figures),
                *(row.subject_node_id for row in setups),
            ],
        )
        return TalesNodeView(
            node=own[node_id],
            formation=FormationView(
                world=ref(refs, formation.world_id),
                zone=formation.zone,
                migration=formation.migration,
                bombardment=formation.bombardment,
                craters=formation.craters,
                core_share=formation.core_share,
                mantle_heat=formation.mantle_heat,
                water_delivered=formation.water_delivered,
                exotic_delivered=formation.exotic_delivered,
                shaped=formation.shaped,
                formed_epoch=formation.formed_epoch,
                locked=formation.locked,
            )
            if formation is not None
            else None,
            seasons=[
                LongSeasonView(
                    id=season.id,
                    world=ref(refs, season.world_id),
                    cause=season.cause,
                    shape=season.shape,
                    spell=season.spell,
                    spell_started_epoch=season.spell_started_epoch,
                    spell_length=season.spell_length,
                    severity=season.severity,
                    reach=season.reach,
                    source_impact_id=season.source_impact_id,
                    source_region=at(refs, season.source_region_id),
                    source_star=at(refs, season.source_star_id),
                    source_incident_id=season.source_incident_id,
                    by_node=at(refs, season.by_node_id),
                    locked=season.locked,
                )
                for season in seasons
            ],
            forecasts=[
                ForecastView(
                    id=row.id,
                    long_season_id=row.long_season_id,
                    world=ref(refs, row.world_id),
                    people=ref(refs, row.people_entity_id),
                    scholar=at(refs, row.scholar_entity_id),
                    predicted_end_epoch=row.predicted_end_epoch,
                    heeded=row.heeded,
                    made_epoch=row.made_epoch,
                    locked=row.locked,
                )
                for row in forecasts
            ],
            transformations=[
                TransformationView(
                    plan_id=plan.id,
                    plan_name=plan.name,
                    holder=at(refs, plan.holder_node_id),
                    target=at(refs, plan.target_node_id),
                    progress=plan.progress,
                    steps=plan.steps,
                    target_moisture=work.target_moisture,
                    target_forest=work.target_forest,
                    target_fertility=work.target_fertility,
                    regions_changed=work.regions_changed,
                    resistance=work.resistance,
                    sabotage=work.sabotage,
                    last_epoch=work.last_epoch,
                    locked=work.locked,
                )
                for work, plan in plans
            ],
            cycle=cosmos.age_cycle,
            ages=[
                AgeView(
                    id=row.id,
                    number=row.number,
                    began_epoch=row.began_epoch,
                    ended_epoch=row.ended_epoch,
                    variant=row.variant,
                    carried=row.carried,
                    locked=row.locked,
                )
                for row in ages
            ],
            echoes=[
                EchoView(
                    id=row.id,
                    age_id=row.age_id,
                    template=row.template,
                    role=row.role,
                    source=at(refs, row.source_node_id),
                    echo=at(refs, row.echo_node_id),
                    weight=row.weight,
                    locked=row.locked,
                )
                for row in echoes
            ],
            arcs=[arc_view(row, figures, beats, refs) for row in arcs],
            setups=[
                SetupView(
                    id=row.id,
                    kind=row.kind,
                    source_id=row.source_id,
                    subject=at(refs, row.subject_node_id),
                    payoff=row.payoff,
                    opened_epoch=row.opened_epoch,
                    paid_epoch=row.paid_epoch,
                    payoff_text=row.payoff_text,
                    locked=row.locked,
                )
                for row in setups
            ],
        )
