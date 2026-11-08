import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from aerona.catalog.bonds import BOND_KINDS
from aerona.catalog.domains import match_domain
from aerona.catalog.entity_types import ENTITY_TYPES, EntityTypeSpec
from aerona.catalog.gates import CREATION_GATE_RULES
from aerona.catalog.knowledge import branch_label
from aerona.catalog.rarities import name_similarity_policy
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import AGENT_TYPES, LIVING_CREATION_TYPES, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.domain.enums.mortal import MortalSex
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.models.entity_stats import MortalStats
from aerona.domain.models.phonology import Phonology
from aerona.engine.body.book import ensure_species_body
from aerona.engine.ecology.anatomy import beast_anatomy
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.gods.progress import power_ceiling
from aerona.engine.gods.rewards import RewardDraft, creation_gains, creation_value, fade_pct, record_reward
from aerona.engine.mind.book import add_trait
from aerona.engine.phases.exploration import land_measure
from aerona.engine.phases.knowledge_levels import empty_branch_hint, empty_branches, same_branch
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.engine.primitives.subtypes import normalized_subtype, tidy
from aerona.language.alphabet import first_word, fold_letter
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.shared_inputs import LinkInput, LinkTarget
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost, son_standard_action
from aerona.tools.framework.stats import fill_stats, mortal_age, stats_model
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.son import lines
from aerona.tools.son.creation_effects import EffectPlan, apply_effects, check_effects, finish_extras, mandatory_holder
from aerona.tools.son.creation_inputs import CREATION_INPUTS, CreationInput
from aerona.tools.son.creation_rules import (
    RepeatQuery,
    base_cost,
    cheap_creation,
    creation_cost,
    final_cost,
    repeat_multiplier,
    same_type_this_epoch,
    similar_creations,
    star_domain,
)
from aerona.tools.son.support import ensure_in_reach, grant, has_covenant, is_active, shift_relation, world_name
from aerona.tools.son.targets import check_links, resolve_location

LAND_TYPES = frozenset({EntityType.REGION, EntityType.PLACE})
FIRST_LIFE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL})
EPITHET = re.compile(r"^([^,(]{2,40}?)\s*(?:,\s*|\(\s*)([^,()]{3,60}?)\)?$")
NUMBERED = re.compile(r"\s(?:II|III|IV|V|VI|VII|VIII|IX)$")
LETTER = re.compile(r"[^\W\d_]")
CREATION_ACTION_KINDS = {entity_type: ActionKind.CREATE_ENTITY for entity_type in ENTITY_TYPES}
CREATION_STAT = "might"
TAG_SEPARATOR = ":"
MAKER_BONDS = frozenset({BondKind.PRODUCED, BondKind.BUILT})
PERCENT = 100
WEAVABLE_SOURCE_STATES = frozenset({EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.FULFILLED})


@dataclass
class CreationPlan:
    spec: EntityTypeSpec
    args: CreationInput
    name: str
    title: str | None
    subtype: str
    domain_label: str
    in_domain: bool
    linked: list[EntityRow]
    links: list[LinkInput]
    location: EntityRow | None
    free_living: bool = False
    free_land: bool = False
    crowded: bool = False
    thread: ThreadRow | None = None
    cost: int = 0
    share: int = 0
    partner: SonRow | None = None
    cheap: bool = False
    starred: bool = False
    repeat: float = 1.0
    similar: list[EntityRow] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    effects: EffectPlan | None = None
    notes: list[str] = field(default_factory=list)


async def _action_plan(call: SonCall, entity_type: EntityType) -> tuple[bool, bool, bool]:
    tools = call.rules.son_tools
    free_living = tools.free_living_creation > 0 and entity_type in LIVING_CREATION_TYPES and await call.count(TurnCounter.FREE_LIVING_CREATION) == 0
    crowded = entity_type in LAND_TYPES and call.world_id is not None and (await land_measure(call.session, call.rules, call.world_id)).narrow
    exploration = call.rules.exploration
    free_land = crowded and exploration.free_land_creation > 0 and not free_living and await call.count(TurnCounter.FREE_LAND_CREATION) == 0
    if not (free_living or free_land):
        call.require_actions(tools.standard_action_cost)
    return free_living, free_land, crowded


