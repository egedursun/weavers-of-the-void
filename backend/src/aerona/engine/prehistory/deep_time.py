from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.prehistory import DeepTimeEventRow, DeepTimeRunRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.prehistory import DeepTimeState
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import Publisher
from aerona.engine.pipeline import simulate
from aerona.engine.prehistory.digest import magnitude_of
from aerona.engine.primitives.manual import silent
from aerona.rules.registry import Rules


@dataclass
class DeepTimeSummary:
    run_id: int
    epochs: int = 0
    events: int = 0
    state: DeepTimeState = DeepTimeState.RUNNING


async def keep_epoch(database: Database, run_id: int, epoch: int, size: int) -> int:
    async with database.write() as session:
        run = await session.get(DeepTimeRunRow, run_id)
        if run is None:
            return 0
        found = list(
            await session.scalars(select(IncidentRow).where(IncidentRow.epoch == epoch).order_by(IncidentRow.magnitude.desc(), IncidentRow.id).limit(size))
        )
        for incident in found:
            session.add(DeepTimeEventRow(run_id=run_id, incident_id=incident.id, epoch=epoch, magnitude=magnitude_of(incident.magnitude), locked=[]))
        run.sons_simulated += int(await session.scalar(select(func.count()).select_from(SonRow).where(SonRow.status == SonStatus.ACTIVE)) or 0)
        run.ran += 1
        run.to_epoch = epoch
        return len(found)


async def prune_run(database: Database, run_id: int, size: int) -> None:
    async with database.write() as session:
        rows = list(
            await session.scalars(
                select(DeepTimeEventRow).where(DeepTimeEventRow.run_id == run_id).order_by(DeepTimeEventRow.magnitude.desc(), DeepTimeEventRow.id)
            )
        )
        for row in rows[size:]:
            if "magnitude" not in (row.locked or []):
                await session.delete(row)


async def fast_forward(database: Database, run_id: int, *, rules: Rules | None = None, publish: Publisher = silent) -> DeepTimeSummary:
    summary = DeepTimeSummary(run_id)
    while True:
        async with database.read() as session:
            run = await session.get(DeepTimeRunRow, run_id)
            cosmos = await CosmosRepository(session).require_cosmos()
            resolved = rules or rules_from_snapshot(cosmos.rules_snapshot)
            if run is None or run.state is not DeepTimeState.RUNNING:
                summary.state = run.state if run is not None else DeepTimeState.STOPPED
                break
            if run.ran >= run.epochs:
                break
        epoch = (await simulate(database, 1, rules=rules, publish=publish))[0].epoch
        summary.events += await keep_epoch(database, run_id, epoch, resolved.prehistory.deep_time_digest_size)
        summary.epochs += 1
    async with database.write() as session:
        run = await session.get(DeepTimeRunRow, run_id)
        if run is not None and run.state is DeepTimeState.RUNNING:
            run.state = DeepTimeState.DONE
            summary.state = run.state
    await prune_run(database, run_id, (rules or resolved).prehistory.deep_time_digest_size)
    return summary
