import math
from collections.abc import Callable
from dataclasses import dataclass

from aerona.catalog.anatomy import Anatomy, Part
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN
from aerona.domain.enums.body import BodyFunction, BodyRegion, DamageType, HarmCause, InjuryKind, StrikeStyle
from aerona.rules.registry import Rules
from aerona.rules.registry.body import InjuryRules

PERMANENT_KINDS = frozenset({InjuryKind.SEVERED, InjuryKind.GOUGED, InjuryKind.DESTROYED, InjuryKind.VOID_TOUCH, InjuryKind.DIVINE_BRAND})
MARK_KINDS = frozenset({InjuryKind.VOID_TOUCH, InjuryKind.DIVINE_BRAND})
TOTAL_LOSS_KINDS = frozenset({InjuryKind.SEVERED, InjuryKind.GOUGED, InjuryKind.DESTROYED})


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


def cause_mix(rules: InjuryRules, cause: HarmCause) -> dict[DamageType, int]:
    mixes: dict[HarmCause, dict[DamageType, int]] = {
        HarmCause.BATTLE: {
            DamageType.CUT: rules.battle_cut,
            DamageType.PIERCE: rules.battle_pierce,
            DamageType.BLUNT: rules.battle_blunt,
            DamageType.FIRE: rules.battle_fire,
        },
        HarmCause.DUEL: {DamageType.CUT: rules.duel_cut, DamageType.PIERCE: rules.duel_pierce, DamageType.BLUNT: rules.duel_blunt},
        HarmCause.MONSTER: {
            DamageType.CUT: rules.monster_claw,
            DamageType.PIERCE: rules.monster_bite,
            DamageType.BLUNT: rules.monster_crush,
            DamageType.VENOM: rules.monster_venom,
        },
        HarmCause.QUEST: {
            DamageType.CUT: rules.quest_cut,
            DamageType.BLUNT: rules.quest_blunt,
            DamageType.COLD: rules.quest_cold,
            DamageType.PIERCE: rules.quest_pierce,
        },
        HarmCause.ACCIDENT: {DamageType.BLUNT: rules.accident_blunt, DamageType.CUT: rules.accident_cut, DamageType.FIRE: rules.accident_fire},
        HarmCause.ESCAPE: {DamageType.BLUNT: rules.escape_blunt, DamageType.CUT: rules.escape_cut},
        HarmCause.PUNISHMENT: {DamageType.CUT: rules.punishment_cut, DamageType.BLUNT: rules.punishment_blunt, DamageType.FIRE: rules.punishment_fire},
        HarmCause.TORTURE: {DamageType.CUT: rules.torture_cut, DamageType.BLUNT: rules.torture_blunt, DamageType.FIRE: rules.torture_fire},
        HarmCause.DISASTER: {
            DamageType.BLUNT: rules.disaster_blunt,
            DamageType.FIRE: rules.disaster_fire,
            DamageType.COLD: rules.disaster_cold,
            DamageType.CUT: rules.disaster_cut,
        },
        HarmCause.CURSE: {DamageType.MAGIC: rules.curse_magic, DamageType.VOID: rules.curse_void},
        HarmCause.MAGIC_BACKLASH: {DamageType.MAGIC: rules.backlash_magic, DamageType.FIRE: rules.backlash_fire, DamageType.VOID: rules.backlash_void},
        HarmCause.GOD: {DamageType.HOLY: rules.god_holy, DamageType.FIRE: rules.god_fire, DamageType.BLUNT: rules.god_blunt},
        HarmCause.POISON: {DamageType.VENOM: rules.poison_venom},
        HarmCause.SACRIFICE: {DamageType.CUT: rules.sacrifice_cut, DamageType.MAGIC: rules.sacrifice_magic},
        HarmCause.AGE: {DamageType.BLUNT: rules.age_blunt},
        HarmCause.PLAYER: {DamageType.CUT: rules.player_cut, DamageType.BLUNT: rules.player_blunt, DamageType.PIERCE: rules.player_pierce},
    }
    return {kind: weight for kind, weight in mixes[cause].items() if weight > 0}


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
    lean = {
        StrikeStyle.NORMAL: {},
        StrikeStyle.WHOLE: {},
        StrikeStyle.TRAMPLE: {BodyRegion.LEGS: table.trample_legs_pct, BodyRegion.TORSO: table.trample_torso_pct},
        StrikeStyle.AERIAL: {BodyRegion.HEAD: table.aerial_head_pct, BodyRegion.WINGS: table.aerial_wings_pct},
        StrikeStyle.LOW: {BodyRegion.LEGS: table.low_legs_pct},
    }[style]
    present = {part.region for part in anatomy.parts}
    if style is StrikeStyle.WHOLE:
        return {region: 1.0 for region in base if region in present}
    return {region: weight * lean.get(region, PERCENT) / PERCENT for region, weight in base.items() if region in present}


def pick_part(rules: Rules, anatomy: Anatomy, region: BodyRegion, damage_type: DamageType, severity: int, *, rng: SeededRandom) -> Part:
    parts = anatomy.in_region(region)
    exposed = [part for part in parts if not part.internal] or list(parts)
    inner = [part for part in parts if part.internal]
    reach = rules.anatomy
    deep = damage_type in {DamageType.PIERCE, DamageType.BLUNT, DamageType.VENOM} and severity >= reach.organ_reach_severity
    if inner and deep and rng.chance(reach.organ_reach_chance):
        return inner[rng.below(len(inner))]
    return exposed[rng.below(len(exposed))]


