import math
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.constants.warfare import ARMY_NAME_TEMPLATE, LOG_FLOOR, WAR_NAME_TEMPLATE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, TributeRow, WarRow, WarSideRow
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import CaptiveStatus, TributeStatus, WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import ArmyStats, EventStats
from aerona.engine.body.book import effective
from aerona.engine.context import TickContext
from aerona.engine.demography.labour import fighting_age, mobilisation
from aerona.engine.economy.equipment import equip_army
from aerona.engine.gods.incitement import held_incitement
from aerona.engine.interconnect.flows import flowing
from aerona.engine.mind.hooks import freed, taken_captive
from aerona.engine.primitives.levies import levy, levy_category
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

ACTIVE_WAR_STATUSES = (WarStatus.MOBILIZING, WarStatus.ONGOING)
SUBJECT_BOND_KINDS = (BondKind.RULES, BondKind.PAYS_TRIBUTE)
PAIR_SIZE = 2


class WarBlock(StrEnum):
    SAME_PARTY = "same_party"
    NOT_LIVING = "not_living"
    OUT_OF_REACH = "out_of_reach"
    ALREADY_ENEMIES = "already_enemies"
    TRUCE = "truce"
    SUBJECT = "subject"
    WORLD_CAP = "world_cap"
    COMMUNITY_CAP = "community_cap"


@dataclass(frozen=True)
class OngoingWar:
    war: WarRow
    attacker_id: int
    defender_id: int

    @property
    def sides(self) -> tuple[int, int]:
        return (self.attacker_id, self.defender_id)

    def involves(self, entity_id: int) -> bool:
        return entity_id in self.sides

    def pair(self) -> frozenset[int]:
        return frozenset(self.sides)


DECLARATIONS_COUNTER = "epoch.declarations"


def unordered(first: int, second: int) -> frozenset[int]:
    return frozenset((first, second))


def is_community(entity: EntityRow | None) -> bool:
    return entity is not None and entity.entity_type in COMMUNITY_TYPES


async def uprising_target(session: AsyncSession, entity: EntityRow) -> EntityRow:
    rulers = await BondRepository(session).incoming(entity.id, BondKind.RULES)
    newest = max(rulers, key=lambda bond: bond.id, default=None)
    ruler = await living_entity(session, newest.source_node_id) if newest is not None else None
    return ruler if ruler is not None and is_community(ruler) and ruler.id != entity.id else entity


async def truce_bonds(session: AsyncSession, first: int, second: int) -> list[BondRow]:
    return await BondRepository(session).active_between(first, second, [BondKind.TRUCE])


def truce_until(rules: Rules, bond: BondRow) -> int:
    return bond.truce_until_epoch if bond.truce_until_epoch is not None else bond.epoch + rules.diplomacy.truce_epochs


async def has_truce(session: AsyncSession, rules: Rules, first: int, second: int, epoch: int) -> bool:
    return any(truce_until(rules, bond) > epoch for bond in await truce_bonds(session, first, second))


async def expire_truces(session: AsyncSession, rules: Rules, epoch: int) -> int:
    bonds = list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.TRUCE, BondRow.state == BondState.ACTIVE)))
    repository = BondRepository(session)
    expired = 0
    for bond in bonds:
        if truce_until(rules, bond) <= epoch:
            await repository.deactivate(bond, epoch, "truce expired")
            expired += 1
    return expired


async def ever_fought(session: AsyncSession, first: int, second: int) -> bool:
    statement = (
        select(WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_([first, second]))
        .group_by(WarSideRow.war_id)
        .having(func.count(func.distinct(WarSideRow.entity_id)) == PAIR_SIZE)
        .limit(1)
    )
    return await session.scalar(statement) is not None


async def grant_truce(ctx: TickContext, first: int, second: int, reason: str) -> bool:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if await has_truce(session, rules, first, second, epoch):
        return False
    until = epoch + rules.diplomacy.truce_epochs
    await BondRepository(session).connect(BondDraft(first, second, BondKind.TRUCE, epoch, f"{reason}; until Epoch {until}", truce_until_epoch=until))
    return True


