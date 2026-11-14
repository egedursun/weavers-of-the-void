from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.body import Capacity, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import HERO_ROLES, SOCIETY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.war import HeroQuestKind, HeroQuestStatus
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.book import factor
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import apply_hits, fatal_injury
from aerona.engine.notes import note
from aerona.engine.operations.expeditions import quest_expedition
from aerona.engine.phase import Phase
from aerona.engine.phases.heroism import encounter
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.phases.society_support.quests import QuestOption, QuestWorld, open_threads, quest_options
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int, fraction
from aerona.engine.primitives.queries import BondIndex, canon, flags_by_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.engine.records import death_path
from aerona.engine.services.community_relations import blood_feud_pairs
from aerona.engine.services.sides import SideIndex, held_captives
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.sites.rooms import layout_of, rooms_of
from aerona.rules.registry import Rules

HERO_SUBTYPE = "hero"
APPRENTICE_SUBTYPE = "apprentice"
APPRENTICE_STATS = ("strength", "agility", "intellect", "charisma")
QUEST_BOND_KINDS = (BondKind.KILLED, BondKind.OWNS, BondKind.COMPANION, BondKind.RIVAL, BondKind.APPRENTICE_OF, BondKind.ENEMY)


@dataclass
class HeroCounters:
    started: int = 0
    resolved: int = 0
    companions: int = 0
    apprentices: int = 0


@dataclass(frozen=True)
class HeroWorld:
    quests: QuestWorld
    faith: FaithIndex
    chosen: set[int]
    captives: set[int]
    heroes: list[EntityRow] = field(default_factory=list)


def is_hero(rules: Rules, mortal: EntityRow, chosen: set[int], captives: set[int]) -> bool:
    if mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON or mortal.id in captives:
        return False
    if mortal.mortal_role in HERO_ROLES or mortal.id in chosen:
        return True
    return stat_or(mortal, "strength", 0) + stat_or(mortal, "agility", 0) >= rules.heroes.hero_strength_agility_sum


async def load_hero_world(ctx: TickContext) -> HeroWorld:
    session = ctx.session
    entities = {entity.id: entity for entity in await canon(session)}
    neighbourhood = await Neighbourhood.load(session, ctx.rules)
    quests = QuestWorld(
        entities=entities,
        bonds=await BondIndex.load(session, QUEST_BOND_KINDS),
        atlas=await RegionAtlas.load(session),
        sides=await SideIndex.load(session, neighbourhood),
        lost=await flags_by_entity(session, EntityFlag.LOST),
        feuds=await blood_feud_pairs(session),
        threads=await open_threads(session),
    )
    chosen = await flags_by_entity(session, EntityFlag.CHOSEN)
    captives = await held_captives(session)
    heroes = [entity for entity in entities.values() if is_hero(ctx.rules, entity, chosen, captives)]
    return HeroWorld(quests, await FaithIndex.load(session), chosen, captives, heroes)


async def active_quest(session: AsyncSession, hero_id: int) -> HeroQuestRow | None:
    statement = select(HeroQuestRow).where(HeroQuestRow.hero_entity_id == hero_id, HeroQuestRow.status == HeroQuestStatus.ACTIVE)
    found: HeroQuestRow | None = await session.scalar(statement.order_by(HeroQuestRow.id.desc()).limit(1))
    return found


async def start_quest(ctx: TickContext, hero: EntityRow, option: QuestOption) -> HeroQuestRow:
    bond = await BondRepository(ctx.session).connect(BondDraft(hero.id, option.target_id, BondKind.PURSUES, ctx.epoch, option.description))
    quest = HeroQuestRow(
        hero_entity_id=hero.id,
        kind=option.kind,
        target_node_id=option.target_id,
        thread_id=option.thread_id,
        bond_id=bond.id,
        description=option.description,
        status=HeroQuestStatus.ACTIVE,
        started_epoch=ctx.epoch,
    )
    ctx.session.add(quest)
    await ctx.session.flush()
    await note(ctx, f"{hero.name} set out {option.description}.", key="heroes.quest_start", ids=[hero.id, option.target_id], kind=ChronicleKind.ADVENTURE)
    return quest


async def close_quest(ctx: TickContext, quest: HeroQuestRow, status: HeroQuestStatus) -> None:
    quest.status = status
    quest.ended_epoch = ctx.epoch
    if quest.bond_id is not None:
        bond = await ctx.session.get(BondRow, quest.bond_id)
        if bond is not None and bond.active:
            await BondRepository(ctx.session).deactivate(bond, ctx.epoch, status.value)
    await ctx.session.flush()


