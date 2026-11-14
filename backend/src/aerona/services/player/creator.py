from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.creator import CreatorMoodLabel, CreatorPassion
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.engine.gods.mood import MoodState, mood_of
from aerona.engine.gods.reputation import ReputationAxes
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.gods import creator_mood, reputation
from aerona.services.player import guards
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import CREATOR_EDITED, NOTE_STORED
from aerona.services.player.ports import ContentJob, ContentJobKind
from aerona.services.player.runtime import FreeJob, PlayerRuntime, submit_free, unavailable
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action

CREATOR_TEXT_FIELDS = ("title", "appearance", "temperament", "image_prompt")
PROFILE_TRACE_KINDS = (
    ChronicleKind.CREATOR_HAND,
    ChronicleKind.WORLD_BIRTH,
    ChronicleKind.COUNCIL,
    ChronicleKind.DIVINE_SIGN,
    ChronicleKind.ORDER,
)
CONTENT_LOCKS = {
    ContentJobKind.CREATOR_PORTRAIT: "creator:portrait",
    ContentJobKind.CREATOR_EPIC: "creator:epic",
    ContentJobKind.CREATOR_DEEPEN: "creator:deepen",
}
CONTENT_DONE = {
    ContentJobKind.CREATOR_PORTRAIT: "The Creator's likeness was redrawn.",
    ContentJobKind.CREATOR_EPIC: "The Creator's epic was written.",
    ContentJobKind.CREATOR_DEEPEN: "The Creator was deepened.",
    ContentJobKind.SON_EPIC: "A son's epic was written.",
    ContentJobKind.FOREIGN_GOD_DEEPEN: "A foreign god was deepened.",
    ContentJobKind.FOREIGN_GOD_AWAKENED: "An awakened foreign god was rewritten.",
}


class EditCreator(Command):
    title: str | None = None
    appearance: str | None = None
    temperament: str | None = None
    image_prompt: str | None = None


class CreatorNote(Command):
    text: str = ""


class SetPassions(Command):
    passions: tuple[CreatorPassion, ...] = ()
    automatic: bool = False


class NudgeReputation(Command):
    son_id: int
    love: int = 0
    fear: int = 0
    forgotten: int = 0


class SetMood(Command):
    contentment: int | None = None
    anger: int | None = None
    interest: int | None = None
    loneliness: int | None = None


class CreatorContent(Command):
    kind: ContentJobKind = ContentJobKind.CREATOR_PORTRAIT


class SonEpic(Command):
    son_id: int


class CreatorProfile(BaseModel):
    name: str
    title: str | None
    appearance: str | None
    temperament: str | None
    image_prompt: str | None
    note: str | None
    essence: int
    mood: dict[str, int]
    mood_label: CreatorMoodLabel
    faith: int
    cult: list[dict[str, Any]] = Field(default_factory=list)
    peoples_views: list[dict[str, Any]] = Field(default_factory=list)
    traces: list[dict[str, Any]] = Field(default_factory=list)


def _clamp(value: int) -> int:
    return max(PERCENT_MIN, min(PERCENT_MAX, value))


@player_action("creator:edit", ActionKind.EDIT_CREATOR)
async def edit_creator(scope: PlayerScope, command: EditCreator) -> Effect:
    creator = await scope.creator()
    changed: list[str] = []
    for name in CREATOR_TEXT_FIELDS:
        value = getattr(command, name)
        if value is None:
            continue
        setattr(creator, name, value or None)
        changed.append(name.replace("_", " "))
    if not changed:
        raise ValidationFailedError("Nothing to change: give a title, appearance, temperament or image prompt.")
    ctx = await scope.context("edit_creator")
    message = await tell(ctx, CREATOR_EDITED, creator=creator.name, fields=", ".join(changed))
    return Effect(message, creator.id)


@player_action("creator:note", ActionKind.EDIT_CREATOR)
async def set_creator_note(scope: PlayerScope, command: CreatorNote) -> Effect:
    creator = await scope.creator()
    creator.note = guards.clip(command.text, scope.rules.god_actions.note_max_chars) or None
    if creator.note is None:
        return Effect("The standing note was cleared.", creator.id)
    ctx = await scope.context("creator_note")
    return Effect(await tell(ctx, NOTE_STORED, creator=creator.name), creator.id, values={"length": len(creator.note)})


@player_action("creator:passions", ActionKind.SET_PASSIONS)
async def set_passions(scope: PlayerScope, command: SetPassions) -> Effect:
    view = await reputation.set_passions(scope.session, scope.rules, list(command.passions), command.automatic)
    creator = await scope.creator()
    label = ", ".join(passion.value for passion in view.passions) or "read from the creator's deeds"
    mode = "automatic" if view.automatic else "chosen"
    return Effect(f"{creator.name}'s passions ({mode}): {label}.", creator.id)


