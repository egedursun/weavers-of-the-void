from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.military import FeudParty, FeudStatus
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.community_relations import open_feud

PEACE_TENETS = frozenset({TenetKind.PACIFISM})
LIVE = (FeudStatus.ACTIVE,)


async def active_feuds(session: AsyncSession) -> list[FeudRow]:
    return list(await session.scalars(select(FeudRow).where(FeudRow.status.in_(LIVE)).order_by(FeudRow.id)))


async def house_of(session: AsyncSession, mortal_id: int) -> int | None:
    found: int | None = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))
    return found


async def house_feud(ctx: TickContext, killer_id: int, victim_id: int, reason: str) -> FeudRow | None:
    killer_house, victim_house = await house_of(ctx.session, killer_id), await house_of(ctx.session, victim_id)
    if killer_house is None or victim_house is None or killer_house == victim_house:
        return None
    return await open_feud(ctx.session, ctx.rules, victim_house, killer_house, epoch=ctx.epoch, cause=reason, party=FeudParty.HOUSE)


async def members(session: AsyncSession, entity: EntityRow) -> set[int]:
    if entity.entity_type is EntityType.HOUSE:
        return set(await session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == entity.id)))
    return set(await session.scalars(select(EntityRow.id).where(await folk_of(session, entity), EntityRow.entity_type == EntityType.MORTAL)))


async def intermarried(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    left, right = await members(session, first), await members(session, second)
    if not left or not right:
        return False
    statement = select(BondRow.id).where(
        BondRow.kind == BondKind.LOVES,
        BondRow.state == BondState.ACTIVE,
        or_(
            BondRow.source_node_id.in_(left) & BondRow.target_node_id.in_(right),
            BondRow.source_node_id.in_(right) & BondRow.target_node_id.in_(left),
        ),
    )
    return await session.scalar(statement.limit(1)) is not None


async def foes(session: AsyncSession, entity_id: int) -> set[int]:
    mine = select(WarSideRow.war_id, WarSideRow.side).where(WarSideRow.entity_id == entity_id, WarSideRow.left_epoch.is_(None)).subquery()
    statement = (
        select(WarSideRow.entity_id).join(mine, mine.c.war_id == WarSideRow.war_id).where(WarSideRow.side != mine.c.side, WarSideRow.left_epoch.is_(None))
    )
    return set(await session.scalars(statement))


async def common_enemy(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    shared = await foes(session, first.id) & await foes(session, second.id)
    return bool(shared - {first.id, second.id})


async def realm_party(session: AsyncSession, entity: EntityRow) -> int:
    if entity.entity_type is not EntityType.HOUSE:
        return entity.id
    profile = await session.get(HouseProfileRow, entity.id)
    return profile.polity_entity_id if profile is not None and profile.polity_entity_id is not None else entity.id


async def peace_mediator(ctx: TickContext, first: EntityRow, second: EntityRow) -> bool:
    for party in (first, second):
        tenets = await faith_tenets(ctx.session, await realm_party(ctx.session, party))
        if tenets & PEACE_TENETS:
            return True
    return False


async def temper(ctx: TickContext, row: FeudRow, first: EntityRow, second: EntityRow, grief: int) -> int:
    table = ctx.rules.vendetta
    honour = max(
        (await values_for(ctx.session, await realm_party(ctx.session, first))).get(ValueAxis.HONOUR, 0),
        (await values_for(ctx.session, await realm_party(ctx.session, second))).get(ValueAxis.HONOUR, 0),
    )
    if "grievance" not in row.locked:
        row.grievance = clamp_int(max(grief, row.grievance - table.fade_per_epoch), 0, PERCENT)
    target = row.grievance * (1 + max(0, honour) / PERCENT * table.honour_pct / PERCENT)
    if await intermarried(ctx.session, first, second):
        target *= 1 - table.marriage_brake_pct / PERCENT
    if await common_enemy(ctx.session, first, second):
        target *= 1 - table.common_enemy_brake_pct / PERCENT
    if "intensity" not in row.locked:
        row.intensity = clamp_int(round_half_up(min(target, row.intensity + table.grievance // 4)) - table.fade_per_epoch, 0, PERCENT)
    epochs = max(1, table.generation_epochs)
    if (ctx.epoch - row.since_epoch) and (ctx.epoch - row.since_epoch) % epochs == 0 and "generations" not in row.locked:
        row.generations += 1
        if "intensity" not in row.locked:
            row.intensity = clamp_int(row.intensity - table.generation_fade, 0, PERCENT)
    if row.intensity <= table.fade_floor and "status" not in row.locked:
        row.status = FeudStatus.FADED
        row.ended_epoch = ctx.epoch
    return row.intensity


async def sides_of(ctx: TickContext, row: FeudRow) -> tuple[EntityRow, EntityRow] | None:
    first, second = await living_entity(ctx.session, row.first_entity_id), await living_entity(ctx.session, row.second_entity_id)
    if first is None or second is None:
        return None
    return first, second


async def head_of(ctx: TickContext, party: EntityRow) -> EntityRow | None:
    if party.entity_type is not EntityType.HOUSE:
        return None
    profile = await ctx.session.get(HouseProfileRow, party.id)
    return await living_entity(ctx.session, profile.head_entity_id) if profile is not None else None
