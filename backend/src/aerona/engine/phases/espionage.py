from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.military import SabotageKind, SpyCover, SpyOperation
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.blueprints import steal_design
from aerona.engine.lore.research import steal_technique
from aerona.engine.military.feuds import house_feud
from aerona.engine.military.spycraft import (
    agents_of,
    blackmail_office,
    burn_district,
    catch_agent,
    cover_access,
    cover_exposure,
    cover_for,
    migrate_bonds,
    owner_kind,
    plant_claimant,
    recruit,
    retire_agents,
    reveal_aims,
    side_for,
    wound_ruler,
)
from aerona.engine.mind.book import skill_level
from aerona.engine.mind.drives import deceit_drive
from aerona.engine.mind.opinion import mortal_rulers
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, living_entity
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import move_stat, shift_stat, stat
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war, has_truce, uprising_target

SABOTAGED_STATS = ("defense", "strength", "wealth")
PRESSURE_STATS = ("influence", "sway", "defense")


async def _note(ctx: TickContext, text: str, key: str, ids: tuple[int, ...]) -> None:
    await ctx.chronicle(ChronicleKind.INTRIGUE, text, template_key=key, entity_ids=ids)


async def _targets(ctx: TickContext, faction: EntityRow) -> list[tuple[bool, int, EntityRow]]:
    bonds = BondRepository(ctx.session)
    ranked: list[tuple[bool, int, EntityRow]] = []
    for community in await canon(ctx.session, COMMUNITY_TYPES, faction.world_id):
        if community.id == faction.id:
            continue
        hostile = bool(await bonds.active_between(faction.id, community.id, [BondKind.ENEMY, BondKind.PAYS_TRIBUTE]))
        truce = await has_truce(ctx.session, ctx.rules, faction.id, community.id, ctx.epoch)
        value = await relation(ctx.session, ctx.rules, faction.id, community.id)
        if hostile or truce or value <= -ctx.rules.espionage.spy_target_relation:
            ranked.append((hostile, value, community))
    ranked.sort(key=lambda item: (not item[0], item[1], item[2].id))
    return ranked


async def would_spy(ctx: TickContext, owner: EntityRow) -> int | None:
    rules = ctx.rules.espionage
    if owner.entity_type is EntityType.FACTION:
        return rules.spy_net_chance if (stat(owner, "sway") or 0) >= rules.spy_min_sway else None
    if owner.entity_type is EntityType.POLITY:
        return rules.polity_spy_chance if await spymaster_of(ctx, owner.id) is not None else None
    if owner.entity_type is EntityType.CULT:
        return rules.spy_net_chance if (stat(owner, "zeal") or 0) >= rules.cult_spy_zeal else None
    return None


async def found_networks(ctx: TickContext) -> int:
    rules = ctx.rules.espionage
    rng = ctx.rng("networks")
    founded = 0
    owned = set(await ctx.session.scalars(select(SpyNetworkRow.owner_entity_id)))
    for owner in await canon(ctx.session, [EntityType.FACTION, EntityType.POLITY, EntityType.CULT]):
        if founded >= rules.spy_net_cap:
            break
        chance = await would_spy(ctx, owner)
        if chance is None or owner.id in owned:
            continue
        targets = await _targets(ctx, owner)
        if not targets:
            continue
        hostile, _, target = targets[0]
        if not rng.chance(chance + (rules.spy_net_enemy_bonus_pct if hostile else 0)):
            continue
        network = await network_for(ctx, owner, target, None)
        await ctx.session.flush()
        await recruit(ctx, network)
        founded += 1
        await _note(ctx, f"{owner.name} began building a secret agent network inside {target.name}.", "espionage.network_founded", (owner.id, target.id))
    return founded


def capture_chance(ctx: TickContext, target: EntityRow) -> float:
    rules = ctx.rules.espionage
    pressure = next((value for value in (stat(target, key) for key in PRESSURE_STATS) if value), rules.spy_capture_default)
    return rules.spy_capture_base_pct + PERCENT * pressure / rules.spy_capture_divisor


async def _stealable(ctx: TickContext, spymaster: EntityRow, target: EntityRow) -> list[EntityRow]:
    bonds = BondRepository(ctx.session)
    known = {bond.target_node_id for bond in await bonds.outgoing(spymaster.id, BondKind.KNOWS)}
    found: list[EntityRow] = []
    for bond in await bonds.outgoing(target.id, BondKind.KNOWS):
        knowledge = await living_entity(ctx.session, bond.target_node_id)
        if knowledge is not None and knowledge.entity_type is EntityType.KNOWLEDGE and knowledge.id not in known:
            found.append(knowledge)
    return found


