from dataclasses import dataclass, field

from aerona.catalog.units import (
    AMBUSH_TERRAIN,
    ARMOUR_DEFENCE,
    DEFENDER_TERRAIN,
    HEAVY_WEATHER,
    SHIELD_DEFENCE,
    STYLE_TACTICS,
    TACTIC_COUNTERS,
    TACTIC_TERRAIN,
    TERRAIN_EFFECTS,
    UNITS,
    WEATHER_EFFECTS,
    UnitSpec,
)
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import ArmourType, BattlePhase, CommanderTrait, OutcomeClass, Tactic, UnitFamily, UnitKind
from aerona.rules.registry import Rules

F = UnitFamily
MISSILE_FAMILIES = frozenset({F.MISSILE, F.MAGIC, F.ENGINEER})
CHARGE_FAMILIES = frozenset({F.MOUNTED, F.BEAST})
FLYERS = frozenset({UnitKind.SKY_MOUNTS, UnitKind.SKYSHIPS})
SCOUTS = frozenset({UnitKind.LIGHT_CAVALRY, UnitKind.SKIRMISHERS, UnitKind.HORSE_ARCHERS, UnitKind.SKY_MOUNTS})
SHELTER = frozenset({TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.MOUNTAINS, TerrainKind.MARSH, TerrainKind.HIGH_PASS})
HELMET = 5
NORMAL = 50
REFUSE_RATIO = 0.6
GENERIC = (Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT)
TRAIT_TACTICS: dict[CommanderTrait, tuple[Tactic, ...]] = {
    CommanderTrait.RECKLESS: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.AGGRESSIVE_ASSAULTER: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.CAUTIOUS: (Tactic.HOLD_LINE, Tactic.SHIELD_WALL),
    CommanderTrait.DEFENSIVE_GENIUS: (Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE, Tactic.SHIELD_WALL),
    CommanderTrait.CAVALRY_MASTER: (Tactic.FLANK_CAVALRY, Tactic.FEIGNED_RETREAT),
    CommanderTrait.SIEGE_EXPERT: (Tactic.SIEGE_ASSAULT,),
}


@dataclass
class Stack:
    row: ArmyUnitRow
    spec: UnitSpec
    start: int
    routed: bool = False
    lost: int = 0

    @property
    def alive(self) -> bool:
        return self.row.count > 0 and not self.routed

    @property
    def armour(self) -> int:
        return self.spec.defence + ARMOUR_DEFENCE[self.row.armour] + SHIELD_DEFENCE[self.row.shield] + (HELMET if self.row.helmet else 0)


@dataclass
class Side:
    entity: EntityRow
    army: EntityRow
    profile: ArmyProfileRow
    stacks: list[Stack]
    edge: float
    defending: bool
    skill: int
    traits: set[CommanderTrait]
    intel: int = 0
    veteran: float = 0.0
    leadership: int = 0
    tactic: Tactic = Tactic.HOLD_LINE
    tactic_factor: float = 1.0
    surprise: float = 1.0
    pursuit_lost: int = 0
    captives: int = 0

    @property
    def start(self) -> int:
        return sum(stack.start for stack in self.stacks)

    @property
    def standing(self) -> int:
        return sum(stack.row.count for stack in self.stacks if stack.alive)

    @property
    def lost(self) -> int:
        return sum(stack.lost for stack in self.stacks)


@dataclass
class PhaseLog:
    phase: BattlePhase
    attacker_losses: int
    defender_losses: int
    summary: str
    details: dict[str, int | str] = field(default_factory=dict)


@dataclass
class BattleResult:
    attacker: Side
    defender: Side
    winner: Side | None
    loser: Side | None
    refused: bool
    outcome: OutcomeClass
    gap: float
    phases: list[PhaseLog]
    wounded: dict[int, int]
    maimed: dict[int, int]
    by_kind: dict[str, int]


@dataclass(frozen=True)
class Field:
    terrain: TerrainKind | None
    weather: WeatherKind | None
    night: bool
    river: bool = False