async def war_sides(session: AsyncSession, war_id: int) -> list[WarSideRow]:
    statement = select(WarSideRow).where(WarSideRow.war_id == war_id, WarSideRow.left_epoch.is_(None)).order_by(WarSideRow.side, WarSideRow.entity_id)
    return list(await session.scalars(statement))


async def sides_of(session: AsyncSession, war: WarRow) -> tuple[int, int] | None:
    rows = await war_sides(session, war.id)
    attackers = [row.entity_id for row in rows if row.side is WarSide.ATTACKER]
    defenders = [row.entity_id for row in rows if row.side is WarSide.DEFENDER]
    if not attackers or not defenders:
        return None
    return attackers[0], defenders[0]


async def active_wars(session: AsyncSession) -> list[WarRow]:
    return list(await session.scalars(select(WarRow).where(WarRow.status.in_(ACTIVE_WAR_STATUSES)).order_by(WarRow.id)))


async def ongoing_wars(session: AsyncSession, side_id: int | None = None) -> list[OngoingWar]:
    result: list[OngoingWar] = []
    for war in await active_wars(session):
        sides = await sides_of(session, war)
        if sides is None:
            continue
        if await living_entity(session, sides[0]) is None or await living_entity(session, sides[1]) is None:
            continue
        if side_id is None or side_id in sides:
            result.append(OngoingWar(war, sides[0], sides[1]))
    return result


async def ongoing_war_count(session: AsyncSession, side_id: int | None = None) -> int:
    return len(await ongoing_wars(session, side_id))


async def current_war(session: AsyncSession, first: int, second: int) -> WarRow | None:
    pair = unordered(first, second)
    return next((item.war for item in await ongoing_wars(session, first) if item.pair() == pair), None)


async def hostile_pairs(session: AsyncSession) -> list[tuple[int, int, int]]:
    bonds = list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)))
    seen: dict[frozenset[int], tuple[int, int, int]] = {}
    for bond in bonds:
        key = unordered(bond.source_node_id, bond.target_node_id)
        first, second = await living_entity(session, bond.source_node_id), await living_entity(session, bond.target_node_id)
        if not is_community(first) or not is_community(second):
            continue
        previous = seen.get(key)
        if previous is None or bond.epoch < previous[2]:
            seen[key] = (bond.source_node_id, bond.target_node_id, bond.epoch)
    return list(seen.values())


async def hostile_pair_count(session: AsyncSession) -> int:
    return len(await hostile_pairs(session))


async def _party_block(session: AsyncSession, first_id: int, second_id: int) -> WarBlock | None:
    if first_id == second_id:
        return WarBlock.SAME_PARTY
    first, second = await living_entity(session, first_id), await living_entity(session, second_id)
    if first is None or second is None:
        return WarBlock.NOT_LIVING
    if first.world_id != second.world_id and not await WorldRepository(session).connected(first.world_id, second.world_id):
        return WarBlock.OUT_OF_REACH
    return None


async def _bond_block(session: AsyncSession, rules: Rules, first_id: int, second_id: int, epoch: int) -> WarBlock | None:
    bonds = BondRepository(session)
    if await bonds.exists_between(first_id, second_id, BondKind.ENEMY):
        return WarBlock.ALREADY_ENEMIES
    if await has_truce(session, rules, first_id, second_id, epoch):
        return WarBlock.TRUCE
    if await bonds.active_between(first_id, second_id, SUBJECT_BOND_KINDS):
        return WarBlock.SUBJECT
    return None


async def _cap_block(session: AsyncSession, rules: Rules, first_id: int, second_id: int, *, world_cap: bool, community_cap: bool) -> WarBlock | None:
    if not is_community(await living_entity(session, first_id)) or not is_community(await living_entity(session, second_id)):
        return None
    if world_cap and await ongoing_war_count(session) >= rules.diplomacy.world_war_cap:
        return WarBlock.WORLD_CAP
    cap = rules.diplomacy.community_war_cap
    if community_cap and (await ongoing_war_count(session, first_id) >= cap or await ongoing_war_count(session, second_id) >= cap):
        return WarBlock.COMMUNITY_CAP
    return None


