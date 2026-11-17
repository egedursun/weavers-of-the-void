from typing import Annotated

from fastapi import APIRouter, Query

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.cards import CardQuery, CharacterCardPage
from aerona.api.views.character_cards import character_cards

router = APIRouter(tags=["cards"])


@router.get("/cards", response_model=CharacterCardPage)
async def list_cards(services: ServicesDep, query: Annotated[CardQuery, Query()]) -> CharacterCardPage:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return await character_cards(session, rules, query)
