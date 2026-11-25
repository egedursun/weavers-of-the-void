from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.divine_will import DivineWillAttachmentRow
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, DivineWillMode
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from tests.tools.divine_will_case import WillCase, WillWorld
from tests.tools.divine_will_media import session_media

W = DivineWillToolId
LEDGER_NAME = "harvest-ledger.md"
LEDGER_KEY = "divine-will/harness/document.md"
LEDGER_TEXT = "# Harvest ledger\n\nThe Kessar Folk count their grain in the ledger of Brinewatch.\n\nEach season the count is read aloud at the gate."


async def attached(session: AsyncSession, world: WillWorld) -> dict[str, int]:
    await session_media(session).put(LEDGER_KEY, LEDGER_TEXT.encode())
    row = DivineWillAttachmentRow(
        cycle_id=world.cycle_id,
        kind=AttachmentKind.DOCUMENT,
        filename=LEDGER_NAME,
        mime="text/markdown",
        size=len(LEDGER_TEXT),
        media_key=LEDGER_KEY,
        markdown_key=LEDGER_KEY,
        status=AttachmentStatus.CONVERTED,
        note="",
    )
    session.add(row)
    await session.flush()
    return {"attachment": row.id}


RETRIEVAL_CASES: dict[DivineWillToolId, WillCase] = {
    W.SEARCH_LORE: WillCase(arguments=lambda _world: {"query": "Brinewatch"}, mode=DivineWillMode.ASK_LORE, expect=('"source": "entity"', "Brinewatch")),
    W.ATTACHMENT_LIST: WillCase(setup=attached, expect=(LEDGER_NAME, '"status": "converted"')),
    W.ATTACHMENT_READ: WillCase(arguments=lambda world: {"attachment_id": world.ids["attachment"]}, setup=attached, expect=("ledger of Brinewatch",)),
    W.ATTACHMENT_SEARCH: WillCase(arguments=lambda _world: {"query": "grain ledger"}, setup=attached, expect=('"source": "attachment"', "count their grain")),
}