async def can_open_war(
    session: AsyncSession, rules: Rules, first_id: int, second_id: int, epoch: int, *, world_cap: bool = True, community_cap: bool = False
) -> WarBlock | None:
    return (
        await _party_block(session, first_id, second_id)
        or await _bond_block(session, rules, first_id, second_id, epoch)
        or await _cap_block(session, rules, first_id, second_id, world_cap=world_cap, community_cap=community_cap)
    )


async def declare_war(
    ctx: TickContext,
    first_id: int,
    second_id: int,
    reason: str,
    *,
    cause: WarCause = WarCause.HOSTILITY,
    incited_by_son_id: int | None = None,
    world_cap: bool = True,
    community_cap: bool = False,
    since_epoch: int | None = None,
) -> bool:
    counters = ctx.environment.stats.counters
    if world_cap and counters[DECLARATIONS_COUNTER] >= ctx.rules.diplomacy.declarations_cap:
        return False
    if await can_open_war(ctx.session, ctx.rules, first_id, second_id, ctx.epoch, world_cap=world_cap, community_cap=community_cap) is not None:
        return False
    bonds = BondRepository(ctx.session)
    await bonds.close_between(first_id, second_id, [BondKind.ALLY, BondKind.TRADES_WITH], ctx.epoch, "war declared")
    epoch = since_epoch if since_epoch is not None else ctx.epoch
    await bonds.connect(BondDraft(first_id, second_id, BondKind.ENEMY, epoch, reason, war_cause=cause, incited_by_son_id=incited_by_son_id))
    ctx.count("hostilities_declared")
    if world_cap:
        counters[DECLARATIONS_COUNTER] += 1
    return True


async def require_war_block_free(ctx: TickContext, first_id: int, second_id: int, community_cap: bool) -> None:
    block = await can_open_war(ctx.session, ctx.rules, first_id, second_id, ctx.epoch, community_cap=community_cap)
    if block is not None:
        raise ConflictError(f"No war can open between these two: {block.value.replace('_', ' ')}.")


async def hostility_reason(session: AsyncSession, first: int, second: int) -> str | None:
    bonds = await BondRepository(session).active_between(first, second, [BondKind.ENEMY])
    described = [bond.description for bond in sorted(bonds, key=lambda bond: bond.id, reverse=True) if bond.description]
    return described[0] if described else None


async def hostility_origin(session: AsyncSession, first: int, second: int) -> BondRow | None:
    bonds = await BondRepository(session).active_between(first, second, [BondKind.ENEMY])
    return max(bonds, key=lambda bond: bond.id, default=None)


