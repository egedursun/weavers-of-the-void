from typing import Any

from aerona.catalog.estates import ESTATE_NAMES, PRIVILEGE_LABELS
from aerona.db.tables.estates import EstateProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.faction import EstatePrivilege
from aerona.engine.factions.estates import grant, revoke
from aerona.engine.polity.book import RealmBook
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

PRIVILEGES = "privileges"


class BargainInput(ToolInput):
    estate_id: int
    privilege: EstatePrivilege
    grant: bool


async def bargain_with_estate(call: MortalCall, args: BargainInput) -> str:
    row = await call.session.get(EstateProfileRow, args.estate_id)
    if row is None:
        fail(MortalResult.ESTATE_REFUSED, why="there is no such estate")
    book = await RealmBook.load(call.session)
    realm = book.realms.get(row.polity_entity_id)
    if realm is None or realm.ruler_id != call.me.id:
        fail(MortalResult.ESTATE_REFUSED, why="you do not rule the realm of that estate")
    if PRIVILEGES in (row.locked or []):
        fail(MortalResult.ESTATE_REFUSED, why="a god holds its privileges")
    done = await grant(call.tick, row, args.privilege) if args.grant else await revoke(call.tick, row, args.privilege)
    if not done:
        fail(MortalResult.ESTATE_REFUSED, why="it already has that privilege" if args.grant else "it does not hold that privilege, or it is held")
    deed = "granted" if args.grant else "took back"
    estate = ESTATE_NAMES[row.social_class].lower()
    label = PRIVILEGE_LABELS[args.privilege].lower()
    call.target(row.faction_entity_id)
    await call.chronicle(
        ChronicleKind.CIVILIZATION,
        lines.ESTATE_BARGAIN,
        entity_ids=[call.me.id, row.faction_entity_id],
        me=call.me.name,
        deed=deed,
        privilege=label,
        estate=estate,
    )
    return result(MortalResult.ESTATE_BARGAINED, deed=deed, privilege=label, estate=estate, loyalty=row.loyalty)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.BARGAIN_WITH_ESTATE, AgentKind.MORTAL, BargainInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), bargain_with_estate)
    ]
