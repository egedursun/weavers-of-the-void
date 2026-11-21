from typing import Any

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.tables.speech import SpeechRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.referendums import CampaignMeans, ReferendumCaller, ReferendumResult, ReferendumSubject, VoteSide
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.referendums.book import ReferendumTally
from aerona.engine.referendums.voting import call_vote
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

CAMPAIGN_COIN = 100
SIDE_SIGN = {VoteSide.YES: 1, VoteSide.NO: -1}


class CallReferendumInput(ToolInput):
    polity_id: int
    subject: ReferendumSubject
    question_target_id: int | None = None
    binding: bool = True


class CampaignForVoteInput(ToolInput):
    referendum_id: int
    side: VoteSide
    means: CampaignMeans


async def call_referendum_tool(call: MortalCall, args: CallReferendumInput) -> str:
    holder = await living_entity(call.session, args.polity_id)
    if holder is None or not await controls(call, holder.id):
        fail(MortalResult.VOTE_REFUSED, why="only the ruler of a realm, town or league puts a question to its people")
    if held(holder.id) or (args.question_target_id is not None and held(args.question_target_id)):
        fail(MortalResult.VOTE_REFUSED, why="a god holds it as it is")
    row = await call_vote(
        call.tick,
        holder,
        args.subject,
        args.question_target_id,
        binding=args.binding,
        caller=ReferendumCaller.RULER,
        called_by=call.me.id,
        tally=ReferendumTally(),
    )
    call.target(holder.id)
    return result(MortalResult.VOTE_CALLED, question=spoken(args.subject), holder=holder.name, franchise=spoken(row.franchise))


async def media_shift(call: MortalCall, row: ReferendumRow) -> int:
    reach = await call.session.scalar(select(func.max(MediaOutletRow.reach)).where(MediaOutletRow.owner_node_id == call.me.id))
    if not reach:
        fail(MortalResult.VOTE_REFUSED, why="you own no outlet to carry the campaign")
    return round_half_up(call.tick.rules.referendums.media_shift * reach / PERCENT)


async def speech_shift(call: MortalCall) -> int:
    effect = await call.session.scalar(select(func.max(SpeechRow.effect)).where(SpeechRow.speaker_node_id == call.me.id, SpeechRow.heard.is_(True)))
    if effect is None:
        fail(MortalResult.VOTE_REFUSED, why="you have given no speech that was heard")
    return round_half_up(call.tick.rules.referendums.speech_shift * max(0, effect) / PERCENT)


async def campaign_for_vote_tool(call: MortalCall, args: CampaignForVoteInput) -> str:
    table = call.tick.rules.referendums
    row = await call.session.get(ReferendumRow, args.referendum_id)
    if row is None or row.result is not ReferendumResult.PENDING:
        fail(MortalResult.VOTE_REFUSED, why="there is no such vote still to be held")
    if held(row.holder_node_id) or "yes_pct" in (row.locked or []):
        fail(MortalResult.VOTE_REFUSED, why="a god holds that vote as it is")
    sign = SIDE_SIGN[args.side]
    if args.means is CampaignMeans.MONEY:
        if not await take_coin(call.session, call.tick.rules, call.me, CAMPAIGN_COIN):
            fail(MortalResult.VOTE_REFUSED, why=f"you cannot spend {CAMPAIGN_COIN}")
        if args.side is VoteSide.YES:
            row.yes_spending += CAMPAIGN_COIN
        else:
            row.no_spending += CAMPAIGN_COIN
    elif args.means is CampaignMeans.MEDIA:
        row.yes_pct = clamp_int(row.yes_pct + sign * await media_shift(call, row), 0, PERCENT)
    elif args.means is CampaignMeans.SPEECH:
        row.yes_pct = clamp_int(row.yes_pct + sign * await speech_shift(call), 0, PERCENT)
    elif args.means is CampaignMeans.FRAUD:
        row.fraud = clamp_int(row.fraud + table.fraud_step, 0, PERCENT)
        row.yes_pct = clamp_int(row.yes_pct + sign * table.fraud_step * table.fraud_shift_pct // PERCENT, 0, PERCENT)
    call.target(row.holder_node_id)
    await call.record(
        "vote.campaigned", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: row.holder_node_id}, facts={"side": args.side, "means": args.means}
    )
    return result(MortalResult.VOTE_CAMPAIGNED, side=spoken(args.side), means=spoken(args.means), yes=row.yes_pct)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.CALL_REFERENDUM, AgentKind.MORTAL, CallReferendumInput, act, call_referendum_tool),
        ToolSpec(MortalToolId.CAMPAIGN_FOR_VOTE, AgentKind.MORTAL, CampaignForVoteInput, act, campaign_for_vote_tool),
    ]
