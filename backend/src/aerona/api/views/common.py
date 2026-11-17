from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.records import (
    Ascension,
    BondRecord,
    BondView,
    ChronicleLineRecord,
    ForeignGodRecord,
    ImageRecord,
    Kin,
    NodeRef,
    Requirement,
    RouteRecord,
    RouteStatusRecord,
    SonCard,
    SonPower,
    SonPublic,
    SonRecord,
)
from aerona.catalog.travel import TRAVEL_MODEL
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.meta import ImageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import VISIBLE_BOND_STATES, BondKind, BondState
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.cosmos.routes import RouteBook, current_calendar, forgotten_world_ids
from aerona.engine.lore.display_bonds import DerivedBond, derived_bonds
from aerona.rules.registry import Rules
from aerona.services.images.records import cover_of
from aerona.services.state import SonView


async def node_refs(session: AsyncSession, node_ids: Iterable[int]) -> dict[int, NodeRef]:
    wanted = sorted({node_id for node_id in node_ids})
    if not wanted:
        return {}
    rows = await session.execute(select(NodeRow.id, NodeRow.kind, NodeRow.name).where(NodeRow.id.in_(wanted)))
    return {node_id: NodeRef(id=node_id, kind=kind, name=name) for node_id, kind, name in rows}


async def node_ref(session: AsyncSession, node_id: int | None) -> NodeRef | None:
    if node_id is None:
        return None
    return (await node_refs(session, [node_id])).get(node_id)


def kin(value: tuple[int, str, int] | None) -> Kin | None:
    return Kin(id=value[0], name=value[1], value=value[2]) if value is not None else None


def son_public(view: SonView) -> SonPublic:
    card = view.card
    return SonPublic(
        son=SonRecord.model_validate(view.son),
        powers=[SonPower.model_validate(power) for power in view.powers],
        max_hp=view.max_hp,
        max_essence=view.max_essence,
        action_points=view.action_points,
        power_cap=view.power_cap,
        band=view.band,
        band_label=view.band_label,
        band_effect=view.band_effect,
        band_action_loss=view.band_action_loss,
        unlocked_powers=view.unlocked_powers,
        next_star=Requirement.model_validate(view.next_star) if view.next_star else None,
        ascension=Ascension.model_validate(view.ascension) if view.ascension else None,
        cover=view.cover,
        card=SonCard(
            last_action=card.last_action,
            last_action_epoch=card.last_action_epoch,
            last_words=card.last_words,
            reputation=card.reputation,
            best_friend=kin(card.best_friend),
            worst_rival=kin(card.worst_rival),
        ),
    )


HIDDEN_BOND_KINDS = (BondKind.INSIDE,)


def touching(node_id: int, active_only: bool) -> ColumnElement[bool]:
    states = [BondState.ACTIVE] if active_only else list(VISIBLE_BOND_STATES)
    return and_(
        or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id),
        BondRow.kind.not_in(HIDDEN_BOND_KINDS),
        BondRow.state.in_(states),
    )


async def bond_count(session: AsyncSession, node_id: int, active_only: bool) -> int:
    statement = select(func.count()).select_from(BondRow).where(touching(node_id, active_only))
    return int(await session.scalar(statement) or 0) + len(await derived_bonds(session, node_id))


def derived_view(index: int, bond: DerivedBond, node_id: int, other: NodeRef | None) -> BondView:
    return BondView(
        id=-(index + 1),
        source_node_id=bond.source_node_id,
        target_node_id=bond.target_node_id,
        kind=bond.kind,
        description=bond.description,
        role=None,
        epoch=bond.epoch,
        state=BondState.ACTIVE,
        closed_epoch=None,
        closed_reason=None,
        war_id=None,
        debt_amount=None,
        debt_what=None,
        debt_due_epoch=None,
        debt_status=None,
        outgoing=bond.source_node_id == node_id,
        other=other,
        derived=True,
    )


