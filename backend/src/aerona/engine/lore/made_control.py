from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.culture import BookContentRow, ItemHistoryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import ArtMode, ItemDeed
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore import art, items
from aerona.engine.lore.history import scope_incident
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record as record_incident

NOTE_MAX = 480


async def living_item(ctx: TickContext, item_id: int) -> EntityRow:
    item = await living_entity(ctx.session, item_id)
    if item is None or item.entity_type is not EntityType.ITEM:
        raise NotFoundError("No such living item.")
    return item


async def transfer(ctx: TickContext, item_id: int, receiver_id: int, reason: str) -> EntityRow:
    item = await living_item(ctx, item_id)
    receiver = await living_entity(ctx.session, receiver_id)
    if receiver is None:
        raise NotFoundError("No such living receiver.")
    giver = await items.owner_of(ctx, item.id)
    if giver == receiver.id:
        raise ValidationFailedError(f"{receiver.name} already holds {item.name}.")
    await items.profile_of(ctx, item)
    await items.give(ctx, item, receiver.id, ItemDeed.GIVEN, reason.strip()[:NOTE_MAX] or f"given into the keeping of {receiver.name}")
    await record_incident(
        ctx,
        "item.transferred",
        roles={IncidentRole.SUBJECT: item.id, IncidentRole.RECEIVER: receiver.id, IncidentRole.GIVER: giver},
        place=receiver.location_id,
    )
    await ctx.session.flush()
    return receiver


async def add_deed(ctx: TickContext, item_id: int, deed: ItemDeed, *, actor_id: int | None, text: str, epoch: int | None) -> ItemHistoryRow:
    item = await living_item(ctx, item_id)
    actor = await ctx.session.get(EntityRow, actor_id) if actor_id is not None else None
    if actor_id is not None and actor is None:
        raise NotFoundError("No such record to name in the deed.")
    if epoch is not None and not 0 <= epoch <= ctx.epoch:
        raise ValidationFailedError(f"A deed is set between the first age and age {ctx.epoch}.")
    row = ItemHistoryRow(
        item_entity_id=item.id,
        epoch=ctx.epoch if epoch is None else epoch,
        deed=deed,
        actor_entity_id=actor_id,
        note=text.strip()[:NOTE_MAX],
        incident_id=scope_incident(),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def remove_deed(ctx: TickContext, deed_id: int) -> ItemHistoryRow:
    row = await ctx.session.get(ItemHistoryRow, deed_id)
    if row is None:
        raise NotFoundError("No such deed in the item's story.")
    await ctx.session.delete(row)
    await ctx.session.flush()
    return row


async def set_content(ctx: TickContext, book_id: int, knowledge_id: int, fidelity: int) -> BookContentRow | None:
    book = await living_item(ctx, book_id)
    profile = await items.profile_of(ctx, book)
    if not items.is_book(profile):
        raise ValidationFailedError(f"{book.name} is not a book, scroll or prayer book.")
    knowledge = await ctx.session.get(EntityRow, knowledge_id)
    if knowledge is None or knowledge.entity_type is not EntityType.KNOWLEDGE:
        raise NotFoundError("No such knowledge to write down.")
    row = await ctx.session.get(BookContentRow, (book.id, knowledge.id))
    if fidelity == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if not 0 < fidelity <= PERCENT:
        raise ValidationFailedError(f"Fidelity runs from 1 to {PERCENT}.")
    if row is None:
        row = BookContentRow(book_entity_id=book.id, knowledge_entity_id=knowledge.id, fidelity=fidelity)
        ctx.session.add(row)
    row.fidelity = fidelity
    await ctx.session.flush()
    return row


async def commission(
    ctx: TickContext,
    patron_id: int,
    *,
    name: str,
    medium: ArtMode,
    author_id: int | None,
    subject_id: int | None,
    message: dict[str, int] | None,
    paid: bool,
) -> EntityRow:
    return await art.commission_work(ctx, patron_id, name=name, medium=medium, author_id=author_id, subject_id=subject_id, message=message, paid=paid)


async def canonise(ctx: TickContext, artwork_id: int, *, canon: bool) -> bool:
    row = await art.canonise(ctx, artwork_id, canon=canon)
    return row.canon
