from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.law_depth import METHOD_HARM, METHOD_SEEMING, METHOD_TEXT
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
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.military import SabotageKind, SpyCover, SpyOperation
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind, DeathCause
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.blueprints import steal_design
from aerona.engine.lore.research import steal_technique
from aerona.engine.military.feuds import house_feud
from aerona.engine.military.forensics import choose_method, examine
from aerona.engine.military.sabotage import WIDER_SABOTAGE, wider_choices
from aerona.engine.military.spy_depth import topology_pct
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
from aerona.engine.nature.effects import sensed
from aerona.engine.nature.senses import AGENTS
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import canon, living_entity
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import move_stat, shift_stat, stat
from aerona.engine.recording.record import FactInput, record
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war, has_truce, uprising_target

SABOTAGED_STATS = ("defense", "strength", "wealth")
PRESSURE_STATS = ("influence", "sway", "defense")


async def told(ctx: TickContext, key: str, actor: EntityRow, target: EntityRow, *, facts: Mapping[str, FactInput] | None = None, **others: int) -> str:
    roles: dict[IncidentRole, int] = {IncidentRole.ACTOR: actor.id, IncidentRole.TARGET: target.id}
    for name, node in others.items():
        roles[IncidentRole(name)] = node
    written = await record(ctx, key, roles=roles, facts=facts, place=target.id)
    return written.text


async def _targets(ctx: TickContext, faction: EntityRow) -> list[tuple[bool, int, EntityRow]]:
    bonds = BondRepository(ctx.session)
    ranked: list[tuple[bool, int, EntityRow]] = []
    for community in await canon(ctx.session, COMMUNITY_TYPES, faction.world_id):
        if community.id == faction.id or held(community.id):
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
    owners = await canon(ctx.session, [EntityType.FACTION, EntityType.POLITY, EntityType.CULT])
    cap = scaled_cap(rules.spy_net_cap, rules.spy_net_cap_owner_divisor, len(owners))
    for owner in rng.shuffled(owners):
        if founded >= cap:
            break
        chance = await would_spy(ctx, owner)
        if chance is None or owner.id in owned or held(owner.id):
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
        await told(ctx, "espionage.network_founded", owner, target)
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
        await told(ctx, "espionage.stole_design", spymaster, target, facts={"design": design.name})
    if secret is not None:
        return await told(ctx, "espionage.stole_technique", spymaster, target, facts={"technique": secret})
    loot = await _stealable(ctx, spymaster, target)
    if not loot:
        return None
    knowledge = ctx.rng("loot").pick(loot)
    await teach(ctx, spymaster.id, knowledge, f"stolen from {target.name}")
    return await told(ctx, "espionage.stole_knowledge", spymaster, target, facts={"knowledge": knowledge.id})


