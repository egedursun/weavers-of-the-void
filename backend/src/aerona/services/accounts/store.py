from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.library.tables import (
    AccountRow,
    SessionRow,
    UniverseOverrideRow,
    UniversePermissionRow,
    UniverseRow,
    WorkspaceMemberRow,
    WorkspaceRow,
)
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
from aerona.services.library.catalogue import Catalogue


@dataclass(frozen=True)
class AccountRecord:
    id: int
    username: str
    email: str
    display_name: str
    password_hash: str
    must_change_password: bool
    status: AccountStatus
    server_role: ServerRole
    avatar_tone: AvatarTone
    created_by: int | None
    created_at: datetime
    last_sign_in_at: datetime | None
    password_changed_at: datetime | None
    failed_attempts: int
    locked_until: datetime | None

    @classmethod
    def of(cls, row: AccountRow) -> "AccountRecord":
        return cls(
            id=row.id,
            username=row.username,
            email=row.email,
            display_name=row.display_name,
            password_hash=row.password_hash,
            must_change_password=row.must_change_password,
            status=row.status,
            server_role=row.server_role,
            avatar_tone=row.avatar_tone,
            created_by=row.created_by,
            created_at=row.created_at,
            last_sign_in_at=row.last_sign_in_at,
            password_changed_at=row.password_changed_at,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
        )

    @property
    def active(self) -> bool:
        return self.status is AccountStatus.ACTIVE

    @property
    def server_admin(self) -> bool:
        return self.server_role in (ServerRole.OWNER, ServerRole.ADMIN)


@dataclass(frozen=True)
class SessionRecord:
    id: int
    account_id: int
    token_hash: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    user_agent: str
    address: str

    @classmethod
    def of(cls, row: SessionRow) -> "SessionRecord":
        return cls(row.id, row.account_id, row.token_hash, row.created_at, row.last_used_at, row.expires_at, row.user_agent, row.address)


@dataclass(frozen=True)
class WorkspaceRecord:
    id: int
    name: str
    kind: WorkspaceKind
    owner_account_id: int | None
    created_by: int | None
    created_at: datetime

    @classmethod
    def of(cls, row: WorkspaceRow) -> "WorkspaceRecord":
        return cls(row.id, row.name, row.kind, row.owner_account_id, row.created_by, row.created_at)


@dataclass(frozen=True)
class MemberRecord:
    workspace_id: int
    account: AccountRecord
    role: WorkspaceRole
    added_by: int | None
    added_at: datetime


@dataclass(frozen=True)
class OverrideRecord:
    universe_id: str
    account_id: int
    role: UniverseRole
    set_by: int | None
    set_at: datetime


@dataclass(frozen=True)
class NewAccount:
    username: str
    email: str
    display_name: str
    password_hash: str
    must_change_password: bool
    server_role: ServerRole
    avatar_tone: AvatarTone
    created_by: int | None


