from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.catalog.divine_grammar import VERB_SIGN
from aerona.catalog.kinds.council import VOTING_RULES
from aerona.catalog.life_traits import COUNCIL_MOTION_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import several, spoken
from aerona.core.total import total
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.council_order import CouncilProcedureRow, CouncilViolationRow, DivineSeatRow
from aerona.db.tables.divine import CouncilRulingRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.foreign_gods import ForeignGodRow, GodConflictRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.lore import CouncilRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import CouncilMotion, CouncilSeat, EscalationStep, VotingRule
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.life_traits import CouncilMotionTrait
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.powers import SourceAccess
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.divine.decrees import active_rulings, assigned_world
from aerona.engine.divine.foreign import pact_between
from aerona.engine.divine.motions import Motion
from aerona.engine.primitives.doom import step_doom
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

M = CouncilMotion
LADDER = (EscalationStep.CENSURE, EscalationStep.SANCTION, EscalationStep.EXCLUSION, EscalationStep.DUEL, EscalationStep.DIVINE_WAR)
CLOSED_TO_ALL = SourceAccess.GRANTED
HARMFUL = sorted(verb for verb, sign in VERB_SIGN.items() if sign < 0)


async def read_procedure(session: AsyncSession, rules: Rules) -> CouncilProcedureRow:
    row = await session.scalar(select(CouncilProcedureRow).order_by(CouncilProcedureRow.id).limit(1))
    return (
        row
        if row is not None
        else CouncilProcedureRow(quorum_pct=50, voting_rule=VotingRule.MAJORITY, creator_veto=True, term_epochs=rules.council.ruling_epochs, locked=[])
    )


async def procedure_of(ctx: TickContext) -> CouncilProcedureRow:
    row = await ctx.session.scalar(select(CouncilProcedureRow).order_by(CouncilProcedureRow.id).limit(1))
    if row is None:
        row = CouncilProcedureRow(term_epochs=ctx.rules.council.ruling_epochs, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def seat_of(ctx: TickContext, god_id: int, seat: CouncilSeat) -> DivineSeatRow:
    row = await ctx.session.get(DivineSeatRow, god_id)
    if row is None:
        row = DivineSeatRow(god_node_id=god_id, seat=seat, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


def sitting(row: DivineSeatRow | None, epoch: int) -> bool:
    return row is not None and (row.excluded_until is None or row.excluded_until <= epoch)


async def seat_gods(ctx: TickContext) -> None:
    for son in list(await ctx.session.scalars(select(SonRow).where(SonRow.status.in_([SonStatus.ACTIVE, SonStatus.ASLEEP])).order_by(SonRow.id))):
        await seat_of(ctx, son.id, CouncilSeat.BY_RIGHT)
    for treaty_party in list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id))):
        if not held(treaty_party.id) and await in_pact(ctx, treaty_party.id):
            await seat_of(ctx, treaty_party.id, CouncilSeat.BY_PACT)
    await ctx.session.flush()


async def in_pact(ctx: TickContext, god_id: int) -> bool:
    for son_id in list(await ctx.session.scalars(select(SonRow.id).where(SonRow.status == SonStatus.ACTIVE))):
        if await pact_between(ctx, son_id, god_id) is not None:
            return True
    return False


async def foreign_members(ctx: TickContext) -> list[ForeignGodRow]:
    seats = await ctx.session.scalars(select(DivineSeatRow).where(DivineSeatRow.seat != CouncilSeat.BY_RIGHT).order_by(DivineSeatRow.god_node_id))
    found: list[ForeignGodRow] = []
    for seat in list(seats):
        god = await ctx.session.get(ForeignGodRow, seat.god_node_id)
        if god is not None and god.status is ForeignGodStatus.AWAKE and sitting(seat, ctx.epoch):
            found.append(god)
    return found


async def excluded(ctx: TickContext, god_id: int) -> bool:
    row = await ctx.session.get(DivineSeatRow, god_id)
    return row is not None and not sitting(row, ctx.epoch)


