from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.aspirations import FEARS, FOCUSES, GOALS, PERKS, WANT_VALUES, WANTS
from aerona.catalog.conditions import OPEN_INJURY_STATES
from aerona.catalog.life.mind import GLORIOUS_SINCE_THOUGHT_KINDS
from aerona.catalog.life_traits import SKILL_KIND_TRAITS, having
from aerona.catalog.mind import SKILLS
from aerona.catalog.thoughts import THOUGHTS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.culture_kinds import AimKindRow, FearKindRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import FearRow, LifeDreamRow, MemoryRow, PerkRow, SkillRow, ThoughtRow, WantRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import HouseProfileRow, OathRow, OfficeRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.life_traits import SkillKindTrait
from aerona.domain.enums.mind import (
    DreamState,
    Facet,
    FearKind,
    FocusKind,
    LifeGoal,
    MemoryKind,
    NeedKind,
    PerkKind,
    SkillFamily,
    SkillKind,
    ThoughtKind,
    ValueAxis,
    ValueHolder,
    WantKind,
)
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.records import StepAction
from aerona.engine.context import TickContext
from aerona.engine.kinds.culture_life import aims_held, fears_held
from aerona.engine.mind.book import Values, is_locked, mind_of, needs_of, stored_values
from aerona.engine.mind.ethics import at_war
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import need_importance, think
from aerona.engine.mortal.kin import children_of, partners_of, spouses_of
from aerona.engine.mortal.life import adult
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

ASPIRATION_LOCK = "aspirations"
ASPIRATIONS_KEY = "aspirations"
FOCUS_FIELD = "focus"
CONVICTION_FIELD = "conviction"
MILESTONES = (33, 66, 100)
FACET_SPAN = 50
PLAIN_GRIP = 50
VALUE_SPAN = 100
FIGHTERS = frozenset(
    {MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.HERO, MortalRole.CAPTAIN, MortalRole.HUNTER, MortalRole.OFFICER, MortalRole.PILOT}
)
EYES = ("left_eye", "right_eye")
TRAVEL_SKILLS = having(SKILL_KIND_TRAITS, SkillKindTrait.TRAVEL_SKILLS)
CRAFT_SKILLS = frozenset(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.CRAFT)
LORE_SKILLS = frozenset(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.KNOWLEDGE)
HOLY_ROLES = {MortalRole.SAINT: PERCENT, MortalRole.PRIEST: 66, MortalRole.CHOSEN: 66, MortalRole.SEER: 50}
SERVING_ROLES = frozenset({MortalRole.PRIEST, MortalRole.CHOSEN, MortalRole.SAINT, MortalRole.SEER})
VICTORIES = (BondKind.KILLED, BondKind.BEAT)
HUNT_SKILLS = having(SKILL_KIND_TRAITS, SkillKindTrait.HUNT_SKILLS)


def score_goal(rules: Rules, goal: LifeGoal, values: Values, facets: dict[Facet, int]) -> float:
    spec = GOALS[goal]
    table = rules.aspirations
    from_beliefs = sum(values.get(axis, 0) / VALUE_SPAN * weight for axis, weight in spec.beliefs.items()) * table.belief_weight_pct / PERCENT
    from_facets = sum(facets.get(facet, 0) / FACET_SPAN * weight for facet, weight in spec.facets.items()) * table.facet_weight_pct / PERCENT
    return from_beliefs + from_facets


def aim_pull(rules: Rules, held_aim: tuple[int, AimKindRow], values: Values, needs: dict[NeedKind, int]) -> float:
    strength, aim = held_aim
    pull = aim.pull * strength / PERCENT * rules.kinds.aim_pull_pct / PERCENT
    if aim.value_axis is not None:
        pull += values.get(aim.value_axis, 0) / VALUE_SPAN * aim.value_weight * rules.aspirations.belief_weight_pct / PERCENT
    if aim.need is not None:
        pull += needs.get(aim.need, 0) / PERCENT * aim.pull
    return pull


async def grudge_target(session: AsyncSession, mortal_id: int) -> int | None:
    rows = await session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == mortal_id, MemoryRow.kind == MemoryKind.KILLED_KIN).order_by(MemoryRow.magnitude)
    )
    for row in rows:
        target = await living_entity(session, row.subject_node_id)
        if target is not None:
            return target.id
    return None


