from collections import defaultdict

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Executable

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.made import (
    AugmentRow,
    DataStoreRow,
    IntrusionRow,
    MadeRealmRow,
    PeopleSubstrateRow,
    ReplicatorPresenceRow,
)
from aerona.db.tables.minds import MindProfileRow, MindStateRow, RemoteBodyRow
from aerona.db.tables.networks import NetworkGatewayRow, NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.made import AugmentSlot
from aerona.domain.enums.minds import MindOrigin, MindSeat
from aerona.engine.primitives.numbers import apportion

TIME_RATIO_MIN = 1


async def run(session: AsyncSession, statements: list[Executable]) -> int:
    mended = 0
    for statement in statements:
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended


async def balance_substrates(session: AsyncSession) -> int:
    by_people: dict[int, list[PeopleSubstrateRow]] = defaultdict(list)
    for row in await session.scalars(select(PeopleSubstrateRow).order_by(PeopleSubstrateRow.people_entity_id, PeopleSubstrateRow.seat)):
        by_people[row.people_entity_id].append(row)
    mended = 0
    for rows in by_people.values():
        total = sum(row.share_pct for row in rows)
        if total in {0, PERCENT}:
            continue
        shares = apportion(PERCENT, {row.seat.value: row.share_pct for row in rows})
        for row in rows:
            row.share_pct = shares.get(row.seat.value, 0)
        mended += 1
    return mended


async def trim_shares(session: AsyncSession) -> int:
    mended = 0
    totals = await session.execute(select(CompanyShareRow.company_entity_id, func.sum(CompanyShareRow.share)).group_by(CompanyShareRow.company_entity_id))
    for company, total in totals.all():
        if int(total or 0) <= PERCENT:
            continue
        rows = list(await session.scalars(select(CompanyShareRow).where(CompanyShareRow.company_entity_id == company).order_by(CompanyShareRow.holder_node_id)))
        shares = apportion(PERCENT, {str(row.holder_node_id): row.share for row in rows})
        for row in rows:
            row.share = shares.get(str(row.holder_node_id), 0)
        mended += 1
    return mended


async def cap_copies(session: AsyncSession) -> int:
    mended = 0
    copies = await session.execute(
        select(MindProfileRow, BondRow.target_node_id).join(BondRow, BondRow.source_node_id == MindProfileRow.node_id).where(BondRow.kind == BondKind.COPY_OF)
    )
    for copy, source_id in copies.all():
        source = await session.get(MindProfileRow, source_id)
        if source is not None and copy.fidelity_pct > source.fidelity_pct:
            copy.fidelity_pct = source.fidelity_pct
            mended += 1
    return mended


async def drop_empty_profiles(session: AsyncSession) -> int:
    empty = select(MindProfileRow).where(
        MindProfileRow.seat == MindSeat.NONE,
        MindProfileRow.will == MindWill.NONE,
        MindProfileRow.origin == MindOrigin.BORN,
        MindProfileRow.made_by_node_id.is_(None),
        MindProfileRow.dormant.is_(False),
    )
    dropped = 0
    for row in list(await session.scalars(empty)):
        if row.locked:
            continue
        await session.delete(row)
        dropped += 1
    return dropped


async def mend_minds_links(session: AsyncSession) -> int:
    nodes = select(NodeRow.id)
    networks = select(NetworkProfileRow.network_entity_id)
    bearers = select(EntityRow.id)
    return (
        await run(
            session,
            [
                update(MindProfileRow)
                .where(MindProfileRow.seat_node_id.is_not(None), MindProfileRow.seat_node_id.not_in(nodes))
                .values(seat=MindSeat.NONE, seat_node_id=None),
                update(MindStateRow).where(MindStateRow.fidelity_pct > 100).values(fidelity_pct=100),
                delete(MindStateRow).where(MindStateRow.holder_node_id.is_(None), MindStateRow.owner_node_id.is_(None)),
                delete(RemoteBodyRow).where(RemoteBodyRow.mind_node_id.not_in(nodes)),
                delete(NetworkNodeRow).where(or_(NetworkNodeRow.member_node_id.not_in(nodes), NetworkNodeRow.network_entity_id.not_in(networks))),
                delete(NetworkGatewayRow).where(
                    or_(
                        NetworkGatewayRow.first_network_id == NetworkGatewayRow.second_network_id,
                        NetworkGatewayRow.first_network_id.not_in(networks),
                        NetworkGatewayRow.second_network_id.not_in(networks),
                    )
                ),
                update(NetworkProfileRow).where(NetworkProfileRow.delay_days < 0).values(delay_days=0),
                update(AugmentRow).where(AugmentRow.slot == AugmentSlot.PART, AugmentRow.part.is_(None)).values(slot=AugmentSlot.WHOLE_BODY),
                delete(AugmentRow).where(AugmentRow.bearer_node_id.not_in(bearers)),
                update(IntrusionRow).where(IntrusionRow.target_node_id.is_not(None), IntrusionRow.target_node_id.not_in(nodes)).values(target_node_id=None),
                update(DataStoreRow).where(DataStoreRow.owner_node_id.is_not(None), DataStoreRow.owner_node_id.not_in(nodes)).values(owner_node_id=None),
                update(ReplicatorPresenceRow).where(ReplicatorPresenceRow.mass < 0).values(mass=0),
                update(MadeRealmRow).where(MadeRealmRow.host_node_id.is_not(None), MadeRealmRow.host_node_id.not_in(nodes)).values(host_node_id=None),
                update(MadeRealmRow).where(MadeRealmRow.time_ratio_pct < TIME_RATIO_MIN).values(time_ratio_pct=TIME_RATIO_MIN),
            ],
        )
        + await balance_substrates(session)
        + await trim_shares(session)
        + await cap_copies(session)
        + await drop_empty_profiles(session)
    )