async def _naming(call: SonCall, args: CreationInput) -> tuple[str, str | None]:
    name = " ".join(args.name.split())
    title = args.option("title")
    found = EPITHET.match(name)
    if found is not None and LETTER.search(found.group(2)):
        name, title = found.group(1).strip(), title or found.group(2).strip()
    if NUMBERED.search(name):
        fail(SonResult.NUMBERED_NAME, name=name)
    names = NameRepository(call.session)
    if await names.is_taken(name):
        fail(SonResult.NAME_TAKEN, name=name)
    similar = await names.similar_name(name, name_similarity_policy(call.rules))
    if similar is not None:
        fail(SonResult.NAME_SIMILAR, name=name, other=similar)
    return name, title


async def _thread(call: SonCall, plan: CreationPlan) -> None:
    thread_id = plan.args.story_id
    if thread_id is None:
        return
    thread = await call.session.get(ThreadRow, thread_id)
    if thread is None or thread.status is not ThreadStatus.OPEN:
        plan.notes.append(result(SonResult.THREAD_CLOSED, id=thread_id))
        return
    plan.thread = thread


async def _price(call: SonCall, plan: CreationPlan, entity_type: EntityType) -> None:
    son = call.son
    plan.cheap = await cheap_creation(call.session, call.rules, son, entity_type)
    base = creation_cost(
        call.rules, base_cost(call.rules, entity_type), plan.args.power_level, in_domain=plan.in_domain, creativity=son.creativity, cheap=plan.cheap
    )
    star = await star_domain(call.session, call.world_id)
    plan.starred = star is not None and star.value == plan.domain_label
    query = RepeatQuery(son.id, entity_type, plan.subtype, plan.args.description, plan.name, call.epoch)
    plan.similar = await similar_creations(call.session, call.rules, query)
    plan.repeat = repeat_multiplier(call.rules, len(plan.similar))
    plan.cost = final_cost(call.rules, base, plan.starred, plan.repeat)
    plan.share = plan.cost
    partner_id = plan.args.co_creator_id
    if partner_id is not None and partner_id != son.id:
        partner = await call.session.get(SonRow, partner_id)
        if partner is None or not is_active(partner):
            fail(SonResult.PARTNER_UNAVAILABLE)
        if not await has_covenant(call, partner.id):
            fail(SonResult.PARTNER_NO_COVENANT, name=partner.name)
        if partner.essence < math.ceil(plan.cost / 2):
            fail(SonResult.PARTNER_POOR, name=partner.name, have=partner.essence, share=math.ceil(plan.cost / 2))
        plan.partner = partner
        plan.share = plan.cost // 2
    if son.essence < plan.share:
        fail(SonResult.CREATION_ESSENCE, cost=plan.share, have=son.essence)


async def _source_might(call: SonCall, plan: CreationPlan) -> None:
    if plan.spec.type is not EntityType.ITEM:
        return
    divisor = max(1, call.rules.son_tools.item_resource_might_divisor)
    for link in plan.links:
        if link.kind is not BondKind.SOURCE_OF or link.target_kind is not LinkTarget.ENTITY:
            continue
        resource = await call.session.get(EntityRow, link.target_id)
        might = getattr(resource.stats, CREATION_STAT, None) if resource is not None and resource.entity_type is EntityType.RESOURCE else None
        if isinstance(might, int):
            plan.stats[CREATION_STAT] = max(0, min(PERCENT, plan.stats.get(CREATION_STAT, 0) + round(might / divisor)))


