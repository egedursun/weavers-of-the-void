from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import EntityNoteRecord, MapNoteRecord, NotesView
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.services.wiki import map_notes

router = APIRouter(tags=["notes"])

NO_NOTE = "That record has no personal note."
ENTITY_ID = {"entity_id": "entity_id"}

ALIASES = (Alias("DELETE", "/entities/{entity_id}/note", "record:note", path_fields=ENTITY_ID, fixed={"text": ""}, summary="Delete a personal note"),)
mount_all(router, ALIASES)


def note_record(row: EntityRow) -> EntityNoteRecord:
    return EntityNoteRecord(
        entity_id=row.id,
        entity_name=row.name,
        entity_type=row.entity_type,
        world_id=row.world_id,
        text=row.private_note or "",
        author_account_id=row.note_author_account_id,
        author_name=row.note_author_name,
    )


@router.get("/notes", response_model=NotesView)
async def list_notes(services: ServicesDep) -> NotesView:
    async with reader(services) as session:
        statement = select(EntityRow).where(EntityRow.private_note.is_not(None), EntityRow.status != EntityStatus.DESTROYED).order_by(EntityRow.name)
        rows = await session.scalars(statement)
        return NotesView(
            entity_notes=[note_record(row) for row in rows],
            map_notes=[MapNoteRecord.model_validate(row) for row in await map_notes(session)],
        )


@router.get("/entities/{entity_id}/note", response_model=EntityNoteRecord)
async def read_note(services: ServicesDep, entity_id: int = Path(ge=1)) -> EntityNoteRecord:
    async with reader(services) as session:
        row = await session.get(EntityRow, entity_id)
        if row is None or not row.private_note:
            raise NotFoundError(NO_NOTE)
        return note_record(row)
