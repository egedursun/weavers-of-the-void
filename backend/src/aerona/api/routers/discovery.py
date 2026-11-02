from fastapi import APIRouter

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import ApiModel
from aerona.services.discovery import GuestWorld

router = APIRouter(tags=["discovery"])


class DiscoveryStatus(ApiModel):
    active: bool
    guest: GuestWorld | None


class DiscoveryEnded(ApiModel):
    ok: bool = True
    guest: GuestWorld | None


@router.get("/discovery", response_model=DiscoveryStatus)
async def discovery_status(services: ServicesDep) -> DiscoveryStatus:
    discovery = services.application.discovery
    return DiscoveryStatus(active=discovery.active, guest=discovery.guest())


@router.post("/discovery/end", response_model=DiscoveryEnded)
async def end_discovery(services: ServicesDep) -> DiscoveryEnded:
    return DiscoveryEnded(guest=await services.application.exchange.end_discovery())
