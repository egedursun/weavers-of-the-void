from pydantic import Field

from aerona.catalog.thoughts import DREAM_LABELS, EMOTIONS, THOUGHTS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import DreamRow, GriefRow, ThoughtRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.mind import DreamKind, DreamReading, Emotion, GriefStage, ThoughtKind
from aerona.engine.mind.book import ensure_mind_row
from aerona.engine.mind.dreams import DreamDraft, record_dream
from aerona.engine.mind.grief import start_grief
from aerona.engine.mind.thoughts import MOOD_FIELD, mood_state, think, thinker
from aerona.engine.mortal.profile import ensure_profile
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

DREAM_THOUGHTS = {
    DreamKind.ORDINARY: ThoughtKind.HAD_GOOD_DREAM,
    DreamKind.NIGHTMARE: ThoughtKind.HAD_NIGHTMARE,
    DreamKind.LONGING: ThoughtKind.DREAMED_OF_LONGING,
    DreamKind.PROPHETIC: ThoughtKind.RECEIVED_VISITATION,
    DreamKind.VISITATION: ThoughtKind.RECEIVED_VISITATION,
    DreamKind.SHARED: ThoughtKind.HAD_GOOD_DREAM,
}


class SendThought(Command):
    holder_id: int
    kind: ThoughtKind = ThoughtKind.SENT_BY_THE_CREATOR
    emotion: Emotion | None = None
    intensity: int = Field(default=50, ge=1, le=PERCENT)
    subject_id: int | None = None


class ThoughtTarget(Command):
    thought_id: int


class EditThought(ThoughtTarget):
    intensity: int | None = Field(default=None, ge=0, le=PERCENT)
    decay_pct: int | None = Field(default=None, ge=0, le=PERCENT)
    emotion: Emotion | None = None
    subject_id: int | None = None
    clear_subject: bool = False


class SetMood(Command):
    node_id: int
    score: int = Field(ge=-PERCENT, le=PERCENT)
    hold: bool = True


class StartGrief(Command):
    mourner_id: int
    deceased_id: int
    strength: int = Field(default=70, ge=1, le=PERCENT)


class GriefTarget(Command):
    grief_id: int


class EditGrief(GriefTarget):
    stage: GriefStage | None = None
    strength: int | None = Field(default=None, ge=0, le=PERCENT)
    length_epochs: int | None = Field(default=None, ge=1, le=PERCENT)


class SendDream(Command):
    dreamer_id: int
    kind: DreamKind = DreamKind.VISITATION
    intensity: int = Field(default=60, ge=1, le=PERCENT)
    sender_id: int | None = None
    partner_id: int | None = None
    reading: DreamReading = DreamReading.UNREAD


class DreamTarget(Command):
    dream_id: int


class EditDream(DreamTarget):
    kind: DreamKind | None = None
    intensity: int | None = Field(default=None, ge=0, le=PERCENT)
    reading: DreamReading | None = None
    reading_true: bool | None = None
    recurring: bool | None = None
    reader_id: int | None = None
    clear_reader: bool = False


