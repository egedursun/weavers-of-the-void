from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

FAULT_LAYERS = (IdentityLayer.PEOPLE, IdentityLayer.FAITH, IdentityLayer.LOCALITY)
GROUP_LAYERS = frozenset({IdentityLayer.HOUSE, IdentityLayer.PROFESSION, IdentityLayer.CIRCLE, IdentityLayer.LOCALITY})


@memoized(HeldIdentityRow)
async def identities_of(session: AsyncSession, holder_id: int) -> dict[IdentityLayer, HeldIdentityRow]:
    return {row.layer: row for row in await session.scalars(select(HeldIdentityRow).where(HeldIdentityRow.holder_entity_id == holder_id))}


def same_value(first: HeldIdentityRow, second: HeldIdentityRow) -> bool:
    if first.value_node_id is not None:
        return first.value_node_id == second.value_node_id
    return first.value_label is not None and first.value_label == second.value_label


def shared_weight(mine: dict[IdentityLayer, HeldIdentityRow], theirs: dict[IdentityLayer, HeldIdentityRow]) -> float:
    total = 0.0
    for layer, row in mine.items():
        other = theirs.get(layer)
        if other is not None and same_value(row, other):
            total += row.salience / PERCENT * row.strength / PERCENT
    return min(1.0, total)


async def shared_identity(session: AsyncSession, rules: Rules, holder_id: int, subject_id: int) -> int:
    mine = await identities_of(session, holder_id)
    if not mine:
        return 0
    return round_half_up(shared_weight(mine, await identities_of(session, subject_id)) * rules.identities.in_group_opinion)


def salience_of(rows: dict[IdentityLayer, HeldIdentityRow], layer: IdentityLayer) -> int:
    row = rows.get(layer)
    return row.salience if row is not None else 0


def fault_layer(rules: Rules, members: list[dict[IdentityLayer, HeldIdentityRow]]) -> IdentityLayer | None:
    if not members:
        return None
    means = {layer: sum(salience_of(rows, layer) for rows in members) / len(members) for layer in FAULT_LAYERS}
    _rank, layer = max(enumerate(FAULT_LAYERS), key=lambda pair: (means[pair[1]], -pair[0]))
    return layer if means[layer] >= rules.identities.fault_at else None


async def realm_fault(session: AsyncSession, rules: Rules, member_ids: list[int]) -> IdentityLayer | None:
    return fault_layer(rules, [await identities_of(session, member) for member in member_ids])


async def identity_loyalty(
    session: AsyncSession, rules: Rules, realm_id: int, member_id: int, *, ruler_id: int | None, fault: IdentityLayer | None
) -> tuple[int, int]:
    mine = await identities_of(session, member_id)
    table = rules.identities
    polity = mine.get(IdentityLayer.POLITY)
    cohesion = round_half_up(table.cohesion * polity.salience / PERCENT) if polity is not None and polity.value_node_id == realm_id else 0
    if fault is None or ruler_id is None or fault not in mine:
        return cohesion, 0
    ruler = (await identities_of(session, ruler_id)).get(fault)
    differs = ruler is not None and (ruler.value_node_id is not None or ruler.value_label is not None) and not same_value(mine[fault], ruler)
    return cohesion, round_half_up(table.separatism * mine[fault].salience / PERCENT) if differs else 0


async def apart_from_ruler(session: AsyncSession, rules: Rules, town_id: int) -> int:
    realm = await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    if realm is None:
        return 0
    members = sorted(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm)))
    fault = await realm_fault(session, rules, members)
    ruler = await session.scalar(select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.RULER).limit(1))
    _, separatism = await identity_loyalty(session, rules, int(realm), town_id, ruler_id=ruler, fault=fault)
    return round_half_up(separatism * PERCENT / max(1, rules.identities.separatism))


async def identity_levy(session: AsyncSession, rules: Rules, community_id: int) -> float:
    row = await session.get(HeldIdentityRow, (community_id, IdentityLayer.POLITY))
    if row is None or row.value_node_id is None:
        return 1.0
    return max(0.1, 1 + (row.salience - rules.identities.base_salience) / PERCENT * rules.identities.mobilisation_pct / PERCENT)


def approach(current: int, target: int, pct: int) -> int:
    return clamp_int(current + round_half_up((target - current) * pct / PERCENT), 0, PERCENT)
