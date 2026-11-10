from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.dominion import (
    CreatureView,
    DeedWeightView,
    DominionClaimView,
    GodDesignView,
    GodDominionView,
    ImageView,
    LessonView,
    MagicSiteView,
    MiracleView,
    PlaceDominionView,
    RegionRuleView,
    ScaleView,
    ThroneView,
    WorldDominionView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.dominion import (
    CreatureLessonRow,
    DivineCreatureRow,
    DominionRow,
    GodDesignRow,
    GodImageRow,
    GodScaleRow,
    MagicSiteRow,
    MiracleRecordRow,
    RegionDominionRow,
    ThroneRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.dominion import CreatureDeed, DivineScale
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.distance import RegionAtlas

router = APIRouter(tags=["dominion"])
Id = Annotated[int, Path(ge=1)]


def refs_in(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def ruling_pairs(session: AsyncSession, claims: list[DominionRow]) -> set[tuple[int, int]]:
    regions = sorted({row.region_entity_id for row in claims})
    if not regions:
        return set()
    rows = await session.scalars(select(RegionDominionRow).where(RegionDominionRow.region_entity_id.in_(regions)))
    return {(row.god_node_id, row.region_entity_id) for row in rows}


async def claim_views(session: AsyncSession, claims: list[DominionRow]) -> list[DominionClaimView]:
    refs = await node_refs(session, [*(row.god_node_id for row in claims), *(row.region_entity_id for row in claims)])
    ruling = await ruling_pairs(session, claims)
    return [
        DominionClaimView(
            god=refs.get(row.god_node_id),
            region=refs.get(row.region_entity_id),
            strength=row.strength,
            temples=row.temples,
            holy_sites=row.holy_sites,
            prophets=row.prophets,
            miracles=row.miracles,
            worship=row.worship,
            spread=row.spread,
            trend=row.trend,
            epoch=row.epoch,
            ruling=(row.god_node_id, row.region_entity_id) in ruling,
            locked=list(row.locked),
        )
        for row in claims
    ]


async def miracle_views(session: AsyncSession, rows: list[MiracleRecordRow]) -> list[MiracleView]:
    refs = await node_refs(
        session, [value for row in rows for value in (row.god_node_id, row.target_entity_id, row.region_entity_id, row.credited_node_id) if value is not None]
    )
    return [
        MiracleView(
            id=row.id,
            god=refs.get(row.god_node_id),
            kind=row.kind,
            epoch=row.epoch,
            target=refs_in(refs, row.target_entity_id),
            region=refs_in(refs, row.region_entity_id),
            magnitude=row.magnitude,
            witnesses=row.witnesses,
            need=row.need,
            novelty=row.novelty,
            legibility=row.legibility,
            belief=row.belief,
            credited=refs_in(refs, row.credited_node_id),
            locked=list(row.locked),
        )
        for row in rows
    ]


async def creature_views(session: AsyncSession, rows: list[DivineCreatureRow]) -> list[CreatureView]:
    ids = [row.creature_entity_id for row in rows]
    lessons = (
        list(
            await session.scalars(
                select(CreatureLessonRow)
                .where(CreatureLessonRow.creature_entity_id.in_(ids))
                .order_by(CreatureLessonRow.epoch.desc(), CreatureLessonRow.id.desc())
            )
        )
        if ids
        else []
    )
    refs = await node_refs(session, [*ids, *(row.god_node_id for row in rows)])
    return [
        CreatureView(
            creature=refs.get(row.creature_entity_id),
            god=refs.get(row.god_node_id),
            weights=[DeedWeightView(deed=deed, weight=(row.weights or {}).get(deed.value, 0)) for deed in CreatureDeed],
            hunger=row.hunger,
            neglect_epochs=row.neglect_epochs,
            last_deed=row.last_deed,
            deeds=row.deeds,
            since_epoch=row.since_epoch,
            lessons=[
                LessonView(id=lesson.id, deed=lesson.deed, lesson=lesson.lesson, strength=lesson.strength, epoch=lesson.epoch)
                for lesson in lessons
                if lesson.creature_entity_id == row.creature_entity_id
            ],
            locked=list(row.locked),
        )
        for row in rows
    ]


async def throne_views(session: AsyncSession, rows: Iterable[ThroneRow]) -> list[ThroneView]:
    found = list(rows)
    refs = await node_refs(session, [value for row in found for value in (row.world_id, row.place_entity_id, row.holder_node_id) if value is not None])
    return [
        ThroneView(
            id=row.id,
            world=refs.get(row.world_id),
            place=refs.get(row.place_entity_id),
            power=row.power,
            holder=refs_in(refs, row.holder_node_id),
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in found
    ]


async def site_views(session: AsyncSession, rows: Iterable[MagicSiteRow]) -> list[MagicSiteView]:
    found = list(rows)
    refs = await node_refs(
        session, [value for row in found for value in (row.place_entity_id, row.found_by_node_id, row.holder_node_id, row.target_world_id) if value is not None]
    )
    return [
        MagicSiteView(
            id=row.id,
            place=refs.get(row.place_entity_id),
            kind=row.kind,
            school=row.school,
            strength=row.strength,
            found_epoch=row.found_epoch,
            found_by=refs_in(refs, row.found_by_node_id),
            holder=refs_in(refs, row.holder_node_id),
            output=row.output,
            target_world=refs_in(refs, row.target_world_id),
            locked=list(row.locked),
        )
        for row in found
    ]


async def rule_views(session: AsyncSession, rows: list[RegionDominionRow]) -> list[RegionRuleView]:
    refs = await node_refs(session, [value for row in rows for value in (row.region_entity_id, row.god_node_id)])
    return [
        RegionRuleView(region=refs.get(row.region_entity_id), god=refs.get(row.god_node_id), share=row.share, rivals=row.rivals, epoch=row.epoch)
        for row in rows
    ]


@router.get("/dominion/of/{node_id}", response_model=GodDominionView)
async def god_dominion(services: ServicesDep, node_id: Id) -> GodDominionView:
    async with reader(services) as session:
        god = (await node_refs(session, [node_id])).get(node_id)
        if god is None:
            raise NotFoundError("No such god.")
        claims = list(
            await session.scalars(
                select(DominionRow).where(DominionRow.god_node_id == node_id).order_by(DominionRow.strength.desc(), DominionRow.region_entity_id)
            )
        )
        stored = {row.scale: row for row in await session.scalars(select(GodScaleRow).where(GodScaleRow.god_node_id == node_id))}
        design = await session.get(GodDesignRow, node_id)
        image = await session.get(GodImageRow, node_id)
        miracles = list(
            await session.scalars(
                select(MiracleRecordRow).where(MiracleRecordRow.god_node_id == node_id).order_by(MiracleRecordRow.epoch.desc(), MiracleRecordRow.id.desc())
            )
        )
        credited = list(
            await session.scalars(
                select(MiracleRecordRow)
                .where(MiracleRecordRow.credited_node_id == node_id, MiracleRecordRow.god_node_id != node_id)
                .order_by(MiracleRecordRow.epoch.desc(), MiracleRecordRow.id.desc())
            )
        )
        creatures = list(
            await session.scalars(select(DivineCreatureRow).where(DivineCreatureRow.god_node_id == node_id).order_by(DivineCreatureRow.creature_entity_id))
        )
        thrones = await session.scalars(select(ThroneRow).where(ThroneRow.holder_node_id == node_id).order_by(ThroneRow.id))
        sites = await session.scalars(select(MagicSiteRow).where(MagicSiteRow.holder_node_id == node_id).order_by(MagicSiteRow.id))
        return GodDominionView(
            node=god,
            claims=await claim_views(session, claims),
            scales=[
                ScaleView(
                    scale=scale,
                    value=stored[scale].value if scale in stored else 0,
                    stored=scale in stored,
                    locked=list(stored[scale].locked) if scale in stored else [],
                )
                for scale in DivineScale
            ],
            design=GodDesignView.model_validate(design) if design is not None else None,
            image=ImageView.model_validate(image) if image is not None else None,
            miracles=await miracle_views(session, miracles),
            credited=await miracle_views(session, credited),
            creatures=await creature_views(session, creatures),
            thrones=await throne_views(session, thrones),
            sites=await site_views(session, sites),
        )


@router.get("/dominion/place/{place_id}", response_model=PlaceDominionView)
async def place_dominion(services: ServicesDep, place_id: Id) -> PlaceDominionView:
    async with reader(services) as session:
        place = await session.get(EntityRow, place_id)
        ref = (await node_refs(session, [place_id])).get(place_id)
        if place is None or ref is None:
            raise NotFoundError("No such place.")
        atlas = await RegionAtlas.load(session)
        region_id = place.id if place.entity_type is EntityType.REGION else atlas.top_region(place.id)
        rule = await session.get(RegionDominionRow, region_id) if region_id is not None else None
        claims = (
            list(
                await session.scalars(
                    select(DominionRow).where(DominionRow.region_entity_id == place.id).order_by(DominionRow.strength.desc(), DominionRow.god_node_id)
                )
            )
            if place.entity_type is EntityType.REGION
            else []
        )

        def here(entity_id: int) -> bool:
            return entity_id == place.id or (place.entity_type is EntityType.REGION and atlas.top_region(entity_id) == place.id)

        world = [place.world_id] if place.world_id is not None else []
        thrones = [
            row for row in await session.scalars(select(ThroneRow).where(ThroneRow.world_id.in_(world)).order_by(ThroneRow.id)) if here(row.place_entity_id)
        ]
        sites = [row for row in await session.scalars(select(MagicSiteRow).order_by(MagicSiteRow.id)) if here(row.place_entity_id)]
        dwellers = set(await session.scalars(select(EntityRow.id).where(or_(EntityRow.location_id == place.id, EntityRow.id == place.id))))
        creatures = [
            row
            for row in await session.scalars(select(DivineCreatureRow).order_by(DivineCreatureRow.creature_entity_id))
            if here(row.creature_entity_id) or row.creature_entity_id in dwellers
        ]
        return PlaceDominionView(
            place=ref,
            rule=(await rule_views(session, [rule]))[0] if rule is not None else None,
            claims=await claim_views(session, claims),
            thrones=await throne_views(session, thrones),
            sites=await site_views(session, sites),
            creatures=await creature_views(session, creatures),
        )


@router.get("/dominion/world/{world_id}", response_model=WorldDominionView)
async def world_dominion(services: ServicesDep, world_id: Id) -> WorldDominionView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        world = (await node_refs(session, [world_id]))[world_id]
        rules = list(
            await session.scalars(
                select(RegionDominionRow)
                .where(RegionDominionRow.world_id == world_id)
                .order_by(RegionDominionRow.share.desc(), RegionDominionRow.region_entity_id)
            )
        )
        thrones = await session.scalars(select(ThroneRow).where(ThroneRow.world_id == world_id).order_by(ThroneRow.id))
        places = select(EntityRow.id).where(EntityRow.world_id == world_id)
        sites = await session.scalars(select(MagicSiteRow).where(MagicSiteRow.place_entity_id.in_(places)).order_by(MagicSiteRow.id))
        return WorldDominionView(
            world=world, rules=await rule_views(session, rules), thrones=await throne_views(session, thrones), sites=await site_views(session, sites)
        )
