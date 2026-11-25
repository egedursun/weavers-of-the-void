from enum import StrEnum


class ServerRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class AvatarTone(StrEnum):
    GOLD = "gold"
    VERDIGRIS = "verdigris"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    MUTED = "muted"


class WorkspaceKind(StrEnum):
    PERSONAL = "personal"
    TEAM = "team"


class WorkspaceRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class UniverseRole(StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    NONE = "none"


class TunedRole(StrEnum):
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    VIEW = "view"
    EDIT_WORLD = "edit_world"
    START_AGES = "start_ages"
    CHANGE_RULES = "change_rules"
    LOCK_CANON = "lock_canon"
    ALTERNATIVE_HISTORIES = "alternative_histories"
    UNDO_OWN = "undo_own"
    UNDO_ANY = "undo_any"
    GENERATE_IMAGES = "generate_images"
    EXPORT = "export"
    DOWNLOAD_BOOKS = "download_books"
    DIVINE_WILL_READ = "divine_will_read"
    PRESENCE_ON_RECORD = "presence_on_record"
    MANAGE_SHELF = "manage_shelf"
