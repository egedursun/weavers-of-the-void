from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.powers import POWERS
from aerona.catalog.rarities import build_rarity_table, entity_rarity
from aerona.catalog.stats import max_essence, max_hp
from aerona.core.errors import ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import PowerDraft, SonDraft, SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import PowerEffect, Stat
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR, PassionBlock, StatBlock
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.transform.record import blocked, record_transformation
from aerona.rules.registry import Rules

DEIFY_RARITY_CAP = Rarity.LEGENDARY
MORTAL_TO_SON_STATS: tuple[tuple[str, Stat], ...] = (
    ("strength", Stat.STRENGTH),
    ("intellect", Stat.WISDOM),
    ("charisma", Stat.CHARISMA),
    ("agility", Stat.CUNNING),
)
TITLE = "Raised {subtype}"
DEFAULT_SUBTYPE = "Mortal"
TEMPERAMENT = "When mortal they were {subtype}; the only god who knows what death is."
OBSESSION = "The mortals left behind"
FEAR = "Becoming mortal again"
DEATH_CAUSE = "was taken up into the sky by {creator}; now a god among the sons"
MORTAL_PAST = "mortal past"
OLD_FAITH = "they believed in them when mortal too"


@dataclass(frozen=True)
class Deification:
    son: SonRow
    mortal: EntityRow
    followers: tuple[int, ...]


def deified_rarity(rules: Rules, power_level: int) -> Rarity:
    rolled = entity_rarity(rules, power_level)
    return Rarity.from_rank(min(rolled.rank, DEIFY_RARITY_CAP.rank))


def strong_stats(rules: Rules, mortal: EntityRow) -> list[Stat]:
    ranked = sorted(MORTAL_TO_SON_STATS, key=lambda pair: -(stat(mortal, pair[0]) or 0))
    return [son_stat for _, son_stat in ranked[: rules.god_power.deify_strong_stats]]


def roll_stats(rules: Rules, rng: SeededRandom, rarity: Rarity, strong: list[Stat], weak: list[Stat] | None = None) -> StatBlock:
    profile = build_rarity_table(rules)[rarity]
    values: dict[Stat, int] = {}
    for item in Stat:
        value = rng.integer(profile.stat_min, profile.stat_max)
        if item in strong:
            value += rules.core_rules.strength_bonus
        if weak and item in weak:
            value -= rules.core_rules.weakness_penalty
        values[item] = max(STAT_FLOOR, min(STAT_CEILING, value))
    return StatBlock.from_mapping(values)


def roll_passions(rules: Rules, rng: SeededRandom) -> PassionBlock:
    ceiling = rules.god_power.deify_passion_max
    return PassionBlock(
        loyalty=rules.god_power.deify_loyalty,
        ambition=rng.integer(0, ceiling),
        wrath=rng.integer(0, ceiling),
        mercy=rng.integer(0, ceiling),
    )


def roll_domains(rng: SeededRandom) -> tuple[Domain, Domain]:
    first, second = rng.sample(list(Domain), 2)
    return first, second


async def least_owned_power(ctx: TickContext) -> PowerDraft:
    owned = Counter(await ctx.session.scalars(select(SonPowerRow.effect)))
    candidates = [spec for spec in POWERS.values() if spec.param is None]
    chosen = min(candidates, key=lambda spec: (owned.get(spec.effect, 0), list(PowerEffect).index(spec.effect)))
    return PowerDraft(name=chosen.name, description=chosen.describe(ctx.rules), effect=chosen.effect)


def first_sentence(description: str) -> str:
    text = description.strip()
    if text.startswith("["):
        closing = text.find("]")
        text = text[closing + 1 :].strip() if closing >= 0 else text
    for mark in ".!?":
        position = text.find(mark)
        if position >= 0:
            text = text[: position + 1]
            break
    return text


async def deify(ctx: TickContext, creator: CreatorRow, mortal: EntityRow, kind: TransformKind = TransformKind.DEIFICATION) -> Deification:
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a named mortal can be raised to godhood.")
    if mortal.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{mortal.name} is not among the living.")
    if await blocked(ctx, kind, mortal.id):
        raise ValidationFailedError(f"The Creator has blocked {mortal.name} from rising to godhood.")
    if await ctx.session.scalar(select(SonRow.id).where(SonRow.name == mortal.name)) is not None:
        raise ValidationFailedError(f"A son named {mortal.name} already exists; rename the mortal first.")
    rng = ctx.rng(f"deify.{mortal.id}")
    rarity = deified_rarity(ctx.rules, mortal.power_level)
    stats = roll_stats(ctx.rules, rng, rarity, strong_stats(ctx.rules, mortal))
    subtype = mortal.subtype or DEFAULT_SUBTYPE
    personality = Personality(
        appearance=first_sentence(mortal.description),
        temperament=TEMPERAMENT.format(subtype=mortal.subtype or "a mortal"),
        obsession=OBSESSION,
        fear=FEAR,
    )
    followers = list(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == mortal.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        )
    )
    await die(ctx, mortal, cause=DEATH_CAUSE.format(creator=creator.name), manner=DeathCause.DIVINE, forced=True)
    await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.DEIFIED, ctx.epoch)
    await NameRepository(ctx.session).release(mortal.id)
    son = await SonRepository(ctx.session).create(
        SonDraft(
            name=mortal.name,
            title=TITLE.format(subtype=subtype),
            rarity=rarity,
            domains=roll_domains(rng),
            stats=stats,
            passions=roll_passions(ctx.rules, rng),
            personality=personality,
            existence=ctx.rules.god_power.deify_existence,
            hp=max_hp(ctx.rules, stats.endurance),
            essence=max_essence(ctx.rules, stats.might),
            birth_epoch=ctx.epoch,
            powers=(await least_owned_power(ctx),),
            current_world_id=mortal.world_id,
            image_prompt=mortal.image_prompt,
        )
    )
    await connect(ctx.session, son.id, mortal.id, BondKind.DESCENDS_FROM, ctx.epoch, description=MORTAL_PAST)
    for follower in followers:
        if follower != son.id:
            await connect(ctx.session, follower, son.id, BondKind.WORSHIPS, ctx.epoch, description=OLD_FAITH)
    await record(
        ctx,
        "gods.deify.ascended",
        roles={IncidentRole.AUTHORITY: creator.id, IncidentRole.SUBJECT: mortal.id, IncidentRole.PRODUCT: son.id},
        facts={"rarity": rarity},
        kind=ChronicleKind.ASCENSION,
        son_id=son.id,
    )
    await record_transformation(ctx, kind, mortal.id, son.id)
    return Deification(son, mortal, tuple(followers))
