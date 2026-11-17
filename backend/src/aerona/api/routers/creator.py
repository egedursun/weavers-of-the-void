from fastapi import APIRouter
from sqlalchemy import select

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.gods import CreatorDetail, CreatorMood, CreatorReputation, FolkView, MoodInput, PassionInfo, SonReputation
from aerona.api.schemas.records import CreatorRecord, EntitySummary
from aerona.api.views.common import images_of
from aerona.api.views.scoped_lines import scoped_lines
from aerona.catalog.creator import CREATOR_PASSIONS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import FolkBeliefRow
from aerona.domain.enums.chronicle import ChronicleScope
from aerona.services.gods.creator_mood import read_cult, read_mood
from aerona.services.gods.reputation import read_cosmos_reputation
from aerona.services.images.records import cover_of

router = APIRouter(tags=["creator"])


ALIASES = (
    Alias("PATCH", "/creator", "creator:edit"),
    Alias("PUT", "/creator/note", "creator:note"),
    Alias("PUT", "/creator/mood", "creator:mood"),
    Alias("PUT", "/creator/passions", "creator:passions"),
    Alias("POST", "/creator/portrait", "creator:content", fixed={"kind": "creator_portrait"}, summary="Redraw the Creator's portrait"),
    Alias("POST", "/creator/epic", "creator:content", fixed={"kind": "creator_epic"}, summary="Compose the Creator's epic"),
    Alias("POST", "/creator/deepen", "creator:content", fixed={"kind": "creator_deepen"}, summary="Deepen the Creator"),
    Alias("POST", "/sons/{son_id}/reputation-nudge", "creator:reputation", path_fields={"son_id": "son_id"}),
    Alias("POST", "/revelations", "revelation"),
)


@router.get("/creator", response_model=CreatorDetail)
async def read_creator(services: ServicesDep) -> CreatorDetail:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        creator = await CosmosRepository(session).require_creator()
        mood = await read_mood(session, rules)
        cult = await read_cult(session, rules)
        beliefs = await session.execute(
            select(FolkBeliefRow, EntityRow.name)
            .join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id)
            .where(FolkBeliefRow.god_node_id == creator.id)
            .order_by(FolkBeliefRow.epoch.desc())
        )
        traces, traces_total = await scoped_lines(session, ChronicleScope.CREATOR, None, offset=0, limit=rules.server.god_traces)
        return CreatorDetail(
            creator=CreatorRecord.model_validate(creator),
            cover=await cover_of(session, creator.id),
            mood=CreatorMood(
                contentment=mood.state.contentment,
                anger=mood.state.anger,
                interest=mood.state.interest,
                loneliness=mood.state.loneliness,
                label=mood.label,
                breakdown=[MoodInput.model_validate(row) for row in mood.breakdown],
            ),
            faith=cult.effect.faith,
            cult_essence=cult.effect.essence,
            cult=[EntitySummary.model_validate(member) for member in cult.members],
            folk_views=[
                FolkView(
                    people_id=row.people_entity_id,
                    people_name=name,
                    local_name=row.local_name,
                    account=row.account,
                    misconception=row.misconception,
                    epoch=row.epoch,
                )
                for row, name in beliefs
            ],
            traces=traces,
            traces_total=traces_total,
            images=await images_of(session, creator.id),
        )


@router.get("/creator/reputation", response_model=CreatorReputation)
async def read_reputation(services: ServicesDep) -> CreatorReputation:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        found = await read_cosmos_reputation(session, rules)
    return CreatorReputation(
        love=found.love,
        fear=found.fear,
        forgotten=found.forgotten,
        label=found.label,
        sons=[
            SonReputation(
                son_id=son.id,
                name=son.name,
                love=value.love,
                fear=value.fear,
                forgotten=value.forgotten,
                unanswered=value.unanswered,
                last_contact=value.last_contact,
                label=value.label,
            )
            for son, value in found.sons
        ],
        passions=list(found.passions),
        automatic=found.automatic,
        all_passions=[PassionInfo(passion=spec.passion, name=spec.label, hint=spec.hint) for spec in CREATOR_PASSIONS.values()],
    )


mount_all(router, ALIASES, tag="creator")