def success_chance(rules: Rules, hero: EntityRow, companions: int, chosen: bool, body: float = 1.0) -> float:
    settings = rules.heroes
    base = (stat_or(hero, "strength", 0) + stat_or(hero, "agility", 0) + stat_or(hero, "intellect", 0)) * body / settings.quest_success_divisor
    bonus = companions * fraction(settings.quest_companion_bonus_pct) + (fraction(settings.quest_chosen_bonus_pct) if chosen else 0.0)
    return clamp_float(base + bonus, fraction(settings.quest_success_min_pct), fraction(settings.quest_success_max_pct))


async def companions_of(ctx: TickContext, hero: EntityRow) -> list[EntityRow]:
    found: list[EntityRow] = []
    for bond in await _companion_bonds(ctx, hero.id):
        other = await ctx.session.get(EntityRow, bond.other_end(hero.id))
        if other is not None and other.status is EntityStatus.CANON:
            found.append(other)
    return found


async def _companion_bonds(ctx: TickContext, hero_id: int) -> list[BondRow]:
    bonds = BondRepository(ctx.session)
    return [*await bonds.outgoing(hero_id, BondKind.COMPANION), *await bonds.incoming(hero_id, BondKind.COMPANION)]


async def _reward(ctx: TickContext, hero: EntityRow, faith: FaithIndex) -> None:
    settings = ctx.rules.heroes
    set_stats(hero, charisma=clamp_int(stat_or(hero, "charisma", 0) + settings.quest_charisma_gain, 0, PERCENT))
    patron = faith.living_patron_son(hero.id)
    if patron is not None:
        patron.fame += settings.quest_god_renown


async def _claim_prize(ctx: TickContext, hero: EntityRow, quest: HeroQuestRow, target: EntityRow, world: HeroWorld) -> str:
    if quest.kind is HeroQuestKind.RELIC:
        await BondRepository(ctx.session).connect(BondDraft(hero.id, target.id, BondKind.OWNS, ctx.epoch, "found by quest"))
        return f"{hero.name} found the lost {target.name} and took it up."
    if quest.kind is HeroQuestKind.KNOWLEDGE:
        side_id = world.quests.sides.side_of(hero) or hero.id
        side = await ctx.session.get(EntityRow, side_id) or hero
        await teach(ctx, side.id, target, f"{hero.name} recovered it from the ruins")
        await EntityRepository(ctx.session).remove_flag(target.id, EntityFlag.LOST)
        return f"{hero.name} found the forgotten {target.name} knowledge among the ruins and brought it back to {side.name}."
    if quest.kind is HeroQuestKind.VENGEANCE:
        await death_path(ctx, target, f"killed by {hero.name} avenging the blood feud", hero.id, "blood feud", harm=HarmCause.DUEL)
        return f"{hero.name} took revenge for the blood feud: {target.name} is dead."
    return f"{hero.name} found what they sought on the road taken {quest.description}: a hidden truth about {target.name} is now in their hands."


async def _quest_failed(ctx: TickContext, hero: EntityRow, quest: HeroQuestRow) -> None:
    settings = ctx.rules.heroes
    rng = ctx.rng(f"quest_failure.{quest.id}")
    if rng.chance(settings.quest_death_chance):
        await close_quest(ctx, quest, HeroQuestStatus.DIED)
        await fatal_injury(ctx, hero, Harm(settings.quest_epoch_hp_loss, HarmCause.QUEST, f"died on the road {quest.description}"))
        await death_path(ctx, hero, f"died on the road {quest.description}", manner=DeathCause.HARDSHIP)
        text, key = f"{hero.name} gave their life on the road {quest.description}.", "heroes.quest_death"
    elif ctx.epoch - quest.started_epoch >= settings.quest_abandon_epochs:
        await close_quest(ctx, quest, HeroQuestStatus.ABANDONED)
        text, key = f"{hero.name} searched for years but came back empty-handed from the quest {quest.description}.", "heroes.quest_abandoned"
    else:
        await apply_hits(ctx, hero, Harm(settings.quest_epoch_hp_loss, HarmCause.QUEST, f"died on the road {quest.description}"), lethal=False)
        return
    await note(ctx, text, key=key, ids=[hero.id], kind=ChronicleKind.ADVENTURE)


