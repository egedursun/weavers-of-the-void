from collections.abc import Callable
from dataclasses import dataclass, field

from aerona.catalog.battle_depth import BASE_DISCIPLINE, FORMATIONS, TERRAIN_WIDTH, FormationSpec, WeaponProfile, formation_for
from aerona.catalog.materials import MATERIALS
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
    weapon_of,
)
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.environment import PlaceCover, TerrainKind, WeatherKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import (
    ArmourType,
    BattlePhase,
    CommandArea,
    CommanderTrait,
    Formation,
    MoraleState,
    OutcomeClass,
    Tactic,
    TargetClass,
    UnitFamily,
    UnitKind,
)
from aerona.domain.enums.mortal import HarshnessScale
from aerona.engine.economy.materials import MaterialProps, from_spec
from aerona.engine.environment.battleground import cover_missile_pct
from aerona.engine.military.command import family_factor
from aerona.engine.military.tables import counters, defender_cell, matchup, terrain_cell, unit_terrain, weather_cell
from aerona.engine.primitives.harshness import harshness
from aerona.engine.recording.record import StepDraft
from aerona.rules.registry import Rules
from aerona.rules.registry.scale import ScaleRules

F = UnitFamily
MISSILE_FAMILIES = frozenset({F.MISSILE, F.MAGIC, F.ENGINEER, F.VEHICLE, F.AIR, F.ELECTRONIC, F.SPACE})
CHARGE_FAMILIES = frozenset({F.MOUNTED, F.BEAST})
SWIFT_FAMILIES = frozenset({F.MOUNTED, F.BEAST})
FLYERS = frozenset({UnitKind.SKY_RIDERS, UnitKind.SKY_CREW})
SCOUTS = frozenset({UnitKind.LIGHT_CAVALRY, UnitKind.LIGHT_INFANTRY, UnitKind.MOUNTED_ARCHERS, UnitKind.SKY_RIDERS})
SHELTER = frozenset({TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.MOUNTAINS, TerrainKind.MARSH, TerrainKind.HIGH_PASS})
NARROW = frozenset({TerrainKind.CANYON, TerrainKind.HIGH_PASS, TerrainKind.FOREST, TerrainKind.JUNGLE, TerrainKind.URBAN, TerrainKind.UNDERGROUND})
HIGHLANDS = frozenset({TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
RAIN = frozenset({WeatherKind.RAIN, WeatherKind.DOWNPOUR, WeatherKind.STORM})
SNOW = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})
WIND = frozenset({WeatherKind.STORM, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
HEAVY = frozenset({ArmourType.MAIL, ArmourType.SCALE, ArmourType.PLATE})
SOFT_ARMOUR = {ArmourType.HIDE: MaterialKind.HIDE, ArmourType.PADDED: MaterialKind.CLOTH}
BLUNT_WEAPONS = frozenset({"blunt", "sling", "staff"})
BOWS = frozenset({UnitKind.ARCHERS, UnitKind.MOUNTED_ARCHERS})
CROSSBOWS = frozenset({UnitKind.CROSSBOW_INFANTRY})
FIRE_CASTERS = frozenset({UnitKind.BATTLE_CASTERS})
HELMET = 5
NORMAL = 50
REFUSE_RATIO = 0.6
GENERIC = (Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT)
STRIKE_TACTICS = frozenset({Tactic.INFILTRATION, Tactic.DROP_ASSAULT})
TRAIT_TACTICS: dict[CommanderTrait, tuple[Tactic, ...]] = {
    CommanderTrait.RECKLESS: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.AGGRESSIVE_ASSAULTER: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.CAUTIOUS: (Tactic.HOLD_LINE, Tactic.SHIELD_WALL),
    CommanderTrait.DEFENSIVE_GENIUS: (Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE, Tactic.SHIELD_WALL),
    CommanderTrait.CAVALRY_MASTER: (Tactic.FLANK_CAVALRY, Tactic.FEIGNED_RETREAT),
    CommanderTrait.SIEGE_EXPERT: (Tactic.SIEGE_ASSAULT,),
    CommanderTrait.SKY_COMMANDER: (Tactic.AIR_SUPERIORITY,),
    CommanderTrait.SPACE_COMMANDER: (Tactic.ORBITAL_BOMBARDMENT, Tactic.DROP_ASSAULT),
    CommanderTrait.ARTILLERIST: (Tactic.ARTILLERY_BARRAGE, Tactic.MISSILE_ATTRITION),
    CommanderTrait.AMBUSHER: (Tactic.AMBUSH, Tactic.NIGHT_RAID, Tactic.GUERRILLA),
    CommanderTrait.FOREST_FIGHTER: (Tactic.AMBUSH, Tactic.SKIRMISH_HARASS),
    CommanderTrait.SKIRMISHER: (Tactic.SKIRMISH_HARASS, Tactic.FEINT),
    CommanderTrait.ARMOURED_COMMANDER: (Tactic.ARMOURED_THRUST,),
    CommanderTrait.DISCIPLINARIAN: (Tactic.HOLD_LINE, Tactic.SHIELD_WALL),
    CommanderTrait.SIGNALS_COMMANDER: (Tactic.ELECTRONIC_WARFARE,),
    CommanderTrait.SIEGE_DEFENDER: (Tactic.HOLD_LINE,),
    CommanderTrait.NIGHT_FIGHTER: (Tactic.NIGHT_RAID,),
}
Streams = Callable[[str], SeededRandom]


def armour_value(spec: UnitSpec, row: ArmyUnitRow) -> int:
    return spec.defence + ARMOUR_DEFENCE[row.armour] + SHIELD_DEFENCE[row.shield] + (HELMET if row.helmet else 0)


def class_of(rules: Rules, spec: UnitSpec, row: ArmyUnitRow) -> TargetClass:
    return TargetClass.HARD if armour_value(spec, row) >= rules.battle_depth.hard_defence else TargetClass.SOFT


@dataclass
class Stack:
    row: ArmyUnitRow
    spec: UnitSpec
    start: int
    routed: bool = False
    lost: int = 0
    hardness: int = NORMAL
    raised: bool = False
    reserve: bool = False
    suppressed: bool = False
    delayed: bool = False
    misread: bool = False
    initiative: bool = False
    hidden: bool = False
    spent: int = 0
    killed: int = 0
    walking: int = 0
    stretcher: int = 0
    captured: int = 0
    missing: int = 0
    deserted: int = 0
    seen: tuple[int, int, bool, Formation] | None = None

    @property
    def alive(self) -> bool:
        return self.row.count > 0 and not self.routed

    @property
    def engaged(self) -> bool:
        return self.alive and not self.reserve

    @property
    def weapon(self) -> WeaponProfile:
        return weapon_of(self.spec)

    @property
    def formation(self) -> FormationSpec:
        return FORMATIONS[self.row.formation]

    @property
    def armour(self) -> int:
        return armour_value(self.spec, self.row)

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
    fortune: int = 0
    veteran: float = 0.0
    leadership: int = 0
    tactic: Tactic = Tactic.HOLD_LINE
    tactic_factor: float = 1.0
    surprise: float = 1.0
    keen: float = 0.0
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
    dread_pct: int = PERCENT
    width: int = 0
    reserves_committed: int = 0
    span: int = 0
    commander_struck: bool = False
    planned: bool = False
    trap: bool = False
    feint_pinned: bool = False
    deceiver: bool = False
    standard: bool = False
    babel: int = 0
    wits: int = NORMAL
    initiative_officers: int = 0
    salvaged: int = 0
    concealment: int = 0
    detection: int = 0
    areas: dict[CommandArea, int] = field(default_factory=dict)
    divine_strike_pct: int = 0
    divine_shield: int = 0
    divine_spurned: int = 0
    divine_struck: int = 0
    square_reserve: int = 0
    linear_cap: float = 0.0
    firepower_pct: int = 0

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


@dataclass(frozen=True)
class StackChange:
    army_id: int
    enemy_id: int
    stack_id: int
    kind: UnitKind
    lost: int
    morale: int
    routed: bool
    rallied: bool
    formation: Formation | None


@dataclass
class PhaseLog:
    phase: BattlePhase
    attacker_losses: int
    defender_losses: int
    summary: str
    details: dict[str, int | str] = field(default_factory=dict)
    changes: list[StackChange] = field(default_factory=list)


def traced(log: PhaseLog, *sides: Side) -> PhaseLog:
    first, second = sides
    for side, enemy in ((first, second), (second, first)):
        for stack in side.stacks:
            if stack.seen is None:
                stack.seen = (stack.start, stack.row.morale, False, stack.row.formation)
            count, morale, routed, formation = stack.seen
            morale_now = stack.row.morale
            now = (stack.row.count, morale_now, stack.routed, stack.row.formation)
            if now != stack.seen:
                log.changes.append(
                    StackChange(
                        side.army.id,
                        enemy.army.id,
                        stack.row.id,
                        stack.row.kind,
                        max(0, count - stack.row.count),
                        morale_now - morale,
                        stack.routed and not routed,
                        routed and not stack.routed,
                        stack.row.formation if stack.row.formation != formation else None,
                    )
                )
            stack.seen = now
    return log


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
    planned_by: int | None = None
    trapped_by: int | None = None
    feint: bool = False
    collapsed: int | None = None
    standard_taken: int | None = None
    vehicle_steps: list[StepDraft] = field(default_factory=list)


@dataclass(frozen=True)
class Field:
    terrain: TerrainKind | None
    weather: WeatherKind | None
    night: bool
    river: bool = False
    bridge: bool = False
    ford: bool = False
    cover: PlaceCover | None = None
    earthworks: int = 0


MELEE_FIRST = (F.INFANTRY, F.EXOTIC, F.BEAST, F.MOUNTED, F.VEHICLE, F.ENGINEER, F.MAGIC, F.MISSILE)


def target_class(rules: Rules, stack: Stack) -> TargetClass:
    return class_of(rules, stack.spec, stack.row)


def morale_state(rules: Rules, stack: Stack) -> MoraleState:
    table = rules.battle_depth
    morale = stack.row.morale
    if stack.routed:
        return MoraleState.BROKEN if morale < table.broken_below else MoraleState.ROUTING
    if stack.row.morale_state is MoraleState.RALLIED and morale >= rules.morale.rout_morale:
        return MoraleState.RALLIED
    if morale < rules.morale.rout_morale:
        return MoraleState.ROUTING
    if morale < table.wavering_below:
        return MoraleState.WAVERING
    if morale < table.shaken_below:
        return MoraleState.SHAKEN
    return MoraleState.STEADY


def settle(rules: Rules, stack: Stack) -> MoraleState:
    if stack.row.count > 0 and stack.row.morale < rules.morale.rout_morale:
        stack.routed = True
    stack.row.morale_state = morale_state(rules, stack)
    return stack.row.morale_state


def state_factor(rules: Rules, stack: Stack) -> float:
    table = rules.battle_depth
    state = stack.row.morale_state
    if state is MoraleState.SHAKEN:
        return table.shaken_pct / PERCENT
    if state is MoraleState.WAVERING:
        return table.wavering_pct / PERCENT
    return 1.0


def organisation_factor(stack: Stack) -> float:
    return 0.4 + 0.6 * stack.row.organisation / PERCENT


def disorganise(rules: Rules, stack: Stack, amount: float) -> None:
    table = rules.battle_depth
    guard = 1 - stack.row.discipline / PERCENT * table.discipline_guard_pct / PERCENT
    loss = amount * guard * stack.formation.organisation_loss_pct / PERCENT
    stack.row.organisation = max(0, round(stack.row.organisation - loss))
    if stack.row.count > 0 and stack.row.organisation <= table.disorganised_at:
        stack.routed = True
        stack.row.morale_state = MoraleState.ROUTING


def order_factor(rules: Rules, stack: Stack) -> float:
    table = rules.battle_depth
    if stack.initiative:
        return table.initiative_strength_pct / PERCENT
    if stack.misread:
        return table.misread_strength_pct / PERCENT
    if stack.delayed:
        return table.delayed_pct / PERCENT
    return 1.0


def piercing_of(attackers: list[Stack]) -> float:
    armed = [stack for stack in attackers if stack.alive]
    total = sum(stack.row.count for stack in armed)
    return sum(stack.row.count * stack.weapon.piercing for stack in armed) / total if total else 0.0


def hard_guard(rules: Rules, target: Stack, attackers: list[Stack] | None) -> float:
    if target_class(rules, target) is TargetClass.SOFT:
        return 1.0
    pierce = piercing_of(attackers) / PERCENT if attackers else 0.0
    return 1 - rules.battle_depth.hard_guard_pct / PERCENT * (1 - pierce)


def battle_width(rules: Rules, ground: Field, fog: bool) -> int:
    width = TERRAIN_WIDTH[ground.terrain or TerrainKind.PLAIN] * rules.battle_depth.width_scale
    return round(width * (rules.battle_depth.fog_width_pct / PERCENT if fog or ground.weather is WeatherKind.FOG else 1.0))


def deploy(rules: Rules, side: Side, ground: Field) -> None:
    side.width = battle_width(rules, ground, side.fog)
    filled = 0
    order = sorted(side.stacks, key=lambda stack: (stack.hidden, MELEE_FIRST.index(stack.spec.family), -stack.row.count, stack.row.id))
    for stack in order:
        if not stack.alive:
            continue
        stack.reserve = stack.hidden or filled >= side.width
        if not stack.reserve:
            filled += stack.row.count


def front_room(side: Side) -> int:
    return side.width - sum(stack.row.count for stack in side.stacks if stack.engaged)


def refill(side: Side, *, everyone: bool = False) -> int:
    committed = 0
    waiting = sorted((stack for stack in side.stacks if stack.alive and stack.reserve and not stack.hidden), key=lambda stack: (-stack.row.count, stack.row.id))
    for stack in waiting:
        if not everyone and front_room(side) <= 0:
            break
        stack.reserve = False
        committed += stack.row.count
    side.reserves_committed += committed
    return committed


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
    if ground.terrain in HIGHLANDS and stack.row.kind is UnitKind.SIEGE_CREW:
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
    worn = armour_material(stack)
    fatigue *= 1 + (worn.density if worn is not None else 0) * rules.tissues.unit_density_fatigue_pct / PERCENT / PERCENT
    quality = row.quality / NORMAL * (1 + row.experience / PERCENT * rules.military_units.experience_pct / PERCENT) * (1 + side.veteran + side.wing_bonus)
    vigour = max(0.2, 1 - fatigue / (2 * PERCENT)) * (0.5 + min(PERCENT, row.morale + side.leadership) / PERCENT)
    height = 1.0
    if side.defending:
        height = 1 + (defender_cell(rules, ground.terrain) - 1) * rules.terrain_effects.defender_height_pct / PERCENT
        if weather in SNOW:
            height *= rules.battle_weather.snow_defender_pct / PERCENT
    dug = 1 + dug_in(side, ground) / PERCENT * rules.logistics.entrench_defence_pct / PERCENT if side.defending else 1.0
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
        * family_factor(rules, side.areas, stack.spec.family)
        * organisation_factor(stack)
        * state_factor(rules, stack)
        * order_factor(rules, stack)
        * (1 + rules.battle_depth.planning_pct / PERCENT if side.planned else 1.0)
    )


def called_fog(rules: Rules, stack: Stack, side: Side, enemy: Side | None) -> float:
    if enemy is None or not (side.fog or enemy.fog) or stack.spec.family is not F.MISSILE:
        return 1.0
    return rules.battle_magic.fog_missile_pct / PERCENT


def cast_luck(rules: Rules, streams: Streams, *sides: Side) -> None:
    table = rules.campaigns
    for side in sides:
        side.luck = 1 + streams(f"luck.{side.entity.id}").die(table.battle_die) * table.battle_die_mult / PERCENT
        side.luck *= 1 + side.fortune / PERCENT * rules.fortune.draw_cap_pct / PERCENT


def strength(rules: Rules, side: Side, ground: Field) -> float:
    return sum(
        stack.row.count * (stack.spec.melee + stack.spec.missile + stack.armour) / 3 * modifier(rules, stack, side, ground)
        for stack in side.stacks
        if stack.alive
    )


def scouting(side: Side) -> float:
    eyes = sum(stack.row.count * stack.spec.speed / PERCENT for stack in side.stacks if stack.alive and stack.row.kind in SCOUTS)
    return eyes + side.skill * 10 + side.intel + side.watch


BARRAGE_KINDS = frozenset({UnitKind.ARTILLERY_CREW, UnitKind.SIEGE_CREW, UnitKind.DRONE_OPERATORS})
ARMOURED_KINDS = frozenset({UnitKind.MECHANISED_INFANTRY, UnitKind.POWERED_TROOPERS})
BLOCKADE_KINDS = frozenset({UnitKind.NAVAL_CREW, UnitKind.VOID_CREW})
IRREGULAR_KINDS = frozenset({UnitKind.PARTISANS, UnitKind.LIGHT_INFANTRY, UnitKind.SPECIAL_FORCES})
DROP_KINDS = frozenset({UnitKind.DROP_TROOPS, UnitKind.SKY_CREW, UnitKind.VOID_CREW, UnitKind.PILOTS})


def fielded(option: Tactic, side: Side) -> bool:
    kinds = {stack.row.kind for stack in side.stacks if stack.alive}
    families = {stack.spec.family for stack in side.stacks if stack.alive}
    needs: dict[Tactic, bool] = {
        Tactic.ARTILLERY_BARRAGE: bool(kinds & BARRAGE_KINDS),
        Tactic.ARMOURED_THRUST: F.VEHICLE in families or bool(kinds & ARMOURED_KINDS),
        Tactic.AIR_SUPERIORITY: any(stack.spec.flying for stack in side.stacks if stack.alive),
        Tactic.BLOCKADE: bool(kinds & BLOCKADE_KINDS),
        Tactic.GUERRILLA: bool(kinds & IRREGULAR_KINDS),
        Tactic.ELECTRONIC_WARFARE: F.ELECTRONIC in families,
        Tactic.ORBITAL_BOMBARDMENT: UnitKind.VOID_CREW in kinds or F.SPACE in families,
        Tactic.DROP_ASSAULT: bool(kinds & DROP_KINDS),
        Tactic.INFILTRATION: F.SPECIAL in families,
    }
    return needs.get(option, True)


def choose_tactic(rules: Rules, rng: SeededRandom, side: Side, enemy_doctrine: str, ground: Field) -> Tactic:
    if side.profile.tactic is not None:
        return side.profile.tactic
    options = list(dict.fromkeys([*STYLE_TACTICS.get(side.profile.doctrine, GENERIC), *GENERIC, *side.learned]))
    for trait in side.traits:
        options.extend(item for item in TRAIT_TACTICS.get(trait, ()) if item not in options)
    options = [option for option in options if fielded(option, side)] or list(GENERIC)
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


def stack_material(kind: str | None) -> MaterialProps:
    found = next((item for item in MaterialKind if item.value == kind), MaterialKind.IRON)
    return from_spec(MATERIALS[found])


def armour_material(stack: Stack) -> MaterialProps | None:
    if stack.row.armour is ArmourType.NONE:
        return None
    if stack.row.armour in SOFT_ARMOUR:
        return from_spec(MATERIALS[SOFT_ARMOUR[stack.row.armour]])
    return stack_material(stack.row.material)


def penetration(rules: Rules, attackers: list[Stack], target: Stack) -> float:
    armour = armour_material(target)
    if armour is None:
        return 0.0
    floor = rules.strike.shape_floor_pct / PERCENT
    total = weighted = 0.0
    for stack in attackers:
        if not stack.alive or not stack.row.weapons:
            continue
        best = max(stack.row.weapons, key=lambda weapon: WEAPON_EDGE.get(weapon, 0))
        weapon = stack_material(stack.row.material)
        edged = best not in BLUNT_WEAPONS
        attack = weapon.shear_yield if edged else weapon.impact_yield
        guard = armour.shear_yield if edged else armour.impact_yield
        match = max(0.0, min(1.0, floor + (attack - guard) / PERCENT))
        weighted += stack.row.count * WEAPON_EDGE.get(best, 0) / PERCENT * match
        total += stack.row.count
    return min(1.0, weighted / total) * rules.battle_magic.weapon_vs_armour_pct / PERCENT if total else 0.0


def taken_pct(stack: Stack, mode: str) -> float:
    spec = stack.formation
    if mode == "missile":
        return spec.missile_taken_pct / PERCENT
    if mode == "charge":
        return spec.charge_taken_pct / PERCENT
    return PERCENT / max(1, spec.defence_pct)


def deal(targets: list[Stack], damage: float, rules: Rules, *, attackers: list[Stack] | None = None, mode: str = "melee") -> int:
    alive = [stack for stack in targets if stack.engaged] or [stack for stack in targets if stack.alive]
    total = sum(stack.row.count for stack in alive)
    if total <= 0 or damage <= 0:
        return 0
    killed = 0
    harsh = harshness(rules, HarshnessScale.BATTLE_LOSS)
    for stack in alive:
        share = stack.row.count / total
        armour = stack.armour * (1 - penetration(rules, attackers, stack) if attackers else 1)
        dealt = damage * share * taken_pct(stack, mode) * hard_guard(rules, stack, attackers)
        before = stack.row.count
        losses = min(stack.row.count, int(dealt * rules.tactics.loss_scale_pct / PERCENT * NORMAL / max(10, armour) * harsh))
        stack.row.count -= losses
        stack.lost += losses
        killed += losses
        if losses and before:
            disorganise(rules, stack, losses / max(1, stack.start) * rules.battle_depth.organisation_loss_pct)
    return killed


def resist(rules: Rules, side: Side, shock: float) -> float:
    return shock * max(0.0, 1 - side.willpower / PERCENT * rules.battle_magic.willpower_pct / PERCENT) * side.dread_pct / PERCENT


def shaken(rules: Rules, side: Side, streams: Streams | None = None, *, phase: str = "check") -> None:
    routs = 0
    for stack in side.stacks:
        if not stack.alive or stack.start <= 0:
            continue
        share = stack.lost / stack.start
        stack.row.morale = max(0, round(stack.row.morale - share * PERCENT * 0.8 * side.dread_pct / PERCENT))
        if settle(rules, stack) is MoraleState.ROUTING:
            routs += 1
    if routs:
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = max(0, stack.row.morale - round(resist(rules, side, rules.morale.rout_contagion * routs)))
                settle(rules, stack)
    if streams is not None:
        rally(rules, streams, side, phase)
    for stack in side.stacks:
        if stack.routed:
            settle(rules, stack)


def rally(rules: Rules, streams: Streams, side: Side, phase: str) -> int:
    table = rules.battle_depth
    lift = min(1.0, side.leadership / PERCENT + (0.25 if side.standard else 0.0) + (0.25 if side.count_of(UnitKind.SUPPORT_CASTERS) else 0.0))
    rallied = 0
    for stack in side.stacks:
        if not stack.routed or stack.row.count <= 0 or stack.row.morale_state is MoraleState.BROKEN or stack.row.organisation <= table.disorganised_at:
            continue
        if streams(f"rally.{phase}.{stack.row.id}").chance(table.rally_chance * lift):
            stack.routed = False
            stack.row.morale = max(stack.row.morale, table.rally_morale)
            stack.row.morale_state = MoraleState.RALLIED
            rallied += 1
    return rallied


def enemy_reach(side: Side) -> int:
    return max((stack.weapon.reach for stack in side.stacks if stack.engaged and stack.spec.missile > 0), default=0)


def volley(rules: Rules, stack: Stack, enemy: Side, *, engaged: bool) -> float:
    if stack.row.ammunition <= 0:
        return 0.0
    rate = max(1, stack.weapon.volleys)
    fired = 1 if engaged else min(rate, stack.row.ammunition)
    stack.row.ammunition -= fired
    stack.spent += fired
    reach = 1 + max(0, stack.weapon.reach - enemy_reach(enemy)) * rules.battle_depth.reach_pct / PERCENT
    close = rules.battle_depth.engaged_missile_pct / PERCENT if engaged else 1.0
    return fired / rate * stack.weapon.accuracy / NORMAL * reach * close


def suppress(rules: Rules, target: Side, before: dict[int, int]) -> int:
    pinned = 0
    for stack in target.stacks:
        start = before.get(id(stack), 0)
        if start and stack.alive and (start - stack.row.count) * PERCENT >= start * rules.battle_depth.suppression_pct:
            stack.suppressed = True
            pinned += 1
    return pinned


def loosing_share(rules: Rules, stack: Stack, families: frozenset[UnitFamily], *, coastal: bool) -> float:
    if stack.spec.missile <= 0:
        return 0.0
    if stack.row.kind is UnitKind.NAVAL_CREW:
        return rules.battle_terrain.coastal_fleet_support_pct / PERCENT if coastal else 0.0
    return 1.0 if stack.spec.family in families else 0.0


def missiles(rules: Rules, streams: Streams, shooter: Side, target: Side, ground: Field, *, families: frozenset[UnitFamily], engaged: bool = False) -> int:
    coastal = ground.terrain is TerrainKind.COAST
    damage = 0.0
    for stack in shooter.stacks:
        massed = not engaged and stack.alive and stack.reserve
        share = loosing_share(rules, stack, families, coastal=coastal) if stack.engaged or massed else 0.0
        if share <= 0:
            continue
        shot = volley(rules, stack, target, engaged=engaged)
        if shot <= 0:
            continue
        if massed:
            share *= rules.lanchester.square_reserve_pct / PERCENT
            shooter.square_reserve += stack.row.count
        damage += (
            stack.row.count
            * stack.spec.missile
            / PERCENT
            * modifier(rules, stack, shooter, ground, target)
            * share
            * shot
            * fortune(rules, streams, "missile", stack)
        )
    damage *= 1 + shooter.firepower_pct / PERCENT
    if shooter.tactic is Tactic.ARTILLERY_BARRAGE:
        damage *= rules.tactics.barrage_pct / PERCENT
    elif shooter.tactic is Tactic.ORBITAL_BOMBARDMENT:
        damage *= rules.tactics.bombardment_pct / PERCENT
    if target.tactic is Tactic.ELECTRONIC_WARFARE:
        damage *= rules.tactics.jammed_pct / PERCENT
    if target.defending:
        damage *= cover_missile_pct(rules, ground.cover) / PERCENT
    before = {id(stack): stack.row.count for stack in target.stacks}
    killed = deal(target.stacks, damage, rules, attackers=shooter.stacks, mode="missile")
    if not engaged:
        suppress(rules, target, before)
    return killed


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
        * stack.formation.charge_pct
        / PERCENT
        * fortune(rules, streams, "charge", stack)
        for stack in rider.stacks
        if stack.engaged and stack.spec.family in CHARGE_FAMILIES and charges(stack)
    )
    if target.defending:
        impact *= 1 - rules.army_depth.earthworks_charge_pct * dug_in(target, ground) / PERCENT / PERCENT
    dealt = deal(target.stacks, impact * (1 - brace), rules, mode="charge")
    taken = deal([stack for stack in rider.stacks if stack.spec.family in CHARGE_FAMILIES], impact * brace / 2, rules)
    terror = sum(stack.row.count * stack.spec.terror for stack in rider.stacks if stack.alive) / max(1, rider.standing)
    if terror:
        frighten(rules, target, terror * rules.morale.terror_pct / PERCENT)
    return dealt, taken


