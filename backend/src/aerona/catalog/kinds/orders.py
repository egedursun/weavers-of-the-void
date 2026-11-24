from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.operations import EchelonOrder


@dataclass(frozen=True)
class EchelonOrderSpec:
    cost_rule: str
    organisation_rule: str | None = None
    organisation_sign: int = 0
    entrench_rule: str | None = None
    edge_rule: str | None = None
    edge_sign: int = 0


E = EchelonOrder
ECHELON_ORDERS: Mapping[EchelonOrder, EchelonOrderSpec] = total(
    EchelonOrder,
    {
        E.ATTACK: EchelonOrderSpec("attack_cost", edge_rule="attack_edge_pct", edge_sign=1),
        E.MANOEUVRE: EchelonOrderSpec("order_cost", organisation_rule="manoeuvre_organisation", organisation_sign=1),
        E.RESUPPLY: EchelonOrderSpec("order_cost"),
        E.HOLD: EchelonOrderSpec("order_cost", entrench_rule="hold_entrench"),
        E.STANDING: EchelonOrderSpec(
            "order_cost", organisation_rule="standing_organisation", organisation_sign=-1, edge_rule="standing_edge_pct", edge_sign=-1
        ),
        E.SCREEN: EchelonOrderSpec("order_cost", edge_rule="screen_edge_pct", edge_sign=1),
    },
)