def modifier(rules: Rules, stack: Stack, side: Side, ground: Field) -> float:
    family = stack.spec.family
    row = stack.row
    terrain = TERRAIN_EFFECTS.get(ground.terrain, {}).get(family, 1.0) if ground.terrain is not None else 1.0
    terrain = 1 + (terrain - 1) * rules.terrain_effects.strength_pct / PERCENT
    terrain *= stack.spec.terrain.get(ground.terrain, 1.0) if ground.terrain is not None else 1.0
    weather = WEATHER_EFFECTS.get(ground.weather, {}).get(family, 1.0) if ground.weather is not None else 1.0
    weather = 1 + (weather - 1) * rules.weather_battle_effects.strength_pct / PERCENT
    heavy = row.armour in {ArmourType.MAIL, ArmourType.SCALE, ArmourType.PLATE}
    fatigue = row.fatigue * (rules.weather_battle_effects.heavy_fatigue_pct / PERCENT if heavy and ground.weather in HEAVY_WEATHER else 1.0)
    quality = row.quality / NORMAL * (1 + row.experience / PERCENT * rules.military_units.experience_pct / PERCENT) * (1 + side.veteran)
    vigour = max(0.2, 1 - fatigue / (2 * PERCENT)) * (0.5 + min(PERCENT, row.morale + side.leadership) / PERCENT)
    crossing = rules.terrain_effects.river_crossing_pct / PERCENT if ground.river and not side.defending else 1.0
    height = DEFENDER_TERRAIN.get(ground.terrain, 1.0) if side.defending and ground.terrain is not None else 1.0
    height = 1 + (height - 1) * rules.terrain_effects.defender_height_pct / PERCENT
    dug = 1 + side.profile.entrenchment / PERCENT * rules.logistics.entrench_defence_pct / PERCENT if side.defending else 1.0
    return quality * vigour * terrain * weather * height * dug * crossing * side.edge * side.tactic_factor * side.surprise


def strength(rules: Rules, side: Side, ground: Field) -> float:
    return sum(
        stack.row.count * (stack.spec.melee + stack.spec.missile + stack.armour) / 3 * modifier(rules, stack, side, ground)
        for stack in side.stacks
        if stack.alive
    )


def scouting(side: Side) -> float:
    eyes = sum(stack.row.count * stack.spec.speed / PERCENT for stack in side.stacks if stack.alive and stack.row.kind in SCOUTS)
    return eyes + side.skill * 10 + side.intel


def choose_tactic(rules: Rules, rng: SeededRandom, side: Side, enemy_doctrine: str, ground: Field) -> Tactic:
    options = list(dict.fromkeys([*STYLE_TACTICS.get(side.profile.doctrine, GENERIC), *GENERIC]))
    for trait in side.traits:
        options.extend(item for item in TRAIT_TACTICS.get(trait, ()) if item not in options)
    expected = STYLE_TACTICS.get(enemy_doctrine, GENERIC)[0]
    weights = []
    for option in options:
        weight = 1.0
        if ground.terrain is not None and option in TACTIC_TERRAIN:
            weight *= 2.0 if ground.terrain in TACTIC_TERRAIN[option] else 0.4
        if expected in TACTIC_COUNTERS.get(option, frozenset()):
            weight *= 1 + side.skill * rules.tactics.skill_weight / 10
        if option is Tactic.AMBUSH and not (ground.terrain in AMBUSH_TERRAIN or ground.weather is WeatherKind.FOG or ground.night):
            weight *= 0.1
        if option is Tactic.NIGHT_RAID and not ground.night:
            weight *= 0.1
        if any(option in TRAIT_TACTICS.get(trait, ()) for trait in side.traits):
            weight *= 2.0
        weights.append(weight)
    return rng.weighted(options, weights)


def tactic_factor(rules: Rules, mine: Tactic, theirs: Tactic, ground: Field) -> float:
    table = rules.tactics
    factor = 1.0
    if theirs in TACTIC_COUNTERS.get(mine, frozenset()):
        factor *= table.counter_pct / PERCENT
    if mine in TACTIC_COUNTERS.get(theirs, frozenset()):
        factor *= table.countered_pct / PERCENT
    if ground.terrain is not None and mine in TACTIC_TERRAIN:
        factor *= (table.terrain_pct if ground.terrain in TACTIC_TERRAIN[mine] else table.misplaced_pct) / PERCENT
    return factor


