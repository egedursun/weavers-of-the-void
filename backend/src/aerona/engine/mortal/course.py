from sqlalchemy import select

from aerona.catalog.mind import CAREER_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import OPEN_INJURY_STATES, ConditionKind, HarmCause, InjuryState
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import MemoryKind, OpinionComponent, SkillKind, SkillSource, ValueHolder, WantKind
from aerona.domain.enums.mortal import Ability, DeathCause, LifeStage, MarriageEnd, MarriageKind
from aerona.domain.enums.polity import LawKind, OathKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.aspirations import open_wants
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.memories import strength_of
from aerona.engine.mind.needs import role_status
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.skills import practise
from aerona.engine.mind.space import blend
from aerona.engine.mortal.death import HARM_DEATHS
from aerona.engine.mortal.kin import betrothed_of, children_of, parents_of, partners_of, siblings_of
from aerona.engine.mortal.kinship import betroth, end_marriage, foster, marriage_between, marriages_of, marry
from aerona.engine.mortal.life import ability, adult, assign_sex, refresh_life, seed_abilities, stage_rank
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.mortal.standing import add_renown
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.oaths import swear
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, connect, living_entity
from aerona.engine.primitives.stats import set_stats, stat

ROLE_CLASSES: dict[MortalRole, SocialClass] = {
    MortalRole.RULER: SocialClass.NOBLE,
    MortalRole.KNIGHT: SocialClass.NOBLE,
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
PLURAL_CUSTOMS = ("polygyny", "polyandry", "group")
STANDING_FIXUP = "mortal.standing_backfill"
DEATH_FIXUP = "mortal.death_causes"
FULL = PERCENT


def class_for(mortal: EntityRow) -> SocialClass:
    return ROLE_CLASSES.get(mortal.mortal_role or MortalRole.COMMONER, SocialClass.FARMER)


async def heritage_class(ctx: TickContext, mortal: EntityRow) -> SocialClass:
    for parent_id in await parents_of(ctx.session, mortal.id):
        parent = await ctx.session.get(EntityRow, parent_id)
        if parent is not None and parent.social_class is not None:
            return parent.social_class
    return class_for(mortal)


async def seed_mortal(ctx: TickContext, mortal: EntityRow) -> bool:
    profile, created = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    abilities = seed_abilities(ctx.rules, mortal, ctx.rng(seed_of("abilities", mortal.id)))
    if abilities:
        set_stats(mortal, **abilities)
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
        dread = sum(-strength_of(row, ctx.epoch) for row in rows if row.kind in (MemoryKind.MAIMED_ME, MemoryKind.KILLED_KIN, MemoryKind.HARMED_ME))
        profile.infamy = clamp_int(dread * table.infamy_atrocity / PERCENT, 0, FULL)


async def active_flags(ctx: TickContext, mortal_id: int) -> set[EntityFlag]:
    return await EntityRepository(ctx.session).flags(mortal_id)


async def backfill_deaths(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, DEATH_FIXUP) is not None:
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
        grown = {key: clamp_int((stat(mortal, key) or FULL // 2) + table.youth_growth, 0, FULL) for key in ("strength", "agility", "endurance")}
        set_stats(mortal, **grown)
    if stage in (LifeStage.ELDER, LifeStage.ANCIENT):
        set_stats(
            mortal,
            strength=clamp_int((stat(mortal, "strength") or FULL // 2) - table.elder_strength_decline, 0, FULL),
            agility=clamp_int((stat(mortal, "agility") or FULL // 2) - table.elder_agility_decline, 0, FULL),
            endurance=clamp_int(ability(mortal, Ability.ENDURANCE) - table.elder_endurance_decline, 0, FULL),
            wisdom=clamp_int(ability(mortal, Ability.WISDOM) + table.elder_wisdom_gain, 0, FULL),
        )
        rng = ctx.rng(seed_of("age_condition", mortal.id, ctx.epoch))
        if rng.chance(table.age_condition_chance):
            kind = rng.pick((ConditionKind.AGE_BLINDNESS, ConditionKind.AGE_DEAFNESS, ConditionKind.CHRONIC_ILLNESS))
            await gain_condition(ctx, mortal, kind, HarmCause.AGE, severity=1)
    await update_health(ctx, mortal, profile, stage)
    if stage is not before and stage_rank(stage) > stage_rank(before) and stage in (LifeStage.ADULT, LifeStage.ELDER):
        await note(ctx, f"{mortal.name} came into {'adulthood' if stage is LifeStage.ADULT else 'old age'}.", key=f"life.{stage.value}", ids=[mortal.id])
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
    loss += table.ancient_health_loss if stage is LifeStage.ANCIENT else table.elder_health_loss if stage is LifeStage.ELDER else 0
    gain = table.health_recovery * (1 + (ability(mortal, Ability.ENDURANCE) - FULL // 2) / PERCENT) if stage not in (LifeStage.ELDER, LifeStage.ANCIENT) else 0
    profile.health = clamp_int(profile.health + gain - loss, 0, FULL)


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
    if profile.life_stage not in (LifeStage.CHILD, LifeStage.YOUTH):
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
    if not ctx.rng(seed_of("patronage", mortal.id, ctx.epoch)).chance(ability(mortal, Ability.CREATIVITY)):
        return False
    authors = select(EntityRow.id).where(EntityRow.location_id == mortal.location_id, EntityRow.entity_type == EntityType.MORTAL)
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
    await note(
        ctx,
        f"{mortal.name} became the patron of {artwork.name if artwork else 'a work of art'}.",
        key="standing.patronage",
        ids=[mortal.id, work.artwork_entity_id],
    )
    return True


async def marriage_wish(ctx: TickContext, mortal: EntityRow) -> float:
    return 1 + ctx.rules.aspirations.want_match_pct / PERCENT if WantKind.MARRY in await open_wants(ctx.session, mortal.id) else 1.0


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
            and rng.chance(table.marriage_chance * await marriage_wish(ctx, mortal))
        ):
            await marry(ctx.session, mortal, partner, ctx.epoch, kind=MarriageKind.POLITICAL, description="as they were promised")
            await note(ctx, f"{mortal.name} and {partner.name} were wed as they had been promised.", key="kin.marriage", ids=[mortal.id, partner.id])
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
        if (married and not plural) or not rng.chance(table.marriage_chance * await marriage_wish(ctx, mortal)):
            continue
        await marry(ctx.session, mortal, lover, ctx.epoch, kind=MarriageKind.PLURAL if married else MarriageKind.MONOGAMOUS, description="for love")
        await note(ctx, f"{mortal.name} and {lover.name} were wed.", key="kin.marriage", ids=[mortal.id, lover.id])
        return "married"
    custom = await divorce_custom(ctx, mortal)
    for row in await marriages_of(ctx.session, mortal.id, ended=False):
        spouse_id = row.second_id if row.first_id == mortal.id else row.first_id
        view = await opinion(ctx.session, ctx.rules, ctx.epoch, mortal.id, spouse_id)
        if custom != "forbidden" and view.value < table.divorce_opinion_below and rng.chance(table.divorce_chance * (2 if custom == "free" else 1)):
            await end_marriage(ctx.session, row, ctx.epoch, MarriageEnd.DIVORCE)
            spouse = await ctx.session.get(EntityRow, spouse_id)
            await note(ctx, f"{mortal.name} and {spouse.name if spouse else 'their spouse'} parted.", key="kin.divorce", ids=[mortal.id, spouse_id])
            return "divorced"
    return None


async def divorce_custom(ctx: TickContext, mortal: EntityRow) -> str:
    found = await law_param(ctx.session, mortal.location_id, LawKind.MARRIAGE_LAW, "divorce") if mortal.location_id is not None else None
    return str(found) if found is not None else "for_cause"


async def plural_custom(ctx: TickContext, mortal: EntityRow) -> bool:
    people = await people_of(ctx.session, mortal)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture is not None and culture.marriage.value in PLURAL_CUSTOMS


async def betroth_children(ctx: TickContext, mortal: EntityRow) -> bool:
    if mortal.social_class is not SocialClass.NOBLE or not ctx.rng(seed_of("betroth", mortal.id, ctx.epoch)).chance(ctx.rules.kinship.betrothal_chance):
        return False
    for child_id in await children_of(ctx.session, mortal.id):
        child = await living_entity(ctx.session, child_id)
        child_profile = await ctx.session.get(MortalProfileRow, child_id)
        if child is None or child_profile is None or adult(child_profile.life_stage) or await betrothed_of(ctx.session, child_id):
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
                MortalProfileRow.life_stage.in_([LifeStage.CHILD, LifeStage.YOUTH]),
            )
            .order_by(EntityRow.id)
        )
        kin = {child.id, *await siblings_of(ctx.session, child.id)}
        for other in await ctx.session.scalars(statement):
            if other.id in kin or await betrothed_of(ctx.session, other.id):
                continue
            await betroth(ctx.session, child, other, ctx.epoch, description="promised by their families")
            await note(ctx, f"{child.name} was promised to {other.name}.", key="kin.betrothal", ids=[child.id, other.id])
            return True
    return False


async def foster_orphan(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    if adult(profile.life_stage) or mortal.location_id is None:
        return False
    parents = [await living_entity(ctx.session, parent) for parent in await parents_of(ctx.session, mortal.id)]
    if any(parent is not None for parent in parents) or not ctx.rng(seed_of("foster", mortal.id, ctx.epoch)).chance(ctx.rules.kinship.foster_chance):
        return False
    statement = select(EntityRow).where(
        EntityRow.location_id == mortal.location_id,
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.id != mortal.id,
        EntityRow.social_class == SocialClass.NOBLE,
    )
    fosterer = next(iter(unheld(await ctx.session.scalars(statement.order_by(EntityRow.id)))), None)
    if fosterer is None:
        return False
    await foster(ctx.session, mortal.id, fosterer.id, ctx.epoch, description="taken in as a ward")
    await note(ctx, f"The orphaned {mortal.name} was taken in as a ward by {fosterer.name}.", key="kin.fostered", ids=[mortal.id, fosterer.id])
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
        await connect(ctx.session, mortal.id, friend.id, BondKind.SWORN_KIN, ctx.epoch, description="blood brotherhood")
        await swear(ctx, mortal, OathKind.BLOOD_BROTHERHOOD, recipient_id=friend.id, note_text="sworn kin")
        await note(ctx, f"{mortal.name} and {friend.name} swore themselves kin by blood.", key="kin.sworn", ids=[mortal.id, friend.id])
        return True
    return False
