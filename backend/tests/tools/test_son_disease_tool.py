from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.disease import DiseaseVector
from tests.tools.factories import seed_realm, son_toolkit

REASON = "The proud city mocked my priests and must learn humility."


async def test_a_son_forges_and_looses_a_typed_disease(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    outcome = await toolkit.runtime.call(
        "loose_disease",
        {
            "target_id": realm.cosmos.region_id,
            "name": "Grey Breath of Thalor",
            "vector": "air",
            "target_functions": ["breath", "vital"],
            "virulence": 70,
            "lethality": 45,
            "incubation": 3,
            "chronic_rate": 20,
            "climate_affinity": "cold",
            "host_species_id": realm.species_id,
            "severity": 60,
            "reason": REASON,
        },
    )
    assert not outcome.is_error, outcome.text
    async with database.read() as session:
        disease = await session.scalar(select(EntityRow).where(EntityRow.name == "Grey Breath of Thalor"))
        assert disease is not None and disease.creator_son_id == realm.son_id
        profile = await session.get(DiseaseProfileRow, disease.id)
        assert profile is not None
        assert profile.vector is DiseaseVector.AIR and profile.target_functions == ["breath", "vital"]
        assert profile.incubation == 3 and profile.host_species_id == realm.species_id
        assert profile.origin_incident_id is not None
        assert await session.scalar(select(OutbreakRow).where(OutbreakRow.disease_entity_id == disease.id)) is not None


async def test_a_son_cannot_loose_a_disease_on_a_mortal(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    outcome = await toolkit.runtime.call(
        "loose_disease",
        {"target_id": realm.mortal_id, "name": "Pale Rot", "vector": "touch", "target_functions": ["skin"], "reason": REASON},
    )
    assert outcome.is_error