async def choose_goal(ctx: TickContext, mortal: EntityRow) -> tuple[LifeGoal, int | None]:
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    facets = await facets_of(ctx.session, mortal.id)
    rng = ctx.rng(seed_of("life_dream", mortal.id, ctx.epoch))
    jitter = ctx.rules.aspirations.dream_jitter
    grudge = await grudge_target(ctx.session, mortal.id)
    patron = await living_patron(ctx.session, mortal)
    scored = []
    aims = await aims_held(ctx.session, mortal)
    needs = await needs_of(ctx.session, mortal.id)
    for goal in LifeGoal:
        if (goal is LifeGoal.AVENGE_KIN and grudge is None) or (goal is LifeGoal.SERVE_A_GOD and patron is None):
            continue
        held_aim = aims.get(goal)
        drawn = aim_pull(ctx.rules, held_aim, values, needs) if held_aim is not None else 0.0
        scored.append((score_goal(ctx.rules, goal, values, facets) + drawn + rng.integer(-jitter, jitter), goal))
    chosen = max(scored, key=lambda item: (item[0], item[1].value))[1]
    target = grudge if chosen is LifeGoal.AVENGE_KIN else patron.id if chosen is LifeGoal.SERVE_A_GOD and patron is not None else None
    return chosen, target


async def best_level(session: AsyncSession, mortal_id: int, skills: frozenset[SkillKind]) -> int:
    rows = await session.scalars(select(SkillRow.level).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill.in_(list(skills))))
    return max(rows, default=0)


async def rules_over(session: AsyncSession, mortal_id: int) -> int:
    ruled = [await session.get(EntityRow, bond.target_node_id) for bond in await active_bonds(session, [BondKind.RULES], sources=[mortal_id])]
    if any(entity is not None and entity.entity_type is EntityType.POLITY for entity in ruled):
        return PERCENT
    if ruled:
        return 66
    office = await session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == mortal_id).limit(1))
    return 33 if office is not None else 0


def scaled(value: float, full: float) -> int:
    return clamp_int(value * PERCENT / max(1.0, full), 0, PERCENT)


@dataclass(frozen=True)
class Probe:
    ctx: TickContext
    mortal: EntityRow
    profile: MortalProfileRow
    target_id: int | None
    since: int

    @property
    def session(self) -> AsyncSession:
        return self.ctx.session

    @property
    def rules(self) -> Rules:
        return self.ctx.rules

    @property
    def home(self) -> list[int]:
        return [self.mortal.id, *([self.mortal.location_id] if self.mortal.location_id is not None else [])]


async def probe_of(ctx: TickContext, mortal: EntityRow, target_id: int | None, since: int) -> Probe:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    return Probe(ctx, mortal, profile, target_id, since)


async def gone(probe: Probe) -> bool:
    target = await probe.session.get(EntityRow, probe.target_id) if probe.target_id is not None else None
    return target is None or target.status is not EntityStatus.CANON


