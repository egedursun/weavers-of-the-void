from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from sqlalchemy import select

from aerona.catalog.harm_kinds import DAMAGE
from aerona.catalog.terrain import terrains
from aerona.catalog.weather import has_trait
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.enums.body import BodyFunction, BodyRegion, DamageType, HarmCause, InjuryKind, StrikeStyle
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import TerrainKind, TerrainTrait, WeatherKind, WeatherTrait
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.mind import Attribute, SkillKind, TraitEffect, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepLocus, StepOutcome, StepState
from aerona.engine.body.book import anatomy_for, effective, ensure_body
from aerona.engine.body.hits import Harm
from aerona.engine.body.strike import worn_layers
from aerona.engine.body.variants import folk_biology, shaped
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import mount_of, mounted_power
from aerona.engine.economy.sanctity import holy_strike
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.arms import best_weapon, burden_of, grip, guard_of, held_profiles, war_magic, ward_magic
from aerona.engine.mind.book import effect_of, scaled_by, skill_level, values_for
from aerona.engine.mind.inspiration import resolute
from aerona.engine.mind.split import attribute
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.primitives.strength import equipment, weapon_power
from aerona.engine.recording.record import FactInput, StepDraft, record
from aerona.engine.relations.passions import invoke
from aerona.rules.registry import Rules

ARMOUR_CAP = 0.8
SLIPPERY = terrains(TerrainTrait.SLIPPERY)
REACH_ITEMS = 2
LANCES = frozenset({ItemClass.SPEAR, ItemClass.POLEARM})
WEAPON_SKILLS: Mapping[ItemClass, SkillKind] = {
    ItemClass.BLADE: SkillKind.BLADE,
    ItemClass.LONGBLADE: SkillKind.BLADE,
    ItemClass.AXE: SkillKind.AXE,
    ItemClass.SPEAR: SkillKind.SPEAR,
    ItemClass.POLEARM: SkillKind.SPEAR,
    ItemClass.MACE: SkillKind.BLUNT,
    ItemClass.STAFF: SkillKind.BLUNT,
    ItemClass.THROWING: SkillKind.THROWING,
    ItemClass.BOW: SkillKind.BOW,
    ItemClass.CROSSBOW: SkillKind.BOW,
    ItemClass.SLING: SkillKind.SLING,
}
WEAPON_DAMAGE: Mapping[ItemClass, DamageType] = {
    ItemClass.BLADE: DamageType.CUT,
    ItemClass.LONGBLADE: DamageType.CUT,
    ItemClass.AXE: DamageType.CUT,
    ItemClass.SPEAR: DamageType.PIERCE,
    ItemClass.POLEARM: DamageType.PIERCE,
    ItemClass.THROWING: DamageType.PIERCE,
    ItemClass.BOW: DamageType.PIERCE,
    ItemClass.CROSSBOW: DamageType.PIERCE,
}
LOOSED: Mapping[ItemClass, StepAction] = {
    ItemClass.BOW: StepAction.SHOOT,
    ItemClass.CROSSBOW: StepAction.SHOOT,
    ItemClass.SLING: StepAction.SHOOT,
    ItemClass.FIREARM: StepAction.SHOOT,
    ItemClass.THROWING: StepAction.THROW,
}
REGION_WEIGHTS: Mapping[BodyRegion, int] = {
    BodyRegion.TORSO: 40,
    BodyRegion.ARMS: 25,
    BodyRegion.LEGS: 20,
    BodyRegion.HEAD: 15,
    BodyRegion.WINGS: 5,
    BodyRegion.TAIL: 5,
}
UNARMED_KEY = "hand"
TEETH_KEY = "teeth"


@dataclass
class Fighter:
    entity: EntityRow
    power: float
    hp: int
    armour: int
    reach: int
    honour: int
    mercy: int
    burden: int = 0
    stamina: int = PERCENT
    harm: int = 0
    disarmed: bool = False
    footing: int = PERCENT
    pain: int = 0
    cut: float = 1.0
    weapon_id: int | None = None
    weapon_class: ItemClass | None = None
    damage: DamageType = DamageType.BLUNT
    weapon_skill: int = 0
    shield: bool = False
    shield_skill: int = 0
    unarmed_skill: int = 0
    mounted_skill: int = 0
    feint: int = 0
    read: int = 0
    agility: int = 0
    mount_id: int | None = None
    mount_hp: int = 0
    mount_harm: int = 0
    parts: Mapping[BodyRegion, tuple[str, ...]] = field(default_factory=dict)
    arms: tuple[str, ...] = ()
    prone: bool = False
    conscious: bool = True
    feinted: bool = False


