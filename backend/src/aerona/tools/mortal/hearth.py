from enum import StrEnum
from typing import Any

from aerona.catalog.genetics import HOUSEHOLD_DECISION_LABELS
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.genetics import HouseholdDecision, HouseholdRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.households.homes import dwelling_of
from aerona.engine.households.life import HouseholdTally, apprentice, lodger, match, members_of, migrate, renovate, sell_furnishing, servants
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

RULERS = frozenset({HouseholdRole.HEAD, HouseholdRole.SPOUSE})


class HomeChoice(StrEnum):
    RENOVATE = "renovate"
    SERVANTS = "servants"
    APPRENTICE = "apprentice"
    LODGER = "lodger"
    MARRY = "marry"
    SELL_FURNISHING = "sell_furnishing"
    MIGRATE = "migrate"


class HomeInput(ToolInput):
    choice: HomeChoice


async def tend_home(call: MortalCall, args: HomeInput) -> str:
    member = await call.session.get(HouseholdMemberRow, call.me.id)
    household = await call.session.get(HouseholdRow, member.household_id) if member is not None else None
    if member is None or household is None:
        fail(MortalResult.HOME_REFUSED, why="you belong to no household")
    if member.role not in RULERS:
        fail(MortalResult.HOME_REFUSED, why="only the head of a household or their spouse decides for it")
    if "decisions" in (household.locked or []):
        fail(MortalResult.HOME_REFUSED, why="a god holds the choices of your household")
    members = await members_of(call.tick, household)
    dwelling = await dwelling_of(call.session, household.id)
    tally = HouseholdTally()
    actions = {
        HomeChoice.RENOVATE: lambda: renovate(call.tick, household, dwelling, tally),
        HomeChoice.SERVANTS: lambda: servants(call.tick, household, dwelling, tally),
        HomeChoice.APPRENTICE: lambda: apprentice(call.tick, household, members, tally),
        HomeChoice.LODGER: lambda: lodger(call.tick, household, members, dwelling, tally, forced=True),
        HomeChoice.MARRY: lambda: match(call.tick, household, members, tally),
        HomeChoice.SELL_FURNISHING: lambda: sell_furnishing(call.tick, household, dwelling, tally),
        HomeChoice.MIGRATE: lambda: migrate(call.tick, household, members, dwelling, tally, forced=True),
    }
    if not await actions[args.choice]():
        fail(MortalResult.HOME_REFUSED, why="it cannot be done now: your purse, your home or your people do not allow it")
    decision = household.last_decision or HouseholdDecision.RENOVATE
    label = HOUSEHOLD_DECISION_LABELS[decision].lower()
    call.target(call.me.id)
    await call.record(
        "tools.mortal.home_tended",
        roles={IncidentRole.ACTOR: call.me.id},
        facts={"household": household.name, "decision": decision, "wealth": household.wealth},
        place=household.settlement_node_id,
    )
    return result(MortalResult.HOME_TENDED, household=household.name, deed=label, wealth=household.wealth)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.TEND_HOME, AgentKind.MORTAL, HomeInput, ToolMeta(ActionKind.BUILD, mortal_standard_action), tend_home)]