async def heads_house(probe: Probe) -> int:
    from_house = await probe.session.scalar(
        select(HouseProfileRow.house_entity_id)
        .where((HouseProfileRow.head_entity_id == probe.mortal.id) | (HouseProfileRow.founder_entity_id == probe.mortal.id))
        .limit(1)
    )
    return (
        PERCENT
        if from_house is not None
        else max(await rules_over(probe.session, probe.mortal.id) // 2, scaled(probe.profile.renown, probe.rules.aspirations.renown_full) // 2)
    )


async def craft_mastery(probe: Probe) -> int:
    return scaled(await best_level(probe.session, probe.mortal.id, CRAFT_SKILLS), probe.rules.aspirations.skill_full)


async def masterwork(probe: Probe) -> int:
    made = await probe.session.scalar(
        select(ThoughtRow.id).where(ThoughtRow.holder_node_id == probe.mortal.id, ThoughtRow.kind == ThoughtKind.MADE_MASTERWORK).limit(1)
    )
    return PERCENT if made is not None else min(66, await craft_mastery(probe))


async def worldly(probe: Probe) -> int:
    return (
        PERCENT
        if probe.mortal.mortal_role is MortalRole.EXPLORER
        else scaled(await best_level(probe.session, probe.mortal.id, TRAVEL_SKILLS), probe.rules.aspirations.skill_full)
    )


async def holiness(probe: Probe) -> int:
    return HOLY_ROLES.get(probe.mortal.mortal_role or MortalRole.COMMONER, 33 if await living_patron(probe.session, probe.mortal) else 0)


async def vengeance_done(probe: Probe) -> int:
    return PERCENT if await gone(probe) else 33


async def beast_slain(probe: Probe) -> int:
    won = await active_bonds(probe.session, list(VICTORIES), sources=[probe.mortal.id])
    beasts = [await probe.session.get(EntityRow, bond.target_node_id) for bond in won]
    if any(entity is not None and entity.entity_type in {EntityType.BEAST, EntityType.SPECIES} for entity in beasts):
        return PERCENT
    return min(66, scaled(await best_level(probe.session, probe.mortal.id, HUNT_SKILLS), probe.rules.aspirations.skill_full))


async def service(probe: Probe) -> int:
    patron = await living_patron(probe.session, probe.mortal)
    if patron is None:
        return 0
    return PERCENT if probe.mortal.mortal_role in SERVING_ROLES else 33


async def peace(probe: Probe) -> int:
    calm = not await at_war(probe.session, probe.home)
    return scaled(probe.ctx.epoch - probe.since if calm else 0, probe.rules.aspirations.peace_epochs)


async def love(probe: Probe) -> int:
    if await partners_of(probe.session, probe.mortal.id) or await spouses_of(probe.session, probe.mortal.id):
        return PERCENT
    return 33 if (await needs_of(probe.session, probe.mortal.id)).get(NeedKind.ROMANCE, 0) > PERCENT // 2 else 0


async def realm(probe: Probe) -> int:
    return await rules_over(probe.session, probe.mortal.id)


async def legend(probe: Probe) -> int:
    return scaled(probe.profile.renown, probe.rules.aspirations.renown_full)


async def family(probe: Probe) -> int:
    return scaled(len(await children_of(probe.session, probe.mortal.id)), probe.rules.aspirations.children_full)


async def riches(probe: Probe) -> int:
    return scaled(probe.profile.wealth, probe.rules.aspirations.wealth_full)


async def truth(probe: Probe) -> int:
    return scaled(await best_level(probe.session, probe.mortal.id, LORE_SKILLS), probe.rules.aspirations.skill_full)


MEASURES = {
    LifeGoal.RULE_A_REALM: realm,
    LifeGoal.FOUND_A_HOUSE: heads_house,
    LifeGoal.MASTER_A_CRAFT: craft_mastery,
    LifeGoal.CREATE_A_MASTERWORK: masterwork,
    LifeGoal.BECOME_A_LEGEND: legend,
    LifeGoal.RAISE_A_FAMILY: family,
    LifeGoal.SEE_THE_WORLD: worldly,
    LifeGoal.ACHIEVE_HOLINESS: holiness,
    LifeGoal.GAIN_WEALTH: riches,
    LifeGoal.AVENGE_KIN: vengeance_done,
    LifeGoal.KNOW_A_TRUTH: truth,
    LifeGoal.DEFEAT_A_BEAST: beast_slain,
    LifeGoal.SERVE_A_GOD: service,
    LifeGoal.LIVE_IN_PEACE: peace,
    LifeGoal.FIND_LOVE: love,
}


async def measure(ctx: TickContext, mortal: EntityRow, dream: LifeDreamRow) -> int:
    return await MEASURES[dream.goal](await probe_of(ctx, mortal, dream.target_node_id, dream.started_epoch))


async def impossible(ctx: TickContext, mortal: EntityRow, dream: LifeDreamRow) -> bool:
    if dream.goal is LifeGoal.SERVE_A_GOD:
        return await living_patron(ctx.session, mortal) is None
    if not GOALS[dream.goal].physical:
        return False
    maimed = await ctx.session.scalar(
        select(InjuryRow.id).where(
            InjuryRow.bearer_node_id == mortal.id, InjuryRow.part.in_(("left_hand", "right_hand", "left_arm", "right_arm")), InjuryRow.function_loss >= PERCENT
        )
    )
    return maimed is not None


@dataclass
class AspirationTally:
    dreams: int = 0
    milestones: int = 0
    fulfilled: int = 0
    shattered: int = 0
    wants: int = 0
    wants_met: int = 0
    fears: int = 0
    perks: int = 0
    journeys: int = 0


async def adopt(ctx: TickContext, mortal: EntityRow, existing: LifeDreamRow | None, exclude: LifeGoal | None = None) -> LifeDreamRow:
    goal, target = await choose_goal(ctx, mortal)
    if exclude is not None and goal is exclude:
        others = [item for item in LifeGoal if item is not exclude and item is not LifeGoal.AVENGE_KIN and item is not LifeGoal.SERVE_A_GOD]
        goal, target = ctx.rng(seed_of("redream", mortal.id, ctx.epoch)).pick(others), None
    if existing is None:
        existing = LifeDreamRow(
            holder_node_id=mortal.id, goal=goal, target_node_id=target, milestones=[], progress=0, state=DreamState.PURSUING, started_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(existing)
    else:
        existing.goal, existing.target_node_id, existing.milestones, existing.progress = goal, target, [], 0
        existing.state, existing.started_epoch, existing.ended_epoch = DreamState.PURSUING, ctx.epoch, None
    held_aim = (await aims_held(ctx.session, mortal)).get(goal)
    existing.aim_kind_id = held_aim[1].id if held_aim is not None else None
    await ctx.session.flush()
    return existing


async def gain_conviction(session: AsyncSession, rules: Rules, mortal_id: int, amount: float, epoch: int) -> None:
    profile, _ = await ensure_profile(session, mortal_id, epoch)
    if not is_held(profile, CONVICTION_FIELD):
        profile.conviction = clamp_int(profile.conviction + amount, 0, PERCENT)


async def pursue(ctx: TickContext, mortal: EntityRow, tally: AspirationTally) -> None:
    table = ctx.rules.aspirations
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    dream = await ctx.session.get(LifeDreamRow, mortal.id)
    if dream is None:
        if adult(profile.life_stage) and ctx.rng(seed_of("dream_up", mortal.id, ctx.epoch)).chance(table.dream_pct):
            await adopt(ctx, mortal, None)
            tally.dreams += 1
        return
    if dream.state is not DreamState.PURSUING or "progress" in (dream.locked or []):
        return
    progress = await measure(ctx, mortal, dream)
    reached = [mark for mark in MILESTONES if progress >= mark]
    fresh = [mark for mark in reached if mark not in dream.milestones]
    dream.milestones, dream.progress = sorted({*dream.milestones, *reached}), progress
    for _ in fresh:
        tally.milestones += 1
        await gain_conviction(ctx.session, ctx.rules, mortal.id, table.conviction_gain, ctx.epoch)
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.DREAM_PROGRESS, ctx.epoch, subject_id=dream.target_node_id)
    if progress >= PERCENT:
        dream.state, dream.ended_epoch = DreamState.FULFILLED, ctx.epoch
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.DREAM_FULFILLED, ctx.epoch, subject_id=dream.target_node_id)
        tally.fulfilled += 1
        return
    if not await impossible(ctx, mortal, dream):
        return
    tally.shattered += 1
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.DREAM_SHATTERED, ctx.epoch, subject_id=dream.target_node_id)
    facets = await facets_of(ctx.session, mortal.id)
    bounce = 1 + (facets.get(Facet.CHEERFULNESS, 0) + facets.get(Facet.PERSEVERANCE, 0)) / (2 * FACET_SPAN)
    if ctx.rng(seed_of("redream", mortal.id, ctx.epoch)).chance(table.redream_pct * bounce):
        await adopt(ctx, mortal, dream, exclude=dream.goal)
    else:
        dream.state, dream.ended_epoch = DreamState.FAILED, ctx.epoch


