from collections.abc import Callable

from sqlalchemy import select

from aerona.catalog.conditions import AGE_CONDITIONS, OPEN_INJURY_STATES
from aerona.catalog.kinds.harm import HARM_DEATHS
from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.catalog.life.mortal import BETROTH_CHILDREN_LIFE_STAGES, EDUCATE_LIFE_STAGES, LIVE_ONE_EPOCH_LIFE_STAGES, SEED_STANDING_MEMORY_KINDS
from aerona.catalog.mind import CAREER_SKILLS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import partial
from aerona.db.fixups import fixup_due
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.body import ConditionKind, HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.genetics import GeneticEffect
from aerona.domain.enums.mind import Attribute, OpinionComponent, SkillKind, SkillSource, ValueHolder, WantKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause, LifeStage, MarriageEnd
from aerona.domain.enums.polity import OathKind
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.unions import UnionForm, UnionPurpose
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.body.bands import banded
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import union_of
from aerona.engine.environment.book import region_environment
from aerona.engine.genetics.genome import effect_steps
from aerona.engine.genetics.life import climate_health
from aerona.engine.law.prisons import realm_of_town
from aerona.engine.military.terms import war_between
from aerona.engine.mind.aspirations import open_wants
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.memories import strength_of
from aerona.engine.mind.needs import role_status
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.skills import practise
from aerona.engine.mind.space import blend
from aerona.engine.mind.split import seed_split, stored_attribute
from aerona.engine.mortal.kin import betrothed_of, children_of, parents_of, partners_of, siblings_of
from aerona.engine.mortal.kinship import betroth, end_marriage, foster, marriage_between, marriages_of, marry
from aerona.engine.mortal.life import CHILD_SUBTYPE, StageBounds, adult, assign_sex, biology_of, refresh_life, stage_bounds, stage_rank, young
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.mortal.standing import add_renown
from aerona.engine.polity.oaths import swear
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.maturity import away_among, of_age_query
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, connect, living_entity
from aerona.engine.primitives.stats import set_stats, shift_stat, stat, stat_or
from aerona.engine.recording.births import birth_year
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.unions.axes import spousing_of
from aerona.engine.unions.customs import divorce_rule

ROLE_CLASSES: dict[MortalRole, SocialClass] = {
    MortalRole.RULER: SocialClass.NOBLE,
    MortalRole.SWORN_WARRIOR: SocialClass.NOBLE,
    MortalRole.PRIEST: SocialClass.PRIEST,
    MortalRole.SAINT: SocialClass.PRIEST,
    MortalRole.SEER: SocialClass.PRIEST,
    MortalRole.WARRIOR: SocialClass.WARRIOR,
    MortalRole.HERO: SocialClass.WARRIOR,
    MortalRole.HUNTER: SocialClass.WARRIOR,
    MortalRole.CAPTAIN: SocialClass.WARRIOR,
    MortalRole.CHOSEN: SocialClass.WARRIOR,
    MortalRole.SAGE: SocialClass.SCRIBE,
    MortalRole.SCRIBE: SocialClass.SCRIBE,
    MortalRole.MERCHANT: SocialClass.MERCHANT,
    MortalRole.ARTISAN: SocialClass.ARTISAN,
    MortalRole.HEALER: SocialClass.ARTISAN,
    MortalRole.APPRENTICE: SocialClass.ARTISAN,
    MortalRole.BANDIT: SocialClass.OUTCAST,
    MortalRole.OFFICER: SocialClass.OFFICIAL,
    MortalRole.SPY: SocialClass.OFFICIAL,
    MortalRole.SCIENTIST: SocialClass.PROFESSIONAL,
    MortalRole.ENGINEER: SocialClass.PROFESSIONAL,
    MortalRole.PILOT: SocialClass.PROFESSIONAL,
    MortalRole.PHYSICIAN: SocialClass.PROFESSIONAL,
    MortalRole.JOURNALIST: SocialClass.PROFESSIONAL,
    MortalRole.EXECUTIVE: SocialClass.MERCHANT,
}
DEATH_FLAGS: dict[EntityFlag, DeathCause] = {
    EntityFlag.FELL_IN_BATTLE: DeathCause.BATTLE,
    EntityFlag.DIED_IN_SIEGE: DeathCause.BATTLE,
    EntityFlag.DIED_IN_DISASTER: DeathCause.DISASTER,
    EntityFlag.DIED_OF_PLAGUE: DeathCause.DISEASE,
    EntityFlag.SLAIN_IN_CAPTIVITY: DeathCause.EXECUTION,
}
SCHOOL_KINDS = frozenset({EngineKind.SCHOOL, EngineKind.LIBRARY})
TEMPLE_KINDS = frozenset({EngineKind.TEMPLE})
DEATH_FIXUP = "mortal.death_causes"
FULL = PERCENT


