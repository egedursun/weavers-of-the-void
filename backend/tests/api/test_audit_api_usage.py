import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_api_usage.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("audit_api_usage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_matches_typed_calls_and_url_templates(tmp_path: Path) -> None:
    audit = load_script()
    source = "api.GET('/api/jobs/{job_id}', {})\nconst url = `/api/sons/${son.id}/resurrection?x=1`\n"
    callers = audit.callers_in(source, tmp_path / "caller.ts")
    routes = [
        audit.Route("GET", "/api/jobs/{job_id}"),
        audit.Route("POST", "/api/jobs/{job_id}/cancel"),
        audit.Route("GET", "/api/sons/{son_id}/resurrection"),
    ]
    missing = audit.uncalled(routes, callers)
    assert [route.path for route in missing] == ["/api/jobs/{job_id}/cancel"]


def test_audit_lists_every_route_of_the_app() -> None:
    audit = load_script()
    routes = audit.api_routes()
    assert audit.Route("GET", "/api/health") in routes
    assert len(routes) > 300
    assert audit.main([]) == 0
