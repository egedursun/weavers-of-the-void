from typing import Any

from sqlalchemy import select

from aerona.catalog.life.tools import SEARCH_RUINS_SKILL_KINDS
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import HerdRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.body.hits import Harm
from aerona.engine.cosmos.fauna import merge_species as merge
from aerona.engine.ecology.domestication import KEPT, drill
from aerona.engine.ecology.pets import pet_kinds, pet_of, take_pet
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import skill_level
from aerona.engine.phases.afterlife import soul_bind
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import BindSpiritInput, KeepPetInput, MergeSpeciesInput, RuinsInput, TameInput, TrainHerdInput
from aerona.tools.mortal.support import first_stat, i_know, name_free, near, practised, same_region, wits_of

PERCENT = 100
SKILL_CHAIN = ("craft", "intellect")
BINDABLE = frozenset({EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})
RUIN_FLAGS = (EntityFlag.RUIN, EntityFlag.REMNANT, EntityFlag.EMPTY_TOMB)
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
    danger = stat_or(species, "danger", tools.tame_default_danger)
    giant = tools.tame_megafauna_difficulty if await EntityRepository(call.session).has_flag(species.id, EntityFlag.MEGAFAUNA) else 0
    difficulty = (
        danger / (tools.tame_danger_divisor / PERCENT)
        + (stat_or(species, "intelligence", tools.tame_default_intelligence)) / 2
        + giant
        + call.die(tools.tame_difficulty_die, "beast")
    )
    call.target(species.id)
    if skill >= difficulty:
        await bonds.connect(BondDraft(call.me.id, species.id, BondKind.TAMED, call.epoch, args.how))
        await call.record(
            "tools.mortal.tamed", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: species.id}, facts={"how": args.how, "danger": round(danger)}
        )
        return result(MortalResult.TAMED, name=species.name)
    attacked = call.rng("rage").probability(danger / tools.tame_attack_divisor)
    if attacked:
        kept = (PERCENT - tools.tame_attack_loss_pct) / PERCENT
        population = stat(call.me, "population")
        if population is not None:
            set_stats(call.me, population=max(1, round(population * kept)))
        hp = stat(call.me, "hp")
        if hp is not None and call.me.entity_type is EntityType.MORTAL:
            mauled = Harm(hp - max(1, round(hp * kept)), HarmCause.MONSTER, f"mauled by {species.name}", source_node_id=species.id, killer_id=species.id)
            await apply_hits(call.tick, call.me, mauled, lethal=False)
        await bonds.connect(BondDraft(species.id, call.me.id, BondKind.HUNTS, call.epoch, lines.ENRAGED))
    await call.record(
        "tools.mortal.tame_failed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: species.id},
        facts={"danger": round(danger), "attacked": int(attacked)},
    )
    return result(MortalResult.NOT_TAMED, name=species.name)


async def merge_species(call: MortalCall, args: MergeSpeciesInput) -> str:
    steps = call.rules.creatures.species_merge_distance
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
    description = lines.MERGED_DESCRIPTION.format(me=call.me.name, first=first.name, second=second.name, goal=args.goal)
    merged = await merge(call.tick, first, second, name=args.name, maker=call.me, description=description)
    await BondRepository(call.session).connect(BondDraft(call.me.id, merged.id, BondKind.TAMED, call.epoch, lines.SELF_MADE))
    call.remember_creation(merged.id)
    call.target(merged.id)
    held_traits = sorted(await EntityRepository(call.session).traits(merged.id))
    traits = [spoken(trait) for trait in held_traits]
    await call.record(
        "tools.mortal.species_merged",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.PARENT: [first.id, second.id], IncidentRole.PRODUCT: merged.id},
        facts={"traits": held_traits},
    )
    return result(MortalResult.SPECIES_MERGED, id=merged.id, name=merged.name, traits=TRAIT_SEPARATOR.join(traits) or NO_TRAITS)


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
    bound = await soul_bind(call.tick, spirit.id, target.id, call.me.id)
    animated = bound.id if bound.id != target.id else None
    if animated is not None:
        call.remember_creation(animated)
    call.target(target.id)
    return result(MortalResult.SPIRIT_BOUND, animated=animated)


