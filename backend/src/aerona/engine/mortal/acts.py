from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.careers import CAREERS
from aerona.catalog.life.collective import CAREER_ROLES as ROLE_OF_CAREER
from aerona.catalog.life.mortal import (
    BREAK_TRAITS,
    CAREER_NEEDS,
    CAREER_ROLES,
    CAREER_TRAITS,
    CAREER_VALUES,
    CHOOSE_PATH_LIFE_STAGES,
    GRATEFUL,
    OPENINGS_CAREER_PATHS,
    OPENINGS_LIFE_STAGES_2,
)
from aerona.catalog.mind import CAREER_SKILLS, PROFESSIONS
from aerona.catalog.mind_split import BREAK_FACETS, STRESS_FACETS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.random import SeededRandom
from aerona.db.record_context import Term
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.mind import ActKind, Attribute, Facet, GratitudeDeed, MemoryKind, NeedKind, OpinionComponent, ThoughtKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CareerPath, CrimeKind, DeathCause, StressBreak
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.bands import banded
from aerona.engine.body.book import perception_of
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.collective.roles import breach_cost, career_open
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.folkways.biases import lean
from aerona.engine.genetics.life import madness_factor, stress_factor
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import is_locked, mind_of, needs_of, traits_of, values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember, strength_of
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.space import value_alignment
from aerona.engine.mind.split import facet_weight, facets_of, stored_attribute
from aerona.engine.mind.thoughts import need_importance, think
from aerona.engine.mind.values import liege_of
from aerona.engine.mortal.justice import code_punishment, community_ruler, sentence
from aerona.engine.mortal.paths import path_open, path_weight
from aerona.engine.mortal.profile import is_held
from aerona.engine.mortal.standing import add_renown, add_wealth
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.engine.recording.record import record as record_incident
from aerona.engine.relations.passions import invoke
from aerona.engine.services.war import ongoing_wars

SCHEMERS = frozenset({TraitKind.AMBITIOUS, TraitKind.DECEITFUL})
FIGHTERS = frozenset({MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.CAPTAIN, MortalRole.OFFICER})
OFFICE_CLASSES = frozenset({SocialClass.NOBLE, SocialClass.SCRIBE, SocialClass.PRIEST, SocialClass.OFFICIAL, SocialClass.PROFESSIONAL})
OFFICER_CLASSES = frozenset({SocialClass.NOBLE, SocialClass.OFFICIAL, SocialClass.PROFESSIONAL})
STUDY_ROLES = frozenset({MortalRole.SCIENTIST, MortalRole.ENGINEER, MortalRole.PILOT, MortalRole.PHYSICIAN, MortalRole.JOURNALIST})
FULL = PERCENT
PERSECUTION = "persecution"


@dataclass(frozen=True)
class Liege:
    entity: EntityRow | None
    polity_id: int | None


async def polity_of(ctx: TickContext, mortal: EntityRow) -> int | None:
    if mortal.location_id is None:
        return None
    found: int | None = await ctx.session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == mortal.location_id).limit(1)
    )
    return found