async def wed_since(probe: Probe) -> bool:
    return any(bond.epoch >= probe.since for bond in await active_bonds(probe.session, [BondKind.SPOUSE_OF], sources=[probe.mortal.id]))


async def in_office(probe: Probe) -> bool:
    return await rules_over(probe.session, probe.mortal.id) > 0


async def armed_well(probe: Probe) -> bool:
    return probe.profile.wealth >= PERCENT // 2 and probe.mortal.mortal_role in FIGHTERS


async def prayed_since(probe: Probe) -> bool:
    found = await probe.session.scalar(
        select(MessageRow.id)
        .where(MessageRow.sender_node_id == probe.mortal.id, MessageRow.intent == MessageIntent.PRAYER, MessageRow.epoch >= probe.since)
        .limit(1)
    )
    walked = await probe.session.scalar(
        select(OathRow.id)
        .where(
            OathRow.swearer_entity_id == probe.mortal.id,
            OathRow.kind == OathKind.PILGRIMAGE,
            OathRow.status == OathStatus.FULFILLED,
            OathRow.ended_epoch >= probe.since,
        )
        .limit(1)
    )
    return found is not None or walked is not None


async def learned_since(probe: Probe) -> bool:
    return (
        await probe.session.scalar(select(SkillRow.id).where(SkillRow.holder_node_id == probe.mortal.id, SkillRow.last_used_epoch > probe.since).limit(1))
        is not None
    )


