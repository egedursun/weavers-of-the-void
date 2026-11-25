import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aerona.constants.accounts import (
    ADDRESS_ATTEMPTS_FACTOR,
    ADDRESS_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    PERSONAL_WORKSPACE_NAME,
    SECONDS_PER_MINUTE,
    SESSION_TOUCH_SECONDS,
    USER_AGENT_MAX_LENGTH,
    USERNAME_PATTERN,
    WORKSPACE_NAME_MAX_LENGTH,
)
from aerona.core.account_scope import current_workspace
from aerona.core.errors import ConflictError, ForbiddenError, LockedError, NotFoundError, SignedOutError, ValidationFailedError
from aerona.domain.enums.accounts import (
    AccountStatus,
    AvatarTone,
    Permission,
    ServerRole,
    TunedRole,
    UniverseRole,
    WorkspaceKind,
    WorkspaceRole,
)
from aerona.domain.enums.library import LibraryEventKind
from aerona.services.accounts.access import UniverseAccess, universe_access, visible_universes
from aerona.services.accounts.passwords import (
    hash_password,
    needs_rehash,
    password_matches,
    password_problem,
    spend_time_on_missing_account,
    temporary_password,
)
from aerona.services.accounts.permissions import FIXED_PERMISSIONS, WORKSPACE_RANK, WORKSPACE_ROLE_WORDS, default_allowed, refusal_text
from aerona.services.accounts.sessions import AddressThrottle, SessionWindow, new_token, token_hash
from aerona.services.accounts.store import AccountRecord, AccountStore, MemberRecord, NewAccount, OverrideRecord, SessionRecord, WorkspaceRecord
from aerona.services.library.catalogue import Catalogue, UniverseRecord
from aerona.services.library.trash import stamp_workspace
from aerona.settings import Settings

USERNAME = re.compile(USERNAME_PATTERN)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TONES = tuple(AvatarTone)
SETUP_DONE = "This server already has an owner; sign in instead."
WRONG_LOGIN = "That username, e-mail or password is not right."
DEACTIVATED = "This account is deactivated; ask an administrator to reactivate it."
LOCKED = "Too many wrong passwords: this account is locked until {at:%H:%M} UTC."
SLOW_DOWN = "Too many failed sign-ins from this address; wait a few minutes and try again."
BAD_USERNAME = "A username has 3 to 32 lowercase letters, digits, dots, dashes or underscores."
BAD_EMAIL = "That is not an e-mail address."
BAD_DISPLAY_NAME = "A display name has 1 to 80 characters."
BAD_WORKSPACE_NAME = "A workspace name has 1 to 80 characters."
USERNAME_TAKEN = "That username is taken."
EMAIL_TAKEN = "That e-mail belongs to another account."
WRONG_CURRENT = "The current password is not right."
SAME_PASSWORD = "Choose a password different from the current one."
NO_ACCOUNT = "No such account."
NO_WORKSPACE = "No such workspace."
NO_SESSION = "No such session."
NOT_A_MEMBER = "That account is not a member of this workspace."
ALREADY_MEMBER = "That account is already a member of this workspace."
OWNER_PROTECTED = "The server owner cannot be deactivated, deleted or changed by others."
ADMINS_ONLY_BY_OWNER = "Only the server owner can manage server administrators."
OWNER_ONLY = "Only the server owner can do this."
NEW_OWNER_ADMIN = "Ownership passes only to an active server administrator."
NOT_YOURSELF = "You cannot do this to your own account."
LAST_ADMIN = "A workspace keeps at least one administrator."
PERSONAL_ALONE = "A personal workspace has its owner alone."
PERSONAL_KEPT = "A personal workspace stays while its account exists."
HOLDS_UNIVERSES = "{name}'s personal workspace still holds universes; move them or delete them first."
WORKSPACE_ADMIN_SCOPE = "Only a server administrator, or an administrator of every workspace this account belongs to, can do this."
INACTIVE_MEMBER = "A deactivated account cannot be added; reactivate it first."
ROLE_FORBIDDEN = "Your role in this workspace does not allow this."
NO_ACCESS = "You have no access to this universe."


