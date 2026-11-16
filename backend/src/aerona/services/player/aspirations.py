from pydantic import Field
from sqlalchemy import select

from aerona.catalog.aspirations import FEARS, GOALS, INSPIRATION_LABELS, PERKS, WANTS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import FearRow, InspirationRow, LifeDreamRow, PerkRow, WantRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import DreamState, FearKind, FocusKind, InspirationKind, InspirationState, LifeGoal, PerkKind, WantKind
from aerona.engine.mind.aspirations import CONVICTION_FIELD, FOCUS_FIELD, drop_perk, perk_modifier
from aerona.engine.mind.book import ensure_mind_row
from aerona.engine.mortal.profile import ensure_profile
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class MortalTarget(Command):
    holder_id: int


class SetDream(MortalTarget):
    goal: LifeGoal
    target_id: int | None = None
    progress: int = Field(default=0, ge=0, le=PERCENT)
    state: DreamState = DreamState.PURSUING
    hold: bool = True


class AddWant(MortalTarget):
    kind: WantKind
    target_id: int | None = None


class WantTarget(Command):
    want_id: int


class EditWant(WantTarget):
    fulfilled: bool | None = None
    target_id: int | None = None
    hold: bool | None = None


class SetFear(MortalTarget):
    kind: FearKind
    strength: int = Field(default=50, ge=0, le=PERCENT)
    target_id: int | None = None


class FearTarget(Command):
    fear_id: int


class SetFocus(MortalTarget):
    focus: FocusKind | None = None
    hold: bool = True


class PerkTarget(MortalTarget):
    perk: PerkKind


class Inspire(MortalTarget):
    kind: InspirationKind
    material: str | None = Field(default=None, max_length=120)
    epochs: int = Field(default=2, ge=1, le=50)


class InspirationTarget(Command):
    inspiration_id: int


class EditInspiration(InspirationTarget):
    state: InspirationState | None = None
    deadline_epoch: int | None = Field(default=None, ge=0)
    material: str | None = Field(default=None, max_length=120)


class SetConviction(MortalTarget):
    value: int = Field(ge=0, le=PERCENT)
    hold: bool = True