async def enriched(probe: Probe) -> bool:
    return probe.profile.wealth >= probe.rules.aspirations.wealth_full // 2


async def child_since(probe: Probe) -> bool:
    return any(bond.epoch >= probe.since for bond in await active_bonds(probe.session, [BondKind.PARENT_OF], sources=[probe.mortal.id]))


async def travelled_since(probe: Probe) -> bool:
    if probe.target_id is not None and probe.mortal.location_id == probe.target_id:
        return True
    found = await probe.session.scalar(
        select(SkillRow.id)
        .where(SkillRow.holder_node_id == probe.mortal.id, SkillRow.skill.in_(list(TRAVEL_SKILLS)), SkillRow.last_used_epoch > probe.since)
        .limit(1)
    )
    return found is not None


async def glorious_since(probe: Probe) -> bool:
    found = await probe.session.scalar(
        select(ThoughtRow.id)
        .where(ThoughtRow.holder_node_id == probe.mortal.id, ThoughtRow.kind.in_(GLORIOUS_SINCE_THOUGHT_KINDS), ThoughtRow.epoch >= probe.since)
        .limit(1)
    )
    return found is not None


async def peaceful(probe: Probe) -> bool:
    return not await at_war(probe.session, probe.home)


async def taught(probe: Probe) -> bool:
    return bool(await active_bonds(probe.session, [BondKind.APPRENTICE_OF], sources=[probe.mortal.id]))


WANT_CHECKS = {
    WantKind.MARRY: wed_since,
    WantKind.GAIN_OFFICE: in_office,
    WantKind.FINE_WEAPON: armed_well,
    WantKind.VISIT_A_SHRINE: prayed_since,
    WantKind.LEARN_A_SKILL: learned_since,
    WantKind.GAIN_WEALTH: enriched,
    WantKind.HAVE_A_CHILD: child_since,
    WantKind.TRAVEL: travelled_since,
    WantKind.WIN_GLORY: glorious_since,
    WantKind.MAKE_PEACE: peaceful,
    WantKind.AVENGE: gone,
    WantKind.FIND_A_TEACHER: taught,
}


async def want_met(ctx: TickContext, mortal: EntityRow, want: WantRow) -> bool:
    return await WANT_CHECKS[want.kind](await probe_of(ctx, mortal, want.target_node_id, want.epoch))


async def wanted(ctx: TickContext, mortal: EntityRow) -> list[tuple[WantKind, int | None]]:
    table = ctx.rules.aspirations
    facets = await facets_of(ctx.session, mortal.id)
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    needs = await needs_of(ctx.session, mortal.id)
    pressing = sorted(
        (
            need
            for need, value in needs.items()
            if value < table.want_need_below and need_importance(ctx.rules, need, facets, values) >= ctx.rules.thoughts.need_felt_above_pct
        ),
        key=lambda need: (needs[need], need.value),
    )
    found: list[tuple[WantKind, int | None]] = []
    dream = await ctx.session.get(LifeDreamRow, mortal.id)
    if dream is not None and dream.goal is LifeGoal.AVENGE_KIN and dream.state is DreamState.PURSUING:
        found.append((WantKind.AVENGE, dream.target_node_id))
    for need in pressing:
        for kind, spec in WANTS.items():
            if need in spec.needs and kind not in {item[0] for item in found}:
                found.append((kind, None))
                break
    return found


