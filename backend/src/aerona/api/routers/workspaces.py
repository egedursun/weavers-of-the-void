import asyncio

from fastapi import APIRouter, Path, Query

from aerona.api.dependencies import AccountsDep, SignedDep
from aerona.api.routers.auth import account_view
from aerona.api.routers.library import LibraryDep
from aerona.api.schemas.accounts import (
    CandidateView,
    CanonApprovalPut,
    IssuedPassword,
    MemberAdd,
    MemberAdded,
    MemberRole,
    OverridePut,
    PermissionRow,
    PermissionsPut,
    PersonAccess,
    UniverseAccessView,
    WorkspaceMemberView,
    WorkspaceName,
    WorkspaceView,
)
from aerona.api.schemas.common import Done
from aerona.constants.accounts import EMAIL_MAX_LENGTH
from aerona.core.errors import NotFoundError
from aerona.domain.enums.accounts import AccountStatus, Permission, TunedRole
from aerona.services.accounts.access import effective_role
from aerona.services.accounts.permissions import PERMISSION_LABELS, PERMISSION_MEANINGS, default_allowed
from aerona.services.accounts.service import AccountService
from aerona.services.accounts.store import MemberRecord, WorkspaceRecord
from aerona.services.library.catalogue import UniverseRecord
from aerona.services.library.service import LibraryService
from aerona.services.library.trash import set_entry_workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

WorkspaceId = Path(ge=1)
NOT_HERE = "That universe is not in this workspace."
LEFT = "You left the workspace."
REMOVED = "The member is removed; everything they made keeps their name."
DELETED = "The workspace is deleted; its universes wait in your trash."
NO_WORKSPACE = "No such workspace."


async def workspace_view(accounts: AccountService, workspace: WorkspaceRecord, account_id: int) -> WorkspaceView:
    role = await accounts.role_in(workspace.id, account_id)
    if role is None:
        raise NotFoundError(NO_WORKSPACE)
    return WorkspaceView(
        id=workspace.id,
        name=workspace.name,
        kind=workspace.kind,
        role=role,
        member_count=len(await accounts.members(workspace.id)),
        universe_count=len(await accounts.visible(account_id, workspace.id)),
        created_at=workspace.created_at,
    )


async def member_view(accounts: AccountService, member: MemberRecord) -> WorkspaceMemberView:
    return WorkspaceMemberView(
        account=account_view(member.account),
        role=member.role,
        added_at=member.added_at,
        universe_count=len(await accounts.visible(member.account.id, member.workspace_id)),
    )


async def universe_here(library: LibraryService, workspace_id: int, universe_id: str) -> UniverseRecord:
    record = await library.catalogue.get(universe_id)
    if record is None or record.workspace_id != workspace_id:
        raise NotFoundError(NOT_HERE)
    return record


async def access_view(accounts: AccountService, universe: UniverseRecord) -> UniverseAccessView:
    table = await accounts.access_table(universe)
    overrides = {override.account_id: override.role for override in table.overrides}
    people = [
        PersonAccess(
            account=account_view(member.account),
            workspace_role=member.role,
            role=effective_role(member.role, overrides.get(member.account.id)),
            overridden=member.account.id in overrides,
        )
        for member in table.members
    ]
    editor, viewer = table.changes.get(TunedRole.EDITOR, {}), table.changes.get(TunedRole.VIEWER, {})
    rows = [
        PermissionRow(
            permission=permission,
            label=PERMISSION_LABELS[permission],
            meaning=PERMISSION_MEANINGS[permission],
            editor_default=default_allowed(TunedRole.EDITOR, permission),
            viewer_default=default_allowed(TunedRole.VIEWER, permission),
            editor=editor.get(permission, default_allowed(TunedRole.EDITOR, permission)),
            viewer=viewer.get(permission, default_allowed(TunedRole.VIEWER, permission)),
        )
        for permission in Permission
    ]
    assert universe.workspace_id is not None
    return UniverseAccessView(
        universe_id=universe.id,
        universe_name=universe.name,
        workspace_id=universe.workspace_id,
        canon_approval=universe.canon_approval,
        people=people,
        permissions=rows,
    )


