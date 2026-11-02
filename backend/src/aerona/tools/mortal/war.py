from typing import Any

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.war import WarCause
from aerona.engine.lifecycle.wounds import WoundOutcome, wound
from aerona.engine.primitives.faith import patron_son
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import WarBlock, can_open_war, declare_war
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import DeclareWarInput, SabotageInput, SabotageKind, SpyInput
from aerona.tools.mortal.support import enemies, fail_with_candidates, first_stat, is_community, near, require_target, wits_of

PERCENT = 100
SPY_COVER_EXCERPT = 80
WATCH_CHAIN = ("defense", "intellect")
WAR_TARGETS = COMMUNITY_TYPES | {EntityType.SPECIES}
SABOTAGE_TARGETS = COMMUNITY_TYPES | {EntityType.MORTAL}
WAR_BLOCK_TEXTS = {WarBlock.TRUCE: MortalResult.TRUCE_HOLDS, WarBlock.SUBJECT: MortalResult.SUBJECT_BOND, WarBlock.ALREADY_ENEMIES: MortalResult.ALREADY_AT_WAR}


async def _sour_patrons(call: MortalCall, target: EntityRow) -> None:
    mine = await patron_son(call.session, call.me)
    theirs = await patron_son(call.session, target)
    if mine is not None and theirs is not None and mine.id != theirs.id:
        await SonRepository(call.session).change_relation(mine.id, theirs.id, -call.rules.mortal_tools.war_declare_patron_relation)


async def declare(call: MortalCall, args: DeclareWarInput) -> str:
    tools = call.rules.mortal_tools
    target = await require_target(call, args.target_id)
    species = target.entity_type is EntityType.SPECIES
    if target.id == call.me.id or not (is_community(target) or species):
        await fail_with_candidates(call, MortalResult.INVALID_TARGET, WAR_TARGETS)
    if not await near(call, target):
        await fail_with_candidates(call, MortalResult.TARGET_TOO_FAR, WAR_TARGETS)
    bonds = BondRepository(call.session)
    hostile = BondKind.HUNTS if species else BondKind.ENEMY
    if await bonds.exists_between(call.me.id, target.id, hostile):
        fail(MortalResult.ALREADY_AT_WAR)
    call.target(target.id)
    if species:
        await bonds.connect(BondDraft(call.me.id, target.id, BondKind.HUNTS, call.epoch, args.reason))
    else:
        block = await can_open_war(call.session, call.rules, call.me.id, target.id, call.epoch)
        if block is not None:
            template = WAR_BLOCK_TEXTS.get(block)
            if template is not None:
                fail(template)
            fail(MortalResult.WAR_BLOCKED, reason=block.value.replace("_", " "))
        await declare_war(call.tick, call.me.id, target.id, args.reason, cause=WarCause.DECLARED)
        await change_relation(call.tick, call.me.id, target.id, -tools.war_declare_relation, args.reason[:KEY_MAX_LENGTH])
        await _sour_patrons(call, target)
    await call.chronicle(ChronicleKind.WAR, lines.WAR, entity_ids=[call.me.id, target.id], me=call.me.name, target=target.name, reason=args.reason)
    return result(MortalResult.WAR_DECLARED, name=target.name)


async def _poison(call: MortalCall, target: EntityRow, caught: bool) -> str:
    tools = call.rules.mortal_tools
    if target.entity_type is EntityType.MORTAL:
        outcome = await wound(call.tick, target, tools.poison_hp, cause=lines.POISON_DEATH, killer_id=call.me.id if caught else None)
        if outcome is WoundOutcome.DIED:
            return result(MortalResult.POISON_KILLED, name=target.name)
        return result(MortalResult.POISON_WORKED, name=target.name)
    floor = call.rules.limits.population_floor
    for key in ("population", "followers"):
        value = stat(target, key)
        if value is not None:
            set_stats(target, **{key: max(1 if key == "followers" else floor, round(value * (PERCENT - tools.poison_population_pct) / PERCENT))})
    hp = stat(target, "hp")
    if hp is not None:
        set_stats(target, hp=max(0, hp - tools.poison_hp))
    return result(MortalResult.POISON_WORKED, name=target.name)


async def _arson(call: MortalCall, target: EntityRow) -> str:
    loss = call.rules.mortal_tools.arson_loss
    for key in ("prosperity", "defense", "wealth"):
        value = stat(target, key)
        if value is not None:
            set_stats(target, **{key: max(0, value - loss)})
    return result(MortalResult.ARSON_WORKED, name=target.name)


async def _discord(call: MortalCall, target: EntityRow) -> str:
    bonds = BondRepository(call.session)
    allies = [*await bonds.outgoing(target.id, BondKind.ALLY), *await bonds.incoming(target.id, BondKind.ALLY)]
    if not allies:
        return result(MortalResult.NO_ALLIANCE)
    bond = allies[0]
    other = await call.session.get(EntityRow, bond.other_end(target.id))
    await bonds.deactivate(bond, call.epoch, SabotageKind.DISCORD.value)
    return result(MortalResult.DISCORD_WORKED, name=target.name, other=other.name if other is not None else "")