@player_action("creator:reputation", ActionKind.PUSH_REPUTATION)
async def nudge_reputation(scope: PlayerScope, command: NudgeReputation) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    if not (command.love or command.fear or command.forgotten):
        raise ValidationFailedError("Nothing to change: move love, fear or forgottenness.")
    result = await reputation.nudge_reputation(scope.session, scope.rules, son.id, ReputationAxes(command.love, command.fear, command.forgotten))
    return Effect(
        f"{son.name} now sees the Creator with love {result.love}, fear {result.fear} and forgottenness {result.forgotten}.",
        son.id,
        values={"love": result.love, "fear": result.fear, "forgotten": result.forgotten},
    )


@player_action("creator:mood", ActionKind.EDIT_CREATOR)
async def set_mood(scope: PlayerScope, command: SetMood) -> Effect:
    current = mood_of(await scope.creator())
    state = MoodState(
        contentment=_clamp(command.contentment if command.contentment is not None else current.contentment),
        anger=_clamp(command.anger if command.anger is not None else current.anger),
        interest=_clamp(command.interest if command.interest is not None else current.interest),
        loneliness=_clamp(command.loneliness if command.loneliness is not None else current.loneliness),
        temperament=current.temperament,
    )
    view = await creator_mood.set_mood(scope.session, scope.rules, state)
    return Effect(f"The Creator's mood is now {view.label.value}.", (await scope.creator()).id, values={"label": view.label.value})


async def creator_profile(scope: PlayerScope) -> CreatorProfile:
    creator = await scope.creator()
    mood = await creator_mood.read_mood(scope.session, scope.rules)
    cult = await creator_mood.read_cult(scope.session, scope.rules)
    views = await scope.session.execute(
        select(FolkBeliefRow, EntityRow.name).join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id).where(FolkBeliefRow.god_node_id == creator.id)
    )
    traces = await scope.session.scalars(
        select(ChronicleRow)
        .where(ChronicleRow.kind.in_(PROFILE_TRACE_KINDS), shown_lines())
        .order_by(ChronicleRow.id.desc())
        .limit(scope.rules.server.god_traces)
    )
    return CreatorProfile(
        name=creator.name,
        title=creator.title,
        appearance=creator.appearance,
        temperament=creator.temperament,
        image_prompt=creator.image_prompt,
        note=creator.note,
        essence=creator.essence,
        mood={"contentment": mood.state.contentment, "anger": mood.state.anger, "interest": mood.state.interest, "loneliness": mood.state.loneliness},
        mood_label=mood.label,
        faith=cult.effect.faith,
        cult=[{"id": member.id, "name": member.name, "type": member.entity_type.value} for member in cult.members],
        peoples_views=[
            {
                "people_id": belief.people_entity_id,
                "people": people,
                "name": belief.local_name,
                "account": belief.account,
                "misconception": belief.misconception,
            }
            for belief, people in sorted(views, key=lambda row: -row[0].epoch)
        ],
        traces=[{"epoch": row.epoch, "year": row.year, "kind": row.kind.value, "text": row.text} for row in traces],
    )


def _content_work(runtime: PlayerRuntime, job: ContentJob) -> Any:
    writer = runtime.ports.writer
    if writer is None:
        raise unavailable("Writing")

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, job.kind.value)
        summary = await writer.write(job)
        runtime.bus.publish(
            EventKind.EPIC_WRITTEN if job.kind in (ContentJobKind.CREATOR_EPIC, ContentJobKind.SON_EPIC) else EventKind.SYSTEM_NOTE,
            {
                "kind": job.kind.value,
                "target_id": job.target_id,
                "text": summary or CONTENT_DONE[job.kind],
            },
        )
        return {"summary": summary}

    return work


async def write_creator_content(runtime: PlayerRuntime, rules: Rules, command: CreatorContent) -> ActionOutcome:
    if command.kind not in CONTENT_LOCKS:
        raise ValidationFailedError("Choose the portrait, the epic or the deepening of the Creator.")
    job = ContentJob(command.kind, None)
    return await submit_free(
        runtime, FreeJob(f"creator:{command.kind.value}", JobKind.CONTENT, CONTENT_LOCKS[command.kind]), command, _content_work(runtime, job)
    )


async def write_son_epic(runtime: PlayerRuntime, rules: Rules, command: SonEpic) -> ActionOutcome:
    async with runtime.database.read() as session:
        son = await guards.son(session, command.son_id)
    job = ContentJob(ContentJobKind.SON_EPIC, son.id)
    return await submit_free(runtime, FreeJob("son:epic", JobKind.CONTENT, f"son:{son.id}:epic"), command, _content_work(runtime, job))
