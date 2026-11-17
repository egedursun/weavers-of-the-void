from pydantic import Field

from aerona.catalog.communication import CONTENT_LABELS, MEDIUM_LABELS, SIGNAL_LABELS, SUBJECT_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.communication import APPROVAL_MAX, APPROVAL_MIN, CipherRow, PublicOpinionRow, SignalLinkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, OpinionSubject, SignalKind, SignalState
from aerona.domain.enums.entity import EntityType
from aerona.engine.communication.post import send
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
DISPATCH_FIELDS = ("state", "arrival_epoch", "forged", "misread", "enciphered", "intercepted_by_node_id")


class SendDispatch(Command):
    sender_id: int
    recipient_id: int
    content: DispatchContent
    medium: Medium = Medium.LETTER
    envoy_id: int | None = None
    forged: bool = False


class DispatchTarget(Command):
    message_id: int


class EditDispatch(Command):
    message_id: int
    state: DispatchState | None = None
    arrival_epoch: int | None = Field(default=None, ge=0)
    forged: bool | None = None
    misread: bool | None = None
    enciphered: bool | None = None
    intercepted_by_id: int | None = None
    hold: bool = True


class SetOpinion(Command):
    community_id: int
    subject_id: int
    subject: OpinionSubject = OpinionSubject.RULER
    approval: int = Field(ge=APPROVAL_MIN, le=APPROVAL_MAX)
    censored: bool | None = None
    hold: bool = True


class OpinionTarget(Command):
    community_id: int
    subject_id: int


class SetCipher(Command):
    owner_id: int
    strength: int = Field(default=30, ge=0, le=SPAN)
    hold: bool = True


class CipherTarget(Command):
    owner_id: int


class BreakCipher(Command):
    owner_id: int
    breaker_id: int
    known: bool = False


class BuildSignal(Command):
    owner_id: int
    kind: SignalKind
    from_region_id: int
    to_region_id: int


class SignalTarget(Command):
    link_id: int


class EditSignal(Command):
    link_id: int
    state: SignalState | None = None
    owner_id: int | None = None
    hold: bool = True


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def node(scope: PlayerScope, node_id: int | None, label: str) -> NodeRow:
    found = await scope.session.get(NodeRow, node_id) if node_id is not None else None
    if found is None:
        raise ValidationFailedError(f"{label} must be a living thing of the cosmos.")
    return found


async def region(scope: PlayerScope, region_id: int, label: str) -> EntityRow:
    found = await scope.session.get(EntityRow, region_id)
    if found is None or found.entity_type is not EntityType.REGION:
        raise ValidationFailedError(f"{label} must be a land.")
    return found


async def dispatch(scope: PlayerScope, message_id: int) -> MessageRow:
    row = await scope.session.get(MessageRow, message_id)
    if row is None or row.intent is not MessageIntent.DISPATCH:
        raise NotFoundError("No such message between the living.")
    return row


@player_action("dispatch:send", ActionKind.EDIT_RECORD)
async def post(scope: PlayerScope, command: SendDispatch) -> Effect:
    sender = await node(scope, command.sender_id, "The sender")
    recipient = await node(scope, command.recipient_id, "The recipient")
    if command.envoy_id is not None:
        await node(scope, command.envoy_id, "The envoy")
    if sender.id == recipient.id:
        raise ValidationFailedError("A message goes to someone else.")
    row = await send(
        await manual_context(scope.session, "dispatch.send"),
        sender.id,
        recipient.id,
        command.content,
        command.medium,
        envoy_id=command.envoy_id,
        forged=command.forged,
    )
    if row is None:
        raise ValidationFailedError(f"{sender.name} is held against change.")
    label = CONTENT_LABELS[command.content].lower()
    return Effect(
        f"{label.capitalize()} set out from {sender.name} to {recipient.name} by {MEDIUM_LABELS[command.medium].lower()}, due in epoch {row.arrival_epoch}.",
        target_node_id=sender.id,
        values={"message_id": row.id},
    )


