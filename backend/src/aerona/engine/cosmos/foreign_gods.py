import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.foreign_gods import FOREIGN_GOD_POWERS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.units import PERCENT
from aerona.core.keyed_random import keyed_random
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodPowerDraft, ForeignGodRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow, GodConflictRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import ExistenceMode, PowerEffect, SonStatus, Stat
from aerona.domain.enums.war import GodConflictOutcome
from aerona.domain.enums.world import Discovery
from aerona.domain.models.profiles import ExistenceProfile
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR, StatBlock
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.hooks import desecrated
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import stat_or
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

SLEEPING_PREFIX = "the sleeping "
AWAKE_PREFIX = "the "
DOMAIN_SEPARATOR = "/"
POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"
F = ForeignGodPowerEffect


def god_seed(name: str, world_id: int, epoch: int) -> str:
    return f"{name}:{world_id}:{epoch}"


def seeded_stats(rules: Rules, seed: str) -> StatBlock:
    roll = keyed_random(seed)
    settings = rules.foreign_gods
    return StatBlock.from_mapping({stat: clamp_int(settings.stat_base + roll() * settings.stat_die, STAT_FLOOR, STAT_CEILING) for stat in Stat})


def stat_effect(rules: Rules, god: ForeignGodRow, stat: Stat, rate: int) -> float:
    return (god.stat(stat) - rules.foreign_gods.stat_neutral) * rate / PERCENT


async def powers_of(session: AsyncSession, god_id: int) -> set[ForeignGodPowerEffect]:
    return set(await session.scalars(select(ForeignGodPowerRow.effect).where(ForeignGodPowerRow.god_id == god_id)))


def war_power(rules: Rules, god: ForeignGodRow, powers: set[ForeignGodPowerEffect]) -> float:
    share = rules.foreign_gods.war_stat_share_pct
    shield = rules.foreign_gods.power_shield if F.SHIELD in powers else 0
    return god.power * (PERCENT - share) / PERCENT + (god.stat(Stat.STRENGTH) + god.stat(Stat.WILL)) / 2 * share / PERCENT + shield


def clean_stats(raw: Mapping[str, Any], previous: StatBlock | None, rules: Rules) -> StatBlock:
    values: dict[Stat, int] = {}
    for stat in Stat:
        candidate = raw.get(stat.value)
        if isinstance(candidate, int | float) and not isinstance(candidate, bool):
            values[stat] = clamp_int(candidate, STAT_FLOOR, STAT_CEILING)
        elif previous is not None:
            values[stat] = previous.get(stat)
        else:
            values[stat] = rules.foreign_gods.stat_neutral
    return StatBlock.from_mapping(values)


def unwrap_text(value: Any) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in "[{":
            try:
                return unwrap_text(json.loads(stripped))
            except ValueError:
                return stripped
        return stripped
    if isinstance(value, list):
        return "\n\n".join(part for part in (unwrap_text(item) for item in value) if part)
    if isinstance(value, dict):
        return "\n\n".join(part for part in (unwrap_text(item) for item in value.values()) if part)
    return "" if value is None else str(value)


def clean_powers(raw: Any) -> list[ForeignGodPowerDraft]:
    items: Sequence[Any] = list(raw.values()) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    cleaned: list[ForeignGodPowerDraft] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            effect = ForeignGodPowerEffect(str(item.get("effect", "")).strip())
        except ValueError:
            continue
        name = unwrap_text(item.get("name")) or FOREIGN_GOD_POWERS[effect].label
        description = unwrap_text(item.get("description")) or FOREIGN_GOD_POWERS[effect].effect_text
        cleaned.append(ForeignGodPowerDraft(name=name, effect=effect, description=description))
    return cleaned


def clean_existence(raw: Mapping[str, Any]) -> ExistenceProfile:
    mode_value = raw.get("mode")
    mode = ExistenceMode(mode_value) if isinstance(mode_value, str) and mode_value in ExistenceMode.__members__.values() else None
    return ExistenceProfile(
        nature=unwrap_text(raw.get("nature")),
        mode=mode,
        manifestation=unwrap_text(raw.get("manifestation")),
        true_name=unwrap_text(raw.get("true_name")),
    )


