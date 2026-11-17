from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.kinds import DrinkRole
from aerona.domain.enums.mind import MemoryKind


@dataclass(frozen=True)
class DrinkRoleEffect:
    rule: str | None
    town_stat: str | None = None
    profile_field: str | None = None
    lowers: bool = False
    bonds: bool = False
    memory: MemoryKind | None = None
    note: str = ""


R = DrinkRole
DRINK_ROLES: Mapping[DrinkRole, DrinkRoleEffect] = total(
    DrinkRole,
    {
        R.DAILY: DrinkRoleEffect(None),
        R.HOSPITALITY: DrinkRoleEffect("hospitality_regard", bonds=True, memory=MemoryKind.GIFTED_ME, note="a drink of welcome shared"),
        R.FEAST: DrinkRoleEffect("feast_calm", profile_field="unrest", lowers=True),
        R.RITE: DrinkRoleEffect("rite_piety", town_stat="piety"),
        R.MEDICINE: DrinkRoleEffect("medicine_care", profile_field="sanitation"),
        R.TRADE: DrinkRoleEffect("trade_prosperity", town_stat="prosperity"),
        R.BOND_MAKING: DrinkRoleEffect("bond_regard", bonds=True, memory=MemoryKind.ALLIED_WITH, note="a drink kept for making bonds shared"),
    },
)
BONDING_ROLES = frozenset(role for role, effect in DRINK_ROLES.items() if effect.bonds)