@player_action("dispatch:edit", ActionKind.EDIT_RECORD)
async def edit_dispatch(scope: PlayerScope, command: EditDispatch) -> Effect:
    row = await dispatch(scope, command.message_id)
    touched = [name for name in ("state", "arrival_epoch", "forged", "misread", "enciphered") if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.intercepted_by_id is not None:
        row.intercepted_by_node_id = (await node(scope, command.intercepted_by_id, "The interceptor")).id
        touched.append("intercepted_by_node_id")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(
        f"The message is {row.state.value.replace('_', ' ') if row.state else 'set'}, due in epoch {row.arrival_epoch}.", target_node_id=row.sender_node_id
    )


@player_action("dispatch:hold", ActionKind.EDIT_RECORD)
async def hold_dispatch(scope: PlayerScope, command: EditDispatch) -> Effect:
    row = await dispatch(scope, command.message_id)
    row.locked = held(row.locked, list(DISPATCH_FIELDS), command.hold)
    await scope.session.flush()
    return Effect("The message is held where it is." if command.hold else "The message travels on.", target_node_id=row.sender_node_id)


@player_action("dispatch:delete", ActionKind.EDIT_RECORD)
async def delete_dispatch(scope: PlayerScope, command: DispatchTarget) -> Effect:
    row = await dispatch(scope, command.message_id)
    sender = row.sender_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The message was unmade, as if never written.", target_node_id=sender)


@player_action("opinion:set", ActionKind.EDIT_RECORD)
async def set_opinion(scope: PlayerScope, command: SetOpinion) -> Effect:
    community = await node(scope, command.community_id, "The community")
    subject = await node(scope, command.subject_id, "The subject")
    row = await scope.session.get(PublicOpinionRow, (community.id, subject.id))
    if row is None:
        row = PublicOpinionRow(
            community_node_id=community.id, subject_node_id=subject.id, subject=command.subject, approval=0, epoch=await scope.epoch(), locked=[]
        )
        scope.session.add(row)
    row.subject, row.approval = command.subject, command.approval
    if command.censored is not None:
        row.censored = command.censored
    row.locked = held(row.locked, ["approval"], command.hold)
    await scope.session.flush()
    return Effect(
        f"{community.name} now thinks {command.approval:+d} of {subject.name} as {SUBJECT_LABELS[command.subject].lower()}.", target_node_id=community.id
    )


@player_action("opinion:delete", ActionKind.EDIT_RECORD)
async def delete_opinion(scope: PlayerScope, command: OpinionTarget) -> Effect:
    row = await scope.session.get(PublicOpinionRow, (command.community_id, command.subject_id))
    if row is None:
        raise NotFoundError("That community holds no such opinion.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The opinion was wiped; it forms anew from the next epoch.", target_node_id=command.community_id)


@player_action("cipher:set", ActionKind.EDIT_RECORD)
async def set_cipher(scope: PlayerScope, command: SetCipher) -> Effect:
    owner = await node(scope, command.owner_id, "The owner")
    row = await scope.session.get(CipherRow, owner.id)
    if row is None:
        row = CipherRow(owner_node_id=owner.id, strength=command.strength, broken_by=[], attempts={}, since_epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    row.strength = command.strength
    row.locked = held(row.locked, ["strength"], command.hold)
    await scope.session.flush()
    return Effect(f"{owner.name} writes in a cipher of strength {command.strength}.", target_node_id=owner.id)


@player_action("cipher:break", ActionKind.EDIT_RECORD)
async def break_cipher(scope: PlayerScope, command: BreakCipher) -> Effect:
    row = await scope.session.get(CipherRow, command.owner_id)
    if row is None:
        raise NotFoundError("That owner writes in no cipher.")
    breaker = await node(scope, command.breaker_id, "The codebreaker")
    row.broken_by = sorted({*row.broken_by, breaker.id})
    row.break_known = command.known
    row.locked = held(row.locked, ["broken_by"], True)
    await scope.session.flush()
    return Effect(f"{breaker.name} now reads every message in this cipher.", target_node_id=command.owner_id)


@player_action("cipher:mend", ActionKind.EDIT_RECORD)
async def mend_cipher(scope: PlayerScope, command: CipherTarget) -> Effect:
    row = await scope.session.get(CipherRow, command.owner_id)
    if row is None:
        raise NotFoundError("That owner writes in no cipher.")
    row.broken_by, row.break_known, row.attempts = [], False, {}
    row.locked = held(row.locked, ["broken_by"], False)
    await scope.session.flush()
    return Effect("The cipher is made new; no one reads it now.", target_node_id=command.owner_id)


@player_action("cipher:delete", ActionKind.EDIT_RECORD)
async def delete_cipher(scope: PlayerScope, command: CipherTarget) -> Effect:
    row = await scope.session.get(CipherRow, command.owner_id)
    if row is None:
        raise NotFoundError("That owner writes in no cipher.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The cipher was forgotten; its messages go in plain words.", target_node_id=command.owner_id)


@player_action("signal:build", ActionKind.EDIT_RECORD)
async def build_signal(scope: PlayerScope, command: BuildSignal) -> Effect:
    owner = await node(scope, command.owner_id, "The owner")
    start = await region(scope, command.from_region_id, "The first end")
    end = await region(scope, command.to_region_id, "The far end")
    if start.id == end.id:
        raise ValidationFailedError("A signal link joins two lands.")
    row = SignalLinkRow(
        owner_node_id=owner.id,
        kind=command.kind,
        from_region_id=start.id,
        to_region_id=end.id,
        state=SignalState.ACTIVE,
        since_epoch=await scope.epoch(),
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{SIGNAL_LABELS[command.kind]} now link {start.name} and {end.name} for {owner.name}.", target_node_id=owner.id, values={"link_id": row.id})


@player_action("signal:edit", ActionKind.EDIT_RECORD)
async def edit_signal(scope: PlayerScope, command: EditSignal) -> Effect:
    row = await scope.session.get(SignalLinkRow, command.link_id)
    if row is None:
        raise NotFoundError("No such signal link.")
    touched: list[str] = []
    if command.state is not None:
        row.state = command.state
        touched.append("state")
    if command.owner_id is not None:
        row.owner_node_id = (await node(scope, command.owner_id, "The owner")).id
        touched.append("owner_node_id")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The link is {spoken(row.state)}.", target_node_id=row.owner_node_id)


@player_action("signal:delete", ActionKind.EDIT_RECORD)
async def delete_signal(scope: PlayerScope, command: SignalTarget) -> Effect:
    row = await scope.session.get(SignalLinkRow, command.link_id)
    if row is None:
        raise NotFoundError("No such signal link.")
    owner = row.owner_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The signal link was torn down.", target_node_id=owner)