async def sabotage(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    kind = await sabotage_kind(ctx, target)
    rules = ctx.rules.espionage
    facts: dict[str, FactInput] = {"sabotage": kind}
    if kind in WIDER_SABOTAGE:
        await WIDER_SABOTAGE[kind][0](ctx, spymaster, target)
        return await told(ctx, f"espionage.sabotage.{kind.value}", spymaster, target, facts=facts)
    if kind is SabotageKind.GRANARY_FIRE:
        society = await ctx.session.get(CommunitySocietyRow, target.id)
        burned = round_half_up((society.stock_food if society is not None else 0) * rules.granary_fire_pct / PERCENT)
        await shift_stock(ctx.session, ctx.rules, target.id, Commodity.FOOD, -burned, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
        facts["food_burned"] = burned
    elif kind is SabotageKind.WALL_WEAKENING:
        walls = await ctx.session.get(SettlementInfrastructureRow, target.id)
        if walls is not None:
            walls.walls_condition = clamp_int(walls.walls_condition - rules.wall_damage, 0, PERCENT)
            facts["wall_damage"] = rules.wall_damage
    elif kind is SabotageKind.POISON_WELLS:
        await strike_plague(ctx, target, rules.poison_severity, path=SpreadPath.LOOSED)
        facts["severity"] = rules.poison_severity
    else:
        for key in SABOTAGED_STATS:
            shift_stat(target, key, -rules.spy_sabotage_damage)
        facts["harm"] = rules.spy_sabotage_damage
        district = await burn_district(ctx, target)
        if district is not None:
            facts["district"] = district
    return await told(ctx, f"espionage.sabotage.{kind.value}", spymaster, target, facts=facts)


async def sabotage_kind(ctx: TickContext, target: EntityRow) -> SabotageKind:
    at_war = bool(await BondRepository(ctx.session).outgoing(target.id, BondKind.ENEMY))
    walls = await ctx.session.get(SettlementInfrastructureRow, target.id)
    society = await ctx.session.get(CommunitySocietyRow, target.id)
    wider = await wider_choices(ctx, target)
    if wider and ctx.rng(f"sabotage.wider.{target.id}.{ctx.epoch}").chance(ctx.rules.espionage.wider_sabotage_pct):
        return ctx.rng(f"sabotage.pick.{target.id}.{ctx.epoch}").pick(wider)
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
        return await told(ctx, "espionage.assassination_wounded", spymaster, target, victim=victim.id)
    method = await choose_method(ctx, spymaster, network, victim)
    killing = await examine(ctx, victim, spymaster.id, method)
    manner = DeathCause.MURDER if killing.recognised else METHOD_SEEMING[method]
    await death_path(ctx, victim, f"died {METHOD_TEXT[method]}", spymaster.id, "assassination", forced=True, harm=METHOD_HARM[method], manner=manner)
    if not killing.recognised:
        return await told(ctx, "espionage.assassination_hidden", spymaster, target, facts={"method": method}, victim=victim.id)
    await answer_murder(ctx, network, victim, target)
    return await told(ctx, "espionage.assassination", spymaster, target, facts={"method": method}, victim=victim.id)


async def answer_murder(ctx: TickContext, network: SpyNetworkRow, victim: EntityRow, target: EntityRow) -> None:
    killers = [agent.mortal_entity_id for agent in await agents_of(ctx, network) if agent.mortal_entity_id is not None]
    if not killers:
        return
    await house_feud(ctx, killers[0], victim.id, f"the murder of {victim.name}")
    if ctx.rng(f"espionage.revenge.{victim.id}").chance(ctx.rules.espionage.spy_war_chance) and network.owner_entity_id != target.id:
        await declare_war(ctx, target.id, network.owner_entity_id, "a ruler's murder", cause=WarCause.ESPIONAGE)
    town = victim.location_id if victim.location_id is not None else target.id
    if ctx.rng(f"espionage.inquest.{victim.id}").chance(ctx.rules.forensics.investigate_pct):
        await report_crime(ctx, town, killers[0], CrimeKind.MURDER)


async def incite(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    rules = ctx.rules.espionage
    town = await ctx.session.get(SettlementProfileRow, target.id)
    if town is None:
        return None
    town.unrest = clamp_int(town.unrest + rules.incite_unrest, 0, PERCENT)
    risen = town.unrest >= rules.incite_uprising_unrest and await incite_uprising_quietly(ctx, target)
    claimant = await plant_claimant(ctx, spymaster, target)
    others = {"subject": claimant.id} if claimant is not None else {}
    key = "espionage.incite_uprising" if risen else "espionage.incite"
    return await told(ctx, key, spymaster, target, facts={"unrest": town.unrest}, **others)


async def incite_uprising_quietly(ctx: TickContext, community: EntityRow) -> bool:
    target = await uprising_target(ctx.session, community)
    return target.id != community.id and await declare_war(ctx, community.id, target.id, "uprising", cause=WarCause.UPRISING, world_cap=False)


async def gather(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    privacy = await law_param(ctx.session, target.id, LawKind.DATA_PRIVACY, "strictness")
    shield = 1 - (int(privacy) if isinstance(privacy, int) else 0) * ctx.rules.espionage.privacy_pct / PERCENT / PERCENT
    gain = cover_access(network, ctx.rules.espionage.intel_gain) * await ctx.hook_factor(spymaster.id, DomainHook.SPY_DEPTH) * shield
    network.intel = clamp_int(network.intel + round_half_up(gain), 0, PERCENT)
    aims = await reveal_aims(ctx, network, target)
    return await told(ctx, "espionage.intel", spymaster, target, facts={"intel": network.intel, "aims": len(aims)})


async def blackmail(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    rules = ctx.rules.espionage
    if network.intel < rules.assassinate_depth // 2:
        return None
    network.intel = clamp_int(network.intel - rules.intel_gain, 0, PERCENT)
    bent = await blackmail_office(ctx, spymaster, target, network)
    facts: dict[str, FactInput] = {"intel_spent": rules.intel_gain}
    if bent is None:
        move_stat(target, spymaster, "wealth", rules.blackmail_wealth)
        facts["paid"] = rules.blackmail_wealth
    others = {"victim": bent} if bent is not None else {}
    return await told(ctx, "espionage.blackmail", spymaster, target, facts=facts, **others)


async def counterfeit(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    coin = await ctx.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == target.id).order_by(CurrencyRow.id).limit(1))
    if coin is None:
        return None
    coin.trust = clamp_int(coin.trust - ctx.rules.espionage.counterfeit_trust, 0, PERCENT)
    return await told(ctx, "espionage.counterfeit", spymaster, target, facts={"currency": coin.name, "trust_lost": ctx.rules.espionage.counterfeit_trust})


OPERATIONS = {
    SpyOperation.STEAL_KNOWLEDGE: steal,
    SpyOperation.SABOTAGE: sabotage,
    SpyOperation.ASSASSINATE: assassinate,
    SpyOperation.INCITE: incite,
    SpyOperation.INTEL: gather,
    SpyOperation.BLACKMAIL: blackmail,
    SpyOperation.COUNTERFEIT: counterfeit,
}
WAR_OPERATIONS = (SpyOperation.SABOTAGE, SpyOperation.ASSASSINATE, SpyOperation.INTEL)
PEACE_OPERATIONS = (SpyOperation.STEAL_KNOWLEDGE, SpyOperation.BLACKMAIL, SpyOperation.COUNTERFEIT, SpyOperation.INCITE, SpyOperation.INTEL)


async def perform_operation(ctx: TickContext, spymaster: EntityRow, target: EntityRow, operation: SpyOperation) -> str:
    network = await network_for(ctx, spymaster, target, None)
    text = await OPERATIONS[operation](ctx, spymaster, target, network)
    if text is None and operation is not SpyOperation.INTEL:
        text = await gather(ctx, spymaster, target, network)
    found = 1 + await sensed(ctx.session, ctx.rules, target.id, AGENTS, ctx.rules.senses.agents_pct)
    gain = round_half_up(cover_exposure(network, ctx.rules.espionage.exposure_per_operation) * found)
    if "exposure" not in network.locked:
        network.exposure = clamp_int(network.exposure + gain, 0, PERCENT)
    for agent in await agents_of(ctx, network):
        agent.exposure = clamp_int(agent.exposure + gain, 0, PERCENT)
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
            cover=await cover_for(ctx.session, owner)
            if owner.entity_type in {EntityType.FACTION, EntityType.POLITY, EntityType.CULT}
            else COVERS.get(target.entity_type, SpyCover.BEGGAR),
            since_epoch=ctx.epoch,
            intel=0,
            owner_kind=await owner_kind(ctx.session, owner),
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
        gain = round_half_up(rules.depth_gain * (1 + skill / PERCENT) * await topology_pct(ctx, network) / PERCENT)
        network.depth = clamp_int(network.depth + cover_access(network, gain), 0, PERCENT)
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
            if rng.chance(rules.spy_war_chance):
                await declare_war(ctx, target.id, spymaster.id, "espionage", cause=WarCause.ESPIONAGE)
            rolled = not await agents_of(ctx, network) and network.exposure >= rules.roll_up_exposure
            if rolled:
                await ctx.session.delete(network)
            others = {"subject": caught.id} if caught is not None else {}
            await told(ctx, "espionage.caught", spymaster, target, facts={"exposure": network.exposure}, **others)
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
    "table.company_profiles",
    "table.cosmos",
    "table.creator",
    "table.culture_values",
    "table.currencies",
    "table.dimensions",
    "table.districts",
    "table.entities",
    "table.feuds",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.goods",
    "table.held_identities",
    "table.hooks",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.law_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_profiles",
    "table.minds",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.peace_terms",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.registries",
    "table.relationships",
    "table.reputations",
    "table.routes",
    "table.ruler_currencies",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sons",
    "table.spy_agents",
    "table.spy_cells",
    "table.spy_networks",
    "table.stars",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vessel_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.workshops",
    "table.worlds",
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
