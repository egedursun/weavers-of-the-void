from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.eras import EraEffectView, ErasNodeView, EraTechniqueView, TechProgrammeView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.eras import ERA_EFFECTS, TECHNIQUE_ERAS
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.cycles.book import realm_of
from aerona.engine.eras.effects import channel_value, era_holders, era_of, era_techniques, held_by, world_start
from aerona.engine.primitives.knowledge import LawBook

router = APIRouter(tags=["eras"])
COMMUNITIES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
NodeId = Annotated[int, Path(ge=1)]


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


@router.get("/eras/of/{node_id}", response_model=ErasNodeView)
async def node_eras(services: ServicesDep, node_id: NodeId) -> ErasNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        rules = await world_rules(services, session)
        known = await era_techniques(session, node_id)
        entity = await session.get(EntityRow, node_id)
        keeper = None
        for holder in await era_holders(session, node_id):
            found = await session.get(EntityRow, holder)
            if found is not None and found.entity_type in COMMUNITIES:
                keeper = holder
                break
        kept = await held_by(session, keeper) if keeper is not None else frozenset()
        realm = node_id if await session.get(PolityProfileRow, node_id) is not None else await realm_of(session, node_id)
        programmes = (
            list(await session.scalars(select(TechProgrammeRow).where(TechProgrammeRow.polity_entity_id == realm).order_by(TechProgrammeRow.id.desc())))
            if realm is not None
            else []
        )
        start = await world_start(session)
        barred = entity is not None and (await LawBook.load(session)).has(NaturalLaw.NO_GUNPOWDER, entity.world_id)
        refs = await node_refs(
            session,
            sorted(
                {node_id, *([realm] if realm is not None else []), *([keeper] if keeper is not None else []), *(row.polity_entity_id for row in programmes)}
            ),
        )
    return ErasNodeView(
        node=ref(refs, node_id),
        realm=refs.get(realm) if realm is not None else None,
        keeper=refs.get(keeper) if keeper is not None else None,
        era=era_of(known, start),
        starting_era=start,
        no_gunpowder=barred,
        channels=[EraEffectView(channel=channel, value=value) for channel in EraChannel if (value := channel_value(rules, known, channel))],
        techniques=[
            EraTechniqueView(
                technique=technique,
                label=TECHNIQUES[technique].label,
                effect=TECHNIQUES[technique].effect,
                era=era,
                held=technique in known,
                kept=technique in kept,
                programme=TECHNIQUES[technique].programme,
                requires=list(TECHNIQUES[technique].requires),
                effects=[EraEffectView(channel=channel, value=int(getattr(rules.eras, field))) for channel, field in ERA_EFFECTS.get(technique, ())],
            )
            for technique, era in TECHNIQUE_ERAS.items()
        ],
        programmes=[
            TechProgrammeView(
                id=row.id,
                polity=ref(refs, row.polity_entity_id),
                technique=row.technique,
                label=TECHNIQUES[row.technique].label,
                progress=row.progress,
                stage=row.stage,
                visibility=row.visibility,
                sabotaged=row.sabotaged,
                started_epoch=row.started_epoch,
                finished_epoch=row.finished_epoch,
                locked=row.locked,
            )
            for row in programmes
        ],
    )
