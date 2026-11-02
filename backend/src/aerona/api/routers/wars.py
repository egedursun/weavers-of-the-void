from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import Page
from aerona.api.schemas.wars import (
    ArmyView,
    BattleView,
    CaptiveView,
    HeroView,
    SiegeView,
    TributeView,
    WarSideView,
    WarSummary,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, SiegeRow, TributeRow, WarRow, WarSideRow
from aerona.domain.enums.war import CaptiveStatus, TributeStatus, WarStatus
from aerona.engine.services.sides import heroes_of
from aerona.engine.services.war_geography import Neighbourhood

router = APIRouter(tags=["wars"])

PAGE_DEFAULT = 50
PAGE_MAX = 500
NO_WAR = "No such war."
WarId = Annotated[int, Path(ge=1)]
EntityId = Annotated[int, Path(ge=1)]


@dataclass
class Paging:
    offset: Annotated[int, Query(ge=0)] = 0
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX)] = PAGE_DEFAULT


PagingDep = Annotated[Paging, Depends()]


async def page_of[T](session: AsyncSession, statement: Select[T], offset: int, limit: int) -> tuple[list[T], int]:
    total = int(await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)
    return list(await session.scalars(statement.offset(offset).limit(limit))), total


async def summaries(session: AsyncSession, wars: list[WarRow]) -> list[WarSummary]:
    sides = list(
        await session.scalars(select(WarSideRow).where(WarSideRow.war_id.in_([war.id for war in wars])).order_by(WarSideRow.war_id, WarSideRow.joined_epoch))
    )
    refs = await node_refs(
        session,
        [
            *(war.event_entity_id for war in wars),
            *(war.victor_entity_id for war in wars if war.victor_entity_id is not None),
            *(war.loser_entity_id for war in wars if war.loser_entity_id is not None),
            *(side.entity_id for side in sides),
        ],
    )
    result: list[WarSummary] = []
    for war in wars:
        views = [
            WarSideView(entity=refs.get(side.entity_id), side=side.side, joined_epoch=side.joined_epoch, left_epoch=side.left_epoch)
            for side in sides
            if side.war_id == war.id
        ]
        result.append(
            WarSummary(
                id=war.id,
                event=refs.get(war.event_entity_id),
                world_id=war.world_id,
                status=war.status,
                cause=war.cause,
                cause_text=war.cause_text,
                started_epoch=war.started_epoch,
                ended_epoch=war.ended_epoch,
                last_clash_epoch=war.last_clash_epoch,
                battles=war.battles,
                score=war.score,
                violence=war.violence,
                ending=war.ending,
                victor=refs.get(war.victor_entity_id) if war.victor_entity_id is not None else None,
                loser=refs.get(war.loser_entity_id) if war.loser_entity_id is not None else None,
                sides=views,
            )
        )
    return result


async def require_war(session: AsyncSession, war_id: int) -> WarRow:
    war = await session.get(WarRow, war_id)
    if war is None:
        raise NotFoundError(NO_WAR)
    return war


async def wars_page(session: AsyncSession, statement: Select[WarRow], paging: Paging) -> Page[WarSummary]:
    rows, total = await page_of(session, statement.order_by(WarRow.id.desc()), paging.offset, paging.limit)
    return Page[WarSummary](items=await summaries(session, rows), total=total, offset=paging.offset, limit=paging.limit)


@router.get("/wars", response_model=Page[WarSummary])
async def list_wars(
    services: ServicesDep,
    paging: PagingDep,
    *,
    status: WarStatus | None = None,
    world_id: Annotated[int | None, Query(ge=1)] = None,
) -> Page[WarSummary]:
    statement = select(WarRow)
    if status is not None:
        statement = statement.where(WarRow.status == status)
    if world_id is not None:
        statement = statement.where(WarRow.world_id == world_id)
    async with reader(services) as session:
        return await wars_page(session, statement, paging)


@router.get("/wars/{war_id}", response_model=WarSummary)
async def read_war(services: ServicesDep, war_id: WarId) -> WarSummary:
    async with reader(services) as session:
        return (await summaries(session, [await require_war(session, war_id)]))[0]


@router.get("/wars/{war_id}/armies", response_model=Page[ArmyView])
async def war_armies(services: ServicesDep, war_id: WarId, paging: PagingDep) -> Page[ArmyView]:
    async with reader(services) as session:
        await require_war(session, war_id)
        rows, total = await page_of(
            session, select(ArmyRow).where(ArmyRow.war_id == war_id).order_by(ArmyRow.raised_epoch.desc(), ArmyRow.entity_id), paging.offset, paging.limit
        )
        refs = await node_refs(session, [value for row in rows for value in (row.entity_id, row.owner_entity_id, row.commander_entity_id) if value is not None])
        items = [
            ArmyView(
                army=refs.get(row.entity_id),
                war_id=row.war_id,
                owner=refs.get(row.owner_entity_id),
                commander=refs.get(row.commander_entity_id) if row.commander_entity_id is not None else None,
                raised_epoch=row.raised_epoch,
                disbanded_epoch=row.disbanded_epoch,
            )
            for row in rows
        ]
        return Page[ArmyView](items=items, total=total, offset=paging.offset, limit=paging.limit)


