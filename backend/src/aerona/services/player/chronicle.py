from collections.abc import Sequence

from aerona.catalog.god_lines import Line
from aerona.db.tables.cosmos import CreatorRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.engine.context import TickContext
from aerona.events.kinds import EventKind
from aerona.services.player.lines import HAND


async def tell(
    ctx: TickContext,
    line: Line,
    *,
    ids: Sequence[int] = (),
    son_id: int | None = None,
    world_id: int | None = None,
    kind: ChronicleKind = ChronicleKind.CREATOR_HAND,
    **fields: object,
) -> str:
    text = line.render(**fields)
    await ctx.chronicle(kind, text, template_key=line.key, entity_ids=[item for item in ids if item], son_id=son_id, world_id=world_id)
    ctx.publish(EventKind.ENGINE_NOTE, {"epoch": ctx.epoch, "phase": ctx.phase, "kind": kind.value, "template_key": line.key, "text": text})
    return text


async def hand(
    ctx: TickContext,
    creator: CreatorRow,
    line: Line,
    *,
    ids: Sequence[int] = (),
    son_id: int | None = None,
    world_id: int | None = None,
    kind: ChronicleKind = ChronicleKind.CREATOR_HAND,
    **fields: object,
) -> str:
    text = HAND.render(creator=creator.name, text=line.render(**fields))
    await ctx.chronicle(kind, text, template_key=line.key, entity_ids=[item for item in ids if item], son_id=son_id, world_id=world_id)
    ctx.publish(EventKind.ENGINE_NOTE, {"epoch": ctx.epoch, "phase": ctx.phase, "kind": kind.value, "template_key": line.key, "text": text})
    return text
