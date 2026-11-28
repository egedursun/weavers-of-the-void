from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.medicine import MEDICINE, tier_of
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.domain.enums.cosmography import PhenomenonKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityFlag, EntityType, MortalRole
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.engine.body.agelessness import ageless
from aerona.engine.body.variants import folk_biology
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import world_pull
from aerona.engine.cycles.book import realm_of, realm_towns
from aerona.engine.divine.laws import binds
from aerona.engine.eras.effects import tech_bonus
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import LawBook, known_levels
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

IMMORTAL_FLAGS = frozenset({EntityFlag.IMMORTAL, EntityFlag.GHOST})
NOTABLE_FLAGS = frozenset({EntityFlag.CHOSEN, EntityFlag.AGE_CHANGER, EntityFlag.WIZARD})
NOTABLE_ROLES = frozenset({MortalRole.RULER, MortalRole.HERO, MortalRole.PRIEST, MortalRole.SAGE, MortalRole.SEER, MortalRole.CHOSEN})
MEDICINE_COMMUNITY_TYPES = (EntityType.SETTLEMENT, EntityType.PEOPLE)


@dataclass(frozen=True)
class LifespanInfo:
    base: int
    medicine: int

    @property
    def effective(self) -> int:
        return self.base + self.medicine


@dataclass(frozen=True)
class LifeInfo:
    lifespan: LifespanInfo
    age: int | None
    time_factor: float
    years_per_epoch: int
    immortal: bool
    death_year: int | None


def immortal(flags: set[EntityFlag]) -> bool:
    return bool(flags & IMMORTAL_FLAGS)


async def is_immortal(session: AsyncSession, entity: EntityRow) -> bool:
    return immortal(await EntityRepository(session).flags(entity.id))


def is_notable(rules: Rules, entity: EntityRow, flags: set[EntityFlag]) -> bool:
    if flags & NOTABLE_FLAGS or entity.mortal_role in NOTABLE_ROLES or entity.title:
        return True
    charisma = stat(entity, "charisma")
    return charisma is not None and charisma >= rules.world_effects.notable_min_charisma


async def medicine_regions(session: AsyncSession, atlas: RegionAtlas) -> dict[int, int]:
    communities = await canon(session, MEDICINE_COMMUNITY_TYPES)
    levels = await known_levels(session, [community.id for community in communities])
    best: dict[int, int] = {}
    for community in communities:
        region = atlas.top_region(community.id)
        level = levels.get(community.id, {}).get(KnowledgeBranch.MEDICINE, 0)
        if region is not None and level > best.get(region, 0):
            best[region] = level
    return best


async def realm_care(session: AsyncSession, home: EntityRow, healing: dict[int, int] | None) -> int:
    realm = await realm_of(session, home.id)
    if realm is None:
        return 0
    if healing is not None and realm in healing:
        return healing[realm]
    towns = [town.id for town in await realm_towns(session, realm)]
    levels = await known_levels(session, towns)
    best = max((levels.get(town, {}).get(KnowledgeBranch.MEDICINE, 0) for town in towns), default=0)
    if healing is not None:
        healing[realm] = best
    return best


async def effective_lifespan(
    session: AsyncSession,
    rules: Rules,
    entity: EntityRow,
    atlas: RegionAtlas | None = None,
    medicine: dict[int, int] | None = None,
    *,
    healing: dict[int, int] | None = None,
) -> LifespanInfo:
    region_atlas = atlas or await RegionAtlas.load(session)
    healed = medicine if medicine is not None else await medicine_regions(session, region_atlas)
    recorded = stat(entity, "lifespan")
    base = recorded if recorded else rules.world_effects.default_lifespan
    region = region_atlas.top_region(entity.id)
    level = healed.get(region, 0) if region is not None else 0
    home = await community_of(session, entity) if entity.entity_type is EntityType.MORTAL else None
    if home is not None:
        known = healing.get(home.id) if healing is not None else None
        if known is None:
            known = (await known_levels(session, [home.id])).get(home.id, {}).get(KnowledgeBranch.MEDICINE, 0)
            if healing is not None:
                healing[home.id] = known
        level = max(level, known)
        if is_notable(rules, entity, await EntityRepository(session).flags(entity.id)):
            level = max(level, await realm_care(session, home, healing))
    medicine_bonus = round(base * MEDICINE[tier_of(rules.healing, level, 0, False)].lifespan_pct / PERCENT)
    if home is not None:
        medicine_bonus += round(base * await tech_bonus(session, rules, home.id, EraChannel.HEALTH) / PERCENT)
    return LifespanInfo(base=base, medicine=medicine_bonus)


async def in_time_slip(session: AsyncSession, region_id: int | None) -> bool:
    if region_id is None:
        return False
    statement = (
        select(PhenomenonFootprintRow.phenomenon_entity_id)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .where(PhenomenonFootprintRow.region_entity_id == region_id, PhenomenonProfileRow.kind == PhenomenonKind.TIME_DISTORTION)
    )
    return await session.scalar(statement.limit(1)) is not None


async def life_info(session: AsyncSession, rules: Rules, entity: EntityRow) -> LifeInfo:
    world = await session.get(WorldRow, entity.world_id)
    time_factor = world.time_factor if world is not None and world.time_factor else 1.0
    if world is not None:
        time_factor *= (await world_pull(session, rules, world)).time
    if await in_time_slip(session, entity.location_id):
        time_factor *= 1 + rules.phenomena.time_slip_age_pct / PERCENT
    return LifeInfo(
        lifespan=await effective_lifespan(session, rules, entity),
        age=stat(entity, "age"),
        time_factor=time_factor,
        years_per_epoch=round_half_up(rules.time.years_per_epoch * time_factor),
        immortal=await is_immortal(session, entity),
        death_year=stat(entity, "death_year"),
    )


async def raise_lifespan_to_death_age(
    session: AsyncSession, rules: Rules, mortal: EntityRow, atlas: RegionAtlas | None = None, medicine: dict[int, int] | None = None
) -> bool:
    age = stat(mortal, "age")
    if age is None:
        return False
    info = await effective_lifespan(session, rules, mortal, atlas, medicine)
    if age <= info.effective:
        return False
    set_stats(mortal, lifespan=age - info.medicine)
    return True


async def aging_rate(ctx: TickContext, mortal: EntityRow, laws: LawBook, physics: PhysicsTable) -> float:
    if (
        await binds(ctx, NaturalLaw.IMMORTALITY, mortal)
        or immortal(await EntityRepository(ctx.session).flags(mortal.id))
        or await ageless(ctx.session, mortal.id)
    ):
        return 0.0
    if not (await folk_biology(ctx.session, mortal)).ages:
        return 0.0
    seated = await ctx.session.get(MindProfileRow, mortal.id)
    if seated is not None and seated.dormant:
        return 0.0
    effects = ctx.rules.world_effects
    multiplier = (effects.short_life_aging_mult if laws.has(NaturalLaw.SHORT_LIFE, mortal.world_id) else 1) * physics.of(mortal.world_id).time
    return multiplier * await ctx.hook_easing(mortal.id, DomainHook.AGING)
