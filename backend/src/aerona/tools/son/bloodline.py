from typing import Any

from aerona.core.grammar import spoken
from aerona.db.tables.polity import HouseProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import HouseTrait
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son.support import require_essence


class BloodlineInput(ToolInput):
    house_id: int
    trait: HouseTrait
    revoke: bool = False


async def bless_bloodline(call: SonCall, args: BloodlineInput) -> str:
    house = await require_canon(call.session, args.house_id)
    profile = await call.session.get(HouseProfileRow, house.id)
    if house.entity_type is not EntityType.HOUSE or profile is None:
        fail(SonResult.NO_HOUSE)
    require_essence(call, call.rules.son_tools.bloodline_cost)
    traits = [item for item in profile.traits if item is not args.trait]
    profile.traits = traits if args.revoke else [*traits, args.trait]
    if args.trait is HouseTrait.GOD_BLOODED and not args.revoke:
        profile.divine_son_id = call.son.id
    call.spend_essence(call.rules.son_tools.bloodline_cost)
    call.target(house.id)
    await call.record(
        "tools.son.bloodline",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: house.id},
        facts={"trait": args.trait},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.BLOODLINE_SET, house=house.name, trait=spoken(args.trait))


def bloodline_cost(rules: Rules) -> int:
    return rules.son_tools.bloodline_cost


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.BLESS_BLOODLINE,
            AgentKind.SON,
            BloodlineInput,
            ToolMeta(ActionKind.BLESS_BLOODLINE, lambda rules: rules.son_tools.treaty_ap, essence_cost=bloodline_cost),
            bless_bloodline,
        )
    ]