def dug_in(side: Side, ground: Field) -> int:
    return max(side.profile.entrenchment, ground.earthworks)


def charges(stack: Stack) -> bool:
    return not stack.suppressed and stack.row.morale_state not in (MoraleState.WAVERING, MoraleState.ROUTING, MoraleState.BROKEN)


def frighten(rules: Rules, target: Side, shock: float) -> int:
    dread = resist(rules, target, shock)
    for stack in target.stacks:
        if stack.alive:
            stack.row.morale = max(0, round(stack.row.morale - dread * (1 - stack.row.morale / (2 * PERCENT))))
            disorganise(rules, stack, dread * rules.battle_depth.shock_organisation_pct / PERCENT)
    return round(dread)


def reach(rules: Rules, striker: Side, target: Side) -> float:
    if any(stack.alive and (stack.flying or stack.spec.missile > 0) for stack in striker.stacks):
        return 1.0
    present = sum(stack.row.count for stack in target.stacks if stack.alive) or 1
    aloft = sum(stack.row.count for stack in target.stacks if stack.alive and stack.flying) / present
    return 1 - aloft * (1 - rules.naval.sky_counter_pct / PERCENT)


def hidden_soldiers(side: Side) -> int:
    return sum(stack.row.count for stack in side.stacks if stack.hidden)