@dataclass(frozen=True)
class Exchange:
    action: StepAction
    actor: int
    target: int | None
    round: int
    parent: int | None = None
    instrument_kind: InstrumentKind = InstrumentKind.NONE
    instrument_node: int | None = None
    instrument_key: str | None = None
    part: str | None = None
    damage_type: DamageType | None = None
    harm: int = 0
    outcome: StepOutcome | None = None
    states: tuple[tuple[int, StepState], ...] = ()
    kind: InjuryKind | None = None


@dataclass
class Bout:
    winner: Fighter
    loser: Fighter
    end: DuelEnd
    context: DuelContext
    exchanges: int
    killed: bool = False
    spared: bool = False
    steps: list[Exchange] = field(default_factory=list)

    @property
    def hits(self) -> list[tuple[int, int]]:
        return [(step.target, step.harm) for step in self.steps if step.harm > 0 and step.target is not None]


async def heroic_effort(ctx: TickContext, hero: EntityRow) -> float:
    table = ctx.rules.aspirations
    lift = 1 + table.resolve_pct / PERCENT if await resolute(ctx.session, hero.id) else 1.0
    profile = await ctx.session.get(MortalProfileRow, hero.id)
    if profile is not None and profile.conviction >= table.conviction_spend and table.conviction_spend and not is_held(profile, "conviction"):
        profile.conviction -= table.conviction_spend
        lift *= 1 + table.conviction_spend_pct / PERCENT
    return lift


async def exposed_parts(ctx: TickContext, hero: EntityRow) -> tuple[dict[BodyRegion, tuple[str, ...]], tuple[str, ...]]:
    body = await ensure_body(ctx.session, ctx.rules, hero, ctx.epoch)
    anatomy = shaped(anatomy_for(body), await folk_biology(ctx.session, hero))
    found: dict[BodyRegion, tuple[str, ...]] = {}
    for region in BodyRegion:
        keys = tuple(part.key.value for part in anatomy.in_region(region) if not part.internal)
        if keys:
            found[region] = keys
    arms = tuple(part.key.value for part in anatomy.with_function(BodyFunction.GRASP) if not part.internal)
    return found, arms


def weapon_damage(blade: ItemProfileRow | None) -> DamageType:
    if blade is None:
        return DamageType.BLUNT
    named = next((kind for kind in DamageType if kind.value == blade.damage_type), None)
    return named or WEAPON_DAMAGE.get(blade.item_class, DamageType.BLUNT)


