from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.queries import add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import stat

LEFT_BEHIND_TYPES = frozenset({EntityType.STRUCTURE, EntityType.ITEM})


async def abandon(ctx: TickContext, settlement: EntityRow) -> EntityRow:
    await retire(ctx.session, settlement, ctx.epoch, f"Epoch {ctx.epoch}: abandoned, turned into a ruin.", append=True, close_bonds=True)
    await add_flag(ctx.session, settlement.id, EntityFlag.RUIN, ctx.epoch)
    remains = [item for item in await EntityRepository(ctx.session).contents(settlement.id) if item.entity_type in LEFT_BEHIND_TYPES]
    left = f" Left behind: {', '.join(item.name for item in remains)}." if remains else ""
    await note(ctx, f"{settlement.name} was abandoned and fell to ruin.{left}", key="ruins.abandoned", ids=[settlement.id, *(item.id for item in remains)])
    ctx.count("abandoned")
    return settlement


@reads("settlement.population", "table.bonds", "table.entity_flags", "table.epoch_year_cursors", "table.routes")
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def abandonment(ctx: TickContext) -> None:
    world_rules = ctx.rules.deep_world
    sheltered = await flags_by_entity(ctx.session, EntityFlag.PROTECTED_FROM_RUIN)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
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
        text = f"{settlement.name} was sheltered: however empty it grows, it will not fall to ruin."
    else:
        changed = await remove_flag(ctx.session, settlement.id, EntityFlag.PROTECTED_FROM_RUIN)
        text = f"{settlement.name} lost its shelter against ruin."
    if changed:
        await note(ctx, text, key="ruins.sheltered" if protected else "ruins.unsheltered", ids=[settlement.id])
    return changed


async def abandon_settlement(ctx: TickContext, settlement_id: int) -> EntityRow:
    settlement = await living_entity(ctx.session, settlement_id)
    if settlement is None or settlement.entity_type is not EntityType.SETTLEMENT or settlement.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living settlement can be abandoned.")
    return await abandon(ctx, settlement)


PHASES = (Phase("ruins", abandonment),)
