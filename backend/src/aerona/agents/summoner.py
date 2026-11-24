from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.chronicle import ChroniclePhase, record_line
from aerona.agents.context.briefs import son_brief
from aerona.agents.context.recent_chronicle import recent_chronicle
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.thread_lines import thread_lines
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_line import world_line
from aerona.agents.fate.name_check import god_lookalike
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import replace_name, sanitize
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import RARITY_LABELS, build_rarity_table
from aerona.catalog.stats import max_essence, max_hp
from aerona.constants.agents import INSPIRATION_SUMMARY_CHARS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import PowerDraft, SonDraft, SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import MIN_STARS
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.rarity import RARITY_ORDER, Rarity
from aerona.domain.enums.son import PowerEffect, SonStatus, Stat
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import revised
from aerona.domain.models.profiles import ExistenceProfile, Personality
from aerona.domain.models.son_design import SonDesign
from aerona.domain.models.stats import PassionBlock
from aerona.engine.divine.lineage import inherited_domains, inherited_stats
from aerona.engine.dominion.design import Design, budget_of, fate_check, scaled_stats, write_design
from aerona.engine.gods.deification import roll_stats
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.genesis import SonPowersContext, SummonSonContext
from aerona.prompts.schemas.genesis import SonPowersOutput
from aerona.prompts.schemas.shared import ExistenceOutput, PowerOutput, SonProfileOutput
from aerona.rules.registry import Rules

PERCENT = 100
DUEL_STATS = (Stat.STRENGTH, Stat.WISDOM, Stat.CUNNING, Stat.CHARISMA, Stat.WILL)
DEFAULT_ENTITY_TYPE = EntityType.PLACE
DEFAULT_DUEL_STAT = Stat.STRENGTH
POWER_COUNT = 3
UNWORSHIPPED_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION)
LIVING_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.SPECIES)
SUMMON_STREAM = "agents.summon"
DOMAIN_ORDER = list(Domain)

GOD_NAME_SEED = "god-name"


@dataclass(frozen=True)
class Parentage:
    parent_id: int | None = None
    co_parent_id: int | None = None
    inspiration: str | None = None


NO_PARENT = Parentage()


def summon_rng(scope: Scope, salt: str) -> SeededRandom:
    return SeededRandom.for_epoch(scope.cosmos.rng_seed, scope.epoch, f"{SUMMON_STREAM}.{salt}")


def roll_rarity(rules: Rules, rng: SeededRandom) -> Rarity:
    table = build_rarity_table(rules)
    options = [profile for profile in table.values() if profile.summonable]
    return rng.weighted([profile.rarity for profile in options], [profile.summon_weight for profile in options])


def child_rarity(rules: Rules, rng: SeededRandom, parent: Rarity) -> Rarity:
    table = build_rarity_table(rules)
    allowed = [rarity for rarity in RARITY_ORDER if rarity.rank < parent.rank and table[rarity].summon_weight > 0]
    if not allowed:
        return parent
    for _ in range(rules.summoning.child_rarity_rolls):
        rolled = roll_rarity(rules, rng)
        if rolled in allowed:
            return rolled
    return allowed[-1]


def clamp_passion(value: int | None, default: int) -> int:
    return max(0, min(PERCENT, default if value is None else value))


async def power_usage(session: AsyncSession) -> Counter[PowerEffect]:
    return Counter(await session.scalars(select(SonPowerRow.effect)))


async def clean_powers(session: AsyncSession, rules: Rules, rng: SeededRandom, powers: Sequence[PowerOutput]) -> list[PowerDraft]:
    usage = await power_usage(session)
    fallback = sorted(PowerEffect, key=lambda effect: (usage[effect], rng.random()))
    chosen: list[PowerDraft] = []
    used: set[PowerEffect] = set()
    for power in powers[:POWER_COUNT]:
        effect = power.effect
        if effect in used or usage[effect] >= rules.summoning.power_effect_cap:
            effect = next(item for item in fallback if item not in used)
        used.add(effect)
        entity_type = stat = None
        if effect is PowerEffect.CHEAP_CREATION:
            entity_type = EntityType(power.param) if power.param in EntityType.__members__.values() else DEFAULT_ENTITY_TYPE
        elif effect is PowerEffect.DUEL_MASTER:
            stat = Stat(power.param) if power.param in {item.value for item in DUEL_STATS} else DEFAULT_DUEL_STAT
        chosen.append(
            PowerDraft(
                name=power.name.strip() or effect.value, description=sanitize(power.description), effect=effect, param_entity_type=entity_type, param_stat=stat
            )
        )
    return chosen


