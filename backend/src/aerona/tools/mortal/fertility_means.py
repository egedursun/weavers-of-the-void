from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.fertility_means import FertilityMeans
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.fertility_means.tend import HIDING
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

SECRET = "in secret, since your people frown on it"


class UseFertilityMeansInput(ToolInput):
    means: FertilityMeans


async def use_fertility_means(call: MortalCall, args: UseFertilityMeansInput) -> str:
    people = await people_of(call.session, call.me)
    known = await call.session.get(FertilityMeansRow, (people.id, args.means)) if people is not None else None
    if people is None or known is None:
        fail(MortalResult.MEANS_REFUSED, why=f"your people know no way of {spoken(args.means)}")
    if held(call.me.id):
        fail(MortalResult.MEANS_REFUSED, why="a god holds you unchanged")
    mine = select(FertilityUseRow.id).where(FertilityUseRow.user_entity_id == call.me.id, FertilityUseRow.means == args.means)
    if await call.session.scalar(mine) is not None:
        fail(MortalResult.MEANS_REFUSED, why="you use it already")
    hidden = known.stance in HIDING
    call.session.add(
        FertilityUseRow(user_entity_id=call.me.id, people_entity_id=people.id, means=args.means, hidden=hidden, since_epoch=call.tick.epoch, locked=[])
    )
    await call.record(
        "birth.means_used", roles={IncidentRole.SUBJECT: call.me.id, IncidentRole.MEMBER: people.id}, facts={"means": args.means, "stance": known.stance}
    )
    return result(MortalResult.MEANS_USED, means=spoken(args.means), manner=SECRET if hidden else "openly")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(
            MortalToolId.USE_FERTILITY_MEANS,
            AgentKind.MORTAL,
            UseFertilityMeansInput,
            ToolMeta(ActionKind.INFLUENCE, mortal_standard_action),
            use_fertility_means,
        )
    ]
