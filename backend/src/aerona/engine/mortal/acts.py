from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.mind import CAREER_SKILLS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mind import MemoryKind, NeedKind, OpinionComponent, TraitKind, ValueAxis
from aerona.domain.enums.mortal import Ability, CareerPath, CrimeKind, DeathCause, LifeStage, StressBreak
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.book import perception_of
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import is_locked, mind_of, needs_of, traits_of, values_for
from aerona.engine.mind.memories import remember, strength_of
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.space import value_alignment
from aerona.engine.mind.values import liege_of
from aerona.engine.mortal.justice import code_punishment, sentence
from aerona.engine.mortal.life import ability
from aerona.engine.mortal.profile import is_held
from aerona.engine.mortal.standing import add_renown, add_wealth
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.services.war import ongoing_wars

GRATEFUL = (MemoryKind.SAVED_ME, MemoryKind.GIFTED_ME, MemoryKind.TAUGHT_ME, MemoryKind.FREED_US)
SCHEMERS = frozenset({TraitKind.AMBITIOUS, TraitKind.DECEITFUL})
BREAK_TRAITS: dict[StressBreak, frozenset[TraitKind]] = {
    StressBreak.RAGE: frozenset({TraitKind.WRATHFUL, TraitKind.CRUEL, TraitKind.RECKLESS, TraitKind.VENGEFUL}),
    StressBreak.FLIGHT: frozenset({TraitKind.CRAVEN, TraitKind.FICKLE, TraitKind.PARANOID}),
    StressBreak.DESPAIR: frozenset({TraitKind.MELANCHOLIC, TraitKind.RECLUSIVE}),
    StressBreak.ZEAL: frozenset({TraitKind.ZEALOUS, TraitKind.ASCETIC, TraitKind.IMPRESSIONABLE}),
    StressBreak.VICE: frozenset({TraitKind.GLUTTONOUS, TraitKind.LUSTFUL, TraitKind.GREEDY}),
    StressBreak.REVELATION: frozenset({TraitKind.CURIOUS, TraitKind.SCHOLARLY}),
}
FIGHTERS = frozenset({MortalRole.WARRIOR, MortalRole.KNIGHT, MortalRole.CAPTAIN})
CAREER_ROLES: dict[CareerPath, MortalRole] = {
    CareerPath.ARMY: MortalRole.WARRIOR,
    CareerPath.OFFICE: MortalRole.SCRIBE,
    CareerPath.APPRENTICE: MortalRole.APPRENTICE,
    CareerPath.VOWS: MortalRole.PRIEST,
    CareerPath.TRADE: MortalRole.MERCHANT,
    CareerPath.WANDER: MortalRole.EXPLORER,
    CareerPath.BANDIT: MortalRole.BANDIT,
}
CAREER_TRAITS: dict[CareerPath, frozenset[TraitKind]] = {
    CareerPath.ARMY: frozenset({TraitKind.BRAVE, TraitKind.WRATHFUL, TraitKind.RECKLESS, TraitKind.CUNNING_TACTICIAN}),
    CareerPath.OFFICE: frozenset({TraitKind.AMBITIOUS, TraitKind.JUST, TraitKind.PROUD}),
    CareerPath.APPRENTICE: frozenset({TraitKind.PATIENT, TraitKind.HUMBLE, TraitKind.CURIOUS}),
    CareerPath.VOWS: frozenset({TraitKind.ZEALOUS, TraitKind.ASCETIC, TraitKind.CHASTE}),
    CareerPath.TRADE: frozenset({TraitKind.GREEDY, TraitKind.GREGARIOUS, TraitKind.DECEITFUL}),
    CareerPath.WANDER: frozenset({TraitKind.CURIOUS, TraitKind.RECKLESS, TraitKind.FICKLE}),
    CareerPath.BANDIT: frozenset({TraitKind.CRUEL, TraitKind.GREEDY, TraitKind.DECEITFUL}),
}
CAREER_VALUES: dict[CareerPath, ValueAxis] = {
    CareerPath.ARMY: ValueAxis.MARTIAL,
    CareerPath.OFFICE: ValueAxis.HIERARCHY,
    CareerPath.APPRENTICE: ValueAxis.TRADITION,
    CareerPath.VOWS: ValueAxis.PIETY,
    CareerPath.TRADE: ValueAxis.WEALTH,
    CareerPath.WANDER: ValueAxis.XENOPHILIA,
}
CAREER_NEEDS: dict[CareerPath, NeedKind] = {
    CareerPath.ARMY: NeedKind.STATUS,
    CareerPath.OFFICE: NeedKind.STATUS,
    CareerPath.APPRENTICE: NeedKind.PURPOSE,
    CareerPath.VOWS: NeedKind.FAITH,
    CareerPath.TRADE: NeedKind.SUSTENANCE,
    CareerPath.WANDER: NeedKind.PURPOSE,
    CareerPath.BANDIT: NeedKind.SUSTENANCE,
}
OFFICE_CLASSES = frozenset({SocialClass.NOBLE, SocialClass.SCRIBE, SocialClass.PRIEST})
FULL = PERCENT


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
    if not ctx.rng(seed_of("convert", mortal.id, ctx.epoch)).chance(table.conversion_chance):
        return False
    for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[mortal.id]):
        await close(ctx.session, bond, ctx.epoch, "turned to another god")
    await connect(ctx.session, mortal.id, target.id, BondKind.WORSHIPS, ctx.epoch, description="converted")
    if not is_held(profile, "loyalty_god"):
        profile.loyalty_god = FULL // 2
    await note(
        ctx,
        f"{mortal.name} turned away from their old god to the faith of {community.name if community else 'their people'}.",
        key="mind.conversion",
        ids=[mortal.id],
    )
    return True


