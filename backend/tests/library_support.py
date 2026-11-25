from fastapi import FastAPI
from starlette.types import ASGIApp

from aerona.constants.library import UNIVERSE_HEADER
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