async def steal(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    secret = await steal_technique(ctx, spymaster.location_id or spymaster.id, target.id)
    design = await steal_design(ctx, spymaster.location_id or spymaster.id, target.id)
    if design is not None:
        await _note(
            ctx, f"The agents of {spymaster.name} carried off {design.name.lower()} from {target.name}.", "espionage.stole_design", (spymaster.id, target.id)
        )
    if secret is not None:
        text = f"The agents of {spymaster.name} carried off the secret of {secret.value.replace('_', ' ')} from {target.name}."
        await _note(ctx, text, "espionage.stole_technique", (spymaster.id, target.id))
        return text
    loot = await _stealable(ctx, spymaster, target)
    if not loot:
        return None
    knowledge = ctx.rng("loot").pick(loot)
    await teach(ctx, spymaster.id, knowledge, f"stolen from {target.name}")
    text = f"The agents of {spymaster.name} stole the knowledge of {knowledge.name} from {target.name}."
    await _note(ctx, text, "espionage.stole_knowledge", (spymaster.id, target.id, knowledge.id))
    return text


async def sabotage(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    kind = await sabotage_kind(ctx, target)
    rules = ctx.rules.espionage
    if kind is SabotageKind.GRANARY_FIRE:
        society = await ctx.session.get(CommunitySocietyRow, target.id)
        burned = round_half_up((society.stock_food if society is not None else 0) * rules.granary_fire_pct / PERCENT)
        await shift_stock(ctx.session, ctx.rules, target.id, Commodity.FOOD, -burned, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    elif kind is SabotageKind.WALL_WEAKENING:
        walls = await ctx.session.get(SettlementInfrastructureRow, target.id)
        if walls is not None:
            walls.walls_condition = clamp_int(walls.walls_condition - rules.wall_damage, 0, PERCENT)
    elif kind is SabotageKind.POISON_WELLS:
        await strike_plague(ctx, target, rules.poison_severity, path=SpreadPath.LOOSED)
    else:
        for key in SABOTAGED_STATS:
            shift_stat(target, key, -rules.spy_sabotage_damage)
        line = await burn_district(ctx, target)
        text = f"The agents of {spymaster.name} set fires in {target.name}: {line}."
        await _note(ctx, text, f"espionage.sabotage.{kind.value}", (spymaster.id, target.id))
        return text
    text = f"The agents of {spymaster.name} sabotaged {target.name}: {SABOTAGE_LINES[kind]}."
    await _note(ctx, text, f"espionage.sabotage.{kind.value}", (spymaster.id, target.id))
    return text


async def sabotage_kind(ctx: TickContext, target: EntityRow) -> SabotageKind:
    at_war = bool(await BondRepository(ctx.session).outgoing(target.id, BondKind.ENEMY))
    walls = await ctx.session.get(SettlementInfrastructureRow, target.id)
    society = await ctx.session.get(CommunitySocietyRow, target.id)
    if at_war and walls is not None and walls.walls_level > 0:
        return SabotageKind.WALL_WEAKENING
    if society is not None and society.stock_food > 0 and ctx.rng(f"granary.{target.id}.{ctx.epoch}").chance(PERCENT // 2):
        return SabotageKind.GRANARY_FIRE
    if at_war and ctx.rng(f"wells.{target.id}.{ctx.epoch}").chance(PERCENT // 4):
        return SabotageKind.POISON_WELLS
    return SabotageKind.ARSON


async def assassinate(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    rulers = await mortal_rulers(ctx.session, target.id)
    victim = await living_entity(ctx.session, rulers[0]) if rulers else None
    if victim is None:
        return None
    if network.depth < ctx.rules.espionage.assassinate_depth:
        await wound_ruler(ctx, victim, spymaster)
        text = f"An assassin of {spymaster.name} struck at {victim.name}, ruler of {target.name}, and left them wounded."
        await _note(ctx, text, "espionage.assassination_wounded", (spymaster.id, target.id, victim.id))
        return text
    await death_path(
        ctx, victim, f"murdered by the agents of {spymaster.name}", spymaster.id, "assassination", forced=True, harm=HarmCause.POISON, manner=DeathCause.MURDER
    )
    for agent in await agents_of(ctx, network):
        if agent.mortal_entity_id is not None:
            await house_feud(ctx, agent.mortal_entity_id, victim.id, f"the murder of {victim.name}")
            break
    text = f"Agents of {spymaster.name} reached {victim.name}, ruler of {target.name}, and killed them."
    await _note(ctx, text, "espionage.assassination", (spymaster.id, target.id, victim.id))
    return text


async def incite(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    rules = ctx.rules.espionage
    town = await ctx.session.get(SettlementProfileRow, target.id)
    if town is None:
        return None
    town.unrest = clamp_int(town.unrest + rules.incite_unrest, 0, PERCENT)
    risen = town.unrest >= rules.incite_uprising_unrest and await incite_uprising_quietly(ctx, target)
    claimant = await plant_claimant(ctx, spymaster, target)
    planted = f"; they whispered that {claimant.name} was the rightful ruler" if claimant is not None else ""
    text = f"Agents of {spymaster.name} stirred the streets of {target.name}{planted}" + (" until the townsfolk rose against their rulers." if risen else ".")
    await _note(ctx, text, "espionage.incite", (spymaster.id, target.id))
    return text


async def incite_uprising_quietly(ctx: TickContext, community: EntityRow) -> bool:
    target = await uprising_target(ctx.session, community)
    return target.id != community.id and await declare_war(ctx, community.id, target.id, "uprising", cause=WarCause.UPRISING, world_cap=False)


async def gather(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    gain = cover_access(network, ctx.rules.espionage.intel_gain) * await ctx.hook_factor(spymaster.id, DomainHook.SPY_DEPTH)
    network.intel = clamp_int(network.intel + round_half_up(gain), 0, PERCENT)
    aims = await reveal_aims(ctx, network, target)
    tail = f"; {len(aims)} of its war aims lie open" if aims else ""
    return f"The agents of {spymaster.name} learned the secrets of {target.name}{tail}."


async def blackmail(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    rules = ctx.rules.espionage
    if network.intel < rules.assassinate_depth // 2:
        return None
    network.intel = clamp_int(network.intel - rules.intel_gain, 0, PERCENT)
    bent = await blackmail_office(ctx, spymaster, target, network)
    if bent is None:
        move_stat(target, spymaster, "wealth", rules.blackmail_wealth)
    text = (bent + ".") if bent is not None else f"{spymaster.name} held the secrets of {target.name}'s rulers over them and was paid to keep quiet."
    await _note(ctx, text, "espionage.blackmail", (spymaster.id, target.id))
    return text


async def counterfeit(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    coin = await ctx.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == target.id).order_by(CurrencyRow.id).limit(1))
    if coin is None:
        return None
    coin.trust = clamp_int(coin.trust - ctx.rules.espionage.counterfeit_trust, 0, PERCENT)
    text = f"False coins of {coin.name} from the agents of {spymaster.name} spread through the markets of {target.name}."
    await _note(ctx, text, "espionage.counterfeit", (spymaster.id, target.id))
    return text


OPERATIONS = {
    SpyOperation.STEAL_KNOWLEDGE: steal,
    SpyOperation.SABOTAGE: sabotage,
    SpyOperation.ASSASSINATE: assassinate,
    SpyOperation.INCITE: incite,
    SpyOperation.INTEL: gather,
    SpyOperation.BLACKMAIL: blackmail,
    SpyOperation.COUNTERFEIT: counterfeit,
}
SABOTAGE_LINES = {
    SabotageKind.GRANARY_FIRE: "the granaries burned",
    SabotageKind.WALL_WEAKENING: "the walls were undermined",
    SabotageKind.POISON_WELLS: "the wells were poisoned",
    SabotageKind.ARSON: "fires were set",
}
WAR_OPERATIONS = (SpyOperation.SABOTAGE, SpyOperation.ASSASSINATE, SpyOperation.INTEL)
PEACE_OPERATIONS = (SpyOperation.STEAL_KNOWLEDGE, SpyOperation.BLACKMAIL, SpyOperation.COUNTERFEIT, SpyOperation.INCITE, SpyOperation.INTEL)


async def perform_operation(ctx: TickContext, spymaster: EntityRow, target: EntityRow, operation: SpyOperation) -> str:
    network = await network_for(ctx, spymaster, target, None)
    text = await OPERATIONS[operation](ctx, spymaster, target, network)
    if text is None and operation is not SpyOperation.INTEL:
        text = await gather(ctx, spymaster, target, network)
    if "exposure" not in network.locked:
        network.exposure = clamp_int(network.exposure + cover_exposure(network, ctx.rules.espionage.exposure_per_operation), 0, PERCENT)
    for agent in await agents_of(ctx, network):
        agent.exposure = clamp_int(agent.exposure + cover_exposure(network, ctx.rules.espionage.exposure_per_operation), 0, PERCENT)
    network.last_operation, network.last_epoch = operation.value, ctx.epoch
    return text or ""


async def choose_operation(ctx: TickContext, spymaster: EntityRow, target: EntityRow) -> SpyOperation:
    rng = ctx.rng(f"operation.{spymaster.id}.{target.id}.{ctx.epoch}")
    if rng.chance(ctx.rules.espionage.spy_steal_knowledge_pct) and await _stealable(ctx, spymaster, target):
        return SpyOperation.STEAL_KNOWLEDGE
    at_war = bool(await BondRepository(ctx.session).active_between(spymaster.id, target.id, [BondKind.ENEMY]))
    return rng.pick(list(WAR_OPERATIONS if at_war else PEACE_OPERATIONS))


MIN_GUILE = 0.1
COVERS = {EntityType.CULT: SpyCover.PRIEST, EntityType.POLITY: SpyCover.ENVOY, EntityType.SETTLEMENT: SpyCover.MERCHANT}


async def spymaster_of(ctx: TickContext, entity_id: int) -> int | None:
    polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == entity_id).limit(1))
    owner = polity if polity is not None else entity_id
    statement = select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == owner, OfficeRow.kind == OfficeKind.SPYMASTER)
    return await ctx.session.scalar(statement.where(OfficeRow.holder_entity_id.is_not(None)).limit(1))


async def network_for(ctx: TickContext, owner: EntityRow, target: EntityRow, bond: BondRow | None) -> SpyNetworkRow:
    found = await ctx.session.scalar(
        select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == owner.id, SpyNetworkRow.target_entity_id == target.id).order_by(SpyNetworkRow.id).limit(1)
    )
    if found is None:
        found = SpyNetworkRow(
            owner_entity_id=owner.id,
            target_entity_id=target.id,
            agents=1,
            agent_ids=[],
            depth=0,
            exposure=0,
            cover=cover_for(owner)
            if owner.entity_type in {EntityType.FACTION, EntityType.POLITY, EntityType.CULT}
            else COVERS.get(target.entity_type, SpyCover.BEGGAR),
            since_epoch=ctx.epoch,
            intel=0,
            owner_kind=owner_kind(owner),
            side_entity_id=await side_for(ctx, owner),
            revealed_aims=[],
            locked=[],
        )
        ctx.session.add(found)
    if bond is not None:
        found.bond_id = bond.id
    found.spymaster_entity_id = await spymaster_of(ctx, owner.id)
    return found


async def deepen(ctx: TickContext, network: SpyNetworkRow) -> None:
    rules = ctx.rules.espionage
    skill = await skill_level(ctx.session, network.spymaster_entity_id, SkillKind.INTRIGUE) if network.spymaster_entity_id is not None else 0
    if "depth" not in network.locked:
        network.depth = clamp_int(network.depth + cover_access(network, round_half_up(rules.depth_gain * (1 + skill / PERCENT))), 0, PERCENT)
    ctx.count("agents_retired", await retire_agents(ctx, network))
    if "agents" not in network.locked and await recruit(ctx, network) is not None:
        network.agents += 1
    network.intel = clamp_int(network.intel + round_half_up(rules.intel_gain * network.depth / PERCENT), 0, PERCENT)
    network.exposure = clamp_int(network.exposure - rules.exposure_decay, 0, PERCENT)


async def caught_chance(ctx: TickContext, network: SpyNetworkRow, target: EntityRow) -> float:
    watcher = await spymaster_of(ctx, target.id)
    counter = await skill_level(ctx.session, watcher, SkillKind.INTRIGUE) if watcher is not None else 0
    return capture_chance(ctx, target) * (1 + network.exposure / PERCENT) * (1 + counter / PERCENT * ctx.rules.espionage.counter_intel_pct / PERCENT)


async def run_networks(ctx: TickContext) -> None:
    rules = ctx.rules.espionage
    rng = ctx.rng("operations")
    ctx.count("spy_bonds_migrated", await migrate_bonds(ctx))
    for network in list(await ctx.session.scalars(select(SpyNetworkRow).order_by(SpyNetworkRow.id))):
        spymaster, target = await living_entity(ctx.session, network.owner_entity_id), await living_entity(ctx.session, network.target_entity_id)
        if spymaster is None or target is None:
            await ctx.session.delete(network)
            continue
        if network.since_epoch == ctx.epoch or held(spymaster.id, target.id):
            continue
        guile = await deceit_drive(ctx.session, ctx.rules, spymaster.id)
        network.spymaster_entity_id = await spymaster_of(ctx, spymaster.id)
        await deepen(ctx, network)
        if rng.chance(await caught_chance(ctx, network, target) / max(guile, MIN_GUILE)):
            caught = await catch_agent(ctx, network, target)
            await change_relation(ctx, spymaster.id, target.id, -rules.spy_caught_relation_loss, MemoryKind.SPIED_ON_US, note="caught spies")
            war = rng.chance(rules.spy_war_chance) and await declare_war(ctx, target.id, spymaster.id, "espionage", cause=WarCause.ESPIONAGE)
            rolled = not await agents_of(ctx, network) and network.exposure >= rules.roll_up_exposure
            if rolled:
                await ctx.session.delete(network)
            who = f"{caught.name}, a spy of {spymaster.name}," if caught is not None else f"The spies of {spymaster.name}"
            tail = f"; {target.name} declared them its enemy" if war else "; the network was rolled up" if rolled else ""
            await _note(ctx, f"{who} were caught in {target.name}{tail}.", "espionage.caught", (spymaster.id, target.id))
            ctx.count("spies_caught")
            continue
        if not rng.chance(rules.spy_action_chance * guile):
            continue
        operation = await choose_operation(ctx, spymaster, target)
        await perform_operation(ctx, spymaster, target, operation)
        ctx.count("spy_operations")
        ctx.count(f"spy_{operation.value}")


@reads(
    "cult.influence",
    "cult.zeal",
    "faction.sway",
    "knowledge.spread",
    "people.wealth",
    "settlement.defense",
    "table.applied_fixups",
    "table.army_officers",
    "table.bonds",
    "table.captives",
    "table.claims",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_stocks",
    "table.cosmos",
    "table.culture_values",
    "table.currencies",
    "table.districts",
    "table.epoch_year_cursors",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.law_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.memories",
    "table.mercenary_contracts",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.peace_terms",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.relationships",
    "table.reputations",
    "table.routes",
    "table.ruler_currencies",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.spy_agents",
    "table.spy_networks",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.workshops",
)
@writes(
    "knowledge.spread",
    "people.wealth",
    "settlement.wealth",
    "table.applied_fixups",
    "table.army_officers",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.epoch_year_cursors",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.offices",
    "table.peace_terms",
    "table.polity_profiles",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.spy_agents",
    "table.spy_networks",
    "table.treaty_breaches",
    "table.vessel_profiles",
)
async def espionage(ctx: TickContext) -> None:
    ctx.count("spy_networks_founded", await found_networks(ctx))
    await run_networks(ctx)


async def order_spy_operation(ctx: TickContext, spymaster_id: int, target_id: int, operation: SpyOperation) -> str:
    spymaster, target = await living_entity(ctx.session, spymaster_id), await living_entity(ctx.session, target_id)
    if spymaster is None or target is None or spymaster.entity_type not in SPY_OWNERS or target.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("A living realm, faction or cult spies on a living community.")
    if spymaster.id == target.id:
        raise ConflictError("No one can spy on itself.")
    if spymaster.status is not EntityStatus.CANON:
        raise ConflictError(f"{spymaster.name} is gone.")
    network = await network_for(ctx, spymaster, target, None)
    await ctx.session.flush()
    if not await agents_of(ctx, network):
        await recruit(ctx, network)
    return await perform_operation(ctx, spymaster, target, operation)


SPY_OWNERS = frozenset({EntityType.FACTION, EntityType.POLITY, EntityType.CULT, *COMMUNITY_TYPES})


PHASES = (Phase("espionage", espionage),)
