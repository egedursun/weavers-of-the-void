from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.outer_agency import (
    OuterAgencyView,
    OuterHeraldView,
    OuterIncursionView,
    OuterPactView,
    OuterPlanView,
    OuterRelationView,
    OuterSealView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.divine import OuterBeingProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.outer_agency import OuterHeraldRow, OuterIncursionRow, OuterPactRow, OuterPlanRow, OuterRelationRow, OuterSealRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.outer import OuterFate

router = APIRouter(tags=["outer-beings"])
Id = Annotated[int, Path(ge=1)]


@router.get("/outer-beings/{being_id}/agency", response_model=OuterAgencyView)
async def outer_agency(being_id: Id, services: ServicesDep) -> OuterAgencyView:
    async with reader(services) as session:
        being = await session.get(EntityRow, being_id)
        if being is None or being.entity_type is not EntityType.OUTER_BEING:
            raise NotFoundError("No such outer being.")
        rules = await world_rules(services, session)
        profile = await session.get(OuterBeingProfileRow, being_id)
        plans = list(await session.scalars(select(OuterPlanRow).where(OuterPlanRow.outer_entity_id == being_id).order_by(OuterPlanRow.id.desc())))
        heralds = list(await session.scalars(select(OuterHeraldRow).where(OuterHeraldRow.outer_entity_id == being_id).order_by(OuterHeraldRow.herald_node_id)))
        incursions = list(
            await session.scalars(select(OuterIncursionRow).where(OuterIncursionRow.outer_entity_id == being_id).order_by(OuterIncursionRow.id.desc()))
        )
        pacts = list(await session.scalars(select(OuterPactRow).where(OuterPactRow.outer_entity_id == being_id).order_by(OuterPactRow.id.desc())))
        relations = list(
            await session.scalars(select(OuterRelationRow).where(OuterRelationRow.outer_entity_id == being_id).order_by(OuterRelationRow.other_entity_id))
        )
        seals = list(await session.scalars(select(OuterSealRow).where(OuterSealRow.outer_entity_id == being_id).order_by(OuterSealRow.id.desc())))
        wanted = [
            being_id,
            *(plan.target_node_id for plan in plans if plan.target_node_id is not None),
            *(herald.herald_node_id for herald in heralds),
            *(row.region_entity_id for row in incursions if row.region_entity_id is not None),
            *(pact.holder_node_id for pact in pacts),
            *(relation.other_entity_id for relation in relations),
            *(seal.sealer_node_id for seal in seals if seal.sealer_node_id is not None),
        ]
        refs = await node_refs(session, wanted)
        stages = max(1, rules.outer_beings.plan_stages)
        return OuterAgencyView(
            being=refs[being_id],
            fate=profile.fate if profile is not None else OuterFate.ACTIVE,
            unfed_epochs=profile.unfed_epochs if profile is not None else 0,
            starve_epochs=rules.outer_beings.starve_epochs,
            plans=[
                OuterPlanView(
                    id=plan.id,
                    goal=plan.goal,
                    stage=plan.stage,
                    stages=stages,
                    progress=plan.progress,
                    target=refs.get(plan.target_node_id) if plan.target_node_id is not None else None,
                    state=plan.state,
                    started_epoch=plan.started_epoch,
                    sign_epoch=plan.sign_epoch,
                    locked=list(plan.locked),
                )
                for plan in plans
            ],
            heralds=[OuterHeraldView(herald=refs[row.herald_node_id], zeal=row.zeal, bound_epoch=row.bound_epoch, locked=list(row.locked)) for row in heralds],
            incursions=[
                OuterIncursionView(
                    id=row.id,
                    rift_id=row.rift_id,
                    region=refs.get(row.region_entity_id) if row.region_entity_id is not None else None,
                    stage=row.stage,
                    strength=row.strength,
                    started_epoch=row.started_epoch,
                    ended_epoch=row.ended_epoch,
                    locked=list(row.locked),
                )
                for row in incursions
            ],
            pacts=[
                OuterPactView(
                    id=row.id,
                    holder=refs[row.holder_node_id],
                    price=row.price,
                    paid=row.paid,
                    power_id=row.power_id,
                    struck_epoch=row.struck_epoch,
                    locked=list(row.locked),
                )
                for row in pacts
            ],
            relations=[
                OuterRelationView(other=refs[row.other_entity_id], relation=row.relation, since_epoch=row.since_epoch, locked=list(row.locked))
                for row in relations
            ],
            seals=[
                OuterSealView(
                    id=row.id,
                    kind=row.kind,
                    strength=row.strength,
                    sealer=refs.get(row.sealer_node_id) if row.sealer_node_id is not None else None,
                    sealed_epoch=row.sealed_epoch,
                    broken_epoch=row.broken_epoch,
                    locked=list(row.locked),
                )
                for row in seals
            ],
        )
