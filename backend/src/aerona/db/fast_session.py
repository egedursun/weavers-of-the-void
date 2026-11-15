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

from aerona.db.read_memo import memo_of, table_names, track_dirty

PREFIX_KEYS = 2
COLUMN_KEYS: dict[Mapper[Any], frozenset[str]] = {}


def column_keys(mapper: Mapper[Any]) -> frozenset[str]:
    found = COLUMN_KEYS.get(mapper)
    if found is None:
        found = COLUMN_KEYS[mapper] = frozenset(prop.key for prop in mapper.column_attrs if not prop.deferred)
    return found


class TrackedSession(Session):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        track_dirty(self)

    def expunge_all(self) -> None:
        super().expunge_all()
        track_dirty(self)


class FastSession(AsyncSession):
    sync_session_class = TrackedSession

    async def delete(self, instance: object) -> None:
        if instance_state(instance).pending:
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
        if not isinstance(ident, dict) and all(part is None for part in (ident if isinstance(ident, tuple | list) else (ident,))):
            return None
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
                if state.dict.keys() >= column_keys(mapper):
                    return known
                return await super().get(entity, ident, populate_existing=True)
        return await self.load_unknown(entity, mapper, ident, key)

    async def load_unknown[O](self, entity: _EntityBindKey[O], mapper: Mapper[O], ident: _PKIdentityArgument, key: Any) -> O | None:
        tables = table_names(mapper.tables)
        if len(mapper.primary_key) == PREFIX_KEYS and isinstance(ident, tuple | list):
            siblings = await self.prefix_keys(mapper, ident[0], tables)
            if siblings is not None:
                return siblings.get(tuple(ident))
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

    async def prefix_keys[O](self, mapper: Mapper[O], value: Any, tables: frozenset[str]) -> dict[tuple[Any, ...], O] | None:
        name = f"prefix_keys:{','.join(sorted(tables))}"
        memo = memo_of(self, name, tables)
        if memo is not None and value in memo:
            known: dict[tuple[Any, ...], O] = memo[value]
            return known
        siblings = await self.prefix_rows(mapper, value, tables)
        if siblings is None:
            return None
        keyed: dict[tuple[Any, ...], O] = {}
        for row in siblings:
            keyed.setdefault(tuple(mapper.primary_key_from_instance(row)), row)
        after = memo_of(self, name, tables)
        if after is not None:
            after[value] = keyed
        return keyed

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