async def refresh_wants(ctx: TickContext, mortal: EntityRow, tally: AspirationTally) -> None:
    table = ctx.rules.aspirations
    rows = list(await ctx.session.scalars(select(WantRow).where(WantRow.holder_node_id == mortal.id)))
    for row in rows:
        if row.fulfilled_epoch is not None:
            continue
        if await want_met(ctx, mortal, row):
            row.fulfilled_epoch = ctx.epoch
            tally.wants_met += 1
            await gain_conviction(ctx.session, ctx.rules, mortal.id, table.conviction_gain, ctx.epoch)
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.WANT_FULFILLED, ctx.epoch, subject_id=row.target_node_id)
        elif ctx.epoch - row.epoch >= table.want_epochs and "kind" not in (row.locked or []):
            await ctx.session.delete(row)
    await ctx.session.flush()
    open_rows = [row for row in await ctx.session.scalars(select(WantRow).where(WantRow.holder_node_id == mortal.id, WantRow.fulfilled_epoch.is_(None)))]
    have = {row.kind for row in open_rows}
    for kind, target in await wanted(ctx, mortal):
        if len(have) >= table.want_count:
            break
        if kind in have:
            continue
        ctx.session.add(WantRow(holder_node_id=mortal.id, kind=kind, target_node_id=target, epoch=ctx.epoch, locked=[]))
        have.add(kind)
        tally.wants += 1
    await ctx.session.flush()


async def open_wants(session: AsyncSession, mortal_id: int) -> set[WantKind]:
    return set(await session.scalars(select(WantRow.kind).where(WantRow.holder_node_id == mortal_id, WantRow.fulfilled_epoch.is_(None))))


def steered_values(rules: Rules, values: Mapping[ValueAxis, int], wants: set[WantKind]) -> Values:
    pushed = dict(values)
    for want in wants:
        for axis, weight in WANT_VALUES.get(want, {}).items():
            pushed[axis] = clamp_int(pushed.get(axis, 0) + weight * rules.aspirations.want_career_pct / PERCENT, -VALUE_SPAN, VALUE_SPAN)
    return pushed


async def seed_fears(ctx: TickContext, mortal: EntityRow) -> int:
    if await ctx.session.scalar(select(FearRow.id).where(FearRow.holder_node_id == mortal.id).limit(1)) is not None:
        return 0
    table = ctx.rules.aspirations
    facets = await facets_of(ctx.session, mortal.id)
    scores: dict[FearKind, float] = {
        kind: sum(facets.get(facet, 0) * weight for facet, weight in spec.facets.items()) / FACET_SPAN for kind, spec in FEARS.items()
    }
    if await children_of(ctx.session, mortal.id):
        scores[FearKind.LOSING_A_CHILD] += FACET_SPAN
    authored: dict[FearKind, int] = {}
    for holding, row in await fears_held(ctx.session, mortal):
        if row.facet is not None:
            scores[row.category] += facets.get(row.facet, 0) * row.facet_weight / FACET_SPAN * holding.strength / PERCENT
        authored.setdefault(row.category, row.id)
    ranked = [kind for kind, score in sorted(scores.items(), key=lambda item: (-item[1], item[0].value)) if score > 0][: table.fear_count]
    for kind in ranked:
        ctx.session.add(
            FearRow(
                holder_node_id=mortal.id,
                kind=kind,
                fear_kind_id=authored.get(kind),
                strength=table.fear_strength,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
    await ctx.session.flush()
    return len(ranked)


async def wounded(probe: Probe) -> bool:
    found = await probe.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id == probe.mortal.id, InjuryRow.state.in_(tuple(OPEN_INJURY_STATES))).limit(1)
    )
    return found is not None


async def warring(probe: Probe) -> bool:
    return await at_war(probe.session, probe.home)


async def region_of(probe: Probe) -> int | None:
    return (await RegionAtlas.load(probe.session)).top_region(probe.mortal.id)


async def plague_near(probe: Probe) -> bool:
    region = await region_of(probe)
    if region is None:
        return False
    found = await probe.session.scalar(
        select(OutbreakRow.id).where(OutbreakRow.region_entity_id == region, OutbreakRow.status != OutbreakStatus.ENDED).limit(1)
    )
    return found is not None


async def beasts_near(probe: Probe) -> bool:
    region = await region_of(probe)
    places = [place for place in (region, probe.mortal.location_id) if place is not None]
    if not places:
        return False
    found = await probe.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.BEAST, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(places))
        .limit(1)
    )
    return found is not None


async def child_in_danger(probe: Probe) -> bool:
    children = await children_of(probe.session, probe.mortal.id)
    if not children:
        return False
    sick = await probe.session.scalar(select(ConditionRow.id).where(ConditionRow.bearer_node_id.in_(children), ConditionRow.ended_epoch.is_(None)).limit(1))
    hurt = await probe.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id.in_(children), InjuryRow.state.in_(tuple(OPEN_INJURY_STATES))).limit(1)
    )
    return sick is not None or hurt is not None