@dataclass(frozen=True)
class SignedIn:
    account: AccountRecord
    session: SessionRecord
    token: str


@dataclass(frozen=True)
class Resolved:
    account: AccountRecord
    session: SessionRecord


@dataclass(frozen=True)
class Issued:
    account: AccountRecord
    temporary_password: str


@dataclass(frozen=True)
class AccessTable:
    universe: UniverseRecord
    members: list[MemberRecord]
    overrides: list[OverrideRecord]
    changes: dict[TunedRole, dict[Permission, bool]]


def now_utc() -> datetime:
    return datetime.now(UTC)


def clean_username(username: str) -> str:
    cleaned = username.strip().lower()
    if not USERNAME.match(cleaned):
        raise ValidationFailedError(BAD_USERNAME)
    return cleaned


def clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if len(cleaned) > EMAIL_MAX_LENGTH or not EMAIL.match(cleaned):
        raise ValidationFailedError(BAD_EMAIL)
    return cleaned


def clean_display_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > DISPLAY_NAME_MAX_LENGTH:
        raise ValidationFailedError(BAD_DISPLAY_NAME)
    return cleaned


def clean_workspace_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > WORKSPACE_NAME_MAX_LENGTH:
        raise ValidationFailedError(BAD_WORKSPACE_NAME)
    return cleaned


def tone_for(name: str) -> AvatarTone:
    return TONES[sum(ord(letter) for letter in name.casefold()) % len(TONES)]


def personal_name(display_name: str) -> str:
    return PERSONAL_WORKSPACE_NAME.format(name=display_name)[:WORKSPACE_NAME_MAX_LENGTH]


