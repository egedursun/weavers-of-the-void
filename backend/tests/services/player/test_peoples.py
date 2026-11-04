from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.demography import FolkDiet, FuneralCustom
from aerona.domain.enums.entity import EntityType
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import peoples
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def test_a_people_is_founded_edited_held_released_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await peoples.found_people(
        scope,
        peoples.FoundPeople(name="Glasskin", region_id=world.region.id, population=800, values={"body_plan": "construct", "diet": "lithovore"}),
    )
    founded = await session.scalar(select(EntityRow).where(EntityRow.name == "Glasskin", EntityRow.entity_type == EntityType.PEOPLE))
    assert founded is not None and outcome.created_ids == [founded.id]
    biology = await session.get(PeopleBiologyRow, founded.id)
    culture = await session.get(PeopleCultureRow, founded.id)
    assert biology is not None and culture is not None
    assert biology.body_plan is BodyPlan.CONSTRUCT and biology.diet is FolkDiet.LITHOVORE
    assert culture.funeral_rite_id is not None
    held = await peoples.edit_people(scope, peoples.EditPeople(people_id=founded.id, values={"traits": ["thick_hide"]}))
    assert biology.traits == ["thick_hide"] and "traits" in biology.locked and held.ledger_entry_id is not None
    await peoples.edit_people(scope, peoples.EditPeople(people_id=founded.id, release=["traits"]))
    assert "traits" not in biology.locked
    edited = await peoples.edit_people(scope, peoples.EditPeople(people_id=founded.id, values={"funeral_rite": "soul_binding"}))
    assert culture.funeral_rite is FuneralCustom.SOUL_BINDING and "funeral_rite" in culture.locked
    assert edited.ledger_entry_id is not None
    changes = await changes_of(session, edited.ledger_entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []
    await session.refresh(culture)
    assert culture.funeral_rite is FuneralCustom.BURIAL
    assert culture.locked == []
