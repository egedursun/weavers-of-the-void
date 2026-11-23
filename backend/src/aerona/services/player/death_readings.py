from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import DeathReadingRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mortal import DeathCause, DeathReading
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

READING_LOCK = "reading"


class ReadingTarget(Command):
    people_id: int
    cause: DeathCause


class SetReading(ReadingTarget):
    reading: DeathReading
    hold: bool | None = None


async def people_of(scope: PlayerScope, people_id: int) -> EntityRow:
    people = await scope.session.get(EntityRow, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE:
        raise NotFoundError("No such people.")
    return people


def held_as(row: DeathReadingRow, hold: bool | None) -> None:
    if hold is None:
        return
    row.locked = [READING_LOCK] if hold else []


@player_action("death_reading:create", ActionKind.EDIT_RECORD)
async def create_reading(scope: PlayerScope, command: SetReading) -> Effect:
    people = await people_of(scope, command.people_id)
    row = await scope.session.get(DeathReadingRow, (people.id, command.cause))
    if row is not None and row.authored:
        raise ValidationFailedError(f"The {people.name} already read that death by a god's word; edit the reading instead.")
    if row is None:
        row = DeathReadingRow(people_entity_id=people.id, cause=command.cause, reading=command.reading, authored=True, locked=[])
        scope.session.add(row)
    row.reading, row.authored = command.reading, True
    held_as(row, True if command.hold is None else command.hold)
    await scope.session.flush()
    return Effect(f"The {people.name} now read that death as {spoken(command.reading)}.", target_node_id=people.id)


@player_action("death_reading:edit", ActionKind.EDIT_RECORD)
async def edit_reading(scope: PlayerScope, command: SetReading) -> Effect:
    people = await people_of(scope, command.people_id)
    row = await scope.session.get(DeathReadingRow, (people.id, command.cause))
    if row is None:
        raise NotFoundError("That people holds no reading of that death yet.")
    row.reading = command.reading
    row.authored = True
    held_as(row, command.hold)
    return Effect(f"The {people.name} now read that death as {spoken(command.reading)}.", target_node_id=people.id)


@player_action("death_reading:delete", ActionKind.EDIT_RECORD)
async def delete_reading(scope: PlayerScope, command: ReadingTarget) -> Effect:
    people = await people_of(scope, command.people_id)
    row = await scope.session.get(DeathReadingRow, (people.id, command.cause))
    if row is None:
        raise NotFoundError("That people holds no reading of that death.")
    await scope.session.delete(row)
    return Effect(f"The {people.name} will read that death again from their values.", target_node_id=people.id)
