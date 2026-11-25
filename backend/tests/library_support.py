from fastapi import FastAPI
from httpx import AsyncClient
from starlette.types import ASGIApp

from aerona.constants.accounts import SESSION_COOKIE, WORKSPACE_HEADER
from aerona.constants.library import UNIVERSE_HEADER
from aerona.services.accounts.service import AccountService, SignedIn
from aerona.services.container import Services
from aerona.services.library.hub import UniverseHub


def hub_of(app: ASGIApp) -> UniverseHub:
    assert isinstance(app, FastAPI)
    hub: UniverseHub = app.state.hub
    return hub


async def sole_universe(app: ASGIApp) -> str:
    records = await hub_of(app).catalogue.every()
    assert records, "the test library holds no universe"
    return records[0].id


def universe_headers(universe_id: str) -> dict[str, str]:
    return {UNIVERSE_HEADER: universe_id}


async def opened_services(app: ASGIApp, universe_id: str) -> Services:
    return (await hub_of(app).open(universe_id)).services


OWNER_USERNAME = "owner"
OWNER_EMAIL = "owner@example.test"
OWNER_NAME = "The Owner"
OWNER_PASSWORD = "a long and quiet morning"


def accounts_of(app: ASGIApp) -> AccountService:
    assert isinstance(app, FastAPI)
    accounts: AccountService = app.state.accounts
    return accounts


async def signed_owner(app: ASGIApp) -> SignedIn:
    accounts = accounts_of(app)
    if not await accounts.ready():
        return await accounts.setup(
            username=OWNER_USERNAME, email=OWNER_EMAIL, display_name=OWNER_NAME, password=OWNER_PASSWORD, user_agent="tests", address="tests"
        )
    return await accounts.sign_in(OWNER_USERNAME, OWNER_PASSWORD, user_agent="tests", address="tests")


async def owner_workspace(app: ASGIApp, account_id: int) -> int:
    workspace = await accounts_of(app).store.personal_workspace(account_id)
    assert workspace is not None
    return workspace.id


async def sign_in_owner(app: ASGIApp, http: AsyncClient) -> SignedIn:
    signed = await signed_owner(app)
    http.cookies.set(SESSION_COOKIE, signed.token)
    http.headers[WORKSPACE_HEADER] = str(await owner_workspace(app, signed.account.id))
    return signed