def deal(targets: list[Stack], damage: float, rules: Rules) -> int:
    alive = [stack for stack in targets if stack.alive]
    total = sum(stack.row.count for stack in alive)
    if total <= 0 or damage <= 0:
        return 0
    killed = 0
    for stack in alive:
        share = stack.row.count / total
        losses = min(stack.row.count, int(damage * share * rules.tactics.loss_scale_pct / PERCENT * NORMAL / max(10, stack.armour)))
        stack.row.count -= losses
        stack.lost += losses
        killed += losses
    return killed


def shaken(rules: Rules, side: Side) -> None:
    routs = 0
    for stack in side.stacks:
        if not stack.alive or stack.start <= 0:
            continue
        share = stack.lost / stack.start
        stack.row.morale = max(0, round(stack.row.morale - share * PERCENT * 0.8))
        if stack.row.morale < rules.morale.rout_morale:
            stack.routed = True
            routs += 1
    if routs:
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = max(0, stack.row.morale - rules.morale.rout_contagion * routs)
                if stack.row.morale < rules.morale.rout_morale:
                    stack.routed = True


def missiles(rules: Rules, shooter: Side, target: Side, ground: Field, families: frozenset[UnitFamily]) -> int:
    damage = sum(
        stack.row.count * stack.spec.missile / PERCENT * modifier(rules, stack, shooter, ground)
        for stack in shooter.stacks
        if stack.alive and stack.spec.family in families and stack.spec.missile > 0
    )
    return deal(target.stacks, damage, rules)


def charge(rules: Rules, rider: Side, target: Side, ground: Field) -> tuple[int, int]:
    braced = sum(stack.row.count for stack in target.stacks if stack.alive and stack.spec.counters_charge)
    present = sum(stack.row.count for stack in target.stacks if stack.alive) or 1
    brace = braced / present
    impact = sum(
        stack.row.count * stack.spec.mass * stack.spec.speed / (PERCENT * NORMAL) * modifier(rules, stack, rider, ground)
        for stack in rider.stacks
        if stack.alive and stack.spec.family in CHARGE_FAMILIES
    )
    dealt = deal(target.stacks, impact * (1 - brace), rules)
    taken = deal([stack for stack in rider.stacks if stack.spec.family in CHARGE_FAMILIES], impact * brace / 2, rules)
    terror = sum(stack.row.count * stack.spec.terror for stack in rider.stacks if stack.alive) / max(1, rider.standing)
    if terror:
        for stack in target.stacks:
            if stack.alive:
                stack.row.morale = max(0, round(stack.row.morale - terror * rules.morale.terror_pct / PERCENT * (1 - stack.row.morale / (2 * PERCENT))))
    return dealt, taken


def reach(rules: Rules, striker: Side, target: Side) -> float:
    if any(stack.alive and (stack.row.kind in FLYERS or stack.spec.missile > 0) for stack in striker.stacks):
        return 1.0
    present = sum(stack.row.count for stack in target.stacks if stack.alive) or 1
    aloft = sum(stack.row.count for stack in target.stacks if stack.alive and stack.row.kind in FLYERS) / present
    return 1 - aloft * (1 - rules.naval.sky_counter_pct / PERCENT)


def melee_round(rules: Rules, first: Side, second: Side, ground: Field) -> tuple[int, int]:
    power_first = sum(stack.row.count * stack.spec.melee / PERCENT * modifier(rules, stack, first, ground) for stack in first.stacks if stack.alive)
    power_second = sum(stack.row.count * stack.spec.melee / PERCENT * modifier(rules, stack, second, ground) for stack in second.stacks if stack.alive)
    to_second = deal(second.stacks, power_first * reach(rules, first, second), rules)
    to_first = deal(first.stacks, power_second * reach(rules, second, first), rules)
    return to_first, to_second


def rites(rules: Rules, side: Side, enemy: Side, ground: Field) -> int:
    priests = sum(stack.row.count for stack in side.stacks if stack.alive and stack.row.kind is UnitKind.PRIESTS)
    if priests:
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = min(PERCENT, stack.row.morale + rules.morale.priests_gain)
    return missiles(rules, side, enemy, ground, frozenset({F.MAGIC}))


