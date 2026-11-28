from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.record_keepers.keepers import KeeperTally, keep_record_keepers
from aerona.engine.record_keepers.legacy import recover_keepers


@reads(
    "table.bonds",
    "table.court_positions",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.epochs",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.historian_views",
    "table.node_births",
    "table.nodes",
    "table.record_keepers",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.record_keepers",
)
async def record_keepers(ctx: TickContext) -> None:
    ctx.count("record_keepers_recovered", await recover_keepers(ctx))
    tally = KeeperTally()
    await keep_record_keepers(ctx, tally)
    ctx.count("record_keepers_seated", tally.seated)
    ctx.count("record_keepers_succeeded", tally.succeeded)
    ctx.count("record_keepers_vacant", tally.vacant)


PHASES = (Phase("record_keepers", record_keepers),)
