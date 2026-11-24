from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.arts import FIELD_GAMES
from aerona.catalog.market_kinds import ANIMAL_CLUBS, CLUBS, MIND_CLUBS
from aerona.db.tables.arts import ClubRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.arts import ClubKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.kind_crafts import GameCategory
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.arts.sport import draw_fans
from aerona.services.integrity.market_links import beastless_clubs, unbeast_club
from tests.engine.core.factories import CoreWorld, entity
from tests.engine.core.test_cycles_w21 import context, town_of


def test_six_club_kinds_with_beasts_and_minds() -> None:
    assert set(CLUBS) == set(ClubKind)
    assert {ClubKind.ANIMAL_CONTEST, ClubKind.HUNT} == ANIMAL_CLUBS and {ClubKind.MIND_GAMES} == MIND_CLUBS
    assert FIELD_GAMES[GameCategory.BOARD] is ClubKind.MIND_GAMES


async def club(session: AsyncSession, world: CoreWorld, kind: ClubKind) -> ClubRow:
    town = await town_of(session, world, "Ashby")
    faction = await entity(session, "The Reds", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.CLUB, home_entity_id=town.id, influence_over={}, cohort_share={}, locked=[]))
    row = ClubRow(faction_entity_id=faction.id, kind=kind, fandom=10, locked=[])
    session.add(row)
    await session.flush()
    return row


async def test_a_club_draws_fans_by_its_kind(session: AsyncSession, world: CoreWorld) -> None:
    row = await club(session, world, ClubKind.MIND_GAMES)
    await draw_fans(await context(session, clubs={"mind_games_fan_draw": 50}))
    assert row.fandom == 55


async def test_a_club_of_animal_contests_needs_a_town_that_keeps_sport_beasts(session: AsyncSession, world: CoreWorld) -> None:
    row = await club(session, world, ClubKind.ANIMAL_CONTEST)
    assert row.faction_entity_id in await beastless_clubs(session)
    await unbeast_club(session, row.faction_entity_id)
    assert row.kind not in ANIMAL_CLUBS