async def fighter(ctx: TickContext, hero: EntityRow, foe: EntityRow | None = None) -> Fighter:
    campaigns = ctx.rules.campaigns
    nerve = scaled_by(await effect_of(ctx.session, hero.id, TraitEffect.COURAGE, ctx.rules.traits.effect_scale_pct))
    agility = await effective(ctx.session, hero, "agility", rules=ctx.rules)
    base = (
        await effective(ctx.session, hero, "strength", rules=ctx.rules)
        + agility / campaigns.duel_agility_divisor
        + await weapon_power(ctx.session, ctx.rules, hero.id, campaigns.duel_weapon_mult)
    ) * nerve
    items = await equipment(ctx.session, hero.id)
    values = await values_for(ctx.session, hero.id)
    held = await held_profiles(ctx.session, hero.id)
    broken = ctx.rules.item_wear.broken
    blade = best_weapon(held, broken)
    reach = blade.reach if blade is not None else min(REACH_ITEMS, sum(1 for item in items if (stat(item, "damage") or 0) > 0))
    magic = await war_magic(ctx.session, ctx.rules, blade)
    holy = await holy_strike(ctx.session, ctx.rules, hero.id, foe)
    holy *= await heroic_effort(ctx, hero)
    holy *= await invoke(ctx, hero, [foe.id] if foe is not None else None)
    mount = await mount_of(ctx, hero.id)
    weapon_skill = await skill_level(ctx.session, hero.id, WEAPON_SKILLS[blade.item_class]) if blade is not None and blade.item_class in WEAPON_SKILLS else 0
    parts, arms = await exposed_parts(ctx, hero)
    return Fighter(
        entity=hero,
        power=base * (grip(blade) if blade is not None else 1.0) * magic * await mounted_power(ctx, hero.id) * holy,
        hp=stat_or(hero, "hp", campaigns.hero_default_hp),
        armour=sum(stat(item, "protection") or 0 for item in items) + guard_of(held, broken) + await ward_magic(ctx.session, ctx.rules, held),
        reach=reach,
        honour=values.get(ValueAxis.HONOUR, 0),
        mercy=values.get(ValueAxis.MERCY, 0),
        burden=burden_of(held, broken) * ctx.rules.item_powers.weight_fatigue_pct // PERCENT + await armour_burden(ctx, hero.id),
        stamina=PERCENT - await spent_strength(ctx, hero.id),
        cut=await ctx.hook_factor(hero.id, DomainHook.DUEL_WOUNDS),
        weapon_id=blade.item_entity_id if blade is not None else None,
        weapon_class=blade.item_class if blade is not None else None,
        damage=weapon_damage(blade),
        weapon_skill=weapon_skill,
        shield=any(row.item_class is ItemClass.SHIELD and row.condition >= max(1, broken) for row in held),
        shield_skill=await skill_level(ctx.session, hero.id, SkillKind.SHIELD),
        unarmed_skill=await skill_level(ctx.session, hero.id, SkillKind.UNARMED),
        mounted_skill=await skill_level(ctx.session, hero.id, SkillKind.MOUNTED_COMBAT) if mount is not None else 0,
        feint=await skill_level(ctx.session, hero.id, SkillKind.DECEPTION),
        read=await attribute(ctx.session, ctx.rules, hero, Attribute.INTUITION),
        agility=round_half_up(agility),
        mount_id=mount.id if mount is not None else None,
        mount_hp=stat_or(mount, "hp", campaigns.hero_default_hp) if mount is not None else 0,
        parts=parts,
        arms=arms,
    )


async def armour_burden(ctx: TickContext, hero_id: int) -> int:
    layers = await worn_layers(ctx.session, hero_id)
    density = sum(layer.props.density for layer in layers) / len(layers) if layers else 0
    return round(density * ctx.rules.tissues.duel_density_burden / PERCENT)


async def spent_strength(ctx: TickContext, hero_id: int) -> int:
    body = await ctx.session.get(BodyRow, hero_id)
    return body.exertion if body is not None else 0


def swing(rules: Rules, rng: SeededRandom, fighter: Fighter, foe: Fighter, first: bool) -> float:
    campaigns, table = rules.campaigns, rules.duels
    reach = 1 + table.reach_pct / PERCENT if first and fighter.reach > foe.reach else 1.0
    armed = 0.3 if fighter.disarmed else 1.0
    footing = fighter.footing / PERCENT
    pain = max(0.2, 1 - fighter.pain / (2 * PERCENT))
    prone = 1 - table.prone_penalty_pct / PERCENT if fighter.prone else 1.0
    return (
        fighter.power * (0.5 + fighter.stamina / (2 * PERCENT)) * reach * armed * footing * pain * prone + rng.die(campaigns.duel_die) * campaigns.duel_die_mult
    )


def wound(rules: Rules, target: Fighter, margin: float, total: float, cut: float = 1.0) -> int:
    table = rules.duels
    shield = min(ARMOUR_CAP, target.armour / PERCENT * table.armour_pct / PERCENT)
    harm = round_half_up(table.hit_hp * (0.5 + margin / max(1.0, total)) * (1 - shield) * cut)
    target.harm += harm
    target.pain = min(PERCENT, target.pain + round_half_up(harm * table.pain_pct / PERCENT))
    if harm >= table.hit_hp:
        target.footing = max(table.footing_floor, target.footing - table.stagger)
    return harm


def instrument_of(fighter: Fighter) -> tuple[InstrumentKind, int | None, str]:
    if fighter.disarmed or fighter.weapon_id is None or fighter.weapon_class is None:
        return InstrumentKind.BODY, None, UNARMED_KEY
    return InstrumentKind.ITEM, fighter.weapon_id, fighter.weapon_class.value


