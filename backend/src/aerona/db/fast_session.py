from collections.abc import Sequence
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper, ORMExecuteState, Session, class_mapper
from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
from sqlalchemy.orm.attributes import instance_state
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.orm.session import _EntityBindKey, _PKIdentityArgument
from sqlalchemy.sql.selectable import ForUpdateParameter
from sqlalchemy.util import EMPTY_DICT

from aerona.db.read_memo import memo_of, table_names

PREFIX_KEYS = 2
COLUMN_KEYS: dict[Mapper[Any], tuple[str, ...]] = {}


def column_keys(mapper: Mapper[Any]) -> tuple[str, ...]:
    found = COLUMN_KEYS.get(mapper)
    if found is None:
        found = COLUMN_KEYS[mapper] = tuple(prop.key for prop in mapper.column_attrs if not prop.deferred)
    return found


class FastSession(AsyncSession):
    async def delete(self, instance: object) -> None:
        if instance in self.sync_session.new:
            self.sync_session.expunge(instance)
            return
        await super().delete(instance)

    async def get[O](
        self,
        entity: _EntityBindKey[O],
        ident: _PKIdentityArgument,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool | None = None,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,
        execution_options: OrmExecuteOptionsParameter = EMPTY_DICT,
    ) -> O | None:
        plain = not options and not populate_existing and not with_for_update and identity_token is None and not execution_options
        mapper = entity if isinstance(entity, Mapper) else class_mapper(entity)
        if not plain or isinstance(ident, dict):
            return await super().get(
                entity,
                ident,
                options=options,
                populate_existing=populate_existing,
                with_for_update=with_for_update,
                identity_token=identity_token,
                execution_options=execution_options,
            )
        key = mapper.identity_key_from_primary_key(tuple(ident) if isinstance(ident, tuple | list) else (ident,))
        known = self.sync_session.identity_map.get(key)
        if known is not None:
            state = instance_state(known)
            if not state.expired and state.mapper.isa(mapper):
                if all(key in state.dict for key in column_keys(mapper)):
                    return known
                return await super().get(entity, ident, populate_existing=True)
        tables = table_names(mapper.tables)
        if len(mapper.primary_key) == PREFIX_KEYS and isinstance(ident, tuple | list):
            siblings = await self.prefix_rows(mapper, ident[0], tables)
            if siblings is not None:
                wanted = tuple(ident)
                return next((row for row in siblings if tuple(mapper.primary_key_from_instance(row)) == wanted), None)
        name = f"missing:{','.join(sorted(tables))}"
        missing = memo_of(self, name, tables)
        if missing is not None and key in missing:
            return None
        loaded = await super().get(entity, ident)
        if loaded is None:
            after = memo_of(self, name, tables)
            if after is not None:
                after[key] = True
        return loaded

    async def prefix_rows[O](self, mapper: Mapper[O], value: Any, tables: frozenset[str]) -> list[O] | None:
        name = f"prefix:{','.join(sorted(tables))}"
        memo = memo_of(self, name, tables)
        if memo is None:
            return None
        found: list[O] | None = memo.get(value)
        if found is None:
            found = list(await self.scalars(select(mapper).where(mapper.primary_key[0] == value)))
            after = memo_of(self, name, tables)
            if after is None:
                return None
            after[value] = found
        return found


async def rows_by_prefix[O](session: AsyncSession, model: type[O], value: Any) -> list[O]:
    mapper = class_mapper(model)
    if isinstance(session, FastSession):
        found = await session.prefix_rows(mapper, value, table_names(mapper.tables))
        if found is not None:
            return list(found)
    return list(await session.scalars(select(model).where(mapper.primary_key[0] == value)))


def fetch_matches(state: ORMExecuteState) -> None:
    if (state.is_update or state.is_delete) and not state.is_executemany and state.execution_options.get("synchronize_session") is None:
        state.update_execution_options(synchronize_session="fetch")


event.listen(Session, "do_orm_execute", fetch_matches)
