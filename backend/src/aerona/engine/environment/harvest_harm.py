from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.model import EPOCH_YEARS

HARVEST_CEILING = PERCENT * 2


def harm_harvest(ground: RegionEnvironmentRow | None, year_loss_pct: float) -> int:
    if ground is None or held(ground.entity_id) or "harvest_pct" in ground.locked:
        return 0
    share = min(float(PERCENT), max(0.0, year_loss_pct)) / PERCENT
    lost = min(ground.harvest_pct, round_half_up(ground.harvest_pct * share / EPOCH_YEARS))
    ground.harvest_pct = clamp_int(ground.harvest_pct - lost, 0, HARVEST_CEILING)
    return lost


def shift_harvest(ground: RegionEnvironmentRow | None, points: int) -> int:
    if ground is None or held(ground.entity_id) or "harvest_pct" in ground.locked:
        return 0
    before = ground.harvest_pct
    ground.harvest_pct = clamp_int(before + points, 0, HARVEST_CEILING)
    return ground.harvest_pct - before
