from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgCliqueRow, OrgGovernanceRow, OrgSeatRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.governance import CliqueAim, HeadSelection, InsolvencyPath, MergerKind, OrgStrategy, VoteChoice
from aerona.engine.economy.purse import take_coin
from aerona.engine.governance.cliques import split_away
from aerona.engine.governance.heads import busy_heads, candidates, chosen_head, cliques_of, install_head, set_strategy, strategy_vote
from aerona.engine.governance.insolvency import InsolvencyTally, case_of, file_case
from aerona.engine.governance.mergers import open_bid, worth
from aerona.engine.governance.research import begin_research, open_research, reachable
from aerona.engine.governance.seats import members_of, shares_of, sync_seats
from aerona.engine.mortal.life import years_to_step
from aerona.engine.polity.divided_loyalty import serves_a_foe
from aerona.engine.primitives.maturity import away_among, of_age_among, past_office_age
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.population import realm_ruled_by

OrgName = Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
BUDGET_MAX = 100000


class CastOrgVoteInput(ToolInput):
    org_id: int
    motion: OrgStrategy
    vote: VoteChoice = VoteChoice.FOR


class SeekHeadshipInput(ToolInput):
    org_id: int


class SplitOrgInput(ToolInput):
    org_id: int
    clique_id: int
    name_reason: OrgName


class BidForOrgInput(ToolInput):
    acquirer_id: int
    target_id: int
    kind: MergerKind
    price: int | None = Field(default=None, ge=0)


class FundResearchInput(ToolInput):
    org_id: int
    technique: Technique | None = None
    design_id: int | None = None
    budget: int = Field(ge=1, le=BUDGET_MAX)


class FileInsolvencyInput(ToolInput):
    org_id: int
    path: InsolvencyPath


async def may_head(call: MortalCall, row: OrgGovernanceRow, org: EntityRow) -> None:
    ctx, me = call.tick, call.me
    if me.id in await away_among(ctx.session, [me.id]):
        fail(MortalResult.ORG_REFUSED, why=f"you stand away from {org.name} now")
    if me.id in await busy_heads(ctx, row.org_node_id, [me.id]):
        fail(MortalResult.ORG_REFUSED, why=f"you already head as many bodies as one may, {ctx.rules.governance.headships_max}")
    if me.id in await serves_a_foe(ctx.session, [me.id], row.org_node_id):
        fail(MortalResult.ORG_REFUSED, why=f"you serve a foe of {org.name}")
    if row.head_selection is not HeadSelection.INHERITED and not await of_age_among(ctx.session, [me]):
        fail(MortalResult.ORG_REFUSED, why="you have not yet come of age")
    if row.head_selection is not HeadSelection.INHERITED and past_office_age(ctx.rules, me, years_to_step(ctx.environment)):
        fail(MortalResult.ORG_REFUSED, why="custom retires those of your age from office")
    if me.id not in {entity.id for entity in await candidates(ctx, row)}:
        fail(MortalResult.ORG_REFUSED, why=f"{org.name} does not count you among those who may head it")


async def body_of(call: MortalCall, org_id: int) -> tuple[EntityRow, OrgGovernanceRow]:
    org = await call.session.get(EntityRow, org_id)
    body = await call.session.get(OrgGovernanceRow, org_id)
    if org is None or body is None or org.status is not EntityStatus.CANON:
        fail(MortalResult.ORG_REFUSED, why="there is no such organisation with a governing body")
    if held(org.id):
        fail(MortalResult.ORG_REFUSED, why="a god holds it as it is")
    return org, body


async def headed_by_me(call: MortalCall, org_id: int) -> tuple[EntityRow, OrgGovernanceRow]:
    org, body = await body_of(call, org_id)
    if body.head_node_id != call.me.id:
        fail(MortalResult.ORG_REFUSED, why=f"only the head of {org.name} acts for it")
    return org, body