def spring_trap(rules: Rules, side: Side, enemy: Side) -> list[Stack]:
    if not side.trap:
        return []
    sprung = [stack for stack in side.stacks if stack.alive and stack.hidden]
    for stack in sprung:
        stack.hidden = False
        stack.reserve = False
    if sprung:
        frighten(rules, enemy, rules.battle_depth.trap_shock)
    side.trap = False
    return sprung


def linear_share(rules: Rules, side: Side, enemy: Side) -> float:
    mine = sum(stack.row.count for stack in side.stacks if stack.engaged)
    front = sum(stack.row.count for stack in enemy.stacks if stack.engaged) * rules.lanchester.linear_overlap_pct / PERCENT
    if mine <= 0 or mine <= front:
        return 1.0
    share = front / mine
    side.linear_cap = max(side.linear_cap, 1 - share)
    return share


def melee_power(rules: Rules, streams: Streams, sides: tuple[Side, Side], ground: Field, *, index: int, sprung: list[Stack]) -> float:
    side, enemy = sides
    trap = rules.battle_depth.trap_strength_pct / PERCENT
    return linear_share(rules, side, enemy) * sum(
        stack.row.count
        * stack.spec.melee
        / PERCENT
        * modifier(rules, stack, side, ground, enemy)
        * (trap if stack in sprung else 1.0)
        * fortune(rules, streams, f"melee{index}", stack)
        for stack in side.stacks
        if stack.engaged
    )


