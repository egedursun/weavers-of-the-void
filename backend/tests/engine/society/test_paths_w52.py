from sqlalchemy import select

from aerona.catalog.careers import CAREERS, OPEN_PATHS
from aerona.catalog.life.mortal import CAREER_ROLES
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.mortal import CareerPath
from aerona.engine.mortal.paths import path_open, settle_frontier, walk_path
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.primitives.queries import add_flag
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, settlement, tuned

RULES = Rules()


def test_thirteen_paths_each_with_skills_weight_and_the_old_tables_read_from_the_catalogue() -> None:
    assert len(CAREERS) == len(CareerPath) == 15
    assert all(0 <= spec.weight(RULES) <= 100 for spec in CAREERS.values())
    assert {CareerPath.SEA, CareerPath.SERVICE, CareerPath.ARTS, CareerPath.SETTLE} <= set(CAREER_ROLES)
    assert CareerPath.ARTS in OPEN_PATHS and CareerPath.SEA not in OPEN_PATHS


async def test_the_frontier_path_opens_only_where_a_frontier_exists_and_takes_the_young_there(realm: Realm) -> None:
    home = await settlement(realm, "Home")
    youth = await mortal(realm, "Youth", location_id=home.id, age=17)
    assert not await path_open(context(realm.session), youth, CAREERS[CareerPath.SETTLE])
    frontier = await settlement(realm, "Edge")
    await add_flag(realm.session, frontier.id, EntityFlag.COLONY, 1)
    ctx = context(realm.session, tuned(careers={"settle_found_pct": 100}))
    assert await path_open(ctx, youth, CAREERS[CareerPath.SETTLE])
    assert await settle_frontier(ctx, youth)
    assert youth.location_id == frontier.id
    assert "career.settled_frontier" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_walking_a_path_trains_its_skills(realm: Realm) -> None:
    artist = await mortal(realm, "Artist")
    profile, _ = await ensure_profile(realm.session, artist.id, 3)
    profile.career = CareerPath.ARTS
    assert await walk_path(context(realm.session), artist, profile) == CareerPath.ARTS.value