async def cast_org_vote(call: MortalCall, args: CastOrgVoteInput) -> str:
    org, body = await body_of(call, args.org_id)
    seat = await call.session.scalar(select(OrgSeatRow).where(OrgSeatRow.org_node_id == org.id, OrgSeatRow.member_node_id == call.me.id))
    if seat is None:
        fail(MortalResult.ORG_REFUSED, why=f"you hold no seat on the body of {org.name}")
    backing = [clique for clique in await cliques_of(call.tick, org.id) if clique.aim is CliqueAim.STRATEGY and clique.aim_strategy is args.motion]
    for clique in await cliques_of(call.tick, org.id):
        if call.me.id in (clique.members or []) and "members" not in (clique.locked or []):
            clique.members = [node for node in clique.members or [] if node != call.me.id]
    if args.vote is VoteChoice.AGAINST:
        backing = []
    elif backing and "members" not in (backing[0].locked or []):
        backing[0].members = sorted({*(backing[0].members or []), call.me.id})
    else:
        call.session.add(
            OrgCliqueRow(
                org_node_id=org.id,
                name=f"those around {call.me.name}",
                leader_node_id=call.me.id,
                members=[call.me.id],
                aim=CliqueAim.STRATEGY,
                aim_strategy=args.motion,
                strength=seat.vote_weight,
                since_epoch=call.epoch,
                locked=[],
            )
        )
    await call.session.flush()
    decided = await strategy_vote(call.tick, body)
    if decided is not None:
        await set_strategy(call.tick, body, decided, call.me.id)
    call.target(org.id)
    outcome = "the motion carried" if decided is args.motion else "the course stands"
    return result(MortalResult.ORG_VOTED, org=org.name, motion=spoken(args.motion), vote=spoken(args.vote), outcome=outcome)


async def seek_headship(call: MortalCall, args: SeekHeadshipInput) -> str:
    org, body = await body_of(call, args.org_id)
    members = {member.mortal_entity_id for member in await members_of(call.tick, org.id)} | set(await shares_of(call.tick, org.id))
    if call.me.id not in members:
        fail(MortalResult.ORG_REFUSED, why=f"only a member or an owner of {org.name} may stand for its headship")
    if body.head_node_id == call.me.id:
        fail(MortalResult.ORG_REFUSED, why=f"you already head {org.name}")
    if "head_node_id" in (body.locked or []):
        fail(MortalResult.ORG_REFUSED, why="its head is held as it is")
    call.target(org.id)
    await may_head(call, body, org)
    if body.head_selection is HeadSelection.PURCHASE:
        price = await worth(call.tick, org) // max(1, call.rules.governance.term_epochs)
        if not await take_coin(call.session, call.rules, call.me, price):
            fail(MortalResult.ORG_REFUSED, why=f"the headship costs {price} and you cannot pay it")
        await install_head(call.tick, body, call.me, "the headship was bought")
        return result(MortalResult.ORG_HEAD_WON, org=org.name, how="by purchase")
    call.session.add(
        OrgCliqueRow(
            org_node_id=org.id,
            name=f"those around {call.me.name}",
            leader_node_id=call.me.id,
            members=[call.me.id],
            aim=CliqueAim.HEAD,
            aim_node_id=call.me.id,
            strength=0,
            since_epoch=call.epoch,
            locked=[],
        )
    )
    await call.session.flush()
    await sync_seats(call.tick, body)
    if body.term_ends_epoch is not None and call.epoch >= body.term_ends_epoch:
        head = await chosen_head(call.tick, body)
        if head is not None and head.id == call.me.id:
            await install_head(call.tick, body, call.me, "the term ended and the body chose anew")
            return result(MortalResult.ORG_HEAD_WON, org=org.name, how=spoken(body.head_selection))
    return result(MortalResult.ORG_HEAD_SOUGHT, org=org.name, selection=spoken(body.head_selection), ends=body.term_ends_epoch or call.epoch)


async def split_org(call: MortalCall, args: SplitOrgInput) -> str:
    org, body = await body_of(call, args.org_id)
    clique = await call.session.get(OrgCliqueRow, args.clique_id)
    if clique is None or clique.org_node_id != org.id or clique.leader_node_id != call.me.id:
        fail(MortalResult.ORG_REFUSED, why=f"you lead no such clique in {org.name}")
    if org.entity_type is not EntityType.FACTION:
        fail(MortalResult.ORG_REFUSED, why="a cult parts only through a schism of its faith")
    threshold = call.rules.governance.split_clique_threshold
    if clique.strength < threshold:
        fail(MortalResult.ORG_REFUSED, why=f"your clique holds {clique.strength} of the votes and needs {threshold} to leave with a share")
    child = await split_away(call.tick, body, clique, args.name_reason)
    if child is None:
        fail(MortalResult.ORG_REFUSED, why="no member of the clique could leave with you")
    call.target(child.id)
    call.remember_creation(child.id)
    return result(MortalResult.ORG_SPLIT, org=org.name, product=child.name)


