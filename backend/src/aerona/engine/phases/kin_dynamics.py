from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kin_dynamics.tend import tend_kin
from aerona.engine.phase import Phase


@reads(
    "table.designated_heirs",
    "table.elder_sway",
    "table.house_members",
    "table.house_profiles",
    "table.kin_blends",
    "table.kin_disownings",
    "table.kin_dynamics",
    "table.kin_favours",
    "table.kin_rivalries",
)
@writes("table.elder_sway", "table.house_members", "table.kin_blends", "table.kin_disownings", "table.kin_dynamics", "table.kin_favours", "table.kin_rivalries")
async def kin_dynamics(ctx: TickContext) -> None:
    for key, value in asdict(await tend_kin(ctx)).items():
        ctx.count(f"kin_dynamics_{key}", value)


PHASES = (Phase("kin_dynamics", kin_dynamics),)
