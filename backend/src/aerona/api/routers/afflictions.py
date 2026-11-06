from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.body import bearer_row, link_in, name_in, nodes_of
from aerona.api.schemas.afflictions import AfflictionsView, BearerAfflictionView, PackageView, StageView
from aerona.catalog.effect_packages import PACKAGES, PackageSpec
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.afflictions import STAGE_HOLD, bearable, spec_of, stage_of

router = APIRouter(tags=["afflictions"])


def package_view(spec: PackageSpec) -> PackageView:
    return PackageView(
        kind=spec.kind,
        label=spec.label,
        description=spec.description,
        transmissions=sorted(spec.transmissions),
        onset=spec.onset,
        stages=[
            StageView(
                number=index,
                label=stage.label,
                epochs=stage.epochs,
                condition=stage.condition,
                severity=stage.severity,
                stats=dict(stage.stats),
                values=dict(stage.values),
                needs=sorted(stage.needs),
                sanity_loss=stage.sanity_loss,
                ageless=stage.ageless,
                sunlight_harm=stage.sunlight_harm,
                transforms=stage.transforms,
                recruits=stage.recruits,
                fears_source=stage.fears_source,
            )
            for index, stage in enumerate(spec.stages, start=1)
        ],
        cures=sorted(spec.cures),
        visibility=spec.visibility,
        contagion=sorted(spec.contagion),
        cure_level=spec.cure_level,
        hereditary=spec.hereditary,
    )


def next_stage(row: AfflictionRow) -> int | None:
    if row.cured_epoch is not None or STAGE_HOLD in row.locked:
        return None
    spec = spec_of(row)
    if row.stage == 0:
        return row.since_epoch + spec.onset
    stage = stage_of(row)
    if stage is None or stage.epochs is None or row.stage >= len(spec.stages):
        return None
    return row.stage_since_epoch + stage.epochs


@router.get("/effect-packages", response_model=list[PackageView])
async def effect_packages() -> list[PackageView]:
    return [package_view(spec) for spec in PACKAGES.values()]


@router.get("/bodies/{node_id}/afflictions", response_model=AfflictionsView)
async def afflictions_of(services: ServicesDep, node_id: int = Path(ge=1)) -> AfflictionsView:
    async with reader(services) as session:
        bearer = await bearer_row(session, node_id)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        rows = list(
            await session.scalars(
                select(AfflictionRow).where(AfflictionRow.bearer_node_id == node_id).order_by(AfflictionRow.cured_epoch.is_not(None), AfflictionRow.id.desc())
            )
        )
        names = await nodes_of(session, [row.source_node_id for row in rows])
        return AfflictionsView(
            node_id=bearer.id,
            name=bearer.name,
            bearable=isinstance(bearer, EntityRow) and bearable(bearer),
            epoch=epoch,
            afflictions=[
                BearerAfflictionView(
                    id=row.id,
                    package=row.package,
                    label=spec_of(row).label,
                    stage=row.stage,
                    stage_label=stage.label if (stage := stage_of(row)) is not None else None,
                    stage_count=len(spec_of(row).stages),
                    since_epoch=row.since_epoch,
                    stage_since_epoch=row.stage_since_epoch,
                    next_stage_epoch=next_stage(row),
                    transmission=row.transmission,
                    source_node_id=row.source_node_id,
                    source_name=name_in(names, row.source_node_id),
                    source_link=link_in(names, row.source_node_id),
                    visibility=spec_of(row).visibility,
                    cured_epoch=row.cured_epoch,
                    applied=dict(row.applied),
                    held=STAGE_HOLD in row.locked,
                )
                for row in rows
            ],
        )
