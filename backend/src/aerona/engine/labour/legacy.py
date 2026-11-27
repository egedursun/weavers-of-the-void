from sqlalchemy import select

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.labour import LabourDisputeRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.labour import DisputeAct, DisputeOutcome, LabourDemand, WorkerBodyForm
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import body_covering, body_of
from aerona.engine.labour.founding import found_body

LEGACY_FIXUP = "labour.legacy_bodies"
STRIKE_KIND = "faction.strike"


async def past_strikes(ctx: TickContext) -> list[tuple[int, int, int | None]]:
    rows = await ctx.session.execute(
        select(IncidentRow.epoch, IncidentParticipantRow.node_id, IncidentRow.place_entity_id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == STRIKE_KIND, IncidentParticipantRow.role == IncidentRole.ACTOR)
        .order_by(IncidentRow.id)
    )
    return [(epoch, actor, place) for epoch, actor, place in rows]


async def apply_legacy(ctx: TickContext) -> dict[str, int]:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return {}
    societies = disputes = 0
    for epoch, actor, place in await past_strikes(ctx):
        striker = await ctx.session.get(EntityRow, actor)
        town = await ctx.session.get(EntityRow, place) if place is not None else None
        if striker is None:
            continue
        profile = await ctx.session.get(FactionProfileRow, actor)
        body_id = actor if await body_of(ctx.session, actor) is not None else None
        if profile is not None and profile.kind is FactionKind.CRAFT_GUILD and town is not None and town.status is EntityStatus.CANON:
            society = await body_covering(ctx.session, town.id, Job.CRAFTING)
            if society is None:
                society = await found_body(ctx, town, [Job.CRAFTING], WorkerBodyForm.COMPANION_SOCIETY)
                societies += 1
            body_id = society.faction_node_id
        ctx.session.add(
            LabourDisputeRow(
                name=f"the strike at {town.name}" if town is not None else f"the strike of {striker.name}",
                body_node_id=body_id,
                hirer_node_id=None,
                settlement_entity_id=town.id if town is not None else None,
                trade=Job.CRAFTING,
                demand=LabourDemand.WAGE,
                act=DisputeAct.STRIKE,
                outcome=DisputeOutcome.SETTLED,
                started_epoch=epoch,
                ended_epoch=epoch,
                locked=[],
            )
        )
        disputes += 1
    result = {"societies": societies, "disputes": disputes}
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return result