async def open_war(
    ctx: TickContext,
    attacker: EntityRow,
    defender: EntityRow,
    *,
    cause: WarCause = WarCause.HOSTILITY,
    cause_text: str | None = None,
    incited_by_son_id: int | None = None,
) -> WarRow:
    campaigns = ctx.rules.campaigns
    reason = cause_text or await hostility_reason(ctx.session, attacker.id, defender.id) or "old hostility"
    origin = await hostility_origin(ctx.session, attacker.id, defender.id)
    if cause is WarCause.HOSTILITY and origin is not None and origin.war_cause is not None:
        cause = origin.war_cause
    if incited_by_son_id is None and origin is not None:
        incited_by_son_id = origin.incited_by_son_id
    held, kept = await held_incitement(ctx.session, ctx.epoch, attacker.id, defender.id)
    if held:
        incited_by_son_id = kept
    location = defender.id if defender.entity_type is EntityType.SETTLEMENT else defender.location_id
    namer = Namer(ctx.session, ctx.rules)
    seed = seed_of(attacker.id, defender.id, ctx.epoch, "war")
    first = await namer.from_speaker(attacker.id, seed_of(seed, attacker.id), NameKind.PEOPLE) or attacker.name
    second = await namer.from_speaker(defender.id, seed_of(seed, defender.id), NameKind.PEOPLE) or defender.name
    derived = (first, second) != (attacker.name, defender.name)
    event = await create_record(
        ctx,
        RecordSpec(
            name=WAR_NAME_TEMPLATE.format(first=first, second=second),
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if derived else (),
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=campaigns.war_initial_severity),
            body=f"A war began between {attacker.name} and {defender.name}. Cause: {reason}.",
            power=campaigns.war_event_initial_power,
            world_id=defender.world_id,
            location_id=location,
            engine_kind=EngineKind.WAR,
        ),
    )
    status = WarStatus.MOBILIZING if campaigns.mobilization else WarStatus.ONGOING
    war = WarRow(
        event_entity_id=event.id,
        world_id=event.world_id,
        status=status,
        cause=cause,
        cause_text=reason,
        started_epoch=ctx.epoch,
        battles=0,
        score=0,
        violence=campaigns.war_initial_severity,
        incited_by_son_id=incited_by_son_id,
    )
    ctx.session.add(war)
    await ctx.session.flush()
    ctx.session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=attacker.id, side=WarSide.ATTACKER, joined_epoch=ctx.epoch),
            WarSideRow(war_id=war.id, entity_id=defender.id, side=WarSide.DEFENDER, joined_epoch=ctx.epoch),
        ]
    )
    await ctx.session.flush()
    bonds = BondRepository(ctx.session)
    for side in (attacker, defender):
        await bonds.connect(BondDraft(event.id, side.id, BondKind.PARTY_TO, ctx.epoch, "side", role=BondRole.SIDE, war_id=war.id))
    ctx.count("wars_opened")
    return war


async def war_event(session: AsyncSession, war: WarRow) -> EntityRow:
    event = await session.get(EntityRow, war.event_entity_id)
    if event is None:
        raise NotFoundError("The war has lost its record.")
    return event


async def require_ongoing_war(session: AsyncSession, war_id: int) -> OngoingWar:
    war = await session.get(WarRow, war_id)
    if war is None:
        raise NotFoundError("No such war.")
    if war.status not in ACTIVE_WAR_STATUSES:
        raise ConflictError("That war has already ended.")
    sides = await sides_of(session, war)
    if sides is None:
        raise ConflictError("That war has no two sides left.")
    return OngoingWar(war, sides[0], sides[1])


def soldier_count(rules: Rules, strength: MilitaryStrength, community: EntityRow) -> int:
    campaigns = rules.campaigns
    match community.entity_type:
        case EntityType.CULT:
            followers = stat(community, "followers") or campaigns.cult_default_followers
            return round_half_up(followers * campaigns.cult_soldier_pct / PERCENT)
        case EntityType.FACTION:
            power = stat(community, "strength") or campaigns.faction_default_strength
            wealth = stat(community, "wealth") or campaigns.faction_default_wealth
            return round_half_up(power * campaigns.faction_soldiers_per_strength + wealth * campaigns.faction_soldiers_per_wealth)
        case _:
            population = stat(community, "population") or campaigns.default_population
            share = max(campaigns.min_soldier_pct, strength.warrior_share(community)) / PERCENT
            return round_half_up(population * share)


async def army_of(session: AsyncSession, community_id: int, war_id: int) -> tuple[EntityRow, ArmyRow] | None:
    statement = select(ArmyRow).where(ArmyRow.owner_entity_id == community_id, ArmyRow.war_id == war_id, ArmyRow.disbanded_epoch.is_(None))
    for row in await session.scalars(statement.order_by(ArmyRow.entity_id)):
        army = await living_entity(session, row.entity_id)
        if army is not None:
            return army, row
    return None


async def commander_of(session: AsyncSession, army: ArmyRow) -> EntityRow | None:
    return await living_entity(session, army.commander_entity_id)


