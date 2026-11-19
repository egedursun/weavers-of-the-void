from typing import Any

from aerona.catalog.statecraft import DEMAND_TEXT
from aerona.core.grammar import spoken
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.crises import nearest_land, open_crisis
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.ruler import throne_of


class DemandInput(ToolInput):
    target_id: int
    demand: CrisisDemand
    subject_id: int | None = None


class BackInput(ToolInput):
    crisis_id: int
    side: CrisisSide


async def issue_demand(call: MortalCall, args: DemandInput) -> str:
    realm = await throne_of(call)
    book = await RealmBook.load(call.session)
    target = book.realm_for(args.target_id)
    if target is None or target.entity.id == realm.entity.id:
        fail(MortalResult.DEMAND_REFUSED, why="that is not another realm")
    subject = args.subject_id
    if args.demand is CrisisDemand.CEDE_REGION:
        subject = subject if subject in target.territory else nearest_land(book, realm, target)
    elif args.demand is CrisisDemand.RELEASE_VASSAL:
        vassal = book.vassals.get(subject) if subject is not None else None
        if vassal is None or vassal.overlord_entity_id != target.entity.id:
            fail(MortalResult.DEMAND_REFUSED, why="that realm holds no such vassal")
    elif args.demand is CrisisDemand.CONVERT:
        subject = realm.profile.state_religion_id
    if args.demand in {CrisisDemand.CEDE_REGION, CrisisDemand.CONVERT} and subject is None:
        fail(MortalResult.DEMAND_REFUSED, why="there is nothing of that kind to demand")
    amount = target.profile.treasury * call.rules.statecraft.pay_share_pct // 100 if args.demand is CrisisDemand.PAY else 0
    row = await open_crisis(call.tick, realm, target, args.demand, subject_id=subject, amount=amount)
    if row is None:
        fail(MortalResult.DEMAND_REFUSED, why="a crisis between you already runs, or a god holds one of you")
    text = DEMAND_TEXT[args.demand]
    call.target(target.entity.id)
    await call.record(f"tools.mortal.demand_{args.demand.value}", roles={IncidentRole.ACCUSER: call.me.id, IncidentRole.TARGET: target.entity.id})
    return result(MortalResult.DEMAND_ISSUED, realm=target.entity.name, demand=text, steps=call.rules.statecraft.crisis_steps)


async def back_crisis(call: MortalCall, args: BackInput) -> str:
    realm = await throne_of(call)
    row = await call.session.get(CrisisRow, args.crisis_id)
    if row is None or row.state is not CrisisState.ESCALATING:
        fail(MortalResult.BACKING_REFUSED, why="there is no such crisis under way")
    if realm.entity.id in (row.demander_entity_id, row.target_entity_id):
        fail(MortalResult.BACKING_REFUSED, why="your realm is one of its sides")
    found = await call.session.get(CrisisBackerRow, (row.id, realm.entity.id))
    if found is not None and found.locked:
        fail(MortalResult.BACKING_REFUSED, why="a god holds your realm's stance")
    if found is None:
        found = CrisisBackerRow(crisis_id=row.id, backer_entity_id=realm.entity.id, side=args.side)
        call.session.add(found)
    found.side, found.swing = args.side, False
    await call.session.flush()
    lead = row.demander_entity_id if args.side is CrisisSide.DEMANDER else row.target_entity_id
    call.target(lead)
    await call.record("tools.mortal.backed", roles={IncidentRole.ALLY: call.me.id, IncidentRole.BENEFICIARY: lead}, facts={"side": args.side})
    return result(MortalResult.CRISIS_BACKED, side=spoken(args.side))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.ISSUE_DEMAND, AgentKind.MORTAL, DemandInput, meta, issue_demand),
        ToolSpec(MortalToolId.BACK_CRISIS, AgentKind.MORTAL, BackInput, meta, back_crisis),
    ]