def blow_of(attacker: Fighter, kind: InstrumentKind, damage: DamageType) -> StepAction:
    loosed = LOOSED.get(attacker.weapon_class) if kind is InstrumentKind.ITEM and attacker.weapon_class is not None else None
    return loosed or DAMAGE[damage].blow or StepAction.STRIKE


def pick(rng: SeededRandom, keys: tuple[str, ...]) -> str | None:
    return keys[rng.below(len(keys))] if keys else None


def aimed_part(rules: Rules, rng: SeededRandom, striker: Fighter, target: Fighter) -> str | None:
    if not target.parts:
        return None
    if striker.weapon_skill >= rules.duels.called_shot_skill:
        armed = target.shield or not target.disarmed
        wanted = (target.arms or target.parts.get(BodyRegion.ARMS, ())) if armed else target.parts.get(BodyRegion.HEAD, ())
        if wanted:
            return pick(rng, wanted)
    weights = {region: float(REGION_WEIGHTS.get(region, 1)) for region in target.parts}
    roll = rng.random() * sum(weights.values())
    for region, weight in weights.items():
        roll -= weight
        if roll < 0:
            return pick(rng, target.parts[region])
    return pick(rng, next(iter(target.parts.values())))


def defence_of(defender: Fighter) -> tuple[StepAction, StepOutcome, int] | None:
    if defender.prone or not defender.conscious:
        return None
    options: list[tuple[int, StepAction, StepOutcome]] = [(defender.agility, StepAction.DODGE, StepOutcome.DODGED)]
    if defender.shield:
        options.append((defender.shield_skill, StepAction.BLOCK, StepOutcome.BLOCKED))
    if not defender.disarmed and defender.weapon_id is not None:
        options.append((defender.weapon_skill, StepAction.PARRY, StepOutcome.PARRIED))
    skill, action, outcome = max(options, key=lambda option: (option[0], option[1].value))
    return action, outcome, skill


def reads(rules: Rules, rng: SeededRandom, attacker: Fighter, defender: Fighter, skill: int) -> bool:
    table = rules.duels
    edge = table.feint_edge_pct if attacker.feinted else 0
    guard = defender.read * table.read_weight_pct / PERCENT + skill * (PERCENT - table.read_weight_pct) / PERCENT
    trick = attacker.feint * table.read_weight_pct / PERCENT + attacker.weapon_skill * (PERCENT - table.read_weight_pct) / PERCENT + edge
    chance = max(table.read_floor_pct, min(PERCENT - table.read_floor_pct, round_half_up(table.read_base_pct + (guard - trick) / 2)))
    return rng.chance(chance)


