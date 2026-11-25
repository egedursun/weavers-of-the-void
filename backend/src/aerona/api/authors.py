from typing import Annotated

from fastapi import Depends, Request

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.team import AuthorView
from aerona.services.library.hub import UniverseHub


async def legacy_author(request: Request, services: ServicesDep) -> AuthorView | None:
    hub: UniverseHub | None = getattr(request.app.state, "hub", None)
    universe_id = services.settings.universe_id
    if hub is None or not universe_id:
        return None
    record = await hub.catalogue.get(universe_id)
    if record is None or (record.legacy_author_account_id is None and not record.legacy_author_name):
        return None
    return AuthorView(account_id=record.legacy_author_account_id, name=record.legacy_author_name)


LegacyAuthorDep = Annotated[AuthorView | None, Depends(legacy_author)]


def authored(account_id: int | None, name: str | None, *, by_hand: bool, legacy: AuthorView | None) -> AuthorView | None:
    if account_id is not None or name:
        return AuthorView(account_id=account_id, name=name or "")
    return legacy if by_hand else None
