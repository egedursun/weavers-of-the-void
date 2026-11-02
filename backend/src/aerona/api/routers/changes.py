from fastapi import APIRouter, Query

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.records import EntityRecord
from aerona.api.schemas.state import ChangesResponse
from aerona.api.views.common import son_public
from aerona.services.state import change_digest

router = APIRouter(tags=["state"])


@router.get("/changes", response_model=ChangesResponse)
async def read_changes(services: ServicesDep, since: str | None = Query(default=None, max_length=64)) -> ChangesResponse:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        changes = services.application.feed.changes_since(since, rules.ui.delta_max_changes)
        digest = await change_digest(session, rules, changes)
    return ChangesResponse(
        full=digest.full,
        version=digest.version,
        entities=[EntityRecord.model_validate(entity) for entity in digest.entities],
        removed_entity_ids=digest.removed_entity_ids,
        sons=[son_public(view) for view in digest.sons],
        removed_son_ids=digest.removed_son_ids,
        new_chronicle_lines=digest.new_chronicle_lines,
        bonds_changed=digest.bonds_changed,
        cosmos_changed=digest.cosmos_changed,
        worlds_changed=digest.worlds_changed,
        relations_changed=digest.relations_changed,
        foreign_god_ids=digest.foreign_god_ids,
    )