ARMY_KINDS = {EntityType.CULT: (EngineKind.HOLY_GUARD, "holy guard"), EntityType.FACTION: (EngineKind.MERCENARY_ARMY, "mercenary army")}
PEOPLES_ARMY = (EngineKind.PEOPLES_ARMY, "people's army")


async def harvest_share(ctx: TickContext, community: EntityRow) -> float:
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == community.world_id)))
    if not seasons:
        return 0.0
    top = max(season.growth for season in seasons)
    return sum(1 for season in seasons if season.growth == top) / len(seasons)


async def raise_army(ctx: TickContext, strength: MilitaryStrength, sides: SideIndex, community: EntityRow, war: WarRow) -> tuple[EntityRow, ArmyRow]:
    campaigns = ctx.rules.campaigns
    heroes = sides.heroes_of(community.id)
    scores = {
        hero.id: await effective(ctx.session, hero, "strength", rules=ctx.rules)
        + await effective(ctx.session, hero, "charisma", capacity=Capacity.COMMAND, rules=ctx.rules)
        for hero in heroes
    }
    commander = max(heroes, key=lambda hero: (scores[hero.id], -hero.id), default=None)
    engine_kind, subtype = ARMY_KINDS.get(community.entity_type, PEOPLES_ARMY)
    share = await mobilisation(ctx.session, ctx.rules, community, harvest_share=await harvest_share(ctx, community))
    wanted = clamp_int(soldier_count(ctx.rules, strength, community) * share, campaigns.army_min_soldiers, ctx.rules.limits.army_soldier_cap)
    adults = await fighting_age(ctx.session, community.id, ctx.rules)
    if adults is not None:
        wanted = max(campaigns.army_min_soldiers, min(wanted, adults))
    size = levy(ctx.rules, community, wanted)
    zeal_bonus = 0
    if community.entity_type is EntityType.CULT:
        zeal_bonus = round_half_up((stat(community, "zeal") or campaigns.default_zealotry) / campaigns.holy_guard_zealotry_divisor)
    morale = clamp_int(campaigns.army_morale_base + ctx.rng("army").die(campaigns.army_morale_die) + zeal_bonus, 0, PERCENT_MAX)
    metallurgy = campaigns.army_equipment_metallurgy if strength.knows(community.id, KnowledgeBranch.METALLURGY) else 0
    equipment = clamp_int(
        campaigns.army_equipment_base + await strength.weapon_power(community) * campaigns.army_equipment_weapon_mult + metallurgy, 0, PERCENT_MAX
    )
    experience = campaigns.army_experience_warcraft if strength.knows(community.id, KnowledgeBranch.WARFARE) else campaigns.army_experience
    event = await war_event(ctx.session, war)
    led = f"; {commander.name} leads it" if commander is not None else ""
    derived = await Namer(ctx.session, ctx.rules).from_speaker(community.id, seed_of(community.id, war.id, "army"), NameKind.ARMY)
    with flowing(levy_category(community)):
        army = await create_record(
            ctx,
            RecordSpec(
                name=ARMY_NAME_TEMPLATE.format(root=derived or community.name),
                flags=(EntityFlag.NAME_FROM_LANGUAGE,) if derived else (),
                entity_type=EntityType.ARMY,
                stats=ArmyStats(size=size, morale=morale, equipment=equipment, experience=experience),
                body=f"{community.name} raised an army of {size} for {event.name}{led}.",
                power=clamp_int(community.power_level, campaigns.army_power_min, campaigns.army_power_max),
                world_id=community.world_id,
                location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
                subtype=subtype,
                engine_kind=engine_kind,
            ),
        )
    kit = await equip_army(ctx, community, army, size)
    if kit.bonus:
        set_stats(army, equipment=clamp_int((stat(army, "equipment") or 0) + kit.bonus, 0, PERCENT_MAX))
    row = ArmyRow(
        entity_id=army.id,
        war_id=war.id,
        owner_entity_id=community.id,
        commander_entity_id=commander.id if commander is not None else None,
        raised_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(army.id, community.id, BondKind.PROTECTS, ctx.epoch, "serves"))
    await bonds.connect(BondDraft(army.id, event.id, BondKind.PART_OF, ctx.epoch, "army", war_id=war.id))
    if commander is not None:
        await bonds.connect(BondDraft(commander.id, army.id, BondKind.COMMANDS, ctx.epoch, "commands"))
        await bonds.connect(BondDraft(event.id, commander.id, BondKind.PARTY_TO, ctx.epoch, "commander", role=BondRole.COMMANDER, war_id=war.id))
    await ctx.session.flush()
    ctx.count("armies_raised")
    return army, row


