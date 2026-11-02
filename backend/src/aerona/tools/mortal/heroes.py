from typing import Any

from aerona.catalog.stats import max_hp
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.son import PowerEffect, SonDeathCause, SonStatus
from aerona.engine.gods.god_death import god_death
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.primitives.faith import has_unlocked_power
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import held_captive
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import AdoptInput, AdventureInput, DefyInput
from aerona.tools.mortal.support import first_stat, near, require_target, same_region

PERCENT = 100
OWNER_DEFENCE = ("defense", "strength")


async def _hunt(call: MortalCall, species: EntityRow, goal: str) -> str:
    if not await near(call, species):
        fail(MortalResult.CREATURE_TOO_FAR)
    await BondRepository(call.session).connect(BondDraft(call.me.id, species.id, BondKind.HUNTS, call.epoch, goal))
    await call.chronicle(ChronicleKind.ADVENTURE, lines.HUNT, entity_ids=[call.me.id, species.id], me=call.me.name, species=species.name, goal=goal)
    return result(MortalResult.HUNT_BEGUN)


async def _seize(call: MortalCall, item: EntityRow, goal: str) -> str:
    tools = call.rules.mortal_tools
    bonds = BondRepository(call.session)
    owned = await bonds.incoming(item.id, BondKind.OWNS)
    owner = await call.session.get(EntityRow, owned[0].source_node_id) if owned else None
    if owner is not None and owner.id == call.me.id:
        fail(MortalResult.ALREADY_YOURS)
    if owner is not None and not await near(call, owner):
        fail(MortalResult.ITEM_OWNER_FAR)
    if owner is None and not await near(call, item):
        fail(MortalResult.ITEM_TOO_FAR)
    default = tools.default_stat
    mine = stat_or(call.me, "agility", default) + stat_or(call.me, "intellect", default) // 2 + call.die(tools.seize_item_die, "seize")
    theirs = (first_stat(owner, OWNER_DEFENCE, default) if owner is not None else default) + call.die(tools.seize_item_die, "guard")
    if mine >= theirs:
        for bond in owned:
            await bonds.deactivate(bond, call.epoch, lines.SEIZE_BOND.format(goal=goal)[:KEY_MAX_LENGTH])
        await bonds.connect(BondDraft(call.me.id, item.id, BondKind.OWNS, call.epoch, lines.SEIZE_BOND.format(goal=goal)))
        if owner is not None:
            await bonds.connect(BondDraft(owner.id, call.me.id, BondKind.ENEMY, call.epoch, lines.STOLEN.format(item=item.name)))
        holder = lines.ITEM_OWNER.format(owner=owner.name) if owner is not None else ""
        await call.chronicle(ChronicleKind.ADVENTURE, lines.SEIZED, entity_ids=[call.me.id, item.id], me=call.me.name, item=item.name, owner=holder, goal=goal)
        return result(MortalResult.ITEM_SEIZED, name=item.name, mine=mine, theirs=theirs)
    hp = stat(call.me, "hp")
    if hp is not None:
        set_stats(call.me, hp=max(1, min(call.rules.limits.hp_cap, hp - tools.seize_item_fail_wound)))
    await call.chronicle(ChronicleKind.ADVENTURE, lines.SEIZE_FAILED, entity_ids=[call.me.id, item.id], me=call.me.name, item=item.name)
    return result(MortalResult.SEIZE_FAILED, mine=mine, theirs=theirs)


async def go_on_adventure(call: MortalCall, args: AdventureInput) -> str:
    target = await call.session.get(EntityRow, args.target_id)
    if target is None or target.status is not EntityStatus.CANON:
        fail(MortalResult.NOT_IN_WORLD)
    call.target(target.id)
    if target.entity_type is EntityType.SPECIES:
        return await _hunt(call, target, args.goal)
    if target.entity_type is EntityType.ITEM:
        return await _seize(call, target, args.goal)
    fail(MortalResult.ADVENTURE_TARGET)


async def _weapons(call: MortalCall) -> float:
    tools = call.rules.mortal_tools
    total = 0.0
    for bond in await BondRepository(call.session).outgoing(call.me.id, BondKind.OWNS):
        item = await call.session.get(EntityRow, bond.target_node_id)
        if item is not None and item.entity_type is EntityType.ITEM and item.status is EntityStatus.CANON:
            total += stat_or(item, "damage", 0) / tools.defy_god_damage_divisor + stat_or(item, "might", 0) / tools.defy_god_might_divisor
    return total


async def _slay(call: MortalCall, son: SonRow, args: DefyInput, mine: int, theirs: int) -> str:
    tools = call.rules.mortal_tools
    set_stats(call.me, charisma=min(PERCENT, stat_or(call.me, "charisma", 0) + tools.godslayer_charisma))
    call.me.title = lines.GODSLAYER_TITLE
    await god_death(call.tick, son, lines.SLAIN_BY.format(me=call.me.name), SonDeathCause.OTHER)
    await BondRepository(call.session).connect(BondDraft(call.me.id, son.id, BondKind.KILLED, call.epoch, args.reason))
    await call.chronicle(
        ChronicleKind.WAR_OF_GODS,
        lines.GODSLAYER,
        entity_ids=[call.me.id],
        about=son.id,
        me=call.me.name,
        son=son.name,
        mine=mine,
        theirs=theirs,
        reason=args.reason,
    )
    return result(MortalResult.GOD_SLAIN, title=lines.GODSLAYER_TITLE)