async def _is_ruin(call: MortalCall, target: EntityRow) -> bool:
    if target.status in GONE:
        return False
    flags = await EntityRepository(call.session).flags(target.id)
    return bool(flags.intersection(RUIN_FLAGS)) or target.engine_kind is EngineKind.DEAD_GOD


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
    await practised(call, SEARCH_RUINS_SKILL_KINDS, call.rules.skills.travel_xp)
    call.target(ruin.id)
    lost = await _lost_knowledge(call, ruin.world_id)
    items = await _ownerless_items(call, ruin)
    if reason >= tools.relic_knowledge_threshold and lost:
        knowledge = call.rng("relic").pick(lost)
        await teach(call.tick, call.me.id, knowledge, lines.RUIN_FOUND.format(ruin=ruin.name))
        await EntityRepository(call.session).remove_flag(knowledge.id, EntityFlag.LOST)
        await call.record(
            "tools.mortal.ruin_knowledge", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: ruin.id, IncidentRole.PRODUCT: knowledge.id}
        )
        return result(MortalResult.RUIN_KNOWLEDGE, knowledge=knowledge.name, ruin=ruin.name)
    if reason >= tools.relic_item_threshold and items:
        item = items[0]
        await BondRepository(call.session).connect(BondDraft(call.me.id, item.id, BondKind.OWNS, call.epoch, lines.RUIN_FOUND.format(ruin=ruin.name)))
        await call.record(
            "tools.mortal.ruin_item",
            roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: ruin.id, IncidentRole.PRODUCT: item.id},
            facts={"reason": reason},
            place=ruin.id,
        )
        return result(MortalResult.RUIN_ITEM, item=item.name, ruin=ruin.name)
    if reason < tools.relic_curse_threshold:
        await EntityRepository(call.session).add_flag(call.me.id, EntityFlag.CURSED, call.epoch)
        await call.record("tools.mortal.ruin_curse", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: ruin.id}, kind=ChronicleKind.EXPLORATION)
        return result(MortalResult.RUIN_CURSE, ruin=ruin.name)
    await call.record("tools.mortal.ruin_nothing", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: ruin.id}, facts={"reason": reason}, place=ruin.id)
    return result(MortalResult.RUIN_NOTHING, ruin=ruin.name)


async def keep_pet(call: MortalCall, args: KeepPetInput) -> str:
    if call.me.entity_type is not EntityType.MORTAL or call.me.location_id is None:
        fail(MortalResult.PET_NONE)
    kept = await pet_of(call.tick, call.me.id)
    if kept is not None:
        fail(MortalResult.PET_ALREADY, id=kept.id, name=kept.name)
    kinds = await pet_kinds(call.tick, call.me.location_id)
    chosen = next((kind for kind in kinds if args.species_id is None or kind.id == args.species_id), None)
    if chosen is None:
        fail(MortalResult.PET_NONE)
    pet = await take_pet(call.tick, call.me, chosen)
    call.target(pet.id)
    await call.record("tools.mortal.pet_taken", roles={IncidentRole.OWNER: call.me.id, IncidentRole.SUBJECT: pet.id, IncidentRole.ORIGIN: chosen.id})
    return result(MortalResult.PET_TAKEN, id=pet.id, name=pet.name)


async def train_herd(call: MortalCall, args: TrainHerdInput) -> str:
    session, rules = call.session, call.rules
    herd = await session.get(HerdRow, (call.me.location_id, args.species_id)) if call.me.location_id is not None else None
    if call.me.entity_type is not EntityType.MORTAL or herd is None or herd.head <= 0 or herd.stage not in KEPT:
        fail(MortalResult.HERD_NONE)
    if held(herd.community_entity_id) or "training" in herd.locked or "trained" in herd.locked:
        fail(MortalResult.HERD_HELD)
    skill = await skill_level(session, call.me.id, SkillKind.BEAST_HANDLING)
    if skill < rules.husbandry.train_skill:
        fail(MortalResult.HERD_UNSKILLED, need=rules.husbandry.train_skill, have=skill)
    herd.training = args.training
    gained = drill(rules, herd, skill)
    await practised(call, (SkillKind.BEAST_HANDLING,), call.rules.skills.hunt_xp)
    kind = await session.get(EntityRow, args.species_id)
    name = kind.name if kind is not None else f"#{args.species_id}"
    call.target(args.species_id)
    await call.record(
        "tools.mortal.herd_trained",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: args.species_id},
        facts={"training": args.training, "gained": gained, "trained": herd.trained, "head": herd.head},
    )
    return result(MortalResult.HERD_TRAINED, id=args.species_id, name=name, training=spoken(args.training), gained=gained, trained=herd.trained, head=herd.head)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.TAME_SPECIES, mortal, TameInput, ToolMeta(ActionKind.TAME, standard), tame_species),
        ToolSpec(MortalToolId.KEEP_PET, mortal, KeepPetInput, ToolMeta(ActionKind.TAME, no_cost), keep_pet),
        ToolSpec(MortalToolId.TRAIN_HERD, mortal, TrainHerdInput, ToolMeta(ActionKind.TAME, standard), train_herd),
        ToolSpec(MortalToolId.MERGE_SPECIES, mortal, MergeSpeciesInput, ToolMeta(ActionKind.MERGE_SPECIES, standard), merge_species),
        ToolSpec(MortalToolId.BIND_SPIRIT, mortal, BindSpiritInput, ToolMeta(ActionKind.BIND_SPIRIT, standard), bind_spirit),
        ToolSpec(MortalToolId.SEARCH_RUINS, mortal, RuinsInput, ToolMeta(ActionKind.SEARCH_RUINS, standard), search_ruins),
    ]
