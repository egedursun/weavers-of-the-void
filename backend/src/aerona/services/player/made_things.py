from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import ArtMedium, ItemDeed
from aerona.engine.lore import made_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class TransferItem(Command):
    item_id: int
    receiver_id: int
    reason: str = ""


class AddDeed(Command):
    item_id: int
    deed: ItemDeed
    actor_id: int | None = None
    note: str = ""
    epoch: int | None = None


class DeedTarget(Command):
    deed_id: int


class BookContent(Command):
    book_id: int
    knowledge_id: int
    fidelity: int


class CommissionArtwork(Command):
    patron_id: int
    medium: ArtMedium
    name: str = ""
    author_id: int | None = None
    subject_id: int | None = None
    message: dict[str, int] = Field(default_factory=dict)
    paid: bool = True


class Canonise(Command):
    artwork_id: int
    canon: bool = True


@player_action("item:transfer", ActionKind.EDIT_RECORD)
async def transfer_item(scope: PlayerScope, command: TransferItem) -> Effect:
    receiver = await made_control.transfer(await scope.context("item_transfer"), command.item_id, command.receiver_id, command.reason)
    return Effect(f"It passes to {receiver.name}.", command.item_id)


@player_action("item:deed", ActionKind.EDIT_RECORD)
async def add_deed(scope: PlayerScope, command: AddDeed) -> Effect:
    row = await made_control.add_deed(
        await scope.context("item_deed"), command.item_id, command.deed, actor_id=command.actor_id, text=command.note, epoch=command.epoch
    )
    return Effect(f"A deed is written into its story in age {row.epoch}.", command.item_id)


@player_action("item:deed_remove", ActionKind.EDIT_RECORD)
async def remove_deed(scope: PlayerScope, command: DeedTarget) -> Effect:
    row = await made_control.remove_deed(await scope.context("item_deed_remove"), command.deed_id)
    return Effect("That deed is struck from its story.", row.item_entity_id)


@player_action("item:content", ActionKind.EDIT_RECORD)
async def set_content(scope: PlayerScope, command: BookContent) -> Effect:
    row = await made_control.set_content(await scope.context("item_content"), command.book_id, command.knowledge_id, command.fidelity)
    return Effect(f"It holds that knowledge {row.fidelity}% true." if row is not None else "That knowledge is scraped from its pages.", command.book_id)


@player_action("art:commission", ActionKind.OTHER)
async def commission_artwork(scope: PlayerScope, command: CommissionArtwork) -> Effect:
    work = await made_control.commission(
        await scope.context("art_commission"),
        command.patron_id,
        name=command.name,
        medium=command.medium,
        author_id=command.author_id,
        subject_id=command.subject_id,
        message=command.message or None,
        paid=command.paid,
    )
    return Effect(f"{work.name} is begun.", work.id, created_ids=(work.id,))


@player_action("art:canonise", ActionKind.EDIT_RECORD)
async def canonise(scope: PlayerScope, command: Canonise) -> Effect:
    canon = await made_control.canonise(await scope.context("art_canonise"), command.artwork_id, canon=command.canon)
    return Effect("It is set among the classics." if canon else "It is struck from the classics.", command.artwork_id)
