from aerona.agents.fate.naming import dialect_violation
from aerona.constants.player import ENTITY_TEXT_MAX_LENGTH
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.renames import rewrite_name
from aerona.services.integrity.folk_names import rename_belief
from aerona.services.narrative import clean_chronicle_text, collapse_spaces
from aerona.services.player import guards
from aerona.services.player.chronicle import hand
from aerona.services.player.lines import BELIEF_NAME_DERIVED, NAME_ACCEPTED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditChronicleLine(Command):
    chronicle_id: int
    text: str | None = None
    visible: bool | None = None


class BeliefTarget(Command):
    people_id: int
    son_id: int | None = None


class AcceptName(Command):
    entity_id: int
    name: str


@player_action("chronicle:edit", ActionKind.EDIT_RECORD)
async def edit_chronicle_line(scope: PlayerScope, command: EditChronicleLine) -> Effect:
    line = await scope.session.get(ChronicleRow, command.chronicle_id)
    if line is None:
        raise NotFoundError("No such chronicle line.")
    fields: list[str] = []
    if command.text is not None:
        text = collapse_spaces(clean_chronicle_text(command.text))[:ENTITY_TEXT_MAX_LENGTH]
        if not text:
            raise ValidationFailedError("A chronicle line cannot be emptied; hide it instead.")
        if text != line.text:
            line.text = text
            fields.append("text")
    if command.visible is not None and command.visible != line.visible:
        line.visible = command.visible
        fields.append("shown" if command.visible else "hidden")
    if not fields:
        raise ValidationFailedError("Nothing to change on this chronicle line.")
    await scope.session.flush()
    return Effect(f"The chronicle line was amended ({', '.join(fields)}).", values={"chronicle_id": line.id, "text": line.text, "visible": line.visible})


@player_action("belief:rename", ActionKind.EDIT_RECORD)
async def rename_folk_god(scope: PlayerScope, command: BeliefTarget) -> Effect:
    people = await guards.entity(scope.session, command.people_id)
    god_id = (await guards.son(scope.session, command.son_id)).id if command.son_id is not None else (await scope.creator()).id
    belief = await scope.session.get(FolkBeliefRow, (people.id, god_id))
    if belief is None:
        raise NotFoundError(f"{people.name} tells no tale of this god yet.")
    old = belief.local_name
    name = await rename_belief(scope.session, scope.rules, belief, Namer(scope.session, scope.rules), fresh=True)
    if name is None:
        raise ValidationFailedError(f"The language of {people.name} gives no other name for this god.")
    ctx = await scope.context("rename_folk_god")
    text = await hand(ctx, await scope.creator(), BELIEF_NAME_DERIVED, ids=[people.id], people=people.name, name=name)
    return Effect(text, people.id, values={"old": old, "name": name})


@player_action("name:accept", ActionKind.EDIT_RECORD)
async def accept_name(scope: PlayerScope, command: AcceptName) -> Effect:
    record = await guards.entity(scope.session, command.entity_id)
    proposed = " ".join(command.name.split())[:NAME_MAX_LENGTH]
    if not proposed:
        raise ValidationFailedError("A name cannot be empty.")
    world = await scope.session.get(WorldRow, record.world_id)
    violation = dialect_violation(record.id, proposed, world.phonology if world is not None else None)
    old = record.name
    if proposed != old and await NameRepository(scope.session).is_taken(proposed, record.id):
        raise ValidationFailedError(f"The name {proposed} already belongs to another.")
    await EntityRepository(scope.session).add_flag(record.id, EntityFlag.FIXED_NAME, await scope.epoch())
    if proposed != old:
        await EntityRepository(scope.session).rename(record, proposed)
        await rewrite_name(scope.session, record.id, old, record.name)
    await scope.session.flush()
    ctx = await scope.context("accept_name")
    text = await hand(ctx, await scope.creator(), NAME_ACCEPTED, ids=[record.id], old=old, new=record.name)
    letters = ", ".join(violation.letters) if violation is not None else ""
    return Effect(text, record.id, values={"overridden_letters": letters})