async def sabotage(call: MortalCall, args: SabotageInput) -> str:
    tools = call.rules.mortal_tools
    target = await require_target(call, args.target_id)
    if target.id == call.me.id or not (is_community(target) or target.entity_type is EntityType.MORTAL):
        await fail_with_candidates(call, MortalResult.INVALID_TARGET, SABOTAGE_TARGETS)
    if not await near(call, target):
        await fail_with_candidates(call, MortalResult.TOO_FAR, SABOTAGE_TARGETS)
    cunning = wits_of(call) + call.die(tools.sabotage_die, "cunning")
    watch = first_stat(target, WATCH_CHAIN, tools.default_stat) + call.die(tools.sabotage_die, "watch")
    caught = watch > cunning + tools.sabotage_caught_margin
    call.target(target.id)
    if cunning >= watch:
        effects = {
            SabotageKind.POISON: lambda: _poison(call, target, caught),
            SabotageKind.ARSON: lambda: _arson(call, target),
            SabotageKind.DISCORD: lambda: _discord(call, target),
        }
        note = await effects[args.kind]()
    else:
        note = result(MortalResult.SABOTAGE_FAILED)
    label = lines.SABOTAGE_KINDS[args.kind.value]
    if caught:
        if not await enemies(call, call.me.id, target.id):
            await BondRepository(call.session).connect(BondDraft(target.id, call.me.id, BondKind.ENEMY, call.epoch, lines.SABOTAGE_BOND.format(kind=label)))
        if is_community(target) and is_community(call.me):
            await change_relation(call.tick, call.me.id, target.id, -tools.sabotage_caught_relation, label)
        note += lines.CAUGHT_SUFFIX
        await call.chronicle(
            ChronicleKind.INTRIGUE, lines.SABOTAGE_CAUGHT, entity_ids=[call.me.id, target.id], me=call.me.name, kind=label, target=target.name, note=note
        )
    else:
        await call.chronicle(ChronicleKind.INTRIGUE, lines.SABOTAGE_HIDDEN, entity_ids=[target.id], kind=label, target=target.name)
    return result(MortalResult.SABOTAGE_DONE, note=note[:1].upper() + note[1:])


async def build_spy_network(call: MortalCall, args: SpyInput) -> str:
    tools = call.rules.mortal_tools
    target = await require_target(call, args.target_id)
    if target.id == call.me.id or not is_community(target):
        await fail_with_candidates(call, MortalResult.SPY_TARGET, COMMUNITY_TYPES)
    if not await near(call, target):
        await fail_with_candidates(call, MortalResult.TOO_FAR, COMMUNITY_TYPES)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(call.me.id, target.id, BondKind.SPY_NETWORK):
        fail(MortalResult.SPIES_EXIST)
    mine = wits_of(call) + call.die(tools.spy_die, "spy_wits")
    theirs = first_stat(target, WATCH_CHAIN, tools.default_stat) + call.die(tools.spy_die, "spy_watch")
    call.target(target.id)
    if theirs > mine + tools.spy_caught_margin:
        relation = -tools.spy_war_threshold
        if is_community(call.me):
            relation = await change_relation(call.tick, target.id, call.me.id, -tools.spy_caught_relation, lines.SPIES_CAUGHT_EVENT)
        war = relation <= -tools.spy_war_threshold and await declare_war(call.tick, target.id, call.me.id, lines.SPIES_CAUGHT_EVENT, cause=WarCause.ESPIONAGE)
        await call.chronicle(ChronicleKind.INTRIGUE, lines.SPIES_CAUGHT, entity_ids=[call.me.id, target.id], me=call.me.name, target=target.name)
        return result(MortalResult.SPIES_CAUGHT, name=target.name, mine=mine, theirs=theirs, war=war)
    await bonds.connect(BondDraft(call.me.id, target.id, BondKind.SPY_NETWORK, call.epoch, args.cover))
    await call.chronicle(ChronicleKind.INTRIGUE, lines.SPIES, entity_ids=[target.id], target=target.name, cover=args.cover[:SPY_COVER_EXCERPT])
    return result(MortalResult.SPIES_PLANTED, name=target.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.DECLARE_WAR, mortal, DeclareWarInput, ToolMeta(ActionKind.DECLARE_WAR, standard), declare),
        ToolSpec(MortalToolId.SABOTAGE, mortal, SabotageInput, ToolMeta(ActionKind.SABOTAGE, standard), sabotage),
        ToolSpec(MortalToolId.BUILD_SPY_NETWORK, mortal, SpyInput, ToolMeta(ActionKind.BUILD_SPY_NETWORK, standard), build_spy_network),
    ]
