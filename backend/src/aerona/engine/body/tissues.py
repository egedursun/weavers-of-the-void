from dataclasses import dataclass

from aerona.catalog.anatomy import Part
from aerona.catalog.tissues import MAJOR_VESSELS, TISSUES, covering_of, stack_of
from aerona.constants.units import PERCENT
from aerona.domain.enums.body import BodyPlan, DamageType, NerveDamage, TissueKind
from aerona.rules.registry import Rules

T = TissueKind
CUTTING = frozenset({DamageType.CUT, DamageType.PIERCE})
STRIKING = frozenset({*CUTTING, DamageType.BLUNT})
SEARING = frozenset({DamageType.FIRE, DamageType.COLD})


@dataclass(frozen=True)
class TissueHit:
    deepest: TissueKind | None = None
    bleeding: int = 0
    nerve: NerveDamage = NerveDamage.NONE
    tendon: bool = False
    bone: bool = False
    organ: bool = False


def bleed_rate(rules: Rules, part: Part, severity: int) -> int:
    table = rules.tissues
    base = table.major_bleed if part.key in MAJOR_VESSELS else table.minor_bleed
    return min(PERCENT, round(base * (1 + max(0, severity - 1) * table.bleed_severity_pct / PERCENT)))


def tissue_hit(rules: Rules, plan: BodyPlan, part: Part, damage_type: DamageType, severity: int, *, attack: float | None = None) -> TissueHit:
    if damage_type in SEARING:
        return TissueHit(covering_of(plan))
    if damage_type not in STRIKING:
        return TissueHit()
    table = rules.tissues
    edged = damage_type in CUTTING
    force = attack if attack is not None else severity * table.depth_per_severity
    reached: list[TissueKind] = []
    for tissue in stack_of(plan, part.key, part.region):
        spec = TISSUES[tissue]
        guard = spec.shear_yield if edged else spec.impact_yield
        if force < guard:
            break
        reached.append(tissue)
        force -= guard * table.tissue_spend_pct / PERCENT
    nerve = NerveDamage.MOTOR if T.MOTOR_NERVE in reached else NerveDamage.SENSORY if T.SENSORY_NERVE in reached else NerveDamage.NONE
    return TissueHit(
        deepest=reached[-1] if reached else None,
        bleeding=bleed_rate(rules, part, severity) if T.ARTERY in reached else 0,
        nerve=nerve,
        tendon=edged and T.TENDON in reached,
        bone=T.BONE in reached,
        organ=T.ORGAN in reached,
    )


def tissue_loss(rules: Rules, hit: TissueHit) -> int:
    table = rules.tissues
    loss = 0
    if hit.tendon:
        loss = max(loss, table.tendon_loss)
    if hit.nerve is NerveDamage.MOTOR:
        loss = max(loss, table.motor_loss)
    return loss
