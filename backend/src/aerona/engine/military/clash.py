from math import sqrt

from sqlalchemy import func, select

from aerona.catalog.mind import COMBAT_SKILLS
from aerona.catalog.units import UNITS, UnitSpec
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import (
    ArmyOfficerRow,
    BattlePhaseRow,
    CaptiveCohortRow,
    CommanderTraitRow,
    LearnedTacticRow,
    SpyNetworkRow,
    UnitDesignRow,
)
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import ArmyRole, CaptiveFate, CommanderTrait, OutcomeClass, Tactic, UnitFamily
from aerona.domain.enums.mind import SkillKind, TraitEffect, ValueAxis
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.body.book import perception_of
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import battle_edge, profiles_of
from aerona.engine.ecology.beasts import beast_dread, mounted_edge
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.economy.sanctity import holy_strike
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.faith.souls import ancestral_site, guardians_of
from aerona.engine.lore.items import standard_of
from aerona.engine.lore.language import barrier
from aerona.engine.military.aftermath import flaring_items
from aerona.engine.military.battle import BattleResult, Field, Side, Stack, make_stacks, resolve
from aerona.engine.military.units import muster, profile_of, sync
from aerona.engine.mind.book import effect_of, scaled_by, values_for
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

EDGE_FLOOR, EDGE_CEILING = 0.5, 2.0
INSPIRING_CHARISMA = 70
CAVALRY_SHARE = 0.4
HILLS = frozenset({TerrainKind.HILLS, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
WINTER = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})
Armies = list[tuple[EntityRow, ArmyRow]]


async def skill_level(ctx: TickContext, mortal_id: int | None, skill: SkillKind) -> int:
    if mortal_id is None:
        return 0
    found = await ctx.session.scalar(select(func.max(SkillRow.level)).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill == skill))
    return int(found or 0)


async def traits_of(ctx: TickContext, mortal_id: int | None) -> set[CommanderTrait]:
    if mortal_id is None:
        return set()
    return set(await ctx.session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == mortal_id)))


async def side_owners(ctx: TickContext, community_id: int) -> list[int]:
    owners = [community_id]
    owners.extend(await ctx.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id)))
    return owners


async def intel_on(ctx: TickContext, owner_id: int, target_id: int) -> int:
    owners = await side_owners(ctx, owner_id)
    targets = await side_owners(ctx, target_id)
    by_owner = select(func.max(SpyNetworkRow.intel)).where(SpyNetworkRow.owner_entity_id.in_(owners), SpyNetworkRow.target_entity_id.in_(targets))
    by_side = select(func.max(SpyNetworkRow.intel)).where(SpyNetworkRow.side_entity_id == owner_id, SpyNetworkRow.target_entity_id.in_(targets))
    return max(int(await ctx.session.scalar(by_owner) or 0), int(await ctx.session.scalar(by_side) or 0))