def foreign_vote(god: ForeignGodRow, motion: CouncilMotion, target: int | None) -> bool:
    if target == god.id:
        return False
    return god.stance >= 0 if motion is not M.WAR_ON_FOREIGN_GOD else god.stance > PERCENT // 2


def weight_of(rule: VotingRule, god: SonRow | ForeignGodRow) -> int:
    spec = VOTING_RULES[rule]
    if isinstance(god, SonRow):
        return max(1, int(getattr(god, spec.son_weight))) if spec.son_weight is not None else 1
    return max(1, int(getattr(god, spec.foreign_weight)) // spec.foreign_divisor) if spec.foreign_weight is not None else 1


def carried(procedure: CouncilProcedureRow, weights: Mapping[int, tuple[int, bool]], seats: int) -> bool:
    if seats == 0 or len(weights) * PERCENT < procedure.quorum_pct * seats:
        return False
    if VOTING_RULES[procedure.voting_rule].everyone_agrees:
        return all(vote for _, vote in weights.values())
    yes = sum(weight for weight, vote in weights.values() if vote)
    no = sum(weight for weight, vote in weights.values() if not vote)
    return yes > no


Breaches = Callable[[TickContext, CouncilRulingRow], Awaitable[list[int]]]


WATCHED: Handlers[CouncilMotion, Breaches] = Handlers(CouncilMotion)


@WATCHED.on(CouncilMotion.COSMIC_TRUCE)
async def truce_breakers(ctx: TickContext, ruling: CouncilRulingRow) -> list[int]:
    rows = await ctx.session.scalars(select(GodConflictRow.attacker_node_id).where(GodConflictRow.duel.is_(True), GodConflictRow.epoch >= ruling.epoch))
    return sorted(set(rows))


@WATCHED.on(CouncilMotion.DIVIDE_WORLDS)
async def world_trespassers(ctx: TickContext, _ruling: CouncilRulingRow) -> list[int]:
    found = []
    for son in list(await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id))):
        world = await assigned_world(ctx, son.id)
        if world is not None and son.current_world_id is not None and son.current_world_id != world:
            found.append(son.id)
    return found


@WATCHED.on(CouncilMotion.OUTLAW_POWER)
async def outlawed_wielders(ctx: TickContext, ruling: CouncilRulingRow) -> list[int]:
    if ruling.target_node_id is None:
        return []
    used = select(DivinePowerRow.holder_node_id).where(DivinePowerRow.holder_node_id == ruling.target_node_id, DivinePowerRow.last_used_epoch > ruling.epoch)
    return sorted(set(await ctx.session.scalars(used)))


async def censure(ctx: TickContext, god_id: int) -> None:
    son = await ctx.session.get(SonRow, god_id)
    if son is not None:
        son.fame = max(0, son.fame - ctx.rules.council.censure_renown_cost)


async def sanction(ctx: TickContext, god_id: int) -> None:
    son = await ctx.session.get(SonRow, god_id)
    if son is not None:
        son.essence = max(0, son.essence - ctx.rules.council.sanction_essence)
        return
    god = await ctx.session.get(ForeignGodRow, god_id)
    if god is not None:
        god.faith = max(0, god.faith - ctx.rules.council.sanction_essence)


async def exclusion(ctx: TickContext, god_id: int) -> None:
    seat = await seat_of(ctx, god_id, CouncilSeat.BY_RIGHT)
    if "excluded_until" not in seat.locked:
        seat.excluded_until = ctx.epoch + ctx.rules.council.exclusion_epochs


async def duel(ctx: TickContext, god_id: int) -> None:
    champion = await ctx.session.scalar(
        select(SonRow).where(SonRow.id != god_id, SonRow.status == SonStatus.ACTIVE).order_by(SonRow.level.desc(), SonRow.id).limit(1)
    )
    if champion is not None and await ctx.session.get(SonRow, god_id) is not None:
        await SonRepository(ctx.session).change_relation(champion.id, god_id, -ctx.rules.council.duel_relation, "called out before the council")


