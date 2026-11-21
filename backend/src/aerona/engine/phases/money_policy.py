from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.monetary.tend import tend_money_policy
from aerona.engine.phase import Phase


@reads("table.currencies", "table.monetary_authorities")
@writes("table.applied_fixups", "table.currencies", "table.monetary_authorities", "table.monetary_rates")
async def money_policy(ctx: TickContext) -> None:
    for key, value in asdict(await tend_money_policy(ctx)).items():
        ctx.count(f"monetary_{key}", value)


PHASES = (Phase("money_policy", money_policy),)
