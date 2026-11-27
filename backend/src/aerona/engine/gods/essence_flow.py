from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.gods.essence import son_room
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record


def sendable(ctx: TickContext, giver: SonRow, receiver: SonRow | CreatorRow, amount: int) -> int:
    keep = ctx.rules.son_tools.gift_min_remaining
    room = son_room(ctx.rules, receiver) if isinstance(receiver, SonRow) else amount
    return max(0, min(amount, giver.essence - keep, room))


async def send_essence(ctx: TickContext, giver: SonRow, receiver: SonRow | CreatorRow, amount: int, words: str = "") -> int:
    if receiver.id == giver.id:
        raise ValidationFailedError("A son cannot send essence to themselves.")
    sent = sendable(ctx, giver, receiver, amount)
    if sent <= 0:
        raise ValidationFailedError(
            f"{giver.name} can send no essence to {receiver.name}: {giver.name} must keep {ctx.rules.son_tools.gift_min_remaining} "
            f"(world rule son_tools.gift_min_remaining) and the receiver has no room left."
        )
    if not move_amount(giver, receiver, "essence", sent):
        raise ValidationFailedError(f"The essence of {giver.name} or {receiver.name} is locked.")
    await record(
        ctx,
        "gods.essence_sent",
        roles={IncidentRole.ACTOR: giver.id, IncidentRole.RECEIVER: receiver.id},
        facts={"amount": sent, "words": str(words)},
        kind=ChronicleKind.GIFT,
        son_id=giver.id,
    )
    return sent


async def take_from_creator(ctx: TickContext, son: SonRow, creator: CreatorRow, wanted: int) -> int:
    taken = max(0, min(wanted, creator.essence, son_room(ctx.rules, son)))
    if taken <= 0 or not move_amount(creator, son, "essence", taken):
        return 0
    return taken