def broken(side: Side) -> bool:
    return side.standing <= side.start // 4 or all(not stack.alive for stack in side.stacks)


def pursue(rules: Rules, winner: Side, loser: Side, ground: Field) -> int:
    riders = sum(stack.row.count for stack in winner.stacks if stack.alive and stack.spec.family in CHARGE_FAMILIES)
    reach = min(1.0, 2 * riders / max(1, winner.standing))
    shelter = 0.5 if ground.terrain in SHELTER else 1.0
    fleeing = sum(stack.row.count for stack in loser.stacks)
    losses = round(fleeing * rules.tactics.pursuit_pct / PERCENT * (0.3 + reach) * shelter)
    taken = 0
    for stack in sorted(loser.stacks, key=lambda item: -item.row.count):
        part = min(stack.row.count, round(losses * stack.row.count / max(1, fleeing)))
        stack.row.count -= part
        stack.lost += part
        taken += part
    loser.pursuit_lost = taken
    loser.captives = round(taken * rules.tactics.captive_pct / PERCENT)
    return taken


def classify(rules: Rules, winner: Side, loser: Side, ratio: float) -> OutcomeClass:
    table = rules.tactics
    if loser.start and loser.pursuit_lost >= loser.start * table.massacre_pct / PERCENT:
        return OutcomeClass.MASSACRE
    if winner.start and winner.lost >= winner.start * table.pyrrhic_pct / PERCENT:
        return OutcomeClass.PYRRHIC
    if ratio * PERCENT >= table.decisive_ratio_pct:
        return OutcomeClass.DECISIVE
    if all(not stack.alive for stack in loser.stacks):
        return OutcomeClass.ROUT
    if ratio < 1.15:
        return OutcomeClass.STALEMATE
    return OutcomeClass.VICTORY


def opening(rules: Rules, rng: SeededRandom, attacker: Side, defender: Side, ground: Field) -> tuple[Side | None, list[PhaseLog]]:
    table = rules.tactics
    eyes_a, eyes_d = scouting(attacker), scouting(defender)
    lead = attacker if eyes_a > eyes_d else defender
    other = defender if lead is attacker else attacker
    margin = abs(eyes_a - eyes_d) / max(1.0, eyes_a, eyes_d) * PERCENT
    refused = False
    if margin >= table.scouting_margin:
        if strength(rules, lead, ground) < strength(rules, other, ground) * REFUSE_RATIO:
            refused = True
        elif ground.terrain in AMBUSH_TERRAIN or ground.weather is WeatherKind.FOG or ground.night:
            lead.surprise = rules.weather_battle_effects.fog_ambush_pct / PERCENT
    phases = [PhaseLog(BattlePhase.SCOUTING, 0, 0, f"{lead.entity.name} saw further" + (" and refused battle" if refused else ""), {"margin": round(margin)})]
    if refused:
        return lead, phases
    attacker.tactic = choose_tactic(rules, rng, attacker, defender.profile.doctrine, ground)
    defender.tactic = choose_tactic(rules, rng, defender, attacker.profile.doctrine, ground)
    attacker.tactic_factor = tactic_factor(rules, attacker.tactic, defender.tactic, ground)
    defender.tactic_factor = tactic_factor(rules, defender.tactic, attacker.tactic, ground)
    summary = f"{attacker.tactic.value.replace('_', ' ')} against {defender.tactic.value.replace('_', ' ')}"
    phases.append(PhaseLog(BattlePhase.PLAN, 0, 0, summary, {"attacker": attacker.tactic.value, "defender": defender.tactic.value}))
    return None, phases


