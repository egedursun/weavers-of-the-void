from collections.abc import Callable
from dataclasses import dataclass, field

from aerona.catalog.units import (
    AMBUSH_TERRAIN,
    ARMOUR_DEFENCE,
    BURROWERS,
    HEAVY_WEATHER,
    SHIELD_DEFENCE,
    STYLE_TACTICS,
    TACTIC_TERRAIN,
    UNITS,
    WEAPON_EDGE,
    UnitSpec,
)
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.environment import PlaceCover, TerrainKind, WeatherKind
from aerona.domain.enums.military import ArmourType, BattlePhase, CommanderTrait, OutcomeClass, Tactic, UnitFamily, UnitKind
from aerona.domain.enums.mortal import HarshnessScale
from aerona.engine.environment.battleground import cover_missile_pct
from aerona.engine.military.tables import counters, defender_cell, matchup, terrain_cell, unit_terrain, weather_cell
from aerona.engine.primitives.harshness import harshness
from aerona.rules.registry import Rules

F = UnitFamily
MISSILE_FAMILIES = frozenset({F.MISSILE, F.MAGIC, F.ENGINEER})
CHARGE_FAMILIES = frozenset({F.MOUNTED, F.BEAST})
SWIFT_FAMILIES = frozenset({F.MOUNTED, F.BEAST})
FLYERS = frozenset({UnitKind.SKY_MOUNTS, UnitKind.SKYSHIPS})
SCOUTS = frozenset({UnitKind.LIGHT_CAVALRY, UnitKind.SKIRMISHERS, UnitKind.HORSE_ARCHERS, UnitKind.SKY_MOUNTS})
SHELTER = frozenset({TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.MOUNTAINS, TerrainKind.MARSH, TerrainKind.HIGH_PASS})
NARROW = frozenset({TerrainKind.CANYON, TerrainKind.HIGH_PASS, TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.URBAN, TerrainKind.UNDERGROUND})
HIGHLANDS = frozenset({TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
RAIN = frozenset({WeatherKind.RAIN, WeatherKind.DOWNPOUR, WeatherKind.STORM})
SNOW = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})
WIND = frozenset({WeatherKind.STORM, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
HEAVY = frozenset({ArmourType.MAIL, ArmourType.SCALE, ArmourType.PLATE})
BOWS = frozenset({UnitKind.ARCHERS, UnitKind.HORSE_ARCHERS})
CROSSBOWS = frozenset({UnitKind.CROSSBOWMEN})
FIRE_CASTERS = frozenset({UnitKind.WAR_MAGES})
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
Streams = Callable[[str], SeededRandom]


@dataclass
class Stack:
    row: ArmyUnitRow
    spec: UnitSpec
    start: int
    routed: bool = False
    lost: int = 0
    hardness: int = NORMAL
    raised: bool = False

    @property
    def alive(self) -> bool:
        return self.row.count > 0 and not self.routed

    @property
    def armour(self) -> int:
        return self.spec.defence + ARMOUR_DEFENCE[self.row.armour] + SHIELD_DEFENCE[self.row.shield] + (HELMET if self.row.helmet else 0)

    @property
    def flying(self) -> bool:
        return self.row.kind in FLYERS or self.spec.flying


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
    watch: float = 0.0
    veteran: float = 0.0
    leadership: int = 0
    tactic: Tactic = Tactic.HOLD_LINE
    tactic_factor: float = 1.0
    surprise: float = 1.0
    pursuit_lost: int = 0
    captives: int = 0
    willpower: int = 0
    learned: dict[Tactic, int] = field(default_factory=dict)
    morale_parts: dict[str, int] = field(default_factory=dict)
    wing_bonus: float = 0.0
    flanking: bool = False
    luck: float = 1.0
    fog: bool = False
    baggage_taken: int = 0
    healed: int = 0
    raised_dead: int = 0
    backlash: int = 0
    terror_dealt: int = 0
    medicine: int = 0
    priests_healing: bool = True

    @property
    def start(self) -> int:
        return sum(stack.start for stack in self.stacks)

    @property
    def standing(self) -> int:
        return sum(stack.row.count for stack in self.stacks if stack.alive)

    @property
    def lost(self) -> int:
        return sum(stack.lost for stack in self.stacks)

    def count_of(self, kind: UnitKind) -> int:
        return sum(stack.row.count for stack in self.stacks if stack.alive and stack.row.kind is kind)


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
    factors: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Field:
    terrain: TerrainKind | None
    weather: WeatherKind | None
    night: bool
    river: bool = False
    bridge: bool = False
    ford: bool = False
    cover: PlaceCover | None = None


def weather_now(side: Side, enemy: Side, ground: Field) -> WeatherKind | None:
    return WeatherKind.FOG if side.fog or enemy.fog else ground.weather


def terrain_factor(rules: Rules, stack: Stack, side: Side, ground: Field) -> float:
    if stack.flying:
        return rules.battle_terrain.sky_terrain_pct / PERCENT
    terrain = 1 + (terrain_cell(rules, ground.terrain, stack.spec.family) - 1) * rules.terrain_effects.strength_pct / PERCENT
    terrain *= unit_terrain(rules, stack.row.kind, ground.terrain, stack.spec.terrain)
    if ground.terrain is TerrainKind.MARSH and stack.row.armour in HEAVY:
        terrain *= rules.battle_terrain.marsh_heavy_armour_pct / PERCENT
    if ground.terrain is TerrainKind.UNDERGROUND and stack.row.kind in BURROWERS:
        terrain *= rules.battle_terrain.burrower_underground_pct / PERCENT
    if ground.terrain in HIGHLANDS and stack.row.kind is UnitKind.SIEGE_ENGINES:
        terrain *= rules.battle_terrain.mountain_engines_pct / PERCENT
    return terrain


def weather_factor(rules: Rules, stack: Stack, weather: WeatherKind | None) -> float:
    factor = 1 + (weather_cell(rules, weather, stack.spec.family) - 1) * rules.weather_battle_effects.strength_pct / PERCENT
    if weather in RAIN and stack.row.kind in BOWS:
        factor *= rules.battle_weather.rain_bow_pct / PERCENT
    elif weather in RAIN and stack.row.kind in CROSSBOWS:
        factor *= rules.battle_weather.rain_crossbow_pct / PERCENT
    if weather in WIND and stack.spec.missile > 0 and stack.spec.family is F.MISSILE:
        factor *= rules.battle_weather.wind_missile_pct / PERCENT
    if stack.row.kind in FIRE_CASTERS:
        if weather in RAIN:
            factor *= rules.battle_weather.rain_fire_rites_pct / PERCENT
        if weather in WIND:
            factor *= rules.battle_weather.wind_fire_pct / PERCENT
    return factor


def crossing_factor(rules: Rules, side: Side, ground: Field) -> float:
    if not ground.river or side.defending:
        return 1.0
    if ground.bridge:
        return rules.battle_terrain.bridge_crossing_pct / PERCENT
    if ground.ford:
        return rules.battle_terrain.ford_crossing_pct / PERCENT
    return rules.terrain_effects.river_crossing_pct / PERCENT


def arms_factor(rules: Rules, stack: Stack) -> float:
    magic = rules.battle_magic
    worn = magic.condition_floor_pct / PERCENT + (1 - magic.condition_floor_pct / PERCENT) * stack.row.condition / PERCENT
    hardness = 1 + (stack.hardness - NORMAL) / PERCENT * magic.material_hardness_pct / PERCENT
    return worn * max(0.5, hardness)


def modifier(rules: Rules, stack: Stack, side: Side, ground: Field, enemy: Side | None = None) -> float:
    row = stack.row
    weather = weather_now(side, enemy, ground) if enemy is not None else ground.weather
    heavy = row.armour in HEAVY
    fatigue = row.fatigue * (rules.weather_battle_effects.heavy_fatigue_pct / PERCENT if heavy and weather in HEAVY_WEATHER else 1.0)
    quality = row.quality / NORMAL * (1 + row.experience / PERCENT * rules.military_units.experience_pct / PERCENT) * (1 + side.veteran + side.wing_bonus)
    vigour = max(0.2, 1 - fatigue / (2 * PERCENT)) * (0.5 + min(PERCENT, row.morale + side.leadership) / PERCENT)
    height = 1.0
    if side.defending:
        height = 1 + (defender_cell(rules, ground.terrain) - 1) * rules.terrain_effects.defender_height_pct / PERCENT
        if weather in SNOW:
            height *= rules.battle_weather.snow_defender_pct / PERCENT
    dug = 1 + side.profile.entrenchment / PERCENT * rules.logistics.entrench_defence_pct / PERCENT if side.defending else 1.0
    learned = 1 + min(rules.battle_magic.learned_tactic_cap, side.learned.get(side.tactic, 0) * rules.battle_magic.learned_tactic_pct) / PERCENT
    return (
        quality
        * vigour
        * terrain_factor(rules, stack, side, ground)
        * weather_factor(rules, stack, weather)
        * called_fog(rules, stack, side, enemy)
        * arms_factor(rules, stack)
        * height
        * dug
        * crossing_factor(rules, side, ground)
        * side.edge
        * side.tactic_factor
        * side.surprise
        * side.luck
        * learned
    )


def called_fog(rules: Rules, stack: Stack, side: Side, enemy: Side | None) -> float:
    if enemy is None or not (side.fog or enemy.fog) or stack.spec.family is not F.MISSILE:
        return 1.0
    return rules.battle_magic.fog_missile_pct / PERCENT


def cast_luck(rules: Rules, streams: Streams, *sides: Side) -> None:
    table = rules.campaigns
    for side in sides:
        side.luck = 1 + streams(f"luck.{side.entity.id}").die(table.battle_die) * table.battle_die_mult / PERCENT


def strength(rules: Rules, side: Side, ground: Field) -> float:
    return sum(
        stack.row.count * (stack.spec.melee + stack.spec.missile + stack.armour) / 3 * modifier(rules, stack, side, ground)
        for stack in side.stacks
        if stack.alive
    )


def scouting(side: Side) -> float:
    eyes = sum(stack.row.count * stack.spec.speed / PERCENT for stack in side.stacks if stack.alive and stack.row.kind in SCOUTS)
    return eyes + side.skill * 10 + side.intel + side.watch


def choose_tactic(rules: Rules, rng: SeededRandom, side: Side, enemy_doctrine: str, ground: Field) -> Tactic:
    if side.profile.tactic is not None:
        return side.profile.tactic
    options = list(dict.fromkeys([*STYLE_TACTICS.get(side.profile.doctrine, GENERIC), *GENERIC, *side.learned]))
    for trait in side.traits:
        options.extend(item for item in TRAIT_TACTICS.get(trait, ()) if item not in options)
    expected = STYLE_TACTICS.get(enemy_doctrine, GENERIC)[0]
    weights = []
    for option in options:
        weight = 1.0 + side.learned.get(option, 0) * rules.battle_magic.learned_tactic_pct / PERCENT * 5
        if ground.terrain is not None and option in TACTIC_TERRAIN:
            weight *= 2.0 if ground.terrain in TACTIC_TERRAIN[option] else 0.4
        if counters(option, expected):
            weight *= 1 + side.skill * rules.tactics.skill_weight / 10
        if option is Tactic.AMBUSH and not (
            ground.terrain in AMBUSH_TERRAIN or ground.cover is PlaceCover.HEAVY or ground.weather is WeatherKind.FOG or ground.night
        ):
            weight *= 0.1
        if option is Tactic.NIGHT_RAID and not ground.night:
            weight *= 0.1
        if any(option in TRAIT_TACTICS.get(trait, ()) for trait in side.traits):
            weight *= 2.0
        weights.append(weight)
    return rng.weighted(options, weights)


def tactic_factor(rules: Rules, mine: Tactic, theirs: Tactic, ground: Field) -> float:
    table = rules.tactics
    factor = matchup(rules, mine, theirs)
    if counters(theirs, mine):
        factor *= table.countered_pct / PERCENT
    if ground.terrain is not None and mine in TACTIC_TERRAIN:
        factor *= (table.terrain_pct if ground.terrain in TACTIC_TERRAIN[mine] else table.misplaced_pct) / PERCENT
    return factor


def fortune(rules: Rules, streams: Streams, phase: str, stack: Stack) -> float:
    spread = rules.tactics.fortune_pct / PERCENT
    return 1 + streams(f"{phase}.{stack.row.id}").uniform(-spread, spread)


def deal(targets: list[Stack], damage: float, rules: Rules, *, piercing: float = 0.0) -> int:
    alive = [stack for stack in targets if stack.alive]
    total = sum(stack.row.count for stack in alive)
    if total <= 0 or damage <= 0:
        return 0
    killed = 0
    for stack in alive:
        share = stack.row.count / total
        armour = stack.armour * (1 - piercing if stack.row.armour in HEAVY else 1)
        harsh = harshness(rules, HarshnessScale.BATTLE_LOSS)
        losses = min(stack.row.count, int(damage * share * rules.tactics.loss_scale_pct / PERCENT * NORMAL / max(10, armour) * harsh))
        stack.row.count -= losses
        stack.lost += losses
        killed += losses
    return killed


def piercing_of(rules: Rules, stacks: list[Stack]) -> float:
    total = sum(stack.row.count for stack in stacks if stack.alive) or 1
    edged = sum(stack.row.count * max((WEAPON_EDGE.get(weapon, 0) for weapon in stack.row.weapons), default=0) for stack in stacks if stack.alive)
    return min(1.0, edged / total / PERCENT) * rules.battle_magic.weapon_vs_armour_pct / PERCENT


def resist(rules: Rules, side: Side, shock: float) -> float:
    return shock * max(0.0, 1 - side.willpower / PERCENT * rules.battle_magic.willpower_pct / PERCENT)


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
                stack.row.morale = max(0, stack.row.morale - round(resist(rules, side, rules.morale.rout_contagion * routs)))
                if stack.row.morale < rules.morale.rout_morale:
                    stack.routed = True


def missiles(rules: Rules, streams: Streams, shooter: Side, target: Side, ground: Field, *, families: frozenset[UnitFamily]) -> int:
    coastal = ground.terrain is TerrainKind.COAST
    damage = 0.0
    for stack in shooter.stacks:
        if not stack.alive or stack.spec.missile <= 0:
            continue
        if stack.spec.family in families:
            share = 1.0
        elif coastal and stack.spec.family is F.NAVAL:
            share = rules.battle_terrain.coastal_fleet_support_pct / PERCENT
        else:
            continue
        damage += (
            stack.row.count * stack.spec.missile / PERCENT * modifier(rules, stack, shooter, ground, target) * share * fortune(rules, streams, "missile", stack)
        )
    if target.defending:
        damage *= cover_missile_pct(rules, ground.cover) / PERCENT
    return deal(target.stacks, damage, rules, piercing=piercing_of(rules, shooter.stacks))


def charge(rules: Rules, streams: Streams, rider: Side, target: Side, ground: Field) -> tuple[int, int]:
    present = sum(stack.row.count for stack in target.stacks if stack.alive) or 1
    braced = sum(
        stack.row.count * (1 + (rules.battle_magic.spear_charge_pct / PERCENT if {"spear", "pike"} & set(stack.row.weapons) else 0))
        for stack in target.stacks
        if stack.alive and (stack.spec.counters_charge or {"spear", "pike"} & set(stack.row.weapons))
    )
    brace = min(1.0, braced / present)
    impact = sum(
        stack.row.count
        * stack.spec.mass
        * stack.spec.speed
        / (PERCENT * NORMAL)
        * modifier(rules, stack, rider, ground, target)
        * fortune(rules, streams, "charge", stack)
        for stack in rider.stacks
        if stack.alive and stack.spec.family in CHARGE_FAMILIES
    )
    dealt = deal(target.stacks, impact * (1 - brace), rules)
    taken = deal([stack for stack in rider.stacks if stack.spec.family in CHARGE_FAMILIES], impact * brace / 2, rules)
    terror = sum(stack.row.count * stack.spec.terror for stack in rider.stacks if stack.alive) / max(1, rider.standing)
    if terror:
        frighten(rules, target, terror * rules.morale.terror_pct / PERCENT)
    return dealt, taken


def frighten(rules: Rules, target: Side, shock: float) -> int:
    felt = resist(rules, target, shock)
    for stack in target.stacks:
        if stack.alive:
            stack.row.morale = max(0, round(stack.row.morale - felt * (1 - stack.row.morale / (2 * PERCENT))))
    return round(felt)


def reach(rules: Rules, striker: Side, target: Side) -> float:
    if any(stack.alive and (stack.flying or stack.spec.missile > 0) for stack in striker.stacks):
        return 1.0
    present = sum(stack.row.count for stack in target.stacks if stack.alive) or 1
    aloft = sum(stack.row.count for stack in target.stacks if stack.alive and stack.flying) / present
    return 1 - aloft * (1 - rules.naval.sky_counter_pct / PERCENT)


def melee_round(rules: Rules, streams: Streams, first: Side, second: Side, ground: Field, *, index: int) -> tuple[int, int]:
    power_first = sum(
        stack.row.count * stack.spec.melee / PERCENT * modifier(rules, stack, first, ground, second) * fortune(rules, streams, f"melee{index}", stack)
        for stack in first.stacks
        if stack.alive
    )
    power_second = sum(
        stack.row.count * stack.spec.melee / PERCENT * modifier(rules, stack, second, ground, first) * fortune(rules, streams, f"melee{index}", stack)
        for stack in second.stacks
        if stack.alive
    )
    to_second = deal(second.stacks, power_first * reach(rules, first, second), rules, piercing=piercing_of(rules, first.stacks))
    to_first = deal(first.stacks, power_second * reach(rules, second, first), rules, piercing=piercing_of(rules, second.stacks))
    return to_first, to_second


def frontage(rules: Rules, ground: Field) -> float:
    return rules.battle_magic.narrow_frontage_pct / PERCENT if ground.terrain in NARROW else 1.0


def swift_speed(side: Side) -> float:
    swift = [stack for stack in side.stacks if stack.alive and stack.spec.family in SWIFT_FAMILIES]
    total = sum(stack.row.count for stack in swift)
    return sum(stack.row.count * stack.spec.speed for stack in swift) / total if total else 0.0


def outflank(rules: Rules, first: Side, second: Side, ground: Field) -> PhaseLog | None:
    table = rules.battle_magic
    room = frontage(rules, ground)
    for flanker, line in ((first, second), (second, first)):
        wide = flanker.standing * room > line.standing
        swift = swift_speed(flanker) - swift_speed(line) >= table.flank_speed_lead
        if wide and swift and not flanker.flanking:
            flanker.flanking = True
            flanker.tactic_factor *= 1 + table.flank_pct / PERCENT
            return PhaseLog(BattlePhase.CHARGE, 0, 0, f"{flanker.entity.name} turned the flank", {"flank": flanker.entity.name})
    return None


def call_fog(rules: Rules, streams: Streams, caster: Side, enemy: Side) -> bool:
    mages = caster.count_of(UnitKind.WAR_MAGES)
    shooters = sum(stack.row.count for stack in enemy.stacks if stack.alive and stack.spec.family is F.MISSILE)
    mine = sum(stack.row.count for stack in caster.stacks if stack.alive and stack.spec.family is F.MISSILE)
    if mages <= 0 or shooters <= mine:
        return False
    if streams(f"fog.{caster.entity.id}").chance(rules.battle_magic.fog_chance):
        caster.fog = True
        caster.surprise = max(caster.surprise, rules.weather_battle_effects.fog_ambush_pct / PERCENT if caster.tactic is Tactic.AMBUSH else 1.0)
        return True
    return False


def terror_rite(rules: Rules, caster: Side, enemy: Side) -> int:
    mages = caster.count_of(UnitKind.WAR_MAGES) + caster.count_of(UnitKind.NECROMANCERS)
    if mages <= 0:
        return 0
    density = min(1.0, mages * PERCENT / max(1, caster.standing) / rules.battle_magic.terror_mages_per_100)
    caster.terror_dealt = frighten(rules, enemy, rules.battle_magic.terror_rite * density)
    return caster.terror_dealt


def backlash(rules: Rules, side: Side, ground: Field) -> int:
    if ground.weather is not WeatherKind.MAGIC_STORM:
        return 0
    lost = 0
    for stack in side.stacks:
        if stack.alive and stack.row.kind is UnitKind.WAR_MAGES:
            part = round(stack.row.count * rules.battle_weather.magic_storm_backlash_pct / PERCENT)
            stack.row.count -= part
            stack.lost += part
            lost += part
    side.backlash = lost
    return lost


def rites(rules: Rules, streams: Streams, side: Side, enemy: Side, ground: Field) -> int:
    if side.count_of(UnitKind.PRIESTS):
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = min(PERCENT, stack.row.morale + rules.morale.priests_gain)
    return missiles(rules, streams, side, enemy, ground, families=frozenset({F.MAGIC}))


def broken(side: Side) -> bool:
    return side.standing <= side.start // 4 or all(not stack.alive for stack in side.stacks)


def pursue(rules: Rules, winner: Side, loser: Side, ground: Field) -> int:
    riders = sum(stack.row.count for stack in winner.stacks if stack.alive and stack.spec.family in CHARGE_FAMILIES)
    span = min(1.0, 2 * riders / max(1, winner.standing))
    shelter = 0.5 if ground.terrain in SHELTER else 1.0
    fleeing = sum(stack.row.count for stack in loser.stacks)
    losses = round(fleeing * rules.tactics.pursuit_pct / PERCENT * (0.3 + span) * shelter * harshness(rules, HarshnessScale.BATTLE_LOSS))
    taken = 0
    for stack in sorted(loser.stacks, key=lambda item: -item.row.count):
        part = min(stack.row.count, round(losses * stack.row.count / max(1, fleeing)))
        stack.row.count -= part
        stack.lost += part
        taken += part
    loser.pursuit_lost = taken
    loser.captives = round(taken * rules.tactics.captive_pct / PERCENT)
    winner.baggage_taken = round((loser.profile.baggage + loser.profile.loot) * rules.battle_magic.baggage_capture_pct / PERCENT * (0.3 + span) * shelter)
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
    if ratio * PERCENT < table.stalemate_ratio_pct:
        return OutcomeClass.STALEMATE
    return OutcomeClass.VICTORY


def opening(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> tuple[Side | None, list[PhaseLog]]:
    table = rules.tactics
    eyes_a, eyes_d = scouting(attacker), scouting(defender)
    lead = attacker if eyes_a > eyes_d else defender
    other = defender if lead is attacker else attacker
    margin = abs(eyes_a - eyes_d) / max(1.0, eyes_a, eyes_d) * PERCENT
    refused = False
    if margin >= table.scouting_margin:
        if strength(rules, lead, ground) < strength(rules, other, ground) * REFUSE_RATIO:
            refused = True
        else:
            lead.defending, other.defending = True, False
            if ground.terrain in AMBUSH_TERRAIN or ground.cover is PlaceCover.HEAVY or ground.weather is WeatherKind.FOG or ground.night:
                lead.surprise = rules.weather_battle_effects.fog_ambush_pct / PERCENT
    summary = f"{lead.entity.name} saw further" + (" and refused battle" if refused else " and chose the ground")
    phases = [PhaseLog(BattlePhase.SCOUTING, 0, 0, summary, {"margin": round(margin), "ground": lead.entity.name})]
    if refused:
        return lead, phases
    attacker.tactic = choose_tactic(rules, streams("plan.attacker"), attacker, defender.profile.doctrine, ground)
    defender.tactic = choose_tactic(rules, streams("plan.defender"), defender, attacker.profile.doctrine, ground)
    attacker.tactic_factor = tactic_factor(rules, attacker.tactic, defender.tactic, ground)
    defender.tactic_factor = tactic_factor(rules, defender.tactic, attacker.tactic, ground)
    details: dict[str, int | str] = {
        "attacker": attacker.tactic.value,
        "defender": defender.tactic.value,
        "attacker_factor": round(attacker.tactic_factor * PERCENT),
        "defender_factor": round(defender.tactic_factor * PERCENT),
        "countered": attacker.entity.name
        if counters(defender.tactic, attacker.tactic)
        else defender.entity.name
        if counters(attacker.tactic, defender.tactic)
        else "",
    }
    summary = f"{attacker.tactic.value.replace('_', ' ')} against {defender.tactic.value.replace('_', ' ')}"
    phases.append(PhaseLog(BattlePhase.PLAN, 0, 0, summary, details))
    return None, phases


def fighting(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> list[PhaseLog]:
    fog = [side.entity.name for side, enemy in ((attacker, defender), (defender, attacker)) if call_fog(rules, streams, side, enemy)]
    ranged = MISSILE_FAMILIES - {F.MAGIC}
    to_d, to_a = missiles(rules, streams, attacker, defender, ground, families=ranged), missiles(rules, streams, defender, attacker, ground, families=ranged)
    phases = [PhaseLog(BattlePhase.MISSILE, to_a, to_d, "the volleys flew" + (" into a called fog" if fog else ""), {"fog": ", ".join(fog)})]
    attacker.surprise = defender.surprise = 1.0
    flank = outflank(rules, attacker, defender, ground)
    if flank is not None:
        phases.append(flank)
    dealt_a, taken_a = charge(rules, streams, attacker, defender, ground)
    dealt_d, taken_d = charge(rules, streams, defender, attacker, ground)
    phases.append(PhaseLog(BattlePhase.CHARGE, taken_a + dealt_d, dealt_a + taken_d, "the horse and the beasts struck"))
    shaken(rules, attacker)
    shaken(rules, defender)
    for index in range(rules.tactics.melee_rounds):
        lost_a, lost_d = melee_round(rules, streams, attacker, defender, ground, index=index)
        shaken(rules, attacker)
        shaken(rules, defender)
        phases.append(PhaseLog(BattlePhase.MELEE, lost_a, lost_d, f"melee, round {index + 1}"))
        if broken(attacker) or broken(defender):
            break
    burn_a, burn_d = backlash(rules, attacker, ground), backlash(rules, defender, ground)
    terror = {"attacker_terror": terror_rite(rules, attacker, defender), "defender_terror": terror_rite(rules, defender, attacker)}
    magic_a, magic_d = rites(rules, streams, attacker, defender, ground), rites(rules, streams, defender, attacker, ground)
    phases.append(PhaseLog(BattlePhase.RITES, magic_d + burn_a, magic_a + burn_d, "rites and prayers", {**terror, "backlash": burn_a + burn_d}))
    return phases


def victor(rules: Rules, attacker: Side, defender: Side, ground: Field) -> tuple[Side, Side, float, float]:
    power_a, power_d = strength(rules, attacker, ground), strength(rules, defender, ground)
    winner, loser = (attacker, defender) if power_a >= power_d else (defender, attacker)
    if broken(attacker) != broken(defender):
        winner, loser = (defender, attacker) if broken(attacker) else (attacker, defender)
    return winner, loser, max(power_a, power_d), max(1.0, min(power_a, power_d))


def treat(rules: Rules, side: Side, wounded: int) -> int:
    magic = rules.battle_magic
    healed = min(wounded, side.count_of(UnitKind.PRIESTS) * magic.heal_per_priest) if side.priests_healing else 0
    rest = wounded - healed
    saved = round(rest * min(PERCENT, side.medicine) / PERCENT * magic.medicine_pct / PERCENT)
    dying = round((rest - saved) * magic.untreated_death_pct / PERCENT)
    side.healed = healed
    return max(0, wounded - dying)


def raise_dead(rules: Rules, side: Side, fallen: int) -> int:
    necromancers = side.count_of(UnitKind.NECROMANCERS)
    if necromancers <= 0:
        return 0
    side.raised_dead = min(round(fallen * rules.battle_magic.raise_dead_pct / PERCENT), necromancers * rules.battle_magic.raise_per_necromancer)
    return side.raised_dead


def aftermath(rules: Rules, winner: Side, loser: Side, gap: float) -> tuple[dict[int, int], dict[int, int], dict[str, int]]:
    table, campaigns = rules.tactics, rules.campaigns
    wounded: dict[int, int] = {}
    maimed: dict[int, int] = {}
    by_kind: dict[str, int] = {}
    fallen = winner.lost + loser.lost
    for side in (winner, loser):
        hurt = round(side.lost * table.wounded_pct / PERCENT)
        wounded[side.entity.id] = treat(rules, side, hurt)
        maimed[side.entity.id] = round(side.lost * rules.maimed.return_pct / PERCENT)
        raise_dead(rules, side, fallen)
        gained = campaigns.winner_experience_gain if side is winner else campaigns.loser_experience_gain
        for stack in side.stacks:
            by_kind[stack.row.kind.value] = by_kind.get(stack.row.kind.value, 0) + stack.lost
            stack.row.wounded += round(stack.lost * table.wounded_pct / PERCENT)
            stack.row.experience = min(PERCENT, stack.row.experience + gained)
            stack.row.condition = max(0, stack.row.condition - rules.battle_magic.wear_per_battle)
            if stack.routed:
                stack.row.morale = max(stack.row.morale, rules.morale.rout_morale // 2)
    for stack in winner.stacks:
        stack.row.morale = min(PERCENT, stack.row.morale + campaigns.winner_morale_gain)
    beaten = campaigns.loser_morale_loss + round(gap / campaigns.loser_morale_diff_divisor)
    for stack in loser.stacks:
        stack.row.morale = max(0, stack.row.morale - beaten)
    return wounded, maimed, by_kind


def resolve(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> BattleResult:
    cast_luck(rules, streams, attacker, defender)
    refuser, phases = opening(rules, streams, attacker, defender, ground)
    if refuser is not None:
        holder = defender if refuser is attacker else attacker
        return BattleResult(attacker, defender, holder, refuser, True, OutcomeClass.REFUSED, 0.0, phases, {}, {}, {})
    phases.extend(fighting(rules, streams, attacker, defender, ground))
    winner, loser, strong, weak = victor(rules, attacker, defender, ground)
    pursued = pursue(rules, winner, loser, ground)
    details: dict[str, int | str] = {"baggage": winner.baggage_taken}
    phases.append(
        PhaseLog(BattlePhase.PURSUIT, pursued if loser is attacker else 0, pursued if loser is defender else 0, f"{winner.entity.name} pursued", details)
    )
    outcome = classify(rules, winner, loser, strong / weak)
    gap = min(PERCENT, (strong - weak) / strong * PERCENT) if strong else 0.0
    wounded, maimed, by_kind = aftermath(rules, winner, loser, gap)
    summary = {
        "wounded": sum(wounded.values()),
        "maimed": sum(maimed.values()),
        "healed": attacker.healed + defender.healed,
        "raised": attacker.raised_dead + defender.raised_dead,
    }
    phases.append(PhaseLog(BattlePhase.AFTERMATH, attacker.lost, defender.lost, outcome.value, dict(summary)))
    factors = {
        "attacker": round(attacker.tactic_factor, 3),
        "defender": round(defender.tactic_factor, 3),
        "attacker_flank": float(attacker.flanking),
        "attacker_luck": round(attacker.luck, 3),
        "defender_luck": round(defender.luck, 3),
        "defender_flank": float(defender.flanking),
    }
    return BattleResult(attacker, defender, winner, loser, False, outcome, gap, phases, wounded, maimed, by_kind, factors)


def make_stacks(rows: list[ArmyUnitRow], specs: dict[int, UnitSpec] | None = None, hardness: dict[str, int] | None = None) -> list[Stack]:
    found = []
    for row in rows:
        if row.count <= 0:
            continue
        spec = (specs or {}).get(row.design_id or 0) or UNITS[row.kind]
        found.append(Stack(row, spec, row.count, hardness=(hardness or {}).get(row.material or "", NORMAL)))
    return found
