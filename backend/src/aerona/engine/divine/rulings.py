from collections import Counter
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from aerona.catalog.life.divine import LEANING_COUNCIL_MOTIONS, MOTION_LABELS, PENANCE_DEEDS, PUNISHMENTS, RULING_LASTING
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.repositories.sons import COUNCIL_SEATING, SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.divine import CouncilRulingRow, GodGoalRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow, GodConflictRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import CouncilRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import CouncilCaller, CouncilVote
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import CouncilMotion, GoalState, PenanceDeed, SonPunishment
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mythic import OfficeChoice
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.domain.models.records import CouncilBallot, CouncilMinutes
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.cosmos.worlds import declare_holy_world
from aerona.engine.divine.council_order import (
    ORDER_ENACTMENTS,
    ORDER_LASTING,
    carried,
    excluded,
    foreign_members,
    foreign_vote,
    order_motion,
    procedure_of,
    weight_of,
)
from aerona.engine.divine.decrees import active_rulings, assigned_world
from aerona.engine.divine.motions import Motion
from aerona.engine.gods.essence import endow
from aerona.engine.mind.book import stored_values
from aerona.engine.mythic.offices import appoint, vacant_office
from aerona.engine.primitives.doom import step_doom
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.recording.record import StepDraft
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.conflict import foreign_god_war
from aerona.engine.transform.run import order

M = CouncilMotion
LASTING = RULING_LASTING | ORDER_LASTING


async def divide(ctx: TickContext) -> list[str]:
    worshipped = Counter[tuple[int, int]]()
    god = aliased(SonRow, flat=True)
    rows = await ctx.session.execute(
        select(EntityRow.world_id, BondRow.target_node_id)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .join(god, god.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, god.status != SonStatus.DEAD)
    )
    for world_id, son_id in rows:
        worshipped[(world_id, son_id)] += 1
    claimed: set[int] = set()
    given: Counter[int] = Counter()
    lines: list[str] = []
    for (world_id, son_id), _ in sorted(worshipped.items(), key=lambda item: (-item[1], item[0])):
        world = await ctx.session.get(WorldRow, world_id)
        son = await ctx.session.get(SonRow, son_id)
        if world is None or son is None or world.id in claimed or given[son_id] >= ctx.rules.council.worlds_per_son or held(son.id):
            continue
        world.patron_son_id, world.patron_automatic = son.id, False
        claimed.add(world.id)
        given[son_id] += 1
        lines.append(f"{world.name} to {son.name}")
    return lines


