from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.pursuits import (
    ArtMovementView,
    ArtPriceView,
    ArtSaleView,
    BetView,
    BirthSignView,
    CanonWorkView,
    ClubView,
    CollectorView,
    ConstructView,
    ForgeryView,
    InstructionOrderView,
    InstructionSetView,
    LeagueView,
    MatchView,
    MonsterContractView,
    PursuitsNodeView,
    RemadeView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.arts import ArtMovementRow, ArtPriceRow, ArtSaleRow, BetRow, CanonWorkRow, ClubRow, CollectorRow, ForgeryRow, LeagueRow, MatchRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow, RemadeRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sacred import BirthSignRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.node import NodeKind

router = APIRouter(tags=["pursuits"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def construct_view(row: ConstructRow, refs: dict[int, NodeRef], wills: dict[int, MindWill]) -> ConstructView:
    return ConstructView(
        body=ref(refs, row.entity_id),
        material=row.material,
        power_source=row.power_source,
        power=row.power,
        upkeep=row.upkeep,
        maker=at(refs, row.maker_entity_id),
        decay=row.decay,
        will=wills.get(row.entity_id, MindWill.INSTRUCTED),
        soul=at(refs, row.soul_entity_id),
        made_epoch=row.made_epoch,
        locked=row.locked,
    )


def set_view(row: InstructionSetRow, orders: list[InstructionOrderRow], refs: dict[int, NodeRef]) -> InstructionSetView:
    return InstructionSetView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        binding=row.binding,
        command_token=row.command_token,
        token=at(refs, row.token_entity_id),
        holder=at(refs, row.holder_node_id),
        kill_switch=row.kill_switch,
        kill_token=at(refs, row.kill_token_entity_id),
        literalness=row.literalness,
        orders=[
            InstructionOrderView(
                id=order.id,
                kind=order.kind,
                target=at(refs, order.target_node_id),
                priority=order.priority,
                condition=order.condition,
                until_epoch=order.until_epoch,
                lapsed=order.lapsed,
                locked=order.locked,
            )
            for order in orders
            if order.set_id == row.id
        ],
        locked=row.locked,
    )


def club_view(row: ClubRow, refs: dict[int, NodeRef]) -> ClubView:
    return ClubView(
        faction=ref(refs, row.faction_entity_id),
        kind=row.kind,
        league=at(refs, row.league_entity_id),
        arena=at(refs, row.arena_entity_id),
        wins=row.wins,
        losses=row.losses,
        rating=row.rating,
        fandom=row.fandom,
        line=row.line,
        line_node=at(refs, row.line_entity_id),
        leverage=row.leverage,
        bought_by=at(refs, row.bought_by_entity_id),
        founded_epoch=row.founded_epoch,
        locked=row.locked,
    )


def forgery_view(row: ForgeryRow, refs: dict[int, NodeRef]) -> ForgeryView:
    return ForgeryView(
        id=row.id,
        item=ref(refs, row.item_entity_id),
        kind=row.kind,
        forger=at(refs, row.forger_entity_id),
        original=at(refs, row.original_entity_id),
        brand_id=row.brand_id,
        claim_id=row.claim_id,
        skill=row.skill,
        status=row.status,
        exposed_by=at(refs, row.exposed_by_entity_id),
        exposed_epoch=row.exposed_epoch,
        made_epoch=row.made_epoch,
        locked=row.locked,
    )


async def art_rows(session: AsyncSession, node_id: int) -> tuple[list[ArtPriceRow], list[ArtSaleRow], list[ForgeryRow], list[CanonWorkRow]]:
    authored = select(ArtworkProfileRow.artwork_entity_id).where(ArtworkProfileRow.author_entity_id == node_id)
    prices = list(
        await session.scalars(
            select(ArtPriceRow)
            .where(or_(ArtPriceRow.artwork_entity_id == node_id, ArtPriceRow.last_buyer_node_id == node_id, ArtPriceRow.artwork_entity_id.in_(authored)))
            .order_by(ArtPriceRow.price.desc(), ArtPriceRow.artwork_entity_id)
        )
    )
    sales = list(
        await session.scalars(
            select(ArtSaleRow)
            .where(
                or_(
                    ArtSaleRow.artwork_entity_id == node_id,
                    ArtSaleRow.seller_node_id == node_id,
                    ArtSaleRow.buyer_node_id == node_id,
                    ArtSaleRow.fair_place_entity_id == node_id,
                )
            )
            .order_by(ArtSaleRow.epoch.desc(), ArtSaleRow.id.desc())
        )
    )
    forgeries = list(
        await session.scalars(
            select(ForgeryRow)
            .where(
                or_(
                    ForgeryRow.item_entity_id == node_id,
                    ForgeryRow.forger_entity_id == node_id,
                    ForgeryRow.original_entity_id == node_id,
                    ForgeryRow.exposed_by_entity_id == node_id,
                )
            )
            .order_by(ForgeryRow.id.desc())
        )
    )
    canon = list(
        await session.scalars(
            select(CanonWorkRow)
            .where(or_(CanonWorkRow.people_entity_id == node_id, CanonWorkRow.artwork_entity_id == node_id))
            .order_by(CanonWorkRow.weight.desc(), CanonWorkRow.artwork_entity_id)
        )
    )
    return prices, sales, forgeries, canon


async def sport_rows(session: AsyncSession, node_id: int) -> tuple[list[ClubRow], LeagueRow | None, list[MatchRow], list[BetRow]]:
    clubs = list(
        await session.scalars(
            select(ClubRow)
            .where(
                or_(
                    ClubRow.faction_entity_id == node_id,
                    ClubRow.league_entity_id == node_id,
                    ClubRow.arena_entity_id == node_id,
                    ClubRow.line_entity_id == node_id,
                    ClubRow.bought_by_entity_id == node_id,
                )
            )
            .order_by(ClubRow.wins.desc(), ClubRow.faction_entity_id)
        )
    )
    league = await session.get(LeagueRow, node_id) or await session.scalar(select(LeagueRow).where(LeagueRow.polity_entity_id == node_id).limit(1))
    matches = list(
        await session.scalars(
            select(MatchRow)
            .where(or_(MatchRow.home_entity_id == node_id, MatchRow.away_entity_id == node_id, MatchRow.league_entity_id == node_id))
            .order_by(MatchRow.epoch.desc(), MatchRow.id.desc())
        )
    )
    bets = list(
        await session.scalars(select(BetRow).where(or_(BetRow.settlement_entity_id == node_id, BetRow.club_entity_id == node_id)).order_by(BetRow.id.desc()))
    )
    return clubs, league, matches, bets


@router.get("/pursuits/of/{node_id}", response_model=PursuitsNodeView)
async def node_pursuits(services: ServicesDep, node_id: NodeId) -> PursuitsNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        prices, sales, forgeries, canon = await art_rows(session, node_id)
        collector = await session.get(CollectorRow, node_id)
        movement = await session.get(ArtMovementRow, node_id)
        clubs, league, matches, bets = await sport_rows(session, node_id)
        construct = await session.get(ConstructRow, node_id)
        made = list(await session.scalars(select(ConstructRow).where(ConstructRow.maker_entity_id == node_id).order_by(ConstructRow.entity_id)))
        bodies_ids = [row.entity_id for row in [*([construct] if construct is not None else []), *made]]
        wills = {row.node_id: row.will for row in await session.scalars(select(MindProfileRow).where(MindProfileRow.node_id.in_(bodies_ids)))}
        instructions = list(
            await session.scalars(
                select(InstructionSetRow)
                .where(
                    or_(
                        InstructionSetRow.owner_entity_id == node_id,
                        InstructionSetRow.holder_node_id == node_id,
                        InstructionSetRow.token_entity_id == node_id,
                        InstructionSetRow.kill_token_entity_id == node_id,
                    )
                )
                .order_by(InstructionSetRow.id)
            )
        )
        orders = list(
            await session.scalars(
                select(InstructionOrderRow)
                .where(InstructionOrderRow.set_id.in_([row.id for row in instructions] or [0]))
                .order_by(InstructionOrderRow.priority, InstructionOrderRow.id)
            )
        )
        remade = await session.get(RemadeRow, node_id)
        contracts = list(
            await session.scalars(
                select(MonsterContractRow)
                .where(
                    or_(
                        MonsterContractRow.community_entity_id == node_id,
                        MonsterContractRow.beast_entity_id == node_id,
                        MonsterContractRow.hunter_entity_id == node_id,
                    )
                )
                .order_by(MonsterContractRow.id.desc())
            )
        )
        sign = await session.get(BirthSignRow, node_id)
        bodies = [*([construct] if construct is not None else []), *made]
        refs = await refs_of(
            session,
            [
                node_id,
                *(item for row in prices for item in (row.artwork_entity_id, row.last_buyer_node_id)),
                *(item for row in sales for item in (row.artwork_entity_id, row.seller_node_id, row.buyer_node_id, row.fair_place_entity_id)),
                *((collector.holder_entity_id, collector.taste_form_entity_id) if collector is not None else ()),
                *(item for row in forgeries for item in (row.item_entity_id, row.forger_entity_id, row.original_entity_id, row.exposed_by_entity_id)),
                *(item for row in canon for item in (row.people_entity_id, row.artwork_entity_id)),
                *((movement.faction_entity_id, movement.art_form_entity_id) if movement is not None else ()),
                *(
                    item
                    for row in clubs
                    for item in (row.faction_entity_id, row.league_entity_id, row.arena_entity_id, row.line_entity_id, row.bought_by_entity_id)
                ),
                *((league.faction_entity_id, league.polity_entity_id, league.champion_entity_id) if league is not None else ()),
                *(item for row in matches for item in (row.league_entity_id, row.home_entity_id, row.away_entity_id, row.winner_entity_id)),
                *(item for row in bets for item in (row.settlement_entity_id, row.club_entity_id)),
                *(item for row in bodies for item in (row.entity_id, row.maker_entity_id, row.soul_entity_id)),
                *(item for row in instructions for item in (row.owner_entity_id, row.token_entity_id, row.holder_node_id, row.kill_token_entity_id)),
                *(row.target_node_id for row in orders),
                *((remade.mortal_entity_id, remade.sentenced_by_entity_id, remade.bound_to_entity_id) if remade is not None else ()),
                *(item for row in contracts for item in (row.community_entity_id, row.beast_entity_id, row.hunter_entity_id)),
                *((sign.ruling_celestial_entity_id,) if sign is not None else ()),
            ],
        )
        return PursuitsNodeView(
            node=own[node_id],
            prices=[
                ArtPriceView(
                    artwork=ref(refs, row.artwork_entity_id),
                    price=row.price,
                    provenance=row.provenance,
                    interest=row.interest,
                    last_buyer=at(refs, row.last_buyer_node_id),
                    last_sale_epoch=row.last_sale_epoch,
                    updated_epoch=row.updated_epoch,
                    locked=row.locked,
                )
                for row in prices
            ],
            sales=[
                ArtSaleView(
                    id=row.id,
                    artwork=ref(refs, row.artwork_entity_id),
                    seller=at(refs, row.seller_node_id),
                    buyer=at(refs, row.buyer_node_id),
                    price=row.price,
                    fair_place=at(refs, row.fair_place_entity_id),
                    epoch=row.epoch,
                    locked=row.locked,
                )
                for row in sales
            ],
            collector=CollectorView(
                holder=ref(refs, collector.holder_entity_id),
                role=collector.role,
                taste=at(refs, collector.taste_form_entity_id),
                connoisseurship=collector.connoisseurship,
                since_epoch=collector.since_epoch,
                locked=collector.locked,
            )
            if collector is not None
            else None,
            forgeries=[forgery_view(row, refs) for row in forgeries],
            canon=[
                CanonWorkView(
                    people=ref(refs, row.people_entity_id),
                    artwork=ref(refs, row.artwork_entity_id),
                    path=row.path,
                    weight=row.weight,
                    contested=row.contested,
                    since_epoch=row.since_epoch,
                    locked=row.locked,
                )
                for row in canon
            ],
            movement=ArtMovementView(
                faction=ref(refs, movement.faction_entity_id),
                manifesto=movement.manifesto,
                art_form=at(refs, movement.art_form_entity_id),
                orthodoxy=movement.orthodoxy,
                scandals=movement.scandals,
                patrons=movement.patrons,
                founded_epoch=movement.founded_epoch,
                locked=movement.locked,
            )
            if movement is not None
            else None,
            clubs=[club_view(row, refs) for row in clubs],
            league=LeagueView(
                faction=ref(refs, league.faction_entity_id),
                polity=at(refs, league.polity_entity_id),
                champion=at(refs, league.champion_entity_id),
                season_epoch=league.season_epoch,
                locked=league.locked,
            )
            if league is not None
            else None,
            matches=[
                MatchView(
                    id=row.id,
                    league=at(refs, row.league_entity_id),
                    home=ref(refs, row.home_entity_id),
                    away=ref(refs, row.away_entity_id),
                    winner=at(refs, row.winner_entity_id),
                    stake=row.stake,
                    riot=row.riot,
                    epoch=row.epoch,
                    locked=row.locked,
                )
                for row in matches
            ],
            bets=[
                BetView(
                    id=row.id,
                    match_id=row.match_id,
                    settlement=ref(refs, row.settlement_entity_id),
                    club=ref(refs, row.club_entity_id),
                    stake=row.stake,
                    won=row.won,
                    locked=row.locked,
                )
                for row in bets
            ],
            as_construct=construct_view(construct, refs, wills) if construct is not None else None,
            made=[construct_view(row, refs, wills) for row in made],
            instructions=[set_view(row, orders, refs) for row in instructions],
            remade=RemadeView(
                mortal=ref(refs, remade.mortal_entity_id),
                lost_function=remade.lost_function,
                forced_function=remade.forced_function,
                sentenced_by=at(refs, remade.sentenced_by_entity_id),
                case_id=remade.case_id,
                bound_to=at(refs, remade.bound_to_entity_id),
                grievance=remade.grievance,
                epoch=remade.epoch,
                locked=remade.locked,
            )
            if remade is not None
            else None,
            contracts=[
                MonsterContractView(
                    id=row.id,
                    community=ref(refs, row.community_entity_id),
                    beast=ref(refs, row.beast_entity_id),
                    bounty=row.bounty,
                    hunter=at(refs, row.hunter_entity_id),
                    status=row.status,
                    study=row.study,
                    posted_epoch=row.posted_epoch,
                    closed_epoch=row.closed_epoch,
                    locked=row.locked,
                )
                for row in contracts
            ],
            sign=BirthSignView(
                mortal=ref(refs, sign.mortal_entity_id),
                season=sign.season,
                ruling_celestial=at(refs, sign.ruling_celestial_entity_id),
                dreaded=sign.dreaded,
                influence=sign.influence,
                fortune=sign.fortune,
                exposed=sign.exposed,
                born_epoch=sign.born_epoch,
                locked=sign.locked,
            )
            if sign is not None
            else None,
        )