def melee_round(rules: Rules, streams: Streams, first: Side, second: Side, ground: Field, *, index: int) -> tuple[int, int]:
    sprung_first, sprung_second = spring_trap(rules, first, second), spring_trap(rules, second, first)
    close_first = missiles(rules, streams, first, second, ground, families=MISSILE_FAMILIES - {F.MAGIC}, engaged=True)
    close_second = missiles(rules, streams, second, first, ground, families=MISSILE_FAMILIES - {F.MAGIC}, engaged=True)
    power_first = melee_power(rules, streams, (first, second), ground, index=index, sprung=sprung_first)
    power_second = melee_power(rules, streams, (second, first), ground, index=index, sprung=sprung_second)
    to_second = deal(second.stacks, power_first * reach(rules, first, second), rules, attackers=first.stacks)
    to_first = deal(first.stacks, power_second * reach(rules, second, first), rules, attackers=second.stacks)
    for stack in (*first.stacks, *second.stacks):
        stack.suppressed = False
    return to_first + close_second, to_second + close_first


def frontage(rules: Rules, ground: Field) -> float:
    return rules.battle_magic.narrow_frontage_pct / PERCENT if ground.terrain in NARROW else 1.0


def swift_speed(side: Side) -> float:
    swift = [stack for stack in side.stacks if stack.alive and stack.spec.family in SWIFT_FAMILIES]
    total = sum(stack.row.count for stack in swift)
    return sum(stack.row.count * stack.spec.speed for stack in swift) / total if total else 0.0


