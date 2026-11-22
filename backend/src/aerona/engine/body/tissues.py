from dataclasses import dataclass

from aerona.catalog.anatomy import Part
from aerona.catalog.creature_anatomy import TISSUES as MATERIALS
from aerona.catalog.harm_kinds import DAMAGE, damage_where
from aerona.catalog.tissues import MAJOR_VESSELS, TISSUES, covering_of, stack_of
from aerona.constants.units import PERCENT
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.domain.enums.body import BodyPlan, DamageType, NerveDamage, TissueKind
from aerona.domain.enums.ecology import TissueMaterial
from aerona.rules.registry import Rules

T = TissueKind
CUTTING = damage_where(lambda spec: spec.edged)
STRIKING = damage_where(lambda spec: spec.striking)
SEARING = damage_where(lambda spec: spec.searing)


@dataclass(frozen=True)
class TissueHit:
    deepest: TissueKind | None = None
    bleeding: int = 0
    nerve: NerveDamage = NerveDamage.NONE
    tendon: bool = False
    bone: bool = False
    organ: bool = False


@dataclass(frozen=True)
class Hardness:
    skin: TissueMaterial | None = None
    bone: TissueMaterial | None = None

    def guard(self, tissue: TissueKind, layer: int, *, edged: bool) -> int:
        material = self.skin if layer == 0 else self.bone if tissue is T.BONE else None
        if material is not None:
            spec = MATERIALS[material]
            return spec.shear_yield if edged else spec.impact_yield
        base = TISSUES[tissue]
        return base.shear_yield if edged else base.impact_yield


PLAIN = Hardness()


def hardness_of(creature: CreatureAnatomyRow | None) -> Hardness:
    return Hardness(creature.skin, creature.bone) if creature is not None else PLAIN


def property_kept(skin: TissueMaterial, damage_type: DamageType | None) -> float:
    spec = MATERIALS[skin]
    if damage_type is DamageType.ELECTRIC:
        return 1 + spec.conductivity / PERCENT / 2
    if damage_type is not None and DAMAGE[damage_type].thermal:
        return 1 - spec.heat_resistance / PERCENT / 2
    if damage_type is DamageType.BLUNT:
        return 1 - spec.flexibility / PERCENT / 4
    if damage_type in CUTTING:
        return 1 - spec.hardness / PERCENT / 4
    return 1.0


def skin_kept(rules: Rules, creature: CreatureAnatomyRow | None, damage_type: DamageType | None = None) -> float:
    if creature is None:
        return 1.0
    armour = max(0.0, 1 - MATERIALS[creature.skin].armour_pct * rules.creature_anatomy.skin_damage_pct / PERCENT / PERCENT)
    return max(0.0, armour * property_kept(creature.skin, damage_type))


def bleed_rate(rules: Rules, part: Part, severity: int) -> int:
    table = rules.tissues
    base = table.major_bleed if part.key in MAJOR_VESSELS else table.minor_bleed
    return min(PERCENT, round(base * (1 + max(0, severity - 1) * table.bleed_severity_pct / PERCENT)))


def tissue_hit(
    rules: Rules, plan: BodyPlan, part: Part, damage_type: DamageType, severity: int, *, attack: float | None = None, hardness: Hardness = PLAIN
) -> TissueHit:
    if damage_type in SEARING:
        return TissueHit(covering_of(plan))
    if damage_type not in STRIKING:
        return TissueHit()
    table = rules.tissues
    edged = damage_type in CUTTING
    force = attack if attack is not None else severity * table.depth_per_severity
    reached: list[TissueKind] = []
    for layer, tissue in enumerate(stack_of(plan, part.key, part.region)):
        guard = hardness.guard(tissue, layer, edged=edged)
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
