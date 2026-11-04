import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.disease import DiseaseVector, OutbreakStatus
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.society import SocialClass
from aerona.engine.disease.control import ProfileValue
from aerona.engine.primitives.stats import set_stats, stat
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import disease, peoples
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity

NEW_ACTIONS = ("disease:create", "outbreak:edit", "endemic:set", "endemic:remove", "cohort:set", "mortal:dormancy")


async def forged(scope: PlayerScope, world: PlayerWorld) -> int:
    values: dict[str, ProfileValue] = {"vector": "air", "target_functions": ["breath"], "virulence": 55}
    outcome = await disease.create_disease(scope, disease.CreateDisease(region_id=world.region.id, name="The Ash Cough", values=values))
    assert outcome.created_ids
    return outcome.created_ids[0]


def test_the_new_levers_are_in_the_catalogue() -> None:
    assert [action for action in NEW_ACTIONS if action not in ACTIONS_BY_ID] == []


async def test_a_disease_is_forged_held_released_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await disease.create_disease(
        scope,
        disease.CreateDisease(region_id=world.region.id, name="The Ash Cough", values={"vector": "spirit", "target_functions": ["cognition"], "incubation": 5}),
    )
    disease_id = outcome.created_ids[0]
    profile = await session.get(DiseaseProfileRow, disease_id)
    assert profile is not None and profile.vector is DiseaseVector.SPIRIT and profile.incubation == 5
    assert set(profile.locked) == {"vector", "target_functions", "incubation"}
    await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"target_functions": ["sight", "skin"], "lethality": 80}))
    assert profile.target_functions == ["sight", "skin"] and profile.lethality == 80
    await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, release=["vector", "lethality"]))
    assert "vector" not in profile.locked and "lethality" not in profile.locked
    with pytest.raises(ValidationFailedError):
        await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"target_functions": []}))
    with pytest.raises(ValidationFailedError):
        await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"target_functions": ["liver"]}))
    assert outcome.ledger_entry_id is not None
    changes = await changes_of(session, outcome.ledger_entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == [] or report.applied


async def test_host_species_and_origin_are_editable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    disease_id = await forged(scope, world)
    rats = await make_entity(session, "Ash Rats", EntityType.SPECIES, world_id=world.world.id, location_id=world.region.id)
    await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"host_species_id": rats.id}))
    profile = await session.get(DiseaseProfileRow, disease_id)
    assert profile is not None and profile.host_species_id == rats.id
    await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"host_species_id": None}))
    assert profile.host_species_id is None
    with pytest.raises(NotFoundError):
        await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"origin_incident_id": 999999}))


async def test_an_outbreak_is_edited_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    disease_id = await forged(scope, world)
    await disease.loose(scope, disease.Loose(target_id=world.region.id, disease_id=disease_id, severity=50))
    outbreak = await session.scalar(select(OutbreakRow).where(OutbreakRow.disease_entity_id == disease_id))
    assert outbreak is not None
    await disease.edit_outbreak(
        scope, disease.EditOutbreak(outbreak_id=outbreak.id, values={"severity": 90, "infected": 5000, "dead": 700, "status": "waning", "quarantined": True})
    )
    assert (outbreak.severity, outbreak.infected, outbreak.dead, outbreak.status, outbreak.quarantined) == (90, 5000, 700, OutbreakStatus.WANING, True)
    assert set(outbreak.locked) == {"severity", "infected", "dead", "status", "quarantined"}
    host = await session.get(EntityRow, disease_id)
    assert host is not None and stat(host, "dead") == 700
    await disease.edit_outbreak(scope, disease.EditOutbreak(outbreak_id=outbreak.id, release=["severity", "status"]))
    assert set(outbreak.locked) == {"infected", "dead", "quarantined"}
    with pytest.raises(ValidationFailedError):
        await disease.edit_outbreak(scope, disease.EditOutbreak(outbreak_id=outbreak.id, values={"severity": 500}))


