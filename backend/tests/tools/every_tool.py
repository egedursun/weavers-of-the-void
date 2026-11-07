import enum
import types
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from annotated_types import Ge, MaxLen, MinLen
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from sqlalchemy.ext.asyncio import AsyncSession

from tests.tools.factories import Realm

TEXT = (
    "The keepers of the valley walked the old roads at dawn, carrying lamps and ledgers, and spoke at every gate "
    "about the seasons to come; their words were written down by the young scribes, who copied each line twice "
    "so that nothing would be lost when the rains came again and the river rose over the lower fields."
)

Ids = dict[str, int]
Setup = Callable[[AsyncSession, Realm], Awaitable[Ids]]
Arguments = Callable[[Realm, Ids], dict[str, Any]]
Actor = Callable[[Realm, Ids], int]
Lookup = Callable[[AsyncSession, Realm, Ids], Awaitable[Ids]]


@dataclass(frozen=True)
class Step:
    tool: str
    arguments: Callable[[Realm, Ids], dict[str, Any]]
    actor: Actor | None = None


async def nothing(_session: AsyncSession, _realm: Realm) -> Ids:
    return {}


def no_arguments(_realm: Realm, _ids: Ids) -> dict[str, Any]:
    return {}


async def keep(_session: AsyncSession, _realm: Realm, ids: Ids) -> Ids:
    return ids


def combined(*setups: Setup) -> Setup:
    async def run(session: AsyncSession, realm: Realm) -> Ids:
        ids: Ids = {}
        for setup in setups:
            ids.update(await setup(session, realm))
            await session.flush()
        return ids

    return run


@dataclass(frozen=True)
class Case:
    arguments: Arguments = no_arguments
    setup: Setup = nothing
    actor: Actor | None = None
    prelude: tuple[Step, ...] = ()
    lookup: Lookup = keep
    action_points: int = 12


def text_for(info: FieldInfo) -> str:
    low = next((item.min_length for item in info.metadata if isinstance(item, MinLen)), 0)
    high = next((item.max_length for item in info.metadata if isinstance(item, MaxLen)), len(TEXT))
    body = TEXT
    while len(body) < low:
        body = f"{body} {TEXT}"
    return body[:high].rstrip()


def members(annotation: Any) -> list[Any]:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        return [arg for arg in typing.get_args(annotation) if arg is not type(None)]
    return [annotation]


def filler(info: FieldInfo) -> Any:
    for kind in members(info.annotation):
        if isinstance(kind, type) and issubclass(kind, enum.Enum):
            return next(iter(kind)).value
        if kind is str:
            return text_for(info)
        if kind is bool:
            return False
        if kind is int:
            return next((item.ge for item in info.metadata if isinstance(item, Ge)), 1) or 1
    raise AssertionError(f"no filler for {info.annotation}")


def complete(model: type[BaseModel], arguments: dict[str, Any]) -> dict[str, Any]:
    filled = dict(arguments)
    for name, info in model.model_fields.items():
        if name in filled or not info.is_required():
            continue
        if name.endswith("_id") or name.endswith("_ids") or name == "id":
            raise AssertionError(f"{model.__name__}.{name} needs an explicit id")
        filled[name] = filler(info)
    return filled