@dataclass
class Duel:
    rules: Rules
    rng: SeededRandom
    first: Fighter
    second: Fighter
    context: DuelContext
    ending: DuelEnd | None = None
    steps: list[Exchange] = field(default_factory=list)

    def add(self, step: Exchange) -> int:
        self.steps.append(step)
        return len(self.steps) - 1

    def strike(self, attacker: Fighter, defender: Fighter, round_no: int, *, rising: bool = False, charge: bool = False) -> None:
        table = self.rules.duels
        kind, node, key = instrument_of(attacker)
        damage = DamageType.BLUNT if kind is InstrumentKind.BODY else attacker.damage
        action = StepAction.CHARGE if charge else blow_of(attacker, kind, damage)
        if defender.mount_id is not None and not charge and self.rng.chance(table.mount_target_pct):
            self.strike_mount(attacker, defender, round_no, action=action, kind=kind, node=node, key=key, damage=damage)
            return
        part = aimed_part(self.rules, self.rng, attacker, defender)
        defence = None if rising else defence_of(defender)
        if defence is not None and reads(self.rules, self.rng, attacker, defender, defence[2]):
            attacker.feinted = False
            parent = self.add(Exchange(action, attacker.entity.id, defender.entity.id, round_no, None, kind, node, key, part, damage, 0, defence[1]))
            self.add(Exchange(defence[0], defender.entity.id, attacker.entity.id, round_no, parent, outcome=StepOutcome.SUCCESS))
            margin = abs(swing(self.rules, self.rng, defender, attacker, False) - swing(self.rules, self.rng, attacker, defender, False))
            if defence[0] is StepAction.PARRY and not attacker.disarmed and self.rng.chance(table.disarm_chance) and margin < table.hit_hp:
                attacker.disarmed = True
                disarming = Exchange(
                    StepAction.DISARM,
                    defender.entity.id,
                    attacker.entity.id,
                    round_no,
                    parent,
                    outcome=StepOutcome.SUCCESS,
                    states=((attacker.entity.id, StepState.DISARMED),),
                )
                self.add(disarming)
            return
        attacker.feinted = False
        roll_a = swing(self.rules, self.rng, attacker, defender, round_no == 1)
        roll_b = swing(self.rules, self.rng, defender, attacker, round_no == 1)
        margin, total = max(0.0, roll_a - roll_b / 2), max(roll_a, roll_b, 1.0)
        if charge:
            margin *= 1 + table.couched_charge_pct / PERCENT
        if rising:
            margin *= 1 + table.rise_strike_pct / PERCENT
        harm = wound(self.rules, defender, margin, total, attacker.cut)
        outcome = StepOutcome.WOUNDED if harm * 2 >= table.hit_hp else StepOutcome.GLANCED
        index = self.add(Exchange(action, attacker.entity.id, defender.entity.id, round_no, None, kind, node, key, part, damage, harm, outcome))
        if harm >= table.hit_hp and not defender.prone and self.rng.chance(table.knockdown_pct):
            defender.prone = True
            self.add(
                Exchange(
                    StepAction.FALL, defender.entity.id, None, round_no, index, outcome=StepOutcome.DOWNED, states=((defender.entity.id, StepState.PRONE),)
                )
            )

    def strike_mount(
        self, attacker: Fighter, rider: Fighter, round_no: int, *, action: StepAction, kind: InstrumentKind, node: int | None, key: str, damage: DamageType
    ) -> None:
        table = self.rules.duels
        mount_id = rider.mount_id
        if mount_id is None:
            return
        harm = round_half_up(table.hit_hp * (0.5 + self.rng.random() / 2))
        rider.mount_harm += harm
        index = self.add(Exchange(action, attacker.entity.id, mount_id, round_no, None, kind, node, key, None, damage, harm, StepOutcome.WOUNDED))
        if rider.mount_harm * PERCENT < rider.mount_hp * table.mount_fall_pct:
            return
        rider.mount_id = None
        rider.prone = True
        rider.harm += table.fall_hp
        fall = Exchange(
            StepAction.FALL,
            rider.entity.id,
            rider.entity.id,
            round_no,
            index,
            InstrumentKind.CREATURE,
            mount_id,
            None,
            pick(self.rng, rider.parts.get(BodyRegion.LEGS, ())),
            DamageType.BLUNT,
            table.fall_hp,
            StepOutcome.DOWNED,
            ((rider.entity.id, StepState.PRONE),),
            InjuryKind.CRUSH,
        )
        self.add(fall)

    def grapple(self, attacker: Fighter, defender: Fighter, round_no: int) -> None:
        table = self.rules.duels
        hold = attacker.unarmed_skill + self.rng.die(table.grapple_die)
        slip = defender.unarmed_skill + defender.agility / 2 + self.rng.die(table.grapple_die)
        held = hold >= slip
        grip_step = Exchange(
            StepAction.GRAPPLE,
            attacker.entity.id,
            defender.entity.id,
            round_no,
            None,
            InstrumentKind.BODY,
            None,
            UNARMED_KEY,
            outcome=StepOutcome.SUCCESS if held else StepOutcome.FAILURE,
        )
        parent = self.add(grip_step)
        if not held:
            return
        if attacker.harm * 2 >= attacker.hp and attacker.honour <= table.bite_honour:
            harm = wound(self.rules, defender, table.hit_hp / 2, table.hit_hp, attacker.cut)
            part = aimed_part(self.rules, self.rng, attacker, defender)
            self.add(
                Exchange(
                    StepAction.BITE,
                    attacker.entity.id,
                    defender.entity.id,
                    round_no,
                    parent,
                    InstrumentKind.BODY,
                    None,
                    TEETH_KEY,
                    part,
                    DamageType.PIERCE,
                    harm,
                    StepOutcome.WOUNDED,
                    kind=InjuryKind.BITE,
                )
            )
            return
        if not defender.prone:
            defender.prone = True
            harm = wound(self.rules, defender, table.hit_hp / 4, table.hit_hp, 1.0)
            part = pick(self.rng, defender.parts.get(BodyRegion.TORSO, ()))
            states = ((defender.entity.id, StepState.PRONE),)
            self.add(
                Exchange(
                    StepAction.THROW_DOWN,
                    attacker.entity.id,
                    defender.entity.id,
                    round_no,
                    parent,
                    InstrumentKind.BODY,
                    None,
                    UNARMED_KEY,
                    part,
                    DamageType.BLUNT,
                    harm,
                    StepOutcome.DOWNED,
                    states,
                )
            )
            return
        if self.rng.chance(table.choke_chance):
            defender.conscious = False
            states = ((defender.entity.id, StepState.UNCONSCIOUS),)
            self.add(
                Exchange(
                    StepAction.CHOKE,
                    attacker.entity.id,
                    defender.entity.id,
                    round_no,
                    parent,
                    InstrumentKind.BODY,
                    None,
                    UNARMED_KEY,
                    outcome=StepOutcome.DOWNED,
                    states=states,
                )
            )
            return
        harm = wound(self.rules, defender, table.hit_hp, table.hit_hp, 1.0)
        part = pick(self.rng, defender.arms or defender.parts.get(BodyRegion.ARMS, ()) or defender.parts.get(BodyRegion.LEGS, ()))
        self.add(
            Exchange(
                StepAction.LOCK,
                attacker.entity.id,
                defender.entity.id,
                round_no,
                parent,
                InstrumentKind.BODY,
                None,
                UNARMED_KEY,
                part,
                DamageType.BLUNT,
                harm,
                StepOutcome.BROKEN,
                ((defender.entity.id, StepState.RESTRAINED),),
                InjuryKind.FRACTURE,
            )
        )

    def speed(self, one: Fighter, other: Fighter, far: bool) -> float:
        table = self.rules.duels
        reach = table.reach_initiative if far and one.reach > other.reach else 0
        return one.agility + reach + self.rng.die(table.initiative_die) - (table.prone_initiative if one.prone else 0)

    def initiative(self, far: bool) -> tuple[Fighter, Fighter]:
        a, b = self.speed(self.first, self.second, far), self.speed(self.second, self.first, far)
        return (self.first, self.second) if a >= b else (self.second, self.first)

    def act(self, attacker: Fighter, defender: Fighter, round_no: int, far: bool) -> bool:
        table = self.rules.duels
        if far and attacker.reach < defender.reach:
            self.add(Exchange(StepAction.CLOSE, attacker.entity.id, defender.entity.id, round_no, outcome=StepOutcome.SUCCESS))
            far = False
        if not attacker.conscious:
            return far
        if attacker.prone:
            attacker.prone = False
            self.add(
                Exchange(StepAction.RISE, attacker.entity.id, None, round_no, outcome=StepOutcome.SUCCESS, states=((attacker.entity.id, StepState.RISEN),))
            )
            if defender.conscious and not defender.prone and self.rng.chance(table.rise_punish_chance):
                self.strike(defender, attacker, round_no, rising=True)
            return far
        if attacker.mount_id is not None and round_no == 1 and attacker.weapon_class in LANCES and not attacker.disarmed:
            self.strike(attacker, defender, round_no, charge=True)
            return far
        close_quarters = not far and attacker.unarmed_skill >= attacker.weapon_skill
        if attacker.disarmed or (close_quarters and self.rng.chance(table.grapple_chance)):
            self.grapple(attacker, defender, round_no)
            return far
        if attacker.feint >= table.feint_skill and self.rng.chance(table.feint_chance):
            attacker.feinted = True
            self.add(Exchange(StepAction.FEINT, attacker.entity.id, defender.entity.id, round_no, outcome=StepOutcome.SUCCESS))
        self.strike(attacker, defender, round_no)
        return far

    def bounded(self, winner: Fighter, loser: Fighter, round_no: int) -> Bout | None:
        table = self.rules.duels
        if self.ending is DuelEnd.FIRST_WOUND and loser.harm > 0 and loser.harm < loser.hp and loser.conscious:
            self.add(
                Exchange(
                    StepAction.YIELD, loser.entity.id, winner.entity.id, round_no, outcome=StepOutcome.ACCEPTED, states=((loser.entity.id, StepState.YIELDED),)
                )
            )
            return Bout(winner, loser, DuelEnd.FIRST_WOUND, self.context, round_no, steps=self.steps)
        if self.ending is DuelEnd.RING_OUT and loser.conscious and (loser.prone or loser.footing <= table.ring_footing):
            self.add(Exchange(StepAction.FLEE, loser.entity.id, None, round_no, outcome=StepOutcome.SUCCESS, states=((loser.entity.id, StepState.FLEEING),)))
            return Bout(winner, loser, DuelEnd.RING_OUT, self.context, round_no, steps=self.steps)
        return None

    def ended(self, winner: Fighter, loser: Fighter, round_no: int) -> Bout | None:
        table = self.rules.duels
        marked = self.bounded(winner, loser, round_no)
        if marked is not None:
            return marked
        if loser.harm >= loser.hp or not loser.conscious:
            end, killed, spared = self.downed(winner, loser)
            if killed:
                self.add(Exchange(StepAction.FINISH, winner.entity.id, loser.entity.id, round_no, outcome=StepOutcome.KILLED))
            elif spared:
                self.add(Exchange(StepAction.SPARE, winner.entity.id, loser.entity.id, round_no, outcome=StepOutcome.ACCEPTED))
            return Bout(winner, loser, end, self.context, round_no, killed, spared, self.steps)
        beaten = loser.harm * 2 >= loser.hp or loser.disarmed
        if not beaten or loser.honour >= table.yield_honour or self.context is DuelContext.TRIAL:
            return None
        accepted = winner.mercy >= table.yield_refuse_mercy or winner.honour >= table.yield_honour
        yielding = Exchange(
            StepAction.YIELD,
            loser.entity.id,
            winner.entity.id,
            round_no,
            outcome=StepOutcome.ACCEPTED if accepted else StepOutcome.REFUSED,
            states=((loser.entity.id, StepState.YIELDED),) if accepted else (),
        )
        self.add(yielding)
        if not accepted:
            return None
        return Bout(winner, loser, DuelEnd.DISARM if loser.disarmed else DuelEnd.YIELD, self.context, round_no, steps=self.steps)

    def downed(self, winner: Fighter, loser: Fighter) -> tuple[DuelEnd, bool, bool]:
        rules = self.rules
        beaten = DuelEnd.UNCONSCIOUS if not loser.conscious else DuelEnd.CRIPPLED
        if winner.mercy >= rules.duels.mercy_spare and self.context is not DuelContext.TRIAL:
            return beaten, False, True
        death = rules.duels.ritual_death_pct if self.context is DuelContext.RITUAL else rules.campaigns.duel_death_chance
        if self.rng.chance(death) or self.context is DuelContext.TRIAL:
            return DuelEnd.DEATH, True, False
        return beaten, False, False


