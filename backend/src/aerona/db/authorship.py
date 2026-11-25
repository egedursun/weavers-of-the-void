from sqlalchemy import ColumnElement, String, or_, true
from sqlalchemy.orm import InstrumentedAttribute, Mapped, mapped_column

from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH
from aerona.core.account_scope import AccountRef, current_account
from aerona.db.record_context import current_scope
from aerona.domain.enums.node import ActorKind


def hand_of(actor_kind: ActorKind | None) -> AccountRef | None:
    account = current_account()
    if account is None or actor_kind is not ActorKind.CREATOR:
        return None
    return account


def scoped_hand() -> AccountRef | None:
    scope = current_scope()
    return hand_of(scope.actor_kind if scope is not None else None)


def scoped_hand_id() -> int | None:
    found = scoped_hand()
    return found.id if found is not None else None


def scoped_hand_name() -> str | None:
    found = scoped_hand()
    return found.name[:AUTHOR_NAME_MAX_LENGTH] if found is not None else None


def account_id() -> int | None:
    found = current_account()
    return found.id if found is not None else None


def account_name() -> str | None:
    found = current_account()
    return found.name[:AUTHOR_NAME_MAX_LENGTH] if found is not None else None


class OwnedByAccount:
    author_account_id: Mapped[int | None] = mapped_column(default=account_id)
    author_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH), default=account_name)
    shared: Mapped[bool] = mapped_column(default=False, server_default="0")


class HandAuthored:
    author_account_id: Mapped[int | None] = mapped_column(default=scoped_hand_id)
    author_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH), default=scoped_hand_name)


AuthorColumn = InstrumentedAttribute[int | None]
SharedColumn = InstrumentedAttribute[bool]


def mine(author: AuthorColumn) -> ColumnElement[bool]:
    account = current_account()
    return true() if account is None else author == account.id


def visible(author: AuthorColumn, shared: SharedColumn) -> ColumnElement[bool]:
    account = current_account()
    return true() if account is None else or_(author == account.id, author.is_(None), shared.is_(True))


def may_see(author_account_id: int | None, shared: bool) -> bool:
    account = current_account()
    return account is None or author_account_id is None or shared or author_account_id == account.id


def owns(author_account_id: int | None) -> bool:
    account = current_account()
    return account is None or author_account_id is None or author_account_id == account.id
