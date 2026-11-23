import pytest
from sqlalchemy import select

import aerona.domain.enums.disease as disease_enums
from aerona.catalog.transmission import DISEASE_ROUTES, ROUTES
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.disease import DiseaseRouteRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.environment import RiverClass, TemperatureBand
from aerona.domain.enums.evolution import PlagueResponse
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.control import DiseaseDesign, create_disease, remove_route, set_route
from aerona.engine.disease.routes import learn_routes, seed_routes
from aerona.engine.disease.vectors import Spot, routes_of, vector_factor
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, settlement

RULES = Rules()


def land(**values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "river_class": RiverClass.NONE,
        "wetland": 0,
        "temperature_band": TemperatureBand.TEMPERATE,
        "rainfall": 50,
        "magic_density": 0,
        "scars": {},
        "disease_load": 0,
    }
    base.update(values)
    return RegionEnvironmentRow(**base)


async def sickness(realm: Realm, route: str) -> int:
    disease = await create_disease(
        context(realm.session),
        realm.region.id,
        DiseaseDesign(name=None, values={"primary_route": route, "target_functions": ["vital"]}, hold=True),
        son_id=None,
    )
    return disease.id


def test_the_old_route_and_climate_enums_are_gone() -> None:
    assert not hasattr(disease_enums, "DiseaseVector")
    assert not hasattr(disease_enums, "ClimateAffinity")


def test_every_route_has_a_reader_rate_and_block_and_the_affliction_only_routes_stay_out_of_sickness() -> None:
    assert set(ROUTES) == set(Transmission)
    assert {Transmission.RITE, Transmission.GAZE, Transmission.EXPERIENCE}.isdisjoint(DISEASE_ROUTES)
    assert all(0 <= spec.rate(RULES) <= 100 and 0 <= spec.block(RULES) <= 100 for spec in ROUTES.values())


async def test_a_sickness_spreads_by_each_route_it_holds_by_its_share(realm: Realm) -> None:
    town = await settlement(realm, "Ford", population=4000)
    disease_id = await sickness(realm, "inhalation")
    book = await DiseaseBook.load(realm.session, RULES, 3)
    profile = book.profiles[disease_id]
    alone = vector_factor(book, profile, Spot(town, land(river_class=RiverClass.GREAT_RIVER), realm.region.id, SpreadPath.ORIGIN))
    book.routes[disease_id] = [(Transmission.WATER, 40)]
    assert routes_of(book, profile) == [(Transmission.INHALATION, 60), (Transmission.WATER, 40)]
    shared = vector_factor(book, profile, Spot(town, land(river_class=RiverClass.GREAT_RIVER), realm.region.id, SpreadPath.ORIGIN))
    assert shared != alone


async def test_blocking_one_route_cuts_only_that_share(realm: Realm) -> None:
    town = await settlement(realm, "Weir", population=4000)
    disease_id = await sickness(realm, "inhalation")
    book = await DiseaseBook.load(realm.session, RULES, 3)
    profile = book.profiles[disease_id]
    book.routes[disease_id] = [(Transmission.BITE, 50)]
    spot = Spot(town, land(), realm.region.id, SpreadPath.ORIGIN)
    open_factor = vector_factor(book, profile, spot)
    book.responses[(town.id, disease_id)] = {PlagueResponse.QUARANTINE}
    quarantined = vector_factor(book, profile, spot)
    assert 0 < quarantined < open_factor
    book.routes[disease_id] = []
    book.responses[(town.id, disease_id)] = set()
    whole = vector_factor(book, profile, spot)
    book.responses[(town.id, disease_id)] = {PlagueResponse.QUARANTINE}
    assert open_factor - quarantined < whole - vector_factor(book, profile, spot)


async def test_the_god_opens_holds_and_closes_a_further_route(realm: Realm) -> None:
    disease_id = await sickness(realm, "contact")
    ctx = context(realm.session)
    row = await set_route(ctx, disease_id, Transmission.OBJECTS, 25, hold=True)
    assert row.share == 25 and row.locked == ["share"]
    with pytest.raises(ValidationFailedError):
        await set_route(ctx, disease_id, Transmission.GAZE, 25, hold=None)
    with pytest.raises(ValidationFailedError):
        await set_route(ctx, disease_id, Transmission.CONTACT, 25, hold=None)
    assert await remove_route(ctx, disease_id, Transmission.OBJECTS)
    assert await realm.session.get(DiseaseRouteRow, (disease_id, Transmission.OBJECTS)) is None


async def test_a_strain_keeps_its_parents_routes_and_a_people_learns_and_cuts_them(realm: Realm) -> None:
    town = await settlement(realm, "Mere", population=4000)
    disease_id = await sickness(realm, "contact")
    ctx = context(realm.session)
    book = await DiseaseBook.load(realm.session, RULES, 3)
    book.routes[disease_id] = [(Transmission.OBJECTS, 30)]
    parent = book.profiles[disease_id]
    child_id = await sickness(realm, "contact")
    child = book.profiles.get(child_id) or (await DiseaseBook.load(realm.session, RULES, 3)).profiles[child_id]
    child.parent_disease_id = parent.disease_entity_id
    entity = book.diseases.get(child_id) or (await DiseaseBook.load(realm.session, RULES, 3)).diseases[child_id]
    seed_routes(ctx, book, entity, child)
    assert (Transmission.OBJECTS, 30) in book.routes[child_id]
    await set_route(ctx, disease_id, Transmission.OBJECTS, 30, hold=None)
    await learn_routes(ctx, town, disease_id, PlagueResponse.BURN_DEAD, first=True)
    await realm.session.flush()
    kinds = set(await realm.session.scalars(select(IncidentRow.kind)))
    assert {"disease.route_found", "disease.route_blocked"} <= kinds