async def warned(ctx: TickContext, owner_id: int, target_id: int) -> bool:
    targets = await side_owners(ctx, target_id)
    statement = select(SpyNetworkRow.id).where(
        SpyNetworkRow.side_entity_id == owner_id, SpyNetworkRow.target_entity_id.in_(targets), SpyNetworkRow.warned_epoch >= ctx.epoch - 1
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def design_specs(ctx: TickContext, design_ids: set[int]) -> dict[int, UnitSpec]:
    if not design_ids:
        return {}
    rows = await ctx.session.scalars(select(UnitDesignRow).where(UnitDesignRow.id.in_(design_ids)))
    return {row.id: design_spec(row) for row in rows}


def design_spec(row: UnitDesignRow) -> UnitSpec:
    base = UNITS[row.base_kind]
    return UnitSpec(
        kind=row.base_kind,
        family=row.family,
        label=row.name,
        melee=row.melee,
        missile=row.missile,
        defence=row.defence,
        speed=row.speed,
        mass=row.mass,
        cost=row.cost,
        upkeep=row.upkeep,
        armour=row.armour,
        shield=row.shield,
        branch=base.branch,
        level=base.level,
        social_class=row.social_class,
        counters_charge=row.counters_charge,
        terror=row.terror,
        terrain=dict(base.terrain),
        flying=row.flying,
    )


async def hardness_of(ctx: TickContext, world_id: int, materials: set[str]) -> dict[str, int]:
    book = await MaterialBook.load(ctx.session)
    found: dict[str, int] = {}
    for material in materials:
        try:
            props = book.props(world_id, MaterialKind(material))
        except ValueError:
            props = None
        if props is not None:
            found[material] = props.hardness
    return found


async def willpower_of(ctx: TickContext, community: EntityRow, commander_id: int | None) -> int:
    values = await values_for(ctx.session, community.id)
    grit = (values.get(ValueAxis.MARTIAL, 0) + values.get(ValueAxis.HONOUR, 0)) / 2
    base = (grit + PERCENT) / 2
    nerve = scaled_by(await effect_of(ctx.session, commander_id, TraitEffect.COURAGE, ctx.rules.traits.effect_scale_pct)) if commander_id is not None else 1.0
    return clamp_int(round(base * nerve), 0, PERCENT)


async def learned_of(ctx: TickContext, holders: list[int]) -> dict[Tactic, int]:
    found: dict[Tactic, int] = {}
    rows = await ctx.session.scalars(select(LearnedTacticRow).where(LearnedTacticRow.holder_entity_id.in_([item for item in holders if item])))
    for row in rows:
        found[row.tactic] = max(found.get(row.tactic, 0), row.wins)
    return found


async def sub_commander_bonus(ctx: TickContext, army_ids: list[int]) -> float:
    rows = await ctx.session.scalars(
        select(ArmyOfficerRow).where(
            ArmyOfficerRow.army_entity_id.in_(army_ids), ArmyOfficerRow.role == ArmyRole.SUB_COMMANDER, ArmyOfficerRow.until_epoch.is_(None)
        )
    )
    total = 0
    for row in rows:
        total += await skill_level(ctx, row.mortal_entity_id, SkillKind.LEADERSHIP)
    return min(PERCENT, total) / PERCENT * ctx.rules.campaign_depth.sub_commander_pct / PERCENT


async def surgeon_skill(ctx: TickContext, army_ids: list[int]) -> int:
    rows = await ctx.session.scalars(
        select(ArmyOfficerRow).where(ArmyOfficerRow.army_entity_id.in_(army_ids), ArmyOfficerRow.role == ArmyRole.SURGEON, ArmyOfficerRow.until_epoch.is_(None))
    )
    return max([await skill_level(ctx, row.mortal_entity_id, SkillKind.MEDICINE) for row in rows] or [0])


async def side_of(
    ctx: TickContext,
    community: EntityRow,
    armies: Armies,
    *,
    edge: float,
    defending: bool,
    enemy: EntityRow,
    knowledge: KnowledgeMap,
    ground: Field,
) -> Side:
    army, row = armies[0]
    rows = []
    for item, owner_row in armies:
        owner = community if owner_row.owner_entity_id == community.id else await ctx.session.get(EntityRow, owner_row.owner_entity_id)
        rows.extend(await muster(ctx, item, owner, knowledge))
    specs = await design_specs(ctx, {unit.design_id for unit in rows if unit.design_id})
    hardness = await hardness_of(ctx, community.world_id, {unit.material for unit in rows if unit.material})
    stacks = make_stacks(rows, specs, hardness)
    profile = await profile_of(ctx, army, community)
    table = ctx.rules
    commander = row.commander_entity_id
    lead = await skill_level(ctx, commander, SkillKind.LEADERSHIP)
    veteran = max([await skill_level(ctx, commander, skill) for skill in COMBAT_SKILLS] or [0])
    parts = {
        "leadership": round(PERCENT * table.morale.leadership_pct / PERCENT * lead / PERCENT),
        "faith": await faith_spirit(ctx, community, enemy, army.location_id),
        "babel": -await babel(ctx, community),
        "beast_dread": -await beast_dread(ctx, enemy.id),
        "warned": table.morale.warned_morale if await warned(ctx, community.id, enemy.id) else 0,
    }
    medicine = knowledge.level(community.id, KnowledgeBranch.MEDICINE) * PERCENT // max(1, table.morale.medicine_levels)
    medicine += await surgeon_skill(ctx, [item.id for item, _ in armies]) * table.battle_magic.surgeon_pct // PERCENT
    biology, culture = await profiles_of(ctx.session, community)
    kin = battle_edge(ctx.rules, biology, culture, terrain=ground.terrain, weather=ground.weather, night=ground.night, river=ground.river, defending=defending)
    return Side(
        veteran=table.military_units.veteran_skill_pct / PERCENT * veteran / PERCENT,
        leadership=sum(parts.values()),
        entity=community,
        army=army,
        profile=profile,
        stacks=stacks,
        edge=edge * kin * await holy_strike(ctx.session, table, army.id, enemy) * await mounted_edge(ctx, row.commander_entity_id),
        defending=defending,
        skill=await skill_level(ctx, commander, SkillKind.TACTICS),
        traits=await traits_of(ctx, commander),
        intel=await intel_on(ctx, community.id, enemy.id),
        willpower=await willpower_of(ctx, community, commander),
        learned=await learned_of(ctx, [community.id, commander or 0]),
        morale_parts=parts,
        wing_bonus=await sub_commander_bonus(ctx, [item.id for item, _ in armies]),
        medicine=clamp_int(medicine, 0, PERCENT),
        watch=await watchfulness(ctx, row.commander_entity_id),
    )


async def watchfulness(ctx: TickContext, commander_id: int | None) -> float:
    commander = await ctx.session.get(EntityRow, commander_id) if commander_id is not None else None
    if commander is None or commander.entity_type is not EntityType.MORTAL:
        return 0.0
    return await perception_of(ctx.session, ctx.rules, commander) * ctx.rules.capacities.scouting_perception_pct / PERCENT


async def babel(ctx: TickContext, community: EntityRow) -> int:
    realm = (await RealmBook.load(ctx.session)).realm_of(community.id)
    if realm is None:
        return 0
    for member in sorted(realm.members):
        if member != community.id and await barrier(ctx.session, ctx.rules, community.id, member, ctx.epoch) < 1:
            return ctx.rules.interpreters.army_cohesion_pct
    return 0


async def faith_spirit(ctx: TickContext, community: EntityRow, enemy: EntityRow, place_id: int | None = None) -> int:
    tenets = await faith_tenets(ctx.session, community.id)
    lift = 0
    if TenetKind.HOLY_WAR in tenets and await patron_node(ctx.session, community.id) != await patron_node(ctx.session, enemy.id):
        lift += ctx.rules.doctrine.holy_war_morale
    if TenetKind.ANCESTOR_VENERATION in tenets and await guardians_of(ctx, community.id) and await ancestral_site(ctx, community, place_id):
        lift += ctx.rules.spirits.guardian_morale
    return lift + await standard_of(ctx, [community.id])


async def leaders_of(ctx: TickContext, armies: Armies) -> list[EntityRow]:
    ids = {row.commander_entity_id for _, row in armies if row.commander_entity_id}
    officers = select(ArmyOfficerRow.mortal_entity_id).where(
        ArmyOfficerRow.army_entity_id.in_([army.id for army, _ in armies]), ArmyOfficerRow.until_epoch.is_(None)
    )
    ids.update(await ctx.session.scalars(officers))
    found = [await ctx.session.get(EntityRow, mortal_id) for mortal_id in sorted(ids)]
    return [mortal for mortal in found if mortal is not None]


def streams_for(ctx: TickContext, war_id: int, sequence: int) -> "StreamFactory":
    return StreamFactory(ctx, f"battle.{war_id}.{sequence}")


class StreamFactory:
    def __init__(self, ctx: TickContext, root: str) -> None:
        self.ctx = ctx
        self.root = root

    def __call__(self, key: str) -> SeededRandom:
        return self.ctx.rng(f"{self.root}.{key}")


async def clash(
    ctx: TickContext,
    war_id: int,
    sequence: int,
    armies: dict[int, Armies],
    sides: tuple[EntityRow, EntityRow],
    *,
    powers: tuple[float, float],
    ground: Field,
) -> BattleResult:
    attacker, defender = sides
    knowledge = await KnowledgeMap.load(ctx.session)
    mean = max(1e-6, (powers[0] + powers[1]) / 2)
    edges = [max(EDGE_FLOOR, min(EDGE_CEILING, sqrt(max(0.0, power) / mean))) for power in powers]
    first = await side_of(ctx, attacker, armies[attacker.id], edge=edges[0], defending=False, enemy=defender, knowledge=knowledge, ground=ground)
    second = await side_of(ctx, defender, armies[defender.id], edge=edges[1], defending=True, enemy=attacker, knowledge=knowledge, ground=ground)
    for side in (first, second):
        ctx.count("items_flared", await flaring_items(ctx, ground.weather, side, await leaders_of(ctx, armies[side.entity.id])))
    result = resolve(ctx.rules, streams_for(ctx, war_id, sequence), first, second, ground)
    for side in (first, second):
        for army, _ in armies[side.entity.id]:
            sync(army, [stack.row for stack in side.stacks if stack.row.army_entity_id == army.id], ctx.rules)
    return result


def stacks_by_army(side: Side) -> dict[int, list[Stack]]:
    found: dict[int, list[Stack]] = {}
    for stack in side.stacks:
        found.setdefault(stack.row.army_entity_id, []).append(stack)
    return found


def captives_taken(ctx: TickContext, result: BattleResult, war_id: int) -> int:
    if result.winner is None or result.loser is None or result.loser.captives <= 0:
        return 0
    ctx.session.add(
        CaptiveCohortRow(
            captor_entity_id=result.winner.entity.id,
            origin_entity_id=result.loser.entity.id,
            war_id=war_id,
            count=result.loser.captives,
            social_class=SocialClass.WARRIOR,
            fate=CaptiveFate.HELD,
            since_epoch=ctx.epoch,
        )
    )
    return result.loser.captives


def log_phases(ctx: TickContext, battle_id: int, result: BattleResult) -> None:
    for position, phase in enumerate(result.phases):
        ctx.session.add(
            BattlePhaseRow(
                battle_id=battle_id,
                position=position,
                phase=phase.phase.value,
                attacker_losses=phase.attacker_losses,
                defender_losses=phase.defender_losses,
                summary=phase.summary[:480],
                details=dict(phase.details),
            )
        )


def wanted_traits(side: Side, *, won: bool, result: BattleResult, ground: Field, charisma: int) -> list[CommanderTrait]:
    mounted = sum(stack.start for stack in side.stacks if stack.spec.family in {UnitFamily.MOUNTED, UnitFamily.BEAST}) / max(1, side.start)
    assaulting = side.tactic in {Tactic.FRONTAL_ASSAULT, Tactic.WEDGE}
    checks = (
        (won and side.defending and result.outcome in {OutcomeClass.DECISIVE, OutcomeClass.VICTORY}, CommanderTrait.DEFENSIVE_GENIUS),
        (won and assaulting and not side.defending, CommanderTrait.AGGRESSIVE_ASSAULTER),
        (won and mounted >= CAVALRY_SHARE, CommanderTrait.CAVALRY_MASTER),
        (won and ground.weather in WINTER, CommanderTrait.WINTER_CAMPAIGNER),
        (won and ground.terrain in HILLS, CommanderTrait.HILL_FIGHTER),
        (not won and assaulting, CommanderTrait.RECKLESS),
        (won and result.outcome is OutcomeClass.MASSACRE, CommanderTrait.BRUTAL),
        (charisma >= INSPIRING_CHARISMA, CommanderTrait.INSPIRING),
    )
    return [trait for hit, trait in checks if hit]


async def earn_traits(ctx: TickContext, result: BattleResult, ground: Field, commanders: dict[int, int | None]) -> int:
    if result.winner is None or result.loser is None:
        return 0
    earned = 0
    rng = ctx.rng(f"commander_traits.{ctx.epoch}.{result.winner.entity.id}")
    for side, won in ((result.winner, True), (result.loser, False)):
        commander_id = commanders.get(side.entity.id)
        if commander_id is None:
            continue
        commander = await ctx.session.get(EntityRow, commander_id)
        charisma = (stat(commander, "charisma") or 0) if commander is not None else 0
        held = await traits_of(ctx, commander_id)
        for trait in wanted_traits(side, won=won, result=result, ground=ground, charisma=charisma):
            if trait not in held and rng.chance(ctx.rules.morale.trait_chance_pct):
                ctx.session.add(CommanderTraitRow(mortal_entity_id=commander_id, trait=trait, since_epoch=ctx.epoch))
                held.add(trait)
                earned += 1
    return earned


async def learn_tactic(ctx: TickContext, result: BattleResult, commander_id: int | None) -> int:
    if result.winner is None or result.refused or result.outcome is OutcomeClass.STALEMATE:
        return 0
    learned = 0
    for holder in (result.winner.entity.id, commander_id):
        if holder is None:
            continue
        row = await ctx.session.get(LearnedTacticRow, (holder, result.winner.tactic))
        if row is None:
            row = LearnedTacticRow(holder_entity_id=holder, tactic=result.winner.tactic, wins=0, since_epoch=ctx.epoch)
            ctx.session.add(row)
        row.wins += 1
        learned += 1
    return learned


async def cautious(ctx: TickContext, commander_id: int | None) -> None:
    if commander_id is not None and CommanderTrait.CAUTIOUS not in await traits_of(ctx, commander_id):
        ctx.session.add(CommanderTraitRow(mortal_entity_id=commander_id, trait=CommanderTrait.CAUTIOUS, since_epoch=ctx.epoch))
