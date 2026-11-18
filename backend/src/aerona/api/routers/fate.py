from fastapi import APIRouter
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.common import ApiModel
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.db.tables.epochs import DeferredStepRow, EpochRunRow, EpochStepRow
from aerona.db.tables.lore import HistorianViewRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EpochStepKind, EpochStepStatus
from aerona.domain.enums.record_keepers import RecordKeeperKind

router = APIRouter(tags=["fate"])

CONTROLLED_STEPS = (EpochStepKind.FATE_JUDGMENT, EpochStepKind.CHRONICLE, EpochStepKind.VOICES, EpochStepKind.WORLD_BIRTH)


class LimboRecord(ApiModel):
    entity_id: int
    name: str
    born_epoch: int
    rationale: str | None


class FateStepState(ApiModel):
    step: EpochStepKind
    status: EpochStepStatus
    error: str | None


class HistorianViewItem(ApiModel):
    id: int
    people_entity_id: int
    historian: str | None
    historian_entity_id: int | None
    text: str


class RecordKeeperItem(ApiModel):
    id: int
    kind: RecordKeeperKind
    scope_node_id: int
    keeper_entity_id: int | None
    since_epoch: int
    locked: list[str]


class FateControlsView(ApiModel):
    last_epoch: int | None
    fate_debt_epoch: int | None
    limbo: list[LimboRecord]
    steps: list[FateStepState]
    failed_births: int
    views: list[HistorianViewItem]
    keepers: list[RecordKeeperItem]


@router.get("/fate/controls", response_model=FateControlsView)
async def fate_controls(services: ServicesDep) -> FateControlsView:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).get()
        runs = list(await session.scalars(select(EpochRunRow.epoch).order_by(EpochRunRow.epoch.desc()).limit(1)))
        last_epoch = runs[0] if runs else None
        limbo_rows = await session.execute(
            select(CreationVerdictRow, EntityRow.name)
            .join(EntityRow, EntityRow.id == CreationVerdictRow.entity_id)
            .where(CreationVerdictRow.verdict == Verdict.LIMBO)
        )
        steps: list[FateStepState] = []
        views: list[HistorianViewItem] = []
        if last_epoch is not None:
            found = await session.scalars(select(EpochStepRow).where(EpochStepRow.epoch == last_epoch, EpochStepRow.step.in_(CONTROLLED_STEPS)))
            steps = [FateStepState(step=row.step, status=row.status, error=row.error) for row in found]
            views = [
                HistorianViewItem.model_validate(row)
                for row in await session.scalars(select(HistorianViewRow).where(HistorianViewRow.epoch == last_epoch).order_by(HistorianViewRow.id))
            ]
        failed = list(
            await session.scalars(
                select(DeferredStepRow.id).where(DeferredStepRow.kind == DeferredStepKind.WORLD_BIRTH, DeferredStepRow.status == DeferredStepStatus.FAILED)
            )
        )
        return FateControlsView(
            last_epoch=last_epoch,
            fate_debt_epoch=cosmos.fate_debt_epoch if cosmos is not None else None,
            limbo=[LimboRecord(entity_id=row.entity_id, name=name, born_epoch=row.epoch, rationale=row.rationale) for row, name in limbo_rows],
            steps=steps,
            failed_births=len(failed),
            views=views,
            keepers=[
                RecordKeeperItem.model_validate(row)
                for row in await session.scalars(select(RecordKeeperRow).order_by(RecordKeeperRow.kind, RecordKeeperRow.id))
            ],
        )