async def mortal_of(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await thinker(scope.session, node_id)
    if found is None:
        raise ValidationFailedError("Only living mortals think, grieve and dream.")
    return found


async def exists(scope: PlayerScope, node_id: int | None) -> None:
    if node_id is not None and await scope.session.get(NodeRow, node_id) is None:
        raise ValidationFailedError("That record does not exist.")


async def thought_row(scope: PlayerScope, thought_id: int) -> ThoughtRow:
    row = await scope.session.get(ThoughtRow, thought_id)
    if row is None:
        raise NotFoundError("No such thought.")
    return row


@player_action("thought:send", ActionKind.OTHER)
async def send_thought(scope: PlayerScope, command: SendThought) -> Effect:
    mortal = await mortal_of(scope, command.holder_id)
    await exists(scope, command.subject_id)
    await ensure_mind_row(scope.session, mortal, await scope.epoch())
    row = await think(
        scope.session,
        scope.rules,
        mortal.id,
        command.kind,
        await scope.epoch(),
        subject_id=command.subject_id,
        intensity=command.intensity,
        emotion=command.emotion,
        forced=True,
    )
    if row is None:
        raise ValidationFailedError(f"{mortal.name}'s temperament smothers that feeling entirely.")
    feeling = EMOTIONS[row.emotion].label.lower()
    return Effect(f"{mortal.name} now feels {feeling}: {THOUGHTS[row.kind].label.lower()}.", target_node_id=mortal.id, values={"thought_id": row.id})


@player_action("thought:edit", ActionKind.OTHER)
async def edit_thought(scope: PlayerScope, command: EditThought) -> Effect:
    row = await thought_row(scope, command.thought_id)
    await exists(scope, command.subject_id)
    if command.intensity is not None:
        row.intensity = command.intensity
    if command.decay_pct is not None:
        row.decay_pct = command.decay_pct
    if command.emotion is not None:
        row.emotion = command.emotion
    if command.subject_id is not None:
        row.subject_node_id = command.subject_id
    if command.clear_subject:
        row.subject_node_id = None
    await scope.session.flush()
    return Effect(f"The thought {THOUGHTS[row.kind].label.lower()} was reshaped.", target_node_id=row.holder_node_id)


@player_action("thought:remove", ActionKind.OTHER)
async def remove_thought(scope: PlayerScope, command: ThoughtTarget) -> Effect:
    row = await thought_row(scope, command.thought_id)
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The thought was taken away.", target_node_id=holder)


@player_action("thought:mood", ActionKind.OTHER)
async def set_mood(scope: PlayerScope, command: SetMood) -> Effect:
    mortal = await mortal_of(scope, command.node_id)
    profile, _ = await ensure_profile(scope.session, mortal.id, await scope.epoch())
    profile.mood_score = command.score
    profile.mood = mood_state(scope.rules, command.score)
    locked = set(profile.locked or [])
    if command.hold:
        locked.add(MOOD_FIELD)
    else:
        locked.discard(MOOD_FIELD)
    profile.locked = sorted(locked)
    await scope.session.flush()
    return Effect(f"{mortal.name} is now {profile.mood.value}.", target_node_id=mortal.id)


async def grief_row(scope: PlayerScope, grief_id: int) -> GriefRow:
    row = await scope.session.get(GriefRow, grief_id)
    if row is None:
        raise NotFoundError("No such grief.")
    return row


@player_action("grief:start", ActionKind.OTHER)
async def begin_grief(scope: PlayerScope, command: StartGrief) -> Effect:
    mortal = await mortal_of(scope, command.mourner_id)
    lost = await scope.session.get(EntityRow, command.deceased_id)
    if lost is None or lost.id == mortal.id:
        raise ValidationFailedError("A grief needs someone else to mourn.")
    await ensure_mind_row(scope.session, mortal, await scope.epoch())
    row = await start_grief(scope.session, scope.rules, mortal.id, lost.id, strength=command.strength, epoch=await scope.epoch(), forced=True)
    if row is None:
        raise ValidationFailedError(f"{mortal.name} cannot grieve now.")
    return Effect(f"{mortal.name} mourns {lost.name}.", target_node_id=mortal.id, values={"grief_id": row.id})


@player_action("grief:edit", ActionKind.OTHER)
async def edit_grief(scope: PlayerScope, command: EditGrief) -> Effect:
    row = await grief_row(scope, command.grief_id)
    if command.stage is not None and command.stage is not row.stage:
        row.stage, row.stage_epoch = command.stage, await scope.epoch()
    if command.strength is not None:
        row.strength = command.strength
    if command.length_epochs is not None:
        row.length_epochs = command.length_epochs
    await scope.session.flush()
    return Effect(f"The grief is now {row.stage.value}.", target_node_id=row.mourner_node_id)


@player_action("grief:remove", ActionKind.OTHER)
async def remove_grief(scope: PlayerScope, command: GriefTarget) -> Effect:
    row = await grief_row(scope, command.grief_id)
    mourner = row.mourner_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The grief was lifted.", target_node_id=mourner)


async def dream_row(scope: PlayerScope, dream_id: int) -> DreamRow:
    row = await scope.session.get(DreamRow, dream_id)
    if row is None:
        raise NotFoundError("No such dream.")
    return row


@player_action("dream:send", ActionKind.OTHER)
async def send_dream(scope: PlayerScope, command: SendDream) -> Effect:
    mortal = await mortal_of(scope, command.dreamer_id)
    for other in (command.sender_id, command.partner_id):
        await exists(scope, other)
    epoch = await scope.epoch()
    await ensure_mind_row(scope.session, mortal, epoch)
    content = tuple(node for node in (command.sender_id, command.partner_id) if node is not None)
    draft = DreamDraft(command.kind, command.intensity, content, sender_id=command.sender_id, partner_id=command.partner_id)
    row = await record_dream(scope.session, mortal.id, draft, epoch, forced=True)
    if row is None:
        raise ValidationFailedError(f"{mortal.name} cannot dream now.")
    row.reading = command.reading
    await think(
        scope.session, scope.rules, mortal.id, DREAM_THOUGHTS[command.kind], epoch, subject_id=command.sender_id, intensity=command.intensity, forced=True
    )
    await scope.session.flush()
    return Effect(f"{mortal.name} dreamed: {DREAM_LABELS[command.kind].lower()}.", target_node_id=mortal.id, values={"dream_id": row.id})


@player_action("dream:edit", ActionKind.OTHER)
async def edit_dream(scope: PlayerScope, command: EditDream) -> Effect:
    row = await dream_row(scope, command.dream_id)
    await exists(scope, command.reader_id)
    if command.kind is not None:
        row.kind = command.kind
    if command.intensity is not None:
        row.intensity = command.intensity
    if command.reading is not None:
        row.reading = command.reading
    if command.reading_true is not None:
        row.reading_true = command.reading_true
    if command.recurring is not None:
        row.recurring = command.recurring
    if command.reader_id is not None:
        row.reader_node_id = command.reader_id
    if command.clear_reader:
        row.reader_node_id = None
    await scope.session.flush()
    return Effect("The dream was reshaped.", target_node_id=row.dreamer_node_id)


@player_action("dream:remove", ActionKind.OTHER)
async def remove_dream(scope: PlayerScope, command: DreamTarget) -> Effect:
    row = await dream_row(scope, command.dream_id)
    dreamer = row.dreamer_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The dream was forgotten.", target_node_id=dreamer)