LIFE_KEYS = partial(
    LifeStage,
    {LifeStage.ADULT: "life.adult", LifeStage.MATURE: "life.mature", LifeStage.ELDER: "life.elder"},
    without=tuple(stage for stage in LifeStage if LIFE_STAGES[stage].reached is None),
)


def class_for(mortal: EntityRow) -> SocialClass:
    return ROLE_CLASSES.get(mortal.mortal_role or MortalRole.COMMONER, SocialClass.FARMER)


async def parted_by_war(ctx: TickContext, mortal: EntityRow, spouse_id: int) -> bool:
    spouse = await ctx.session.get(EntityRow, spouse_id)
    if spouse is None:
        return False
    mine, theirs = await realm_of_town(ctx, mortal.location_id), await realm_of_town(ctx, spouse.location_id)
    return mine is not None and theirs is not None and mine != theirs and await war_between(ctx, mine, theirs) is not None


async def heritage_class(ctx: TickContext, mortal: EntityRow) -> SocialClass:
    for parent_id in await parents_of(ctx.session, mortal.id):
        parent = await ctx.session.get(EntityRow, parent_id)
        if parent is not None and parent.social_class is not None:
            return parent.social_class
    return class_for(mortal)


async def seed_mortal(ctx: TickContext, mortal: EntityRow) -> bool:
    profile, created = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    await seed_split(ctx.session, ctx.rules, mortal, ctx.rng(seed_of("body_and_mind", mortal.id)))
    assign_sex(mortal)
    if mortal.social_class is None:
        mortal.social_class = await heritage_class(ctx, mortal)
    await refresh_life(ctx.session, ctx.rules, mortal, profile)
    if created:
        await seed_standing(ctx, mortal, profile)
    return created


async def seed_standing(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    table = ctx.rules.standing
    if not is_held(profile, "renown"):
        profile.renown = clamp_int(mortal.importance or 0, 0, FULL)
    if not is_held(profile, "wealth"):
        profile.wealth = clamp_int(role_status(ctx.rules, mortal.mortal_role or MortalRole.COMMONER) * table.wealth_status_pct / PERCENT, 0, FULL)
    flags = {row for row in await active_flags(ctx, mortal.id)}
    if not is_held(profile, "honour") and EntityFlag.OATHBREAKER in flags:
        profile.honour = clamp_int(profile.honour - table.honour_broken_oath, 0, FULL)
    if not is_held(profile, "infamy"):
        rows = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.subject_node_id == mortal.id, MemoryRow.magnitude < 0))
        dread = sum(-strength_of(row, ctx.epoch) for row in rows if row.kind in SEED_STANDING_MEMORY_KINDS)
        profile.infamy = clamp_int(dread * table.infamy_atrocity / PERCENT, 0, FULL)


async def active_flags(ctx: TickContext, mortal_id: int) -> set[EntityFlag]:
    return await EntityRepository(ctx.session).flags(mortal_id)


async def backfill_deaths(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, DEATH_FIXUP):
        return 0
    dead = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD)))
    found = 0
    for mortal in dead:
        profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
        if profile.cause_of_death is not None:
            continue
        lethal = await ctx.session.scalar(select(InjuryRow).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.state == InjuryState.LETHAL).limit(1))
        flags = await active_flags(ctx, mortal.id)
        flagged = next((cause for flag, cause in DEATH_FLAGS.items() if flag in flags), None)
        age, lifespan = stat(mortal, "age") or 0, stat(mortal, "lifespan") or 0
        if lethal is not None:
            profile.cause_of_death = HARM_DEATHS.get(lethal.cause_kind, DeathCause.WOUNDS)
        elif flagged is not None:
            profile.cause_of_death = flagged
        elif lifespan and age >= lifespan:
            profile.cause_of_death = DeathCause.OLD_AGE
        else:
            profile.cause_of_death = DeathCause.UNKNOWN
        profile.death_place_id = mortal.location_id
        found += 1
    ctx.session.add(AppliedFixupRow(key=DEATH_FIXUP, result={"deaths": found}))
    await ctx.session.flush()
    return found


