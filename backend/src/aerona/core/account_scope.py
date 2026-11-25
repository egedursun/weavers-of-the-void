import asyncio
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from contextvars import Context, ContextVar, copy_context
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccountRef:
    id: int
    name: str


CURRENT_ACCOUNT: ContextVar[AccountRef | None] = ContextVar("current_account", default=None)
CURRENT_WORKSPACE: ContextVar[int | None] = ContextVar("current_workspace", default=None)


def current_account() -> AccountRef | None:
    return CURRENT_ACCOUNT.get()


@contextmanager
def acting_account(account: AccountRef | None) -> Iterator[None]:
    token = CURRENT_ACCOUNT.set(account)
    try:
        yield
    finally:
        CURRENT_ACCOUNT.reset(token)


def current_workspace() -> int | None:
    return CURRENT_WORKSPACE.get()


def enter_workspace(workspace_id: int | None) -> None:
    CURRENT_WORKSPACE.set(workspace_id)


PERSON_VARS: list[ContextVar[Any]] = [CURRENT_ACCOUNT, CURRENT_WORKSPACE]


def bind_to_person(variable: ContextVar[Any]) -> None:
    if variable not in PERSON_VARS:
        PERSON_VARS.append(variable)


def unbound_context() -> Context:
    context = copy_context()
    for variable in PERSON_VARS:
        context.run(variable.set, None)
    return context


def detached[T](work: Coroutine[Any, Any, T]) -> "asyncio.Task[T]":
    return asyncio.get_running_loop().create_task(work, context=unbound_context())
