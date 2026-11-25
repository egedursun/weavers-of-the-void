from collections.abc import Mapping
from dataclasses import dataclass

from aerona.domain.enums.accounts import Permission, TunedRole, UniverseRole, WorkspaceRole
from aerona.services.accounts.permissions import TUNED_OF, WORKSPACE_TO_UNIVERSE, permissions_of
from aerona.services.accounts.store import AccountStore
from aerona.services.library.catalogue import UniverseRecord


@dataclass(frozen=True)
class UniverseAccess:
    universe_id: str
    workspace_id: int | None
    workspace_role: WorkspaceRole | None
    role: UniverseRole
    overridden: bool
    permissions: frozenset[Permission]

    @property
    def admin(self) -> bool:
        return self.role is UniverseRole.ADMIN

    @property
    def visible(self) -> bool:
        return self.role is not UniverseRole.NONE

    def allows(self, permission: Permission) -> bool:
        return permission in self.permissions


def effective_role(workspace_role: WorkspaceRole | None, override: UniverseRole | None) -> UniverseRole:
    if workspace_role is None:
        return UniverseRole.NONE
    if override is not None:
        return override
    return WORKSPACE_TO_UNIVERSE[workspace_role]


def tuned_changes(changes: Mapping[TunedRole, Mapping[Permission, bool]], role: UniverseRole) -> Mapping[Permission, bool]:
    tuned = TUNED_OF.get(role)
    return changes.get(tuned, {}) if tuned is not None else {}


async def universe_access(store: AccountStore, account_id: int, universe: UniverseRecord) -> UniverseAccess:
    workspace_role = await store.role_in(universe.workspace_id, account_id) if universe.workspace_id is not None else None
    overrides = await store.overrides_of_account(account_id, (universe.id,)) if workspace_role is not None else {}
    override = overrides.get(universe.id)
    role = effective_role(workspace_role, override)
    changes = await store.permission_changes(universe.id) if role in TUNED_OF else {}
    return UniverseAccess(
        universe_id=universe.id,
        workspace_id=universe.workspace_id,
        workspace_role=workspace_role,
        role=role,
        overridden=override is not None,
        permissions=permissions_of(role, tuned_changes(changes, role)),
    )


async def visible_universes(store: AccountStore, account_id: int, workspace_id: int) -> frozenset[str]:
    workspace_role = await store.role_in(workspace_id, account_id)
    if workspace_role is None:
        return frozenset()
    ids = await store.universe_ids(workspace_id)
    overrides = await store.overrides_of_account(account_id, ids)
    return frozenset(universe_id for universe_id in ids if effective_role(workspace_role, overrides.get(universe_id)) is not UniverseRole.NONE)
