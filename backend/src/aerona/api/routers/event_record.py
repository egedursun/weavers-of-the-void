import json
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Path, Query

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.event_record import (
    EventAccountView,
    EventChangeRecord,
    EventStepRecord,
    FactSearchHit,
    FactSearchView,
    NodeHistoryEntry,
    NodeHistoryView,
    StateAtFieldRecord,
    StateAtRowRecord,
    StateAtView,
)
from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import InstrumentKind, StepAction
from aerona.domain.models.moment import Moment
from aerona.engine.recording.accounts import account_of, history_of
from aerona.engine.recording.search import RecordQuery, search_records
from aerona.engine.recording.then import ThenPage, node_then, table_then

router = APIRouter(tags=["records"])

PAGE_MAX = 200


@router.get("/incidents/{incident_id}", response_model=EventAccountView)
async def incident_account(services: ServicesDep, incident_id: Annotated[int, Path(ge=1)]) -> EventAccountView:
    async with reader(services) as session:
        account = await account_of(session, incident_id)
        found = asdict(account)
        found["witnesses"] = [asdict(item) for item in account.witnesses]
        return EventAccountView.model_validate(found)


@router.get("/nodes/{node_id}/history", response_model=NodeHistoryView)
async def node_history(
    services: ServicesDep,
    *,
    node_id: Annotated[int, Path(ge=1)],
    role: Annotated[IncidentRole | None, Query()] = None,
    kind: Annotated[str | None, Query(max_length=120)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX)] = 20,
) -> NodeHistoryView:
    async with reader(services) as session:
        page = await history_of(session, node_id, role=role, kind=kind, offset=offset, limit=limit)
        return NodeHistoryView(
            node_id=page.node_id,
            offset=offset,
            limit=limit,
            total_incidents=page.total_incidents,
            incidents=[NodeHistoryEntry.model_validate(asdict(item)) for item in page.incidents],
            total_steps=page.total_steps,
            steps=[EventStepRecord.model_validate(asdict(item)) for item in page.steps],
            total_changes=page.total_changes,
            changes=[EventChangeRecord.model_validate(asdict(item)) for item in page.changes],
            kinds=list(page.kinds),
            roles=list(page.roles),
        )


def then_rows(page: ThenPage) -> list[StateAtRowRecord]:
    return [
        StateAtRowRecord(
            table_name=row.table_name,
            row_key=row.row_key,
            existed=row.existed,
            exists_now=row.exists_now,
            fields=[StateAtFieldRecord(field=item.field, then=item.then, now=item.now, changed=item.changed) for item in row.fields],
        )
        for row in page.rows
    ]


@router.get("/state-at", response_model=StateAtView)
async def state_at_moment(
    services: ServicesDep,
    *,
    epoch: Annotated[int, Query(ge=0)],
    year: Annotated[int | None, Query()] = None,
    season: Annotated[int | None, Query(ge=0)] = None,
    day: Annotated[int | None, Query(ge=0)] = None,
    hour: Annotated[int | None, Query(ge=0)] = None,
    node_id: Annotated[int | None, Query(ge=1)] = None,
    table: Annotated[str | None, Query(max_length=120)] = None,
    key: Annotated[str | None, Query(max_length=500)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX)] = 50,
) -> StateAtView:
    if (node_id is None) == (table is None):
        raise ValidationFailedError("Ask for one record: a node, or a table with an optional key.")
    moment = Moment(year=year, season=season, day=day, hour=hour) if year is not None else None
    row_key = json.loads(key) if key else None
    if row_key is not None and not isinstance(row_key, dict):
        raise ValidationFailedError("A key names the columns of one row.")
    async with reader(services) as session:
        if node_id is not None:
            page = await node_then(session, node_id, epoch=epoch, moment=moment)
        else:
            page = await table_then(session, table or "", epoch=epoch, moment=moment, key=row_key, offset=offset, limit=limit)
        return StateAtView(
            epoch=epoch,
            year=year,
            season=season,
            day=day,
            hour=hour,
            node_id=node_id,
            table_name=table,
            offset=offset,
            limit=limit,
            total=page.total,
            rows=then_rows(page),
        )


@router.get("/records/search", response_model=FactSearchView)
async def search_by_facts(
    services: ServicesDep,
    *,
    fact: Annotated[str | None, Query(max_length=120)] = None,
    enum_name: Annotated[str | None, Query(max_length=120)] = None,
    enum_value: Annotated[str | None, Query(max_length=120)] = None,
    node_id: Annotated[int | None, Query(ge=1)] = None,
    kind: Annotated[str | None, Query(max_length=120)] = None,
    action: Annotated[StepAction | None, Query()] = None,
    instrument_kind: Annotated[InstrumentKind | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX)] = 50,
) -> FactSearchView:
    query = RecordQuery(fact_key=fact, enum_name=enum_name, enum_value=enum_value, node_id=node_id, kind=kind, action=action, instrument_kind=instrument_kind)
    async with reader(services) as session:
        total, hits = await search_records(session, query, offset=offset, limit=limit)
        return FactSearchView(offset=offset, limit=limit, total=total, hits=[FactSearchHit.model_validate(asdict(hit)) for hit in hits])
