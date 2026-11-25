import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from aerona.api.access import stale_declarations, undeclared
from aerona.api.app import api_routes
from aerona.services.accounts.permissions import lever_permission


def main() -> int:
    routes = api_routes()
    missing = undeclared(routes, lever_permission)
    stale = stale_declarations(routes)
    for line in missing:
        print(f"no access declaration: {line}")
    for line in stale:
        print(f"declaration for no route: {line}")
    print(f"route access: {len(missing)} undeclared, {len(stale)} stale")
    return 1 if missing or stale else 0


if __name__ == "__main__":
    sys.exit(main())
