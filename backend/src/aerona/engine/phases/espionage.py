from enum import StrEnum

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import deceit_drive
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.queries import canon, living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war, has_truce

SABOTAGED_STATS = ("defense", "strength", "wealth")
PRESSURE_STATS = ("influence", "sway", "defense")


class SpyOperation(StrEnum):
    STEAL = "steal"
    SABOTAGE = "sabotage"


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


async def found_networks(ctx: TickContext) -> int:
    rules = ctx.rules.espionage
    rng = ctx.rng("networks")
    founded = 0
    for faction in await canon(ctx.session, [EntityType.FACTION]):
        if founded >= rules.spy_net_cap:
            break
        if (stat(faction, "sway") or 0) < rules.spy_min_sway or await BondRepository(ctx.session).outgoing(faction.id, BondKind.SPY_NETWORK):
            continue
        targets = await _targets(ctx, faction)
        if not targets:
            continue
        hostile, _, target = targets[0]
        if not rng.chance(rules.spy_net_chance + (rules.spy_net_enemy_bonus_pct if hostile else 0)):
            continue
        await BondRepository(ctx.session).connect(BondDraft(faction.id, target.id, BondKind.SPY_NETWORK, ctx.epoch, "agent network"))
        founded += 1
        await _note(ctx, f"{faction.name} began weaving a secret agent network inside {target.name}.", "espionage.network_founded", (faction.id, target.id))
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


async def perform_operation(ctx: TickContext, spymaster: EntityRow, target: EntityRow, operation: SpyOperation) -> str:
    if operation is SpyOperation.STEAL:
        loot = await _stealable(ctx, spymaster, target)
        if loot:
            knowledge = ctx.rng("loot").pick(loot)
            await teach(ctx, spymaster.id, knowledge, f"stolen from {target.name}")
            text = f"The agents of {spymaster.name} stole the knowledge of {knowledge.name} from {target.name}."
            await _note(ctx, text, "espionage.stole_knowledge", (spymaster.id, target.id, knowledge.id))
            return text
    for key in SABOTAGED_STATS:
        shift_stat(target, key, -ctx.rules.espionage.spy_sabotage_damage)
    text = f"The agents of {spymaster.name} sabotaged {target.name}: granaries burned, sentries poisoned."
    await _note(ctx, text, "espionage.sabotage", (spymaster.id, target.id))
    return text


MIN_GUILE = 0.1


async def run_networks(ctx: TickContext) -> None:
    rules = ctx.rules.espionage
    rng = ctx.rng("operations")
    bonds = BondRepository(ctx.session)
    networks = list(
        await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.SPY_NETWORK, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    )
    for bond in networks:
        spymaster, target = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if spymaster is None or target is None:
            await bonds.deactivate(bond, ctx.epoch, "a side is gone")
            continue
        if bond.epoch == ctx.epoch:
            continue
        guile = await deceit_drive(ctx.session, ctx.rules, spymaster.id)
        if rng.chance(capture_chance(ctx, target) / max(guile, MIN_GUILE)):
            await bonds.deactivate(bond, ctx.epoch, "spies caught")
            await change_relation(ctx, spymaster.id, target.id, -rules.spy_caught_relation_loss, MemoryKind.SPIED_ON_US, note="caught spies")
            war = rng.chance(rules.spy_war_chance) and await declare_war(ctx, target.id, spymaster.id, "espionage", cause=WarCause.ESPIONAGE)
            tail = f"; {target.name} declared them its enemy" if war else "; the network was dismantled"
            await _note(ctx, f"The spies of {spymaster.name} were caught in {target.name}{tail}.", "espionage.caught", (spymaster.id, target.id))
            ctx.count("spies_caught")
            continue
        if not rng.chance(rules.spy_action_chance * guile):
            continue
        operation = SpyOperation.STEAL if rng.chance(rules.spy_steal_knowledge_pct) else SpyOperation.SABOTAGE
        await perform_operation(ctx, spymaster, target, operation)
        ctx.count("spy_operations")


@reads(
    "cult.influence",
    "faction.sway",
    "knowledge.spread",
    "people.wealth",
    "settlement.defense",
    "table.bonds",
    "table.community_relations",
    "table.cosmos",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.traits",
)
@writes(
    "knowledge.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
)
@reads("cult.influence", "faction.sway", "knowledge.spread", "people.wealth", "settlement.defense")
@writes("knowledge.spread")
async def espionage(ctx: TickContext) -> None:
    ctx.count("spy_networks_founded", await found_networks(ctx))
    await run_networks(ctx)


async def order_spy_operation(ctx: TickContext, spymaster_id: int, target_id: int, operation: SpyOperation) -> str:
    spymaster, target = await living_entity(ctx.session, spymaster_id), await living_entity(ctx.session, target_id)
    if spymaster is None or target is None or spymaster.entity_type is not EntityType.FACTION or target.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("A living faction spies on a living community.")
    if spymaster.id == target.id:
        raise ConflictError("A faction cannot spy on itself.")
    if spymaster.status is not EntityStatus.CANON:
        raise ConflictError(f"{spymaster.name} is gone.")
    bonds = BondRepository(ctx.session)
    if not await bonds.active_between(spymaster.id, target.id, [BondKind.SPY_NETWORK]):
        await bonds.connect(BondDraft(spymaster.id, target.id, BondKind.SPY_NETWORK, ctx.epoch, "agent network by decree"))
    return await perform_operation(ctx, spymaster, target, operation)


PHASES = (Phase("espionage", espionage),)
