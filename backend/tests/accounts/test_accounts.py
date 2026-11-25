from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.main import create_app
from aerona.settings import Settings
from tests.accounts.team import NEW_PASSWORD, Team, team_of
from tests.library_support import OWNER_EMAIL, OWNER_PASSWORD, OWNER_USERNAME, accounts_of, sole_universe


@pytest.fixture
async def team(settings: Settings) -> AsyncIterator[Team]:
    async with team_of(settings) as made:
        yield made


async def test_setup_creates_the_owner_and_adopts_every_universe(settings: Settings) -> None:
    app = create_app(settings)
    async with LifespanManager(app, startup_timeout=120, shutdown_timeout=120):
        http = AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost")
        state = (await http.get("/api/auth/state")).json()
        assert state["setup_required"] is True
        blocked = await http.get("/api/library/universes")
        assert (blocked.status_code, blocked.json()["code"]) == (409, "setup_required")
        made = await http.post(
            "/api/auth/setup",
            json={"username": "Maker", "email": "Maker@Example.test", "display_name": "The Maker", "password": "a quiet long morning walk"},
        )
        assert made.status_code == 200, made.text
        assert made.json()["account"]["server_role"] == "owner"
        assert made.json()["account"]["email"] == "maker@example.test"
        workspaces = (await http.get("/api/workspaces")).json()
        assert [workspace["kind"] for workspace in workspaces] == ["personal"]
        universe = await sole_universe(app)
        record = await accounts_of(app).catalogue.require(universe)
        assert record.workspace_id == workspaces[0]["id"]
        assert record.legacy_author_name == "The Maker"
        again = await http.post("/api/auth/setup", json={"username": "other", "email": "o@example.test", "display_name": "O", "password": "x" * 12})
        assert again.status_code == 409
        await http.aclose()


async def test_sign_in_by_username_or_email_and_wrong_passwords_lock(team: Team) -> None:
    by_name = await team.sign_in(OWNER_USERNAME, OWNER_PASSWORD)
    by_mail = await team.sign_in(OWNER_EMAIL.upper(), OWNER_PASSWORD)
    assert (await by_name.get("/api/auth/state")).json()["account"]["username"] == OWNER_USERNAME
    assert (await by_mail.get("/api/auth/state")).json()["account"]["username"] == OWNER_USERNAME
    stranger = team.client()
    wrong = await stranger.post("/api/auth/sign-in", json={"login": OWNER_USERNAME, "password": "not the password"})
    assert (wrong.status_code, wrong.json()["code"]) == (401, "signed_out")
    for _ in range(team.accounts.settings.accounts_lockout_attempts - 2):
        await stranger.post("/api/auth/sign-in", json={"login": OWNER_USERNAME, "password": "not the password"})
    locked = await stranger.post("/api/auth/sign-in", json={"login": OWNER_USERNAME, "password": "not the password"})
    assert (locked.status_code, locked.json()["code"]) == (429, "locked")
    still = await stranger.post("/api/auth/sign-in", json={"login": OWNER_USERNAME, "password": OWNER_PASSWORD})
    assert still.status_code == 429
    owner = await team.accounts.store.by_login(OWNER_USERNAME)
    assert owner is not None
    await team.accounts.store.change_account(owner.id, locked_until=datetime.now(UTC) - timedelta(seconds=1))
    team.accounts.throttle.clear("127.0.0.1")
    assert (await stranger.post("/api/auth/sign-in", json={"login": OWNER_USERNAME, "password": OWNER_PASSWORD})).status_code == 200


async def test_a_temporary_password_must_be_changed_first(team: Team) -> None:
    created = await team.owner.post("/api/accounts", json={"username": "ina", "email": "ina@example.test", "display_name": "Ina"})
    assert created.status_code == 201, created.text
    temporary = created.json()["temporary_password"]
    ina = await team.sign_in("ina", temporary)
    assert (await ina.get("/api/auth/state")).json()["must_change_password"] is True
    refused = await ina.get("/api/workspaces")
    assert (refused.status_code, refused.json()["code"]) == (403, "password_change_required")
    weak = await ina.post("/api/auth/password", json={"current": temporary, "new": "short"})
    assert weak.status_code == 400
    named = await ina.post("/api/auth/password", json={"current": temporary, "new": "ina-is-my-password"})
    assert named.status_code == 400
    changed = await ina.post("/api/auth/password", json={"current": temporary, "new": NEW_PASSWORD})
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False
    assert (await ina.get("/api/workspaces")).status_code == 200


