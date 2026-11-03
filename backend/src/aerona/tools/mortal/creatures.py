import re
from typing import Any

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.cosmos.fauna import weave_chimera as weave
from aerona.engine.phases.afterlife import soul_bind
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import BindSpiritInput, ChimeraInput, RuinsInput, TameInput
from aerona.tools.mortal.support import first_stat, i_know, name_free, near, practised, same_region, wits_of

PERCENT = 100
SKILL_CHAIN = ("craft", "intellect")
BINDABLE = frozenset({EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})
RUIN_FLAGS = (EntityFlag.RUIN, EntityFlag.REMNANT, EntityFlag.EMPTY_TOMB)
RUIN_WORDS = re.compile(r"ruin|remnant|wreck|tomb|corpse", re.IGNORECASE)
GONE = frozenset({EntityStatus.REJECTED, EntityStatus.DESTROYED})
TRAIT_SEPARATOR = ", "
NO_TRAITS = "none"


async def _species(call: MortalCall, species_id: int) -> EntityRow:
    species = await call.session.get(EntityRow, species_id)
    if species is None or species.status is not EntityStatus.CANON or species.entity_type is not EntityType.SPECIES:
        fail(MortalResult.NO_SPECIES)
    return species


async def tame_species(call: MortalCall, args: TameInput) -> str:
    await practised(call, (SkillKind.BEAST_HANDLING,), call.rules.skills.hunt_xp)
    tools = call.rules.mortal_tools
    species = await _species(call, args.species_id)
    if not (await same_region(call, species) or await near(call, species)):
        fail(MortalResult.SPECIES_FAR)
    bonds = BondRepository(call.session)
    if await bonds.exists_between(call.me.id, species.id, BondKind.TAMED):
        fail(MortalResult.ALREADY_TAMED)
    skill = (
        first_stat(call.me, SKILL_CHAIN, tools.default_stat) + stat_or(call.me, "charisma", 0) / tools.tame_charisma_divisor + call.die(tools.tame_die, "tamer")
    )
    danger = stat(species, "danger") or tools.tame_default_danger
    giant = tools.tame_megafauna_difficulty if await EntityRepository(call.session).has_flag(species.id, EntityFlag.MEGAFAUNA) else 0
    difficulty = (
        danger / (tools.tame_danger_divisor / PERCENT)
        + (stat(species, "intelligence") or tools.tame_default_intelligence) / 2
        + giant
        + call.die(tools.tame_difficulty_die, "beast")
    )
    call.target(species.id)
    if skill >= difficulty:
        await bonds.connect(BondDraft(call.me.id, species.id, BondKind.TAMED, call.epoch, args.how))
        await call.chronicle(ChronicleKind.DOMESTICATION, lines.TAMED, entity_ids=[call.me.id, species.id], me=call.me.name, species=species.name, how=args.how)
        return result(MortalResult.TAMED, name=species.name)
    if call.rng("rage").probability(danger / tools.tame_attack_divisor):
        kept = (PERCENT - tools.tame_attack_loss_pct) / PERCENT
        for key in ("population", "hp"):
            value = stat(call.me, key)
            if value is not None:
                set_stats(call.me, **{key: max(1, round(value * kept))})
        await bonds.connect(BondDraft(species.id, call.me.id, BondKind.HUNTS, call.epoch, lines.ENRAGED))
    await call.chronicle(ChronicleKind.DOMESTICATION, lines.TAME_FAILED, entity_ids=[call.me.id, species.id], me=call.me.name, species=species.name)
    return result(MortalResult.NOT_TAMED, name=species.name)


async def weave_chimera(call: MortalCall, args: ChimeraInput) -> str:
    steps = call.rules.creatures.chimera_weave_distance
    if not await i_know(call, KnowledgeBranch.BIOMANCY):
        fail(MortalResult.BIOMANCY_REQUIRED)
    if args.a_id == args.b_id:
        fail(MortalResult.TWO_SPECIES)
    first, second = await _species(call, args.a_id), await _species(call, args.b_id)
    atlas = await call.atlas()
    for species in (first, second):
        if species.world_id != call.me.world_id:
            fail(MortalResult.SPECIES_OTHER_WORLD, name=species.name)
        if atlas.distance(call.me.id, species.id) > steps:
            fail(MortalResult.SPECIES_TOO_FAR, name=species.name, steps=steps)
    await name_free(call, args.name)
    description = lines.CHIMERA_DESCRIPTION.format(me=call.me.name, first=first.name, second=second.name, goal=args.goal)
    chimera = await weave(call.tick, first, second, name=args.name, weaver=call.me, description=description)
    await BondRepository(call.session).connect(BondDraft(call.me.id, chimera.id, BondKind.TAMED, call.epoch, lines.WOVEN))
    call.remember_creation(chimera.id)
    call.target(chimera.id)
    traits = sorted(trait.value.replace("_", " ") for trait in await EntityRepository(call.session).traits(chimera.id))
    await call.chronicle(
        ChronicleKind.CHIMERA, lines.CHIMERA, entity_ids=[call.me.id, chimera.id], me=call.me.name, first=first.name, second=second.name, chimera=chimera.name
    )
    return result(MortalResult.CHIMERA_BORN, id=chimera.id, name=chimera.name, traits=TRAIT_SEPARATOR.join(traits) or NO_TRAITS)


