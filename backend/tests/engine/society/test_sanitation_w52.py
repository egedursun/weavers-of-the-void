from sqlalchemy import select

from aerona.catalog.transmission import ROUTES
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import TheoryStats
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.disease.responses import cleaning_backed, take_up
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, settlement, tuned

RULES = Rules()


def test_cleaning_cuts_the_water_food_and_goods_routes_only() -> None:
    cut = {route for route, spec in ROUTES.items() if PlagueResponse.SANITATION in spec.blocked_by}
    assert cut == {Transmission.WATER, Transmission.INGESTION, Transmission.OBJECTS}


async def test_cleaning_needs_a_medical_theory_behind_it_and_leaves_lasting_works(realm: Realm) -> None:
    town = await settlement(realm, "Well", population=4000)
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, sanitation=20, locked=[]))
    ctx = context(realm.session, tuned(plague_responses={"sanitation_cost": 0}))
    assert not await cleaning_backed(ctx, town)
    theory = await make(realm.session, "Bad Air", EntityType.THEORY, TheoryStats(), world_id=realm.world.id)
    realm.session.add(TheoryProfileRow(theory_entity_id=theory.id, domain=TheoryDomain.MEDICINE, locked=[]))
    realm.session.add(TheoryAdherentRow(theory_entity_id=theory.id, adherent_entity_id=town.id, strength=80, locked=[]))
    await realm.session.flush()
    assert await cleaning_backed(ctx, town)
    disease = await create_disease(
        ctx, realm.region.id, DiseaseDesign(name=None, values={"primary_route": "water", "target_functions": ["vital"]}, hold=True), son_id=None
    )
    await take_up(ctx, town, disease.id, PlagueResponse.SANITATION)
    await realm.session.flush()
    works = await realm.session.get(SettlementProfileRow, town.id)
    kinds = set(await realm.session.scalars(select(IncidentRow.kind)))
    assert works is not None and works.sanitation == 20 + RULES.plague_responses.sanitation_works
    assert {"disease.sanitation_ordered", "disease.route_found", "disease.route_blocked"} <= kinds