async def update_loyalty(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    table = ctx.rules.loyalty
    values = await values_for(ctx.session, mortal.id)
    needs = await needs_of(ctx.session, mortal.id)
    if not is_held(profile, "polity_id"):
        profile.polity_id = await polity_of(ctx, mortal)
    liege = await liege_of(ctx.session, mortal)
    rate = table.drift_pct / PERCENT
    if liege is not None and not is_held(profile, "loyalty_liege"):
        view = await opinion(ctx.session, ctx.rules, ctx.epoch, mortal.id, liege.id)
        bond = value_alignment(values, await values_for(ctx.session, liege.id)) * table.alignment_pct / PERCENT
        regard = (view.components[OpinionComponent.AFFECTION] + view.components[OpinionComponent.RESPECT] + view.components[OpinionComponent.TRUST]) / 3
        regard -= view.components[OpinionComponent.GRIEVANCE]
        target = FULL // 2 + bond + regard * table.opinion_pct / PERCENT + view.components[OpinionComponent.FEAR] * table.fear_pct / PERCENT
        profile.loyalty_liege = clamp_int(profile.loyalty_liege + (target - profile.loyalty_liege) * rate, 0, FULL)
    if mortal.location_id is not None and not is_held(profile, "loyalty_community"):
        bond = value_alignment(values, await values_for(ctx.session, mortal.location_id)) * table.alignment_pct / PERCENT
        target = FULL // 2 + bond + (needs.get(NeedKind.BELONGING, FULL // 2) - FULL // 2) * table.belonging_pct / PERCENT
        profile.loyalty_community = clamp_int(profile.loyalty_community + (target - profile.loyalty_community) * rate, 0, FULL)
    patron = await living_patron(ctx.session, mortal)
    if patron is not None and not is_held(profile, "loyalty_god"):
        bond = value_alignment(values, await values_for(ctx.session, patron.id)) * table.alignment_pct / PERCENT
        target = FULL // 2 + bond + (needs.get(NeedKind.FAITH, FULL // 2) - FULL // 2) * table.faith_pct / PERCENT
        profile.loyalty_god = clamp_int(profile.loyalty_god + (target - profile.loyalty_god) * rate, 0, FULL)


async def convert(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    table = ctx.rules.loyalty
    needs = await needs_of(ctx.session, mortal.id)
    if profile.loyalty_god >= table.conversion_below and needs.get(NeedKind.FAITH, FULL) >= table.faithless_need_below:
        return False
    community = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    target = await living_patron(ctx.session, community) if community is not None else None
    current = await living_patron(ctx.session, mortal)
    if target is None or (current is not None and current.id == target.id):
        return False
    atlas = await RegionAtlas.load(ctx.session)
    share = (await DominionBook.load(ctx.session)).share(atlas.top_region(mortal.id), target.id)
    if not ctx.rng(seed_of("convert", mortal.id, ctx.epoch)).chance(
        table.conversion_chance * (1 + share * ctx.rules.dominion.conversion_pct / PERCENT / PERCENT) * await lean(ctx, mortal.id, BiasedDecision.CONVERSION)
    ):
        return False
    for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[mortal.id]):
        await close(ctx.session, bond, ctx.epoch, "turned to another god")
    await connect(ctx.session, mortal.id, target.id, BondKind.WORSHIPS, ctx.epoch, description="converted")
    if current is not None:
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.LOST_FAITH, ctx.epoch, subject_id=current.id)
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FOUND_FAITH, ctx.epoch, subject_id=target.id)
    if not is_held(profile, "loyalty_god"):
        profile.loyalty_god = FULL // 2
    await record_incident(
        ctx,
        "mind.conversion",
        roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.PREDECESSOR: current.id if current is not None else None, IncidentRole.SUCCESSOR: target.id},
    )
    return True


async def accumulate_stress(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    if is_held(profile, "stress"):
        return
    table = ctx.rules.stress
    needs = await needs_of(ctx.session, mortal.id)
    facets = await facets_of(ctx.session, mortal.id)
    values = await values_for(ctx.session, mortal.id)
    weights = {need: need_importance(ctx.rules, need, facets, values) for need in needs}
    pressing = sum(weight for need, weight in weights.items() if needs[need] < table.unmet_need_below)
    gain = table.unmet_need_stress * ctx.rules.needs_depth.stress_breadth * pressing / max(1, sum(weights.values()))
    gain += max(0, -profile.mood_score) * ctx.rules.thoughts.mood_stress_pct / PERCENT
    if mortal.location_id is not None and await ongoing_wars(ctx.session, mortal.location_id):
        gain += table.war_stress
    if abs(profile.loyalty_liege - profile.loyalty_community) >= table.duty_gap:
        gain += table.duty_conflict_stress
    relief = 1 - (await stored_attribute(ctx.session, mortal, Attribute.WILLPOWER) - FULL // 2) / PERCENT * table.willpower_relief_pct / PERCENT
    fragility = 1 + facet_weight(facets, STRESS_FACETS) * ctx.rules.mind_split.stress_facet_pct / PERCENT
    rest = await ctx.hook_factor(mortal.id, DomainHook.REST)
    gain *= stress_factor(ctx.rules, await ctx.session.get(GenomeRow, mortal.id))
    profile.stress = clamp_int(profile.stress + gain * max(0.0, relief) * max(0.0, fragility) - table.decay * rest, 0, FULL)


def break_weights(
    rules_flight_pct: int, traits: set[TraitKind], profile: MortalProfileRow, facets: Mapping[Facet, int] | None = None, facet_pct: int = 0
) -> dict[StressBreak, float]:
    weights = {kind: 1.0 + 3.0 * len(traits & matching) for kind, matching in BREAK_TRAITS.items()}
    for kind, members in BREAK_FACETS.items():
        weights[kind] += max(0.0, facet_weight(facets or {}, dict.fromkeys(members, 1))) * facet_pct / PERCENT
    weights[StressBreak.FLIGHT] *= rules_flight_pct / PERCENT * (1 + (FULL - profile.loyalty_liege) / PERCENT)
    return weights


async def worst_enemy(ctx: TickContext, mortal: EntityRow) -> EntityRow | None:
    rows = list(await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.magnitude < 0)))
    rows.sort(key=lambda row: (strength_of(row, ctx.epoch), row.id))
    for row in rows:
        target = await living_entity(ctx.session, row.subject_node_id)
        if target is not None and target.entity_type is EntityType.MORTAL:
            return target
    return None