async def accumulate_stress(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> None:
    if is_held(profile, "stress"):
        return
    table = ctx.rules.stress
    needs = await needs_of(ctx.session, mortal.id)
    gain = sum(table.unmet_need_stress for value in needs.values() if value < table.unmet_need_below)
    if mortal.location_id is not None and await ongoing_wars(ctx.session, mortal.location_id):
        gain += table.war_stress
    if abs(profile.loyalty_liege - profile.loyalty_community) >= table.duty_gap:
        gain += table.duty_conflict_stress
    relief = 1 - (ability(mortal, Ability.WILLPOWER) - FULL // 2) / PERCENT * table.willpower_relief_pct / PERCENT
    profile.stress = clamp_int(profile.stress + gain * max(0.0, relief) - table.decay, 0, FULL)


def break_weights(rules_flight_pct: int, traits: set[TraitKind], profile: MortalProfileRow) -> dict[StressBreak, float]:
    weights = {kind: 1.0 + 3.0 * len(traits & matching) for kind, matching in BREAK_TRAITS.items()}
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


async def flee(ctx: TickContext, mortal: EntityRow) -> str:
    if mortal.mortal_role in FIGHTERS:
        mortal.mortal_role = MortalRole.COMMONER
        punishment = await code_punishment(ctx, mortal.location_id, CrimeKind.DESERTION)
        if ctx.rng(seed_of("desertion", mortal.id, ctx.epoch)).chance(ctx.rules.punishment.treason_chance):
            await sentence(ctx, mortal, CrimeKind.DESERTION, punishment)
        return "deserted"
    atlas = await RegionAtlas.load(ctx.session)
    home = atlas.top_region(mortal.id)
    options = [community for region in sorted(atlas.neighbour_regions(home)) for community in atlas.communities_in(region)] if home is not None else []
    if options:
        mortal.location_id = ctx.rng(seed_of("flight", mortal.id, ctx.epoch)).pick(options)
        return "fled their home"
    return "fled into the wilds"


async def rage(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    enemy = await worst_enemy(ctx, mortal)
    await gain_condition(ctx, mortal, ConditionKind.RAGE, HarmCause.ACCIDENT, severity=2)
    if enemy is None:
        return f"{mortal.name} broke under the strain and raged at the world."
    harm = Harm(ctx.rules.skills.spar_hp, HarmCause.DUEL, f"attacked by {mortal.name} in a rage", killer_id=mortal.id)
    await apply_hits(ctx, enemy, harm, lethal=False)
    return f"{mortal.name} broke under the strain and fell upon {enemy.name} in a rage."


async def flight(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    return f"{mortal.name} broke under the strain and {await flee(ctx, mortal)}."


async def despair(ctx: TickContext, mortal: EntityRow, rng: SeededRandom) -> bool:
    table = ctx.rules.stress
    await gain_condition(ctx, mortal, ConditionKind.MELANCHOLY, HarmCause.ACCIDENT, severity=2)
    if table.despair_suicide and rng.chance(table.despair_suicide_chance):
        await die(ctx, mortal, cause="took their own life in despair", manner=DeathCause.DESPAIR, forced=True)
        return True
    return False


async def sorrow(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    return f"{mortal.name} sank into despair."


async def zeal(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    community = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    cults = await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[community.id]) if community is not None else []
    for bond in cults:
        cult = await living_entity(ctx.session, bond.source_node_id)
        if cult is not None and cult.entity_type is EntityType.CULT:
            await connect(ctx.session, mortal.id, cult.id, BondKind.MEMBER_OF, ctx.epoch, description="sought refuge in zeal")
            break
    if not is_held(profile, "loyalty_god"):
        profile.loyalty_god = FULL
    return f"{mortal.name} broke under the strain and gave themself wholly to their faith."


async def vice(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    await gain_condition(ctx, mortal, ConditionKind.ADDICTION, HarmCause.ACCIDENT, severity=2)
    return f"{mortal.name} broke under the strain and fell into vice."


async def revelation(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, rng: SeededRandom) -> str:
    await gain_condition(ctx, mortal, ConditionKind.VISIONS, HarmCause.GOD, severity=1)
    seer = ctx.rules.stress.revelation_seer_chance * (1 + (ability(mortal, Ability.WISDOM) - FULL // 2) / PERCENT)
    if rng.chance(seer) and not await role_locked(ctx, mortal):
        mortal.mortal_role = MortalRole.SEER
    return f"{mortal.name} broke under the strain, and in the breaking saw visions."


BREAKS: dict[StressBreak, Callable[[TickContext, EntityRow, MortalProfileRow, SeededRandom], Awaitable[str]]] = {
    StressBreak.RAGE: rage,
    StressBreak.FLIGHT: flight,
    StressBreak.DESPAIR: sorrow,
    StressBreak.ZEAL: zeal,
    StressBreak.VICE: vice,
    StressBreak.REVELATION: revelation,
}


async def stress_break(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> StressBreak | None:
    table = ctx.rules.stress
    if profile.stress < table.break_threshold:
        return None
    traits = await traits_of(ctx.session, mortal.id)
    weights = break_weights(table.flight_chance_pct, traits, profile)
    rng = ctx.rng(seed_of("break", mortal.id, ctx.epoch))
    kind = rng.weighted(list(weights), list(weights.values()))
    if kind is StressBreak.DESPAIR and await despair(ctx, mortal, rng):
        return kind
    text = await BREAKS[kind](ctx, mortal, profile, rng)
    profile.stress = clamp_int(profile.stress - table.break_release, 0, FULL)
    profile.last_break = kind
    profile.last_break_epoch = ctx.epoch
    await note(ctx, text, key=f"stress.{kind.value}", ids=[mortal.id])
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
            text = f"{mortal.name} stood guard over {benefactor.name}, repaying an old debt."
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
            text = f"{mortal.name} sent gifts to {benefactor.name} in thanks."
        row.magnitude = max(0, row.magnitude // 2)
        await note(ctx, text, key="memory.gratitude", ids=[mortal.id, benefactor.id])
        return True
    return False


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
    cunning = ability(mortal, Ability.PERCEPTION) / 2 + (FULL // 4 if TraitKind.DECEITFUL in traits else 0)
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
        await note(ctx, f"{liege.name} uncovered a plot by {mortal.name}.", key="mind.plot_uncovered", ids=[mortal.id, liege.id])
        if rng.chance(ctx.rules.punishment.treason_chance):
            await sentence(ctx, mortal, CrimeKind.TREASON, await code_punishment(ctx, liege.location_id, CrimeKind.TREASON), judge=liege)
        return True
    await remember(
        ctx.session, ctx.rules, holder_id=liege.id, subject_id=mortal.id, kind=MemoryKind.BETRAYED_ME, magnitude=-table.plot_success_magnitude, epoch=ctx.epoch
    )
    await add_wealth(ctx.session, liege.id, -table.plot_wealth, ctx.epoch)
    await add_wealth(ctx.session, mortal.id, table.plot_wealth, ctx.epoch)
    await add_renown(ctx.session, mortal.id, table.plot_renown, ctx.epoch)
    await note(ctx, f"{mortal.name} plotted against {liege.name} and profited by it.", key="mind.plot", ids=[mortal.id, liege.id])
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
    open_paths = {CareerPath.STAY, CareerPath.TRADE, CareerPath.WANDER, CareerPath.VOWS}
    if mortal.location_id is not None and await ongoing_wars(ctx.session, mortal.location_id):
        open_paths.add(CareerPath.ARMY)
    if profile.polity_id is not None and mortal.social_class in OFFICE_CLASSES:
        empty = await ctx.session.scalar(
            select(OfficeRow.id).where(OfficeRow.polity_entity_id == profile.polity_id, OfficeRow.holder_entity_id.is_(None)).limit(1)
        )
        if empty is not None:
            open_paths.add(CareerPath.OFFICE)
    if profile.life_stage in (LifeStage.YOUTH, LifeStage.ADULT) and mortal.mortal_role is MortalRole.COMMONER:
        open_paths.add(CareerPath.APPRENTICE)
    table = ctx.rules.careers
    if profile.wealth < table.bandit_wealth_below and profile.honour < table.bandit_honour_below:
        open_paths.add(CareerPath.BANDIT)
    return open_paths


async def choose_path(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> CareerPath | None:
    table = ctx.rules.careers
    if is_held(profile, "career") or await role_locked(ctx, mortal) or profile.life_stage not in (LifeStage.YOUTH, LifeStage.ADULT):
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
        if path is CareerPath.STAY:
            scores[path] = table.stay_score + needs.get(NeedKind.PURPOSE, FULL // 2) / 4
            continue
        score = float(len(traits & CAREER_TRAITS.get(path, frozenset())) * table.trait_weight)
        score += await best_level(ctx, mortal.id, path) * table.skill_weight_pct / PERCENT
        axis = CAREER_VALUES.get(path)
        score += values.get(axis, 0) * table.values_weight_pct / PERCENT if axis is not None else 0
        need = CAREER_NEEDS.get(path)
        score += (FULL - needs.get(need, FULL)) * table.need_weight_pct / PERCENT if need is not None else 0
        scores[path] = score + rng.integer(0, table.switch_margin)
    if not scores:
        return None
    best = max(scores, key=lambda path: (scores[path], path.value))
    if best is CareerPath.STAY or best is profile.career:
        return None
    profile.career = best
    role = CAREER_ROLES[best]
    old = mortal.mortal_role
    mortal.mortal_role = role
    if best is CareerPath.VOWS:
        community = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
        patron = await living_patron(ctx.session, community) if community is not None else None
        if patron is not None and not await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[mortal.id], targets=[patron.id]):
            await connect(ctx.session, mortal.id, patron.id, BondKind.WORSHIPS, ctx.epoch, description="took vows")
    await note(
        ctx, f"{mortal.name} left the life of a {(old or MortalRole.COMMONER).value} to become a {role.value}.", key=f"career.{best.value}", ids=[mortal.id]
    )
    return best


async def ruler_favour(ctx: TickContext, ruler_id: int | None, mortal_id: int) -> float:
    if ruler_id is None:
        return 0.0
    rows = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == ruler_id, MemoryRow.subject_node_id == mortal_id, MemoryRow.kind == MemoryKind.GIFTED_ME)
    )
    return float(sum(strength_of(row, ctx.epoch) for row in rows))


async def bribe(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> bool:
    table = ctx.rules.standing
    if profile.career is not CareerPath.OFFICE or profile.wealth < table.bribe_cost or TraitKind.HONEST in await traits_of(ctx.session, mortal.id):
        return False
    liege = await liege_of(ctx.session, mortal)
    if liege is None:
        return False
    resolve = ability(liege, Ability.WILLPOWER)
    if ctx.rng(seed_of("bribe", mortal.id, ctx.epoch)).chance(resolve):
        return False
    await add_wealth(ctx.session, mortal.id, -table.bribe_cost, ctx.epoch)
    await add_wealth(ctx.session, liege.id, table.bribe_cost, ctx.epoch)
    await remember(ctx.session, ctx.rules, holder_id=liege.id, subject_id=mortal.id, kind=MemoryKind.GIFTED_ME, magnitude=table.bribe_effect, epoch=ctx.epoch)
    await note(ctx, f"{mortal.name} bought the favour of {liege.name} with gold.", key="standing.bribe", ids=[mortal.id, liege.id])
    return True