def existence_of(output: ExistenceOutput) -> ExistenceProfile:
    return ExistenceProfile(nature=output.nature, mode=output.state, manifestation=output.manifestation)


async def son_world(session: AsyncSession, rules: Rules, parent_id: int | None, requested: int | None) -> int | None:
    if requested is not None:
        world = await session.get(WorldRow, requested)
        if world is not None and world.discovery is not Discovery.FORGOTTEN:
            return world.id
    parent = await session.get(SonRow, parent_id) if parent_id is not None else None
    if parent is not None and parent.current_world_id is not None:
        return parent.current_world_id
    summoning = rules.summoning
    best: tuple[float, int] | None = None
    worshipped = select(BondRow.source_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    for world in await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        base = select(func.count()).select_from(EntityRow).where(EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON)
        unworshipped = int(await session.scalar(base.where(EntityRow.entity_type.in_(UNWORSHIPPED_TYPES), EntityRow.id.not_in(worshipped))) or 0)
        living = int(await session.scalar(base.where(EntityRow.entity_type.in_(LIVING_TYPES))) or 0)
        sons = int(
            await session.scalar(select(func.count()).select_from(SonRow).where(SonRow.current_world_id == world.id, SonRow.status != SonStatus.DEAD)) or 0
        )
        score = (
            unworshipped * summoning.world_unclaimed_weight_pct + living * summoning.world_living_weight_pct - sons * summoning.world_son_penalty_pct
        ) / PERCENT
        if best is None or score > best[0]:
            best = (score, world.id)
    return best[1] if best is not None else None


async def insert_son(
    session: AsyncSession, rules: Rules, rng: SeededRandom, profile: SonProfileOutput, *, rarity: Rarity, epoch: int, parentage: Parentage, world_id: int | None
) -> SonRow:
    stats = roll_stats(rules, rng, rarity, list(profile.strengths), [profile.weakness])
    default = rules.summoning.default_passion
    passions = PassionBlock(
        loyalty=clamp_passion(profile.passions.loyalty, default),
        ambition=clamp_passion(profile.passions.ambition, default),
        wrath=clamp_passion(profile.passions.wrath, default),
        mercy=clamp_passion(profile.passions.mercy, default),
    )
    second = profile.domain_2
    if second is profile.domain_1:
        second = DOMAIN_ORDER[(DOMAIN_ORDER.index(profile.domain_1) + rules.summoning.domain_shift) % len(DOMAIN_ORDER)]
    parents = [
        son for son in [await session.get(SonRow, node) for node in (parentage.parent_id, parentage.co_parent_id) if node is not None] if son is not None
    ]
    stats = inherited_stats(rules, rng, stats, parents)
    checked = fate_check(rules, budget_of(rules, rarity, MIN_STARS), design_of(profile))
    stats = revised(stats, scaled_stats(stats.model_dump(), checked.stats_pct))
    first, second = inherited_domains(rng, (profile.domain_1, second), parents)
    home = world_id if world_id is not None else await son_world(session, rules, parentage.parent_id, None)
    name = await NameRepository(session).unique_name(await distinct_god_name(session, rules, profile.name, home))
    if name != profile.name:
        profile = renamed_profile(profile, profile.name, name)
    draft = SonDraft(
        name=name,
        title=sanitize(profile.title),
        rarity=rarity,
        domains=(first, second),
        stats=stats,
        passions=passions,
        personality=Personality(
            appearance=profile.appearance,
            temperament=profile.temperament,
            obsession=profile.obsession,
            fear=profile.fear,
            speech_style=profile.speech_style,
            secret=profile.secret,
        ),
        existence=rules.summoning.start_existence,
        hp=max_hp(rules, stats.endurance),
        essence=max_essence(rules, stats.might),
        birth_epoch=epoch,
        powers=await clean_powers(session, rules, rng, profile.powers),
        existence_profile=existence_of(profile.existence),
        parent_son_id=parentage.parent_id,
        co_parent_son_id=parentage.co_parent_id,
        current_world_id=home,
        image_prompt=profile.image_prompt.strip() or None,
    )
    son = await SonRepository(session).create(draft)
    await write_design(session, son.id, checked, epoch)
    return son


def design_of(profile: SonProfileOutput) -> Design:
    scales: dict[DivineScale, int] = {}
    for item in profile.design.scales:
        scales.setdefault(item.scale, item.value)
    return Design(
        dominion_strength=profile.design.dominion_strength,
        magic_aptitude=profile.design.magic_aptitude,
        manifestation_strength=profile.design.manifestation_strength,
        scales=scales,
        powers=len(profile.powers),
    )


async def distinct_god_name(session: AsyncSession, rules: Rules, name: str, world_id: int | None) -> str:
    if await god_lookalike(session, rules, name) is None:
        return name
    namer = Namer(session, rules)
    for attempt in range(rules.naming.fresh_name_attempts):
        candidate = await namer.person([], seed_of(GOD_NAME_SEED, name, attempt), world_id)
        if candidate and await god_lookalike(session, rules, candidate) is None:
            return candidate
    return name


def renamed_profile(profile: SonProfileOutput, old: str, new: str) -> SonProfileOutput:
    fields = ("title", "appearance", "temperament", "obsession", "fear", "speech_style", "secret")
    return profile.model_copy(update={"name": new, **{key: replace_name(getattr(profile, key), old, new) for key in fields}})


async def after_birth(session: AsyncSession, rules: Rules, son: SonRow, parentage: Parentage, *, epoch: int, creator_name: str) -> None:
    repository = SonRepository(session)
    summoning = rules.summoning
    for other in await session.scalars(select(SonRow).where(SonRow.id != son.id)):
        shared = len(set(other.domains) & set(son.domains))
        if shared:
            await repository.change_relation(son.id, other.id, -summoning.shared_domain_relation_loss * shared)
        elif other.id == parentage.parent_id:
            await repository.change_relation(son.id, other.id, summoning.parent_relation)
    bonds = BondRepository(session)
    label = f"{son.name}, {son.title} ({RARITY_LABELS[son.rarity]}; {DOMAIN_LABELS[son.domain_primary]}/{DOMAIN_LABELS[son.domain_secondary]})"
    parent = await session.get(SonRow, parentage.parent_id) if parentage.parent_id is not None else None
    if parent is None:
        await record_line(
            session,
            rules,
            "son.summoned",
            roles={IncidentRole.PRODUCT: son.id},
            facts={"creator_name": creator_name, "label": label},
            phase=ChroniclePhase.GODS,
            kind=ChronicleKind.BIRTH,
            son_id=son.id,
        )
        return
    note = (parentage.inspiration or "")[:INSPIRATION_SUMMARY_CHARS] or None
    await bonds.connect(BondDraft(son.id, parent.id, BondKind.DESCENDS_FROM, epoch, note))
    co_parent = await session.get(SonRow, parentage.co_parent_id) if parentage.co_parent_id is not None else None
    if co_parent is not None:
        await bonds.connect(BondDraft(son.id, co_parent.id, BondKind.DESCENDS_FROM, epoch, note))
        await repository.change_relation(son.id, co_parent.id, summoning.other_parent_relation)
    await record_line(
        session,
        rules,
        "son.born",
        roles={IncidentRole.PARENT: [parent.id, *([co_parent.id] if co_parent is not None else [])], IncidentRole.CHILD: son.id},
        facts={"label": label},
        phase=ChroniclePhase.GODS,
        kind=ChronicleKind.BIRTH,
        son_id=parent.id,
    )


def designed(parentage: Parentage, design: SonDesign | None) -> Parentage:
    if design is None:
        return parentage
    lines = design.given()
    wish = (design.inspiration or "").strip()
    text = "; ".join([*([wish] if wish else []), *lines])
    return replace(parentage, inspiration=text or parentage.inspiration)


def applied(output: SonProfileOutput, design: SonDesign | None) -> SonProfileOutput:
    if design is None:
        return output
    texts = {
        key: value.strip()
        for key, value in {
            "name": design.name,
            "title": design.title,
            "appearance": design.appearance,
            "temperament": design.temperament,
            "obsession": design.obsession,
            "fear": design.fear,
            "speech_style": design.speech_style,
            "secret": design.secret,
        }.items()
        if value and value.strip()
    }
    domains = {key: value for key, value in {"domain_1": design.domain_1, "domain_2": design.domain_2}.items() if value is not None}
    passions = output.passions.model_copy(
        update={
            key: value
            for key, value in {"loyalty": design.loyalty, "ambition": design.ambition, "wrath": design.wrath, "mercy": design.mercy}.items()
            if value is not None
        }
    )
    return output.model_copy(update={**texts, **domains, "passions": passions})


async def summon_context(scope: Scope, rarity: Rarity, world_id: int | None, parentage: Parentage) -> SummonSonContext:
    sons = list(await scope.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))
    parent = await scope.session.get(SonRow, parentage.parent_id) if parentage.parent_id is not None else None
    co_parent = await scope.session.get(SonRow, parentage.co_parent_id) if parentage.co_parent_id is not None else None
    return SummonSonContext(
        lore_language=scope.cosmos.lore_language,
        world_name=scope.cosmos.name,
        world_header=await world_header(scope, world_id if scope.multi_world else None),
        target_world_line=await world_line(scope, world_id) or None if scope.multi_world else None,
        god_name=scope.creator.name,
        pantheon=[son_brief(son) for son in sons],
        threads=await thread_lines(scope),
        recent_events=await recent_chronicle(scope, scope.rules.summoning.recent_events),
        parent=son_brief(parent) if parent is not None else None,
        co_parent=son_brief(co_parent) if co_parent is not None else None,
        inspiration=parentage.inspiration,
        rarity=rarity,
        rarity_label=RARITY_LABELS[rarity],
    )


