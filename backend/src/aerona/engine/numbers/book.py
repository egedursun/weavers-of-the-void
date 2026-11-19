from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.population import PopulationAim, PopulationInstrument
from aerona.engine.context import TickContext
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

AIM_DIRECTION: dict[PopulationAim, int] = {
    PopulationAim.GROW: 1,
    PopulationAim.SETTLE_LAND: 1,
    PopulationAim.SHRINK: -1,
    PopulationAim.EMPTY_LAND: -1,
    PopulationAim.HOLD: 0,
    PopulationAim.REBALANCE_AGE: 0,
    PopulationAim.REBALANCE_CLASS: 0,
    PopulationAim.KEEP_KIND: 0,
    PopulationAim.MIX_KINDS: 0,
    PopulationAim.NONE: 0,
}
LIMIT_MOST = 5
LIMIT_SPAN = 4
QUARTER = 4


def force(policy: PopulationPolicyRow, instrument: PopulationInstrumentRow) -> float:
    return instrument.strength * policy.enforcement / (PERCENT * PERCENT)


def birth_shift(rules: Rules, policy: PopulationPolicyRow, instrument: PopulationInstrumentRow) -> float:
    table = rules.population_policy
    weight = force(policy, instrument)
    if instrument.instrument is PopulationInstrument.BIRTH_REWARD:
        return table.birth_reward_pct * weight
    if instrument.instrument is PopulationInstrument.BIRTH_TAX:
        return -table.birth_tax_pct * weight
    if instrument.instrument is PopulationInstrument.CHILD_SUPPORT:
        return table.birth_reward_pct * weight / 2
    if instrument.instrument in {PopulationInstrument.UNION_LAW, PopulationInstrument.INHERITANCE_RULE}:
        return table.birth_reward_pct * weight / QUARTER
    if instrument.instrument is PopulationInstrument.FAITH_TEACHING:
        return table.birth_reward_pct * weight / 2 * (-1 if AIM_DIRECTION[policy.aim] < 0 else 1)
    return 0.0


async def towns_in(session: AsyncSession, node_id: int | None) -> list[int]:
    node = await session.get(EntityRow, node_id) if node_id is not None else None
    if node is None:
        return []
    if node.entity_type is EntityType.SETTLEMENT:
        return [node.id]
    if node.entity_type is EntityType.PEOPLE:
        return sorted(await towns_of_people(session, node.id))
    places: list[int] = [node.id]
    if node.entity_type is EntityType.POLITY:
        members = set(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == node.id)))
        members |= {bond.source_node_id for bond in await active_bonds(session, [BondKind.MEMBER_OF], targets=[node.id])}
        places = sorted(members)
    rows = await session.scalars(
        select(EntityRow.id).where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            (EntityRow.id.in_(places)) | (EntityRow.location_id.in_(places)),
        )
    )
    return sorted(set(rows))


async def scope_of(session: AsyncSession, policy: PopulationPolicyRow) -> list[int]:
    return await towns_in(session, policy.target_node_id if policy.target_node_id is not None else policy.holder_node_id)


async def instruments_of(session: AsyncSession, policy_id: int) -> list[PopulationInstrumentRow]:
    return list(
        await session.scalars(
            select(PopulationInstrumentRow).where(PopulationInstrumentRow.policy_id == policy_id).order_by(PopulationInstrumentRow.instrument)
        )
    )


@dataclass
class PolicyBook:
    births: dict[int, float] = field(default_factory=dict)
    limits: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, ctx: TickContext) -> "PolicyBook":
        book = cls()
        for policy in await ctx.session.scalars(select(PopulationPolicyRow).order_by(PopulationPolicyRow.id)):
            instruments = await instruments_of(ctx.session, policy.id)
            if not instruments:
                continue
            towns = await scope_of(ctx.session, policy)
            shift = sum(birth_shift(ctx.rules, policy, instrument) for instrument in instruments)
            limit = next((instrument for instrument in instruments if instrument.instrument is PopulationInstrument.CHILD_LIMIT), None)
            for town in towns:
                book.births[town] = book.births.get(town, 1.0) * max(0.0, 1 + shift / PERCENT)
                if limit is not None and force(policy, limit) > 0:
                    cap = max(1, round(LIMIT_MOST - LIMIT_SPAN * force(policy, limit)))
                    book.limits[town] = min(book.limits.get(town, cap), cap)
        return book

    def birth_factor(self, town_id: int | None) -> float:
        return self.births.get(town_id, 1.0) if town_id is not None else 1.0

    def child_limit(self, town_id: int | None) -> int | None:
        return self.limits.get(town_id) if town_id is not None else None
