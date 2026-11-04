from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.foundations import AnchorageView, DedicationView, GoldenAgeView, IncitedWarView
from aerona.api.views.common import node_ref, node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.gods.dedication import dedicated_structures, dedication_of, incited_wars
from aerona.engine.phases.world_age import golden_age_status
from aerona.engine.primitives.holds import ANCHOR_KEY, DEDICATION_KEY, INCITEMENT_KEY, is_held

router = APIRouter(tags=["foundations"])


async def current_epoch(session: AsyncSession) -> int:
    cosmos = await CosmosRepository(session).get()
    return cosmos.epoch if cosmos is not None else 0


@router.get("/worlds/{world_id}/golden-age", response_model=GoldenAgeView)
async def world_golden_age(services: ServicesDep, world_id: int = Path(ge=1)) -> GoldenAgeView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        rules = await world_rules(services, session)
        status = await golden_age_status(session, rules, world_id, await current_epoch(session))
        life = rules.deep_life
        return GoldenAgeView(
            world_id=world_id,
            active=status.active,
            since_epoch=status.since_epoch,
            epochs=status.epochs,
            prosperity_gain=status.prosperity_gain,
            decadence=status.decadence,
            held=status.held,
            communities=status.communities,
            golden_communities=status.golden_communities,
            deepening_epochs=life.golden_age_deepening_epochs,
            deepening_steps=life.golden_age_deepening_steps,
            decadence_epochs=life.golden_age_decadence_epochs,
        )


@router.get("/sons/{son_id}/anchorage", response_model=AnchorageView)
async def son_anchorage(services: ServicesDep, son_id: int = Path(ge=1)) -> AnchorageView:
    async with reader(services) as session:
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError("No such god.")
        epoch = await current_epoch(session)
        anchor = await session.get(EntityRow, son.anchor_entity_id) if son.anchor_entity_id is not None else None
        shrines = await dedicated_structures(session, son.id)
        wars = await incited_wars(session, son.id)
        made = list(
            await session.scalars(select(EntityRow.id).where(EntityRow.creator_son_id == son.id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
        )
        refs = await node_refs(session, [*(work.id for work in shrines), *(war.event_entity_id for war in wars), *made])
        return AnchorageView(
            son_id=son.id,
            anchor=await node_ref(session, anchor.id) if anchor is not None else None,
            anchor_alive=anchor is not None and anchor.status is EntityStatus.CANON,
            anchor_held=await is_held(session, son.id, ANCHOR_KEY, epoch),
            shrines=[refs[work.id] for work in shrines if work.id in refs],
            creations=[refs[item] for item in made if item in refs],
            incited=[
                IncitedWarView(
                    war_id=war.id,
                    event=refs.get(war.event_entity_id),
                    status=war.status,
                    ending=war.ending,
                    started_epoch=war.started_epoch,
                    ended_epoch=war.ended_epoch,
                    battles=war.battles,
                    held=await is_held(session, war.event_entity_id, INCITEMENT_KEY, epoch),
                )
                for war in wars
            ],
        )


@router.get("/entities/{entity_id}/dedication", response_model=DedicationView)
async def structure_dedication(services: ServicesDep, entity_id: int = Path(ge=1)) -> DedicationView:
    async with reader(services) as session:
        structure = await session.get(EntityRow, entity_id)
        if structure is None or structure.entity_type is not EntityType.STRUCTURE:
            raise NotFoundError("No such structure.")
        son = await dedication_of(session, structure.id)
        return DedicationView(
            structure_id=structure.id,
            son=await node_ref(session, son.id) if son is not None else None,
            held=await is_held(session, structure.id, DEDICATION_KEY, await current_epoch(session)),
            anchors_son=son is not None and son.anchor_entity_id == structure.id,
        )