def anchored(rules: Rules, streams: Streams, line: Side, ground: Field) -> bool:
    return line.defending and ground.cover is PlaceCover.HEAVY and streams(f"anchor.{line.entity.id}").chance(rules.battle_depth.anchored_flank_pct)


def outflank(rules: Rules, first: Side, second: Side, ground: Field, streams: Streams | None = None) -> PhaseLog | None:
    table = rules.battle_magic
    room = frontage(rules, ground)
    for flanker, line in ((first, second), (second, first)):
        if streams is not None and anchored(rules, streams, line, ground):
            continue
        wide = flanker.standing * room > line.standing
        swift = swift_speed(flanker) - swift_speed(line) >= table.flank_speed_lead
        if wide and swift and not flanker.flanking:
            flanker.flanking = True
            flanker.tactic_factor *= 1 + table.flank_pct / PERCENT
            for stack in line.stacks:
                if stack.alive:
                    disorganise(rules, stack, rules.battle_depth.flank_organisation)
            return PhaseLog(BattlePhase.CHARGE, 0, 0, f"{flanker.entity.name} turned the flank", {"flank": flanker.entity.name})
    return None


def call_fog(rules: Rules, streams: Streams, caster: Side, enemy: Side) -> bool:
    mages = caster.count_of(UnitKind.BATTLE_CASTERS)
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
    mages = caster.count_of(UnitKind.BATTLE_CASTERS) + caster.count_of(UnitKind.SUMMONERS)
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
        if stack.alive and stack.row.kind is UnitKind.BATTLE_CASTERS:
            part = round(stack.row.count * rules.battle_weather.magic_storm_backlash_pct / PERCENT)
            stack.row.count -= part
            stack.lost += part
            lost += part
    side.backlash = lost
    return lost


def rites(rules: Rules, streams: Streams, side: Side, enemy: Side, ground: Field) -> int:
    if side.count_of(UnitKind.SUPPORT_CASTERS):
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = min(PERCENT, stack.row.morale + rules.morale.priests_gain)
    return missiles(rules, streams, side, enemy, ground, families=frozenset({F.MAGIC}))


def divine_hand(rules: Rules, side: Side, enemy: Side) -> int:
    if side.divine_shield:
        for stack in side.stacks:
            if stack.alive:
                stack.row.morale = min(PERCENT, stack.row.morale + side.divine_shield)
    if side.divine_spurned:
        frighten(rules, side, side.divine_spurned)
    if side.divine_strike_pct <= 0:
        return 0
    side.divine_struck = deal(enemy.stacks, enemy.standing * side.divine_strike_pct / PERCENT, rules, mode="missile")
    return side.divine_struck


def broken(side: Side) -> bool:
    return side.standing <= side.start // 4 or all(not stack.alive for stack in side.stacks)


def pursue(rules: Rules, winner: Side, loser: Side, ground: Field) -> int:
    riders = sum(stack.row.count for stack in winner.stacks if stack.alive and stack.spec.family in CHARGE_FAMILIES)
    span = min(1.0, 2 * riders / max(1, winner.standing))
    shelter = 0.5 if ground.terrain in SHELTER else 1.0
    fleeing = sum(stack.row.count for stack in loser.stacks)
    escape = 1 - rules.army_depth.command_area_pct * loser.areas.get(CommandArea.MANOEUVRE, 0) / PERCENT / PERCENT
    losses = round(fleeing * rules.tactics.pursuit_pct / PERCENT * (0.3 + span) * shelter * escape * harshness(rules, HarshnessScale.BATTLE_LOSS))
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