async def create_son(
    runtime: AgentRuntime, *, rarity: Rarity | None = None, world_id: int | None = None, parentage: Parentage = NO_PARENT, design: SonDesign | None = None
) -> SonRow:
    runtime.require_llm("son summoning")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        rng = summon_rng(scope, str(parentage.parent_id or 0))
        parent = await session.get(SonRow, parentage.parent_id) if parentage.parent_id is not None else None
        chosen = (
            rarity
            or (design.rarity if design is not None else None)
            or (child_rarity(rules, rng, parent.rarity) if parent is not None else roll_rarity(rules, rng))
        )
        target = await son_world(session, rules, parentage.parent_id, world_id)
        context = await summon_context(scope, chosen, target, designed(parentage, design))
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.SUMMONING,
        system=(PromptId.SUMMON_SON_SYSTEM, context),
        user=(PromptId.SUMMON_SON_USER, context),
        output=SonProfileOutput,
    )
    output = applied(output, design)
    async with runtime.database.write() as session:
        scope = await load_scope(session, rules)
        son = await insert_son(session, rules, summon_rng(scope, output.name), output, rarity=chosen, epoch=scope.epoch, parentage=parentage, world_id=target)
        await after_birth(session, rules, son, parentage, epoch=scope.epoch, creator_name=scope.creator.name)
        son_id, name = son.id, son.name
    runtime.publish(EventKind.NEW_SON, {"son_id": son_id, "name": name, "rarity": chosen.value})
    async with runtime.database.read() as session:
        created = await session.get(SonRow, son_id)
    if created is None:
        raise NotFoundError("The new son vanished.")
    return created


