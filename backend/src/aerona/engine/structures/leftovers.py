from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import ConstructionState
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, connect, remove_flag
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.recording.record import record
from aerona.engine.structures.spec import build_cost, resolve, scale_index

LEGEND_POWER = 10


async def dismantle(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, *, by: int | None) -> int:
    resolved = resolve(profile.kind)
    gained = round_half_up(build_cost(ctx.rules, resolved, profile.level) * ctx.rules.construction.dismantle_yield_pct / PERCENT)
    town = await ctx.session.get(SettlementProfileRow, profile.host_entity_id) if profile.host_entity_id is not None else None
    if town is not None and "investment_pool" not in town.locked:
        town.investment_pool += gained
    profile.construction_state = ConstructionState.DISMANTLED
    profile.effect_pct = 0
    await remove_flag(ctx.session, work.id, EntityFlag.RUIN)
    await record(
        ctx,
        "structure.dismantled",
        roles={IncidentRole.SUBJECT: work.id, IncidentRole.ACTOR: by, IncidentRole.BENEFICIARY: profile.host_entity_id},
        facts={"structure": profile.kind, "gained": gained},
        place=work.location_id,
    )
    await retire(ctx.session, work, ctx.epoch, f"Epoch {ctx.epoch}: taken apart.", append=True, close_bonds=False)
    return gained


async def gather_legend(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> bool:
    if await active_bonds(ctx.session, [BondKind.TELLS_OF], targets=[work.id]):
        return False
    resolved = resolve(profile.kind)
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"The Telling of {work.name}",
            body=f"What is told of {work.name}, a work left unfinished.",
            stats=LegendStats(spread=clamp_int(scale_index(resolved.scale) * 15 + 10, 0, PERCENT)),
            power=LEGEND_POWER,
            location_id=work.location_id,
            world_id=work.world_id,
            subtype="legend of an unfinished work",
        ),
    )
    await connect(ctx.session, legend.id, work.id, BondKind.TELLS_OF, ctx.epoch, description="tells of the unfinished work")
    await record(ctx, "structure.legend_gathered", roles={IncidentRole.SUBJECT: work.id, IncidentRole.PRODUCT: legend.id}, place=work.location_id)
    return True


async def keep_leftovers(ctx: TickContext) -> int:
    table = ctx.rules.construction
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, StructureProfileRow.construction_state == ConstructionState.ABANDONED)
        .order_by(EntityRow.id)
    )
    touched = 0
    for work, profile in list(rows):
        if held(work.id) or "construction_state" in profile.locked:
            continue
        roll = ctx.rng(f"leftover.{work.id}.{ctx.epoch}")
        host = await ctx.session.get(EntityRow, profile.host_entity_id) if profile.host_entity_id is not None else None
        if host is not None and host.status is EntityStatus.CANON and not held(host.id) and roll.chance(table.salvage_pct):
            await dismantle(ctx, work, profile, by=host.id)
            touched += 1
        elif roll.chance(table.abandoned_legend_pct):
            touched += int(await gather_legend(ctx, work, profile))
    return touched


async def abandon_work(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, *, by: int | None) -> None:
    profile.construction_state = ConstructionState.ABANDONED
    profile.effect_pct = 0
    await add_flag(ctx.session, work.id, EntityFlag.RUIN, ctx.epoch)
    await record(
        ctx,
        "structure.left_unfinished",
        roles={IncidentRole.SUBJECT: work.id, IncidentRole.ACTOR: by},
        facts={"structure": profile.kind},
        place=work.location_id,
    )
