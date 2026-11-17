from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.recording.record import StepDraft, record

HIDDEN_DISCOVERY = frozenset({Discovery.LEGEND, Discovery.UNKNOWN})


async def mark_world_discovered(ctx: TickContext, world: WorldRow, *, discoverer: int | None = None, method: TravelMethod | None = None) -> bool:
    previous = world.discovery
    if previous not in HIDDEN_DISCOVERY:
        return False
    await WorldRepository(ctx.session).set_discovery(world, Discovery.KNOWN)
    step = (StepDraft(StepAction.DISCOVER, actor=discoverer, target=world.id, outcome=StepOutcome.SUCCESS),)
    if discoverer is not None:
        await record(
            ctx,
            "cosmos.world_discovered",
            roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: discoverer},
            facts={"hidden": previous},
            steps=step,
            world_id=world.id,
        )
    else:
        await record(
            ctx,
            "cosmos.world_revealed",
            roles={IncidentRole.SUBJECT: world.id},
            facts={"hidden": previous, "method": method},
            steps=step,
            world_id=world.id,
        )
    ctx.count("worlds_discovered")
    return True