class AccountStore:
    def __init__(self, catalogue: Catalogue) -> None:
        self.catalogue = catalogue

    @asynccontextmanager
    async def read(self) -> AsyncIterator[AsyncSession]:
        async with self.catalogue.read_session() as session:
            yield session

    @asynccontextmanager
    async def write(self) -> AsyncIterator[AsyncSession]:
        async with self.catalogue.write_session() as session:
            yield session

    async def count(self) -> int:
        async with self.read() as session:
            return int(await session.scalar(select(func.count()).select_from(AccountRow)) or 0)

    async def account(self, account_id: int) -> AccountRecord | None:
        async with self.read() as session:
            row = await session.get(AccountRow, account_id)
            return AccountRecord.of(row) if row is not None else None

    async def by_login(self, login: str) -> AccountRecord | None:
        folded = login.strip().casefold()
        async with self.read() as session:
            row = await session.scalar(select(AccountRow).where(or_(func.lower(AccountRow.username) == folded, func.lower(AccountRow.email) == folded)))
            return AccountRecord.of(row) if row is not None else None

    async def exact_matches(self, needle: str) -> list[AccountRecord]:
        folded = needle.strip().casefold()
        if not folded:
            return []
        async with self.read() as session:
            rows = await session.scalars(
                select(AccountRow)
                .where(or_(func.lower(AccountRow.username) == folded, func.lower(AccountRow.email) == folded), AccountRow.status == AccountStatus.ACTIVE)
                .order_by(AccountRow.id)
            )
            return [AccountRecord.of(row) for row in rows]

    async def taken(self, *, username: str | None = None, email: str | None = None, keep: int | None = None) -> bool:
        conditions = []
        if username is not None:
            conditions.append(func.lower(AccountRow.username) == username.casefold())
        if email is not None:
            conditions.append(func.lower(AccountRow.email) == email.casefold())
        if not conditions:
            return False
        statement = select(AccountRow.id).where(or_(*conditions))
        if keep is not None:
            statement = statement.where(AccountRow.id != keep)
        async with self.read() as session:
            return await session.scalar(statement.limit(1)) is not None

    async def accounts(self, ids: Iterable[int] | None = None) -> list[AccountRecord]:
        statement = select(AccountRow).order_by(func.lower(AccountRow.display_name), AccountRow.id)
        if ids is not None:
            statement = statement.where(AccountRow.id.in_(sorted(set(ids))))
        async with self.read() as session:
            return [AccountRecord.of(row) for row in await session.scalars(statement)]

    async def add_account(self, new: NewAccount, now: datetime) -> AccountRecord:
        async with self.write() as session:
            row = AccountRow(
                username=new.username,
                email=new.email,
                display_name=new.display_name,
                password_hash=new.password_hash,
                must_change_password=new.must_change_password,
                status=AccountStatus.ACTIVE,
                server_role=new.server_role,
                avatar_tone=new.avatar_tone,
                created_by=new.created_by,
                created_at=now,
                password_changed_at=None if new.must_change_password else now,
                failed_attempts=0,
            )
            session.add(row)
            await session.flush()
            return AccountRecord.of(row)

    async def change_account(self, account_id: int, **values: object) -> AccountRecord | None:
        async with self.write() as session:
            row = await session.get(AccountRow, account_id)
            if row is None:
                return None
            for key, value in values.items():
                setattr(row, key, value)
            await session.flush()
            return AccountRecord.of(row)

    async def remove_account(self, account_id: int) -> None:
        async with self.write() as session:
            await session.execute(delete(WorkspaceRow).where(WorkspaceRow.owner_account_id == account_id))
            await session.execute(delete(AccountRow).where(AccountRow.id == account_id))

    async def add_session(self, account_id: int, token_hash: str, now: datetime, expires_at: datetime, *, user_agent: str, address: str) -> SessionRecord:
        async with self.write() as session:
            row = SessionRow(
                account_id=account_id, token_hash=token_hash, created_at=now, last_used_at=now, expires_at=expires_at, user_agent=user_agent, address=address
            )
            session.add(row)
            await session.flush()
            return SessionRecord.of(row)

    async def session_by_hash(self, token_hash: str) -> SessionRecord | None:
        async with self.read() as session:
            row = await session.scalar(select(SessionRow).where(SessionRow.token_hash == token_hash))
            return SessionRecord.of(row) if row is not None else None

    async def sessions_of(self, account_id: int) -> list[SessionRecord]:
        async with self.read() as session:
            rows = await session.scalars(select(SessionRow).where(SessionRow.account_id == account_id).order_by(SessionRow.last_used_at.desc(), SessionRow.id))
            return [SessionRecord.of(row) for row in rows]

    async def touch_session(self, session_id: int, now: datetime) -> None:
        async with self.write() as session:
            await session.execute(update(SessionRow).where(SessionRow.id == session_id).values(last_used_at=now))

    async def end_sessions(self, account_id: int, *, only: int | None = None, keep: int | None = None) -> int:
        statement = delete(SessionRow).where(SessionRow.account_id == account_id)
        if only is not None:
            statement = statement.where(SessionRow.id == only)
        if keep is not None:
            statement = statement.where(SessionRow.id != keep)
        async with self.write() as session:
            result = await session.execute(statement)
            return int(getattr(result, "rowcount", 0) or 0)

    async def end_session(self, session_id: int) -> None:
        async with self.write() as session:
            await session.execute(delete(SessionRow).where(SessionRow.id == session_id))

    async def add_workspace(self, name: str, kind: WorkspaceKind, owner_account_id: int | None, created_by: int | None, now: datetime) -> WorkspaceRecord:
        async with self.write() as session:
            row = WorkspaceRow(name=name, kind=kind, owner_account_id=owner_account_id, created_by=created_by, created_at=now)
            session.add(row)
            await session.flush()
            if created_by is not None:
                session.add(WorkspaceMemberRow(workspace_id=row.id, account_id=created_by, role=WorkspaceRole.ADMIN, added_by=created_by, added_at=now))
            return WorkspaceRecord.of(row)

    async def workspace(self, workspace_id: int) -> WorkspaceRecord | None:
        async with self.read() as session:
            row = await session.get(WorkspaceRow, workspace_id)
            return WorkspaceRecord.of(row) if row is not None else None

    async def personal_workspace(self, account_id: int) -> WorkspaceRecord | None:
        async with self.read() as session:
            row = await session.scalar(
                select(WorkspaceRow).where(WorkspaceRow.owner_account_id == account_id, WorkspaceRow.kind == WorkspaceKind.PERSONAL).order_by(WorkspaceRow.id)
            )
            return WorkspaceRecord.of(row) if row is not None else None

    async def rename_workspace(self, workspace_id: int, name: str) -> WorkspaceRecord | None:
        async with self.write() as session:
            row = await session.get(WorkspaceRow, workspace_id)
            if row is None:
                return None
            row.name = name
            await session.flush()
            return WorkspaceRecord.of(row)

    async def remove_workspace(self, workspace_id: int) -> None:
        async with self.write() as session:
            await session.execute(delete(WorkspaceRow).where(WorkspaceRow.id == workspace_id))

    async def memberships(self, account_id: int) -> list[tuple[WorkspaceRecord, WorkspaceRole]]:
        async with self.read() as session:
            rows = await session.execute(
                select(WorkspaceRow, WorkspaceMemberRow.role)
                .join(WorkspaceMemberRow, WorkspaceMemberRow.workspace_id == WorkspaceRow.id)
                .where(WorkspaceMemberRow.account_id == account_id)
                .order_by(WorkspaceRow.kind.desc(), func.lower(WorkspaceRow.name), WorkspaceRow.id)
            )
            return [(WorkspaceRecord.of(workspace), role) for workspace, role in rows.all()]

    async def role_in(self, workspace_id: int, account_id: int) -> WorkspaceRole | None:
        async with self.read() as session:
            return await session.scalar(
                select(WorkspaceMemberRow.role).where(WorkspaceMemberRow.workspace_id == workspace_id, WorkspaceMemberRow.account_id == account_id)
            )

    async def members(self, workspace_id: int) -> list[MemberRecord]:
        async with self.read() as session:
            rows = await session.execute(
                select(WorkspaceMemberRow, AccountRow)
                .join(AccountRow, AccountRow.id == WorkspaceMemberRow.account_id)
                .where(WorkspaceMemberRow.workspace_id == workspace_id)
                .order_by(func.lower(AccountRow.display_name), AccountRow.id)
            )
            return [
                MemberRecord(member.workspace_id, AccountRecord.of(account), member.role, member.added_by, member.added_at) for member, account in rows.all()
            ]

    async def admins_of(self, workspace_id: int) -> list[int]:
        async with self.read() as session:
            rows = await session.scalars(
                select(WorkspaceMemberRow.account_id)
                .where(WorkspaceMemberRow.workspace_id == workspace_id, WorkspaceMemberRow.role == WorkspaceRole.ADMIN)
                .order_by(WorkspaceMemberRow.account_id)
            )
            return list(rows)

    async def workspaces_of_account(self, account_id: int) -> list[int]:
        async with self.read() as session:
            rows = await session.scalars(
                select(WorkspaceMemberRow.workspace_id).where(WorkspaceMemberRow.account_id == account_id).order_by(WorkspaceMemberRow.workspace_id)
            )
            return list(rows)

    async def put_member(self, workspace_id: int, account_id: int, role: WorkspaceRole, added_by: int | None, now: datetime) -> None:
        async with self.write() as session:
            row = await session.get(WorkspaceMemberRow, (workspace_id, account_id))
            if row is None:
                session.add(WorkspaceMemberRow(workspace_id=workspace_id, account_id=account_id, role=role, added_by=added_by, added_at=now))
            else:
                row.role = role

    async def remove_member(self, workspace_id: int, account_id: int) -> None:
        async with self.write() as session:
            universes = select(UniverseRow.id).where(UniverseRow.workspace_id == workspace_id)
            await session.execute(
                delete(UniverseOverrideRow).where(UniverseOverrideRow.account_id == account_id, UniverseOverrideRow.universe_id.in_(universes))
            )
            await session.execute(
                delete(WorkspaceMemberRow).where(WorkspaceMemberRow.workspace_id == workspace_id, WorkspaceMemberRow.account_id == account_id)
            )

    async def universe_ids(self, workspace_id: int) -> list[str]:
        async with self.read() as session:
            rows = await session.scalars(select(UniverseRow.id).where(UniverseRow.workspace_id == workspace_id).order_by(UniverseRow.id))
            return list(rows)

    async def overrides_of_account(self, account_id: int, universe_ids: Iterable[str]) -> dict[str, UniverseRole]:
        async with self.read() as session:
            rows = await session.execute(
                select(UniverseOverrideRow.universe_id, UniverseOverrideRow.role).where(
                    UniverseOverrideRow.account_id == account_id, UniverseOverrideRow.universe_id.in_(sorted(set(universe_ids)))
                )
            )
            return {universe_id: role for universe_id, role in rows.all()}

    async def hidden_from(self, account_id: int) -> frozenset[str]:
        async with self.read() as session:
            rows = await session.scalars(
                select(UniverseOverrideRow.universe_id)
                .where(UniverseOverrideRow.account_id == account_id, UniverseOverrideRow.role == UniverseRole.NONE)
                .order_by(UniverseOverrideRow.universe_id)
            )
            return frozenset(rows)

    async def overrides_of_universe(self, universe_id: str) -> list[OverrideRecord]:
        async with self.read() as session:
            rows = await session.scalars(
                select(UniverseOverrideRow).where(UniverseOverrideRow.universe_id == universe_id).order_by(UniverseOverrideRow.account_id)
            )
            return [OverrideRecord(row.universe_id, row.account_id, row.role, row.set_by, row.set_at) for row in rows]

    async def put_override(self, universe_id: str, account_id: int, role: UniverseRole, set_by: int | None, now: datetime) -> None:
        async with self.write() as session:
            row = await session.get(UniverseOverrideRow, (universe_id, account_id))
            if row is None:
                session.add(UniverseOverrideRow(universe_id=universe_id, account_id=account_id, role=role, set_by=set_by, set_at=now))
            else:
                row.role, row.set_by, row.set_at = role, set_by, now

    async def remove_override(self, universe_id: str, account_id: int) -> None:
        async with self.write() as session:
            await session.execute(
                delete(UniverseOverrideRow).where(UniverseOverrideRow.universe_id == universe_id, UniverseOverrideRow.account_id == account_id)
            )

    async def permission_changes(self, universe_id: str) -> dict[TunedRole, dict[Permission, bool]]:
        async with self.read() as session:
            rows = await session.scalars(
                select(UniversePermissionRow)
                .where(UniversePermissionRow.universe_id == universe_id)
                .order_by(UniversePermissionRow.role, UniversePermissionRow.permission)
            )
            found: dict[TunedRole, dict[Permission, bool]] = {role: {} for role in TunedRole}
            for row in rows:
                found[row.role][row.permission] = row.allowed
            return found

    async def put_permissions(self, universe_id: str, changes: dict[TunedRole, dict[Permission, bool]]) -> None:
        async with self.write() as session:
            await session.execute(delete(UniversePermissionRow).where(UniversePermissionRow.universe_id == universe_id))
            for role in sorted(changes):
                for permission in sorted(changes[role]):
                    session.add(UniversePermissionRow(universe_id=universe_id, role=role, permission=permission, allowed=changes[role][permission]))

    async def set_canon_approval(self, universe_id: str, on: bool) -> None:
        async with self.write() as session:
            await session.execute(update(UniverseRow).where(UniverseRow.id == universe_id).values(canon_approval=on))

    async def adopt_universes(self, workspace_id: int, author_id: int, author_name: str) -> list[str]:
        async with self.write() as session:
            ids = list(await session.scalars(select(UniverseRow.id).where(UniverseRow.workspace_id.is_(None)).order_by(UniverseRow.id)))
            if ids:
                await session.execute(
                    update(UniverseRow)
                    .where(UniverseRow.id.in_(ids))
                    .values(workspace_id=workspace_id, legacy_author_account_id=author_id, legacy_author_name=author_name)
                )
            return ids

    async def move_universe(self, universe_id: str, workspace_id: int) -> None:
        async with self.write() as session:
            await session.execute(delete(UniverseOverrideRow).where(UniverseOverrideRow.universe_id == universe_id))
            await session.execute(update(UniverseRow).where(UniverseRow.id == universe_id).values(workspace_id=workspace_id))