async def test_reset_deactivate_reactivate_and_delete(team: Team) -> None:
    created = (await team.owner.post("/api/accounts", json={"username": "olu", "email": "olu@example.test", "display_name": "Olu"})).json()
    account_id = created["account"]["id"]
    olu = await team.sign_in("olu", created["temporary_password"])
    await olu.post("/api/auth/password", json={"current": created["temporary_password"], "new": NEW_PASSWORD})
    reset = await team.owner.post(f"/api/accounts/{account_id}/reset-password")
    assert reset.status_code == 200
    assert (await olu.get("/api/workspaces")).status_code == 401
    again = await team.sign_in("olu", reset.json()["temporary_password"])
    await again.post("/api/auth/password", json={"current": reset.json()["temporary_password"], "new": NEW_PASSWORD})
    off = await team.owner.patch(f"/api/accounts/{account_id}", json={"status": "deactivated"})
    assert off.json()["status"] == "deactivated"
    assert (await again.get("/api/workspaces")).status_code == 401
    refused = await team.client().post("/api/auth/sign-in", json={"login": "olu", "password": NEW_PASSWORD})
    assert refused.status_code == 401
    assert "deactivated" in refused.json()["error"]
    on = await team.owner.patch(f"/api/accounts/{account_id}", json={"status": "active"})
    assert on.json()["status"] == "active"
    assert (await team.sign_in("olu", NEW_PASSWORD)) is not None
    gone = await team.owner.delete(f"/api/accounts/{account_id}")
    assert gone.status_code == 200
    assert all(account["id"] != account_id for account in (await team.owner.get("/api/accounts")).json())
    names = [event["account_name"] for event in (await team.owner.get("/api/library/events")).json()["items"]]
    assert "The Owner" in names


async def test_sessions_end_on_idle_and_on_password_change(team: Team) -> None:
    other = await team.sign_in(OWNER_USERNAME, OWNER_PASSWORD)
    sessions = (await team.owner.get("/api/auth/sessions")).json()
    assert len(sessions) == 2
    assert sum(session["current"] for session in sessions) == 1
    owner = await team.accounts.store.by_login(OWNER_USERNAME)
    assert owner is not None
    for session in await team.accounts.store.sessions_of(owner.id):
        if session.id != next(found["id"] for found in sessions if found["current"]):
            await team.accounts.store.touch_session(session.id, datetime.now(UTC) - timedelta(days=30))
    assert (await other.get("/api/workspaces")).status_code == 401
    third = await team.sign_in(OWNER_USERNAME, OWNER_PASSWORD)
    changed = await team.owner.post("/api/auth/password", json={"current": OWNER_PASSWORD, "new": NEW_PASSWORD})
    assert changed.status_code == 200
    assert (await third.get("/api/workspaces")).status_code == 401
    assert (await team.owner.get("/api/workspaces")).status_code == 200
    out = await team.owner.post("/api/auth/sign-out")
    assert out.status_code == 200
    assert (await team.owner.get("/api/workspaces")).status_code == 401


async def test_profile_edits_and_unique_names(team: Team) -> None:
    edited = await team.owner.patch("/api/auth/profile", json={"display_name": "Prime Mover", "avatar_tone": "verdigris"})
    assert (edited.json()["display_name"], edited.json()["avatar_tone"]) == ("Prime Mover", "verdigris")
    workspaces = (await team.owner.get("/api/workspaces")).json()
    assert workspaces[0]["name"] == "Prime Mover's workspace"
    taken = await team.owner.post("/api/accounts", json={"username": "owner", "email": "x@example.test", "display_name": "X"})
    assert taken.status_code == 409
    taken_mail = await team.owner.post("/api/accounts", json={"username": "xxx", "email": OWNER_EMAIL.upper(), "display_name": "X"})
    assert taken_mail.status_code == 409