def fighting(rules: Rules, attacker: Side, defender: Side, ground: Field) -> list[PhaseLog]:
    ranged = MISSILE_FAMILIES - {F.MAGIC}
    to_d, to_a = missiles(rules, attacker, defender, ground, ranged), missiles(rules, defender, attacker, ground, ranged)
    phases = [PhaseLog(BattlePhase.MISSILE, to_a, to_d, "the volleys flew")]
    attacker.surprise = defender.surprise = 1.0
    dealt_a, taken_a = charge(rules, attacker, defender, ground)
    dealt_d, taken_d = charge(rules, defender, attacker, ground)
    phases.append(PhaseLog(BattlePhase.CHARGE, taken_a + dealt_d, dealt_a + taken_d, "the horse and the beasts struck"))
    shaken(rules, attacker)
    shaken(rules, defender)
    for index in range(rules.tactics.melee_rounds):
        lost_a, lost_d = melee_round(rules, attacker, defender, ground)
        shaken(rules, attacker)
        shaken(rules, defender)
        phases.append(PhaseLog(BattlePhase.MELEE, lost_a, lost_d, f"melee, round {index + 1}"))
        if broken(attacker) or broken(defender):
            break
    magic_a, magic_d = rites(rules, attacker, defender, ground), rites(rules, defender, attacker, ground)
    phases.append(PhaseLog(BattlePhase.RITES, magic_d, magic_a, "rites and prayers"))
    return phases


def victor(rules: Rules, attacker: Side, defender: Side, ground: Field) -> tuple[Side, Side, float, float]:
    power_a, power_d = strength(rules, attacker, ground), strength(rules, defender, ground)
    winner, loser = (attacker, defender) if power_a >= power_d else (defender, attacker)
    if broken(attacker) != broken(defender):
        winner, loser = (defender, attacker) if broken(attacker) else (attacker, defender)
    return winner, loser, max(power_a, power_d), max(1.0, min(power_a, power_d))


def aftermath(rules: Rules, winner: Side, loser: Side, gap: float) -> tuple[dict[int, int], dict[int, int], dict[str, int]]:
    table, campaigns = rules.tactics, rules.campaigns
    wounded = {side.entity.id: round(side.lost * table.wounded_pct / PERCENT) for side in (winner, loser)}
    maimed = {side.entity.id: round(side.lost * rules.maimed.return_pct / PERCENT) for side in (winner, loser)}
    by_kind: dict[str, int] = {}
    for side in (winner, loser):
        gained = campaigns.winner_experience_gain if side is winner else campaigns.loser_experience_gain
        for stack in side.stacks:
            by_kind[stack.row.kind.value] = by_kind.get(stack.row.kind.value, 0) + stack.lost
            stack.row.wounded += round(stack.lost * table.wounded_pct / PERCENT)
            stack.row.experience = min(PERCENT, stack.row.experience + gained)
            if stack.routed:
                stack.row.morale = max(stack.row.morale, rules.morale.rout_morale // 2)
    for stack in winner.stacks:
        stack.row.morale = min(PERCENT, stack.row.morale + campaigns.winner_morale_gain)
    beaten = campaigns.loser_morale_loss + round(gap / campaigns.loser_morale_diff_divisor)
    for stack in loser.stacks:
        stack.row.morale = max(0, stack.row.morale - beaten)
    return wounded, maimed, by_kind


def resolve(rules: Rules, rng: SeededRandom, attacker: Side, defender: Side, ground: Field) -> BattleResult:
    refuser, phases = opening(rules, rng, attacker, defender, ground)
    if refuser is not None:
        holder = defender if refuser is attacker else attacker
        return BattleResult(attacker, defender, holder, refuser, True, OutcomeClass.REFUSED, 0.0, phases, {}, {}, {})
    phases.extend(fighting(rules, attacker, defender, ground))
    winner, loser, strong, weak = victor(rules, attacker, defender, ground)
    pursued = pursue(rules, winner, loser, ground)
    phases.append(PhaseLog(BattlePhase.PURSUIT, pursued if loser is attacker else 0, pursued if loser is defender else 0, f"{winner.entity.name} pursued"))
    outcome = classify(rules, winner, loser, strong / weak)
    gap = min(PERCENT, (strong - weak) / strong * PERCENT) if strong else 0.0
    wounded, maimed, by_kind = aftermath(rules, winner, loser, gap)
    phases.append(
        PhaseLog(BattlePhase.AFTERMATH, attacker.lost, defender.lost, outcome.value, {"wounded": sum(wounded.values()), "maimed": sum(maimed.values())})
    )
    return BattleResult(attacker, defender, winner, loser, False, outcome, gap, phases, wounded, maimed, by_kind)


def make_stacks(rows: list[ArmyUnitRow]) -> list[Stack]:
    return [Stack(row, UNITS[row.kind], row.count) for row in rows if row.count > 0]