def parse_domains(text: str, fallback: tuple[Domain, Domain]) -> tuple[Domain, Domain | None]:
    found: list[Domain] = []
    for token in text.split(DOMAIN_SEPARATOR):
        key = token.strip().casefold().replace(" ", "_")
        match = next((domain for domain in Domain if domain.value == key), None)
        if match is not None and match not in found:
            found.append(match)
    if not found:
        return fallback
    return found[0], found[1] if len(found) > 1 else None


@dataclass(frozen=True)
class NewForeignGod:
    name: str
    world_id: int
    domains: tuple[Domain, Domain | None]
    title: str | None = None
    description: str | None = None
    stance: int = 0
    power: int | None = None
    status: ForeignGodStatus = ForeignGodStatus.AWAKE
    image_prompt: str | None = None


async def add_foreign_god(session: AsyncSession, rules: Rules, rng: SeededRandom, epoch: int, spec: NewForeignGod) -> ForeignGodRow:
    name = await NameRepository(session).unique_name(spec.name)
    pantheon = rules.pantheon
    power = spec.power if spec.power is not None else pantheon.foreign_strength_base + rng.die(pantheon.foreign_strength_die)
    god = await ForeignGodRepository(session).create(
        ForeignGodDraft(
            name=name,
            world_id=spec.world_id,
            domain_primary=spec.domains[0],
            domain_secondary=spec.domains[1],
            power=clamp_int(power, 0, PERCENT),
            stats=seeded_stats(rules, god_seed(name, spec.world_id, epoch)),
            created_epoch=epoch,
            title=spec.title,
            stance=clamp_int(spec.stance, RELATION_MIN, RELATION_MAX),
            status=spec.status,
            description=spec.description,
        )
    )
    god.image_prompt = spec.image_prompt
    await session.flush()
    return god


async def worshippers(session: AsyncSession, god_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list((await session.scalars(statement)).unique())


def believers_faith(rules: Rules, believers: Sequence[EntityRow]) -> float:
    pantheon = rules.pantheon
    return sum(
        stat_or(entity, POPULATION_KEY, 0) / pantheon.foreign_population_per_faith + stat_or(entity, FOLLOWERS_KEY, 0) / pantheon.foreign_followers_per_faith
        for entity in believers
    )


async def god_faith(session: AsyncSession, rules: Rules, god_id: int) -> float:
    return believers_faith(rules, await worshippers(session, god_id))


def awaken_text(god: ForeignGodRow) -> None:
    if god.title and god.title.casefold().startswith(SLEEPING_PREFIX):
        god.title = AWAKE_PREFIX + god.title[len(SLEEPING_PREFIX) :]
    if god.description and god.description.casefold().startswith(SLEEPING_PREFIX):
        god.description = AWAKE_PREFIX.capitalize() + god.description[len(SLEEPING_PREFIX) :]


def wake(god: ForeignGodRow) -> None:
    god.status = ForeignGodStatus.AWAKE
    god.awakening_pressure = 0
    awaken_text(god)


async def destroy_temple(ctx: TickContext, god: ForeignGodRow, temple: EntityRow) -> None:
    await retire(ctx.session, temple, ctx.epoch, f"Epoch {ctx.epoch}: destroyed by {god.name}.", status=EntityStatus.DESTROYED)
    await BondRepository(ctx.session).connect(BondDraft(god.id, temple.id, BondKind.DESTROYED, ctx.epoch, "destroyed its temple"))
    keeper = await living_entity(ctx.session, temple.location_id)
    if keeper is not None:
        await desecrated(ctx, keeper.id, god.id, note=temple.name)
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, f"{god.name} destroyed {temple.name}.", template_key="pantheon.temple_destroyed", entity_ids=[temple.id])


async def _world_people(session: AsyncSession, world_id: int) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found: EntityRow | None = await session.scalar(statement.limit(1))
    return found