@router.get("", response_model=list[WorkspaceView])
async def list_workspaces(signed: SignedDep, accounts: AccountsDep) -> list[WorkspaceView]:
    return [await workspace_view(accounts, workspace, signed.account.id) for workspace, _role in await accounts.workspaces(signed.account)]


@router.post("", response_model=WorkspaceView, status_code=201)
async def create_workspace(body: WorkspaceName, signed: SignedDep, accounts: AccountsDep) -> WorkspaceView:
    return await workspace_view(accounts, await accounts.create_workspace(signed.account, body.name), signed.account.id)


@router.patch("/{workspace_id}", response_model=WorkspaceView)
async def rename_workspace(body: WorkspaceName, signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId) -> WorkspaceView:
    return await workspace_view(accounts, await accounts.rename_workspace(workspace_id, body.name), signed.account.id)


@router.delete("/{workspace_id}", response_model=Done)
async def delete_workspace(signed: SignedDep, accounts: AccountsDep, library: LibraryDep, workspace_id: int = WorkspaceId) -> Done:
    await accounts.deletable(workspace_id)
    personal = await accounts.store.personal_workspace(signed.account.id)
    for universe_id in await accounts.store.universe_ids(workspace_id):
        entry = await library.delete(universe_id)
        if personal is not None:
            await asyncio.to_thread(set_entry_workspace, entry, personal.id)
    await accounts.remove_workspace(workspace_id)
    return Done(message=DELETED)


@router.post("/{workspace_id}/leave", response_model=Done)
async def leave_workspace(signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId) -> Done:
    await accounts.leave(signed.account, workspace_id)
    return Done(message=LEFT)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberView])
async def list_members(accounts: AccountsDep, workspace_id: int = WorkspaceId) -> list[WorkspaceMemberView]:
    return [await member_view(accounts, member) for member in await accounts.members(workspace_id)]


@router.get("/{workspace_id}/candidates", response_model=list[CandidateView])
async def find_candidates(
    accounts: AccountsDep, workspace_id: int = WorkspaceId, q: str = Query(min_length=1, max_length=EMAIL_MAX_LENGTH)
) -> list[CandidateView]:
    return [
        CandidateView(id=account.id, username=account.username, display_name=account.display_name, avatar_tone=account.avatar_tone)
        for account in await accounts.candidates(workspace_id, q)
    ]


@router.post("/{workspace_id}/members", response_model=MemberAdded, status_code=201)
async def add_member(body: MemberAdd, signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId) -> MemberAdded:
    account, issued = await accounts.add_member(
        signed.account,
        workspace_id,
        body.role,
        account_id=body.account_id,
        username=body.username,
        email=body.email,
        display_name=body.display_name,
    )
    member = next(member for member in await accounts.members(workspace_id) if member.account.id == account.id)
    return MemberAdded(member=await member_view(accounts, member), temporary_password=issued)


@router.patch("/{workspace_id}/members/{account_id}", response_model=WorkspaceMemberView)
async def change_member(body: MemberRole, accounts: AccountsDep, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)) -> WorkspaceMemberView:
    await accounts.change_member_role(workspace_id, account_id, body.role)
    member = next(member for member in await accounts.members(workspace_id) if member.account.id == account_id)
    return await member_view(accounts, member)


@router.delete("/{workspace_id}/members/{account_id}", response_model=Done)
async def remove_member(accounts: AccountsDep, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)) -> Done:
    await accounts.remove_member(workspace_id, account_id)
    return Done(message=REMOVED)