async def poor(probe: Probe) -> bool:
    return probe.profile.wealth < probe.rules.aspirations.fear_poverty_below


async def disgraced(probe: Probe) -> bool:
    return probe.profile.infamy > probe.rules.aspirations.fear_shame_above


async def in_the_dark(probe: Probe) -> bool:
    sightless = await probe.session.scalar(
        select(ConditionRow.id)
        .where(ConditionRow.bearer_node_id == probe.mortal.id, ConditionRow.kind == ConditionKind.AGE_BLINDNESS, ConditionRow.ended_epoch.is_(None))
        .limit(1)
    )
    eyeless = await probe.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id == probe.mortal.id, InjuryRow.part.in_(EYES), InjuryRow.function_loss >= PERCENT).limit(1)
    )
    home = await region_of(probe)
    region = await probe.session.get(RegionEnvironmentRow, home) if home is not None else None
    buried = region is not None and region.dominant_terrain is TerrainKind.UNDERGROUND
    return sightless is not None or eyeless is not None or buried


FEAR_CHECKS = {
    FearKind.DEATH: wounded,
    FearKind.WAR: warring,
    FearKind.PLAGUE: plague_near,
    FearKind.BEASTS: beasts_near,
    FearKind.LOSING_A_CHILD: child_in_danger,
    FearKind.POVERTY: poor,
    FearKind.SHAME: disgraced,
    FearKind.DARK: in_the_dark,
}


async def fear_near(ctx: TickContext, mortal: EntityRow, kind: FearKind) -> bool:
    return await FEAR_CHECKS[kind](await probe_of(ctx, mortal, None, ctx.epoch))


async def feel_fears(ctx: TickContext, mortal: EntityRow, resolved: bool) -> int:
    if resolved:
        return 0
    felt = 0
    for row in list(await ctx.session.scalars(select(FearRow).where(FearRow.holder_node_id == mortal.id))):
        if await fear_near(ctx, mortal, row.kind):
            kind = await ctx.session.get(FearKindRow, row.fear_kind_id) if row.fear_kind_id is not None else None
            grip = (kind.grip if kind is not None else PLAIN_GRIP) / PLAIN_GRIP
            size = THOUGHTS[ThoughtKind.FEAR_NEAR].intensity * (PERCENT + row.strength) / (2 * PERCENT) * grip
            if await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FEAR_NEAR, ctx.epoch, subject_id=row.target_node_id, intensity=size):
                felt += 1
    return felt


FAMILY_FOCUS = {
    SkillFamily.COMBAT: FocusKind.MARTIAL,
    SkillFamily.COMMAND: FocusKind.MARTIAL,
    SkillFamily.SOCIAL: FocusKind.DIPLOMACY,
    SkillFamily.SURVIVAL: FocusKind.STEWARDSHIP,
    SkillFamily.KNOWLEDGE: FocusKind.LEARNING,
    SkillFamily.FAITH: FocusKind.PIETY,
    SkillFamily.CRAFT: FocusKind.CRAFT,
}
INTRIGUE_SKILLS = having(SKILL_KIND_TRAITS, SkillKindTrait.INTRIGUE_SKILLS)


async def focus_level(session: AsyncSession, mortal_id: int, focus: FocusKind) -> int:
    families = FOCUSES[focus].families
    if not families:
        return (await needs_of(session, mortal_id)).get(NeedKind.PLEASURE, 0)
    rows = await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == mortal_id))
    return max((row.level for row in rows if SKILLS[row.skill].family in families), default=0)


async def settle_focus(ctx: TickContext, mortal: EntityRow) -> FocusKind | None:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    if profile.focus is not None or is_held(profile, FOCUS_FIELD):
        return profile.focus
    best = await ctx.session.scalar(select(SkillRow).where(SkillRow.holder_node_id == mortal.id).order_by(SkillRow.level.desc(), SkillRow.id).limit(1))
    office = await rules_over(ctx.session, mortal.id)
    if best is None or (best.level < ctx.rules.aspirations.focus_skill and not office):
        if (await needs_of(ctx.session, mortal.id)).get(NeedKind.PLEASURE, 0) >= ctx.rules.aspirations.leisure_need:
            profile.focus = FocusKind.LEISURE
            return profile.focus
        return None
    profile.focus = FocusKind.INTRIGUE if best.skill in INTRIGUE_SKILLS else FAMILY_FOCUS[SKILLS[best.skill].family]
    return profile.focus