async def joint_war(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> str | None:
    god = await ctx.session.get(ForeignGodRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    able = [son for son in members if son.status is SonStatus.ACTIVE]
    if god is None or not able:
        return None
    champion = max(able, key=lambda son: (son.strength + son.will + son.level, -son.id))
    result = await foreign_god_war(ctx, champion.id, god.id, "by the council's decree", allies=[son for son in able if son.id != champion.id])
    return result.text


async def enact_divide(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    return [f"the gods gave {line}" for line in await divide(ctx)]


async def enact_war(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    text = await joint_war(ctx, ruling, members)
    return [text] if text else []


async def chain_son(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    son.chained = True
    return [f"{son.name} was chained"]


async def exile_son(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    son.status = SonStatus.EXILED
    return [f"{son.name} was exiled"]


async def strip_power(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    power = await ctx.session.scalar(select(SonPowerRow).where(SonPowerRow.son_id == son.id).order_by(SonPowerRow.slot.desc()).limit(1))
    if power is None:
        return []
    await ctx.session.delete(power)
    return [f"{son.name} was stripped of {power.name}"]


async def strip_divinity(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    await order(ctx, TransformKind.FALL, son.id, TransformTrigger.COUNCIL)
    return [f"{son.name} will be stripped of divinity unless the Creator stays it"]


async def bind_penance(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    deed = ruling.penance_deed or PenanceDeed.RESTORE_WORLD
    return [f"{son.name} must {PENANCE_DEEDS[deed].label} by epoch {ruling.until_epoch}"]


async def bind_to_world(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    if son.current_world_id is None:
        return []
    table = ctx.rules.council
    son.bound_world_id, son.bound_until_epoch = son.current_world_id, ctx.epoch + table.epochs(table.bound_world_years)
    return [f"{son.name} was bound to its world until epoch {son.bound_until_epoch}"]


async def rebuke_son(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    return [f"{son.name} was rebuked before the council"]


async def fine_son(ctx: TickContext, son: SonRow, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    return [await fine_essence(ctx, son, members)]


Penalty = Callable[[TickContext, SonRow, CouncilRulingRow, list[SonRow]], Awaitable[list[str]]]
PENALTIES: Mapping[SonPunishment, Penalty] = total(
    SonPunishment,
    {
        SonPunishment.CHAIN: chain_son,
        SonPunishment.EXILE: exile_son,
        SonPunishment.STRIP_POWER: strip_power,
        SonPunishment.STRIP_DIVINITY: strip_divinity,
        SonPunishment.PENANCE: bind_penance,
        SonPunishment.ESSENCE_FINE: fine_son,
        SonPunishment.BOUND_TO_WORLD: bind_to_world,
        SonPunishment.REBUKE: rebuke_son,
    },
)


async def enact_punishment(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    son = await ctx.session.get(SonRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if son is None or held(son.id):
        return []
    penalty = ruling.punishment or SonPunishment.CHAIN
    await record_incident(
        ctx,
        "council.penalty",
        roles={IncidentRole.TARGET: son.id},
        facts={"penalty": penalty, "penalty_label": PUNISHMENTS[penalty].label},
        kind=ChronicleKind.COUNCIL,
        world_id=ruling.world_id,
    )
    cost = PUNISHMENTS[penalty].renown
    if cost is not None:
        son.fame = max(0, son.fame - cost(ctx.rules))
    return await PENALTIES[penalty](ctx, son, ruling, members)


async def fine_essence(ctx: TickContext, son: SonRow, members: list[SonRow]) -> str:
    fine = son.essence * ctx.rules.council.essence_fine_share_pct // PERCENT
    son.essence -= fine
    takers = [member for member in members if member.id != son.id and not held(member.id)]
    for member in takers:
        endow(ctx.rules, member, fine // len(takers))
    return f"{son.name} paid {fine} essence to the council"


async def penance_done(ctx: TickContext, ruling: CouncilRulingRow) -> bool:
    if ruling.target_node_id is None:
        return False
    deed = ruling.penance_deed or PenanceDeed.RESTORE_WORLD
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(IncidentParticipantRow)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(
            IncidentParticipantRow.node_id == ruling.target_node_id,
            IncidentRow.kind.in_(sorted(PENANCE_DEEDS[deed].deeds)),
            IncidentRow.epoch >= ruling.epoch,
        )
    )
    return bool(found)


async def keep_penance(ctx: TickContext, ruling: CouncilRulingRow) -> bool:
    son = await ctx.session.get(SonRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if son is None or held(son.id) or "active" in ruling.locked:
        return False
    deed = ruling.penance_deed or PenanceDeed.RESTORE_WORLD
    facts = {"deed": deed, "deed_label": PENANCE_DEEDS[deed].label}
    if await penance_done(ctx, ruling):
        ruling.active = False
        son.fame += ctx.rules.council.penance_kept_renown
        await record_incident(
            ctx, "council.penance_kept", roles={IncidentRole.TARGET: son.id}, facts=facts, kind=ChronicleKind.COUNCIL, world_id=ruling.world_id
        )
        return True
    if ruling.until_epoch is None or ctx.epoch < ruling.until_epoch:
        return False
    ruling.punishment = SonPunishment.CHAIN
    ruling.until_epoch = ctx.epoch + (await procedure_of(ctx)).term_epochs
    son.chained = True
    await record_incident(ctx, "council.penance_failed", roles={IncidentRole.TARGET: son.id}, facts=facts, kind=ChronicleKind.COUNCIL, world_id=ruling.world_id)
    return True


async def enact_blessing(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    hero = await ctx.session.get(EntityRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if hero is None or held(hero.id) or await gain_condition(ctx, hero, ConditionKind.CHOSEN_MARK, HarmCause.GOD) is None:
        return []
    return [f"{hero.name} was blessed by the council"]


async def enact_holy_world(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    son = await ctx.session.get(SonRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    world = await ctx.session.get(WorldRow, ruling.world_id) if ruling.world_id is not None else None
    return [await declare_holy_world(ctx, son, world)] if son is not None and world is not None else []


async def enact_petition(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    council = ctx.rules.council
    creator = await ctx.session.scalar(select(CreatorRow).limit(1))
    if creator is None:
        return []
    creator.mood_interest = clamp_percent(creator.mood_interest + council.petition_interest)
    creator.mood_anger = clamp_percent(creator.mood_anger - council.petition_calm)
    return ["the Creator's eye turned to the council"]


async def enact_truce(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    return ["the gods swore a truce among themselves"]


async def enact_outlaw(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    return [f"{spoken(ruling.school)} rites were outlawed among the gods"] if ruling.school is not None else []


async def enact_appointment(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    vacant = await vacant_office(ctx)
    if vacant is None or ruling.target_node_id is None:
        return []
    await appoint(ctx, vacant, ruling.target_node_id, OfficeChoice.COUNCIL)
    return [f"the office of {spoken(vacant)} was given to a son"]


Enactment = Callable[[TickContext, CouncilRulingRow, list[SonRow]], Awaitable[list[str]]]
ENACTMENTS: dict[CouncilMotion, Enactment] = {
    M.DIVIDE_WORLDS: enact_divide,
    M.WAR_ON_FOREIGN_GOD: enact_war,
    M.PUNISH_SON: enact_punishment,
    M.BLESS_HERO: enact_blessing,
    M.HOLY_WORLD: enact_holy_world,
    M.PETITION_CREATOR: enact_petition,
    M.COSMIC_TRUCE: enact_truce,
    M.OUTLAW_RITE: enact_outlaw,
    M.APPOINT_OFFICE: enact_appointment,
    **ORDER_ENACTMENTS,
}


async def enact(ctx: TickContext, ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    action = ENACTMENTS.get(ruling.motion)
    lines = await action(ctx, ruling, members) if action is not None else []
    ruling.enacted = True
    if ruling.motion not in LASTING:
        ruling.active = False
    await ctx.session.flush()
    return lines


def penance_of(ctx: TickContext, motion: Motion) -> PenanceDeed | None:
    if motion.punishment is not SonPunishment.PENANCE:
        return None
    if motion.penance_deed is not None:
        return motion.penance_deed
    return ctx.rng(f"council.penance.{'none' if motion.target_node_id is None else motion.target_node_id}.{ctx.epoch}").pick(list(PenanceDeed))


async def until_of(ctx: TickContext, motion: Motion) -> int | None:
    if motion.motion is M.PUNISH_SON and motion.punishment is SonPunishment.PENANCE:
        return ctx.epoch + ctx.rules.council.penance_epochs
    return ctx.epoch + (await procedure_of(ctx)).term_epochs if motion.motion in LASTING else None


async def record(ctx: TickContext, motion: Motion, *, council_id: int | None, note_text: str | None = None) -> CouncilRulingRow:
    row = CouncilRulingRow(
        council_id=council_id,
        motion=motion.motion,
        target_node_id=motion.target_node_id,
        world_id=motion.world_id,
        school=motion.school,
        punishment=motion.punishment,
        penance_deed=penance_of(ctx, motion),
        epoch=ctx.epoch,
        until_epoch=await until_of(ctx, motion),
        voting_rule=motion.voting_rule,
        active=True,
        enacted=False,
        note=note_text,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def enforce_rulings(ctx: TickContext) -> int:
    kept = 0
    for row in await active_rulings(ctx):
        if row.motion is M.PUNISH_SON and row.punishment is SonPunishment.PENANCE and await keep_penance(ctx, row):
            kept += 1
            continue
        if row.until_epoch is not None and ctx.epoch >= row.until_epoch and "active" not in row.locked:
            row.active = False
            if row.motion is M.PUNISH_SON and row.punishment is SonPunishment.EXILE and row.target_node_id is not None:
                son = await ctx.session.get(SonRow, row.target_node_id)
                if son is not None and son.status is SonStatus.EXILED and not held(son.id):
                    son.status = SonStatus.ACTIVE
            await record_incident(
                ctx,
                "divine.ruling_lapsed",
                roles={IncidentRole.TARGET: row.target_node_id},
                facts={"motion": row.motion, "motion_label": MOTION_LABELS[row.motion].lower()},
                kind=ChronicleKind.COUNCIL,
                world_id=row.world_id,
            )
            continue
        if row.motion is M.PUNISH_SON and row.punishment is SonPunishment.CHAIN and row.target_node_id is not None:
            son = await ctx.session.get(SonRow, row.target_node_id)
            if son is not None and not held(son.id):
                son.chained = True
        if row.motion is M.DIVIDE_WORLDS:
            for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE)):
                world = await assigned_world(ctx, son.id)
                if world is not None and son.current_world_id != world and not held(son.id) and son.manually_assigned_epoch is None:
                    son.current_world_id = world
        kept += 1
    await ctx.session.flush()
    return kept


async def leaning(ctx: TickContext, son: SonRow, motion: Motion) -> int:
    table = ctx.rules.council
    values = await stored_values(ctx.session, ValueHolder.DIVINE, son.id)
    lean = 0
    target = motion.target_node_id
    if target is not None and target != son.id and await ctx.session.get(SonRow, target) is not None:
        lean += round(await SonRepository(ctx.session).relation(son.id, target) * table.relation_vote_pct / PERCENT) * (
            -1 if motion.motion is M.PUNISH_SON else 1
        )
    if target == son.id:
        lean -= PERCENT
    goals = await ctx.session.scalars(select(GodGoalRow).where(GodGoalRow.god_node_id == son.id, GodGoalRow.state == GoalState.ACTIVE))
    if any(goal.target_node_id == target and target is not None for goal in goals):
        lean += table.goal_vote
    martial, mercy = values.get(ValueAxis.MARTIAL, 0), values.get(ValueAxis.MERCY, 0)
    if motion.motion in {M.WAR_ON_FOREIGN_GOD}:
        lean += martial - mercy
    if motion.motion in LEANING_COUNCIL_MOTIONS:
        lean += mercy - martial
    if motion.motion is M.PETITION_CREATOR:
        lean += son.loyalty - PERCENT // 2
    if motion.motion is M.DIVIDE_WORLDS:
        lean += son.ambition - PERCENT // 2
    return lean


async def engine_votes(ctx: TickContext, members: list[SonRow], motion: Motion) -> dict[int, bool]:
    return {son.id: await leaning(ctx, son, motion) >= 0 for son in members}


async def engine_motion(ctx: TickContext, members: list[SonRow]) -> Motion:
    council = ctx.rules.council
    rebel = next((son for son in members if son.rebel), None)
    if rebel is not None:
        return Motion(M.PUNISH_SON, target_node_id=rebel.id, punishment=SonPunishment.CHAIN)
    hostile = await ctx.session.scalar(
        select(ForeignGodRow)
        .where(ForeignGodRow.status == ForeignGodStatus.AWAKE, ForeignGodRow.stance <= -ctx.rules.pantheon.son_war_max_attitude)
        .order_by(ForeignGodRow.stance, ForeignGodRow.id)
        .limit(1)
    )
    if hostile is not None:
        return Motion(M.WAR_ON_FOREIGN_GOD, target_node_id=hostile.id)
    cosmos = await ctx.session.scalar(select(CosmosRow).limit(1))
    if cosmos is not None and cosmos.doom_clock * PERCENT >= ctx.rules.balance.apocalypse_threshold * council.agenda_apocalypse_pct and cosmos.doom_clock:
        return Motion(M.AGAINST_DOOMSDAY)
    duels = await ctx.session.scalar(
        select(func.count(GodConflictRow.id)).where(GodConflictRow.duel.is_(True), GodConflictRow.epoch >= ctx.epoch - council.truce_window)
    )
    if int(duels or 0) >= council.truce_duels and not await active_rulings(ctx, M.COSMIC_TRUCE):
        return Motion(M.COSMIC_TRUCE)
    if await vacant_office(ctx) is not None and members:
        chosen = max(members, key=lambda son: (son.level, son.fame, -son.id))
        return Motion(M.APPOINT_OFFICE, target_node_id=chosen.id)
    return await order_motion(ctx, members) or Motion(M.PETITION_CREATOR)


async def engine_council(ctx: TickContext) -> CouncilRow | None:
    council = ctx.rules.council
    members = list(
        await ctx.session.scalars(
            select(SonRow).where(SonRow.status.in_([SonStatus.ACTIVE, SonStatus.ASLEEP])).order_by(*COUNCIL_SEATING).limit(council.max_members)
        )
    )
    if len(members) < council.min_members:
        return None
    members = [son for son in members if not await excluded(ctx, son.id)]
    if len(members) < council.min_members:
        return None
    motion = await engine_motion(ctx, members)
    votes = await engine_votes(ctx, members, motion)
    guests = await foreign_members(ctx)
    procedure = await procedure_of(ctx)
    weights = {son.id: (weight_of(procedure.voting_rule, son), votes[son.id]) for son in members}
    weights |= {god.id: (weight_of(procedure.voting_rule, god), foreign_vote(god, motion.motion, motion.target_node_id)) for god in guests}
    yes = sum(1 for _, vote in weights.values() if vote)
    passed = carried(procedure, weights, len(members) + len(guests))
    ballots = tuple(CouncilBallot(son_id=god.id, name=god.name, vote=CouncilVote.YES if weights[god.id][1] else CouncilVote.NO) for god in [*members, *guests])
    label = MOTION_LABELS[motion.motion]
    row = CouncilRow(
        epoch=ctx.epoch,
        topic=label,
        minutes=CouncilMinutes(topic=label, convened_by=CouncilCaller.FATE, motion=label, ballots=ballots, passed=passed, decision=motion.motion),
        passed=passed,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    notes: list[str] = []
    if passed:
        if motion.motion is M.AGAINST_DOOMSDAY:
            cosmos = await ctx.session.scalar(select(CosmosRow).limit(1))
            if cosmos is not None:
                step_doom(ctx.rules, cosmos, -council.apocalypse_motion_push)
                notes.append(f"the doomsday clock was pushed back {council.apocalypse_motion_push}")
        else:
            ruling = await record(ctx, motion, council_id=row.id, note_text=label)
            notes.extend(await enact(ctx, ruling, members))
    row.minutes = row.minutes.model_copy(update={"notes": tuple(notes)})
    verdict = "passed" if passed else "rejected"
    tail = f" {'; '.join(notes)}." if notes else ""
    await record_incident(
        ctx,
        "council.engine_held",
        roles={IncidentRole.MEMBER: [god.id for god in [*members, *guests]]},
        facts={"label": label.lower(), "verdict": verdict, "yes": yes, "no": len(weights) - yes, "tail": tail},
        kind=ChronicleKind.COUNCIL,
        steps=(
            *(
                StepDraft(StepAction.VOTE, actor=god.id, outcome=StepOutcome.ACCEPTED if weights[god.id][1] else StepOutcome.REFUSED)
                for god in [*members, *guests]
            ),
            StepDraft(StepAction.COUNT_VOTES, outcome=StepOutcome.ACCEPTED if passed else StepOutcome.REFUSED),
        ),
    )
    return row
