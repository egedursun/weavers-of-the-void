from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import MIN_AGING_MULTIPLIER
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import OPEN_INJURY_STATES, HarmCause, InjuryState
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.aging import effective_lifespan, immortal, medicine_regions
from aerona.engine.lifecycle.mortal_death import die, world_year
from aerona.engine.lifecycle.wounds import fatal_injury
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.queries import add_flag, canon
from aerona.engine.primitives.records import append_sentence
from aerona.engine.primitives.stats import set_stats, stat

WOUND_DEATH = "succumbed to their wounds"


async def mortal_flags(session: AsyncSession, mortal: EntityRow) -> set[EntityFlag]:
    return await EntityRepository(session).flags(mortal.id)


async def succumb(ctx: TickContext, mortal: EntityRow) -> None:
    open_wounds = [
        row
        for row in await ctx.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == mortal.id).order_by(InjuryRow.severity.desc(), InjuryRow.id))
        if row.state in OPEN_INJURY_STATES
    ]
    if open_wounds:
        open_wounds[0].state = InjuryState.LETHAL
    else:
        await fatal_injury(ctx, mortal, Harm(ctx.rules.casualties.wound_hp, HarmCause.ACCIDENT, WOUND_DEATH))
    await die(ctx, mortal, cause=WOUND_DEATH)


@reads("mortal.hp")
@reads("mortal.hp")
async def mortal_wounds(ctx: TickContext) -> None:
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        hp = stat(mortal, "hp")
        if hp is None or hp > 0 or immortal(await mortal_flags(ctx.session, mortal)):
            continue
        await succumb(ctx, mortal)


def years_lived(ctx: TickContext, mortal: EntityRow) -> int:
    engine = ctx.rules.world_engine
    if mortal.birth_epoch != ctx.epoch:
        return ctx.rules.time.years_per_epoch
    return engine.first_epoch_years_engine if mortal.origin is EntityOrigin.ENGINE else engine.first_epoch_years_son


@dataclass(frozen=True)
class AgingWorld:
    laws: LawBook
    physics: PhysicsTable
    atlas: RegionAtlas
    medicine: set[int]
    start_year: int


async def age_one(ctx: TickContext, mortal: EntityRow, world: AgingWorld) -> None:
    laws, physics = world.laws, world.physics
    rules = ctx.rules
    effects = rules.world_effects
    if laws.has(NaturalLaw.IMMORTALITY, mortal.world_id) or immortal(await mortal_flags(ctx.session, mortal)):
        return
    rng = ctx.rng(seed_of("aging", mortal.id))
    first = mortal.birth_epoch == ctx.epoch
    lifespan = stat(mortal, "lifespan") or effects.default_lifespan
    age = stat(mortal, "age") or 0
    if first and age >= lifespan - effects.rejuvenate_years_left:
        age = round_half_up(lifespan * (effects.rejuvenate_age_min_pct / PERCENT + rng.random() * effects.rejuvenate_age_random_pct / PERCENT))
    lived = years_lived(ctx, mortal)
    multiplier = (effects.short_life_aging_mult if laws.has(NaturalLaw.SHORT_LIFE, mortal.world_id) else 1) * physics.of(mortal.world_id).time
    aged = age + round_half_up(lived * multiplier)
    limit = (await effective_lifespan(ctx.session, rules, mortal, world.atlas, world.medicine)).effective
    if aged < limit:
        set_stats(mortal, age=aged)
        return
    years = rules.time.years_per_epoch
    death_age = max(age, limit)
    offset = years - lived if first else 0
    death_year = world.start_year + offset + min(years - 1, max(0, round_half_up((death_age - age) / max(MIN_AGING_MULTIPLIER, multiplier))))
    set_stats(mortal, age=death_age)
    if laws.has(NaturalLaw.DEAD_RETURN, mortal.world_id) and rng.chance(rules.world_engine.ghost_chance):
        await add_flag(ctx.session, mortal.id, EntityFlag.GHOST, ctx.epoch)
        mortal.fate_note = append_sentence(mortal.fate_note, f"Epoch {ctx.epoch}, world year {death_year}: died at age {death_age} and returned as a ghost.")
        await note(
            ctx,
            f"{mortal.name} died but the law of the world called them back: now a ghost.",
            key="mortals.ghost",
            ids=[mortal.id],
            son_id=mortal.creator_son_id,
        )
        return
    await die(ctx, mortal, natural=True, year=death_year)


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "table.bonds",
    "table.community_societies",
    "table.cosmos",
    "table.designated_heirs",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.language_profiles",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.routes",
    "table.traits",
    "table.world_maps",
)
@writes(
    "mortal.age",
    "mortal.death_year",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.memories",
    "table.name_registry",
    "table.sons",
)
@reads("mortal.age", "mortal.agility", "mortal.charisma", "mortal.intellect", "mortal.lifespan", "mortal.strength")
@writes("mortal.age", "mortal.death_year")
async def mortal_aging(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    world = AgingWorld(
        laws=await ctx.laws(),
        physics=await PhysicsTable.load(ctx.session, ctx.rules),
        atlas=atlas,
        medicine=await medicine_regions(ctx.session, atlas),
        start_year=await world_year(ctx.session),
    )
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if mortal.status is EntityStatus.CANON:
            await age_one(ctx, mortal, world)


PHASES = (Phase("mortal_wounds", mortal_wounds), Phase("mortal_aging", mortal_aging))