async def perk_modifier(session: AsyncSession, mortal_id: int, perk: PerkKind, epoch: int) -> None:
    spec = PERKS[perk]
    await add_modifier(
        session,
        ModifierDraft(
            target_node_id=mortal_id,
            target_key=spec.stat,
            op=ModifierOp.ADD,
            magnitude=spec.amount,
            source_kind=ModifierSource.PERK,
            reason_key=f"perk.{perk.value}",
            start_epoch=epoch,
            source_node_id=mortal_id,
            stacking_group=f"perk.{perk.value}",
        ),
    )


async def drop_perk(session: AsyncSession, mortal_id: int, perk: PerkKind) -> None:
    await session.execute(delete(PerkRow).where(PerkRow.holder_node_id == mortal_id, PerkRow.perk == perk))
    await session.execute(
        delete(ModifierRow).where(
            ModifierRow.target_node_id == mortal_id, ModifierRow.source_kind == ModifierSource.PERK, ModifierRow.reason_key == f"perk.{perk.value}"
        )
    )


async def grant_perks(ctx: TickContext, mortal: EntityRow, focus: FocusKind | None) -> int:
    held = set(await ctx.session.scalars(select(PerkRow.perk).where(PerkRow.holder_node_id == mortal.id)))
    for perk in held:
        if focus is None or PERKS[perk].focus is not focus:
            await drop_perk(ctx.session, mortal.id, perk)
    if focus is None:
        return 0
    level = await focus_level(ctx.session, mortal.id, focus)
    granted = 0
    for perk in FOCUSES[focus].perks:
        if perk in held or PERKS[perk].level > level:
            continue
        ctx.session.add(PerkRow(holder_node_id=mortal.id, perk=perk, epoch=ctx.epoch))
        await perk_modifier(ctx.session, mortal.id, perk, ctx.epoch)
        granted += 1
    await ctx.session.flush()
    return granted


async def focus_rate(session: AsyncSession, rules: Rules, mortal_id: int, skill: SkillKind) -> float:
    profile = await session.get(MortalProfileRow, mortal_id)
    if profile is None or profile.focus is None or SKILLS[skill].family not in FOCUSES[profile.focus].families:
        return 1.0
    return 1 + rules.aspirations.focus_learning_pct / PERCENT


async def set_out(ctx: TickContext, mortal: EntityRow) -> bool:
    want = await ctx.session.scalar(
        select(WantRow).where(WantRow.holder_node_id == mortal.id, WantRow.kind == WantKind.TRAVEL, WantRow.fulfilled_epoch.is_(None)).limit(1)
    )
    if want is None or not ctx.rng(seed_of("wanderlust", mortal.id, ctx.epoch)).chance(ctx.rules.aspirations.want_travel_pct):
        return False
    atlas = await RegionAtlas.load(ctx.session)
    home = atlas.top_region(mortal.id)
    options = (
        [community for region in sorted(atlas.neighbour_regions(home)) for community in atlas.communities_in(region) if community != mortal.location_id]
        if home is not None
        else []
    )
    if not options:
        return False
    mortal.location_id = want.target_node_id = ctx.rng(seed_of("journey", mortal.id, ctx.epoch)).pick(options)
    await record(
        ctx,
        "aspiration.journey",
        roles={IncidentRole.ACTOR: mortal.id, IncidentRole.DESTINATION: mortal.location_id},
        steps=(StepDraft(StepAction.DEPART, actor=mortal.id), StepDraft(StepAction.ARRIVE, actor=mortal.id, target=mortal.location_id)),
        place=mortal.location_id,
    )
    return True


async def aspire(ctx: TickContext, mortal: EntityRow, tally: AspirationTally, *, resolved: bool) -> None:
    if is_locked(await mind_of(ctx.session, mortal.id), ASPIRATION_LOCK) or write_blocked(mortal.id, ASPIRATIONS_KEY):
        return
    await pursue(ctx, mortal, tally)
    await refresh_wants(ctx, mortal, tally)
    tally.journeys += await set_out(ctx, mortal)
    tally.fears += await seed_fears(ctx, mortal)
    await feel_fears(ctx, mortal, resolved)
    tally.perks += await grant_perks(ctx, mortal, await settle_focus(ctx, mortal))