async def bind_spirit(call: MortalCall, args: BindSpiritInput) -> str:
    if not (await i_know(call, KnowledgeBranch.MAGIC) or await i_know(call, KnowledgeBranch.BIOMANCY)):
        fail(MortalResult.MAGIC_REQUIRED)
    spirit = await call.session.get(EntityRow, args.spirit_id)
    if spirit is not None and spirit.entity_type is EntityType.SPIRIT and spirit.status is not EntityStatus.CANON:
        fail(MortalResult.SPIRIT_NOT_FREE, id=spirit.id, name=spirit.name)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT:
        fail(MortalResult.NO_FREE_SPIRIT)
    target = await call.session.get(EntityRow, args.target_id)
    if target is None or target.status is not EntityStatus.CANON or target.entity_type not in BINDABLE:
        fail(MortalResult.BIND_TARGET, reason=state_reason(target, args.target_id) if target is None or target.status is not EntityStatus.CANON else "")
    for thing in (spirit, target):
        if thing.world_id != call.me.world_id or not await near(call, thing):
            fail(MortalResult.BIND_TOO_FAR, name=thing.name)
    bound = await soul_bind(call.tick, spirit.id, target.id, call.me.name, call.me.id)
    golem = bound.id if bound.id != target.id else None
    if golem is not None:
        call.remember_creation(golem)
    call.target(target.id)
    return result(MortalResult.SPIRIT_BOUND, golem=golem)


async def _is_ruin(call: MortalCall, target: EntityRow) -> bool:
    if target.status in GONE:
        return False
    flags = await EntityRepository(call.session).flags(target.id)
    return bool(flags.intersection(RUIN_FLAGS)) or target.engine_kind is EngineKind.GOD_CORPSE or bool(RUIN_WORDS.search(target.subtype or ""))


async def _lost_knowledge(call: MortalCall, world_id: int) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON)
    entities = EntityRepository(call.session)
    return [knowledge for knowledge in await call.session.scalars(statement.order_by(EntityRow.id)) if await entities.has_flag(knowledge.id, EntityFlag.LOST)]


async def _ownerless_items(call: MortalCall, ruin: EntityRow) -> list[EntityRow]:
    bonds = BondRepository(call.session)
    contents = await EntityRepository(call.session).contents(ruin.id)
    return [item for item in contents if item.entity_type is EntityType.ITEM and not await bonds.incoming(item.id, BondKind.OWNS)]


async def search_ruins(call: MortalCall, args: RuinsInput) -> str:
    tools = call.rules.mortal_tools
    ruin = await call.session.get(EntityRow, args.target_id)
    if ruin is None or not await _is_ruin(call, ruin):
        fail(MortalResult.NOT_A_RUIN)
    if ruin.world_id != call.me.world_id or not (await same_region(call, ruin) or await near(call, ruin)):
        fail(MortalResult.TOO_FAR)
    shares = await class_shares(call.session, call.rules, call.me.id)
    reason = (await wits_of(call)) + shares.get(SocialClass.SCRIBE, 0.0) * tools.relic_scribe_mult + call.die(tools.relic_die, "ruins")
    await practised(call, (SkillKind.LORE, SkillKind.TRACKING), call.rules.skills.travel_xp)
    call.target(ruin.id)
    lost = await _lost_knowledge(call, ruin.world_id)
    items = await _ownerless_items(call, ruin)
    if reason >= tools.relic_knowledge_threshold and lost:
        knowledge = call.rng("relic").pick(lost)
        await teach(call.tick, call.me.id, knowledge, lines.RUIN_FOUND.format(ruin=ruin.name))
        await EntityRepository(call.session).remove_flag(knowledge.id, EntityFlag.LOST)
        await call.chronicle(
            ChronicleKind.EXPLORATION,
            lines.RUIN_KNOWLEDGE,
            entity_ids=[call.me.id, ruin.id, knowledge.id],
            me=call.me.name,
            knowledge=knowledge.name,
            ruin=ruin.name,
        )
        return result(MortalResult.RUIN_KNOWLEDGE, knowledge=knowledge.name, ruin=ruin.name)
    if reason >= tools.relic_item_threshold and items:
        item = items[0]
        await BondRepository(call.session).connect(BondDraft(call.me.id, item.id, BondKind.OWNS, call.epoch, lines.RUIN_FOUND.format(ruin=ruin.name)))
        await call.chronicle(
            ChronicleKind.EXPLORATION, lines.RUIN_ITEM, entity_ids=[call.me.id, ruin.id, item.id], me=call.me.name, item=item.name, ruin=ruin.name
        )
        return result(MortalResult.RUIN_ITEM, item=item.name, ruin=ruin.name)
    if reason < tools.relic_curse_threshold:
        await EntityRepository(call.session).add_flag(call.me.id, EntityFlag.CURSED, call.epoch)
        await call.chronicle(ChronicleKind.EXPLORATION, lines.RUIN_CURSE, entity_ids=[call.me.id, ruin.id], me=call.me.name, ruin=ruin.name)
        return result(MortalResult.RUIN_CURSE, ruin=ruin.name)
    await call.chronicle(ChronicleKind.EXPLORATION, lines.RUIN_NOTHING, entity_ids=[call.me.id, ruin.id], me=call.me.name, ruin=ruin.name)
    return result(MortalResult.RUIN_NOTHING, ruin=ruin.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.TAME_SPECIES, mortal, TameInput, ToolMeta(ActionKind.TAME, standard), tame_species),
        ToolSpec(MortalToolId.WEAVE_CHIMERA, mortal, ChimeraInput, ToolMeta(ActionKind.WEAVE_CHIMERA, standard), weave_chimera),
        ToolSpec(MortalToolId.BIND_SPIRIT, mortal, BindSpiritInput, ToolMeta(ActionKind.BIND_SPIRIT, standard), bind_spirit),
        ToolSpec(MortalToolId.SEARCH_RUINS, mortal, RuinsInput, ToolMeta(ActionKind.SEARCH_RUINS, standard), search_ruins),
    ]
