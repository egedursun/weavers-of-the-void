from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.conditions import OPEN_INJURY_STATES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import HarmCause, InjuryState
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.calendar import epoch_end_year
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.aging import aging_rate, effective_lifespan, immortal, medicine_regions
from aerona.engine.lifecycle.mortal_death import AgeTrack, die, world_year
from aerona.engine.lifecycle.wounds import fatal_injury
from aerona.engine.mortal.course import grow_into_stage
from aerona.engine.mortal.life import hazard_chance
from aerona.engine.mortal.profile import profile_of
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.queries import add_flag, canon
from aerona.engine.primitives.records import append_sentence
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.births import birth_year
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

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
    await die(ctx, mortal, cause=WOUND_DEATH, manner=DeathCause.WOUNDS)


@reads("mortal.hp", "table.entities", "table.nodes")
@writes(
    "mortal.death_year",
    "mortal.hp",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.designated_heirs",
    "table.entities",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_history",
    "table.language_profiles",
    "table.memories",
    "table.name_registry",
    "table.sons",
    "table.spirit_profiles",
)
async def mortal_wounds(ctx: TickContext) -> None:
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        hp = stat(mortal, "hp")
        if hp is None or hp > 0 or immortal(await mortal_flags(ctx.session, mortal)):
            continue
        await succumb(ctx, mortal)


def years_lived(ctx: TickContext, mortal: EntityRow, born: int | None) -> int:
    engine = ctx.rules.world_engine
    years = ctx.rules.time.years_per_epoch
    if mortal.birth_epoch != ctx.epoch:
        return years
    if born is not None:
        return min(years, max(1, epoch_end_year(ctx.epoch, years) - (born + (stat(mortal, "age") or 0))))
    return engine.first_epoch_years_engine if mortal.origin is EntityOrigin.ENGINE else engine.first_epoch_years_son


@dataclass(frozen=True)
class AgingWorld:
    laws: LawBook
    physics: PhysicsTable
    atlas: RegionAtlas
    medicine: set[int]
    start_year: int
    healing: dict[int, int] = field(default_factory=dict)


def fatal_year(rng: SeededRandom, rules: Rules, age: int, *, multiplier: float, sampled_years: int, limit: int, health: int, medicine: bool) -> int | None:
    for year in range(sampled_years):
        if rng.chance(hazard_chance(rules, age + round_half_up(year * multiplier), limit, health, medicine=medicine)):
            return year
    return None


async def age_one(ctx: TickContext, mortal: EntityRow, world: AgingWorld) -> None:
    laws = world.laws
    rules = ctx.rules
    effects = rules.world_effects
    multiplier = await aging_rate(ctx, mortal, laws, world.physics)
    if multiplier <= 0:
        return
    rng = ctx.rng(seed_of("aging", mortal.id))
    first = mortal.birth_epoch == ctx.epoch
    lifespan = stat_or(mortal, "lifespan", effects.default_lifespan)
    age = stat(mortal, "age") or 0
    if first and age >= lifespan - effects.rejuvenate_years_left:
        age = round_half_up(lifespan * (effects.rejuvenate_age_min_pct / PERCENT + rng.random() * effects.rejuvenate_age_random_pct / PERCENT))
    lived = years_lived(ctx, mortal, await birth_year(ctx.session, mortal.id) if first else None)
    aged = age + round_half_up(lived * multiplier)
    info = await effective_lifespan(ctx.session, rules, mortal, world.atlas, world.medicine, healing=world.healing)
    limit = info.effective
    profile = await profile_of(ctx.session, mortal.id)
    health = profile.health if profile is not None else PERCENT
    fatal = (
        None
        if first and aged < limit
        else fatal_year(rng, rules, age, multiplier=multiplier, sampled_years=lived, limit=limit, health=health, medicine=info.medicine > 0)
    )
    if fatal is None:
        set_stats(mortal, age=aged)
        await grow_into_stage(ctx, mortal)
        return
    years = rules.time.years_per_epoch
    offset = years - lived if first else 0
    reached = fatal
    death_age = age + round_half_up(reached * multiplier)
    death_year = world.start_year + offset + reached
    if laws.has(NaturalLaw.DEAD_RETURN, mortal.world_id) and rng.chance(rules.world_engine.ghost_chance):
        set_stats(mortal, age=death_age)
        await add_flag(ctx.session, mortal.id, EntityFlag.GHOST, ctx.epoch)
        mortal.fate_note = append_sentence(mortal.fate_note, f"Epoch {ctx.epoch}, world year {death_year}: died at age {death_age} and returned as a ghost.")
        steps = (
            StepDraft(StepAction.AGE, actor=mortal.id, amount=death_age - age, unit=FactUnit.YEARS),
            StepDraft(StepAction.DIE, actor=mortal.id, outcome=StepOutcome.KILLED),
            StepDraft(StepAction.RETURN_TO_LIFE, actor=mortal.id, outcome=StepOutcome.SUCCESS),
        )
        await record(
            ctx,
            "mortals.ghost",
            roles={IncidentRole.SUBJECT: mortal.id},
            facts={"age": death_age, "law": NaturalLaw.DEAD_RETURN, "year": death_year},
            steps=steps,
            son_id=mortal.creator_son_id,
        )
        return
    track = AgeTrack(age, world.start_year + offset, multiplier)
    await die(ctx, mortal, natural=True, year=death_year, manner=DeathCause.OLD_AGE, track=track)


@reads(
    "cult.zeal",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.population",
    "spirit.unrest",
    "table.afflictions",
    "table.armies",
    "table.army_officers",
    "table.avatars",
    "table.bonds",
    "table.community_societies",
    "table.cosmos",
    "table.creator",
    "table.crime_cases",
    "table.cult_doctrines",
    "table.cult_offices",
    "table.deep_passages",
    "table.designated_heirs",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.grave_goods",
    "table.griefs",
    "table.holder_levels",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incorporeal_rights",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.kin_disownings",
    "table.kin_group_members",
    "table.kinship_systems",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.legitimacy_rules",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_biology",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.relationships",
    "table.routes",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.state_changes",
    "table.structure_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.war_sides",
    "table.wars",
    "table.wills",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "mortal.age",
    "mortal.death_year",
    "mortal.hp",
    "mortal.lifespan",
    "table.armies",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.designated_heirs",
    "table.entities",
    "table.entity_flags",
    "table.goods_flows",
    "table.grave_goods",
    "table.griefs",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incorporeal_rights",
    "table.item_history",
    "table.language_profiles",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.personality_values",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
    "table.transformations",
)
async def mortal_aging(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    world = AgingWorld(
        laws=await ctx.laws(),
        physics=await PhysicsTable.load(ctx.session, ctx.rules),
        atlas=atlas,
        medicine=await medicine_regions(ctx.session, atlas),
        start_year=await world_year(ctx.session),
    )
    for mortal in unheld(await canon(ctx.session, [EntityType.MORTAL])):
        if mortal.status is EntityStatus.CANON:
            await age_one(ctx, mortal, world)
    if ctx.environment.aging is not None:
        ctx.environment.aging.done = True


PHASES = (Phase("mortal_wounds", mortal_wounds), Phase("mortal_aging", mortal_aging))