async def resolve_quest_now(ctx: TickContext, hero: EntityRow, quest: HeroQuestRow, world: HeroWorld, forced: bool | None = None) -> HeroQuestStatus:
    target = await ctx.session.get(EntityRow, quest.target_node_id) if quest.target_node_id is not None else None
    if target is not None and target.entity_type is EntityType.SPECIES:
        await close_quest(ctx, quest, HeroQuestStatus.SUCCEEDED if target.status is EntityStatus.CANON else HeroQuestStatus.ABANDONED)
        if target.status is EntityStatus.CANON:
            await encounter(ctx, hero, target, "at the end of a long hunt")
        return quest.status
    if target is None or target.status is not EntityStatus.CANON:
        await close_quest(ctx, quest, HeroQuestStatus.ABANDONED)
        return quest.status
    companions = await companions_of(ctx, hero)
    chance = success_chance(ctx.rules, hero, len(companions), hero.id in world.chosen, await factor(ctx.session, hero.id, Capacity.MOBILITY))
    if await layout_of(ctx, target) is not None or await rooms_of(ctx, target.id):
        walk = await quest_expedition(ctx, hero, target, companions)
        succeeded = forced if forced is not None else walk.reached_heart
    else:
        succeeded = forced if forced is not None else ctx.rng(f"quest.{quest.id}").probability(chance)
    if not succeeded:
        await _quest_failed(ctx, hero, quest)
        return quest.status
    await close_quest(ctx, quest, HeroQuestStatus.SUCCEEDED)
    await _reward(ctx, hero, world.faith)
    text = await _claim_prize(ctx, hero, quest, target, world)
    if companions:
        text = f"{text} {', '.join(companion.name for companion in companions)} were at their side."
    await note(ctx, text, key=f"heroes.quest_{quest.kind.value}", ids=[hero.id, target.id, *[item.id for item in companions]], kind=ChronicleKind.ADVENTURE)
    return quest.status


def choose_quest(ctx: TickContext, options: Sequence[QuestOption], stream: str) -> QuestOption | None:
    if not options:
        return None
    return ctx.rng(stream).weighted(list(options), [option.weight for option in options])


async def _quest_round(ctx: TickContext, world: HeroWorld, counters: HeroCounters) -> None:
    settings = ctx.rules.heroes
    rng = ctx.rng("quests")
    for hero in world.heroes:
        if hero.status is not EntityStatus.CANON or held(hero.id):
            continue
        quest = await active_quest(ctx.session, hero.id)
        if quest is not None and quest.started_epoch < ctx.epoch and counters.resolved < settings.quest_resolution_cap:
            counters.resolved += 1
            await resolve_quest_now(ctx, hero, quest, world)
            continue
        if quest is not None or counters.started >= settings.quest_new_cap or not rng.chance(settings.quest_chance):
            continue
        option = choose_quest(ctx, quest_options(ctx.rules, world.quests, hero), f"quest_choice.{hero.id}")
        if option is not None:
            counters.started += 1
            await start_quest(ctx, hero, option)


async def _companion_round(ctx: TickContext, world: HeroWorld, counters: HeroCounters) -> None:
    settings = ctx.rules.heroes
    living = [hero for hero in world.heroes if hero.status is EntityStatus.CANON and not held(hero.id)]
    bonds = world.quests.bonds
    rng = ctx.rng("companions")
    for index, first in enumerate(living):
        for second in living[index + 1 :]:
            if counters.companions >= settings.companion_new_cap:
                return
            if bonds.between(first.id, second.id, BondKind.COMPANION) or bonds.between(first.id, second.id, BondKind.RIVAL):
                continue
            side = world.quests.sides.side_of(first)
            if side is None or side != world.quests.sides.side_of(second) or not rng.chance(settings.companion_chance):
                continue
            bonds.add(await BondRepository(ctx.session).connect(BondDraft(first.id, second.id, BondKind.COMPANION, ctx.epoch, "fellowship of the road")))
            counters.companions += 1
            await note(
                ctx,
                f"{first.name} and {second.name} became companions of the road.",
                key="heroes.companions",
                ids=[first.id, second.id],
                kind=ChronicleKind.ADVENTURE,
            )


