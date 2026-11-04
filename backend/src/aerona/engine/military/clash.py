from math import sqrt

from sqlalchemy import func, select

from aerona.catalog.mind import COMBAT_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import BattlePhaseRow, CaptiveCohortRow, CommanderTraitRow, SpyNetworkRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.military import CaptiveFate, CommanderTrait, OutcomeClass, Tactic, UnitFamily
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.faith.souls import guardians_of
from aerona.engine.lore.items import standard_of
from aerona.engine.lore.language import barrier
from aerona.engine.military.battle import BattleResult, Field, Side, make_stacks, resolve
from aerona.engine.military.units import muster, profile_of, sync
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.stats import stat

EDGE_FLOOR, EDGE_CEILING = 0.5, 2.0
INSPIRING_CHARISMA = 70
CAVALRY_SHARE = 0.4
HILLS = frozenset({TerrainKind.HILLS, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
WINTER = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})


async def skill_level(ctx: TickContext, mortal_id: int | None, skill: SkillKind) -> int:
    if mortal_id is None:
        return 0
    found = await ctx.session.scalar(select(func.max(SkillRow.level)).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill == skill))
    return int(found or 0)


async def traits_of(ctx: TickContext, mortal_id: int | None) -> set[CommanderTrait]:
    if mortal_id is None:
        return set()
    return set(await ctx.session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == mortal_id)))


async def intel_on(ctx: TickContext, owner_id: int, target_id: int) -> int:
    query = select(func.max(SpyNetworkRow.intel)).where(SpyNetworkRow.owner_entity_id == owner_id, SpyNetworkRow.target_entity_id == target_id)
    found = await ctx.session.scalar(query)
    return int(found or 0)


async def side_of(
    ctx: TickContext, community: EntityRow, army: EntityRow, row: ArmyRow, *, edge: float, defending: bool, enemy: EntityRow, knowledge: KnowledgeMap
) -> Side:
    stacks = make_stacks(await muster(ctx, army, community, knowledge))
    profile = await profile_of(ctx, army, community)
    table = ctx.rules
    lead = await skill_level(ctx, row.commander_entity_id, SkillKind.LEADERSHIP)
    veteran = max([await skill_level(ctx, row.commander_entity_id, skill) for skill in COMBAT_SKILLS] or [0])
    spirit = await faith_spirit(ctx, community, enemy) - await babel(ctx, community)
    return Side(
        veteran=table.military_units.veteran_skill_pct / PERCENT * veteran / PERCENT,
        leadership=round(PERCENT * table.morale.leadership_pct / PERCENT * lead / PERCENT) + spirit,
        entity=community,
        army=army,
        profile=profile,
        stacks=stacks,
        edge=edge,
        defending=defending,
        skill=await skill_level(ctx, row.commander_entity_id, SkillKind.TACTICS),
        traits=await traits_of(ctx, row.commander_entity_id),
        intel=await intel_on(ctx, community.id, enemy.id),
    )


async def babel(ctx: TickContext, community: EntityRow) -> int:
    realm = (await RealmBook.load(ctx.session)).realm_of(community.id)
    if realm is None:
        return 0
    for member in sorted(realm.members):
        if member != community.id and await barrier(ctx.session, ctx.rules, community.id, member, ctx.epoch) < 1:
            return ctx.rules.interpreters.army_cohesion_pct
    return 0


async def faith_spirit(ctx: TickContext, community: EntityRow, enemy: EntityRow) -> int:
    tenets = await faith_tenets(ctx.session, community.id)
    lift = 0
    if TenetKind.HOLY_WAR in tenets and await patron_node(ctx.session, community.id) != await patron_node(ctx.session, enemy.id):
        lift += ctx.rules.doctrine.holy_war_morale
    if TenetKind.ANCESTOR_VENERATION in tenets and await guardians_of(ctx, community.id):
        lift += ctx.rules.spirits.guardian_morale
    return lift + await standard_of(ctx, [community.id])


async def clash(
    ctx: TickContext,
    war_id: int,
    sequence: int,
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    sides: tuple[EntityRow, EntityRow],
    *,
    powers: tuple[float, float],
    ground: Field,
) -> BattleResult:
    attacker, defender = sides
    knowledge = await KnowledgeMap.load(ctx.session)
    mean = max(1e-6, (powers[0] + powers[1]) / 2)
    edges = [max(EDGE_FLOOR, min(EDGE_CEILING, sqrt(max(0.0, power) / mean))) for power in powers]
    first = await side_of(ctx, attacker, *armies[attacker.id], edge=edges[0], defending=False, enemy=defender, knowledge=knowledge)
    second = await side_of(ctx, defender, *armies[defender.id], edge=edges[1], defending=True, enemy=attacker, knowledge=knowledge)
    result = resolve(ctx.rules, ctx.rng(f"battle.{war_id}.{sequence}"), first, second, ground)
    for side in (first, second):
        sync(side.army, [stack.row for stack in side.stacks], ctx.rules)
    return result


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


async def cautious(ctx: TickContext, commander_id: int | None) -> None:
    if commander_id is not None and CommanderTrait.CAUTIOUS not in await traits_of(ctx, commander_id):
        ctx.session.add(CommanderTraitRow(mortal_entity_id=commander_id, trait=CommanderTrait.CAUTIOUS, since_epoch=ctx.epoch))
