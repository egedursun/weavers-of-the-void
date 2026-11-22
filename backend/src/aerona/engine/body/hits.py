import math
from dataclasses import dataclass, field

from aerona.catalog.anatomy import Anatomy, Part
from aerona.catalog.harm_kinds import DAMAGE, damage_where, injuries_where
from aerona.catalog.kinds.harm import HARM_CAUSES
from aerona.catalog.kinds.strikes import STRIKE_STYLES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN
from aerona.domain.enums.body import BodyRegion, DamageType, HarmCause, InjuryKind, StrikeStyle
from aerona.domain.enums.records import InstrumentKind
from aerona.engine.body.strike import EDGED, Layer, Scorch, Wielding, heat_of, resolve, strike_of
from aerona.engine.body.tissues import PLAIN, Hardness, TissueHit, tissue_hit
from aerona.rules.registry import Rules
from aerona.rules.registry.body import InjuryRules

PHYSICAL = damage_where(lambda spec: spec.physical)
PERMANENT_KINDS = injuries_where(lambda spec: spec.permanent)
MARK_KINDS = injuries_where(lambda spec: spec.mark)
DEEP_DAMAGE = damage_where(lambda spec: spec.deep)
BODILY_DAMAGE = damage_where(lambda spec: spec.bodily)
TOTAL_LOSS_KINDS = injuries_where(lambda spec: spec.total_loss)
CLEAN_HEALING_KINDS = injuries_where(lambda spec: spec.clean_healing)


@dataclass(frozen=True)
class Harm:
    damage: float
    cause: HarmCause
    death_cause: str
    damage_type: DamageType | None = None
    style: StrikeStyle = StrikeStyle.NORMAL
    source_node_id: int | None = None
    killer_id: int | None = None
    event_entity_id: int | None = None
    part: str | None = None
    kind: InjuryKind | None = None
    severity: int | None = None
    edge: int | None = None
    heft: int | None = None
    venom_pct: int | None = None
    heat: int | None = None
    step_id: int | None = None
    incident_id: int | None = None
    instrument_kind: InstrumentKind | None = None
    instrument_key: str | None = None
    instrument_node_id: int | None = None


@dataclass(frozen=True)
class Armour:
    head: int = 0
    torso: int = 0
    limbs: int = 0

    def coverage(self, region: BodyRegion) -> int:
        if region is BodyRegion.HEAD:
            return self.head
        if region is BodyRegion.TORSO:
            return self.torso
        return self.limbs


@dataclass(frozen=True)
class Hit:
    damage_type: DamageType
    part: Part
    severity: int
    kind: InjuryKind
    hp: float
    absorbed: bool = False
    scorched: tuple[Scorch, ...] = ()
    tissue: TissueHit = field(default_factory=TissueHit)


def cause_mix(rules: InjuryRules, cause: HarmCause) -> dict[DamageType, int]:
    mixed = {kind: int(getattr(rules, rule_name)) for kind, rule_name in HARM_CAUSES[cause].mix}
    return {kind: weight for kind, weight in mixed.items() if weight > 0}


def weighted[K](rng: SeededRandom, weights: dict[K, float]) -> K | None:
    total = sum(weight for weight in weights.values() if weight > 0)
    if total <= 0:
        return None
    roll = rng.random() * total
    for key, weight in weights.items():
        if weight <= 0:
            continue
        roll -= weight
        if roll < 0:
            return key
    return next(key for key, weight in reversed(weights.items()) if weight > 0)


def region_weights(rules: Rules, anatomy: Anatomy, style: StrikeStyle) -> dict[BodyRegion, float]:
    table = rules.anatomy
    base = {
        BodyRegion.HEAD: table.region_head,
        BodyRegion.TORSO: table.region_torso,
        BodyRegion.ARMS: table.region_arms,
        BodyRegion.LEGS: table.region_legs,
        BodyRegion.WINGS: table.region_wings,
        BodyRegion.TAIL: table.region_tail,
    }
    spec = STRIKE_STYLES[style]
    lean = {region: int(getattr(table, rule_name)) for region, rule_name in spec.lean}
    present = {part.region for part in anatomy.parts}
    if spec.whole:
        return {region: 1.0 for region in base if region in present}
    return {region: weight * lean.get(region, PERCENT) / PERCENT for region, weight in base.items() if region in present}


def pick_part(rules: Rules, anatomy: Anatomy, region: BodyRegion, damage_type: DamageType, severity: int, *, rng: SeededRandom) -> Part:
    parts = anatomy.in_region(region)
    exposed = [part for part in parts if not part.internal] or list(parts)
    inner = [part for part in parts if part.internal]
    reach = rules.anatomy
    deep = damage_type in DEEP_DAMAGE and severity >= reach.organ_reach_severity
    if inner and deep and rng.chance(reach.organ_reach_chance):
        return inner[rng.below(len(inner))]
    return exposed[rng.below(len(exposed))]