async def summon_son(runtime: AgentRuntime, world_id: int | None = None, rarity: Rarity | None = None, design: SonDesign | None = None) -> SonRow:
    return await create_son(runtime, rarity=rarity, world_id=world_id, design=design)


async def birth_child(runtime: AgentRuntime, parent_id: int, inspiration: str | None = None, co_parent_id: int | None = None) -> SonRow:
    async with runtime.database.read() as session:
        parent = await session.get(SonRow, parent_id)
        if parent is None or parent.status is SonStatus.DEAD:
            raise ValidationFailedError("Only a living son can give birth.")
    return await create_son(runtime, parentage=Parentage(parent_id, co_parent_id, inspiration))


async def complete_son_powers(runtime: AgentRuntime, son_id: int) -> SonRow:
    runtime.require_llm("son powers")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError("No such son.")
        context = SonPowersContext(
            lore_language=scope.cosmos.lore_language,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            name=son.name,
            title=son.title,
            rarity_label=RARITY_LABELS[son.rarity],
            domain_1=DOMAIN_LABELS[son.domain_primary],
            domain_2=DOMAIN_LABELS[son.domain_secondary],
            appearance=son.personality.appearance,
            temperament=son.personality.temperament,
            obsession=son.personality.obsession,
            secret=son.personality.secret,
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.SON_POWERS,
        system=(PromptId.SON_POWERS_SYSTEM, context),
        user=(PromptId.SON_POWERS_USER, context),
        output=SonPowersOutput,
    )
    async with runtime.database.write() as session:
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError("No such son.")
        scope = await load_scope(session, rules)
        existing = list(await session.scalars(select(SonPowerRow.slot).where(SonPowerRow.son_id == son.id)))
        if not existing:
            await SonRepository(session).set_powers(son.id, await clean_powers(session, rules, summon_rng(scope, son.name), output.powers))
        if son.existence_profile is None:
            son.existence_profile = existence_of(output.existence)
        son.image_prompt = son.image_prompt or output.image_prompt.strip() or None
    return son
