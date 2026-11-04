from fastapi import APIRouter, Path

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.profiles import ProfileColumnRecord, ProfileTableRecord
from aerona.core.errors import NotFoundError
from aerona.db.tables.node import NodeRow
from aerona.services.player.profiles import profile_tables

router = APIRouter(tags=["mechanics"])


@router.get("/nodes/{node_id}/profiles", response_model=list[ProfileTableRecord])
async def node_profiles(services: ServicesDep, node_id: int = Path(ge=1)) -> list[ProfileTableRecord]:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError("No such record.")
        tables = await profile_tables(session, node_id)
    return [
        ProfileTableRecord(
            table=table.table,
            lockable=table.lockable,
            columns=[
                ProfileColumnRecord(
                    name=column.name,
                    kind=column.kind,
                    value=column.value,
                    options=list(column.options),
                    nullable=column.nullable,
                    held=column.held,
                    pinned=column.pinned,
                )
                for column in table.columns
            ],
        )
        for table in tables
    ]
