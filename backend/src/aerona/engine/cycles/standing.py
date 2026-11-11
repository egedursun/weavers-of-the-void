from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import HouseProfileRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import divine_of
from aerona.engine.mind.memories import remember
from aerona.engine.services.community_relations import change_relation


async def node_name(session: AsyncSession, node_id: int) -> str:
    entity = await session.get(EntityRow, node_id)
    if entity is not None:
        return entity.name
    god = await divine_of(session, node_id)
    return str(getattr(god, "name", "a god")) if god is not None else "someone"


async def name_of(ctx: TickContext, node_id: int) -> str:
    return await node_name(ctx.session, node_id)


async def raise_standing(ctx: TickContext, node_id: int, delta: float) -> None:
    if not delta or held(node_id):
        return
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None:
        return
    if entity.entity_type is EntityType.HOUSE and (house := await ctx.session.get(HouseProfileRow, node_id)) is not None:
        shift(house, "prestige", delta)
    elif entity.entity_type is EntityType.POLITY and (realm := await ctx.session.get(PolityProfileRow, node_id)) is not None:
        shift(realm, "legitimacy", delta)
    elif entity.entity_type is EntityType.SETTLEMENT and (town := await ctx.session.get(SettlementProfileRow, node_id)) is not None:
        shift(town, "prestige", delta)
    elif entity.entity_type is EntityType.MORTAL and (profile := await ctx.session.get(MortalProfileRow, node_id)) is not None:
        shift(profile, "renown", delta)
    elif (faction := await ctx.session.get(FactionProfileRow, node_id)) is not None:
        shift(faction, "reputation", delta)


async def regard(ctx: TickContext, pair: tuple[int, int], magnitude: float, kind: MemoryKind, text: str) -> None:
    holder_id, subject_id = pair
    holder = await ctx.session.get(EntityRow, holder_id)
    subject = await ctx.session.get(EntityRow, subject_id)
    if holder is None or subject is None or holder_id == subject_id:
        return
    if holder.entity_type is EntityType.MORTAL or subject.entity_type is EntityType.MORTAL:
        await remember(ctx.session, ctx.rules, holder_id=holder_id, subject_id=subject_id, kind=kind, magnitude=magnitude, epoch=ctx.epoch, note=text)
        return
    await change_relation(ctx, holder_id, subject_id, magnitude, kind, note=text)