@router.get("/wars/{war_id}/battles", response_model=Page[BattleView])
async def war_battles(services: ServicesDep, war_id: WarId, paging: PagingDep) -> Page[BattleView]:
    async with reader(services) as session:
        await require_war(session, war_id)
        rows, total = await page_of(
            session,
            select(BattleRow).where(BattleRow.war_id == war_id).order_by(BattleRow.epoch.desc(), BattleRow.sequence.desc()),
            paging.offset,
            paging.limit,
        )
        refs = await node_refs(
            session,
            [value for row in rows for value in (row.record_entity_id, row.place_entity_id, row.winner_entity_id, row.loser_entity_id) if value is not None],
        )
        items = [
            BattleView(
                id=row.id,
                war_id=row.war_id,
                epoch=row.epoch,
                sequence=row.sequence,
                record=refs.get(row.record_entity_id) if row.record_entity_id is not None else None,
                place=refs.get(row.place_entity_id) if row.place_entity_id is not None else None,
                winner=refs.get(row.winner_entity_id),
                loser=refs.get(row.loser_entity_id),
                outcome=row.outcome,
                gap=row.gap,
                siege_id=row.siege_id,
            )
            for row in rows
        ]
        return Page[BattleView](items=items, total=total, offset=paging.offset, limit=paging.limit)


@router.get("/wars/{war_id}/sieges", response_model=Page[SiegeView])
async def war_sieges(services: ServicesDep, war_id: WarId, paging: PagingDep) -> Page[SiegeView]:
    async with reader(services) as session:
        await require_war(session, war_id)
        rows, total = await page_of(
            session, select(SiegeRow).where(SiegeRow.war_id == war_id).order_by(SiegeRow.started_epoch.desc(), SiegeRow.id.desc()), paging.offset, paging.limit
        )
        refs = await node_refs(session, [value for row in rows for value in (row.besieged_entity_id, row.besieger_entity_id)])
        items = [
            SiegeView(
                id=row.id,
                war_id=row.war_id,
                besieged=refs.get(row.besieged_entity_id),
                besieger=refs.get(row.besieger_entity_id),
                status=row.status,
                started_epoch=row.started_epoch,
                ended_epoch=row.ended_epoch,
                rounds=row.rounds,
            )
            for row in rows
        ]
        return Page[SiegeView](items=items, total=total, offset=paging.offset, limit=paging.limit)


@router.get("/captives", response_model=Page[CaptiveView])
async def list_captives(
    services: ServicesDep,
    paging: PagingDep,
    *,
    status: CaptiveStatus | None = None,
    war_id: Annotated[int | None, Query(ge=1)] = None,
    community_id: Annotated[int | None, Query(ge=1)] = None,
) -> Page[CaptiveView]:
    statement = select(CaptiveRow)
    if status is not None:
        statement = statement.where(CaptiveRow.status == status)
    if war_id is not None:
        statement = statement.where(CaptiveRow.war_id == war_id)
    if community_id is not None:
        statement = statement.where(or_(CaptiveRow.captor_entity_id == community_id, CaptiveRow.home_entity_id == community_id))
    async with reader(services) as session:
        rows, total = await page_of(session, statement.order_by(CaptiveRow.taken_epoch.desc(), CaptiveRow.id.desc()), paging.offset, paging.limit)
        refs = await node_refs(
            session, [value for row in rows for value in (row.captive_entity_id, row.captor_entity_id, row.home_entity_id) if value is not None]
        )
        items = [
            CaptiveView(
                id=row.id,
                captive=refs.get(row.captive_entity_id),
                captor=refs.get(row.captor_entity_id),
                home=refs.get(row.home_entity_id) if row.home_entity_id is not None else None,
                war_id=row.war_id,
                status=row.status,
                taken_epoch=row.taken_epoch,
                released_epoch=row.released_epoch,
                ransom_paid=row.ransom_paid,
            )
            for row in rows
        ]
        return Page[CaptiveView](items=items, total=total, offset=paging.offset, limit=paging.limit)


@router.get("/tributes", response_model=Page[TributeView])
async def list_tributes(
    services: ServicesDep,
    paging: PagingDep,
    *,
    status: TributeStatus | None = None,
    war_id: Annotated[int | None, Query(ge=1)] = None,
    community_id: Annotated[int | None, Query(ge=1)] = None,
) -> Page[TributeView]:
    statement = select(TributeRow)
    if status is not None:
        statement = statement.where(TributeRow.status == status)
    if war_id is not None:
        statement = statement.where(TributeRow.war_id == war_id)
    if community_id is not None:
        statement = statement.where(or_(TributeRow.payer_entity_id == community_id, TributeRow.receiver_entity_id == community_id))
    async with reader(services) as session:
        rows, total = await page_of(session, statement.order_by(TributeRow.since_epoch.desc(), TributeRow.id.desc()), paging.offset, paging.limit)
        refs = await node_refs(session, [value for row in rows for value in (row.payer_entity_id, row.receiver_entity_id)])
        items = [
            TributeView(
                id=row.id,
                payer=refs.get(row.payer_entity_id),
                receiver=refs.get(row.receiver_entity_id),
                war_id=row.war_id,
                status=row.status,
                since_epoch=row.since_epoch,
                ended_epoch=row.ended_epoch,
            )
            for row in rows
        ]
        return Page[TributeView](items=items, total=total, offset=paging.offset, limit=paging.limit)


@router.get("/entities/{entity_id}/wars", response_model=Page[WarSummary])
async def community_wars(services: ServicesDep, entity_id: EntityId, paging: PagingDep) -> Page[WarSummary]:
    statement = select(WarRow).where(WarRow.id.in_(select(WarSideRow.war_id).where(WarSideRow.entity_id == entity_id)))
    async with reader(services) as session:
        return await wars_page(session, statement, paging)


@router.get("/entities/{entity_id}/heroes", response_model=list[HeroView])
async def community_heroes(services: ServicesDep, entity_id: EntityId) -> list[HeroView]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        heroes = await heroes_of(session, entity_id, await Neighbourhood.load(session, rules))
        refs = await node_refs(session, [hero.id for hero in heroes])
        return [HeroView(hero=refs[hero.id], role=hero.mortal_role, entity_type=hero.entity_type, power=hero.power_level) for hero in heroes if hero.id in refs]
