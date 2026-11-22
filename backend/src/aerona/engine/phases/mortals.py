from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import MIN_AGING_MULTIPLIER
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import OPEN_INJURY_STATES, HarmCause, InjuryState
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.body.afflictions import ageless
from aerona.engine.body.hits import Harm
from aerona.engine.body.variants import folk_biology
from aerona.engine.context import TickContext
from aerona.engine.divine.laws import binds
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.aging import effective_lifespan, immortal, medicine_regions
from aerona.engine.lifecycle.mortal_death import die, world_year
from aerona.engine.lifecycle.wounds import fatal_injury
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
from aerona.engine.recording.record import StepDraft, record

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
    healing: dict[int, int] = field(default_factory=dict)


async def age_one(ctx: TickContext, mortal: EntityRow, world: AgingWorld) -> None:
    laws, physics = world.laws, world.physics
    rules = ctx.rules
    effects = rules.world_effects
    if await binds(ctx, NaturalLaw.IMMORTALITY, mortal) or immortal(await mortal_flags(ctx.session, mortal)) or await ageless(ctx.session, mortal.id):
        return
    if not (await folk_biology(ctx.session, mortal)).ages:
        return
    seated = await ctx.session.get(MindProfileRow, mortal.id)
    if seated is not None and seated.dormant:
        return
    rng = ctx.rng(seed_of("aging", mortal.id))
    first = mortal.birth_epoch == ctx.epoch
    lifespan = stat_or(mortal, "lifespan", effects.default_lifespan)
    age = stat(mortal, "age") or 0
    if first and age >= lifespan - effects.rejuvenate_years_left:
        age = round_half_up(lifespan * (effects.rejuvenate_age_min_pct / PERCENT + rng.random() * effects.rejuvenate_age_random_pct / PERCENT))
    lived = years_lived(ctx, mortal)
    multiplier = (effects.short_life_aging_mult if laws.has(NaturalLaw.SHORT_LIFE, mortal.world_id) else 1) * physics.of(mortal.world_id).time
    multiplier *= await ctx.hook_easing(mortal.id, DomainHook.AGING)
    aged = age + round_half_up(lived * multiplier)
    info = await effective_lifespan(ctx.session, rules, mortal, world.atlas, world.medicine, healing=world.healing)
    limit = info.effective
    profile = await profile_of(ctx.session, mortal.id)
    health = profile.health if profile is not None else PERCENT
    if (first and aged < limit) or not rng.chance(hazard_chance(rules, aged, limit, health, medicine=info.medicine > 0)):
        set_stats(mortal, age=aged)
        return
    years = rules.time.years_per_epoch
    death_age = aged
    offset = years - lived if first else 0
    death_year = world.start_year + offset + min(years - 1, max(0, round_half_up((death_age - age) / max(MIN_AGING_MULTIPLIER, multiplier))))
    set_stats(mortal, age=death_age)
    if laws.has(NaturalLaw.DEAD_RETURN, mortal.world_id) and rng.chance(rules.world_engine.ghost_chance):
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
    await die(ctx, mortal, natural=True, year=death_year, manner=DeathCause.OLD_AGE)


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
    "table.avatars",
    "table.bonds",
    "table.community_societies",
    "table.cosmos",
    "table.creator",
    "table.crime_cases",
    "table.cult_doctrines",
    "table.cult_offices",
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
    "table.incident_participants",
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
    "table.routes",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.structure_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "mortal.age",
    "mortal.death_year",
    "mortal.lifespan",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.designated_heirs",
    "table.entities",
    "table.entity_flags",
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


PHASES = (Phase("mortal_wounds", mortal_wounds), Phase("mortal_aging", mortal_aging))
