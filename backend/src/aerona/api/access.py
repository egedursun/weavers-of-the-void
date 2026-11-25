from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastapi.routing import APIRoute

from aerona.domain.enums.accounts import Permission, WorkspaceRole

SAFE = frozenset({"GET", "HEAD", "OPTIONS"})


class AccessKind(StrEnum):
    OPEN = "open"
    SIGNED_IN = "signed_in"
    SERVER_ADMIN = "server_admin"
    WORKSPACE = "workspace"
    UNIVERSE = "universe"


@dataclass(frozen=True)
class Access:
    kind: AccessKind
    permission: Permission | None = None
    workspace_role: WorkspaceRole | None = None
    universe_admin: bool = False
    universe_from_path: bool = False
    during_password_change: bool = False


@dataclass(frozen=True)
class RouterAccess:
    read: Access
    write: Access


def open_route() -> Access:
    return Access(AccessKind.OPEN)


def signed_in(*, during_password_change: bool = False) -> Access:
    return Access(AccessKind.SIGNED_IN, during_password_change=during_password_change)


def server_admin() -> Access:
    return Access(AccessKind.SERVER_ADMIN)


def workspace_role(role: WorkspaceRole) -> Access:
    return Access(AccessKind.WORKSPACE, workspace_role=role)


def universe_permission(permission: Permission, *, from_path: bool = False) -> Access:
    return Access(AccessKind.UNIVERSE, permission=permission, universe_from_path=from_path)


def universe_admin(*, from_path: bool = False) -> Access:
    return Access(AccessKind.UNIVERSE, universe_admin=True, universe_from_path=from_path)


def world(write: Permission = Permission.EDIT_WORLD, read: Permission = Permission.VIEW) -> RouterAccess:
    return RouterAccess(universe_permission(read), universe_permission(write))


