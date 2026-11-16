from typing import Any, Literal

from sqlalchemy import select

from aerona.db.tables.concealment import HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow, TruthSeekerRow
from aerona.db.tables.powers import PowerRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.concealment import KeeperRole, SeekerAim
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import PowerState
from aerona.engine.concealment.truths import knowledge
from aerona.engine.powers.effects import seen_ahead
from aerona.engine.powers.society import test_people
from aerona.engine.powers.use import use
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import connect, living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import EnactLawInput
from aerona.tools.mortal.ruler import enact_law, throne_of

PERCENT = 100
TRAINING = 5


class PowerInput(ToolInput):
    power_id: int


class UsePowerInput(PowerInput):
    target_id: int | None = None


class LinkInput(ToolInput):
    partner_id: int


class TruthInput(ToolInput):
    truth_id: int


class InvestigateInput(TruthInput):
    aim: SeekerAim = SeekerAim.UNDERSTAND


class PowerLawInput(ToolInput):
    level: Literal["free", "registered", "licensed", "conscripted", "hunted", "banned"]
    mind_powers: Literal["allowed", "licensed", "banned"] = "licensed"


async def my_power(call: MortalCall, power_id: int, declined: MortalResult) -> PowerRow:
    power = await call.session.get(PowerRow, power_id)
    if power is None or power.holder_node_id != call.me.id:
        fail(declined, why="you hold no such power")
    if held(call.me.id):
        fail(declined, why="a stronger hand holds you")
    return power


async def use_power_tool(call: MortalCall, args: UsePowerInput) -> str:
    power = await my_power(call, args.power_id, MortalResult.POWER_USE_DECLINED)
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None and target is None:
        fail(MortalResult.POWER_USE_DECLINED, why="there is no one there to reach")
    outcome = await use(call.tick, power, call.me, target)
    if outcome.reason is not None:
        fail(MortalResult.POWER_USE_DECLINED, why=outcome.reason)
    if target is not None:
        call.target(target.id)
    done = outcome.done or "nothing came of it"
    await call.chronicle(
        ChronicleKind.CULTURE, lines.USE_POWER, entity_ids=[call.me.id, *([target.id] if target is not None else [])], me=call.me.name, done=done
    )
    return result(MortalResult.POWER_USED, done=done, strain=power.strain)


async def train_power(call: MortalCall, args: PowerInput) -> str:
    power = await my_power(call, args.power_id, MortalResult.POWER_TRAINING_DECLINED)
    if power.state in {PowerState.LOST, PowerState.BURNED_OUT}:
        fail(MortalResult.POWER_TRAINING_DECLINED, why="that power is lost or spent")
    if "control" not in power.locked:
        power.control = clamp_percent(power.control + call.rules.powers.control_gain * TRAINING)
    if power.state is PowerState.LATENT and "state" not in power.locked:
        power.state = PowerState.EMERGING
    await call.chronicle(ChronicleKind.CULTURE, lines.TRAIN_POWER, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.POWER_TRAINED, control=power.control)


async def test_for_gifts(call: MortalCall, _args: ToolInput) -> str:
    realm = await throne_of(call)
    town = call.me.location_id
    if town is None or held(realm.entity.id):
        fail(MortalResult.TESTING_DECLINED, why="you have no town to test")
    found = await test_people(call.tick, town)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.TEST_FOR_GIFTS, entity_ids=[call.me.id, town], me=call.me.name)
    return result(MortalResult.GIFTS_TESTED, count=found)


async def link_minds(call: MortalCall, args: LinkInput) -> str:
    partner = await living_entity(call.session, args.partner_id)
    if partner is None or partner.id == call.me.id or held(partner.id):
        fail(MortalResult.MIND_LINK_DECLINED, why="there is no one there to link with")
    mine = await call.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == call.me.id, PowerRow.state == PowerState.ACTIVE).limit(1))
    theirs = await call.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == partner.id, PowerRow.state == PowerState.ACTIVE).limit(1))
    if mine is None or theirs is None:
        fail(MortalResult.MIND_LINK_DECLINED, why="both of you need a waking power to link")
    await connect(call.session, call.me.id, partner.id, BondKind.LINKED_WITH, call.tick.epoch, description="linked by their powers")
    call.target(partner.id)
    await call.chronicle(ChronicleKind.CULTURE, lines.LINK_MINDS, entity_ids=[call.me.id, partner.id], me=call.me.name, name=partner.name)
    return result(MortalResult.MINDS_LINKED, name=partner.name)


