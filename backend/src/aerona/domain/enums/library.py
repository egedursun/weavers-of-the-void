from enum import StrEnum


class UniverseStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class UniverseOrigin(StrEnum):
    CREATED = "created"
    IMPORTED = "imported"
    DUPLICATED = "duplicated"
    ADOPTED = "adopted"


class UniverseSort(StrEnum):
    OPENED = "opened"
    CREATED = "created"
    NAME = "name"
    EPOCH = "epoch"
    SIZE = "size"


class LibraryEventKind(StrEnum):
    CREATED = "created"
    ADOPTED = "adopted"
    OPENED = "opened"
    RENAMED = "renamed"
    EDITED = "edited"
    EXPORTED = "exported"
    IMPORTED = "imported"
    DUPLICATED = "duplicated"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"
    RECOVERED = "recovered"
    PURGED = "purged"
    MOVED = "moved"
    ACCOUNT_CREATED = "account_created"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    ACCOUNT_REACTIVATED = "account_reactivated"
    ACCOUNT_DELETED = "account_deleted"
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_RENAMED = "workspace_renamed"
    WORKSPACE_DELETED = "workspace_deleted"
    MEMBER_ADDED = "member_added"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    MEMBER_REMOVED = "member_removed"
    ACCESS_CHANGED = "access_changed"
    CANON_APPROVAL_CHANGED = "canon_approval_changed"