async def _mourning(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> bool:
    gods = list(await session.scalars(select(ForeignGodRow).where(ForeignGodRow.world_id == world_id)))
    if any(god.status is not ForeignGodStatus.DEAD for god in gods):
        return True
    deaths = [god.death_epoch for god in gods if god.death_epoch is not None]
    return bool(deaths) and epoch - max(deaths) < rules.agents.local_god_rebirth_epochs


async def _native_language(session: AsyncSession, world_id: int) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found: EntityRow | None = await session.scalar(statement.limit(1))
    return found


async def local_god_eligible(session: AsyncSession, rules: Rules, world: WorldRow, epoch: int) -> EntityRow | None:
    if world.discovery is Discovery.FORGOTTEN or epoch - world.created_epoch < rules.agents.local_god_epochs:
        return None
    if await _mourning(session, rules, world.id, epoch):
        return None
    if not await _godless_world(session, rules, world):
        return None
    return await _world_people(session, world.id)


async def _godless_world(session: AsyncSession, rules: Rules, world: WorldRow) -> bool:
    if not rules.agents.local_god_with_sons:
        present = await session.scalar(select(SonRow.id).where(SonRow.status != SonStatus.DEAD, SonRow.current_world_id == world.id).limit(1))
        if world.patron_son_id is not None or present is not None:
            return False
    communities = list(
        await session.scalars(
            select(EntityRow.id).where(EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
        )
    )
    if not communities:
        return True
    nodes = NodeRepository(session)
    worshipping = 0
    for community_id in communities:
        for bond in await BondRepository(session).outgoing(community_id, BondKind.WORSHIPS):
            if await nodes.kind_of(bond.target_node_id) in (NodeKind.SON, NodeKind.CREATOR):
                worshipping += 1
                break
    return worshipping * PERCENT / len(communities) < rules.agents.local_god_worshipped_pct


async def birth_local_god(ctx: TickContext, world: WorldRow, people: EntityRow) -> ForeignGodRow:
    session, rules = ctx.session, ctx.rules
    language = await _native_language(session, world.id)
    derived = await Namer(session, rules).from_language(language, f"local-god:{world.id}:{ctx.epoch}", NameKind.PERSON) if language else None
    domains = WORLD_TYPES[world.world_type].domains
    title = f"{SLEEPING_PREFIX}{domains[0].value.replace('_', ' ')} god of the {people.name} people"
    god = await add_foreign_god(
        session,
        rules,
        ctx.rng("local_god"),
        ctx.epoch,
        NewForeignGod(
            name=derived or f"{world.name} Sleeper",
            world_id=world.id,
            domains=(domains[0], domains[1]),
            title=title,
            description=f"{SLEEPING_PREFIX.capitalize()}god of {world.name}, dreaming beneath the land of the {people.name}.",
            power=rules.agents.local_god_strength,
            status=ForeignGodStatus.ASLEEP,
        ),
    )
    await ctx.chronicle(
        ChronicleKind.FOREIGN_GOD,
        f"Beneath {world.name} a god of its own stirred in its sleep: {god.name}, {title}.",
        template_key="pantheon.local_god_born",
        world_id=world.id,
    )
    ctx.count("local_gods_born")
    return god


async def birth_local_gods(ctx: TickContext) -> list[ForeignGodRow]:
    born: list[ForeignGodRow] = []
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        people = await local_god_eligible(ctx.session, ctx.rules, world, ctx.epoch)
        if people is not None:
            born.append(await birth_local_god(ctx, world, people))
    return born


@dataclass(frozen=True)
class GodWarResult:
    son_score: int
    god_score: int
    outcome: GodConflictOutcome
    god_status: ForeignGodStatus
    son_slept: bool
    text: str


async def _son_has_power(session: AsyncSession, son_id: int, effect: PowerEffect) -> bool:
    statement = select(SonPowerRow.son_id).where(SonPowerRow.son_id == son_id, SonPowerRow.effect == effect)
    return await session.scalar(statement.limit(1)) is not None


async def _son_wins(
    ctx: TickContext, son: SonRow, god: ForeignGodRow, diff: int, reason: str, *, powers: set[ForeignGodPowerEffect]
) -> tuple[ForeignGodStatus, str]:
    tools = ctx.rules.son_tools
    killed = diff >= tools.foreign_war_crushing_margin and F.DEATHLESS not in powers
    god.power = max(0, god.power - tools.foreign_war_strength_loss)
    await apply_hits(ctx, god, Harm(tools.foreign_war_strength_loss + diff, HarmCause.GOD, "was struck down by a son of the creator", source_node_id=son.id))
    god.stance = max(RELATION_MIN, god.stance - tools.foreign_war_attitude_loss)
    if killed:
        god.status = ForeignGodStatus.DEAD
        god.death_epoch = ctx.epoch
    else:
        god.status = ForeignGodStatus.DEFEATED
        god.defeated_epoch = ctx.epoch
    kind = BondKind.KILLED if killed else BondKind.BEAT
    await BondRepository(ctx.session).connect(BondDraft(son.id, god.id, kind, ctx.epoch, reason))
    son.xp += tools.foreign_war_xp
    son.fame += tools.foreign_war_renown
    return god.status, "killed it" if killed else "defeated it"


async def _son_loses(ctx: TickContext, son: SonRow, god: ForeignGodRow, diff: int) -> tuple[bool, str]:
    tools = ctx.rules.son_tools
    wound = tools.foreign_war_min_wound + diff
    loss = min(tools.foreign_war_essence_loss, max(0, son.essence))
    await apply_hits(ctx, son, Harm(wound, HarmCause.GOD, "was struck down by a foreign god", source_node_id=god.id))
    son.essence = max(0, son.essence - loss)
    god.stance = max(RELATION_MIN, god.stance - tools.foreign_war_attitude_loss)
    text = f"lost {wound} HP and {loss} essence."
    if son.hp > 0:
        return False, text
    son.status = SonStatus.ASLEEP
    reviving = await _son_has_power(ctx.session, son.id, PowerEffect.REVIVING)
    son.sleep_epochs_left = tools.reviving_sleep_epochs if reviving else tools.foreign_war_sleep_epochs
    return True, f"{text} {son.name} collapsed and fell into a sleep of {son.sleep_epochs_left} epochs."


async def resolve_god_war(ctx: TickContext, son: SonRow, god: ForeignGodRow, reason: str = "to protect their worshippers and temples") -> GodWarResult:
    tools = ctx.rules.son_tools
    rng = ctx.rng("god_war")
    powers = await powers_of(ctx.session, god.id)
    son_score = round_half_up(
        (son.strength + son.will) / max(1, tools.foreign_war_stat_divisor) + son.level * tools.foreign_war_strength_per_level + rng.die(tools.foreign_war_die)
    )
    god_score = round_half_up(war_power(ctx.rules, god, powers) + rng.die(tools.foreign_war_die))
    diff = abs(son_score - god_score)
    son.essence = max(0, son.essence - tools.foreign_war_cost)
    slept = False
    if son_score >= god_score:
        status, verb = await _son_wins(ctx, son, god, diff, reason, powers=powers)
        outcome = GodConflictOutcome.ATTACKER_WON
        text = f"{son.name} declared war on the foreign god {god.name} ({reason}) and {verb} ({son_score}-{god_score})."
    else:
        slept, tail = await _son_loses(ctx, son, god, diff)
        status = god.status
        outcome = GodConflictOutcome.DEFENDER_WON
        text = f"{son.name} declared war on the foreign god {god.name} ({reason}) but lost ({son_score}-{god_score}); {tail}"
    ctx.session.add(
        GodConflictRow(epoch=ctx.epoch, attacker_node_id=son.id, defender_node_id=god.id, outcome=outcome, attacker_score=son_score, defender_score=god_score)
    )
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="pantheon.god_war", son_id=son.id, world_id=god.world_id)
    await ctx.session.flush()
    return GodWarResult(son_score, god_score, outcome, status, slept, text)
