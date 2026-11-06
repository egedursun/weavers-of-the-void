from pydantic import Field

from aerona.catalog.ethics import ACT_LABELS, STANCE_LABELS
from aerona.catalog.preferences import PREFERENCE_LABELS, SPECIES_KINDS, STATIC_TARGETS, target_label
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureHonourRow, PreferenceRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind, EthicalStance, HonourModel, PreferenceKind
from aerona.engine.mind.ethics import MODEL_FIELD, STANCE_FIELD, write_stance
from aerona.engine.mind.preferences import STRENGTH_FIELD, write_pref
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PREFERRING = frozenset({EntityType.MORTAL, EntityType.PEOPLE})
ETHICAL = frozenset({EntityType.PEOPLE, EntityType.CULT})
SPAN = 100


class SetPreference(Command):
    holder_id: int
    kind: PreferenceKind
    target: str = Field(min_length=1, max_length=120)
    strength: int = Field(ge=-SPAN, le=SPAN)
    hold: bool = True


class PreferenceTarget(Command):
    preference_id: int


class SetStance(Command):
    holder_id: int
    act: ActKind
    stance: EthicalStance
    hold: bool = True


class SetHonour(Command):
    holder_id: int
    model: HonourModel
    hold: bool = True


async def holder_of(scope: PlayerScope, node_id: int, allowed: frozenset[EntityType], reason: str) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type not in allowed:
        raise ValidationFailedError(reason)
    return found


def held(locked: list[str] | None, field: str, hold: bool) -> list[str]:
    fields = set(locked or [])
    if hold:
        fields.add(field)
    else:
        fields.discard(field)
    return sorted(fields)


@player_action("preference:set", ActionKind.OTHER)
async def set_preference(scope: PlayerScope, command: SetPreference) -> Effect:
    holder = await holder_of(scope, command.holder_id, PREFERRING, "Only mortals and peoples hold likes and dislikes.")
    node: int | None = None
    if command.kind in SPECIES_KINDS:
        target = await scope.session.get(EntityRow, int(command.target)) if command.target.isdigit() else None
        wanted = EntityType.SPECIES if command.kind is PreferenceKind.CREATURE else EntityType.RESOURCE
        if target is None or target.entity_type is not wanted:
            raise ValidationFailedError(f"A {PREFERENCE_LABELS[command.kind].lower()} must be a {wanted.value} of this world.")
        node = target.id
    elif command.target not in STATIC_TARGETS[command.kind]:
        raise ValidationFailedError(f"That is not a {PREFERENCE_LABELS[command.kind].lower()}.")
    row = await write_pref(scope.session, holder.id, command.kind, command.target, command.strength, target_node_id=node)
    if row is None:
        raise ValidationFailedError(f"{holder.name} is held from changing.")
    row.strength = command.strength
    row.locked = held(row.locked, STRENGTH_FIELD, command.hold)
    await scope.session.flush()
    feeling = "loves" if command.strength > 0 else "hates" if command.strength < 0 else "is indifferent to"
    return Effect(f"{holder.name} {feeling} {target_label(command.kind, command.target)}.", target_node_id=holder.id, values={"preference_id": row.id})


@player_action("preference:remove", ActionKind.OTHER)
async def remove_preference(scope: PlayerScope, command: PreferenceTarget) -> Effect:
    row = await scope.session.get(PreferenceRow, command.preference_id)
    if row is None:
        raise NotFoundError("No such preference.")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The like or dislike was taken away.", target_node_id=holder)


@player_action("ethics:set", ActionKind.OTHER)
async def set_stance(scope: PlayerScope, command: SetStance) -> Effect:
    holder = await holder_of(scope, command.holder_id, ETHICAL, "Only peoples and cults hold ethics.")
    row = await write_stance(scope.session, holder.id, command.act, command.stance, await scope.epoch())
    if row is None:
        raise ValidationFailedError(f"{holder.name} is held from changing.")
    row.stance = command.stance
    row.locked = held(row.locked, STANCE_FIELD, command.hold)
    await scope.session.flush()
    return Effect(f"For the {holder.name}, {ACT_LABELS[command.act].lower()} is now {STANCE_LABELS[command.stance].lower()}.", target_node_id=holder.id)


@player_action("ethics:honour", ActionKind.OTHER)
async def set_honour(scope: PlayerScope, command: SetHonour) -> Effect:
    holder = await holder_of(scope, command.holder_id, frozenset({EntityType.PEOPLE}), "Only peoples hold an honour model.")
    row = await scope.session.get(CultureHonourRow, holder.id)
    if row is None:
        row = CultureHonourRow(entity_id=holder.id, model=command.model, locked=[])
        scope.session.add(row)
    row.model = command.model
    row.locked = held(row.locked, MODEL_FIELD, command.hold)
    await scope.session.flush()
    return Effect(f"The {holder.name} now live by {command.model.value}.", target_node_id=holder.id)
