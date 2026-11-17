from typing import Any

from aerona.catalog.civics import PRIVILEGE_GATES
from aerona.catalog.estates import ESTATE_NAMES, PRIVILEGE_LABELS
from aerona.db.tables.estates import EstateProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.faction import EstatePrivilege
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.factions.estates import grant, revoke
from aerona.engine.lore.civics import realm_allows, unlearned
from aerona.engine.polity.book import RealmBook
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

PRIVILEGES = "privileges"


class BargainInput(ToolInput):
    estate_id: int
    privilege: EstatePrivilege
    grant: bool


async def bargain_with_estate(call: MortalCall, args: BargainInput) -> str:
    limit = call.rules.mortal_tools.estate_bargain_per_epoch
    await call.within_limit(TurnCounter.FACTION_ACTS, limit, "mortal_tools.estate_bargain_per_epoch", MortalResult.ESTATE_LIMIT)
    row = await call.session.get(EstateProfileRow, args.estate_id)
    if row is None:
        fail(MortalResult.ESTATE_REFUSED, why="there is no such estate")
    book = await RealmBook.load(call.session)
    realm = book.realms.get(row.polity_entity_id)
    if realm is None or realm.ruler_id != call.me.id:
        fail(MortalResult.ESTATE_REFUSED, why="you do not rule the realm of that estate")
    if PRIVILEGES in (row.locked or []):
        fail(MortalResult.ESTATE_REFUSED, why="a god holds its privileges")
    needed = PRIVILEGE_GATES.get(args.privilege)
    if args.grant and not await realm_allows(call.session, realm, needed):
        fail(MortalResult.ESTATE_REFUSED, why=f"the realm has not yet learned {unlearned(needed)}, which that privilege needs")
    done = await grant(call.tick, row, args.privilege) if args.grant else await revoke(call.tick, row, args.privilege)
    if not done:
        fail(MortalResult.ESTATE_REFUSED, why="it already has that privilege" if args.grant else "it does not hold that privilege, or it is held")
    deed = "granted" if args.grant else "took back"
    estate = ESTATE_NAMES[row.social_class].lower()
    label = PRIVILEGE_LABELS[args.privilege].lower()
    call.target(row.faction_entity_id)
    await call.record(
        "tools.mortal.estate_granted" if args.grant else "tools.mortal.estate_revoked",
        roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.RECEIVER: row.faction_entity_id},
        facts={"privilege": args.privilege, "estate": row.social_class, "loyalty": row.loyalty},
    )
    return result(MortalResult.ESTATE_BARGAINED, deed=deed, privilege=label, estate=estate, loyalty=row.loyalty)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.BARGAIN_WITH_ESTATE, AgentKind.MORTAL, BargainInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), bargain_with_estate)
    ]
