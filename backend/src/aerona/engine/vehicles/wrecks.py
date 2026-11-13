from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.integrity import SectionHazard, SectionState
from aerona.domain.enums.vehicles import VehicleDomain
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.vehicles.sections import batter_vessel

VOID_DOMAINS = frozenset({VehicleDomain.SPACE, VehicleDomain.GAS_GIANT, VehicleDomain.PLANAR})


def wreck_cause(row: VesselProfileRow, hazard: SectionHazard) -> HarmCause | None:
    if hazard is SectionHazard.CRASH:
        return HarmCause.CRASH
    return HarmCause.DECOMPRESSION if hazard is SectionHazard.BREACH and FRAMES[row.frame].domain in VOID_DOMAINS else None


async def wreck_crew(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, hazard: SectionHazard) -> bool:
    captain = await ctx.session.get(EntityRow, row.captain_entity_id) if row.captain_entity_id is not None else None
    cause = wreck_cause(row, hazard)
    if cause is None or captain is None or captain.status is not EntityStatus.CANON or held(captain.id):
        return False
    words = f"went down with {vessel.name}" if cause is HarmCause.CRASH else f"was caught when {vessel.name} lost its air"
    await apply_hits(ctx, captain, Harm(ctx.rules.vehicles.wreck_hp, cause, words, event_entity_id=vessel.id))
    return True


async def battered(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, hits: int, slot: str) -> int:
    wrecked = 0
    for section, state in await batter_vessel(ctx, vessel, row, hits, slot):
        if state is SectionState.DESTROYED and await wreck_crew(ctx, vessel, row, section.hazard):
            wrecked += 1
    return wrecked
