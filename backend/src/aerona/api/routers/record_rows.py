from typing import Any

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.orm import Mapper

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.body import nodes_of
from aerona.api.schemas.record_rows import ThingRecordColumnView, ThingRecordNodeView, ThingRecordRowView, ThingRecordsView, ThingRecordTableView
from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.db.base import Base
from aerona.db.profile_guard import LOCK_COLUMN, NODE_TABLES, held_columns, owned_shape, table_name
from aerona.services.player.profiles import column_kind, scalar
from aerona.services.player.record_rows import JSON_KIND, editable_columns, is_json

router = APIRouter(tags=["record-rows"])


def shaped() -> list[Mapper[Any]]:
    return sorted(
        (
            mapper
            for mapper in Base.registry.mappers
            if table_name(mapper) not in NODE_TABLES and table_name(mapper) not in BOOKKEEPING_TABLES and owned_shape(mapper) is not None
        ),
        key=table_name,
    )


def columns_of(mapper: Mapper[Any]) -> list[ThingRecordColumnView]:
    shape = owned_shape(mapper)
    owners = set(shape.owners) if shape is not None else set()
    keys = {mapper.get_property_by_column(column).key for column in mapper.primary_key}
    editable = set(editable_columns(mapper))
    found: list[ThingRecordColumnView] = []
    for attribute in mapper.column_attrs:
        name = attribute.key
        if name == LOCK_COLUMN:
            continue
        kind = (JSON_KIND, ()) if is_json(mapper, name) else column_kind(mapper, name)
        if kind is None:
            continue
        column = mapper.columns[name]
        required = not column.nullable and column.default is None and column.server_default is None and not (name in keys and column.autoincrement is True)
        found.append(
            ThingRecordColumnView(
                name=name,
                kind=kind[0],
                options=list(kind[1]),
                nullable=bool(column.nullable),
                primary=name in keys,
                owner=name in owners,
                required=bool(required),
                editable=name in editable,
            )
        )
    return found


def plain(value: Any) -> Any:
    return value if isinstance(value, list | dict) else scalar(value)


@router.get("/records/{node_id}/rows", response_model=ThingRecordsView)
async def record_rows(services: ServicesDep, node_id: int = Path(ge=1)) -> ThingRecordsView:
    tables: list[ThingRecordTableView] = []
    creatable: list[ThingRecordTableView] = []
    async with reader(services) as session:
        for mapper in shaped():
            shape = owned_shape(mapper)
            if shape is None:
                continue
            columns = columns_of(mapper)
            names = [column.name for column in columns]
            keys = [mapper.get_property_by_column(column).key for column in mapper.primary_key]
            label = table_name(mapper).replace("_", " ").capitalize()
            creatable.append(ThingRecordTableView(table=table_name(mapper), label=label, columns=columns, rows=[]))
            statement = select(mapper.class_).where(or_(*(getattr(mapper.class_, owner) == node_id for owner in shape.owners)))
            found = [
                ThingRecordRowView(
                    key={key: plain(getattr(row, key)) for key in keys},
                    values={name: plain(getattr(row, name)) for name in names},
                    held=sorted(held_columns(row)),
                )
                for row in await session.scalars(statement)
            ]
            if found:
                tables.append(ThingRecordTableView(table=table_name(mapper), label=label, columns=columns, rows=found))
        referenced = {
            value for table in tables for column in table.columns if column.owner for row in table.rows if isinstance(value := row.values.get(column.name), int)
        }
        known = await nodes_of(session, referenced)
    labels = {str(node): ThingRecordNodeView(name=name, link=link) for node, (name, link) in known.items()}
    return ThingRecordsView(node_id=node_id, tables=tables, creatable=creatable, names=labels)