async def bid_for_org(call: MortalCall, args: BidForOrgInput) -> str:
    acquirer = await call.session.get(EntityRow, args.acquirer_id)
    target, _target_body = await body_of(call, args.target_id)
    if acquirer is None or acquirer.status is not EntityStatus.CANON or acquirer.id == target.id:
        fail(MortalResult.ORG_REFUSED, why="there is no such bidder")
    if args.kind is MergerKind.ABSORPTION_BY_POLITY:
        if acquirer.entity_type is not EntityType.POLITY or await realm_ruled_by(call) != acquirer.id:
            fail(MortalResult.ORG_REFUSED, why="only the ruler of a realm absorbs an organisation into it")
    else:
        await headed_by_me(call, acquirer.id)
    if held(acquirer.id):
        fail(MortalResult.ORG_REFUSED, why="a god holds the bidder as it is")
    if await case_of(call.tick, target.id) is not None:
        fail(MortalResult.ORG_REFUSED, why=f"{target.name} has an open insolvency case")
    merger = await open_bid(call.tick, acquirer.id, target, args.kind, args.price)
    call.target(target.id)
    return result(MortalResult.ORG_BID, acquirer=acquirer.name, target=target.name, kind=spoken(args.kind), price=merger.price)


async def fund_research(call: MortalCall, args: FundResearchInput) -> str:
    org, _body = await headed_by_me(call, args.org_id)
    if (args.technique is None) == (args.design_id is None):
        fail(MortalResult.ORG_REFUSED, why="name either a technique or a design to pursue")
    design = await call.session.get(DesignRow, args.design_id) if args.design_id is not None else None
    if args.design_id is not None and design is None:
        fail(MortalResult.ORG_REFUSED, why="there is no such design")
    if args.technique is not None and args.technique not in await reachable(call.tick, org):
        fail(MortalResult.ORG_REFUSED, why=f"{spoken(args.technique)} is beyond what its home knows, or it holds it already")
    if not await take_coin(call.session, call.rules, org, args.budget):
        fail(MortalResult.ORG_REFUSED, why=f"{org.name} cannot spare {args.budget}")
    same = next(
        (row for row in await open_research(call.tick, org.id) if row.technique is args.technique and row.design_id == args.design_id),
        None,
    )
    if same is not None and "budget" not in (same.locked or []):
        same.budget = clamp_int(same.budget + args.budget, 0, BUDGET_MAX * 10)
        row = same
    else:
        row = await begin_research(call.tick, org, args.technique, args.design_id, args.budget)
    call.target(org.id)
    pursuit = spoken(args.technique) if args.technique is not None else design.name if design is not None else "a design"
    return result(MortalResult.ORG_RESEARCH_FUNDED, org=org.name, pursuit=pursuit, budget=row.budget)


async def file_insolvency(call: MortalCall, args: FileInsolvencyInput) -> str:
    org, _body = await headed_by_me(call, args.org_id)
    case = await file_case(call.tick, org, args.path, InsolvencyTally())
    if case is None:
        fail(MortalResult.ORG_REFUSED, why=f"{org.name} already has an open insolvency case")
    call.target(org.id)
    return result(MortalResult.ORG_INSOLVENT, org=org.name, path=spoken(args.path), owed=case.owed)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    influence = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.CAST_ORG_VOTE, AgentKind.MORTAL, CastOrgVoteInput, influence, cast_org_vote),
        ToolSpec(MortalToolId.SEEK_HEADSHIP, AgentKind.MORTAL, SeekHeadshipInput, influence, seek_headship),
        ToolSpec(MortalToolId.SPLIT_ORG, AgentKind.MORTAL, SplitOrgInput, influence, split_org),
        ToolSpec(MortalToolId.BID_FOR_ORG, AgentKind.MORTAL, BidForOrgInput, influence, bid_for_org),
        ToolSpec(MortalToolId.FUND_RESEARCH, AgentKind.MORTAL, FundResearchInput, influence, fund_research),
        ToolSpec(MortalToolId.FILE_INSOLVENCY, AgentKind.MORTAL, FileInsolvencyInput, influence, file_insolvency),
    ]