ELEVATED = frozenset({TerrainKind.HILLS, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
HIDDEN_SHARE_MAX = 0.4


def concealment(rules: Rules, side: Side, ground: Field) -> int:
    table = rules.battle_depth
    value = table.cover_concealment if ground.cover is PlaceCover.HEAVY else 0
    value += table.night_concealment if ground.night else 0
    value += table.fog_concealment if side.fog or ground.weather is WeatherKind.FOG else 0
    standing = max(1, side.standing)
    loose = sum(stack.row.count for stack in side.stacks if stack.alive and stack.row.formation is Formation.LOOSE) / standing
    return value + round(loose * table.loose_concealment)


def detection(rules: Rules, side: Side, ground: Field) -> int:
    standing = max(1, side.standing)
    eyes = sum(stack.row.count for stack in side.stacks if stack.alive and stack.row.kind in SCOUTS) / standing * PERCENT * 2
    elevated = rules.battle_depth.elevation_detection if side.defending and ground.terrain in ELEVATED else 0
    return max(0, min(PERCENT, round(eyes + side.skill / 2 + side.intel / 2 + elevated)))


def hide(side: Side) -> int:
    edge = side.concealment - side.detection
    if edge <= 0 or len([stack for stack in side.stacks if stack.alive]) < 2:
        return 0
    share = min(HIDDEN_SHARE_MAX, edge / PERCENT)
    target = side.standing * share
    hidden = 0
    for stack in sorted((item for item in side.stacks if item.alive), key=lambda item: (item.row.count, item.row.id)):
        if hidden + stack.row.count > target:
            break
        stack.hidden = True
        hidden += stack.row.count
    side.trap = hidden > 0
    return hidden


def spot(rules: Rules, attacker: Side, defender: Side, ground: Field) -> dict[str, int | str]:
    for side, enemy in ((attacker, defender), (defender, attacker)):
        if side.deceiver:
            enemy.intel = max(0, enemy.intel - rules.battle_depth.deserter_intel)
    for side, enemy in ((attacker, defender), (defender, attacker)):
        side.concealment = concealment(rules, side, ground)
        side.detection = detection(rules, enemy, ground)
    hidden_a, hidden_d = hide(attacker), hide(defender)
    return {
        "attacker_hidden": hidden_a,
        "defender_hidden": hidden_d,
        "attacker_concealment": attacker.concealment,
        "defender_concealment": defender.concealment,
    }


def command(rules: Rules, streams: Streams, side: Side, ground: Field) -> dict[str, int]:
    table = rules.battle_depth
    capacity = table.command_capacity_base + side.skill * (PERCENT - table.command_capacity_base) / PERCENT
    span = 0 if side.commander_struck else max(1, round(capacity / table.command_capacity_divisor))
    if ground.night:
        span = max(0, round(span * table.night_span_pct / PERCENT)) if not side.commander_struck else 0
    side.span = span
    misread = initiative = 0
    for index, stack in enumerate(sorted((item for item in side.stacks if item.alive), key=lambda item: (-item.row.count, item.row.id))):
        stack.delayed = index >= span
        stack.misread = stack.initiative = False
        if not stack.delayed:
            continue
        rng = streams(f"orders.{side.entity.id}.{stack.row.id}")
        chance = table.misread_pct * max(0.0, 2 - side.wits / NORMAL) + (table.babel_misread_pct if side.babel > 0 else 0)
        if rng.chance(min(PERCENT, round(chance))):
            stack.misread = True
            misread += 1
        elif side.initiative_officers and rng.chance(table.initiative_pct):
            stack.initiative = True
            initiative += 1
    return {"span": span, "delayed": sum(1 for stack in side.stacks if stack.alive and stack.delayed), "misread": misread, "initiative": initiative}


def collapse(rules: Rules, streams: Streams, side: Side, phase: str) -> bool:
    if side.commander_struck or not (broken(side) or side.lost * 2 >= side.start):
        return False
    if not streams(f"struck.{phase}.{side.entity.id}").chance(rules.battle_depth.commander_struck_pct):
        return False
    side.commander_struck = True
    side.span = 0
    for stack in side.stacks:
        stack.delayed = stack.alive
        stack.initiative = False
    frighten(rules, side, rules.battle_depth.collapse_morale)
    return True


def commit_reserves(rules: Rules, streams: Streams, side: Side, index: int) -> int:
    if side.feint_pinned:
        return 0
    committed = refill(side)
    skill = rules.battle_depth.reserve_commit_pct * side.skill / PERCENT
    if not side.commander_struck and streams(f"reserve.{index}.{side.entity.id}").chance(round(skill)):
        committed += refill(side, everyone=True)
    return committed


def opening(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> tuple[Side | None, list[PhaseLog]]:
    table = rules.tactics
    eyes_a, eyes_d = scouting(attacker), scouting(defender)
    lead = attacker if eyes_a > eyes_d else defender
    other = defender if lead is attacker else attacker
    margin = abs(eyes_a - eyes_d) / max(1.0, eyes_a, eyes_d) * PERCENT
    seen = spot(rules, attacker, defender, ground)
    refused = False
    if margin >= table.scouting_margin:
        if strength(rules, lead, ground) < strength(rules, other, ground) * REFUSE_RATIO:
            refused = True
        else:
            lead.defending, other.defending = True, False
            if ground.terrain in AMBUSH_TERRAIN or ground.cover is PlaceCover.HEAVY or ground.weather is WeatherKind.FOG or ground.night:
                lead.surprise = dulled(rules, rules.weather_battle_effects.fog_ambush_pct / PERCENT, other.keen)
    summary = f"{lead.entity.name} saw further" + (" and refused battle" if refused else " and chose the ground")
    phases = [traced(PhaseLog(BattlePhase.SCOUTING, 0, 0, summary, {"margin": round(margin), "ground": lead.entity.name, **seen}), attacker, defender)]
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
    phases.append(traced(PhaseLog(BattlePhase.PLAN, 0, 0, summary, details), attacker, defender))
    return None, phases


def dulled(rules: Rules, surprise: float, keen: float) -> float:
    return 1 + (surprise - 1) * (1 - keen * rules.senses.ambush_pct / PERCENT)


def night_fire(rules: Rules, side: Side) -> None:
    for stack in side.stacks:
        if stack.engaged:
            stack.row.organisation = max(0, stack.row.organisation - rules.battle_depth.friendly_fire_organisation)


def feint(rules: Rules, streams: Streams, attacker: Side, defender: Side) -> bool:
    if attacker.tactic is not Tactic.FEINT or not any(stack.alive and stack.reserve for stack in defender.stacks):
        return False
    defender.feint_pinned = streams(f"feint.{attacker.entity.id}").chance(rules.battle_depth.feint_reserve_pct)
    return defender.feint_pinned


def fighting(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> list[PhaseLog]:
    fog = [side.entity.name for side, enemy in ((attacker, defender), (defender, attacker)) if call_fog(rules, streams, side, enemy)]
    for side in (attacker, defender):
        deploy(rules, side, ground)
        if ground.night:
            night_fire(rules, side)
    orders: dict[str, int | str] = {f"attacker_{key}": value for key, value in command(rules, streams, attacker, ground).items()}
    orders.update({f"defender_{key}": value for key, value in command(rules, streams, defender, ground).items()})
    orders["width"] = attacker.width
    orders["feint"] = attacker.entity.name if feint(rules, streams, attacker, defender) else ""
    phases = [traced(PhaseLog(BattlePhase.COMMAND, 0, 0, "orders went down the line", orders), attacker, defender)]
    ranged = MISSILE_FAMILIES - {F.MAGIC}
    to_d, to_a = missiles(rules, streams, attacker, defender, ground, families=ranged), missiles(rules, streams, defender, attacker, ground, families=ranged)
    pinned: dict[str, int | str] = {"fog": ", ".join(fog), "pinned": sum(1 for stack in (*attacker.stacks, *defender.stacks) if stack.suppressed)}
    phases.append(
        traced(PhaseLog(BattlePhase.MISSILE, to_a, to_d, "the two sides struck at range" + (" into a called fog" if fog else ""), pinned), attacker, defender)
    )
    attacker.surprise = defender.surprise = 1.0
    for striker, target in ((attacker, defender), (defender, attacker)):
        if striker.tactic in STRIKE_TACTICS:
            striker.surprise = dulled(rules, rules.tactics.strike_surprise_pct / PERCENT, target.keen)
    flank = outflank(rules, attacker, defender, ground, streams)
    if flank is not None:
        phases.append(traced(flank, attacker, defender))
    dealt_a, taken_a = charge(rules, streams, attacker, defender, ground)
    dealt_d, taken_d = charge(rules, streams, defender, attacker, ground)
    phases.append(traced(PhaseLog(BattlePhase.CHARGE, taken_a + dealt_d, dealt_a + taken_d, "the charge"), attacker, defender))
    shaken(rules, attacker, streams, phase="charge")
    shaken(rules, defender, streams, phase="charge")
    for index in range(rules.tactics.melee_rounds):
        lying = {"attacker": hidden_soldiers(attacker), "defender": hidden_soldiers(defender)}
        lost_a, lost_d = melee_round(rules, streams, attacker, defender, ground, index=index)
        attacker.planned = defender.planned = False
        shaken(rules, attacker, streams, phase=f"melee{index}")
        shaken(rules, defender, streams, phase=f"melee{index}")
        sprung: dict[str, int | str] = {
            f"{role}_revealed": lying[role] - hidden_soldiers(side)
            for role, side in (("attacker", attacker), ("defender", defender))
            if lying[role] > hidden_soldiers(side)
        }
        phases.append(traced(PhaseLog(BattlePhase.MELEE, lost_a, lost_d, f"melee, round {index + 1}", sprung), attacker, defender))
        struck = [side.entity.name for side in (attacker, defender) if collapse(rules, streams, side, f"melee{index}")]
        committed = {side.entity.name: commit_reserves(rules, streams, side, index) for side in (attacker, defender)}
        if any(committed.values()) or struck:
            details: dict[str, int | str] = {name: soldiers for name, soldiers in committed.items()}
            details["commander_fell"] = ", ".join(struck)
            phases.append(
                traced(
                    PhaseLog(BattlePhase.RESERVES, 0, 0, "reserves committed" if any(committed.values()) else "a commander fell", details), attacker, defender
                )
            )
        if broken(attacker) or broken(defender):
            break
    burn_a, burn_d = backlash(rules, attacker, ground), backlash(rules, defender, ground)
    terror: dict[str, int | str] = {"attacker_terror": terror_rite(rules, attacker, defender), "defender_terror": terror_rite(rules, defender, attacker)}
    magic_a, magic_d = rites(rules, streams, attacker, defender, ground), rites(rules, streams, defender, attacker, ground)
    god_a, god_d = divine_hand(rules, attacker, defender), divine_hand(rules, defender, attacker)
    gods: dict[str, int | str] = {"attacker_god_struck": god_a, "defender_god_struck": god_d}
    rites_log = PhaseLog(
        BattlePhase.RITES, magic_d + burn_a + god_d, magic_a + burn_d + god_a, "rites and prayers", {**terror, **gods, "backlash": burn_a + burn_d}
    )
    phases.append(traced(rites_log, attacker, defender))
    return phases


def victor(rules: Rules, attacker: Side, defender: Side, ground: Field) -> tuple[Side, Side, float, float]:
    power_a, power_d = strength(rules, attacker, ground), strength(rules, defender, ground)
    winner, loser = (attacker, defender) if power_a >= power_d else (defender, attacker)
    if broken(attacker) != broken(defender):
        winner, loser = (defender, attacker) if broken(attacker) else (attacker, defender)
    return winner, loser, max(power_a, power_d), max(1.0, min(power_a, power_d))


def treat(rules: Rules, side: Side, walking: int, stretcher: int) -> int:
    magic = rules.battle_magic
    healed = min(stretcher, side.count_of(UnitKind.SUPPORT_CASTERS) * magic.heal_per_priest) if side.priests_healing else 0
    healed += min(stretcher - healed, side.count_of(UnitKind.MEDICS) * magic.heal_per_medic)
    rest = stretcher - healed
    saved = round(rest * min(PERCENT, side.medicine) / PERCENT * magic.medicine_pct / PERCENT)
    dying = round((rest - saved) * magic.untreated_death_pct / PERCENT)
    side.healed = healed
    return max(0, walking + stretcher - dying)


def classify_losses(rules: Rules, side: Side) -> tuple[int, int]:
    table, depth = rules.tactics, rules.battle_depth
    captives = side.captives
    total_lost = max(1, side.lost)
    walking = stretcher = 0
    for stack in side.stacks:
        stack.missing = round(stack.lost * depth.missing_pct / PERCENT) if stack.routed else 0
        stack.captured = min(stack.lost - stack.missing, round(captives * stack.lost / total_lost))
        hurt = min(stack.lost - stack.missing - stack.captured, round(stack.lost * table.wounded_pct / PERCENT))
        stack.walking = round(hurt * depth.walking_pct / PERCENT)
        stack.stretcher = hurt - stack.walking
        stack.killed = max(0, stack.lost - stack.missing - stack.captured - hurt)
        stack.row.missing += stack.missing
        stack.row.wounded += hurt
        if stack.row.morale_state is MoraleState.BROKEN and stack.row.count > 0:
            stack.deserted = round(stack.row.count * depth.deserted_pct / PERCENT)
            scattered = stack.row.count - stack.deserted
            stack.missing += scattered
            stack.lost += scattered
            stack.row.missing += scattered
            stack.row.count = 0
        walking += stack.walking
        stretcher += stack.stretcher
    return walking, stretcher


def salvage(rules: Rules, winner: Side, loser: Side) -> int:
    table = rules.battle_depth
    arms = loser.lost
    if arms <= 0:
        return 0
    share = min(1.0, arms / max(1, winner.standing))
    for stack in winner.stacks:
        if stack.row.count > 0:
            stack.row.condition = min(PERCENT, stack.row.condition + round(table.salvage_condition * share))
    worst = min((stack for stack in winner.stacks if stack.row.count > 0), key=lambda stack: (stack.row.quality, stack.row.id), default=None)
    if worst is not None:
        worst.row.quality = min(PERCENT, worst.row.quality + round(table.salvage_quality * share))
    winner.salvaged = arms
    return arms


def raise_dead(rules: Rules, side: Side, fallen: int) -> int:
    necromancers = side.count_of(UnitKind.SUMMONERS)
    if necromancers <= 0:
        return 0
    side.raised_dead = min(round(fallen * rules.battle_magic.raise_dead_pct / PERCENT), necromancers * rules.battle_magic.raise_per_necromancer)
    return side.raised_dead


def aftermath(rules: Rules, winner: Side, loser: Side, gap: float) -> tuple[dict[int, int], dict[int, int], dict[str, int]]:
    campaigns = rules.campaigns
    wounded: dict[int, int] = {}
    maimed: dict[int, int] = {}
    by_kind: dict[str, int] = {}
    fallen = winner.lost + loser.lost
    for side in (winner, loser):
        walking, stretcher = classify_losses(rules, side)
        wounded[side.entity.id] = treat(rules, side, walking, stretcher)
        maimed[side.entity.id] = round(side.lost * rules.maimed.return_pct / PERCENT)
        raise_dead(rules, side, fallen)
        gained = campaigns.winner_experience_gain if side is winner else campaigns.loser_experience_gain
        for stack in side.stacks:
            by_kind[stack.row.kind.value] = by_kind.get(stack.row.kind.value, 0) + stack.lost
            stack.row.experience = min(PERCENT, stack.row.experience + gained)
            stack.row.condition = max(0, stack.row.condition - rules.battle_magic.wear_per_battle)
            if stack.routed:
                stack.row.morale = max(stack.row.morale, rules.morale.rout_morale // 2)
    salvage(rules, winner, loser)
    for stack in winner.stacks:
        stack.row.morale = min(PERCENT, stack.row.morale + campaigns.winner_morale_gain)
    dread = (campaigns.loser_morale_loss + round(gap / campaigns.loser_morale_diff_divisor)) * loser.dread_pct // PERCENT
    for stack in loser.stacks:
        stack.row.morale = max(0, stack.row.morale - dread)
    return wounded, maimed, by_kind


def resolve(rules: Rules, streams: Streams, attacker: Side, defender: Side, ground: Field) -> BattleResult:
    cast_luck(rules, streams, attacker, defender)
    planned_by = next((side.entity.id for side in (attacker, defender) if side.planned), None)
    refuser, phases = opening(rules, streams, attacker, defender, ground)
    trapped_by = next((side.entity.id for side in (attacker, defender) if side.trap), None)
    if refuser is not None:
        holder = defender if refuser is attacker else attacker
        return BattleResult(attacker, defender, holder, refuser, True, OutcomeClass.REFUSED, 0.0, phases, {}, {}, {})
    phases.extend(fighting(rules, streams, attacker, defender, ground))
    winner, loser, strong, weak = victor(rules, attacker, defender, ground)
    pursued = pursue(rules, winner, loser, ground)
    details: dict[str, int | str] = {"baggage": winner.baggage_taken}
    phases.append(
        traced(
            PhaseLog(BattlePhase.PURSUIT, pursued if loser is attacker else 0, pursued if loser is defender else 0, f"{winner.entity.name} pursued", details),
            attacker,
            defender,
        )
    )
    outcome = classify(rules, winner, loser, strong / weak)
    gap = min(PERCENT, (strong - weak) / strong * PERCENT) if strong else 0.0
    wounded, maimed, by_kind = aftermath(rules, winner, loser, gap)
    summary = {
        "wounded": sum(wounded.values()),
        "maimed": sum(maimed.values()),
        "healed": attacker.healed + defender.healed,
        "raised": attacker.raised_dead + defender.raised_dead,
        "missing": sum(stack.missing for stack in (*attacker.stacks, *defender.stacks)),
        "deserted": sum(stack.deserted for stack in (*attacker.stacks, *defender.stacks)),
        "captured": sum(stack.captured for stack in (*attacker.stacks, *defender.stacks)),
    }
    phases.append(traced(PhaseLog(BattlePhase.SALVAGE, 0, 0, f"{winner.entity.name} stripped the field", {"arms": winner.salvaged}), attacker, defender))
    phases.append(traced(PhaseLog(BattlePhase.AFTERMATH, attacker.lost, defender.lost, f"the outcome: {spoken(outcome)}", dict(summary)), attacker, defender))
    for stack in (*attacker.stacks, *defender.stacks):
        settle(rules, stack)
    factors = {
        "attacker": round(attacker.tactic_factor, 3),
        "defender": round(defender.tactic_factor, 3),
        "attacker_flank": float(attacker.flanking),
        "attacker_luck": round(attacker.luck, 3),
        "defender_luck": round(defender.luck, 3),
        "defender_flank": float(defender.flanking),
        "attacker_span": float(attacker.span),
        "defender_span": float(defender.span),
        "attacker_concealment": float(attacker.concealment),
        "defender_concealment": float(defender.concealment),
        "attacker_square_reserve": float(attacker.square_reserve),
        "defender_square_reserve": float(defender.square_reserve),
        "attacker_linear_cap": round(attacker.linear_cap, 3),
        "defender_linear_cap": round(defender.linear_cap, 3),
    }
    collapsed = next((side.entity.id for side in (attacker, defender) if side.commander_struck), None)
    return BattleResult(
        attacker,
        defender,
        winner,
        loser,
        False,
        outcome,
        gap,
        phases,
        wounded,
        maimed,
        by_kind,
        factors,
        planned_by=planned_by,
        trapped_by=trapped_by,
        feint=defender.feint_pinned,
        collapsed=collapsed,
    )


def ready(row: ArmyUnitRow, spec: UnitSpec, rounds: int) -> None:
    if row.organisation is None:
        row.organisation = PERCENT
    if row.discipline is None:
        row.discipline = BASE_DISCIPLINE[spec.kind]
    if row.ammunition is None:
        row.ammunition = max(1, weapon_of(spec).volleys) * rounds if spec.missile > 0 else 0
    if row.formation is None:
        row.formation = formation_for(spec.kind, spec.family)
    if row.morale_state is None:
        row.morale_state = MoraleState.STEADY
    if row.missing is None:
        row.missing = 0


def make_stacks(
    rows: list[ArmyUnitRow],
    specs: dict[int, UnitSpec] | None = None,
    hardness: dict[str, int] | None = None,
    fielded: dict[int, UnitSpec] | None = None,
    *,
    rounds: int = ScaleRules.missile_rounds_carried,
) -> list[Stack]:
    found = []
    for row in rows:
        if row.count <= 0:
            continue
        spec = (fielded or {}).get(row.id) or (specs or {}).get(row.design_id or 0) or UNITS[row.kind]
        ready(row, spec, rounds)
        found.append(Stack(row, spec, row.count, hardness=(hardness or {}).get(row.material or "", NORMAL)))
    return found