async def test_endemic_disease_and_immunity_by_age_band(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    disease_id = await forged(scope, world)
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await disease.set_endemic(scope, disease.Endemic(region_id=world.region.id, disease_id=disease_id, load=35, hold=True))
    row = await session.get(EndemicDiseaseRow, (world.region.id, disease_id))
    assert row is not None and row.load == 35 and row.locked
    await disease.set_endemic(scope, disease.Endemic(region_id=world.region.id, disease_id=disease_id, load=10, hold=False))
    assert row.load == 10 and not row.locked
    await disease.remove_endemic(scope, disease.EndemicTarget(region_id=world.region.id, disease_id=disease_id))
    assert await session.get(EndemicDiseaseRow, (world.region.id, disease_id)) is None
    await disease.immunity(scope, disease.Immunity(community_id=town.id, disease_id=disease_id, immune_pct=70, age_band=AgeBand.ELDER, hold=True))
    rows = {row.age_band: row for row in await session.scalars(select(ImmunityRow).where(ImmunityRow.community_entity_id == town.id))}
    assert list(rows) == [AgeBand.ELDER] and rows[AgeBand.ELDER].immune_pct == 70 and rows[AgeBand.ELDER].locked
    await disease.immunity(scope, disease.Immunity(community_id=town.id, disease_id=disease_id, age_band=AgeBand.ELDER, forget=True))
    assert not list(await session.scalars(select(ImmunityRow).where(ImmunityRow.community_entity_id == town.id)))


async def test_a_cohort_headcount_is_set_and_the_population_follows(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Countville", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    set_stats(town, population=4000)
    await session.flush()
    await peoples.set_cohort(
        scope,
        peoples.SetCohort(
            community_id=town.id, age_band=AgeBand.ADULT, sex=Sex.MALE, social_class=SocialClass.FARMER, condition=CohortCondition.SICK, count=321
        ),
    )
    rows = list(await session.scalars(select(CohortRow).where(CohortRow.community_entity_id == town.id)))
    assert sum(row.count for row in rows) == stat(town, "population")
    sick = next(row for row in rows if row.condition is CohortCondition.SICK and row.age_band is AgeBand.ADULT and row.sex is Sex.MALE)
    assert sick.count == 321
    moved = await peoples.move_cohort(
        scope,
        peoples.MoveCohort(
            community_id=town.id,
            count=100,
            source=SocialClass.FARMER,
            target=SocialClass.FARMER,
            condition=CohortCondition.NONE,
            from_condition=CohortCondition.SICK,
        ),
    )
    assert moved.values["moved"] == 100
    await session.refresh(sick)
    assert sick.count == 221


async def test_a_mortal_is_woken_dozed_and_held(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    sleeper = await make_entity(session, "Dreaming Oswin", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    outcome = await peoples.set_dormancy(scope, peoples.Dormancy(mortal_id=sleeper.id, dormant=True, hold=True))
    assert outcome.values["dormant"] is True
    assert await session.get(EntityFlagRow, (sleeper.id, EntityFlag.DORMANT)) is not None
    pins = list(await session.scalars(select(ModifierRow).where(ModifierRow.target_node_id == sleeper.id, ModifierRow.source_kind == ModifierSource.PIN)))
    assert [pin.target_key for pin in pins] == ["dormant"]
    await peoples.set_dormancy(scope, peoples.Dormancy(mortal_id=sleeper.id, dormant=False, hold=False))
    assert await session.get(EntityFlagRow, (sleeper.id, EntityFlag.DORMANT)) is None
    assert not list(await session.scalars(select(ModifierRow).where(ModifierRow.target_node_id == sleeper.id, ModifierRow.source_kind == ModifierSource.PIN)))


async def undo(session: AsyncSession, world: PlayerWorld, entry_id: int | None) -> None:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []


async def test_disease_and_cohort_edits_are_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    disease_id = await forged(scope, world)
    profile = await session.get(DiseaseProfileRow, disease_id)
    assert profile is not None
    edited = await disease.edit_disease(scope, disease.EditDisease(disease_id=disease_id, values={"incubation": 9}))
    assert profile.incubation == 9
    await undo(session, world, edited.ledger_entry_id)
    await session.refresh(profile)
    assert profile.incubation != 9 and "incubation" not in profile.locked
    set_endemic = await disease.set_endemic(scope, disease.Endemic(region_id=world.region.id, disease_id=disease_id, load=44, hold=True))
    await undo(session, world, set_endemic.ledger_entry_id)
    assert await session.get(EndemicDiseaseRow, (world.region.id, disease_id)) is None
    town = await make_entity(session, "Undoford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    set_stats(town, population=2000)
    await session.flush()
    first = await peoples.set_cohort(
        scope, peoples.SetCohort(community_id=town.id, age_band=AgeBand.CHILD, sex=Sex.FEMALE, social_class=SocialClass.FARMER, count=50)
    )
    before = stat(town, "population")
    second = await peoples.set_cohort(
        scope, peoples.SetCohort(community_id=town.id, age_band=AgeBand.CHILD, sex=Sex.FEMALE, social_class=SocialClass.FARMER, count=500)
    )
    assert first.ledger_entry_id is not None and stat(town, "population") == (before or 0) + 450
    await undo(session, world, second.ledger_entry_id)
    await session.refresh(town)
    row = await session.get(CohortRow, (town.id, AgeBand.CHILD, Sex.FEMALE, SocialClass.FARMER, CohortCondition.NONE))
    assert row is not None and row.count == 50
    assert stat(town, "population") == before