def apprentice_stats(ctx: TickContext, master: EntityRow) -> MortalStats:
    settings = ctx.rules.heroes
    rng = ctx.rng(f"apprentice.{master.id}")
    values = {
        key: clamp_int(
            stat_or(master, key, settings.apprentice_stat_fallback) * fraction(settings.apprentice_stat_share_pct) + rng.die(settings.apprentice_stat_die),
            0,
            PERCENT,
        )
        for key in APPRENTICE_STATS
    }
    life = stat_or(master, "lifespan", settings.master_default_lifespan)
    lifespan = clamp_int(
        life + rng.die(settings.apprentice_lifespan_die) - settings.apprentice_lifespan_shift,
        settings.apprentice_min_lifespan,
        ctx.rules.deep_life.lifespan_cap,
    )
    return MortalStats(hp=settings.apprentice_hp, age=settings.apprentice_start_age, lifespan=lifespan, **values)


async def _bequeath_weapon(ctx: TickContext, master: EntityRow, apprentice: EntityRow) -> EntityRow | None:
    bonds = BondRepository(ctx.session)
    owned: list[tuple[BondRow, EntityRow]] = []
    for bond in await bonds.outgoing(master.id, BondKind.OWNS):
        item = await ctx.session.get(EntityRow, bond.target_node_id)
        if item is not None and item.entity_type is EntityType.ITEM and item.status is EntityStatus.CANON:
            owned.append((bond, item))
    if not owned or not ctx.rng(f"bequest.{master.id}").chance(ctx.rules.heroes.weapon_bequest_chance):
        return None
    bond, weapon = max(owned, key=lambda pair: (stat_or(pair[1], "damage", 0), -pair[1].id))
    await bonds.deactivate(bond, ctx.epoch, "entrusted")
    await bonds.connect(BondDraft(apprentice.id, weapon.id, BondKind.OWNS, ctx.epoch, f"entrusted by {master.name}"))
    return weapon


