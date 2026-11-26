from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, MetaData, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aerona.constants.accounts import (
    ADDRESS_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    USER_AGENT_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    WORKSPACE_NAME_MAX_LENGTH,
)
from aerona.constants.library import UNIVERSE_ID_LENGTH, UNIVERSE_NAME_MAX_LENGTH
from aerona.constants.providers import BASE_URL_MAX_LENGTH, CHECK_NOTE_MAX_LENGTH, CONNECTION_LABEL_MAX_LENGTH, MODEL_NAME_MAX_LENGTH, SECRET_HINT_LENGTH
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import NAMING_CONVENTION
from aerona.db.columns import at_least, enum_type
from aerona.db.types import UtcDateTime
from aerona.domain.enums.accounts import AccountStatus, AvatarTone, Permission, ServerRole, TunedRole, UniverseRole, WorkspaceKind, WorkspaceRole
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseStatus
from aerona.domain.enums.providers import ModelRole, ProviderKind


class LibraryBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UniverseRow(LibraryBase):
    __tablename__ = "universes"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("population", 0),
        at_least("sons", 0),
        at_least("size_bytes", 0),
        Index("ix_universes_status", "status"),
        Index("ix_universes_opened_at", "opened_at"),
    )

    id: Mapped[str] = mapped_column(String(UNIVERSE_ID_LENGTH), primary_key=True)
    name: Mapped[str] = mapped_column(String(UNIVERSE_NAME_MAX_LENGTH))
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    cover_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[UniverseStatus] = mapped_column(enum_type(UniverseStatus, "status"), default=UniverseStatus.ACTIVE)
    pinned: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    opened_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    epoch: Mapped[int] = mapped_column(default=0)
    year: Mapped[int] = mapped_column(default=0)
    population: Mapped[int] = mapped_column(BigInteger, default=0)
    sons: Mapped[int] = mapped_column(default=0)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    schema_revision: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")
    app_version: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")
    origin: Mapped[UniverseOrigin] = mapped_column(enum_type(UniverseOrigin, "origin"), default=UniverseOrigin.CREATED)
    origin_note: Mapped[str] = mapped_column(Text, default="", server_default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    media_prefix: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), index=True)
    legacy_author_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    legacy_author_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH), default="", server_default="")
    canon_approval: Mapped[bool] = mapped_column(default=False, server_default="0")


class LibraryEventRow(LibraryBase):
    __tablename__ = "library_events"
    __table_args__ = (Index("ix_library_events_universe_id", "universe_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    kind: Mapped[LibraryEventKind] = mapped_column(enum_type(LibraryEventKind, "kind"))
    universe_id: Mapped[str] = mapped_column(String(UNIVERSE_ID_LENGTH))
    universe_name: Mapped[str] = mapped_column(String(UNIVERSE_NAME_MAX_LENGTH))
    detail: Mapped[str] = mapped_column(Text, default="", server_default="")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    account_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH), default="", server_default="")
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"))


class AccountRow(LibraryBase):
    __tablename__ = "accounts"
    __table_args__ = (
        at_least("failed_attempts", 0),
        UniqueConstraint("username", name="uq_accounts_username"),
        UniqueConstraint("email", name="uq_accounts_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(USERNAME_MAX_LENGTH))
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH))
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    password_hash: Mapped[str] = mapped_column(Text)
    must_change_password: Mapped[bool] = mapped_column(default=False)
    status: Mapped[AccountStatus] = mapped_column(enum_type(AccountStatus, "status"), default=AccountStatus.ACTIVE)
    server_role: Mapped[ServerRole] = mapped_column(enum_type(ServerRole, "server_role"), default=ServerRole.MEMBER)
    avatar_tone: Mapped[AvatarTone] = mapped_column(enum_type(AvatarTone, "avatar_tone"), default=AvatarTone.GOLD)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    last_sign_in_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    password_changed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    failed_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UtcDateTime())


class SessionRow(LibraryBase):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_sessions_token_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    last_used_at: Mapped[datetime] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    user_agent: Mapped[str] = mapped_column(String(USER_AGENT_MAX_LENGTH), default="", server_default="")
    address: Mapped[str] = mapped_column(String(ADDRESS_MAX_LENGTH), default="", server_default="")


class WorkspaceRow(LibraryBase):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(WORKSPACE_NAME_MAX_LENGTH))
    kind: Mapped[WorkspaceKind] = mapped_column(enum_type(WorkspaceKind, "kind"))
    owner_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class WorkspaceMemberRow(LibraryBase):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(enum_type(WorkspaceRole, "role"))
    added_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    added_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class UniverseOverrideRow(LibraryBase):
    __tablename__ = "universe_overrides"

    universe_id: Mapped[str] = mapped_column(String(UNIVERSE_ID_LENGTH), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[UniverseRole] = mapped_column(enum_type(UniverseRole, "role"))
    set_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    set_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class UniversePermissionRow(LibraryBase):
    __tablename__ = "universe_permissions"

    universe_id: Mapped[str] = mapped_column(ForeignKey("universes.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[TunedRole] = mapped_column(enum_type(TunedRole, "role"), primary_key=True)
    permission: Mapped[Permission] = mapped_column(enum_type(Permission, "permission"), primary_key=True)
    allowed: Mapped[bool]


class ProviderConnectionRow(LibraryBase):
    __tablename__ = "provider_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[ProviderKind] = mapped_column(enum_type(ProviderKind, "kind"))
    label: Mapped[str] = mapped_column(String(CONNECTION_LABEL_MAX_LENGTH))
    secret: Mapped[str] = mapped_column(Text, default="", server_default="")
    secret_hint: Mapped[str] = mapped_column(String(SECRET_HINT_LENGTH), default="", server_default="")
    base_url: Mapped[str] = mapped_column(String(BASE_URL_MAX_LENGTH), default="", server_default="")
    logged_in_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class ProviderChainEntryRow(LibraryBase):
    __tablename__ = "provider_chain_entries"
    __table_args__ = (at_least("position", 0),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    role: Mapped[ModelRole] = mapped_column(enum_type(ModelRole, "role"))
    position: Mapped[int]
    connection_id: Mapped[int] = mapped_column(ForeignKey("provider_connections.id", ondelete="CASCADE"), index=True)
    model: Mapped[str] = mapped_column(String(MODEL_NAME_MAX_LENGTH), default="", server_default="")
    tools_work: Mapped[bool | None]
    sees_images: Mapped[bool | None]
    checked_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    check_note: Mapped[str] = mapped_column(String(CHECK_NOTE_MAX_LENGTH), default="", server_default="")