async def mortal_of(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.MORTAL or found.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only living mortals dream, want, fear and take up a focus.")
    await ensure_mind_row(scope.session, found, await scope.epoch())
    return found


async def exists(scope: PlayerScope, node_id: int | None) -> None:
    if node_id is not None and await scope.session.get(NodeRow, node_id) is None:
        raise ValidationFailedError("That record does not exist.")


@player_action("aspiration:dream", ActionKind.OTHER)
async def set_dream(scope: PlayerScope, command: SetDream) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    await exists(scope, command.target_id)
    epoch = await scope.epoch()
    row = await scope.session.get(LifeDreamRow, mortal.id)
    if row is None:
        row = LifeDreamRow(holder_node_id=mortal.id, goal=command.goal, milestones=[], progress=0, state=command.state, started_epoch=epoch, locked=[])
        scope.session.add(row)
    if row.goal is not command.goal:
        row.milestones, row.started_epoch = [], epoch
    row.goal, row.target_node_id, row.progress, row.state = command.goal, command.target_id, command.progress, command.state
    row.ended_epoch = None if command.state is DreamState.PURSUING else epoch
    row.milestones = [mark for mark in (33, 66, 100) if command.progress >= mark]
    row.locked = ["progress"] if command.hold else []
    await scope.session.flush()
    return Effect(f"{mortal.name} now dreams: {GOALS[command.goal].label.lower()}.", target_node_id=mortal.id)


@player_action("aspiration:dream_remove", ActionKind.OTHER)
async def remove_dream(scope: PlayerScope, command: MortalTarget) -> Effect:
    row = await scope.session.get(LifeDreamRow, command.holder_id)
    if row is None:
        raise NotFoundError("That mortal has no life's dream.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The life's dream was taken away.", target_node_id=command.holder_id)


@player_action("aspiration:want", ActionKind.OTHER)
async def add_want(scope: PlayerScope, command: AddWant) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    await exists(scope, command.target_id)
    row = WantRow(holder_node_id=mortal.id, kind=command.kind, target_node_id=command.target_id, epoch=await scope.epoch(), locked=["kind"])
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{mortal.name} now wants to {WANTS[command.kind].label.lower()}.", target_node_id=mortal.id, values={"want_id": row.id})


async def want_row(scope: PlayerScope, want_id: int) -> WantRow:
    row = await scope.session.get(WantRow, want_id)
    if row is None:
        raise NotFoundError("No such want.")
    return row


@player_action("aspiration:want_edit", ActionKind.OTHER)
async def edit_want(scope: PlayerScope, command: EditWant) -> Effect:
    row = await want_row(scope, command.want_id)
    await exists(scope, command.target_id)
    if command.fulfilled is not None:
        row.fulfilled_epoch = await scope.epoch() if command.fulfilled else None
    if command.target_id is not None:
        row.target_node_id = command.target_id
    if command.hold is not None:
        row.locked = ["kind"] if command.hold else []
    await scope.session.flush()
    return Effect(f"The want to {WANTS[row.kind].label.lower()} was changed.", target_node_id=row.holder_node_id)


@player_action("aspiration:want_remove", ActionKind.OTHER)
async def remove_want(scope: PlayerScope, command: WantTarget) -> Effect:
    row = await want_row(scope, command.want_id)
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The want was taken away.", target_node_id=holder)


@player_action("aspiration:fear", ActionKind.OTHER)
async def set_fear(scope: PlayerScope, command: SetFear) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    await exists(scope, command.target_id)
    row = await scope.session.scalar(select(FearRow).where(FearRow.holder_node_id == mortal.id, FearRow.kind == command.kind))
    if row is None:
        row = FearRow(holder_node_id=mortal.id, kind=command.kind, strength=command.strength, since_epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    row.strength, row.target_node_id = command.strength, command.target_id
    await scope.session.flush()
    return Effect(f"{mortal.name} now fears {FEARS[command.kind].label.lower()} ({command.strength}).", target_node_id=mortal.id, values={"fear_id": row.id})


@player_action("aspiration:fear_remove", ActionKind.OTHER)
async def remove_fear(scope: PlayerScope, command: FearTarget) -> Effect:
    row = await scope.session.get(FearRow, command.fear_id)
    if row is None:
        raise NotFoundError("No such fear.")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The fear was lifted.", target_node_id=holder)


def held_fields(locked: list[str] | None, field: str, hold: bool) -> list[str]:
    fields = set(locked or [])
    if hold:
        fields.add(field)
    else:
        fields.discard(field)
    return sorted(fields)


@player_action("aspiration:focus", ActionKind.OTHER)
async def set_focus(scope: PlayerScope, command: SetFocus) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    profile, _ = await ensure_profile(scope.session, mortal.id, await scope.epoch())
    profile.focus = command.focus
    profile.locked = held_fields(profile.locked, FOCUS_FIELD, command.hold)
    for perk, spec in PERKS.items():
        if spec.focus is not command.focus:
            await drop_perk(scope.session, mortal.id, perk)
    await scope.session.flush()
    label = command.focus.value if command.focus is not None else "no focus"
    return Effect(f"{mortal.name} now lives for {label}.", target_node_id=mortal.id)


@player_action("aspiration:perk", ActionKind.OTHER)
async def grant_perk(scope: PlayerScope, command: PerkTarget) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    if await scope.session.get(PerkRow, (mortal.id, command.perk)) is not None:
        raise ValidationFailedError(f"{mortal.name} already has that perk.")
    epoch = await scope.epoch()
    scope.session.add(PerkRow(holder_node_id=mortal.id, perk=command.perk, epoch=epoch))
    await perk_modifier(scope.session, mortal.id, command.perk, epoch)
    await scope.session.flush()
    return Effect(f"{mortal.name} gained the perk {PERKS[command.perk].label}.", target_node_id=mortal.id)


@player_action("aspiration:perk_remove", ActionKind.OTHER)
async def remove_perk(scope: PlayerScope, command: PerkTarget) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    await drop_perk(scope.session, mortal.id, command.perk)
    await scope.session.flush()
    return Effect(f"{mortal.name} lost the perk {PERKS[command.perk].label}.", target_node_id=mortal.id)


@player_action("aspiration:inspire", ActionKind.OTHER)
async def inspire(scope: PlayerScope, command: Inspire) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    epoch = await scope.epoch()
    row = InspirationRow(
        holder_node_id=mortal.id,
        kind=command.kind,
        material=command.material,
        started_epoch=epoch,
        deadline_epoch=epoch + command.epochs,
        state=InspirationState.BURNING,
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"{mortal.name} is seized: {INSPIRATION_LABELS[command.kind].lower()}.", target_node_id=mortal.id, values={"inspiration_id": row.id})


async def inspiration_row(scope: PlayerScope, inspiration_id: int) -> InspirationRow:
    row = await scope.session.get(InspirationRow, inspiration_id)
    if row is None:
        raise NotFoundError("No such inspiration.")
    return row


@player_action("aspiration:inspiration_edit", ActionKind.OTHER)
async def edit_inspiration(scope: PlayerScope, command: EditInspiration) -> Effect:
    row = await inspiration_row(scope, command.inspiration_id)
    if command.state is not None:
        row.state = command.state
    if command.deadline_epoch is not None:
        row.deadline_epoch = command.deadline_epoch
    if command.material is not None:
        row.material = command.material
    await scope.session.flush()
    return Effect("The inspiration was changed.", target_node_id=row.holder_node_id)


@player_action("aspiration:inspiration_remove", ActionKind.OTHER)
async def remove_inspiration(scope: PlayerScope, command: InspirationTarget) -> Effect:
    row = await inspiration_row(scope, command.inspiration_id)
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The inspiration was quenched.", target_node_id=holder)


@player_action("aspiration:conviction", ActionKind.OTHER)
async def set_conviction(scope: PlayerScope, command: SetConviction) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    profile, _ = await ensure_profile(scope.session, mortal.id, await scope.epoch())
    profile.conviction = command.value
    profile.locked = held_fields(profile.locked, CONVICTION_FIELD, command.hold)
    await scope.session.flush()
    return Effect(f"{mortal.name}'s conviction is now {command.value}.", target_node_id=mortal.id)
