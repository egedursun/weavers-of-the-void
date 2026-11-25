from collections.abc import Mapping

from aerona.domain.enums.accounts import Permission, TunedRole, UniverseRole, WorkspaceRole
from aerona.services.accounts.lever_permissions import LEVER_PERMISSIONS

FIXED_PERMISSIONS = frozenset({Permission.VIEW})
VIEWER_DEFAULTS = frozenset({Permission.VIEW, Permission.DOWNLOAD_BOOKS, Permission.DIVINE_WILL_READ})
DEFAULTS: Mapping[TunedRole, frozenset[Permission]] = {
    TunedRole.EDITOR: frozenset(Permission),
    TunedRole.VIEWER: VIEWER_DEFAULTS,
}
WORKSPACE_TO_UNIVERSE: Mapping[WorkspaceRole, UniverseRole] = {
    WorkspaceRole.ADMIN: UniverseRole.ADMIN,
    WorkspaceRole.EDITOR: UniverseRole.EDITOR,
    WorkspaceRole.VIEWER: UniverseRole.VIEWER,
}
TUNED_OF: Mapping[UniverseRole, TunedRole] = {UniverseRole.EDITOR: TunedRole.EDITOR, UniverseRole.VIEWER: TunedRole.VIEWER}
WORKSPACE_RANK: Mapping[WorkspaceRole, int] = {WorkspaceRole.VIEWER: 0, WorkspaceRole.EDITOR: 1, WorkspaceRole.ADMIN: 2}


def default_allowed(role: TunedRole, permission: Permission) -> bool:
    return permission in DEFAULTS[role]


def permissions_of(role: UniverseRole, changes: Mapping[Permission, bool]) -> frozenset[Permission]:
    if role is UniverseRole.ADMIN:
        return frozenset(Permission)
    tuned = TUNED_OF.get(role)
    if tuned is None:
        return frozenset()
    granted = {permission for permission in Permission if changes.get(permission, default_allowed(tuned, permission))}
    return frozenset(granted | FIXED_PERMISSIONS)


def lever_permission(action_id: str) -> Permission:
    return LEVER_PERMISSIONS.get(action_id, Permission.EDIT_WORLD)


ROLE_PLURALS: Mapping[UniverseRole, str] = {
    UniverseRole.ADMIN: "Administrators",
    UniverseRole.EDITOR: "Editors",
    UniverseRole.VIEWER: "Viewers",
    UniverseRole.NONE: "People without access",
}
PERMISSION_VERBS: Mapping[Permission, str] = {
    Permission.VIEW: "read it",
    Permission.EDIT_WORLD: "change the world",
    Permission.START_AGES: "start ages",
    Permission.CHANGE_RULES: "change its rules",
    Permission.LOCK_CANON: "lock or release canon",
    Permission.ALTERNATIVE_HISTORIES: "explore alternative histories",
    Permission.UNDO_OWN: "undo their own acts",
    Permission.UNDO_ANY: "undo other people's acts",
    Permission.GENERATE_IMAGES: "generate images",
    Permission.EXPORT: "export or duplicate it",
    Permission.DOWNLOAD_BOOKS: "download its book or Codex",
    Permission.DIVINE_WILL_READ: "ask the Divine Will",
    Permission.PRESENCE_ON_RECORD: "speak with Presence on the record",
    Permission.MANAGE_SHELF: "change its place on the shelf",
}
ADMIN_VERB = "manage who has access"


def refusal_text(role: UniverseRole, permission: Permission | None, universe_name: str) -> str:
    verb = PERMISSION_VERBS[permission] if permission is not None else ADMIN_VERB
    return f"{ROLE_PLURALS[role]} of {universe_name} cannot {verb}."


PERMISSION_LABELS: Mapping[Permission, str] = {
    Permission.VIEW: "Read the universe",
    Permission.EDIT_WORLD: "Change the world",
    Permission.START_AGES: "Start ages",
    Permission.CHANGE_RULES: "Change rules",
    Permission.LOCK_CANON: "Lock canon",
    Permission.ALTERNATIVE_HISTORIES: "Alternative histories",
    Permission.UNDO_OWN: "Undo own acts",
    Permission.UNDO_ANY: "Undo anyone's acts",
    Permission.GENERATE_IMAGES: "Generate images",
    Permission.EXPORT: "Export and duplicate",
    Permission.DOWNLOAD_BOOKS: "Download the book and Codex",
    Permission.DIVINE_WILL_READ: "Ask the Divine Will",
    Permission.PRESENCE_ON_RECORD: "Presence on the record",
    Permission.MANAGE_SHELF: "Manage the shelf",
}
PERMISSION_MEANINGS: Mapping[Permission, str] = {
    Permission.VIEW: "Every screen, the chronicle, the Atlas and the book on screen.",
    Permission.EDIT_WORLD: "Every god lever that creates, edits, holds or deletes a thing, and every Divine Will act.",
    Permission.START_AGES: "Run epochs, half epochs, prehistory and every job of the world group.",
    Permission.CHANGE_RULES: "Rule and setting changes.",
    Permission.LOCK_CANON: "Hold and release things, strike and restore canon, edit canon facts.",
    Permission.ALTERNATIVE_HISTORIES: "Foresight and other forks of the universe.",
    Permission.UNDO_OWN: "Undo one's own acts.",
    Permission.UNDO_ANY: "Undo anyone's act; every undo names who undid it and can itself be undone.",
    Permission.GENERATE_IMAGES: "Image generation and restyling.",
    Permission.EXPORT: "Export the universe, duplicate it, download backups.",
    Permission.DOWNLOAD_BOOKS: "Book PDF and Codex downloads.",
    Permission.DIVINE_WILL_READ: "Divine Will modes that only read, and off-the-record Presence.",
    Permission.PRESENCE_ON_RECORD: "Presence on the record.",
    Permission.MANAGE_SHELF: "Rename, notes, tags, cover, pin and archive in the library.",
}


WORKSPACE_ROLE_WORDS: Mapping[WorkspaceRole, str] = {
    WorkspaceRole.ADMIN: "Administrator",
    WorkspaceRole.EDITOR: "Editor",
    WorkspaceRole.VIEWER: "Viewer",
}