def severity_of(rules: InjuryRules, magnitude: float, rng: SeededRandom) -> int:
    spread = rng.uniform(rules.severity_spread_low_pct, rules.severity_spread_high_pct) / PERCENT
    raw = magnitude / max(1, rules.severity_step) * spread
    return max(SEVERITY_MIN, min(SEVERITY_MAX, math.ceil(raw)))


def _sight(part: Part) -> bool:
    return BodyFunction.SIGHT in part.functions


def _small(part: Part) -> bool:
    return part.severable and (part.counted > 0 or part.region in {BodyRegion.HEAD, BodyRegion.TAIL})


def _cut(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    sever_at = rules.cut_sever_small_at if _small(part) else rules.cut_sever_at
    if part.severable and severity >= sever_at:
        return InjuryKind.SEVERED
    return InjuryKind.DEEP_CUT if severity >= rules.cut_deep_at else InjuryKind.CUT


def _pierce(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if _sight(part) and severity >= rules.pierce_gouge_at:
        return InjuryKind.GOUGED
    if part.vital and severity >= rules.pierce_destroy_at:
        return InjuryKind.DESTROYED
    return InjuryKind.BITE if cause is HarmCause.MONSTER else InjuryKind.PUNCTURE


def _blunt(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if severity >= rules.blunt_crush_at:
        return InjuryKind.CRUSH
    return InjuryKind.FRACTURE if severity >= rules.blunt_fracture_at else InjuryKind.BRUISE


def _fire(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return InjuryKind.DESTROYED if _sight(part) and severity >= rules.fire_blind_at else InjuryKind.BURN


def _cold(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return InjuryKind.SEVERED if part.severable and severity >= rules.cold_loss_at else InjuryKind.FROSTBITE


def _magic(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return InjuryKind.CURSE_WITHER if severity >= rules.magic_wither_at else InjuryKind.BURN


KindRule = Callable[[InjuryRules, Part, int, HarmCause], InjuryKind]

KIND_RULES: dict[DamageType, KindRule] = {
    DamageType.CUT: _cut,
    DamageType.PIERCE: _pierce,
    DamageType.BLUNT: _blunt,
    DamageType.FIRE: _fire,
    DamageType.COLD: _cold,
    DamageType.MAGIC: _magic,
}

FIXED_KINDS: dict[DamageType, InjuryKind] = {
    DamageType.VOID: InjuryKind.VOID_TOUCH,
    DamageType.HOLY: InjuryKind.DIVINE_BRAND,
    DamageType.VENOM: InjuryKind.VENOM,
}


def kind_for(rules: InjuryRules, damage_type: DamageType, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    chooser = KIND_RULES.get(damage_type)
    return chooser(rules, part, severity, cause) if chooser is not None else FIXED_KINDS[damage_type]


def loss_for(rules: InjuryRules, kind: InjuryKind, severity: int) -> int:
    if kind in TOTAL_LOSS_KINDS:
        return PERCENT
    if kind is InjuryKind.DIVINE_BRAND:
        return 0
    return (rules.loss_severity_1, rules.loss_severity_2, rules.loss_severity_3, rules.loss_severity_4, rules.loss_severity_5)[severity - 1]


def harm_resisted(anatomy: Anatomy, damage_type: DamageType) -> bool:
    physical = damage_type in {DamageType.CUT, DamageType.PIERCE, DamageType.BLUNT, DamageType.COLD, DamageType.VENOM}
    return physical and not anatomy.material


def edged_mix(mix: dict[DamageType, int], edge: int | None, heft: int | None) -> dict[DamageType, int]:
    if edge is None or heft is None:
        return mix
    shaped = dict(mix)
    if DamageType.CUT in shaped:
        shaped[DamageType.CUT] = round(shaped[DamageType.CUT] * (PERCENT + edge) / PERCENT)
    if DamageType.BLUNT in shaped:
        shaped[DamageType.BLUNT] = round(shaped[DamageType.BLUNT] * (PERCENT + heft * (PERCENT - edge) / PERCENT) / PERCENT)
    return shaped


def hits_for(rules: Rules, anatomy: Anatomy, harm: Harm, armour: Armour, rng: SeededRandom) -> list[Hit]:
    table = rules.injury
    if harm.damage <= 0:
        return []
    count = 1 if harm.part else max(1, min(table.max_hits, math.ceil(harm.damage / max(1, table.hit_size))))
    magnitude = harm.damage / count
    hits: list[Hit] = []
    mix = edged_mix(cause_mix(table, harm.cause), harm.edge, harm.heft)
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
        if harm.severity is None and rng.chance(armour.coverage(chosen.region)):
            severity -= table.armour_severity_cut
        if severity < SEVERITY_MIN:
            hits.append(Hit(damage_type, chosen, SEVERITY_MIN, InjuryKind.BRUISE, magnitude * table.absorbed_hp_pct / PERCENT, absorbed=True))
            continue
        kind = harm.kind or kind_for(table, damage_type, chosen, severity, harm.cause)
        hits.append(Hit(damage_type, chosen, severity, kind, magnitude))
    return hits