async def mobilize_watch(ctx: TickContext, strength: MilitaryStrength, community: EntityRow, war: WarRow) -> tuple[EntityRow, ArmyRow] | None:
    statement = select(ArmyRow).where(ArmyRow.owner_entity_id == community.id, ArmyRow.war_id.is_(None), ArmyRow.disbanded_epoch.is_(None))
    for row in await ctx.session.scalars(statement.order_by(ArmyRow.entity_id)):
        army = await living_entity(ctx.session, row.entity_id)
        if army is None:
            continue
        row.war_id = war.id
        await EntityRepository(ctx.session).remove_flag(army.id, EntityFlag.ON_WATCH)
        size = clamp_int(soldier_count(ctx.rules, strength, community), ctx.rules.campaigns.army_min_soldiers, ctx.rules.limits.army_soldier_cap)
        set_stats(army, size=max(stat(army, "size") or 0, size))
        event = await war_event(ctx.session, war)
        await BondRepository(ctx.session).connect(BondDraft(army.id, event.id, BondKind.PART_OF, ctx.epoch, "army", war_id=war.id))
        await ctx.session.flush()
        return army, row
    return None


async def army_or_raise(ctx: TickContext, strength: MilitaryStrength, sides: SideIndex, community: EntityRow, war: WarRow) -> tuple[EntityRow, ArmyRow]:
    existing = await army_of(ctx.session, community.id, war.id) or await mobilize_watch(ctx, strength, community, war)
    return existing if existing is not None else await raise_army(ctx, strength, sides, community, war)


async def last_clash(session: AsyncSession, war: WarRow) -> int:
    if war.last_clash_epoch is not None:
        return war.last_clash_epoch
    latest: int | None = await session.scalar(select(func.max(BattleRow.epoch)).where(BattleRow.war_id == war.id))
    return latest if latest is not None else war.started_epoch


def violence_after(rules: Rules, war: WarRow, gap: float) -> int:
    campaigns = rules.campaigns
    current = war.violence if war.violence is not None else campaigns.war_initial_severity
    return clamp_int(current + campaigns.severity_per_battle + round_half_up(gap / campaigns.severity_diff_divisor), 0, PERCENT_MAX)


def log_size(size: int) -> float:
    return math.log10(max(LOG_FLOOR, size))


async def held_captive(session: AsyncSession, mortal_id: int) -> CaptiveRow | None:
    statement = select(CaptiveRow).where(CaptiveRow.captive_entity_id == mortal_id, CaptiveRow.status == CaptiveStatus.HELD)
    found: CaptiveRow | None = await session.scalar(statement.order_by(CaptiveRow.id).limit(1))
    return found


FREEING_STATUSES = frozenset({CaptiveStatus.RANSOMED, CaptiveStatus.ESCAPED, CaptiveStatus.RESCUED, CaptiveStatus.RELEASED})
RESCUE_STATUSES = frozenset({CaptiveStatus.RANSOMED, CaptiveStatus.RESCUED})