WORLD_ROUTERS = frozenset(
    {
        "actions",
        "affairs",
        "afflictions",
        "agrarian",
        "arcana",
        "belonging",
        "biology",
        "body",
        "bonds",
        "bulk",
        "calendar",
        "cards",
        "catalogue",
        "celestial",
        "changes",
        "chronicle",
        "city_scene",
        "climes",
        "collective",
        "communication",
        "cosmography",
        "cosmos",
        "council",
        "council_order",
        "couplings",
        "crafts",
        "creator",
        "creator_bonds",
        "customs",
        "cycles",
        "depth_society",
        "discovery",
        "divine",
        "divine_powers",
        "dominion",
        "economy",
        "economy_depth",
        "entities",
        "environment",
        "eras",
        "estates",
        "event_record",
        "evolution",
        "expeditions",
        "factions",
        "faith",
        "fate",
        "finance",
        "folkways",
        "foreign_gods",
        "fortune",
        "fossils",
        "foundations",
        "gatherings",
        "genesis",
        "goals",
        "graph",
        "happenings",
        "industry",
        "intrigue",
        "jobs",
        "justice",
        "kinds",
        "languages",
        "law_depth",
        "law_grammar",
        "lifecycle_ends",
        "lineage",
        "living",
        "lore",
        "made_kinds",
        "maintenance",
        "map",
        "means",
        "mechanics",
        "metrics",
        "military",
        "military_depth",
        "mind",
        "minds",
        "mortals",
        "museums",
        "nature",
        "notes",
        "operations",
        "outer_agency",
        "pantheon_of",
        "physics",
        "places",
        "polity_economy",
        "powers",
        "prayers",
        "previews",
        "profiles",
        "prompt_context",
        "pursuits",
        "realms",
        "record_rows",
        "regime",
        "regions",
        "relations",
        "renown",
        "sacred",
        "search",
        "sensed",
        "society_depth",
        "sons",
        "state",
        "statecraft",
        "structures",
        "tales",
        "technology",
        "thin_b",
        "thin_sections",
        "titles",
        "tongues",
        "transform",
        "typed_models",
        "urban_depth",
        "usage",
        "wars",
        "wilds",
        "world_ends",
        "world_views",
    }
)
DIVINE_WILL = world(Permission.DIVINE_WILL_READ, Permission.DIVINE_WILL_READ)
ROUTER_ACCESS: dict[str, RouterAccess] = {
    **{name: world() for name in WORLD_ROUTERS},
    "health": RouterAccess(open_route(), open_route()),
    "auth": RouterAccess(signed_in(), signed_in()),
    "accounts": RouterAccess(server_admin(), server_admin()),
    "workspaces": RouterAccess(workspace_role(WorkspaceRole.VIEWER), workspace_role(WorkspaceRole.ADMIN)),
    "rules": world(Permission.CHANGE_RULES),
    "settings": world(Permission.CHANGE_RULES),
    "epochs": world(Permission.START_AGES),
    "prehistory": world(Permission.START_AGES),
    "engine": world(),
    "events": world(Permission.VIEW),
    "notifications": world(Permission.VIEW),
    "ledger": world(Permission.UNDO_OWN),
    "images": world(Permission.GENERATE_IMAGES),
    "books": world(Permission.DOWNLOAD_BOOKS),
    "backups": world(Permission.EXPORT),
    "exchange": world(Permission.EXPORT),
    "divine_will": DIVINE_WILL,
    "divine_will_attachments": DIVINE_WILL,
    "divine_will_library": DIVINE_WILL,
    "presence": DIVINE_WILL,
    "team": world(Permission.VIEW),
}
SHELF_VIEW = universe_permission(Permission.VIEW, from_path=True)
SHELF_EDIT = universe_permission(Permission.MANAGE_SHELF, from_path=True)
WORKSPACE_VIEWER = workspace_role(WorkspaceRole.VIEWER)
WORKSPACE_EDITOR = workspace_role(WorkspaceRole.EDITOR)
WORKSPACE_ADMIN = workspace_role(WorkspaceRole.ADMIN)
UNIVERSE_ADMIN = universe_admin()
ROUTE_ACCESS: dict[tuple[str, str], Access] = {
    ("GET", "/api/{path:path}"): open_route(),
    ("POST", "/api/{path:path}"): open_route(),
    ("PUT", "/api/{path:path}"): open_route(),
    ("PATCH", "/api/{path:path}"): open_route(),
    ("DELETE", "/api/{path:path}"): open_route(),
    ("GET", "/health/report"): universe_permission(Permission.VIEW),
    ("GET", "/auth/state"): open_route(),
    ("POST", "/team/proposals/{proposal_id}/approve"): UNIVERSE_ADMIN,
    ("POST", "/team/proposals/{proposal_id}/reject"): UNIVERSE_ADMIN,
    ("POST", "/auth/setup"): open_route(),
    ("POST", "/auth/sign-in"): open_route(),
    ("POST", "/auth/sign-out"): signed_in(during_password_change=True),
    ("POST", "/auth/password"): signed_in(during_password_change=True),
    ("GET", "/workspaces"): signed_in(),
    ("POST", "/workspaces"): signed_in(),
    ("POST", "/workspaces/{workspace_id}/leave"): WORKSPACE_VIEWER,
    ("GET", "/workspaces/{workspace_id}/candidates"): WORKSPACE_ADMIN,
    ("PUT", "/workspaces/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}"): universe_admin(from_path=True),
    ("DELETE", "/workspaces/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}"): universe_admin(from_path=True),
    ("PUT", "/workspaces/{workspace_id}/universes/{universe_id}/access/permissions"): universe_admin(from_path=True),
    ("DELETE", "/workspaces/{workspace_id}/universes/{universe_id}/access/permissions"): universe_admin(from_path=True),
    ("PUT", "/workspaces/{workspace_id}/universes/{universe_id}/access/canon-approval"): universe_admin(from_path=True),
    ("GET", "/library/universes"): WORKSPACE_VIEWER,
    ("POST", "/library/universes"): WORKSPACE_EDITOR,
    ("GET", "/library/universes/{universe_id}"): SHELF_VIEW,
    ("PATCH", "/library/universes/{universe_id}"): SHELF_EDIT,
    ("POST", "/library/universes/{universe_id}/open"): SHELF_VIEW,
    ("POST", "/library/universes/{universe_id}/close"): SHELF_VIEW,
    ("POST", "/library/universes/{universe_id}/duplicate"): universe_permission(Permission.EXPORT, from_path=True),
    ("POST", "/library/universes/{universe_id}/archive"): SHELF_EDIT,
    ("POST", "/library/universes/{universe_id}/restore"): SHELF_EDIT,
    ("POST", "/library/universes/{universe_id}/move"): universe_admin(from_path=True),
    ("DELETE", "/library/universes/{universe_id}"): universe_admin(from_path=True),
    ("GET", "/library/trash"): WORKSPACE_VIEWER,
    ("DELETE", "/library/trash"): WORKSPACE_ADMIN,
    ("POST", "/library/trash/{entry_id}/restore"): WORKSPACE_VIEWER,
    ("DELETE", "/library/trash/{entry_id}"): WORKSPACE_ADMIN,
    ("POST", "/library/universes/{universe_id}/export"): universe_permission(Permission.EXPORT, from_path=True),
    ("GET", "/library/exports/{job_id}"): WORKSPACE_VIEWER,
    ("GET", "/library/exports/{job_id}/file"): WORKSPACE_VIEWER,
    ("DELETE", "/library/exports/{job_id}"): WORKSPACE_VIEWER,
    ("POST", "/library/imports"): WORKSPACE_EDITOR,
    ("GET", "/library/imports/{job_id}"): WORKSPACE_EDITOR,
    ("POST", "/library/imports/{job_id}/confirm"): WORKSPACE_EDITOR,
    ("DELETE", "/library/imports/{job_id}"): WORKSPACE_EDITOR,
    ("GET", "/library/jobs"): WORKSPACE_VIEWER,
    ("PUT", "/library/universes/{universe_id}/cover"): SHELF_EDIT,
    ("PUT", "/library/universes/{universe_id}/cover/from-media"): SHELF_EDIT,
    ("GET", "/library/universes/{universe_id}/cover/paint"): SHELF_VIEW,
    ("POST", "/library/universes/{universe_id}/cover/paint"): universe_permission(Permission.GENERATE_IMAGES, from_path=True),
    ("DELETE", "/library/universes/{universe_id}/cover"): SHELF_EDIT,
    ("GET", "/library/universes/{universe_id}/cover"): SHELF_VIEW,
    ("GET", "/library/events"): WORKSPACE_VIEWER,
    ("GET", "/library/events/stream"): WORKSPACE_VIEWER,
    ("GET", "/media/{file_name}"): universe_permission(Permission.VIEW),
    ("HEAD", "/media/{file_name}"): universe_permission(Permission.VIEW),
    ("GET", "/images"): universe_permission(Permission.VIEW),
    ("POST", "/images"): universe_permission(Permission.EDIT_WORLD),
    ("PUT", "/images/{image_id}/cover"): universe_permission(Permission.EDIT_WORLD),
    ("PUT", "/images/{image_id}/caption"): universe_permission(Permission.EDIT_WORLD),
    ("DELETE", "/images/{image_id}"): universe_permission(Permission.EDIT_WORLD),
    ("GET", "/book"): universe_permission(Permission.VIEW),
    ("GET", "/book/maps/{world_id}.jpg"): universe_permission(Permission.VIEW),
    ("GET", "/book/fonts/{file_name}"): universe_permission(Permission.VIEW),
    ("GET", "/book/brand/logo.png"): universe_permission(Permission.VIEW),
    ("GET", "/backups"): universe_permission(Permission.VIEW),
    ("GET", "/backups/secondary"): universe_permission(Permission.VIEW),
    ("PUT", "/backups/secondary"): UNIVERSE_ADMIN,
    ("POST", "/backups/restore"): UNIVERSE_ADMIN,
    ("POST", "/world/reset"): UNIVERSE_ADMIN,
    ("POST", "/world/import"): UNIVERSE_ADMIN,
    ("POST", "/divine-will/confirmations/{confirmation_id}"): universe_permission(Permission.EDIT_WORLD),
    ("GET", "/codex.md"): universe_permission(Permission.DOWNLOAD_BOOKS),
    ("GET", "/codex.zip"): universe_permission(Permission.DOWNLOAD_BOOKS),
    ("GET", "/book.pdf"): universe_permission(Permission.DOWNLOAD_BOOKS),
    ("GET", "/book/pdf"): universe_permission(Permission.DOWNLOAD_BOOKS),
    ("GET", "/backups/{file_name}/database"): universe_permission(Permission.EXPORT),
    ("GET", "/backups/{file_name}/package"): universe_permission(Permission.EXPORT),
    ("GET", "/world/export"): universe_permission(Permission.EXPORT),
    ("POST", "/jobs/{job_id}/cancel"): universe_permission(Permission.START_AGES),
    ("POST", "/sons/{son_id}/act"): universe_permission(Permission.START_AGES),
    ("POST", "/entities/{entity_id}/image-prompt"): universe_permission(Permission.GENERATE_IMAGES),
    ("POST", "/languages/{language_id}/sample-names"): universe_permission(Permission.VIEW),
    ("POST", "/languages/{language_id}/translate"): universe_permission(Permission.VIEW),
    ("POST", "/maintenance/backups/{file_name}/verify"): universe_permission(Permission.EXPORT),
    ("PUT", "/prompt-context/tired-motifs/overrides"): universe_permission(Permission.CHANGE_RULES),
    ("POST", "/prompt-context/tired-motifs/overrides/clear"): universe_permission(Permission.CHANGE_RULES),
    ("PUT", "/divine-will/plans/{plan_id}/steps"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/pause"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/abandon"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/steps/{ordinal}/skip"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/approve"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/execute"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/resume"): universe_permission(Permission.EDIT_WORLD),
    ("POST", "/divine-will/plans/{plan_id}/steps/{ordinal}/undo"): universe_permission(Permission.UNDO_OWN),
    ("POST", "/divine-will/forecasts/{forecast_id}/cancel"): universe_permission(Permission.ALTERNATIVE_HISTORIES),
}
LEVER_ENDPOINTS: dict[Callable[..., Any], str] = {}