def severity_of(rules: InjuryRules, magnitude: float, rng: SeededRandom) -> int:
    spread = rng.uniform(rules.severity_spread_low_pct, rules.severity_spread_high_pct) / PERCENT
    raw = magnitude / max(1, rules.severity_step) * spread
    return max(SEVERITY_MIN, min(SEVERITY_MAX, math.ceil(raw)))


def kind_for(rules: InjuryRules, damage_type: DamageType, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return DAMAGE[damage_type].wound(rules, part, severity, cause)


def loss_for(rules: InjuryRules, kind: InjuryKind, severity: int) -> int:
    if kind in TOTAL_LOSS_KINDS:
        return PERCENT
    if kind is InjuryKind.DIVINE_BRAND:
        return 0
    return (rules.loss_severity_1, rules.loss_severity_2, rules.loss_severity_3, rules.loss_severity_4, rules.loss_severity_5)[severity - 1]


def harm_resisted(anatomy: Anatomy, damage_type: DamageType) -> bool:
    return damage_type in BODILY_DAMAGE and not anatomy.material


def edged_mix(mix: dict[DamageType, int], edge: int | None, heft: int | None) -> dict[DamageType, int]:
    if edge is None or heft is None:
        return mix
    shaped = dict(mix)
    if DamageType.CUT in shaped:
        shaped[DamageType.CUT] = round(shaped[DamageType.CUT] * (PERCENT + edge) / PERCENT)
    if DamageType.BLUNT in shaped:
        shaped[DamageType.BLUNT] = round(shaped[DamageType.BLUNT] * (PERCENT + heft * (PERCENT - edge) / PERCENT) / PERCENT)
    return shaped


def venom_mix(mix: dict[DamageType, int], venom_pct: int | None) -> dict[DamageType, int]:
    if venom_pct is None or DamageType.VENOM not in mix:
        return mix
    shaped = dict(mix)
    shaped[DamageType.VENOM] = round(shaped[DamageType.VENOM] * max(0, venom_pct) / PERCENT)
    return {kind: weight for kind, weight in shaped.items() if weight > 0}


def physical(damage_type: DamageType) -> bool:
    return damage_type in PHYSICAL


def hits_for(
    rules: Rules,
    anatomy: Anatomy,
    harm: Harm,
    armour: Armour,
    rng: SeededRandom,
    *,
    wielding: Wielding | None = None,
    layers: tuple[Layer, ...] = (),
    hardness: Hardness = PLAIN,
) -> list[Hit]:
    table = rules.injury
    if harm.damage <= 0:
        return []
    count = 1 if harm.part else max(1, min(table.max_hits, math.ceil(harm.damage / max(1, table.hit_size))))
    magnitude = harm.damage / count
    hits: list[Hit] = []
    mix = venom_mix(edged_mix(cause_mix(table, harm.cause), harm.edge, harm.heft), harm.venom_pct)
    for _ in range(count):
        damage_type = harm.damage_type or weighted(rng, {key: float(value) for key, value in mix.items()}) or DamageType.BLUNT
        if harm_resisted(anatomy, damage_type):
            hits.append(Hit(damage_type, anatomy.parts[0], SEVERITY_MIN, InjuryKind.BRUISE, magnitude * table.resisted_hp_pct / PERCENT, absorbed=True))
            continue
        severity = harm.severity or severity_of(table, magnitude, rng)
        chosen = anatomy.part(harm.part) if harm.part else None
        if chosen is None:
            region = weighted(rng, region_weights(rules, anatomy, harm.style)) or anatomy.parts[0].region
            chosen = pick_part(rules, anatomy, region, damage_type, severity, rng=rng)
        scorched: tuple[Scorch, ...] = ()
        attack: float | None = None
        if harm.severity is None and wielding is not None and layers and physical(damage_type):
            strike = strike_of(
                rules,
                wielding.weapon,
                damage_type=damage_type,
                heft=wielding.heft,
                skill=wielding.skill,
                heat=heat_of(rules, harm.cause, damage_type, harm.heat),
            )
            outcome = resolve(rules, strike, layers, chosen.region, rng)
            severity = round(severity * outcome.spent * rules.strike.severity_momentum_pct / PERCENT)
            damage_type = DamageType.BLUNT if damage_type in EDGED and outcome.damage_type is DamageType.BLUNT else damage_type
            scorched = outcome.scorched
            attack = outcome.strike.attack if damage_type is not DamageType.FIRE else None
        elif harm.severity is None and rng.chance(armour.coverage(chosen.region)):
            severity -= table.armour_severity_cut
        if severity < SEVERITY_MIN:
            soaked = magnitude * table.absorbed_hp_pct / PERCENT
            hits.append(Hit(damage_type, chosen, SEVERITY_MIN, InjuryKind.BRUISE, soaked, absorbed=True, scorched=scorched))
            continue
        kind = harm.kind or kind_for(table, damage_type, chosen, severity, harm.cause)
        reached = tissue_hit(rules, anatomy.plan, chosen, damage_type, severity, attack=attack, hardness=hardness)
        hits.append(Hit(damage_type, chosen, severity, kind, magnitude, scorched=scorched, tissue=reached))
    return hits
