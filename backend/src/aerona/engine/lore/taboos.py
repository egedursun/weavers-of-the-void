from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.engine.context import TickContext
from aerona.engine.cycles.hospitality import circuit_partners
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note

PERCENT = 100


async def home_of(session: AsyncSession, entity_id: int | None) -> int | None:
    if entity_id is None:
        return None
    entity = await session.get(EntityRow, entity_id)
    if entity is None:
        return None
    return entity.location_id if entity.entity_type is EntityType.MORTAL else entity.id


async def kept(session: AsyncSession, community_id: int | None, kind: TraditionFunction, act: ActKind | None = None) -> list[int]:
    if community_id is None:
        return []
    keeping = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    statement = select(TraditionProfileRow.tradition_entity_id).where(TraditionProfileRow.tradition_entity_id.in_(keeping), TraditionProfileRow.kind == kind)
    if act is not None:
        statement = statement.where(TraditionProfileRow.taboo_act == act)
    living = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    return list(await session.scalars(statement.where(TraditionProfileRow.tradition_entity_id.in_(living)).order_by(TraditionProfileRow.tradition_entity_id)))


async def strength_of(session: AsyncSession, tradition_id: int, community_id: int) -> int:
    row = await session.get(TraditionParticipationRow, (tradition_id, community_id))
    return row.participation if row is not None else PERCENT // 2


async def forbidden(ctx: TickContext, actor_id: int | None, act: ActKind) -> bool:
    home = await home_of(ctx.session, actor_id)
    for tradition_id in await kept(ctx.session, home, TraditionFunction.TABOO, act):
        held = await strength_of(ctx.session, tradition_id, home or 0)
        if ctx.rng(f"taboo.{tradition_id}.{actor_id}.{act.value}.{ctx.epoch}").chance(held):
            ctx.count(f"taboo_obeyed_{act.value}")
            return True
    return False


async def keepers_of(session: AsyncSession, tradition_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(
        BondRow.target_node_id == tradition_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    return sorted(set(await session.scalars(statement)))


async def shame(ctx: TickContext, actor_id: int, keepers: list[int], magnitude: int, note: str) -> int:
    shamed = 0
    for keeper in keepers:
        if keeper == actor_id:
            continue
        await remember(
            ctx.session, ctx.rules, holder_id=keeper, subject_id=actor_id, kind=MemoryKind.ILL_WILL, magnitude=-magnitude, epoch=ctx.epoch, note=note
        )
        shamed += 1
    actor = await ctx.session.get(EntityRow, actor_id)
    if actor is not None and actor.entity_type is EntityType.MORTAL:
        actor.importance = max(0, (actor.importance or 0) - ctx.rules.traditions.taboo_importance)
    return shamed


async def violated(ctx: TickContext, actor_id: int, act: ActKind) -> int:
    home = await home_of(ctx.session, actor_id)
    shamed = 0
    actor = await ctx.session.get(EntityRow, actor_id)
    for tradition_id in await kept(ctx.session, home, TraditionFunction.TABOO, act):
        keepers = await keepers_of(ctx.session, tradition_id)
        label = act.value.replace("_", " ")
        found = await shame(ctx, actor_id, keepers, ctx.rules.traditions.taboo_infamy, f"broke the taboo on {label}")
        shamed += found
        if found and actor is not None:
            tradition = await ctx.session.get(EntityRow, tradition_id)
            await note(
                ctx,
                f"{actor.name} broke the taboo of {tradition.name if tradition else 'the keepers'} against {label}, and the keepers named it infamy.",
                key="lore.taboo_broken",
                ids=[actor_id, *[keeper for keeper in keepers if keeper != actor_id]],
            )
    if shamed:
        ctx.count(f"taboo_broken_{act.value}")
    return shamed


async def homes_of_guest(session: AsyncSession, victim: EntityRow) -> set[int]:
    return set(
        await session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == victim.id, BondRow.kind == BondKind.LIVES_IN, BondRow.state == BondState.ACTIVE)
        )
    )


async def guest_of(session: AsyncSession, victim: EntityRow) -> bool:
    if victim.entity_type is not EntityType.MORTAL or victim.location_id is None:
        return False
    homes = await homes_of_guest(session, victim)
    travelling = await session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == victim.id, BondRow.kind == BondKind.PASSENGER_OF, BondRow.state == BondState.ACTIVE).limit(1)
    )
    return travelling is not None or bool(homes - {victim.location_id})


async def guest_killed(ctx: TickContext, killer_id: int | None, victim: EntityRow) -> int:
    if killer_id is None or killer_id == victim.id or not await guest_of(ctx.session, victim):
        return 0
    host = victim.location_id
    laws = await kept(ctx.session, host, TraditionFunction.HOSPITALITY)
    if not laws:
        return await circuit_guest_killed(ctx, killer_id, victim)
    keepers = sorted({keeper for law in laws for keeper in await keepers_of(ctx.session, law)} | ({host} if host is not None else set()))
    shamed = await shame(ctx, killer_id, keepers, ctx.rules.traditions.guest_killing_infamy, f"killed {victim.name}, a guest under the law of hospitality")
    killer = await ctx.session.get(EntityRow, killer_id)
    await note(
        ctx,
        f"{killer.name if killer else 'A host'} slew {victim.name}, a guest under the law of hospitality: a grave infamy that will not be forgotten.",
        key="lore.guest_killing",
        ids=[killer_id, victim.id, *keepers],
    )
    ctx.count("guests_killed")
    return shamed


async def circuit_guest_killed(ctx: TickContext, killer_id: int, victim: EntityRow) -> int:
    host = victim.location_id
    partners = await circuit_partners(ctx.session, host)
    if host is None or not partners & await homes_of_guest(ctx.session, victim):
        return 0
    keepers = sorted({host, *partners})
    shamed = await shame(ctx, killer_id, keepers, ctx.rules.traditions.guest_killing_infamy, f"killed {victim.name}, a guest under the duty of the circuit")
    killer = await ctx.session.get(EntityRow, killer_id)
    await note(
        ctx,
        f"{killer.name if killer else 'A host'} slew {victim.name}, a guest come along the ceremonial circuit: the stops of the circuit named it infamy.",
        key="circuits.guest_killing",
        ids=[killer_id, victim.id, *keepers],
    )
    ctx.count("guests_killed")
    return shamed


def dead_season(ctx: TickContext, growth: int | None) -> bool:
    return growth is not None and growth <= ctx.rules.traditions.dead_growth


async def winter_rest(ctx: TickContext, attacker_id: int, defender_id: int, *, shamed: bool) -> tuple[bool, bool]:
    if await forbidden(ctx, attacker_id, ActKind.WINTER_FIGHTING):
        return True, shamed
    if shamed:
        return False, shamed
    home = await home_of(ctx.session, defender_id)
    for tradition_id in await kept(ctx.session, home, TraditionFunction.TABOO, ActKind.WINTER_FIGHTING):
        await shame(ctx, attacker_id, await keepers_of(ctx.session, tradition_id), ctx.rules.traditions.taboo_infamy, "made war in the sacred winter")
        ctx.count("winter_war_infamy")
        shamed = True
    return False, shamed