async def live_one_epoch(ctx: TickContext, mortal: EntityRow) -> LifeStage:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    before = profile.life_stage
    stage = await refresh_life(ctx.session, ctx.rules, mortal, profile)
    table = ctx.rules.aging
    if stage is LifeStage.YOUTH and not is_held(profile, "life_stage"):
        grown = {key: clamp_int((stat_or(mortal, key, FULL // 2)) + table.youth_growth, 0, FULL) for key in ("strength", "agility", "endurance")}
        set_stats(mortal, **grown)
    if stage in LIVE_ONE_EPOCH_LIFE_STAGES:
        set_stats(
            mortal,
            strength=clamp_int((stat_or(mortal, "strength", FULL // 2)) - table.elder_strength_decline, 0, FULL),
            agility=clamp_int((stat_or(mortal, "agility", FULL // 2)) - table.elder_agility_decline, 0, FULL),
            endurance=clamp_int((stat_or(mortal, "endurance", FULL // 2)) - table.elder_endurance_decline, 0, FULL),
            wisdom=clamp_int((stat_or(mortal, "wisdom", FULL // 2)) + table.elder_wisdom_gain, 0, FULL),
        )
        rng = ctx.rng(seed_of("age_condition", mortal.id, ctx.epoch))
        if rng.chance(table.age_condition_chance):
            kind = rng.pick(AGE_CONDITIONS)
            await gain_condition(ctx, mortal, kind, HarmCause.AGE, severity=banded(ctx, ctx.rules.harm_bands.old_age, mortal.id))
    await update_health(ctx, mortal, profile, stage)
    await tell_stage(ctx, mortal, profile, before, stage, aged=False)
    return stage


STAGE_ENTRY: dict[LifeStage, Callable[[StageBounds], float]] = {
    LifeStage.ADULT: lambda bounds: bounds.youth,
    LifeStage.MATURE: lambda bounds: bounds.mature,
    LifeStage.ELDER: lambda bounds: bounds.elder,
    LifeStage.ANCIENT: lambda bounds: bounds.ancient,
}


async def reached_at(ctx: TickContext, mortal: EntityRow, stage: LifeStage, *, aged: bool) -> tuple[int, int]:
    years = ctx.rules.time.years_per_epoch
    start = epoch_start_year(ctx.epoch, years)
    reference = epoch_end_year(ctx.epoch, years) - 1 if aged else start
    age = stat_or(mortal, "age", 0)
    entry = STAGE_ENTRY.get(stage)
    if entry is None:
        return reference, age
    bounds = stage_bounds(ctx.rules, await biology_of(ctx.session, mortal), stat_or(mortal, "lifespan", ctx.rules.world_effects.default_lifespan))
    born = await birth_year(ctx.session, mortal.id)
    year = max(start, reference - max(0, age - round_half_up(entry(bounds))), born if born is not None else start)
    return min(year, reference), age - (reference - min(year, reference))


async def tell_stage(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, before: LifeStage, stage: LifeStage, *, aged: bool) -> None:
    key = LIFE_KEYS.get(stage)
    if stage is not before and stage_rank(stage) > stage_rank(before) and key is not None:
        year, age = await reached_at(ctx, mortal, stage, aged=aged)
        await record(
            ctx,
            key,
            roles={IncidentRole.SUBJECT: mortal.id},
            facts={"stage": stage, "age": age, "health": profile.health},
            at_moment=Moment(year),
        )


async def grow_into_stage(ctx: TickContext, mortal: EntityRow) -> LifeStage:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    before = profile.life_stage
    stage = await refresh_life(ctx.session, ctx.rules, mortal, profile)
    if mortal.subtype == CHILD_SUBTYPE and adult(stage):
        mortal.subtype = None
    await tell_stage(ctx, mortal, profile, before, stage, aged=True)
    return stage


async def update_health(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, stage: LifeStage) -> None:
    if is_held(profile, "health"):
        return
    table = ctx.rules.aging
    chronic = await ctx.session.scalars(
        select(ConditionRow.severity).where(
            ConditionRow.bearer_node_id == mortal.id, ConditionRow.ended_epoch.is_(None), ConditionRow.kind == ConditionKind.CHRONIC_ILLNESS
        )
    )
    wounds = await ctx.session.scalars(select(InjuryRow.severity).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.state.in_(list(OPEN_INJURY_STATES))))
    loss = sum(chronic) * table.elder_health_loss + sum(wounds)
    age_loss = LIFE_STAGES[stage].age_loss
    loss += getattr(table, age_loss) if age_loss is not None else 0
    if stage is LifeStage.MATURE:
        decline(ctx, mortal)
    mending = await stored_attribute(ctx.session, mortal, Attribute.RECUPERATION)
    gain = table.health_recovery * (1 + (mending - FULL // 2) / PERCENT) if LIFE_STAGES[stage].recovers else 0
    gain += await land_health(ctx, mortal)
    profile.health = clamp_int(profile.health + gain - loss, 0, FULL)


def decline(ctx: TickContext, mortal: EntityRow) -> None:
    if held(mortal.id):
        return
    share = ctx.rules.life_course.over_epoch(ctx.rules.life_course.mature_decline_pct)
    for key in ("strength", "endurance"):
        if stat(mortal, key) is not None:
            shift_stat(mortal, key, -round_half_up(stat_or(mortal, key, 0) * share / PERCENT))


async def land_health(ctx: TickContext, mortal: EntityRow) -> int:
    genome = await ctx.session.get(GenomeRow, mortal.id)
    if genome is None or mortal.location_id is None:
        return 0
    if not effect_steps(genome.genes, GeneticEffect.COLD) and not effect_steps(genome.genes, GeneticEffect.HEAT):
        return 0
    ground = await region_environment(ctx.session, mortal.location_id)
    return climate_health(ctx.rules, genome, ground.temperature_band if ground is not None else None)


async def institution_bonus(ctx: TickContext, community_id: int | None) -> tuple[float, float]:
    if community_id is None:
        return 0.0, 0.0
    statement = select(EntityRow.engine_kind).where(
        EntityRow.location_id == community_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.STRUCTURE
    )
    kinds = set(await ctx.session.scalars(statement))
    table = ctx.rules.education
    return (table.school_xp if kinds & SCHOOL_KINDS else 0.0), (table.temple_xp if kinds & TEMPLE_KINDS else 0.0)


async def educate(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> int:
    if profile.life_stage not in EDUCATE_LIFE_STAGES:
        return 0
    table = ctx.rules.education
    people = await people_of(ctx.session, mortal)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    literacy = 1 + (culture.literacy if culture is not None else 0) / PERCENT * table.literacy_weight_pct / PERCENT
    school, temple = await institution_bonus(ctx, mortal.location_id)
    learned = 0
    for parent_id in await parents_of(ctx.session, mortal.id):
        parent = await living_entity(ctx.session, parent_id)
        if parent is None:
            continue
        skills = CAREER_SKILLS.get(parent.mortal_role or MortalRole.COMMONER, ())
        for skill in skills[:1]:
            level = await ctx.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == parent.id, SkillRow.skill == skill).limit(1)) or 0
            learned += await practise(
                ctx.session, ctx.rules, mortal.id, skill, table.parent_xp * int(level) / PERCENT * literacy, epoch=ctx.epoch, source=SkillSource.TEACHING
            )
    if school:
        learned += await practise(ctx.session, ctx.rules, mortal.id, SkillKind.WRITING, school * literacy, epoch=ctx.epoch, source=SkillSource.TEACHING)
    if temple:
        learned += await practise(ctx.session, ctx.rules, mortal.id, SkillKind.THEOLOGY, temple * literacy, epoch=ctx.epoch, source=SkillSource.TEACHING)
    if (school or temple) and not is_held(profile, "education"):
        profile.education = clamp_int(profile.education + table.education_gain * literacy, 0, FULL)
    await hostage_drift(ctx, mortal)
    return learned


async def hostage_drift(ctx: TickContext, mortal: EntityRow) -> bool:
    captors = await active_bonds(ctx.session, [BondKind.HOLDS_CAPTIVE], targets=[mortal.id])
    if not captors:
        return False
    captor = await living_entity(ctx.session, captors[0].source_node_id)
    if captor is None:
        return False
    culture = await stored_values(ctx.session, ValueHolder.CULTURE, captor.id)
    if not culture:
        people = await people_of(ctx.session, captor)
        culture = await stored_values(ctx.session, ValueHolder.CULTURE, people.id) if people is not None else {}
    current = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    if not culture or not current:
        return False
    await write_values(ctx.session, ValueHolder.PERSONAL, mortal.id, blend(current, culture, ctx.rules.education.hostage_drift_pct))
    return True


async def upkeep_standing(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    table = ctx.rules.standing
    if not is_held(profile, "renown"):
        profile.renown = clamp_int(profile.renown * (PERCENT - table.renown_decay_pct) / PERCENT, 0, FULL)
    if not is_held(profile, "infamy"):
        profile.infamy = clamp_int(profile.infamy - table.infamy_decay, 0, FULL)
    if not is_held(profile, "wealth"):
        target = role_status(ctx.rules, mortal.mortal_role or MortalRole.COMMONER) * table.wealth_status_pct / PERCENT
        profile.wealth = clamp_int(profile.wealth + (target - profile.wealth) * table.wealth_drift_pct / PERCENT, 0, FULL)
    holds = await ctx.session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == mortal.id).limit(1))
    if not is_held(profile, "legitimacy"):
        if holds is None and mortal.mortal_role is not MortalRole.RULER:
            profile.legitimacy = None
        else:
            value = table.office_legitimacy + (profile.honour - FULL // 2) * table.legitimacy_honour_pct / PERCENT
            value += profile.renown * table.legitimacy_renown_pct / PERCENT - profile.infamy * table.legitimacy_infamy_pct / PERCENT
            profile.legitimacy = clamp_int(value, 0, FULL)


async def patronise(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    table = ctx.rules.standing
    if profile.wealth < table.patronage_wealth or mortal.location_id is None:
        return False
    if not ctx.rng(seed_of("patronage", mortal.id, ctx.epoch)).chance(await stored_attribute(ctx.session, mortal, Attribute.CREATIVITY)):
        return False
    authors = select(EntityRow.id).where(await present_among(ctx.session, [mortal.location_id]), EntityRow.entity_type == EntityType.MORTAL)
    work = await ctx.session.scalar(
        select(ArtworkProfileRow).where(ArtworkProfileRow.author_entity_id.in_(authors), ArtworkProfileRow.patron_entity_id.is_(None)).limit(1)
    )
    if work is None:
        return False
    work.patron_entity_id = mortal.id
    artwork = await ctx.session.get(EntityRow, work.artwork_entity_id)
    if artwork is not None:
        set_stats(artwork, renown=clamp_int((stat(artwork, "renown") or 0) + table.patronage_renown, 0, FULL))
    profile.wealth = clamp_int(profile.wealth - table.patronage_cost, 0, FULL)
    await add_renown(ctx.session, mortal.id, table.patronage_renown, ctx.epoch, rules=ctx.rules)
    await record(
        ctx,
        "standing.patronage",
        roles={IncidentRole.PATRON: mortal.id, IncidentRole.PRODUCT: work.artwork_entity_id},
        facts={"cost": table.patronage_cost, "renown": table.patronage_renown},
        steps=(StepDraft(StepAction.PAY, actor=mortal.id, target=work.artwork_entity_id, amount=table.patronage_cost, unit=FactUnit.WEALTH_POINTS),),
    )
    return True


async def marriage_wish(ctx: TickContext, mortal: EntityRow) -> float:
    return 1 + ctx.rules.aspirations.want_match_pct / PERCENT if WantKind.MARRY in await open_wants(ctx.session, mortal.id) else 1.0


async def end_marriages(ctx: TickContext, mortal: EntityRow, rng: SeededRandom) -> str | None:
    table = ctx.rules.kinship
    custom = await divorce_custom(ctx, mortal)
    for row in await marriages_of(ctx.session, mortal.id, ended=False):
        spouse_id = row.second_id if row.first_id == mortal.id else row.first_id
        view = await opinion(ctx.session, ctx.rules, ctx.epoch, mortal.id, spouse_id)
        if custom != "forbidden" and view.value < table.divorce_opinion_below and rng.chance(table.divorce_chance * (2 if custom == "free" else 1)):
            await end_marriage(ctx.session, row, ctx.epoch, MarriageEnd.DIVORCE)
            await record(
                ctx,
                "kin.divorce",
                roles={IncidentRole.SPOUSE: [mortal.id, spouse_id]},
                facts={"opinion": view.value},
                steps=(StepDraft(StepAction.SEPARATE, actor=mortal.id, target=spouse_id),),
            )
            return "divorced"
        if await parted_by_war(ctx, mortal, spouse_id) and rng.chance(table.war_parting_chance):
            await end_marriage(ctx.session, row, ctx.epoch, MarriageEnd.WAR)
            await record(
                ctx,
                "kin.war_parted",
                roles={IncidentRole.SPOUSE: [mortal.id, spouse_id]},
                steps=(StepDraft(StepAction.SEPARATE, actor=mortal.id, target=spouse_id),),
            )
            return "parted by war"
        cold = custom == "forbidden" and view.value < table.divorce_opinion_below
        if cold and await childless(ctx, mortal.id, spouse_id) and rng.chance(table.annulment_chance):
            await end_marriage(ctx.session, row, ctx.epoch, MarriageEnd.ANNULMENT)
            await record(
                ctx,
                "kin.annulment",
                roles={IncidentRole.SPOUSE: [mortal.id, spouse_id]},
                facts={"opinion": view.value},
                steps=(StepDraft(StepAction.SEPARATE, actor=mortal.id, target=spouse_id, outcome=StepOutcome.REVERSED),),
            )
            return "annulled"
    return None


async def match(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> str | None:
    table = ctx.rules.kinship
    if not adult(profile.life_stage) or is_held(profile, "kin"):
        return None
    rng = ctx.rng(seed_of("kin", mortal.id, ctx.epoch))
    for partner_id in await betrothed_of(ctx.session, mortal.id):
        partner = await living_entity(ctx.session, partner_id)
        partner_profile = await ctx.session.get(MortalProfileRow, partner_id)
        if (
            partner is not None
            and partner_profile is not None
            and adult(partner_profile.life_stage)
            and rng.chance(table.over_epoch(table.marriage_chance * await marriage_wish(ctx, mortal)))
        ):
            await marry(ctx.session, mortal, partner, ctx.epoch, purpose=UnionPurpose.ALLIANCE, description="as they were promised")
            await record(
                ctx,
                "kin.marriage",
                roles={IncidentRole.SPOUSE: [mortal.id, partner.id]},
                facts={"form": UnionForm.PAIR, "purpose": UnionPurpose.ALLIANCE},
                steps=(StepDraft(StepAction.MARRY, actor=mortal.id, target=partner.id),),
                place=mortal.location_id,
            )
            return "married"
    married = bool(await partners_of(ctx.session, mortal.id))
    for bond in await active_bonds(ctx.session, [BondKind.LOVES], sources=[mortal.id]):
        lover = await living_entity(ctx.session, bond.target_node_id)
        lover_profile = await ctx.session.get(MortalProfileRow, bond.target_node_id)
        if lover is None or lover.entity_type is not EntityType.MORTAL or lover_profile is None or not adult(lover_profile.life_stage):
            continue
        if await marriage_between(ctx.session, mortal.id, lover.id) is not None:
            continue
        plural = await plural_custom(ctx, mortal)
        if (married and not plural) or not rng.chance(table.over_epoch(table.marriage_chance * await marriage_wish(ctx, mortal))):
            continue
        await marry(
            ctx.session, mortal, lover, ctx.epoch, form=UnionForm.PLURAL if married else UnionForm.PAIR, purpose=UnionPurpose.LOVE, description="for love"
        )
        await record(
            ctx,
            "kin.marriage",
            roles={IncidentRole.SPOUSE: [mortal.id, lover.id]},
            facts={"form": UnionForm.PLURAL if married else UnionForm.PAIR, "purpose": UnionPurpose.LOVE},
            steps=(StepDraft(StepAction.COURT, actor=mortal.id, target=lover.id), StepDraft(StepAction.MARRY, actor=mortal.id, target=lover.id)),
            place=mortal.location_id,
        )
        return "married"
    return await end_marriages(ctx, mortal, rng)


async def childless(ctx: TickContext, first: int, second: int) -> bool:
    return not set(await children_of(ctx.session, first)) & set(await children_of(ctx.session, second))


async def divorce_custom(ctx: TickContext, mortal: EntityRow) -> str:
    return await divorce_rule(ctx.session, mortal)


async def plural_custom(ctx: TickContext, mortal: EntityRow) -> bool:
    return spousing_of(await union_of(ctx.session, mortal)).several


async def betroth_children(ctx: TickContext, mortal: EntityRow) -> bool:
    if mortal.social_class is not SocialClass.NOBLE or not ctx.rng(seed_of("betroth", mortal.id, ctx.epoch)).chance(
        ctx.rules.kinship.over_epoch(ctx.rules.kinship.betrothal_chance)
    ):
        return False
    for child_id in await children_of(ctx.session, mortal.id):
        child = await living_entity(ctx.session, child_id)
        child_profile = await ctx.session.get(MortalProfileRow, child_id)
        if child is None or child_profile is None or not young(child_profile.life_stage) or await betrothed_of(ctx.session, child_id):
            continue
        statement = (
            select(EntityRow)
            .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.social_class == SocialClass.NOBLE,
                EntityRow.world_id == mortal.world_id,
                EntityRow.id != child.id,
                MortalProfileRow.life_stage.in_(BETROTH_CHILDREN_LIFE_STAGES),
            )
            .order_by(EntityRow.id)
        )
        kin = {child.id, *await siblings_of(ctx.session, child.id)}
        for other in await ctx.session.scalars(statement):
            if other.id in kin or await betrothed_of(ctx.session, other.id):
                continue
            await betroth(ctx.session, child, other, ctx.epoch, description="promised by their families")
            await record(
                ctx,
                "kin.betrothal",
                roles={IncidentRole.SPOUSE: [child.id, other.id]},
                steps=(StepDraft(StepAction.AGREE, target=child.id),),
            )
            return True
    return False


async def foster_orphan(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    if not young(profile.life_stage) or mortal.location_id is None:
        return False
    parents = [await living_entity(ctx.session, parent) for parent in await parents_of(ctx.session, mortal.id)]
    if any(parent is not None for parent in parents) or not ctx.rng(seed_of("foster", mortal.id, ctx.epoch)).chance(ctx.rules.kinship.foster_chance):
        return False
    statement = select(EntityRow).where(
        await present_among(ctx.session, [mortal.location_id]),
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.id != mortal.id,
        EntityRow.social_class == SocialClass.NOBLE,
        of_age_query(),
    )
    willing = unheld(await ctx.session.scalars(statement.order_by(EntityRow.id)))
    away = await away_among(ctx.session, [row.id for row in willing])
    fosterer = next((row for row in willing if row.id not in away), None)
    if fosterer is None:
        return False
    await foster(ctx.session, mortal.id, fosterer.id, ctx.epoch, description="taken in as a ward")
    await record(
        ctx,
        "kin.fostered",
        roles={IncidentRole.CHILD: mortal.id, IncidentRole.PARENT: fosterer.id},
        steps=(StepDraft(StepAction.FOSTER, actor=fosterer.id, target=mortal.id),),
    )
    return True


async def swear_kinship(ctx: TickContext, mortal: EntityRow) -> bool:
    for bond in await active_bonds(ctx.session, [BondKind.COMPANION], sources=[mortal.id]):
        friend = await living_entity(ctx.session, bond.target_node_id)
        if friend is None or friend.entity_type is not EntityType.MORTAL:
            continue
        if await active_bonds(ctx.session, [BondKind.SWORN_KIN], sources=[mortal.id], targets=[friend.id]):
            continue
        view = await opinion(ctx.session, ctx.rules, ctx.epoch, mortal.id, friend.id)
        if view.components[OpinionComponent.AFFECTION] <= 0 or not ctx.rng(seed_of("sworn", mortal.id, friend.id, ctx.epoch)).chance(
            ctx.rules.kinship.sworn_kin_chance
        ):
            continue
        await connect(ctx.session, mortal.id, friend.id, BondKind.SWORN_KIN, ctx.epoch, description="sworn kinship")
        await swear(ctx, mortal, OathKind.SWORN_KINSHIP, recipient_id=friend.id, note_text="sworn kin")
        await record(
            ctx,
            "kin.sworn",
            roles={IncidentRole.ACTOR: mortal.id, IncidentRole.CO_ACTOR: friend.id},
            facts={"affection": view.components[OpinionComponent.AFFECTION]},
            steps=(StepDraft(StepAction.SWEAR, actor=mortal.id, target=friend.id),),
        )
        return True
    return False