async def take_captive(ctx: TickContext, captor: EntityRow, captive: EntityRow, war: WarRow | None, *, description: str, home_id: int | None) -> CaptiveRow:
    existing = await held_captive(ctx.session, captive.id)
    if existing is not None:
        raise ConflictError(f"{captive.name} is already a prisoner.")
    bond = await BondRepository(ctx.session).connect(
        BondDraft(captor.id, captive.id, BondKind.HOLDS_CAPTIVE, ctx.epoch, description, war_id=war.id if war is not None else None)
    )
    row = CaptiveRow(
        captive_entity_id=captive.id,
        captor_entity_id=captor.id,
        home_entity_id=home_id,
        war_id=war.id if war is not None else None,
        bond_id=bond.id,
        status=CaptiveStatus.HELD,
        taken_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await taken_captive(ctx, captive.id, captor.id)
    return row


async def release_captive(ctx: TickContext, row: CaptiveRow, status: CaptiveStatus, ransom: int | None = None) -> None:
    if row.status is not CaptiveStatus.HELD:
        raise ConflictError("That prisoner is no longer held.")
    row.status = status
    row.released_epoch = ctx.epoch
    row.ransom_paid = ransom
    bonds = BondRepository(ctx.session)
    linked = await ctx.session.get(BondRow, row.bond_id) if row.bond_id is not None else None
    for bond in [linked] if linked is not None else await bonds.active_between(row.captor_entity_id, row.captive_entity_id, [BondKind.HOLDS_CAPTIVE]):
        if bond.state is BondState.ACTIVE:
            await bonds.deactivate(bond, ctx.epoch, status.value)
    await ctx.session.flush()
    captive = await ctx.session.get(EntityRow, row.captive_entity_id)
    if captive is not None and status in FREEING_STATUSES:
        await freed(ctx, captive, row.captor_entity_id, row.home_entity_id if status in RESCUE_STATUSES else None)


async def active_tribute(session: AsyncSession, payer_id: int, receiver_id: int) -> TributeRow | None:
    statement = select(TributeRow).where(
        TributeRow.payer_entity_id == payer_id, TributeRow.receiver_entity_id == receiver_id, TributeRow.status == TributeStatus.ACTIVE
    )
    found: TributeRow | None = await session.scalar(statement.order_by(TributeRow.id.desc()).limit(1))
    return found


async def impose_tribute(ctx: TickContext, payer: EntityRow, receiver: EntityRow, war: WarRow | None, description: str) -> TributeRow:
    if payer.id == receiver.id:
        raise ValidationFailedError("A community cannot pay tribute to itself.")
    bonds = BondRepository(ctx.session)
    existing = await active_tribute(ctx.session, payer.id, receiver.id)
    bond = await bonds.connect(BondDraft(payer.id, receiver.id, BondKind.PAYS_TRIBUTE, ctx.epoch, description, war_id=war.id if war else None))
    bond.epoch = ctx.epoch
    bond.description = description
    if existing is not None:
        existing.since_epoch = ctx.epoch
        existing.war_id = war.id if war is not None else existing.war_id
        existing.bond_id = bond.id
        await ctx.session.flush()
        return existing
    row = TributeRow(
        payer_entity_id=payer.id,
        receiver_entity_id=receiver.id,
        war_id=war.id if war is not None else None,
        bond_id=bond.id,
        status=TributeStatus.ACTIVE,
        since_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def end_tribute(ctx: TickContext, row: TributeRow, status: TributeStatus, reason: str) -> None:
    row.status = status
    row.ended_epoch = ctx.epoch
    bonds = BondRepository(ctx.session)
    linked = await ctx.session.get(BondRow, row.bond_id) if row.bond_id is not None else None
    candidates = [linked] if linked is not None else []
    if not await active_tribute(ctx.session, row.payer_entity_id, row.receiver_entity_id):
        candidates.extend(
            bond
            for bond in await bonds.active_between(row.payer_entity_id, row.receiver_entity_id, [BondKind.PAYS_TRIBUTE])
            if bond.source_node_id == row.payer_entity_id
        )
    for bond in candidates:
        if bond.state is BondState.ACTIVE:
            await bonds.deactivate(bond, ctx.epoch, reason)
    await ctx.session.flush()
