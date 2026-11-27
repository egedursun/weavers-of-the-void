from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.phase import Phase
from aerona.engine.primitives.queries import add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import record

LEFT_BEHIND_TYPES = frozenset({EntityType.STRUCTURE, EntityType.ITEM})


async def abandon(ctx: TickContext, settlement: EntityRow, *, tell: bool = True) -> EntityRow:
    await retire(ctx.session, settlement, ctx.epoch, f"Epoch {ctx.epoch}: abandoned, turned into a ruin.", append=True, close_bonds=True)
    await add_flag(ctx.session, settlement.id, EntityFlag.RUIN, ctx.epoch)
    remains = [item for item in await EntityRepository(ctx.session).contents(settlement.id) if item.entity_type in LEFT_BEHIND_TYPES]
    left = stat_or(settlement, "population", 0)
    with flowing(FlowCategory.TRANSFORMATION):
        set_stats(settlement, population=0)
    if not tell:
        ctx.count("abandoned")
        return settlement
    await record(
        ctx,
        "ruins.abandoned",
        roles={IncidentRole.SUBJECT: settlement.id, IncidentRole.PRODUCT: [item.id for item in remains]},
        facts={"population": left, "left_behind": len(remains)},
        place=settlement.id,
    )
    ctx.count("abandoned")
    return settlement


@reads("settlement.population", "table.bonds", "table.entities", "table.entity_flags", "table.node_births", "table.nodes", "table.routes")
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
)
async def abandonment(ctx: TickContext) -> None:
    world_rules = ctx.rules.deep_world
    sheltered = await flags_by_entity(ctx.session, EntityFlag.PROTECTED_FROM_RUIN)
    for settlement in unheld(await canon(ctx.session, [EntityType.SETTLEMENT])):
        if settlement.id in sheltered:
            ctx.count("sheltered")
            continue
        if (stat(settlement, "population") or 0) >= world_rules.ruin_population_threshold:
            continue
        if ctx.epoch - settlement.birth_epoch < world_rules.ruin_grace_epochs:
            continue
        await abandon(ctx, settlement)


async def protect_from_ruin(ctx: TickContext, settlement_id: int, protected: bool = True) -> bool:
    settlement = await living_entity(ctx.session, settlement_id)
    if settlement is None or settlement.entity_type is not EntityType.SETTLEMENT:
        raise ValidationFailedError("Only a living settlement can be sheltered from ruin.")
    if protected:
        changed = await add_flag(ctx.session, settlement.id, EntityFlag.PROTECTED_FROM_RUIN, ctx.epoch)
    else:
        changed = await remove_flag(ctx.session, settlement.id, EntityFlag.PROTECTED_FROM_RUIN)
    if changed:
        await record(ctx, "ruins.sheltered" if protected else "ruins.unsheltered", roles={IncidentRole.SUBJECT: settlement.id}, place=settlement.id)
    return changed


async def abandon_settlement(ctx: TickContext, settlement_id: int) -> EntityRow:
    settlement = await living_entity(ctx.session, settlement_id)
    if settlement is None or settlement.entity_type is not EntityType.SETTLEMENT or settlement.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living settlement can be abandoned.")
    return await abandon(ctx, settlement)


PHASES = (Phase("ruins", abandonment),)