@dataclass(frozen=True)
class Broke:
    key: str
    roles: Mapping[IncidentRole, RoleValue] = field(default_factory=dict)
    facts: Mapping[str, FactInput] = field(default_factory=dict)


async def flee(ctx: TickContext, mortal: EntityRow) -> Broke:
    if mortal.mortal_role in FIGHTERS:
        mortal.mortal_role = MortalRole.COMMONER
        punishment = await code_punishment(ctx, mortal.location_id, CrimeKind.DESERTION)
        if ctx.rng(seed_of("desertion", mortal.id, ctx.epoch)).chance(ctx.rules.punishment.treason_chance):
            await sentence(ctx, mortal, CrimeKind.DESERTION, punishment)
        return Broke("stress.deserted", facts={"crime": CrimeKind.DESERTION})
    atlas = await RegionAtlas.load(ctx.session)
    home = atlas.top_region(mortal.id)
    options = [community for region in sorted(atlas.neighbour_regions(home)) for community in atlas.communities_in(region)] if home is not None else []
    if options:
        left = mortal.location_id
        mortal.location_id = ctx.rng(seed_of("flight", mortal.id, ctx.epoch)).pick(options)
        return Broke("stress.flight", {IncidentRole.ORIGIN: left, IncidentRole.DESTINATION: mortal.location_id})
    return Broke("stress.flight_wilds", {IncidentRole.ORIGIN: mortal.location_id})


BREAKS: Handlers[StressBreak, Callable[[TickContext, EntityRow, MortalProfileRow, SeededRandom], Awaitable[Broke]]] = Handlers(StressBreak)