async def foresee_tool(call: MortalCall, args: PowerInput) -> str:
    power = await my_power(call, args.power_id, MortalResult.FORESIGHT_DECLINED)
    if power.form is not SpellForm.TIME or power.state is not PowerState.ACTIVE:
        fail(MortalResult.FORESIGHT_DECLINED, why="that power does not see what may come")
    sight = clamp_int(power.strength * PERCENT // 10 + power.control // 2, 0, PERCENT)
    row = await seen_ahead(call.tick, call.me, None, sight, power.id)
    if row is None:
        fail(MortalResult.FORESIGHT_DECLINED, why="nothing likely enough shows itself")
    row.strain_cost = power.strength * call.rules.powers.strain_per_use
    if "strain" not in power.locked:
        power.strain += row.strain_cost
    await call.chronicle(ChronicleKind.FATE, lines.FORESEE, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.FORESEEN, certainty=row.certainty)


async def known_truth(call: MortalCall, truth_id: int, declined: MortalResult) -> HiddenTruthRow:
    truth = await call.session.get(HiddenTruthRow, truth_id)
    if truth is None:
        fail(declined, why="you know of no such hidden truth")
    keeper = await call.session.scalar(select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.keeper_node_id == call.me.id))
    seeker = await call.session.scalar(select(TruthSeekerRow.id).where(TruthSeekerRow.truth_id == truth.id, TruthSeekerRow.seeker_node_id == call.me.id))
    heard = await call.session.scalar(
        select(PublicKnowledgeRow.id).where(
            PublicKnowledgeRow.truth_id == truth.id, PublicKnowledgeRow.population_node_id == call.me.location_id, PublicKnowledgeRow.know_pct > 0
        )
    )
    if keeper is None and seeker is None and heard is None and truth.subject_node_id != call.me.id:
        fail(declined, why="you know of no such hidden truth")
    return truth


async def keep_secret_of(call: MortalCall, args: TruthInput) -> str:
    truth = await known_truth(call, args.truth_id, MortalResult.KEEPING_DECLINED)
    exists = await call.session.scalar(select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.keeper_node_id == call.me.id))
    if exists is not None:
        fail(MortalResult.KEEPING_DECLINED, why="you already keep it")
    call.session.add(TruthKeeperRow(truth_id=truth.id, keeper_node_id=call.me.id, role=KeeperRole.MEMBER, locked=[]))
    await call.chronicle(ChronicleKind.FATE, lines.KEEP_SECRET_OF, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.SECRET_KEPT, title=truth.title)


async def investigate(call: MortalCall, args: InvestigateInput) -> str:
    truth = await known_truth(call, args.truth_id, MortalResult.INVESTIGATION_DECLINED)
    seeker = await call.session.scalar(select(TruthSeekerRow).where(TruthSeekerRow.truth_id == truth.id, TruthSeekerRow.seeker_node_id == call.me.id))
    if seeker is None:
        seeker = TruthSeekerRow(truth_id=truth.id, seeker_node_id=call.me.id, aim=args.aim, progress=0, began_epoch=call.tick.epoch, locked=[])
        call.session.add(seeker)
    elif "progress" not in seeker.locked:
        seeker.progress = clamp_percent(seeker.progress + call.rules.concealment.seeker_gain)
    await call.chronicle(ChronicleKind.FATE, lines.INVESTIGATE, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.INVESTIGATED, title=truth.title, progress=seeker.progress)


async def cover_up(call: MortalCall, args: TruthInput) -> str:
    truth = await known_truth(call, args.truth_id, MortalResult.COVER_UP_DECLINED)
    keeper = await call.session.scalar(select(TruthKeeperRow.id).where(TruthKeeperRow.truth_id == truth.id, TruthKeeperRow.keeper_node_id == call.me.id))
    if keeper is None or call.me.location_id is None:
        fail(MortalResult.COVER_UP_DECLINED, why="only a keeper of the truth can cover it up")
    row = await knowledge(call.tick, truth.id, call.me.location_id)
    if "believe_pct" not in row.locked:
        row.believe_pct = clamp_percent(row.believe_pct - row.believe_pct * call.rules.concealment.cover_cut_pct // PERCENT)
    await call.chronicle(ChronicleKind.FATE, lines.COVER_UP, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.COVERED_UP, title=truth.title, believe=row.believe_pct)


async def set_power_law(call: MortalCall, args: PowerLawInput) -> str:
    return await enact_law(call, EnactLawInput(kind=LawKind.POWER_LAW, params={"level": args.level, "mind_powers": args.mind_powers}))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.USE_POWER, mortal, UsePowerInput, meta, use_power_tool),
        ToolSpec(MortalToolId.TRAIN_POWER, mortal, PowerInput, meta, train_power),
        ToolSpec(MortalToolId.TEST_FOR_GIFTS, mortal, ToolInput, meta, test_for_gifts),
        ToolSpec(MortalToolId.LINK_MINDS, mortal, LinkInput, meta, link_minds),
        ToolSpec(MortalToolId.FORESEE, mortal, PowerInput, meta, foresee_tool),
        ToolSpec(MortalToolId.KEEP_SECRET_OF, mortal, TruthInput, meta, keep_secret_of),
        ToolSpec(MortalToolId.INVESTIGATE, mortal, InvestigateInput, meta, investigate),
        ToolSpec(MortalToolId.COVER_UP, mortal, TruthInput, meta, cover_up),
        ToolSpec(MortalToolId.SET_POWER_LAW, mortal, PowerLawInput, meta, set_power_law),
    ]
