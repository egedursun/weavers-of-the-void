from datetime import datetime

from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.constants.accounts import DISPLAY_NAME_MAX_LENGTH, EMAIL_MAX_LENGTH, PASSWORD_MAX_LENGTH, USERNAME_MAX_LENGTH, WORKSPACE_NAME_MAX_LENGTH
from aerona.domain.enums.accounts import (
    AccountStatus,
    AvatarTone,
    Permission,
    ServerRole,
    UniverseRole,
    WorkspaceKind,
    WorkspaceRole,
)

LOGIN_MAX_LENGTH = EMAIL_MAX_LENGTH


class AccountProfileView(ApiModel):
    id: int
    username: str
    email: str
    display_name: str
    status: AccountStatus
    server_role: ServerRole
    avatar_tone: AvatarTone
    must_change_password: bool
    created_at: datetime
    last_sign_in_at: datetime | None
    password_changed_at: datetime | None
    locked_until: datetime | None


class AuthState(ApiModel):
    setup_required: bool
    account: AccountProfileView | None
    must_change_password: bool
    password_min_length: int


class SetupRequest(RequestModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)
    email: str = Field(min_length=3, max_length=EMAIL_MAX_LENGTH)
    display_name: str = Field(min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class SignInRequest(RequestModel):
    login: str = Field(min_length=1, max_length=LOGIN_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class PasswordChange(RequestModel):
    current: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class ProfilePatch(RequestModel):
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)
    email: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    avatar_tone: AvatarTone | None = None


class SessionView(ApiModel):
    id: int
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    user_agent: str
    address: str
    current: bool


class SessionsEnded(ApiModel):
    ended: int


class AccountCreate(RequestModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)
    email: str = Field(min_length=3, max_length=EMAIL_MAX_LENGTH)
    display_name: str = Field(min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    server_role: ServerRole = ServerRole.MEMBER


class AccountPatch(RequestModel):
    status: AccountStatus | None = None
    server_role: ServerRole | None = None


class IssuedPassword(ApiModel):
    account: AccountProfileView
    temporary_password: str


class WorkspaceView(ApiModel):
    id: int
    name: str
    kind: WorkspaceKind
    role: WorkspaceRole
    member_count: int
    universe_count: int
    created_at: datetime


class WorkspaceName(RequestModel):
    name: str = Field(min_length=1, max_length=WORKSPACE_NAME_MAX_LENGTH)


class WorkspaceMemberView(ApiModel):
    account: AccountProfileView
    role: WorkspaceRole
    added_at: datetime
    universe_count: int


class MemberAdd(RequestModel):
    role: WorkspaceRole = WorkspaceRole.VIEWER
    account_id: int | None = Field(default=None, ge=1)
    username: str | None = Field(default=None, max_length=USERNAME_MAX_LENGTH)
    email: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)


class MemberAdded(ApiModel):
    member: WorkspaceMemberView
    temporary_password: str | None


class MemberRole(RequestModel):
    role: WorkspaceRole


class PersonAccess(ApiModel):
    account: AccountProfileView
    workspace_role: WorkspaceRole
    role: UniverseRole
    overridden: bool


class PermissionRow(ApiModel):
    permission: Permission
    label: str
    meaning: str
    editor_default: bool
    viewer_default: bool
    editor: bool
    viewer: bool


class UniverseAccessView(ApiModel):
    universe_id: str
    universe_name: str
    workspace_id: int
    canon_approval: bool
    people: list[PersonAccess]
    permissions: list[PermissionRow]


class OverridePut(RequestModel):
    role: UniverseRole


class PermissionsPut(RequestModel):
    editor: dict[Permission, bool] = Field(default_factory=dict)
    viewer: dict[Permission, bool] = Field(default_factory=dict)


class CanonApprovalPut(RequestModel):
    on: bool


class UniverseMove(RequestModel):
    workspace_id: int = Field(ge=1)


class CandidateView(ApiModel):
    id: int
    username: str
    display_name: str
    avatar_tone: AvatarTone