class AccountService:
    def __init__(self, catalogue: Catalogue, settings: Settings) -> None:
        self.catalogue = catalogue
        self.settings = settings
        self.store = AccountStore(catalogue)
        self.window = SessionWindow(settings.accounts_session_idle_days, settings.accounts_session_max_days)
        self.throttle = AddressThrottle(settings.accounts_lockout_attempts * ADDRESS_ATTEMPTS_FACTOR, settings.accounts_lockout_minutes * SECONDS_PER_MINUTE)
        self._setting_up = asyncio.Lock()
        self._ready = False

    async def ready(self) -> bool:
        if not self._ready:
            self._ready = await self.store.count() > 0
        return self._ready

    async def start(self) -> None:
        if not await self.ready():
            return
        owner = next((account for account in await self.store.accounts() if account.server_role is ServerRole.OWNER), None)
        if owner is not None:
            await self.adopt(owner)

    async def adopt(self, owner: AccountRecord) -> None:
        workspace = await self.store.personal_workspace(owner.id)
        if workspace is None:
            return
        await self.store.adopt_universes(workspace.id, owner.id, owner.display_name)
        await asyncio.to_thread(stamp_workspace, self.catalogue.paths.trash, workspace.id)

    async def note(self, kind: LibraryEventKind, subject: str, *, workspace_id: int | None = None, universe_id: str = "", detail: str = "") -> None:
        await self.catalogue.log(kind, universe_id, subject, detail, workspace_id=workspace_id)

    def problem(self, password: str, *, username: str, email: str) -> None:
        found = password_problem(password, username=username, email=email, min_length=self.settings.accounts_password_min_length)
        if found is not None:
            raise ValidationFailedError(found)

    async def _unique(self, *, username: str | None = None, email: str | None = None, keep: int | None = None) -> None:
        if username is not None and await self.store.taken(username=username, keep=keep):
            raise ConflictError(USERNAME_TAKEN)
        if email is not None and await self.store.taken(email=email, keep=keep):
            raise ConflictError(EMAIL_TAKEN)

    async def _new_account(
        self, *, username: str, email: str, display_name: str, password: str, must_change: bool, role: ServerRole, by: int | None
    ) -> AccountRecord:
        username, email, display_name = clean_username(username), clean_email(email), clean_display_name(display_name)
        await self._unique(username=username, email=email)
        if not must_change:
            self.problem(password, username=username, email=email)
        now = now_utc()
        account = await self.store.add_account(
            NewAccount(username, email, display_name, hash_password(password), must_change, role, tone_for(display_name), by), now
        )
        await self.store.add_workspace(personal_name(display_name), WorkspaceKind.PERSONAL, account.id, account.id, now)
        return account

    async def setup(self, *, username: str, email: str, display_name: str, password: str, user_agent: str, address: str) -> SignedIn:
        async with self._setting_up:
            if await self.ready():
                raise ConflictError(SETUP_DONE)
            owner = await self._new_account(
                username=username, email=email, display_name=display_name, password=password, must_change=False, role=ServerRole.OWNER, by=None
            )
            self._ready = True
        await self.adopt(owner)
        return await self._open_session(owner, user_agent=user_agent, address=address)

    async def _open_session(self, account: AccountRecord, *, user_agent: str, address: str) -> SignedIn:
        now = now_utc()
        token = new_token()
        session = await self.store.add_session(
            account.id, token_hash(token), now, self.window.expires(now), user_agent=user_agent[:USER_AGENT_MAX_LENGTH], address=address[:ADDRESS_MAX_LENGTH]
        )
        return SignedIn(account, session, token)

    async def sign_in(self, login: str, password: str, *, user_agent: str, address: str) -> SignedIn:
        if self.throttle.blocked(address):
            raise LockedError(SLOW_DOWN)
        account = await self.store.by_login(login)
        now = now_utc()
        if account is None:
            await asyncio.to_thread(spend_time_on_missing_account, password)
            self.throttle.fail(address)
            raise SignedOutError(WRONG_LOGIN)
        if account.locked_until is not None and account.locked_until > now:
            raise LockedError(LOCKED.format(at=account.locked_until))
        if not await asyncio.to_thread(password_matches, account.password_hash, password):
            self.throttle.fail(address)
            failed = account.failed_attempts + 1
            if failed >= self.settings.accounts_lockout_attempts:
                until = now + timedelta(minutes=self.settings.accounts_lockout_minutes)
                await self.store.change_account(account.id, failed_attempts=0, locked_until=until)
                raise LockedError(LOCKED.format(at=until))
            await self.store.change_account(account.id, failed_attempts=failed)
            raise SignedOutError(WRONG_LOGIN)
        if not account.active:
            raise SignedOutError(DEACTIVATED)
        self.throttle.clear(address)
        values: dict[str, object] = {"failed_attempts": 0, "locked_until": None, "last_sign_in_at": now}
        if needs_rehash(account.password_hash):
            values["password_hash"] = hash_password(password)
        account = await self.store.change_account(account.id, **values) or account
        return await self._open_session(account, user_agent=user_agent, address=address)

    async def resolve(self, token: str) -> Resolved | None:
        session = await self.store.session_by_hash(token_hash(token))
        if session is None:
            return None
        now = now_utc()
        if self.window.ended(last_used_at=session.last_used_at, expires_at=session.expires_at, now=now):
            await self.store.end_session(session.id)
            return None
        account = await self.store.account(session.account_id)
        if account is None or not account.active:
            await self.store.end_session(session.id)
            return None
        if (now - session.last_used_at).total_seconds() >= SESSION_TOUCH_SECONDS:
            await self.store.touch_session(session.id, now)
        return Resolved(account, session)

    async def sign_out(self, session_id: int) -> None:
        await self.store.end_session(session_id)

    async def sessions_of(self, account: AccountRecord) -> list[SessionRecord]:
        return await self.store.sessions_of(account.id)

    async def end_session(self, account: AccountRecord, session_id: int) -> None:
        if await self.store.end_sessions(account.id, only=session_id) == 0:
            raise NotFoundError(NO_SESSION)

    async def end_other_sessions(self, account: AccountRecord, keep: int) -> int:
        return await self.store.end_sessions(account.id, keep=keep)

    async def change_password(self, account: AccountRecord, current: str, new: str, keep_session: int) -> AccountRecord:
        if not await asyncio.to_thread(password_matches, account.password_hash, current):
            raise ValidationFailedError(WRONG_CURRENT)
        if current == new:
            raise ValidationFailedError(SAME_PASSWORD)
        self.problem(new, username=account.username, email=account.email)
        changed = await self.store.change_account(account.id, password_hash=hash_password(new), must_change_password=False, password_changed_at=now_utc())
        await self.store.end_sessions(account.id, keep=keep_session)
        return changed or account

    async def update_profile(self, account: AccountRecord, *, display_name: str | None, email: str | None, avatar_tone: AvatarTone | None) -> AccountRecord:
        values: dict[str, object] = {}
        if display_name is not None:
            values["display_name"] = clean_display_name(display_name)
        if email is not None:
            cleaned = clean_email(email)
            await self._unique(email=cleaned, keep=account.id)
            values["email"] = cleaned
        if avatar_tone is not None:
            values["avatar_tone"] = avatar_tone
        if not values:
            return account
        changed = await self.store.change_account(account.id, **values)
        if changed is None:
            raise NotFoundError(NO_ACCOUNT)
        if "display_name" in values:
            personal = await self.store.personal_workspace(account.id)
            if personal is not None:
                await self.store.rename_workspace(personal.id, personal_name(changed.display_name))
        return changed

    async def require_account(self, account_id: int) -> AccountRecord:
        found = await self.store.account(account_id)
        if found is None:
            raise NotFoundError(NO_ACCOUNT)
        return found

    async def accounts(self) -> list[AccountRecord]:
        return await self.store.accounts()

    def _may_manage(self, actor: AccountRecord, target: AccountRecord) -> None:
        if target.id == actor.id:
            raise ForbiddenError(NOT_YOURSELF)
        if target.server_role is ServerRole.OWNER:
            raise ForbiddenError(OWNER_PROTECTED)
        if target.server_role is ServerRole.ADMIN and actor.server_role is not ServerRole.OWNER:
            raise ForbiddenError(ADMINS_ONLY_BY_OWNER)

    async def create_account(self, actor: AccountRecord, *, username: str, email: str, display_name: str, server_role: ServerRole) -> Issued:
        if server_role is ServerRole.OWNER or (server_role is ServerRole.ADMIN and actor.server_role is not ServerRole.OWNER):
            raise ForbiddenError(ADMINS_ONLY_BY_OWNER)
        issued = temporary_password()
        account = await self._new_account(
            username=username, email=email, display_name=display_name, password=issued, must_change=True, role=server_role, by=actor.id
        )
        await self.note(LibraryEventKind.ACCOUNT_CREATED, account.display_name, workspace_id=current_workspace())
        return Issued(account, issued)

    async def reset_password(self, target: AccountRecord) -> Issued:
        issued = temporary_password()
        changed = await self.store.change_account(
            target.id, password_hash=hash_password(issued), must_change_password=True, failed_attempts=0, locked_until=None
        )
        await self.store.end_sessions(target.id)
        await self.note(LibraryEventKind.PASSWORD_RESET, target.display_name, workspace_id=current_workspace())
        return Issued(changed or target, issued)

    async def set_status(self, target: AccountRecord, status: AccountStatus) -> AccountRecord:
        changed = await self.store.change_account(target.id, status=status)
        if status is AccountStatus.DEACTIVATED:
            await self.store.end_sessions(target.id)
        kind = LibraryEventKind.ACCOUNT_DEACTIVATED if status is AccountStatus.DEACTIVATED else LibraryEventKind.ACCOUNT_REACTIVATED
        await self.note(kind, target.display_name, workspace_id=current_workspace())
        return changed or target

    async def admin_reset(self, actor: AccountRecord, target_id: int) -> Issued:
        target = await self.require_account(target_id)
        self._may_manage(actor, target)
        return await self.reset_password(target)

    async def edit_account(self, actor: AccountRecord, target_id: int, *, status: AccountStatus | None, server_role: ServerRole | None) -> AccountRecord:
        target = await self.require_account(target_id)
        self._may_manage(actor, target)
        if server_role is not None:
            if actor.server_role is not ServerRole.OWNER or server_role is ServerRole.OWNER:
                raise ForbiddenError(OWNER_ONLY)
            target = await self.store.change_account(target.id, server_role=server_role) or target
        if status is not None:
            target = await self.set_status(target, status)
        return target

    async def delete_account(self, actor: AccountRecord, target_id: int) -> None:
        target = await self.require_account(target_id)
        self._may_manage(actor, target)
        personal = await self.store.personal_workspace(target.id)
        if personal is not None and await self.store.universe_ids(personal.id):
            raise ConflictError(HOLDS_UNIVERSES.format(name=target.display_name))
        for workspace_id in await self.store.workspaces_of_account(target.id):
            if workspace_id != (personal.id if personal else None) and await self.store.admins_of(workspace_id) == [target.id]:
                raise ConflictError(LAST_ADMIN)
        await self.store.remove_account(target.id)
        await self.note(LibraryEventKind.ACCOUNT_DELETED, target.display_name)

    async def transfer_ownership(self, actor: AccountRecord, target_id: int) -> AccountRecord:
        if actor.server_role is not ServerRole.OWNER:
            raise ForbiddenError(OWNER_ONLY)
        target = await self.require_account(target_id)
        if target.id == actor.id or target.server_role is not ServerRole.ADMIN or not target.active:
            raise ValidationFailedError(NEW_OWNER_ADMIN)
        await self.store.change_account(actor.id, server_role=ServerRole.ADMIN)
        return await self.store.change_account(target.id, server_role=ServerRole.OWNER) or target

    async def workspaces(self, account: AccountRecord) -> list[tuple[WorkspaceRecord, WorkspaceRole]]:
        return await self.store.memberships(account.id)

    async def require_workspace(self, workspace_id: int) -> WorkspaceRecord:
        found = await self.store.workspace(workspace_id)
        if found is None:
            raise NotFoundError(NO_WORKSPACE)
        return found

    async def role_in(self, workspace_id: int, account_id: int) -> WorkspaceRole | None:
        return await self.store.role_in(workspace_id, account_id)

    async def create_workspace(self, actor: AccountRecord, name: str) -> WorkspaceRecord:
        workspace = await self.store.add_workspace(clean_workspace_name(name), WorkspaceKind.TEAM, None, actor.id, now_utc())
        await self.note(LibraryEventKind.WORKSPACE_CREATED, workspace.name, workspace_id=workspace.id)
        return workspace

    async def rename_workspace(self, workspace_id: int, name: str) -> WorkspaceRecord:
        workspace = await self.require_workspace(workspace_id)
        if workspace.kind is WorkspaceKind.PERSONAL:
            raise ConflictError(PERSONAL_KEPT)
        renamed = await self.store.rename_workspace(workspace_id, clean_workspace_name(name)) or workspace
        await self.note(LibraryEventKind.WORKSPACE_RENAMED, renamed.name, workspace_id=workspace_id, detail=workspace.name)
        return renamed

    async def deletable(self, workspace_id: int) -> WorkspaceRecord:
        workspace = await self.require_workspace(workspace_id)
        if workspace.kind is WorkspaceKind.PERSONAL:
            raise ConflictError(PERSONAL_KEPT)
        return workspace

    async def remove_workspace(self, workspace_id: int) -> None:
        workspace = await self.require_workspace(workspace_id)
        await self.store.remove_workspace(workspace_id)
        await self.note(LibraryEventKind.WORKSPACE_DELETED, workspace.name)

    async def members(self, workspace_id: int) -> list[MemberRecord]:
        return await self.store.members(workspace_id)

    async def _keep_an_admin(self, workspace_id: int, account_id: int) -> None:
        if await self.store.admins_of(workspace_id) == [account_id]:
            raise ConflictError(LAST_ADMIN)

    async def leave(self, account: AccountRecord, workspace_id: int) -> None:
        workspace = await self.require_workspace(workspace_id)
        if workspace.kind is WorkspaceKind.PERSONAL:
            raise ConflictError(PERSONAL_KEPT)
        if await self.store.role_in(workspace_id, account.id) is None:
            raise NotFoundError(NOT_A_MEMBER)
        await self._keep_an_admin(workspace_id, account.id)
        await self.store.remove_member(workspace_id, account.id)

    async def add_member(
        self,
        actor: AccountRecord,
        workspace_id: int,
        role: WorkspaceRole,
        *,
        account_id: int | None,
        username: str | None,
        email: str | None,
        display_name: str | None,
    ) -> tuple[AccountRecord, str | None]:
        workspace = await self.require_workspace(workspace_id)
        if workspace.kind is WorkspaceKind.PERSONAL:
            raise ConflictError(PERSONAL_ALONE)
        issued: str | None = None
        if account_id is not None:
            account = await self.require_account(account_id)
            if not account.active:
                raise ConflictError(INACTIVE_MEMBER)
            if await self.store.role_in(workspace_id, account.id) is not None:
                raise ConflictError(ALREADY_MEMBER)
        else:
            made = await self.create_account(actor, username=username or "", email=email or "", display_name=display_name or "", server_role=ServerRole.MEMBER)
            account, issued = made.account, made.temporary_password
        await self.store.put_member(workspace_id, account.id, role, actor.id, now_utc())
        await self.note(LibraryEventKind.MEMBER_ADDED, account.display_name, workspace_id=workspace_id, detail=WORKSPACE_ROLE_WORDS[role])
        return account, issued

    async def candidates(self, workspace_id: int, needle: str) -> list[AccountRecord]:
        members = {member.account.id for member in await self.store.members(workspace_id)}
        return [account for account in await self.store.exact_matches(needle) if account.id not in members]

    async def change_member_role(self, workspace_id: int, account_id: int, role: WorkspaceRole) -> None:
        current = await self.store.role_in(workspace_id, account_id)
        if current is None:
            raise NotFoundError(NOT_A_MEMBER)
        if current is WorkspaceRole.ADMIN and role is not WorkspaceRole.ADMIN:
            await self._keep_an_admin(workspace_id, account_id)
        await self.store.put_member(workspace_id, account_id, role, None, now_utc())
        account = await self.require_account(account_id)
        await self.note(LibraryEventKind.MEMBER_ROLE_CHANGED, account.display_name, workspace_id=workspace_id, detail=WORKSPACE_ROLE_WORDS[role])

    async def remove_member(self, workspace_id: int, account_id: int) -> None:
        workspace = await self.require_workspace(workspace_id)
        if workspace.kind is WorkspaceKind.PERSONAL:
            raise ConflictError(PERSONAL_KEPT)
        if await self.store.role_in(workspace_id, account_id) is None:
            raise NotFoundError(NOT_A_MEMBER)
        await self._keep_an_admin(workspace_id, account_id)
        await self.store.remove_member(workspace_id, account_id)
        account = await self.require_account(account_id)
        await self.note(LibraryEventKind.MEMBER_REMOVED, account.display_name, workspace_id=workspace_id)

    async def member_target(self, actor: AccountRecord, workspace_id: int, account_id: int) -> AccountRecord:
        target = await self.require_account(account_id)
        if await self.store.role_in(workspace_id, account_id) is None:
            raise NotFoundError(NOT_A_MEMBER)
        if actor.server_admin:
            self._may_manage(actor, target)
            return target
        if target.id == actor.id:
            raise ForbiddenError(NOT_YOURSELF)
        if target.server_admin:
            raise ForbiddenError(WORKSPACE_ADMIN_SCOPE)
        for other in await self.store.workspaces_of_account(target.id):
            workspace = await self.store.workspace(other)
            if workspace is not None and workspace.kind is WorkspaceKind.PERSONAL:
                continue
            if await self.store.role_in(other, actor.id) is not WorkspaceRole.ADMIN:
                raise ForbiddenError(WORKSPACE_ADMIN_SCOPE)
        return target

    async def universe_access(self, account_id: int, universe: UniverseRecord) -> UniverseAccess:
        return await universe_access(self.store, account_id, universe)

    async def visible(self, account_id: int, workspace_id: int) -> frozenset[str]:
        return await visible_universes(self.store, account_id, workspace_id)

    async def access_table(self, universe: UniverseRecord) -> AccessTable:
        members = await self.store.members(universe.workspace_id) if universe.workspace_id is not None else []
        return AccessTable(universe, members, await self.store.overrides_of_universe(universe.id), await self.store.permission_changes(universe.id))

    async def set_override(self, actor: AccountRecord, universe: UniverseRecord, account_id: int, role: UniverseRole) -> None:
        if universe.workspace_id is None or await self.store.role_in(universe.workspace_id, account_id) is None:
            raise NotFoundError(NOT_A_MEMBER)
        await self.store.put_override(universe.id, account_id, role, actor.id, now_utc())
        await self.note(LibraryEventKind.ACCESS_CHANGED, universe.name, workspace_id=universe.workspace_id, universe_id=universe.id)

    async def clear_override(self, universe: UniverseRecord, account_id: int) -> None:
        await self.store.remove_override(universe.id, account_id)
        await self.note(LibraryEventKind.ACCESS_CHANGED, universe.name, workspace_id=universe.workspace_id, universe_id=universe.id)

    async def set_permissions(self, universe: UniverseRecord, wanted: dict[TunedRole, dict[Permission, bool]]) -> None:
        changes = {
            role: {
                permission: allowed
                for permission, allowed in wanted.get(role, {}).items()
                if permission not in FIXED_PERMISSIONS and allowed != default_allowed(role, permission)
            }
            for role in TunedRole
        }
        await self.store.put_permissions(universe.id, changes)
        await self.note(LibraryEventKind.ACCESS_CHANGED, universe.name, workspace_id=universe.workspace_id, universe_id=universe.id)

    async def reset_permissions(self, universe: UniverseRecord) -> None:
        await self.store.put_permissions(universe.id, {})
        await self.note(LibraryEventKind.ACCESS_CHANGED, universe.name, workspace_id=universe.workspace_id, universe_id=universe.id)

    async def set_canon_approval(self, universe: UniverseRecord, on: bool) -> None:
        await self.store.set_canon_approval(universe.id, on)
        await self.note(LibraryEventKind.CANON_APPROVAL_CHANGED, universe.name, workspace_id=universe.workspace_id, universe_id=universe.id)

    async def move_universe(self, universe: UniverseRecord, workspace_id: int) -> None:
        await self.require_workspace(workspace_id)
        await self.store.move_universe(universe.id, workspace_id)


def workspace_allows(role: WorkspaceRole | None, needed: WorkspaceRole) -> bool:
    return role is not None and WORKSPACE_RANK[role] >= WORKSPACE_RANK[needed]


def refuse(permission: Permission | None, access: UniverseAccess, universe_name: str) -> ForbiddenError:
    text = NO_ACCESS if not access.visible else refusal_text(access.role, permission, universe_name)
    return ForbiddenError(text, permission=permission.value if permission is not None else None, role=access.role.value)


def refuse_workspace(role: WorkspaceRole | None) -> ForbiddenError:
    return ForbiddenError(ROLE_FORBIDDEN, role=role.value if role is not None else None)