@BREAKS.on(StressBreak.RAGE)
async def rage(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    enemy = await worst_enemy(ctx, mortal)
    await gain_condition(ctx, mortal, ConditionKind.RAGE, HarmCause.ACCIDENT, severity=banded(ctx, ctx.rules.harm_bands.rage, mortal.id))
    if enemy is None:
        return Broke("stress.rage")
    harm = Harm(ctx.rules.skills.spar_hp, HarmCause.DUEL, f"attacked by {mortal.name} in a rage", killer_id=mortal.id)
    await apply_hits(ctx, enemy, harm, lethal=False)
    return Broke("stress.rage_at", {IncidentRole.TARGET: enemy.id}, {"harm": ctx.rules.skills.spar_hp})


@BREAKS.on(StressBreak.FLIGHT)
async def flight(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    return await flee(ctx, mortal)


async def despair(ctx: TickContext, mortal: EntityRow, rng: SeededRandom) -> bool:
    table = ctx.rules.stress
    await gain_condition(ctx, mortal, ConditionKind.MELANCHOLY, HarmCause.ACCIDENT, severity=banded(ctx, ctx.rules.harm_bands.despair, mortal.id))
    if table.despair_suicide and rng.chance(table.despair_suicide_chance):
        await die(ctx, mortal, cause="took their own life in despair", manner=DeathCause.DESPAIR, forced=True)
        return True
    return False


@BREAKS.on(StressBreak.DESPAIR)
async def sorrow(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    return Broke("stress.despair", facts={"condition": ConditionKind.MELANCHOLY})


@BREAKS.on(StressBreak.ZEAL)
async def zeal(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    community = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    cults = await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[community.id]) if community is not None else []
    joined: int | None = None
    for bond in cults:
        cult = await living_entity(ctx.session, bond.source_node_id)
        if cult is not None and cult.entity_type is EntityType.CULT:
            await connect(ctx.session, mortal.id, cult.id, BondKind.MEMBER_OF, ctx.epoch, description="sought refuge in zeal")
            joined = cult.id
            break
    if not is_held(profile, "loyalty_god"):
        profile.loyalty_god = FULL
    return Broke("stress.zeal", {IncidentRole.HOST: joined}, {"loyalty_god": profile.loyalty_god})


@BREAKS.on(StressBreak.VICE)
async def vice(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    await afflict(ctx, mortal, PackageKind.DRINK_DEPENDENCE, Transmission.INGESTION)
    return Broke("stress.vice", facts={"package": PackageKind.DRINK_DEPENDENCE})


@BREAKS.on(StressBreak.WITHDRAWAL)
async def withdraw(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    left = 0
    for office in await ctx.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == mortal.id).order_by(OfficeRow.id)):
        if not held(office.polity_entity_id):
            office.holder_entity_id = None
            left += 1
    return Broke("stress.withdrawal", facts={"offices": left})


def withdrawn(ctx: TickContext, profile: MortalProfileRow) -> bool:
    return profile.last_break is StressBreak.WITHDRAWAL and profile.last_break_epoch is not None and profile.last_break_epoch >= 0


async def come_back(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, cared: bool) -> bool:
    table = ctx.rules.breaks
    if not withdrawn(ctx, profile) or profile.last_break_epoch is None:
        return False
    span = table.epochs(table.withdrawal_years) * (PERCENT - (table.withdrawal_care_cut if cared else 0)) / PERCENT
    if ctx.epoch - profile.last_break_epoch < span:
        profile.stress = clamp_int(profile.stress - table.withdrawal_ease, 0, FULL)
        return False
    profile.last_break_epoch = -1
    await record(ctx, "stress.withdrawal_ended", roles={IncidentRole.SUBJECT: mortal.id}, facts={"break": StressBreak.WITHDRAWAL, "stress": profile.stress})
    return True


@BREAKS.on(StressBreak.REVELATION)
async def revelation(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> Broke:
    await gain_condition(ctx, mortal, ConditionKind.VISIONS, HarmCause.GOD, severity=banded(ctx, ctx.rules.harm_bands.revelation, mortal.id))
    seer = ctx.rules.stress.revelation_seer_chance * (1 + (await stored_attribute(ctx.session, mortal, Attribute.INTUITION) - FULL // 2) / PERCENT)
    if rng.chance(seer) and not await role_locked(ctx, mortal):
        mortal.mortal_role = MortalRole.SEER
        return Broke("stress.revelation_seer", facts={"role": MortalRole.SEER})
    return Broke("stress.revelation", facts={"condition": ConditionKind.VISIONS})


async def stress_break(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> StressBreak | None:
    table = ctx.rules.stress
    strain = profile.stress + max(0, -profile.mood_score) * ctx.rules.thoughts.mood_break_pct / PERCENT
    strain -= profile.conviction * ctx.rules.aspirations.conviction_break_pct / PERCENT
    strain *= madness_factor(ctx.rules, await ctx.session.get(GenomeRow, mortal.id))
    if strain < table.break_threshold:
        return None
    if await invoke(ctx, mortal, None) > 1:
        profile.stress = clamp_int(profile.stress - table.break_release, 0, FULL)
        return None
    traits = await traits_of(ctx.session, mortal.id)
    weights = break_weights(table.flight_chance_pct, traits, profile, await facets_of(ctx.session, mortal.id), ctx.rules.mind_split.break_facet_pct)
    rng = ctx.rng(seed_of("break", mortal.id, ctx.epoch))
    kind = rng.weighted(list(weights), list(weights.values()))
    if kind is StressBreak.DESPAIR and await despair(ctx, mortal, rng):
        return kind
    broke: Broke = await BREAKS[kind](ctx, mortal, profile, rng)
    profile.stress = clamp_int(profile.stress - table.break_release, 0, FULL)
    profile.last_break = kind
    profile.last_break_epoch = ctx.epoch
    await record(ctx, broke.key, roles={IncidentRole.SUBJECT: mortal.id, **broke.roles}, facts={"break": kind, "stress": profile.stress, **broke.facts})
    return kind


async def role_locked(ctx: TickContext, mortal: EntityRow) -> bool:
    return is_locked(await mind_of(ctx.session, mortal.id), "role")


async def repay(ctx: TickContext, mortal: EntityRow) -> bool:
    table = ctx.rules.acts
    rows = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind.in_(list(GRATEFUL))).order_by(MemoryRow.id))
    for row in rows:
        if strength_of(row, ctx.epoch) < table.gratitude_threshold:
            continue
        benefactor = await living_entity(ctx.session, row.subject_node_id)
        if benefactor is None or benefactor.entity_type is not EntityType.MORTAL:
            continue
        if not ctx.rng(seed_of("gratitude", row.id, ctx.epoch)).chance(table.gratitude_chance):
            continue
        endangered = benefactor.location_id is not None and bool(await ongoing_wars(ctx.session, benefactor.location_id))
        if endangered:
            await connect(ctx.session, mortal.id, benefactor.id, BondKind.PROTECTS, ctx.epoch, description="repaying a debt of gratitude")
            deed = GratitudeDeed.GUARDED
        else:
            await add_wealth(ctx.session, mortal.id, -table.gift_wealth, ctx.epoch)
            await add_wealth(ctx.session, benefactor.id, table.gift_wealth, ctx.epoch)
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=benefactor.id,
                subject_id=mortal.id,
                kind=MemoryKind.GIFTED_ME,
                magnitude=table.gift_magnitude,
                epoch=ctx.epoch,
            )
            deed = GratitudeDeed.GIFTED
        row.magnitude = max(0, row.magnitude // 2)
        await record_incident(
            ctx,
            "memory.gratitude",
            roles={IncidentRole.ACTOR: mortal.id, IncidentRole.BENEFICIARY: benefactor.id},
            facts={"deed": deed, "wealth": 0 if endangered else table.gift_wealth},
        )
        return True
    return False


async def blasphemy(ctx: TickContext, mortal: EntityRow) -> bool:
    if mortal.location_id is None:
        return False
    level = await law_param(ctx.session, mortal.location_id, LawKind.RELIGIOUS_TOLERANCE, "level")
    if level != PERSECUTION:
        return False
    community = await living_entity(ctx.session, mortal.location_id)
    state_god = await living_patron(ctx.session, community) if community is not None else None
    own = await living_patron(ctx.session, mortal)
    if state_god is None or own is None or own.id == state_god.id:
        return False
    if not ctx.rng(seed_of("blasphemy", mortal.id, ctx.epoch)).chance(ctx.rules.punishment.blasphemy_chance):
        return False
    judge = await community_ruler(ctx.session, mortal.location_id)
    return await sentence(ctx, mortal, CrimeKind.BLASPHEMY, await code_punishment(ctx, mortal.location_id, CrimeKind.BLASPHEMY), judge=judge)


async def plot(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    table = ctx.rules.acts
    traits = await traits_of(ctx.session, mortal.id)
    if not traits & SCHEMERS or profile.loyalty_liege >= table.plot_loyalty_below:
        return False
    liege = await liege_of(ctx.session, mortal)
    if liege is None:
        return False
    view = await opinion(ctx.session, ctx.rules, ctx.epoch, mortal.id, liege.id)
    if view.components[OpinionComponent.GRIEVANCE] < table.plot_grievance:
        return False
    rng = ctx.rng(seed_of("plot", mortal.id, ctx.epoch))
    if not rng.chance(table.plot_chance):
        return False
    watch = await perception_of(ctx.session, ctx.rules, liege) * table.plot_discovery_pct / PERCENT
    cunning = await stored_attribute(ctx.session, mortal, Attribute.SOCIAL_AWARENESS) / 2 + (FULL // 4 if TraitKind.DECEITFUL in traits else 0)
    if rng.chance(max(0.0, min(float(FULL), watch - cunning + FULL // 2))):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=liege.id,
            subject_id=mortal.id,
            kind=MemoryKind.BETRAYED_ME,
            magnitude=-table.plot_success_magnitude,
            epoch=ctx.epoch,
        )
        await record_incident(ctx, "mind.plot_uncovered", roles={IncidentRole.ACCUSER: liege.id, IncidentRole.ACCUSED: mortal.id})
        if rng.chance(ctx.rules.punishment.treason_chance):
            await sentence(ctx, mortal, CrimeKind.TREASON, await code_punishment(ctx, liege.location_id, CrimeKind.TREASON), judge=liege)
        return True
    await remember(
        ctx.session, ctx.rules, holder_id=liege.id, subject_id=mortal.id, kind=MemoryKind.BETRAYED_ME, magnitude=-table.plot_success_magnitude, epoch=ctx.epoch
    )
    await add_wealth(ctx.session, liege.id, -table.plot_wealth, ctx.epoch)
    await add_wealth(ctx.session, mortal.id, table.plot_wealth, ctx.epoch)
    await add_renown(ctx.session, mortal.id, table.plot_renown, ctx.epoch, rules=ctx.rules)
    await record_incident(
        ctx,
        "mind.plot",
        roles={IncidentRole.ACTOR: mortal.id, IncidentRole.VICTIM: liege.id},
        facts={"wealth": table.plot_wealth, "renown": table.plot_renown},
        terms=[Term("rules.acts.plot_wealth", table.plot_wealth), Term("rules.acts.plot_renown", table.plot_renown)],
    )
    return True


async def best_level(ctx: TickContext, mortal_id: int, path: CareerPath) -> int:
    role = CAREER_ROLES.get(path)
    wanted = list(CAREER_SKILLS.get(role, ())) if role is not None else []
    if not wanted:
        return 0
    found = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill.in_(wanted)).order_by(SkillRow.level.desc()).limit(1)
    )
    return int(found or 0)


async def openings(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> set[CareerPath]:
    open_paths = set(OPENINGS_CAREER_PATHS)
    if mortal.location_id is not None and await ongoing_wars(ctx.session, mortal.location_id):
        open_paths.add(CareerPath.ARMY)
    if profile.polity_id is not None and mortal.social_class in OFFICE_CLASSES:
        empty = await ctx.session.scalar(
            select(OfficeRow.id).where(OfficeRow.polity_entity_id == profile.polity_id, OfficeRow.holder_entity_id.is_(None)).limit(1)
        )
        if empty is not None:
            open_paths.add(CareerPath.OFFICE)
    if profile.life_stage in OPENINGS_LIFE_STAGES_2 and mortal.mortal_role is MortalRole.COMMONER:
        open_paths.add(CareerPath.APPRENTICE)
    table = ctx.rules.careers
    if profile.wealth < table.bandit_wealth_below and profile.honour < table.bandit_honour_below:
        open_paths.add(CareerPath.BANDIT)
    home = mortal.location_id
    if home is not None and (await known_levels(ctx.session, [home])).get(home, {}).get(KnowledgeBranch.WRITING, 0) >= table.study_level:
        open_paths.add(CareerPath.STUDY)
    for path, spec in CAREERS.items():
        if (spec.crews or spec.household or spec.frontier) and await path_open(ctx, mortal, spec):
            open_paths.add(path)
    return open_paths


def career_role(path: CareerPath, mortal: EntityRow, profile: MortalProfileRow) -> MortalRole:
    pulled = PROFESSIONS[profile.profession].role if profile.profession is not None else None
    if path is CareerPath.STUDY and pulled in STUDY_ROLES:
        return pulled
    if path is CareerPath.ARMY and mortal.social_class in OFFICER_CLASSES:
        return MortalRole.OFFICER
    if path is CareerPath.TRADE and mortal.social_class is SocialClass.PROFESSIONAL:
        return MortalRole.EXECUTIVE
    return CAREER_ROLES[path]


async def choose_path(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> CareerPath | None:
    table = ctx.rules.careers
    if is_held(profile, "career") or await role_locked(ctx, mortal) or profile.life_stage not in CHOOSE_PATH_LIFE_STAGES:
        return None
    if mortal.mortal_role in (MortalRole.RULER, MortalRole.CHOSEN, MortalRole.SAINT, MortalRole.HERO):
        return None
    rng = ctx.rng(seed_of("career_path", mortal.id, ctx.epoch))
    if not rng.chance(table.choice_chance):
        return None
    traits = await traits_of(ctx.session, mortal.id)
    values = await values_for(ctx.session, mortal.id)
    needs = await needs_of(ctx.session, mortal.id)
    scores: dict[CareerPath, float] = {}
    for path in sorted(await openings(ctx, mortal, profile)):
        if not await career_open(ctx.session, ctx.rules, mortal, path):
            continue
        if path is CareerPath.STAY:
            scores[path] = (table.stay_score + needs.get(NeedKind.PURPOSE, FULL // 2) / 4) * path_weight(ctx, path)
            continue
        score = float(len(traits & CAREER_TRAITS.get(path, frozenset())) * table.trait_weight)
        score += await best_level(ctx, mortal.id, path) * table.skill_weight_pct / PERCENT
        axis = CAREER_VALUES.get(path)
        score += values.get(axis, 0) * table.values_weight_pct / PERCENT if axis is not None else 0
        if profile.profession is not None and PROFESSIONS[profile.profession].role is CAREER_ROLES.get(path):
            score += ctx.rules.skills.profession_pull
        need = CAREER_NEEDS.get(path)
        score += (FULL - needs.get(need, FULL)) * table.need_weight_pct / PERCENT if need is not None else 0
        scores[path] = score * path_weight(ctx, path) + rng.integer(0, table.switch_margin)
    if not scores:
        return None
    best = max(scores, key=lambda path: (scores[path], path.value))
    if best is CareerPath.STAY or best is profile.career:
        return None
    profile.career = best
    shame = await breach_cost(ctx.session, mortal, ROLE_OF_CAREER[best]) if best in ROLE_OF_CAREER else 0
    if shame and "honour" not in profile.locked:
        profile.honour = max(0, profile.honour - shame * ctx.rules.role_norms.breach_stance_cost)
    role = career_role(best, mortal, profile)
    old = mortal.mortal_role
    mortal.mortal_role = role
    if best is CareerPath.VOWS:
        community = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
        patron = await living_patron(ctx.session, community) if community is not None else None
        if patron is not None and not await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[mortal.id], targets=[patron.id]):
            await connect(ctx.session, mortal.id, patron.id, BondKind.WORSHIPS, ctx.epoch, description="took vows")
    await record(
        ctx,
        f"career.{best.value}",
        roles={IncidentRole.SUBJECT: mortal.id},
        facts={"path": best, "before": old or MortalRole.COMMONER, "after": role},
    )
    return best


async def bribe(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    table = ctx.rules.standing
    if profile.career is not CareerPath.OFFICE or profile.wealth < table.bribe_cost or TraitKind.HONEST in await traits_of(ctx.session, mortal.id):
        return False
    liege = await liege_of(ctx.session, mortal)
    if liege is None:
        return False
    resolve = await stored_attribute(ctx.session, liege, Attribute.WILLPOWER)
    if ctx.rng(seed_of("bribe", mortal.id, ctx.epoch)).chance(resolve):
        return False
    await add_wealth(ctx.session, mortal.id, -table.bribe_cost, ctx.epoch)
    await add_wealth(ctx.session, liege.id, table.bribe_cost, ctx.epoch)
    await remember(ctx.session, ctx.rules, holder_id=liege.id, subject_id=mortal.id, kind=MemoryKind.GIFTED_ME, magnitude=table.bribe_effect, epoch=ctx.epoch)
    await record(
        ctx,
        "standing.bribe",
        roles={IncidentRole.GIVER: mortal.id, IncidentRole.RECEIVER: liege.id},
        facts={"amount": table.bribe_cost, "resolve": resolve},
        steps=(
            StepDraft(StepAction.PAY, actor=mortal.id, target=liege.id, amount=table.bribe_cost, unit=FactUnit.WEALTH_POINTS, outcome=StepOutcome.ACCEPTED),
        ),
    )
    await judged(ctx, mortal.id, liege.id, ActKind.BRIBERY)
    return True