def module_of(route: APIRoute) -> str:
    return str(route.endpoint.__module__).rsplit(".", 1)[-1]


def declared(route: APIRoute, method: str, lever_permission: Callable[[str], Permission]) -> Access | None:
    lever = LEVER_ENDPOINTS.get(route.endpoint)
    if lever is not None:
        return universe_permission(lever_permission(lever))
    explicit = ROUTE_ACCESS.get((method.upper(), route.path))
    if explicit is not None:
        return explicit
    defaults = ROUTER_ACCESS.get(module_of(route))
    if defaults is None:
        return None
    return defaults.read if method.upper() in SAFE else defaults.write


def undeclared(routes: Iterable[APIRoute], lever_permission: Callable[[str], Permission]) -> list[str]:
    missing = [(method, route) for route in routes for method in sorted(route.methods or ()) if declared(route, method, lever_permission) is None]
    return sorted(f"{method} {route.path} ({module_of(route)})" for method, route in missing)


def stale_declarations(routes: Iterable[APIRoute]) -> list[str]:
    present = {(method, route.path) for route in routes for method in route.methods or ()}
    modules = {module_of(route) for route in routes}
    stale = [f"{method} {path}" for method, path in ROUTE_ACCESS if (method, path) not in present]
    stale.extend(f"router {name}" for name in ROUTER_ACCESS if name not in modules)
    return sorted(stale)
