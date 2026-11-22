from sqlalchemy import select

from aerona.catalog.life.made import CARRIERS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindLawRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.minds import MadeMindsLaw, MindAffect, MindOrigin, MindPurpose, MindSeat, MindUpkeep
from aerona.domain.enums.networks import NetworkCarrier
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import polities, realm_towns
from aerona.engine.minds.profiles import profile_of
from aerona.engine.minds.souls import default_law
from aerona.engine.networks.backfill import relay


async def law_for(ctx: TickContext, world_id: int, prevalence: int) -> MindLawRow:
    row = await ctx.session.get(MindLawRow, world_id)
    if row is None:
        row = default_law(world_id)
        ctx.session.add(row)
    row.made_minds = MadeMindsLaw.NO_WILL if prevalence == 0 else MadeMindsLaw.WILL_MAY_EMERGE
    return row


async def made_minds(ctx: TickContext, world_id: int, prevalence: int) -> int:
    law = await law_for(ctx, world_id, prevalence)
    will = MindWill.NONE if law.made_minds is MadeMindsLaw.NO_WILL else MindWill.INSTRUCTED
    statement = (
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    seated = 0
    for works in list(await ctx.session.scalars(statement)):
        if held(works.id) or not ctx.rng(f"genesis.made_mind.{works.id}").chance(prevalence):
            continue
        mind = await profile_of(ctx.session, ctx.rules, works.id, ctx.epoch)
        if mind.seat is not MindSeat.NONE:
            continue
        mind.seat, mind.seat_node_id, mind.origin, mind.will = MindSeat.STRUCTURE, works.id, MindOrigin.MADE, will
        mind.affect, mind.purpose, mind.upkeep = MindAffect.MODELLED, MindPurpose.STEWARD, MindUpkeep.MAINTENANCE
        seated += 1
    return seated


async def networks(ctx: TickContext, world_id: int, reach: int, technology: TechnologyEra) -> int:
    founded = 0
    carrier = CARRIERS.get(technology, NetworkCarrier.RELAY)
    for polity, _ in await polities(ctx.session):
        towns = [town for town in await realm_towns(ctx.session, polity.id) if town.world_id == world_id]
        if towns and await relay(ctx, polity, [town.id for town in towns], f"the network of {polity.name}", carrier=carrier, capacity=reach):
            founded += 1
    return founded


async def seed_made_world(ctx: TickContext, world_ids: list[int], *, prevalence: int | None, reach: int | None, technology: TechnologyEra) -> int:
    done = 0
    for world_id in world_ids:
        if prevalence is not None:
            done += await made_minds(ctx, world_id, prevalence)
        if reach:
            done += await networks(ctx, world_id, reach, technology)
    await ctx.session.flush()
    return done