async def train_apprentice(ctx: TickContext, master: EntityRow, world: HeroWorld) -> EntityRow:
    settings = ctx.rules.heroes
    name = await Namer(ctx.session, ctx.rules).person([master], seed_of(master.id, ctx.epoch, APPRENTICE_SUBTYPE), master.world_id)
    apprentice = await create_record(
        ctx,
        RecordSpec(
            name=name or f"{master.name}'s Apprentice",
            entity_type=EntityType.MORTAL,
            stats=apprentice_stats(ctx, master),
            body=f"The ageing {master.name} began passing on what they know to an apprentice.",
            power=max(1, master.power_level - settings.apprentice_power_gap),
            world_id=master.world_id,
            location_id=master.location_id,
            subtype=APPRENTICE_SUBTYPE,
            engine_kind=EngineKind.APPRENTICE,
            mortal_role=MortalRole.APPRENTICE,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(apprentice.id, master.id, BondKind.APPRENTICE_OF, ctx.epoch, "apprenticeship"))
    side = world.quests.sides.side_of(master)
    if side is not None:
        await bonds.connect(BondDraft(apprentice.id, side, BondKind.PROTECTS, ctx.epoch, "sworn with the master"))
    patron = world.faith.patron(master.id)
    if patron is not None and world.faith.is_living_god(patron):
        await bonds.connect(BondDraft(apprentice.id, patron, BondKind.WORSHIPS, ctx.epoch, "the master's faith"))
    language = await spoken_language(ctx.session, master.id)
    if language is not None:
        await bonds.connect(BondDraft(apprentice.id, language.id, BondKind.SPEAKS, ctx.epoch, "the master's tongue"))
    weapon = await _bequeath_weapon(ctx, master, apprentice)
    entrusted = f" and entrusted {weapon.name} to them" if weapon is not None else ""
    await note(
        ctx,
        f"{master.name} began training an apprentice{entrusted}.",
        key="heroes.apprentice",
        ids=[master.id, apprentice.id, *([weapon.id] if weapon else [])],
        kind=ChronicleKind.LINEAGE,
    )
    return apprentice


def ready_to_teach(rules: Rules, master: EntityRow) -> bool:
    settings = rules.heroes
    life = stat_or(master, "lifespan", settings.master_default_lifespan)
    return stat_or(master, "age", 0) >= life * fraction(settings.apprentice_min_life_pct) and stat_or(master, "charisma", 0) >= settings.apprentice_min_charisma


async def _apprentice_round(ctx: TickContext, world: HeroWorld, counters: HeroCounters) -> None:
    settings = ctx.rules.heroes
    rng = ctx.rng("apprentices")
    for hero in world.heroes:
        if counters.apprentices >= settings.apprentice_new_cap:
            return
        if hero.status is not EntityStatus.CANON or held(hero.id) or not ready_to_teach(ctx.rules, hero):
            continue
        if world.quests.bonds.incoming(hero.id, BondKind.APPRENTICE_OF) or not rng.chance(settings.apprentice_chance):
            continue
        await train_apprentice(ctx, hero, world)
        counters.apprentices += 1


@reads(
    "item.damage",
    "item.protection",
    "knowledge.spread",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "species.agility",
    "species.danger",
    "species.strength",
    "table.afterlife_strata",
    "table.assistive_aids",
    "table.avatars",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.captives",
    "table.community_relations",
    "table.community_societies",
    "table.conditions",
    "table.cosmos",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_values",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.entity_flags",
    "table.entity_tags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.expedition_members",
    "table.feuds",
    "table.geasa",
    "table.genomes",
    "table.griefs",
    "table.hero_quests",
    "table.holder_levels",
    "table.house_members",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.passions",
    "table.personality_values",
    "table.place_profiles",
    "table.prostheses",
    "table.quirks",
    "table.region_environment",
    "table.reverences",
    "table.room_contents",
    "table.routes",
    "table.site_rooms",
    "table.skills",
    "table.species_profiles",
    "table.thoughts",
    "table.thread_links",
    "table.threads",
    "table.tradition_profiles",
    "table.traits",
    "table.world_domain_hooks",
    "table.world_maps",
)
@writes(
    "knowledge.spread",
    "mortal.charisma",
    "mortal.death_year",
    "mortal.hp",
    "species.danger",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.expedition_logs",
    "table.expedition_members",
    "table.expeditions",
    "table.griefs",
    "table.hero_quests",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.language_profiles",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.personality_values",
    "table.quirks",
    "table.room_contents",
    "table.site_rooms",
    "table.sons",
    "table.thoughts",
)
async def heroes(ctx: TickContext) -> None:
    world = await load_hero_world(ctx)
    counters = HeroCounters()
    await _quest_round(ctx, world, counters)
    await _companion_round(ctx, world, counters)
    await _apprentice_round(ctx, world, counters)
    ctx.count("quests_started", counters.started)
    ctx.count("quests_resolved", counters.resolved)
    ctx.count("companions", counters.companions)
    ctx.count("apprentices", counters.apprentices)


def hero_stats(ctx: TickContext, community: EntityRow) -> MortalStats:
    settings = ctx.rules.heroes
    rng = ctx.rng(f"hero_birth.{community.id}")
    return MortalStats(
        hp=settings.birth_hp,
        strength=clamp_int(settings.birth_strength_base + rng.die(settings.birth_strength_die), 0, PERCENT),
        agility=clamp_int(settings.birth_agility_base + rng.die(settings.birth_agility_die), 0, PERCENT),
        intellect=clamp_int(settings.birth_intellect_base + rng.die(settings.birth_intellect_die), 0, PERCENT),
        charisma=clamp_int(settings.birth_charisma_base + rng.die(settings.birth_charisma_die), 0, PERCENT),
        age=settings.birth_age_base + rng.die(settings.birth_age_die),
        lifespan=settings.birth_lifespan_base + rng.die(settings.birth_lifespan_die),
    )


async def bear_hero(ctx: TickContext, community: EntityRow) -> EntityRow:
    name = await Namer(ctx.session, ctx.rules).person([community], seed_of(community.id, ctx.epoch, HERO_SUBTYPE), community.world_id)
    hero = await create_record(
        ctx,
        RecordSpec(
            name=name or f"{community.name} Hero",
            entity_type=EntityType.MORTAL,
            stats=hero_stats(ctx, community),
            body=f"From among {community.name}, a hero arose in answer to the troubles of the age.",
            power=ctx.rules.heroes.birth_power,
            world_id=community.world_id,
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            subtype=HERO_SUBTYPE,
            mortal_role=MortalRole.HERO,
            title=f"Hero of {community.name}",
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(hero.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, "born of the people"))
    faith = await FaithIndex.load(ctx.session)
    patron = faith.patron(community.id)
    if patron is not None and faith.is_living_god(patron):
        await bonds.connect(BondDraft(hero.id, patron, BondKind.WORSHIPS, ctx.epoch, "the faith of their people"))
    language = await spoken_language(ctx.session, community.id)
    if language is not None:
        await bonds.connect(BondDraft(hero.id, language.id, BondKind.SPEAKS, ctx.epoch, "mother tongue"))
    await note(
        ctx, f"A new hero was born among {community.name}.", key="heroes.birth", ids=[community.id, hero.id], feed=FeedCategory.LIFE, kind=ChronicleKind.BIRTH
    )
    return hero


@reads(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.epoch_year_cursors",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.reverences",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
async def hero_births(ctx: TickContext) -> None:
    settings = ctx.rules.heroes
    communities = await canon(ctx.session, SOCIETY_TYPES)
    threshold = relative_threshold(
        communities, "population", fraction(settings.birth_top_percentile), settings.birth_min_population, settings.birth_always_population
    )
    hostility = (await BondIndex.load(ctx.session, [BondKind.ENEMY])).bonds
    at_war = {bond.source_node_id for bond in hostility} | {bond.target_node_id for bond in hostility}
    rng = ctx.rng("hero_births")
    born = 0
    for community in unheld(communities):
        if born >= settings.birth_cap:
            break
        if stat_or(community, "population", 0) < threshold(community):
            continue
        chance = settings.birth_chance + (settings.birth_war_bonus_pct if community.id in at_war else 0)
        if rng.chance(chance):
            await bear_hero(ctx, community)
            born += 1
    ctx.count("heroes_born", born)


async def require_mortal(session: AsyncSession, hero_id: int) -> EntityRow:
    hero = await session.get(EntityRow, hero_id)
    if hero is None or hero.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such mortal.")
    if hero.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{hero.name} is no longer among the living.")
    return hero


async def raise_hero(ctx: TickContext, community_id: int) -> EntityRow:
    community = await ctx.session.get(EntityRow, community_id)
    if community is None or community.entity_type not in SOCIETY_TYPES:
        raise NotFoundError("Heroes rise from peoples and settlements.")
    if community.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{community.name} is no longer part of the world.")
    return await bear_hero(ctx, community)


async def send_on_quest(ctx: TickContext, hero_id: int, kind: HeroQuestKind | None = None, target_id: int | None = None) -> HeroQuestRow:
    hero = await require_mortal(ctx.session, hero_id)
    if await active_quest(ctx.session, hero.id) is not None:
        raise ValidationFailedError(f"{hero.name} is already on a quest.")
    world = await load_hero_world(ctx)
    options = [
        option
        for option in quest_options(ctx.rules, world.quests, hero)
        if (kind is None or option.kind is kind) and (target_id is None or option.target_id == target_id)
    ]
    option = choose_quest(ctx, options, f"manual_quest.{hero.id}")
    if option is None:
        raise ValidationFailedError(f"There is no fitting quest for {hero.name}.")
    return await start_quest(ctx, hero, option)


async def resolve_quest(ctx: TickContext, hero_id: int, succeed: bool | None = None) -> HeroQuestStatus:
    hero = await require_mortal(ctx.session, hero_id)
    quest = await active_quest(ctx.session, hero.id)
    if quest is None:
        raise ValidationFailedError(f"{hero.name} is not on a quest.")
    return await resolve_quest_now(ctx, hero, quest, await load_hero_world(ctx), succeed)


async def recall_hero(ctx: TickContext, hero_id: int) -> HeroQuestRow:
    hero = await require_mortal(ctx.session, hero_id)
    quest = await active_quest(ctx.session, hero.id)
    if quest is None:
        raise ValidationFailedError(f"{hero.name} is not on a quest.")
    await close_quest(ctx, quest, HeroQuestStatus.ABANDONED)
    await note(ctx, f"{hero.name} was called back from the quest {quest.description}.", key="heroes.recalled", ids=[hero.id], kind=ChronicleKind.ADVENTURE)
    return quest


async def assign_apprentice(ctx: TickContext, master_id: int) -> EntityRow:
    master = await require_mortal(ctx.session, master_id)
    if await BondRepository(ctx.session).incoming(master.id, BondKind.APPRENTICE_OF):
        raise ValidationFailedError(f"{master.name} already has an apprentice.")
    return await train_apprentice(ctx, master, await load_hero_world(ctx))


PHASES = (
    Phase("hero_births", hero_births),
    Phase("heroes", heroes),
)