def bout(rules: Rules, rng: SeededRandom, first: Fighter, second: Fighter, context: DuelContext, *, ending: DuelEnd | None = None) -> Bout:
    table = rules.duels
    count = table.exchanges_min + rng.below(max(1, table.exchanges_max - table.exchanges_min + 1))
    duel = Duel(rules, rng, first, second, context, ending)
    far = first.reach != second.reach
    for index in range(count):
        round_no = index + 1
        attacker, defender = duel.initiative(far)
        far = duel.act(attacker, defender, round_no, far)
        for one in (first, second):
            one.stamina = max(0, one.stamina - table.stamina_loss - one.burden)
        for winner, loser in ((attacker, defender), (defender, attacker)):
            done = duel.ended(winner, loser, round_no)
            if done is not None:
                return done
    winner, loser = (first, second) if first.harm <= second.harm else (second, first)
    return Bout(winner, loser, DuelEnd.EXHAUSTION, context, count, steps=duel.steps)


def set_footing(rules: Rules, fighter: Fighter, terrain: TerrainKind | None, weather: WeatherKind | None, injuries: int) -> None:
    table = rules.duels
    footing = PERCENT
    if terrain in SLIPPERY:
        footing -= table.terrain_footing
    if has_trait(weather, WeatherTrait.WET):
        footing -= table.weather_footing
    footing -= injuries * table.injury_footing
    fighter.footing = max(table.footing_floor, footing)


