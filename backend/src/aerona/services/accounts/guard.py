from contextvars import ContextVar
from dataclasses import dataclass

from pydantic import BaseModel

from aerona.core.account_scope import bind_to_person, current_account
from aerona.domain.enums.accounts import Permission
from aerona.services.accounts.access import UniverseAccess
from aerona.services.accounts.lever_holds import LEVER_HOLD_FIELDS
from aerona.services.accounts.permissions import lever_permission
from aerona.services.accounts.service import refuse


@dataclass(frozen=True)
class GrantedAccess:
    access: UniverseAccess
    universe_name: str
    canon_approval: bool


CURRENT_GRANT: ContextVar[GrantedAccess | None] = ContextVar("current_grant", default=None)
bind_to_person(CURRENT_GRANT)


def enter_grant(grant: GrantedAccess | None) -> None:
    CURRENT_GRANT.set(grant)


def current_grant() -> GrantedAccess | None:
    return CURRENT_GRANT.get()


def ensure_allowed(permission: Permission) -> None:
    grant = CURRENT_GRANT.get()
    if grant is None or grant.access.allows(permission):
        return
    raise refuse(permission, grant.access, grant.universe_name)


def holds_something(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return False


def ensure_lever_allowed(action_id: str, command: BaseModel | None = None) -> None:
    ensure_allowed(lever_permission(action_id))
    if command is not None and any(holds_something(getattr(command, name, None)) for name in LEVER_HOLD_FIELDS.get(action_id, ())):
        ensure_allowed(Permission.LOCK_CANON)


def ensure_may_undo(author_account_id: int | None) -> None:
    account = current_account()
    if account is not None and author_account_id == account.id:
        return
    ensure_allowed(Permission.UNDO_ANY)
