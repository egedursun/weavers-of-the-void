from typing import Annotated

from fastapi import APIRouter, Path, Query

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.wars import RelationEntry, RelationEventView, RelationList, RelationPair
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.society import community_relation_label
from aerona.core.errors import NotFoundError
from aerona.db.tables.society import CommunityRelationRow
from aerona.engine.services.community_relations import pair_key, relation, relation_history, relation_list

router = APIRouter(tags=["relations"])

RELATION_LIMIT_MAX = 1000
NO_RELATION = "Both ends of a relation must exist."

ALIASES = (
    Alias("PUT", "/entities/{entity_id}/relations/{other_id}", "relation:set", path_fields={"entity_id": "first_id", "other_id": "second_id"}),
    Alias("POST", "/entities/{entity_id}/relations/{other_id}/feud", "feud:start", path_fields={"entity_id": "first_id", "other_id": "second_id"}),
    Alias("DELETE", "/entities/{entity_id}/relations/{other_id}/feud", "feud:end", path_fields={"entity_id": "first_id", "other_id": "second_id"}),
)

mount_all(router, ALIASES, tag="relations")


@router.get("/entities/{entity_id}/relations", response_model=RelationList)
async def community_relations(
    services: ServicesDep, entity_id: int = Path(ge=1), limit: Annotated[int | None, Query(ge=1, le=RELATION_LIMIT_MAX)] = None
) -> RelationList:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        views = await relation_list(session, rules, entity_id, limit)
        refs = await node_refs(session, [view.entity_id for view in views])
        entries = [
            RelationEntry(
                other=refs[view.entity_id],
                value=view.value,
                label=view.label,
                blood_feud_since_epoch=view.blood_feud_since_epoch,
                history=[RelationEventView(epoch=event.epoch, event=event.event, delta=event.delta) for event in view.history],
            )
            for view in views
            if view.entity_id in refs
        ]
        return RelationList(entity_id=entity_id, relations=entries)


@router.get("/entities/{entity_id}/relations/{other_id}", response_model=RelationPair)
async def relation_between(services: ServicesDep, entity_id: int = Path(ge=1), other_id: int = Path(ge=1)) -> RelationPair:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        first, second = await node_ref(session, entity_id), await node_ref(session, other_id)
        if first is None or second is None:
            raise NotFoundError(NO_RELATION)
        value = await relation(session, rules, entity_id, other_id)
        stored = await session.get(CommunityRelationRow, pair_key(entity_id, other_id))
        history = await relation_history(session, entity_id, other_id, rules.diplomacy.relation_history_len)
        return RelationPair(
            first=first,
            second=second,
            value=value,
            label=community_relation_label(rules, value),
            blood_feud_since_epoch=stored.blood_feud_since_epoch if stored is not None else None,
            history=[RelationEventView(epoch=event.epoch, event=event.event, delta=event.delta) for event in history],
        )