async def _wound_god(call: MortalCall, son: SonRow, args: DefyInput, mine: int, theirs: int) -> str:
    tools = call.rules.mortal_tools
    wound = round(max_hp(call.rules, son.endurance) * tools.god_wound_pct / PERCENT)
    son.hp = max(1, son.hp - wound)
    son.fame = max(0, son.fame - tools.god_wound_renown_loss)
    set_stats(call.me, charisma=min(PERCENT, stat_or(call.me, "charisma", 0) + tools.god_wounder_charisma))
    title = lines.WOUNDER_TITLE.format(son=son.name)
    call.me.title = title
    await BondRepository(call.session).connect(BondDraft(son.id, call.me.id, BondKind.ENEMY, call.epoch, lines.DEFEAT_BOND.format(reason=args.reason)))
    await call.chronicle(
        ChronicleKind.WAR_OF_GODS,
        lines.GOD_WOUNDED,
        entity_ids=[call.me.id],
        about=son.id,
        me=call.me.name,
        son=son.name,
        mine=mine,
        theirs=theirs,
        reason=args.reason,
    )
    return result(MortalResult.GOD_WOUNDED, title=title)


async def _defeated(call: MortalCall, son: SonRow, args: DefyInput, mine: int, theirs: int) -> str:
    tools = call.rules.mortal_tools
    if call.die(PERCENT, "defiance_death") <= tools.defy_god_death_chance:
        await die(call.tick, call.me, cause=lines.DEFIANCE_DEATH.format(epoch=call.epoch, son=son.name), killer_id=son.id)
        son.fame += tools.god_crush_renown
        call.died = True
        await call.chronicle(
            ChronicleKind.WAR_OF_GODS, lines.DEFIER_DIED, entity_ids=[call.me.id], about=son.id, me=call.me.name, son=son.name, reason=args.reason
        )
        return result(MortalResult.DEFIER_DIED, mine=mine, theirs=theirs)
    await EntityRepository(call.session).add_flag(call.me.id, EntityFlag.CURSED, call.epoch)
    await BondRepository(call.session).connect(BondDraft(son.id, call.me.id, BondKind.CURSED, call.epoch, lines.INSOLENCE))
    await call.chronicle(
        ChronicleKind.WAR_OF_GODS, lines.DEFIER_CURSED, entity_ids=[call.me.id], about=son.id, me=call.me.name, son=son.name, reason=args.reason
    )
    return result(MortalResult.DEFIER_CURSED)


async def challenge_god(call: MortalCall, args: DefyInput) -> str:
    tools = call.rules.mortal_tools
    son = await call.session.get(SonRow, args.son_id)
    if son is None:
        fail(MortalResult.NO_SUCH_GOD)
    if son.status is SonStatus.DEAD:
        fail(MortalResult.GOD_ALREADY_DEAD, name=son.name)
    default = tools.default_stat
    me = call.me
    mine = round(
        stat_or(me, "strength", default)
        + stat_or(me, "agility", default) / 2
        + stat_or(me, "intellect", default) / tools.defy_god_intellect_divisor
        + await _weapons(call)
        + call.die(tools.defy_god_die, "defier")
    )
    untouchable = tools.defy_god_untouchable if await has_unlocked_power(call.session, call.rules, son, PowerEffect.UNTOUCHABLE) else 0
    theirs = round(son.strength / 2 + son.will / 2 + son.level * tools.defy_god_strength_per_level + call.die(tools.defy_god_die, "god") + untouchable)
    call.target(son.id)
    if mine >= theirs and mine - theirs >= tools.godslayer_margin and son.existence < tools.godslayer_max_existence:
        return await _slay(call, son, args, mine, theirs)
    if mine >= theirs:
        return await _wound_god(call, son, args, mine, theirs)
    return await _defeated(call, son, args, mine, theirs)


async def adopt(call: MortalCall, args: AdoptInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.ADOPTIONS, tools.adopt_per_epoch, "mortal_tools.adopt_per_epoch", MortalResult.ADOPT_LIMIT)
    child = await require_target(call, args.child_id)
    if child.id == call.me.id or child.entity_type is not EntityType.MORTAL:
        fail(MortalResult.ADOPT_TARGET)
    if await held_captive(call.session, child.id) is not None:
        fail(MortalResult.ADOPT_CAPTIVE, name=child.name)
    if not (await same_region(call, child) or await near(call, child)):
        fail(MortalResult.ADOPT_FAR, name=child.name)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(call.me.id, child.id, BondKind.DESCENDS_FROM):
        fail(MortalResult.LINEAGE_EXISTS, name=child.name)
    mine, theirs = stat(call.me, "age"), stat(child, "age")
    if mine is not None and theirs is not None and theirs >= mine:
        fail(MortalResult.NOT_YOUNGER, name=child.name, mine=mine, theirs=theirs)
    await bonds.connect(BondDraft(child.id, call.me.id, BondKind.DESCENDS_FROM, call.epoch, lines.ADOPTION_BOND.format(reason=args.reason)))
    await change_relation(call.tick, call.me.id, child.id, call.rules.civilization.adoption_relation, lines.ADOPTION_EVENT)
    await call.bump(TurnCounter.ADOPTIONS)
    call.target(child.id)
    await call.chronicle(ChronicleKind.LINEAGE, lines.ADOPTED, entity_ids=[call.me.id, child.id], me=call.me.name, child=child.name, reason=args.reason)
    return result(MortalResult.ADOPTED, name=child.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.GO_ON_ADVENTURE, mortal, AdventureInput, ToolMeta(ActionKind.ADVENTURE, mortal_standard_action), go_on_adventure),
        ToolSpec(MortalToolId.CHALLENGE_GOD, mortal, DefyInput, ToolMeta(ActionKind.DEFY_GOD, mortal_standard_action), challenge_god),
        ToolSpec(MortalToolId.ADOPT, mortal, AdoptInput, ToolMeta(ActionKind.ADOPT, lambda rules: rules.mortal_tools.adopt_ap), adopt),
    ]
