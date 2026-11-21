from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.labour import DisputeAct, LabourDemand
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import LabourTally, Parties, body_of, trades_of
from aerona.engine.labour.disputes import open_dispute
from aerona.engine.labour.hirers import hirer_of


async def strike_as_body(ctx: TickContext, faction_id: int, place: EntityRow) -> None:
    body = await body_of(ctx.session, faction_id)
    if body is None or not body.members or held(faction_id):
        return
    trades = trades_of(body)
    if not trades:
        return
    hirer = await hirer_of(ctx.session, place, trades[0])
    if hirer.id == faction_id or held(hirer.id):
        return
    await open_dispute(ctx, Parties(body, hirer, place, trades[0]), DisputeAct.STRIKE, LabourDemand.WAGE, LabourTally())
