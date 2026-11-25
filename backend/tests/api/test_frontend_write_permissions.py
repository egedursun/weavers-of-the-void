import re
from collections.abc import Callable
from pathlib import Path

from aerona.api.access import Access, AccessKind, declared
from aerona.api.app import api_routes
from aerona.domain.enums.accounts import Permission, WorkspaceRole
from aerona.services.accounts.permissions import lever_permission

TABLE = Path(__file__).resolve().parents[3] / "frontend" / "src" / "features" / "team" / "writePermissions.ts"
WRITES = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ENTRY = re.compile(r"'(/api/[^']+)':\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
RULE = re.compile(r"(POST|PUT|PATCH|DELETE):\s*(?:'([a-z_]+)'|\{\s*lever:\s*'([^']+)'\s*\})")
HOLE = re.compile(r"\{[^}]+\}")
SKIPPED_PREFIXES = ("/api/actions/", "/api/api/")
ACCOUNT_KINDS = frozenset({AccessKind.OPEN, AccessKind.SIGNED_IN, AccessKind.SERVER_ADMIN})
HANDLER_RULES = {
    "author": frozenset({Permission.VIEW, Permission.DIVINE_WILL_READ, Permission.EDIT_WORLD, Permission.ALTERNATIVE_HISTORIES}),
    "undo": frozenset({Permission.UNDO_OWN, Permission.UNDO_ANY}),
    "divine_will_mode": frozenset({Permission.DIVINE_WILL_READ}),
    "presence_record": frozenset({Permission.DIVINE_WILL_READ}),
}


def shape(path: str) -> str:
    return HOLE.sub("{}", path)


def frontend_rules() -> dict[str, str]:
    text = TABLE.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for entry in ENTRY.finditer(text):
        for rule in RULE.finditer(entry.group(2)):
            found[f"{rule.group(1)} {shape(entry.group(1))}"] = rule.group(2) or f"lever:{rule.group(3)}"
    return found


def backend_rules() -> dict[str, Access | None]:
    found: dict[str, Access | None] = {}
    for route in api_routes():
        for method in sorted(set(route.methods or ()) & WRITES):
            path = f"/api{route.path}"
            if not path.startswith(SKIPPED_PREFIXES):
                found[f"{method} {shape(path)}"] = declared(route, method, lever_permission)
    return found


def universe_rule(rule: str, access: Access) -> bool:
    if access.kind is not AccessKind.UNIVERSE or access.universe_admin or access.permission is None:
        return False
    if rule in HANDLER_RULES:
        return access.permission in HANDLER_RULES[rule]
    return rule == access.permission.value


NAMED_RULES: dict[str, Callable[[Access], bool]] = {
    "account": lambda access: access.kind in ACCOUNT_KINDS,
    "workspace_admin": lambda access: access.kind is AccessKind.WORKSPACE and access.workspace_role is WorkspaceRole.ADMIN,
    "none": lambda access: access.kind is AccessKind.WORKSPACE,
    "admin": lambda access: access.kind is AccessKind.UNIVERSE and access.universe_admin,
    "universe_admin": lambda access: access.kind is AccessKind.UNIVERSE and access.universe_admin,
}


def agrees(rule: str, access: Access) -> bool:
    if rule.startswith("lever:"):
        return True
    named = NAMED_RULES.get(rule)
    return named(access) if named is not None else universe_rule(rule, access)


def described(access: Access) -> str:
    return f"{access.kind.value} {access.permission} {access.workspace_role} admin={access.universe_admin}"


def test_every_write_route_has_a_rule_on_the_frontend() -> None:
    frontend = frontend_rules()
    assert sorted(key for key in backend_rules() if key not in frontend) == []


def test_the_frontend_never_names_a_write_route_the_server_does_not_have() -> None:
    backend = backend_rules()
    assert sorted(key for key in frontend_rules() if key not in backend) == []


def test_every_frontend_rule_matches_the_server_declaration() -> None:
    backend = backend_rules()
    disagreements = []
    for key, rule in sorted(frontend_rules().items()):
        access = backend.get(key)
        if access is not None and not agrees(rule, access):
            disagreements.append(f"{key}: frontend {rule}, server {described(access)}")
    assert disagreements == []
