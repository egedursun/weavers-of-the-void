from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgCliqueRow, OrgGovernanceRow, OrgMergerRow, OrgResearchRow, OrgSeatRow
from aerona.domain.enums.governance import OPEN_INSOLVENCY_STAGES, OPEN_MERGER_STAGES


async def my_organisations(scope: Scope, me: EntityRow) -> list[int]:
    session = scope.session
    joined = set(await session.scalars(select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == me.id)))
    owned = set(await session.scalars(select(CompanyShareRow.company_entity_id).where(CompanyShareRow.holder_node_id == me.id)))
    headed = set(await session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == me.id)))
    return sorted(joined | owned | headed)


async def body_line(scope: Scope, me: EntityRow, body: OrgGovernanceRow) -> str:
    org = await named(scope, body.org_node_id)
    head = "you" if body.head_node_id == me.id else await named(scope, body.head_node_id) if body.head_node_id is not None else "nobody"
    seat = await scope.session.scalar(select(OrgSeatRow).where(OrgSeatRow.org_node_id == body.org_node_id, OrgSeatRow.member_node_id == me.id))
    mine = f", your seat holds {seat.vote_weight} of the votes" if seat is not None else ", you hold no seat"
    term = f", term ends in epoch {body.term_ends_epoch}" if body.term_ends_epoch is not None else ""
    return (
        f"{org} (organisation {body.org_node_id}) is ruled by its {spoken(body.decision_body)} voting {spoken(body.vote_basis)} with a quorum of "
        f"{body.quorum_pct}; head {head}, chosen by {spoken(body.head_selection)}{term}, trusted {body.trust}; course {spoken(body.strategy)}{mine}"
    )


async def clique_line(scope: Scope, clique: OrgCliqueRow) -> str:
    aim = spoken(clique.aim_strategy) if clique.aim_strategy is not None else spoken(clique.aim)
    target = f" for {await named(scope, clique.aim_node_id)}" if clique.aim_node_id is not None else ""
    leader = await named(scope, clique.leader_node_id) if clique.leader_node_id is not None else "no one"
    return f"clique {clique.id} led by {leader} seeks {aim}{target} with {clique.strength} of the votes"


async def mortal_governance_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for org_id in await my_organisations(scope, me):
        body = await session.get(OrgGovernanceRow, org_id)
        if body is None:
            continue
        found.append(await body_line(scope, me, body))
        for clique in await session.scalars(select(OrgCliqueRow).where(OrgCliqueRow.org_node_id == org_id).order_by(OrgCliqueRow.id)):
            found.append(await clique_line(scope, clique))
        for research in await session.scalars(
            select(OrgResearchRow).where(OrgResearchRow.org_node_id == org_id, OrgResearchRow.done_epoch.is_(None)).order_by(OrgResearchRow.id)
        ):
            pursuit = spoken(research.technique) if research.technique is not None else "a design"
            found.append(f"it researches {pursuit}: progress {research.progress}, budget {research.budget}, staff {research.staff}")
        for merger in await session.scalars(
            select(OrgMergerRow)
            .where(or_(OrgMergerRow.acquirer_node_id == org_id, OrgMergerRow.target_node_id == org_id), OrgMergerRow.stage.in_(sorted(OPEN_MERGER_STAGES)))
            .order_by(OrgMergerRow.id)
        ):
            found.append(
                f"{await named(scope, merger.acquirer_node_id)} bids {merger.price} for {await named(scope, merger.target_node_id)} "
                f"as {spoken(merger.kind)}, now {spoken(merger.stage)}"
            )
        case = await session.scalar(
            select(InsolvencyCaseRow).where(InsolvencyCaseRow.debtor_node_id == org_id, InsolvencyCaseRow.stage.in_(sorted(OPEN_INSOLVENCY_STAGES))).limit(1)
        )
        if case is not None:
            found.append(f"it is before the court owing {case.owed}, by {spoken(case.path)}, now at {spoken(case.stage)}")
    return found