async def divine_war(ctx: TickContext, god_id: int) -> None:
    son = await ctx.session.get(SonRow, god_id)
    if son is not None:
        son.rebel = True
        return
    god = await ctx.session.get(ForeignGodRow, god_id)
    if god is not None:
        god.stance = clamp_int(god.stance - PERCENT, -PERCENT * 2, PERCENT * 2)


PENALTIES: Mapping[EscalationStep, Callable[[TickContext, int], Awaitable[None]]] = total(
    EscalationStep,
    {
        EscalationStep.CENSURE: censure,
        EscalationStep.SANCTION: sanction,
        EscalationStep.EXCLUSION: exclusion,
        EscalationStep.DUEL: duel,
        EscalationStep.DIVINE_WAR: divine_war,
    },
)


async def escalate(ctx: TickContext, ruling: CouncilRulingRow, god_id: int) -> EscalationStep:
    before = int(await ctx.session.scalar(select(func.count(CouncilViolationRow.id)).where(CouncilViolationRow.violator_node_id == god_id)) or 0)
    step = LADDER[min(before, len(LADDER) - 1)]
    ctx.session.add(CouncilViolationRow(ruling_id=ruling.id, violator_node_id=god_id, epoch=ctx.epoch, step=step, locked=[]))
    await PENALTIES[step](ctx, god_id)
    return step


async def enforce_ladder(ctx: TickContext) -> int:
    met = 0
    for ruling in await active_rulings(ctx):
        watch = WATCHED.get(ruling.motion)
        if watch is None:
            continue
        for god_id in await watch(ctx, ruling):
            known = await ctx.session.scalar(
                select(CouncilViolationRow.id).where(
                    CouncilViolationRow.ruling_id == ruling.id, CouncilViolationRow.violator_node_id == god_id, CouncilViolationRow.epoch == ctx.epoch
                )
            )
            if known is not None or held(god_id):
                continue
            step = await escalate(ctx, ruling, god_id)
            await record(ctx, "council.violation", roles={IncidentRole.SUBJECT: god_id}, facts={"step": step}, kind=ChronicleKind.COUNCIL)
            met += 1
    await ctx.session.flush()
    return met


async def regulate(ctx: TickContext) -> None:
    step = ctx.rules.council.regulation_step
    if await active_rulings(ctx, M.REGULATE_MADE_MINDS):
        for mind in list(await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.seat != MindSeat.BODY))):
            if not held(mind.node_id) and "maker_bond" not in mind.locked:
                mind.maker_bond = clamp_int(mind.maker_bond + step, -PERCENT, PERCENT)
    if await active_rulings(ctx, M.REGULATE_LIVING_CRAFT):
        for line in list(await ctx.session.scalars(select(LivingLineRow))):
            if (line.owner_node_id is None or not held(line.owner_node_id)) and "drift_pct" not in line.locked:
                line.drift_pct = max(0, line.drift_pct - step)
                line.stability = clamp_percent(line.stability + step)
    if await active_rulings(ctx, M.REGULATE_POWERS):
        for source in list(await ctx.session.scalars(select(PowerSourceRow).where(PowerSourceRow.access == SourceAccess.ANYONE))):
            if "access" not in source.locked:
                source.access = SourceAccess.TRAINED


async def keep_council_order(ctx: TickContext) -> None:
    await procedure_of(ctx)
    await seat_gods(ctx)
    ctx.count("council_violations", await enforce_ladder(ctx))
    await regulate(ctx)


ORDER_ENACTMENTS: Handlers[CouncilMotion, Callable[[TickContext, CouncilRulingRow, list[SonRow]], Awaitable[list[str]]]] = Handlers(CouncilMotion)


