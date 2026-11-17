from typing import Any

from aerona.catalog.titles import RANK_WORDS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.titles import TitleTenure
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.titles import record_holder, share_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

HOLDER = "holder_node_id"


class SeizeTitleInput(ToolInput):
    title_id: int


async def seize_title(call: MortalCall, args: SeizeTitleInput) -> str:
    row = await call.session.get(TitleProfileRow, args.title_id)
    entity = await call.session.get(EntityRow, args.title_id)
    if row is None or entity is None:
        fail(MortalResult.TITLE_REFUSED, why="there is no such title")
    if row.holder_node_id == call.me.id:
        fail(MortalResult.TITLE_REFUSED, why="you already hold it")
    if HOLDER in (row.locked or []):
        fail(MortalResult.TITLE_REFUSED, why="a god holds it against change")
    book = await RealmBook.load(call.session)
    realm = next((item for item in book.realms.values() if item.ruler_id == call.me.id), None)
    if realm is None:
        fail(MortalResult.TITLE_REFUSED, why="you rule no realm to back a claim")
    share = await share_of(call.tick, realm, row.title_entity_id)
    if share < call.rules.titles.creation_share_pct:
        fail(MortalResult.TITLE_REFUSED, why=f"your realm holds only {round(share)}% of its lands by right")
    if row.capital_entity_id is not None and row.capital_entity_id not in realm.members:
        fail(MortalResult.TITLE_REFUSED, why="you do not hold its seat")
    dormant = row.holder_node_id is None
    await record_holder(call.tick, row, call.me.id, TitleTenure.RESTORED if dormant else TitleTenure.USURPED)
    if dormant:
        row.destroyed_epoch = None
    else:
        realm.profile.legitimacy = max(0, realm.profile.legitimacy - call.rules.titles.usurp_legitimacy)
    deed = "restored" if dormant else "usurped"
    call.target(entity.id)
    tenure = TitleTenure.RESTORED if dormant else TitleTenure.USURPED
    await call.record("tools.mortal.title_seized", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: entity.id}, facts={"tenure": tenure})
    return result(MortalResult.TITLE_SEIZED, title=entity.name, deed=deed, rank=RANK_WORDS[row.rank].lower())


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.SEIZE_TITLE, AgentKind.MORTAL, SeizeTitleInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), seize_title)]
