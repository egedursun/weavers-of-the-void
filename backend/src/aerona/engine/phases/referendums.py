from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.referendums.tend import tend_referendums


@reads("table.movement_profiles", "table.polity_profiles", "table.public_opinion", "table.referendums")
@writes("table.offices", "table.order_transitions", "table.polity_profiles", "table.referendums", "table.treaty_profiles")
async def referendums(ctx: TickContext) -> None:
    for key, value in asdict(await tend_referendums(ctx)).items():
        ctx.count(f"referendums_{key}", value)


PHASES = (Phase("referendums", referendums),)
