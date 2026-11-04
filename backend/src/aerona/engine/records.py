from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import HarmCause, StrikeStyle
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import fatal_injury
from aerona.engine.lore.taboos import guest_killed
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.queries import connect, entity
from aerona.engine.primitives.records import SweepResult, retire, sweep_dead_bonds


async def death_path(
    ctx: TickContext,
    victim: EntityRow,
    cause: str,
    killer_id: int | None = None,
    bond_description: str | None = None,
    *,
    forced: bool = False,
    event_id: int | None = None,
    harm: HarmCause | None = None,
    style: StrikeStyle = StrikeStyle.NORMAL,
) -> bool:
    if victim.status is not EntityStatus.CANON:
        return False
    if victim.entity_type is EntityType.MORTAL:
        await guest_killed(ctx, killer_id, victim)
        if harm is not None:
            await fatal_injury(ctx, victim, Harm(ctx.rules.casualties.wound_hp, harm, cause, killer_id=killer_id, event_entity_id=event_id, style=style))
        return await die(ctx, victim, cause=cause, killer_id=killer_id, forced=forced, event_id=event_id) is not None
    await retire(ctx.session, victim, ctx.epoch, f"Epoch {ctx.epoch}: {cause}.", append=True, close_bonds=True)
    if killer_id is not None and killer_id != victim.id:
        await connect(ctx.session, killer_id, victim.id, BondKind.KILLED, ctx.epoch, description=bond_description or cause)
    return True


async def sweep_bonds_of_the_dead(ctx: TickContext) -> SweepResult:
    result = await sweep_dead_bonds(ctx.session, ctx.epoch)
    ctx.count("bonds_closed", result.closed)
    ctx.count("bonds_inherited", result.transferred)
    if result.transferred:
        await note(ctx, f"The dead's {result.transferred} properties and rulerships passed to their heirs.", key="records.inheritance")
    return result


async def retire_record(ctx: TickContext, entity_id: int, reason: str, status: EntityStatus = EntityStatus.DEAD) -> EntityRow:
    found = await entity(ctx.session, entity_id)
    if found is None or found.status is not EntityStatus.CANON:
        raise NotFoundError("No such living record.")
    if found.entity_type is EntityType.MORTAL and status is EntityStatus.DEAD:
        await die(ctx, found, cause=reason, forced=True)
        return found
    return await retire(ctx.session, found, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", status=status, close_bonds=True)


@reads("table.bonds", "table.routes")
@writes("table.bonds")
async def dead_bonds_before(ctx: TickContext) -> None:
    await sweep_bonds_of_the_dead(ctx)


@reads("table.bonds", "table.routes")
@writes("table.bonds")
async def dead_bonds_after(ctx: TickContext) -> None:
    await sweep_bonds_of_the_dead(ctx)


OPENING_PHASES = (Phase("dead_bonds_opening", dead_bonds_before),)
CLOSING_PHASES = (Phase("dead_bonds_closing", dead_bonds_after),)
PHASES = OPENING_PHASES + CLOSING_PHASES
