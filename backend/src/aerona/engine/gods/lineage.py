from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import community_of
from aerona.engine.gods.stats import Trait, add_trait, trait
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.recording.record import record

CURSED_TRAITS = (
    Trait.PROSPERITY,
    Trait.FERTILITY,
    Trait.STRENGTH,
    Trait.DEFENSE,
    Trait.WEALTH,
    Trait.ABUNDANCE,
    Trait.INFLUENCE,
    Trait.SWAY,
    Trait.CHARISMA,
)


async def descendants(session: AsyncSession, root: EntityRow, depth: int) -> list[EntityRow]:
    found: dict[int, EntityRow] = {root.id: root}
    frontier = [root.id]
    for _ in range(depth):
        if not frontier:
            break
        statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.target_node_id.in_(frontier))
        children = [child for child in dict.fromkeys(await session.scalars(statement.order_by(BondRow.id))) if child not in found]
        frontier = []
        for child_id in children:
            child = await session.get(EntityRow, child_id)
            if child is not None:
                found[child_id] = child
                frontier.append(child_id)
    return list(found.values())


async def ancestors(session: AsyncSession, root: EntityRow, depth: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    seen = {root.id}
    frontier = [root.id]
    for _ in range(depth):
        statement = select(BondRow.target_node_id).where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(frontier))
        parents = [parent for parent in dict.fromkeys(await session.scalars(statement.order_by(BondRow.id))) if parent not in seen]
        frontier = []
        for parent_id in parents:
            parent = await session.get(EntityRow, parent_id)
            if parent is not None:
                seen.add(parent_id)
                found.append(parent)
                frontier.append(parent_id)
        if not frontier:
            break
    return found


async def bloodline(ctx: TickContext, root: EntityRow, depth: int | None = None) -> list[EntityRow]:
    return await descendants(ctx.session, root, ctx.rules.god_power.bloodline_curse_depth if depth is None else depth)


async def curse(ctx: TickContext, entity: EntityRow) -> None:
    for key in CURSED_TRAITS:
        add_trait(entity, key, -ctx.rules.god_power.bloodline_curse_stat_loss)
    entities = EntityRepository(ctx.session)
    await entities.add_flag(entity.id, EntityFlag.CURSED, ctx.epoch)
    await entities.add_flag(entity.id, EntityFlag.BLOODLINE_CURSE, ctx.epoch)


async def curse_bloodline(ctx: TickContext, creator: CreatorRow, root: EntityRow, reason: str | None = None) -> list[EntityRow]:
    members = [member for member in await bloodline(ctx, root) if member.status is EntityStatus.CANON]
    for member in members:
        await curse(ctx, member)
    await record(
        ctx,
        "gods.power.bloodline_curse",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.SUBJECT: [root.id, *[member.id for member in members]]},
        facts={"reason": str(f" ({reason})" if reason else ""), "count": len(members)},
        kind=ChronicleKind.DIVINE_SIGN if reason else ChronicleKind.CREATOR_HAND,
    )
    ctx.count("bloodline_curses")
    return members


async def cursed_members(ctx: TickContext, root: EntityRow) -> list[EntityRow]:
    entities = EntityRepository(ctx.session)
    return [member for member in await bloodline(ctx, root) if await entities.has_flag(member.id, EntityFlag.BLOODLINE_CURSE)]


async def lift_bloodline_curse(ctx: TickContext, creator: CreatorRow, root: EntityRow, members: list[EntityRow]) -> int:
    entities = EntityRepository(ctx.session)
    for member in members:
        await entities.remove_flag(member.id, EntityFlag.BLOODLINE_CURSE)
        await entities.remove_flag(member.id, EntityFlag.CURSED)
    await record(
        ctx,
        "gods.power.bloodline_lift",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.SUBJECT: root.id},
        facts={"count": len(members)},
        kind=ChronicleKind.CREATOR_HAND,
    )
    return len(members)


async def make_prophet(ctx: TickContext, creator: CreatorRow, mortal: EntityRow, spontaneous: bool = False) -> EntityRow | None:
    rules = ctx.rules.god_power
    add_trait(mortal, Trait.CHARISMA, rules.prophet_charisma)
    await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.PROPHET, ctx.epoch)
    await worship_creator(ctx.session, mortal, ctx.epoch, god_lines.PROPHET_VOW)
    community = await community_of(ctx.session, mortal)
    if community is not None and trait(community, Trait.PIETY) is not None:
        add_trait(community, Trait.PIETY, rules.prophet_piety)
    clause = god_lines.PROPHET_LISTENS.format(community=community.name) if community is not None else ""
    await record(
        ctx,
        "gods.power.prophet",
        roles={
            IncidentRole.ACTOR: creator.id,
            IncidentRole.TARGET: mortal.id,
            IncidentRole.SUBJECT: [*[mortal.id] + ([community.id] if community is not None else [])],
        },
        facts={"content": str(god_lines.PROPHET_CONTENT if spontaneous else ""), "community": str(clause)},
        kind=ChronicleKind.DIVINE_SIGN if spontaneous else ChronicleKind.CREATOR_HAND,
    )
    ctx.count("prophets")
    return community