async def bond_views(session: AsyncSession, node_id: int, *, offset: int, limit: int, active_only: bool = False) -> list[BondView]:
    statement = select(BondRow).where(touching(node_id, active_only))
    ordered = statement.order_by((BondRow.source_node_id != node_id), (BondRow.state != BondState.ACTIVE), BondRow.id.desc())
    bonds = list(await session.scalars(ordered.offset(offset).limit(limit)))
    others = [bond.target_node_id if bond.source_node_id == node_id else bond.source_node_id for bond in bonds]
    derived = await derived_bonds(session, node_id) if offset == 0 else []
    derived_others = [bond.target_node_id if bond.source_node_id == node_id else bond.source_node_id for bond in derived]
    refs = await node_refs(session, [*others, *derived_others])
    return [
        BondView(
            **BondRecord.model_validate(bond).model_dump(),
            outgoing=bond.source_node_id == node_id,
            other=refs.get(other),
        )
        for bond, other in zip(bonds, others, strict=True)
    ] + [derived_view(index, bond, node_id, refs.get(other)) for index, (bond, other) in enumerate(zip(derived, derived_others, strict=True))]


async def chronicle_lines(session: AsyncSession, rows: Sequence[ChronicleRow]) -> list[ChronicleLineRecord]:
    ids = [row.id for row in rows]
    linked: dict[int, list[int]] = {}
    if ids:
        links = await session.execute(
            select(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.entity_id)
            .where(ChronicleEntityRow.chronicle_id.in_(ids))
            .order_by(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.position)
        )
        for chronicle_id, entity_id in links:
            linked.setdefault(chronicle_id, []).append(entity_id)
    return [
        ChronicleLineRecord(**ChronicleLineRecord.model_validate(row).model_dump(exclude={"entity_ids"}), entity_ids=linked.get(row.id, [])) for row in rows
    ]


async def mentioning(session: AsyncSession, entity_id: int, *, offset: int, limit: int) -> tuple[list[ChronicleLineRecord], int]:
    base = (
        select(ChronicleRow)
        .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id)
        .where(ChronicleEntityRow.entity_id == entity_id, shown_lines())
    )
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = list(await session.scalars(base.order_by(ChronicleRow.id.desc()).offset(offset).limit(limit)))
    return await chronicle_lines(session, list(reversed(rows))), total


async def images_of(session: AsyncSession, node_id: int) -> list[ImageRecord]:
    rows = await session.scalars(select(ImageRow).where(ImageRow.target_node_id == node_id).order_by(ImageRow.is_cover.desc(), ImageRow.id.desc()))
    return [ImageRecord.model_validate(row) for row in rows]


async def foreign_god_record(session: AsyncSession, row: ForeignGodRow) -> ForeignGodRecord:
    return ForeignGodRecord.model_validate(row).model_copy(update={"cover": await cover_of(session, row.id)})


async def foreign_god_records(session: AsyncSession) -> list[ForeignGodRecord]:
    rows = await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))
    return [await foreign_god_record(session, row) for row in rows]


async def route_records(session: AsyncSession, rules: Rules, routes: Sequence[RouteRow]) -> list[RouteRecord]:
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    book = RouteBook(routes, await current_calendar(session, rules, epoch), await forgotten_world_ids(session))
    ladder = await cosmography_of(session)
    records = []
    for route in routes:
        status = book.status(route)
        state = RouteStatusRecord(
            open=status.is_open, state=status.state, reason=status.reason, opens_epoch=status.opens_epoch, closes_epoch=status.closes_epoch
        )
        scope = ladder.scope_by_id(route.world_a_id, route.world_b_id)
        medium, mechanism = TRAVEL_MODEL[route.method]
        fields = {key: getattr(route, key) for key in ROUTE_FIELDS}
        records.append(RouteRecord.model_validate({**fields, "status": state, "scope": scope, "medium": medium, "mechanism": mechanism}))
    return records


ROUTE_FIELDS = tuple(name for name in RouteRecord.model_fields if name not in ("status", "scope", "medium", "mechanism"))