@ORDER_ENACTMENTS.on(CouncilMotion.REASSIGN_WORLD)
async def enact_reassign(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    son = await ctx.session.get(SonRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    world = await ctx.session.get(WorldRow, ruling.world_id) if ruling.world_id is not None else None
    if son is None or world is None or held(son.id, world.id):
        return []
    world.patron_son_id, world.patron_automatic = son.id, False
    return [f"{world.name} was given to {son.name}"]


@ORDER_ENACTMENTS.on(CouncilMotion.OUTLAW_POWER)
async def enact_outlaw_power(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    holder = await ctx.session.get(NodeRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    return [f"the powers of {holder.name} were outlawed among the gods"] if holder is not None else []


@ORDER_ENACTMENTS.on(CouncilMotion.OUTLAW_SOURCE)
async def enact_outlaw_source(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    if ruling.world_id is None:
        return []
    closed = 0
    for source in list(await ctx.session.scalars(select(PowerSourceRow).where(PowerSourceRow.scope_node_id == ruling.world_id))):
        if "access" not in source.locked and source.access is not CLOSED_TO_ALL:
            source.access = CLOSED_TO_ALL
            closed += 1
    return [f"{several(closed, 'source of power was', 'sources of power were')} closed to all but those the gods allow"] if closed else []


@ORDER_ENACTMENTS.on(CouncilMotion.ADMIT_MEMBER)
async def enact_admit(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    god = await ctx.session.get(ForeignGodRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if god is None or held(god.id):
        return []
    seat = await seat_of(ctx, god.id, CouncilSeat.INVITED)
    seat.excluded_until = None
    return [f"{god.name} was given a seat on the council"]


@ORDER_ENACTMENTS.on(CouncilMotion.EXPEL_MEMBER)
async def enact_expel(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    seat = await ctx.session.get(DivineSeatRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if seat is None or held(seat.god_node_id):
        return []
    if seat.seat is CouncilSeat.BY_RIGHT:
        seat.excluded_until = ctx.epoch + ctx.rules.council.exclusion_epochs
    else:
        await ctx.session.delete(seat)
    return ["a member was put out of the council"]


@ORDER_ENACTMENTS.on(CouncilMotion.RECOGNISE_GOD)
async def enact_recognise(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    god = await ctx.session.get(ForeignGodRow, ruling.target_node_id) if ruling.target_node_id is not None else None
    if god is None or held(god.id):
        return []
    seat = await seat_of(ctx, god.id, CouncilSeat.RECOGNISED)
    seat.seat = CouncilSeat.RECOGNISED
    god.stance = clamp_int(god.stance + ctx.rules.council.covenant_relation, -PERCENT * 2, PERCENT * 2)
    return [f"the gods recognised {god.name} as one of them"]


@ORDER_ENACTMENTS.on(CouncilMotion.ESSENCE_TITHE)
async def enact_tithe(ctx: TickContext, _ruling: CouncilRulingRow, members: list[SonRow]) -> list[str]:
    table = ctx.rules.council
    paid = 0
    for son in members:
        if not held(son.id) and son.essence >= table.tithe_essence:
            son.essence -= table.tithe_essence
            paid += 1
    cosmos = await ctx.session.scalar(select(CosmosRow).limit(1))
    if cosmos is not None and paid:
        step_doom(ctx.rules, cosmos, -table.tithe_doom * paid)
    return [f"{several(paid, 'god paid', 'gods paid')} the tithe for a common work"] if paid else []


@ORDER_ENACTMENTS.on(CouncilMotion.SET_COUNCIL_RULES)
async def enact_rules(ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    procedure = await procedure_of(ctx)
    if ruling.voting_rule is None or "voting_rule" in procedure.locked:
        return []
    procedure.voting_rule = ruling.voting_rule
    return [f"the council now decides by {spoken(ruling.voting_rule)}"]


@ORDER_ENACTMENTS.on(CouncilMotion.REGULATE_MADE_MINDS)
@ORDER_ENACTMENTS.on(CouncilMotion.REGULATE_POWERS)
@ORDER_ENACTMENTS.on(CouncilMotion.REGULATE_LIVING_CRAFT)
async def enact_regulation(_ctx: TickContext, ruling: CouncilRulingRow, _members: list[SonRow]) -> list[str]:
    return [f"the council set a rule: {spoken(ruling.motion)}"]


ORDER_LASTING = having(COUNCIL_MOTION_TRAITS, CouncilMotionTrait.ORDER_LASTING)


async def membership_motion(ctx: TickContext) -> Motion | None:
    table = ctx.rules.council
    seated = {row.god_node_id for row in await ctx.session.scalars(select(DivineSeatRow))}
    awake = list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)))
    for god in awake:
        if god.id not in seated and god.stance >= table.invite_stance:
            return Motion(M.ADMIT_MEMBER, target_node_id=god.id)
        if god.id in seated and god.stance < 0:
            return Motion(M.EXPEL_MEMBER, target_node_id=god.id)
        if god.id not in seated and god.stance >= 0 and god.created_epoch >= ctx.epoch - table.truce_window:
            return Motion(M.RECOGNISE_GOD, target_node_id=god.id)
    return None


async def order_motion(ctx: TickContext, members: list[SonRow]) -> Motion | None:
    joining = await membership_motion(ctx)
    if joining is not None:
        return joining
    able = [son for son in members if son.status is SonStatus.ACTIVE and not son.chained]
    patron = aliased(SonRow, flat=True)
    fallen = await ctx.session.scalar(
        select(WorldRow).join(patron, patron.id == WorldRow.patron_son_id).where(patron.status != SonStatus.ACTIVE).order_by(WorldRow.id).limit(1)
    )
    if fallen is not None and able:
        heir = max(able, key=lambda son: (son.level, son.fame, -son.id))
        return Motion(M.REASSIGN_WORLD, target_node_id=heir.id, world_id=fallen.id)
    harmful = await ctx.session.scalar(
        select(DivinePowerRow.holder_node_id)
        .where(DivinePowerRow.verb.in_(HARMFUL), DivinePowerRow.last_used_epoch >= ctx.epoch - 1)
        .order_by(DivinePowerRow.last_used_epoch.desc(), DivinePowerRow.id)
        .limit(1)
    )
    if harmful is not None and not any(row.target_node_id == harmful for row in await active_rulings(ctx, M.OUTLAW_POWER)):
        return Motion(M.OUTLAW_POWER, target_node_id=harmful)
    bonded = await ctx.session.scalar(
        select(PowerSourceRow.scope_node_id).where(PowerSourceRow.access == SourceAccess.BONDED, PowerSourceRow.scope_node_id.in_(select(WorldRow.id))).limit(1)
    )
    if bonded is not None and not await active_rulings(ctx, M.OUTLAW_SOURCE):
        return Motion(M.OUTLAW_SOURCE, world_id=bonded)
    return await regulation_motion(ctx)


async def regulation_motion(ctx: TickContext) -> Motion | None:
    table = ctx.rules.council
    minds = int(await ctx.session.scalar(select(func.count()).select_from(MindProfileRow).where(MindProfileRow.seat != MindSeat.BODY)) or 0)
    if minds >= table.regulate_at and not await active_rulings(ctx, M.REGULATE_MADE_MINDS):
        return Motion(M.REGULATE_MADE_MINDS)
    drifting = int(await ctx.session.scalar(select(func.count(LivingLineRow.id)).where(LivingLineRow.drift_pct >= table.regulate_drift)) or 0)
    if drifting and not await active_rulings(ctx, M.REGULATE_LIVING_CRAFT):
        return Motion(M.REGULATE_LIVING_CRAFT)
    open_sources = int(await ctx.session.scalar(select(func.count(PowerSourceRow.id)).where(PowerSourceRow.access == SourceAccess.ANYONE)) or 0)
    if open_sources >= table.regulate_at and not await active_rulings(ctx, M.REGULATE_POWERS):
        return Motion(M.REGULATE_POWERS)
    cosmos = await ctx.session.scalar(select(CosmosRow).limit(1))
    if cosmos is not None and cosmos.doom_clock * PERCENT * 2 >= ctx.rules.balance.apocalypse_threshold * table.agenda_apocalypse_pct:
        return Motion(M.ESSENCE_TITHE)
    failed = list(await ctx.session.scalars(select(CouncilRow.passed).order_by(CouncilRow.id.desc()).limit(table.failed_councils)))
    procedure = await procedure_of(ctx)
    if len(failed) == table.failed_councils and not any(failed) and procedure.voting_rule is not VotingRule.MAJORITY:
        return Motion(M.SET_COUNCIL_RULES, voting_rule=VotingRule.MAJORITY)
    return None
