from fastapi import APIRouter

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.records import CosmosRecord, CreatorRecord, EpochRecord, ThreadRecord
from aerona.api.schemas.state import (
    BulkSummary,
    Covenant,
    HalfEpochState,
    MoodSummary,
    SonRelationItem,
    StateResponse,
    WorldBriefItem,
)
from aerona.api.views.common import son_public
from aerona.engine.gods.mood import mood_label, mood_of
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.epoch.resume import half_epoch
from aerona.services.container import Services
from aerona.services.notifications import unread_count
from aerona.services.state import snapshot

router = APIRouter(tags=["state"])


def epoch_running(services: Services) -> bool:
    return services.jobs.busy_group(WORLD_GROUP) is not None


@router.get("/state", response_model=StateResponse)
async def read_state(services: ServicesDep) -> StateResponse:
    application = services.application
    async with reader(services) as session:
        rules = await world_rules(services, session)
        state = await snapshot(session, rules)
        unread = await unread_count(session) if state.cosmos is not None else 0
        half = await half_epoch(session) if state.cosmos is not None else None
    bulk = (await application.bulk_deepen.status()).state
    creator = state.creator
    mood = None
    if creator is not None:
        current = mood_of(creator)
        mood = MoodSummary(
            contentment=current.contentment, anger=current.anger, interest=current.interest, loneliness=current.loneliness, label=mood_label(rules, current)
        )
    return StateResponse(
        world=CosmosRecord.model_validate(state.cosmos) if state.cosmos else None,
        creator=CreatorRecord.model_validate(creator) if creator else None,
        creator_cover=state.creator_cover,
        world_cover=state.world_cover,
        sons=[son_public(view) for view in state.sons],
        counts=state.counts,
        prayers_pending=state.prayers_pending,
        relations=[SonRelationItem.model_validate(row) for row in state.relations],
        worlds=[WorldBriefItem.model_validate(world) for world in state.worlds],
        foreign_god_count=state.foreign_god_count,
        pending_son_ids=state.pending_son_ids,
        covenants=[Covenant(son_a_id=first, son_b_id=second, description=text) for first, second, text in state.covenants],
        threads=[ThreadRecord.model_validate(row) for row in state.open_threads],
        last_epoch=EpochRecord.model_validate(state.last_epoch) if state.last_epoch else None,
        image_count=state.image_count,
        promptless_count=state.promptless_count,
        pulse=state.pulse,
        read_only=application.discovery.active,
        discovery=application.discovery.guest(),
        version=application.feed.version,
        notifications_unread=unread,
        running_jobs=services.jobs.running_count,
        epoch_running=epoch_running(services),
        half_epoch=HalfEpochState.model_validate(half) if half else None,
        mood=mood,
        image_gen=application.images.status(),
        batch_deepen=BulkSummary.model_validate(bulk),
        llm_enabled=services.agents.llm_enabled,
    )
