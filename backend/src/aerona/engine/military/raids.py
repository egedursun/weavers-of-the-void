from aerona.constants.units import PERCENT
from aerona.db.tables.military import ArmyProfileRow
from aerona.domain.enums.military import Stance
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


def escorted_take(rules: Rules, victim: ArmyProfileRow, taken: int) -> int:
    if victim.stance is not Stance.ESCORT:
        return taken
    return round_half_up(taken * (PERCENT - rules.campaign.escort_raid_cut_pct) / PERCENT)