def story_tags(tags: list[str]) -> list[str]:
    mechanical = {flag.value.replace("_", " ") for flag in EntityFlag} | {trait.value.replace("_", " ") for trait in CreatureTrait}
    kept = [tag.strip() for tag in tags if tag.strip() and TAG_SEPARATOR not in tag and tag.strip().casefold().replace("_", " ") not in mechanical]
    return list(dict.fromkeys(kept))


async def _land_relief(call: SonCall, entity_type: EntityType, location: EntityRow | None) -> bool:
    if call.world_id is None or await call.count(TurnCounter.LAND_REWARDS) > 0:
        return False
    if entity_type is EntityType.REGION:
        return True
    if location is None:
        return False
    measure = await land_measure(call.session, call.rules, call.world_id)
    region = (await RegionAtlas.load(call.session)).top_region(location.id)
    return region is not None and any(crowded == region for crowded, _count in measure.crowded)


async def _branch_room(call: SonCall, entity_type: EntityType, branch: KnowledgeBranch | None) -> None:
    if entity_type is not EntityType.KNOWLEDGE or branch is None or call.world_id is None:
        return
    present = await same_branch(call.session, call.rules, call.world_id, branch)
    if len(present) < call.rules.knowledge.branch_record_cap:
        return
    existing = ", ".join(f"#{item.id} {item.name} (level {knowledge_level(call.rules, item)})" for item in present)
    empty = await empty_branches(call.session, call.world_id)
    hint = lines.EMPTY_BRANCHES.format(branches=empty_branch_hint(call.rules, empty)) if empty else ""
    fail(SonResult.BRANCH_FULL, existing=existing, branch=branch_label(branch), hint=hint)


async def _prepare(call: SonCall, args: CreationInput, entity_type: EntityType) -> CreationPlan:
    spec = ENTITY_TYPES[entity_type]
    free_living, free_land, crowded = await _action_plan(call, entity_type)
    domain = match_domain(args.domain or "") or call.son.domain_primary
    subtype = await normalized_subtype(call.session, entity_type, args.subtype or spec.label.lower()) or ""
    links: list[LinkInput] = list(args.links[: call.rules.son_tools.creation_max_links])
    name, title = await _naming(call, args)
    ceiling = power_ceiling(call.rules, call.son)
    if args.power_level > ceiling:
        fail(SonResult.POWER_CEILING, ceiling=ceiling)
    await _branch_room(call, entity_type, args.option("branch"))
    worshipped_id = args.option("worshipped_son_id")
    if worshipped_id is not None:
        worshipped = await call.session.get(SonRow, worshipped_id)
        if worshipped is None or not worshipped.alive:
            fail(SonResult.WORSHIPPED_DEAD, id=worshipped_id)
    linked = await check_links(call, links, creating=True)
    location = await resolve_location(call, entity_type, args.option("location_id"), linked)
    rewarded = crowded and await _land_relief(call, entity_type, location)
    if free_land and not rewarded:
        free_land = False
        call.require_actions(call.rules.son_tools.standard_action_cost)
    plan = CreationPlan(spec, args, name, title, subtype, domain.value, domain in call.son.domains, linked, links, location, free_living, free_land, rewarded)
    await _thread(call, plan)
    await _price(call, plan, entity_type)
    plan.effects = await check_effects(call, plan.args, args.stat_values(), args.power_level)
    plan.stats = fill_stats(call.rules, spec, args.stat_values(), args.power_level)
    if entity_type is EntityType.MORTAL:
        plan.stats = mortal_age(call.rules, plan.stats, call.rng("mortal_age"))
    await _source_might(call, plan)
    return plan


def _traits(call: SonCall, args: CreationInput) -> list[CreatureTrait]:
    traits = [trait for trait in args.option("traits") or [] if isinstance(trait, CreatureTrait)]
    return list(dict.fromkeys(traits))[: call.rules.son_tools.creature_max_traits]


BEAST_ABILITIES = ("endurance", "perception", "willpower", "intelligence")
BEAST_BODY = ("breath", "gaze", "temperament", "habitat", "awakening", "skin")