@router.post("/{workspace_id}/members/{account_id}/reset-password", response_model=IssuedPassword)
async def reset_member_password(signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)) -> IssuedPassword:
    target = await accounts.member_target(signed.account, workspace_id, account_id)
    issued = await accounts.reset_password(target)
    return IssuedPassword(account=account_view(issued.account), temporary_password=issued.temporary_password)


@router.post("/{workspace_id}/members/{account_id}/deactivate", response_model=WorkspaceMemberView)
async def deactivate_member(signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)) -> WorkspaceMemberView:
    target = await accounts.member_target(signed.account, workspace_id, account_id)
    await accounts.set_status(target, AccountStatus.DEACTIVATED)
    member = next(member for member in await accounts.members(workspace_id) if member.account.id == account_id)
    return await member_view(accounts, member)


@router.post("/{workspace_id}/members/{account_id}/reactivate", response_model=WorkspaceMemberView)
async def reactivate_member(signed: SignedDep, accounts: AccountsDep, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)) -> WorkspaceMemberView:
    target = await accounts.member_target(signed.account, workspace_id, account_id)
    await accounts.set_status(target, AccountStatus.ACTIVE)
    member = next(member for member in await accounts.members(workspace_id) if member.account.id == account_id)
    return await member_view(accounts, member)


@router.get("/{workspace_id}/universes/{universe_id}/access", response_model=UniverseAccessView)
async def universe_access(accounts: AccountsDep, library: LibraryDep, universe_id: str, workspace_id: int = WorkspaceId) -> UniverseAccessView:
    return await access_view(accounts, await universe_here(library, workspace_id, universe_id))


@router.put("/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}", response_model=UniverseAccessView)
async def put_override(
    *,
    body: OverridePut,
    signed: SignedDep,
    accounts: AccountsDep,
    library: LibraryDep,
    universe_id: str,
    workspace_id: int = WorkspaceId,
    account_id: int = Path(ge=1),
) -> UniverseAccessView:
    universe = await universe_here(library, workspace_id, universe_id)
    await accounts.set_override(signed.account, universe, account_id, body.role)
    return await access_view(accounts, universe)


@router.delete("/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}", response_model=UniverseAccessView)
async def clear_override(
    accounts: AccountsDep, library: LibraryDep, universe_id: str, workspace_id: int = WorkspaceId, account_id: int = Path(ge=1)
) -> UniverseAccessView:
    universe = await universe_here(library, workspace_id, universe_id)
    await accounts.clear_override(universe, account_id)
    return await access_view(accounts, universe)


@router.put("/{workspace_id}/universes/{universe_id}/access/permissions", response_model=UniverseAccessView)
async def put_permissions(
    body: PermissionsPut, accounts: AccountsDep, library: LibraryDep, universe_id: str, workspace_id: int = WorkspaceId
) -> UniverseAccessView:
    universe = await universe_here(library, workspace_id, universe_id)
    await accounts.set_permissions(universe, {TunedRole.EDITOR: dict(body.editor), TunedRole.VIEWER: dict(body.viewer)})
    return await access_view(accounts, universe)


@router.delete("/{workspace_id}/universes/{universe_id}/access/permissions", response_model=UniverseAccessView)
async def reset_permissions(accounts: AccountsDep, library: LibraryDep, universe_id: str, workspace_id: int = WorkspaceId) -> UniverseAccessView:
    universe = await universe_here(library, workspace_id, universe_id)
    await accounts.reset_permissions(universe)
    return await access_view(accounts, universe)


@router.put("/{workspace_id}/universes/{universe_id}/access/canon-approval", response_model=UniverseAccessView)
async def put_canon_approval(
    body: CanonApprovalPut, accounts: AccountsDep, library: LibraryDep, universe_id: str, workspace_id: int = WorkspaceId
) -> UniverseAccessView:
    universe = await universe_here(library, workspace_id, universe_id)
    await accounts.set_canon_approval(universe, body.on)
    return await access_view(accounts, await universe_here(library, workspace_id, universe_id))