def drafts(result: Bout) -> list[StepDraft]:
    return [
        StepDraft(
            step.action,
            actor=step.actor,
            target=step.target,
            round=step.round,
            parent=step.parent,
            instrument_kind=step.instrument_kind,
            instrument_node=step.instrument_node,
            instrument_key=step.instrument_key,
            locus_kind=StepLocus.BODY_PART if step.part is not None else StepLocus.NONE,
            locus_key=step.part,
            damage_type=step.damage_type,
            amount=float(step.harm) if step.harm else None,
            unit=FactUnit.HP if step.harm else None,
            outcome=step.outcome,
            states=step.states,
        )
        for step in result.steps
    ]


def duel_facts(result: Bout, terrain: TerrainKind | None, weather: WeatherKind | None) -> dict[str, FactInput]:
    facts: dict[str, FactInput] = {"context": result.context, "exchanges": result.exchanges, "end": result.end}
    if terrain is not None:
        facts["terrain"] = terrain
    if weather is not None:
        facts["weather"] = weather
    if result.winner.weapon_id is not None:
        facts["winner_weapon"] = result.winner.weapon_id
    if result.loser.weapon_id is not None:
        facts["loser_weapon"] = result.loser.weapon_id
    return facts


async def settle_bout(
    ctx: TickContext,
    result: Bout,
    *,
    style: StrikeStyle = StrikeStyle.NORMAL,
    place_id: int | None = None,
    terrain: TerrainKind | None = None,
    weather: WeatherKind | None = None,
    cause: int | None = None,
    witnesses: tuple[int, ...] = (),
) -> int:
    winner, loser = result.winner.entity, result.loser.entity
    roles: dict[IncidentRole, int | tuple[int, ...]] = {IncidentRole.ACTOR: winner.id, IncidentRole.OPPONENT: loser.id}
    seen = tuple(node for node in witnesses if node not in (winner.id, loser.id))
    if seen:
        roles[IncidentRole.WITNESS] = seen
    written = await record(ctx, "duel.bout", roles=roles, facts=duel_facts(result, terrain, weather), steps=drafts(result), place=place_id, cause=cause)
    statement = select(IncidentStepRow).where(IncidentStepRow.incident_id == written.incident_id).order_by(IncidentStepRow.position)
    rows = list(await ctx.session.scalars(statement))
    for step, row in zip(result.steps, rows, strict=False):
        if step.harm <= 0 or step.target is None:
            continue
        target = await ctx.session.get(EntityRow, step.target)
        if target is None or target.status is not EntityStatus.CANON:
            continue
        striker = step.actor if step.actor != step.target else (step.instrument_node or step.actor)
        harm = Harm(
            step.harm,
            HarmCause.DUEL,
            "wounded in a duel",
            damage_type=step.damage_type,
            style=style,
            source_node_id=striker,
            killer_id=striker,
            part=step.part,
            kind=step.kind,
            step_id=row.id,
            incident_id=written.incident_id,
            instrument_kind=step.instrument_kind,
            instrument_key=step.instrument_key,
            instrument_node_id=step.instrument_node,
        )
        await apply_hits(ctx, target, harm, lethal=False)
        injury = await ctx.session.scalar(select(InjuryRow.id).where(InjuryRow.step_id == row.id).order_by(InjuryRow.id).limit(1))
        if injury is not None:
            row.record_table = InjuryRow.__tablename__
            row.record_key = str(injury)
    return written.incident_id


def crippling(rules: Rules, result: Bout, style: StrikeStyle) -> Harm:
    winner = result.winner.entity.id
    harm = Harm(rules.campaigns.duel_loser_hp_loss, HarmCause.DUEL, "crippled in a duel", source_node_id=winner, killer_id=winner, style=style)
    last = next((step for step in reversed(result.steps) if step.target == result.loser.entity.id and step.part is not None), None)
    return replace(harm, part=last.part, damage_type=last.damage_type) if last is not None else harm