async def shape_beast(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    kind_id = args.option("species_id")
    kind = await call.session.get(EntityRow, kind_id) if kind_id is not None else None
    species = kind if kind is not None and kind.entity_type is EntityType.SPECIES and kind.status is EntityStatus.CANON else None
    row = await profile_beast(call.tick, created, species, args.option("size_class"))
    if args.option("temper") is not None:
        row.temper = args.option("temper")
    for key in BEAST_ABILITIES:
        value = args.option(key)
        if value is not None:
            setattr(row, key, value)
    if species is not None:
        await BondRepository(call.session).connect(BondDraft(created.id, species.id, BondKind.DESCENDS_FROM, call.epoch, "the greatest of its kind"))
    shaped = {key: args.option(key) for key in BEAST_BODY if args.option(key) is not None}
    if shaped:
        anatomy = await beast_anatomy(call.tick, created, row)
        for key, value in shaped.items():
            setattr(anatomy, key, value)


def species_spec(args: CreationInput) -> SpeciesSpec:
    return SpeciesSpec(
        body_plan=args.option("body_plan"),
        size_class=args.option("size_class"),
        diet=args.option("diet"),
        sociality=args.option("sociality"),
        nocturnal=args.option("nocturnal"),
        migratory=args.option("migratory"),
        products=tuple(dict.fromkeys(args.option("products") or [])),
        species_class=args.option("species_class"),
        biochemistry=args.option("biochemistry"),
        growth_cycle=args.option("growth_cycle"),
        plant_yields=tuple(dict.fromkeys(args.option("plant_yields") or [])),
    )


async def _insert(call: SonCall, plan: CreationPlan) -> EntityRow:
    args = plan.args
    entity_type = plan.spec.type
    flags = [EntityFlag.MEGAFAUNA] if entity_type is EntityType.SPECIES and args.power_level >= call.rules.son_tools.megafauna_power else []
    world_id = plan.location.world_id if plan.location is not None else call.world_id
    domain = match_domain(plan.domain_label)
    draft = EntityDraft(
        name=plan.name,
        entity_type=entity_type,
        description=args.description.strip(),
        stats=stats_model(plan.spec, plan.stats),
        power_level=args.power_level,
        origin=EntityOrigin.SON,
        birth_epoch=call.epoch,
        world_id=world_id,
        location_id=plan.location.id if plan.location is not None else None,
        creator_son_id=call.son.id,
        title=plan.title,
        subtype=tidy(plan.subtype) or None,
        domain=domain,
        natural_law=args.option("mechanic"),
        knowledge_branch=args.option("branch"),
        legend_category=args.option("legend_category"),
        image_prompt=args.image_prompt,
        is_water=entity_type is EntityType.REGION and bool(args.option("water")),
        flags=flags,
        tags=story_tags(args.tags or []),
        traits=_traits(call, args),
        split_title=False,
    )
    return await EntityRepository(call.session).create(draft)


async def _bonds(call: SonCall, plan: CreationPlan, created: EntityRow) -> None:
    bonds = BondRepository(call.session)
    for link in plan.links:
        if link.kind is BondKind.INSIDE and plan.location is not None and link.target_id == plan.location.id:
            continue
        if link.target_id == created.id:
            continue
        target = await call.session.get(EntityRow, link.target_id) if link.target_kind is LinkTarget.ENTITY else None
        if link.kind in MAKER_BONDS and created.entity_type not in AGENT_TYPES and target is not None and target.entity_type in AGENT_TYPES:
            await bonds.connect(BondDraft(target.id, created.id, link.kind, call.epoch, link.description))
            continue
        await bonds.connect(BondDraft(created.id, link.target_id, link.kind, call.epoch, link.description))
    worshipped_id = plan.args.option("worshipped_son_id") or (call.son.id if plan.spec.type is EntityType.CULT else None)
    has_worship = any(link.kind is BondKind.WORSHIPS and link.target_kind is LinkTarget.SON for link in plan.links)
    worshipped = await call.session.get(SonRow, worshipped_id) if worshipped_id is not None else None
    if worshipped is not None and not has_worship:
        await bonds.connect(BondDraft(created.id, worshipped.id, BondKind.WORSHIPS, call.epoch))
    await mandatory_holder(call, created, plan.linked, plan.location)


async def _first_life(call: SonCall, created: EntityRow) -> bool:
    if created.entity_type not in FIRST_LIFE_TYPES:
        return False
    statement = select(EntityRow.id).where(
        EntityRow.world_id == created.world_id,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.entity_type.in_(list(FIRST_LIFE_TYPES)),
        EntityRow.id != created.id,
    )
    return await call.session.scalar(statement.limit(1)) is None


async def _rewards(call: SonCall, plan: CreationPlan, created: EntityRow) -> str:
    son = call.son
    tools = call.rules.son_tools
    empty = call.rules.empty_world
    power = plan.args.power_level
    first_life = await _first_life(call, created)
    call.spend_essence(plan.share)
    essence_before = son.essence
    land_renown = 0
    if plan.crowded:
        exploration = call.rules.exploration
        call.gain_essence(exploration.land_creation_essence)
        land_renown = exploration.land_creation_renown
        son.fame += land_renown
        await call.bump(TurnCounter.LAND_REWARDS)
        await call.chronicle(ChronicleKind.EXPLORATION, lines.CROWDED_LAND, entity_ids=[created.id], son=son.name, type=plan.spec.noun, name=created.name)
    fade = fade_pct(call.rules, await same_type_this_epoch(call.session, son.id, created.entity_type, call.epoch, created.id))
    value = creation_value(call.rules, base_cost(call.rules, created.entity_type), power)
    gained_xp, gained_renown = creation_gains(call.rules, value, power, fade)
    xp = gained_xp + (empty.first_people_xp if first_life else 0)
    renown = gained_renown + (empty.first_people_renown if first_life else 0)
    level = await grant(call, son, xp, renown)
    if first_life:
        call.gain_essence(empty.first_people_essence)
        world = await world_name(call, created.world_id)
        await call.chronicle(ChronicleKind.ASCENSION, lines.FIRST_LIFE, entity_ids=[created.id], son=son.name, world=world, name=created.name)
    partner = plan.partner
    partner_xp = tools.co_creator_xp_base + power * tools.co_creator_xp_per_power
    if partner is not None:
        partner.essence = max(0, partner.essence - (plan.cost - plan.share))
        partner.xp += partner_xp
        partner.fame += tools.co_creator_renown
        await BondRepository(call.session).connect(BondDraft(partner.id, created.id, BondKind.PRODUCED, call.epoch, lines.CO_CREATOR))
        await shift_relation(call, partner.id, tools.co_creation_relation)
    record_reward(
        call.session,
        RewardDraft(
            entity_id=created.id,
            son_id=son.id,
            epoch=call.epoch,
            xp=xp,
            renown=renown + land_renown,
            essence=max(0, son.essence - essence_before),
            cost=plan.share,
            land=plan.crowded,
            thread_id=plan.thread.id if plan.thread is not None else None,
            fade_pct=fade,
            repeats=len(plan.similar),
            partner_son_id=partner.id if partner is not None else None,
            partner_xp=partner_xp if partner is not None else 0,
            partner_renown=tools.co_creator_renown if partner is not None else 0,
            partner_cost=plan.cost - plan.share if partner is not None else 0,
        ),
    )
    plan.notes.append(result(SonResult.CREATION_GAIN, xp=xp, renown=renown + land_renown, fade=fade, faded=fade < PERCENT, kind=plan.spec.noun))
    if plan.similar:
        names = ", ".join(f"#{item.id} {item.name}" for item in plan.similar[: tools.repeat_names_shown])
        plan.notes.append(result(SonResult.CREATION_REPEATS, names=names))
    if (
        created.entity_type in LAND_TYPES
        and not plan.crowded
        and call.world_id is not None
        and (await land_measure(call.session, call.rules, call.world_id)).narrow
    ):
        plan.notes.append(result(SonResult.NO_LAND_REWARD))
    return level


async def _settle_actions(call: SonCall, plan: CreationPlan) -> None:
    if plan.free_living:
        await call.bump(TurnCounter.FREE_LIVING_CREATION)
        call.waive_actions()
    elif plan.free_land:
        await call.bump(TurnCounter.FREE_LAND_CREATION)
        call.waive_actions()
    else:
        call.charge_actions(call.rules.son_tools.standard_action_cost)


def _foreign_sounds(name: str, phonology: Phonology | None) -> str | None:
    if phonology is None:
        return None
    known = {fold_letter(letter) for sound in (*phonology.vowels, *phonology.consonants) for letter in sound if letter.isalpha()}
    missing = sorted({fold_letter(letter) for letter in first_word(name) if letter.isalpha()} - known)
    return result(SonResult.FOREIGN_SOUNDS, sounds=", ".join(missing)) if missing else None


async def _mortal_nature(call: SonCall, args: CreationInput, created: EntityRow) -> None:
    sex = args.option("sex")
    if sex is not None and isinstance(created.stats, MortalStats):
        created.stats = created.stats.model_copy(update={"sex": MortalSex(sex).value})
    for trait in args.option("traits") or []:
        await add_trait(call.session, created.id, TraitKind(trait), TraitSource.BIRTH, call.epoch)


async def create_entity(call: SonCall, args: CreationInput, entity_type: EntityType) -> str:
    plan = await _prepare(call, args, entity_type)
    created = await _insert(call, plan)
    call.target(created.id)
    if entity_type is EntityType.SPECIES:
        await ensure_species_body(call.session, created, args.option("body_plan"))
        await profile_of(call.tick, created, species_spec(args))
    if entity_type is EntityType.BEAST:
        await shape_beast(call, args, created)
    if entity_type is EntityType.MORTAL:
        await _mortal_nature(call, args, created)
    await _bonds(call, plan, created)
    effect_notes = await apply_effects(call, created, plan.effects)
    if plan.effects is not None:
        plan.notes.extend(plan.effects.clipped)
    level = await _rewards(call, plan, created)
    await _settle_actions(call, plan)
    call.remember_creation(created.id)
    plan.notes.extend(await finish_extras(call, plan.args, created))
    if plan.thread is not None:
        plan.thread.progress += 1
        call.session.add(ThreadLinkRow(thread_id=plan.thread.id, entity_id=created.id, role=ThreadLinkRole.ADVANCED, epoch=call.epoch))
    subtype = lines.SUBTYPE_SUFFIX.format(subtype=plan.subtype) if plan.subtype and plan.subtype.casefold() != plan.spec.label.casefold() else ""
    await call.chronicle(
        ChronicleKind.CREATION,
        lines.CREATED,
        entity_ids=[created.id],
        world_id=created.world_id,
        son=call.son.name,
        partner=lines.TOGETHER.format(partner=plan.partner.name) if plan.partner is not None else "",
        type=plan.spec.noun,
        name=created.name,
        subtype=subtype,
        location=lines.INSIDE_SUFFIX.format(location=plan.location.name) if plan.location is not None else "",
        effects=" " + "; ".join(effect_notes) if effect_notes else "",
    )
    world = await call.session.get(WorldRow, created.world_id)
    sound = _foreign_sounds(created.name, world.phonology if world is not None else None)
    notes = [*plan.notes, *([sound] if sound else []), *([level] if level else [])]
    return result(
        SonResult.CREATED,
        id=created.id,
        name=created.name,
        cost=plan.share,
        partner=plan.partner.name if plan.partner is not None else "",
        rest=plan.cost - plan.share,
        in_domain=plan.in_domain,
        cheap=plan.cheap,
        starred=plan.starred,
        repeat=f"{plan.repeat:.2f}" if plan.repeat > 1 else "",
        no_anchor=call.son.anchor_entity_id is None,
        notes=notes,
    )


def example_cost(rules: Rules, son: SonRow, entity_type: EntityType, cheap: bool) -> int:
    return creation_cost(rules, base_cost(rules, entity_type), 1, in_domain=True, creativity=son.creativity, cheap=cheap)


def _handler(entity_type: EntityType) -> Callable[[SonCall, CreationInput], Awaitable[str]]:
    async def handle(call: SonCall, args: CreationInput) -> str:
        return await create_entity(call, args, entity_type)

    return handle


def _base(entity_type: EntityType) -> Callable[[Rules], int]:
    def cost(rules: Rules) -> int:
        return base_cost(rules, entity_type)

    return cost


def _gate(entity_type: EntityType) -> Callable[[Rules], Rarity]:
    def minimum(rules: Rules) -> Rarity:
        return Rarity.from_rank(CREATION_GATE_RULES[entity_type](rules))

    return minimum


class MakeBondInput(ToolInput):
    source_id: int
    target: LinkInput


async def make_bond(call: SonCall, args: MakeBondInput) -> str:
    tools = call.rules.son_tools
    await call.within_limit(TurnCounter.NARRATIVE_BONDS, tools.link_per_epoch, "son_tools.link_per_epoch", SonResult.BONDS_LIMIT)
    if call.son.essence < tools.link_cost:
        fail(SonResult.BOND_ESSENCE)
    link = args.target
    if not BOND_KINDS[link.kind].weavable:
        fail(SonResult.BOND_MECHANICAL, kind=link.kind.value, allowed=", ".join(kind.value for kind, spec in BOND_KINDS.items() if spec.weavable))
    source = await call.session.get(EntityRow, args.source_id)
    if source is None or source.status not in WEAVABLE_SOURCE_STATES:
        fail(SonResult.BOND_SOURCE, reason=state_reason(source, args.source_id))
    await ensure_in_reach(call, source)
    await check_links(call, [link])
    if link.target_kind is LinkTarget.ENTITY and link.target_id == source.id:
        fail(SonResult.BOND_SELF)
    call.spend_essence(tools.link_cost)
    call.target(source.id)
    await BondRepository(call.session).connect(BondDraft(source.id, link.target_id, link.kind, call.epoch, link.description))
    await call.bump(TurnCounter.NARRATIVE_BONDS)
    target_name = await NodeRepository(call.session).name_of(link.target_id)
    description = lines.BOND_DESCRIPTION.format(description=link.description) if link.description else ""
    await call.chronicle(
        ChronicleKind.CREATION,
        lines.BOND,
        entity_ids=[source.id, link.target_id] if link.target_kind is LinkTarget.ENTITY else [source.id],
        son=call.son.name,
        source=source.name,
        relation=BOND_KINDS[link.kind].label,
        target=target_name,
        description=description,
    )
    return result(SonResult.BOND_MADE)


def creation_specs() -> list[ToolSpec[SonCall, Any]]:
    specs: list[ToolSpec[SonCall, Any]] = []
    for entity_type, model in CREATION_INPUTS.items():
        tool = ENTITY_TYPES[entity_type].creation_tool
        if tool is None:
            continue
        meta = ToolMeta(
            CREATION_ACTION_KINDS[entity_type],
            son_standard_action,
            essence_cost=_base(entity_type),
            rarity_gate=_gate(entity_type),
            flexible_actions=True,
        )
        specs.append(ToolSpec(SonToolId(tool), AgentKind.SON, model, meta, _handler(entity_type)))
    bond_meta = ToolMeta(ActionKind.WEAVE_BOND, no_cost, essence_cost=lambda rules: rules.son_tools.link_cost)
    return [ToolSpec(SonToolId.MAKE_BOND, AgentKind.SON, MakeBondInput, bond_meta, make_bond), *specs]
