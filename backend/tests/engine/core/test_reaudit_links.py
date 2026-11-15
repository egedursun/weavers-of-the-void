from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.arts import BetRow, CanonWorkRow, ClubRow, MatchRow
from aerona.db.tables.belonging import SanctuaryLawRow, SanctuaryRow
from aerona.db.tables.crafts import GameFollowingRow, GameRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.customs import BorderControlRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.arts import CanonPath, ClubKind
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.crafts import GameKind, GameRule
from aerona.domain.enums.culture import ArtMedium
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import ArtworkStats, EventStats, PeopleStats, PolityStats, StructureStats
from aerona.engine.arts import control as arts
from aerona.engine.arts.movements import MovementTally, form_canon
from aerona.engine.arts.sport import SportTally, found_clubs, play_friendlies
from aerona.engine.belonging.sanctuary import SanctuaryTally, keep_sanctuaries
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.customs.civics import CivicsTally, adopt_borders
from aerona.engine.mind.book import write_values
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import foe_realms, ongoing_wars
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, phase: str = "arts", **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, phase, rules=tuned_rules(**rules))


async def homeland(session: AsyncSession, people_id: int, town_id: int) -> None:
    await BondRepository(session).connect(BondDraft(people_id, town_id, BondKind.LIVES_IN, 1, "homeland", role=BondRole.HOMELAND))


async def folk(session: AsyncSession, world: CoreWorld, name: str, *towns: EntityRow) -> EntityRow:
    people = await entity(session, name, EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id)
    for town in towns:
        await homeland(session, people.id, town.id)
    await session.flush()
    return people


async def crown(session: AsyncSession, world: CoreWorld, town: EntityRow, ruler: EntityRow | None = None) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            core_entity_id=polity.id,
            treasury=500,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity


async def war_between(session: AsyncSession, world: CoreWorld, attacker: EntityRow, defender: EntityRow) -> WarRow:
    event = await entity(session, f"War of {attacker.name}", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOLY_WAR, started_epoch=1)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=attacker.id, side=WarSide.ATTACKER, joined_epoch=1))
    session.add(WarSideRow(war_id=war.id, entity_id=defender.id, side=WarSide.DEFENDER, joined_epoch=1))
    await session.flush()
    return war


async def test_a_town_finds_its_people_through_the_homeland_bond(session: AsyncSession, world: CoreWorld) -> None:
    first = await settlement(session, "Rimmouth", world, world.regions[0])
    second = await settlement(session, "Rimhold", world, world.regions[1])
    people = await folk(session, world, "Rimfolk", first, second)
    assert await people_id_of(session, first) == people.id
    assert await towns_of_people(session, people.id) == sorted([first.id, second.id])


async def test_a_much_copied_work_enters_the_canon_of_the_people_whose_homeland_keeps_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Copyhold", world, world.regions[0])
    people = await folk(session, world, "Scribefolk", town)
    piece = await entity(session, "The Long Ledger", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id, location_id=town.id)
    session.add(ArtworkProfileRow(artwork_entity_id=piece.id, medium=ArtMedium.FRESCO, quality=40, copies=9, locked=[]))
    await session.flush()
    tally = MovementTally()
    await form_canon(await at(session, 2), tally)
    row = await session.get(CanonWorkRow, (people.id, piece.id))
    assert row is not None and row.path is CanonPath.COPYING and tally.canonised == 1


async def test_clubs_outside_any_league_meet_in_friendlies_and_their_towns_wager(session: AsyncSession, world: CoreWorld) -> None:
    north = await settlement(session, "Northgate", world, world.regions[0], wealth=50)
    south = await settlement(session, "Southgate", world, world.regions[1], wealth=50)
    await crown(session, world, north)
    await crown(session, world, south)
    ctx = await at(session, 2, sports={"friendly_chance": 100})
    home = await arts.start_club(ctx, north.id, ClubKind.TEAM_GAME)
    away = await arts.start_club(ctx, south.id, ClubKind.TEAM_GAME)
    home.fandom = away.fandom = 80
    tally = SportTally()
    await play_friendlies(ctx, tally)
    match = await session.scalar(select(MatchRow).where(MatchRow.league_entity_id.is_(None)))
    bets = list(await session.scalars(select(BetRow)))
    assert match is not None and tally.friendlies == 1 and tally.matches == 1
    assert {bet.settlement_entity_id for bet in bets} == {north.id, south.id}


async def test_a_people_that_loves_a_ball_game_raises_a_club_without_an_arena(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fieldmoor", world, world.regions[0], population=4000)
    people = await folk(session, world, "Fieldfolk", town)
    game = GameRow(name="Hurl", kind=GameKind.BALL, rule=GameRule.PHYSICAL, origin_entity_id=people.id, created_epoch=1, locked=[])
    session.add(game)
    await session.flush()
    session.add(GameFollowingRow(people_entity_id=people.id, game_id=game.id, popularity=70, adopted_epoch=1, locked=[]))
    await session.flush()
    tally = SportTally()
    await found_clubs(await at(session, 2, sports={"club_chance": 100, "club_population": 100}), tally)
    club = await session.scalar(select(ClubRow))
    assert club is not None and club.kind is ClubKind.TEAM_GAME and club.arena_entity_id is None and tally.clubs == 1


async def test_a_realm_is_at_war_through_its_people_and_guards_its_borders(session: AsyncSession, world: CoreWorld) -> None:
    home = await settlement(session, "Ashgate", world, world.regions[0])
    far = await settlement(session, "Farmark", world, world.regions[1])
    ours = await folk(session, world, "Ashfolk", home)
    theirs = await folk(session, world, "Farfolk", far)
    realm = await crown(session, world, home)
    rival = await crown(session, world, far)
    await war_between(session, world, ours, theirs)
    wars = await ongoing_wars(session, realm.id)
    assert len(wars) == 1 and wars[0].own_id == ours.id and wars[0].foe_id == theirs.id
    assert await foe_realms(session, realm.id) == {rival.id}
    tally = CivicsTally()
    await adopt_borders(await at(session, 2, phase="customs"), tally)
    assert await session.get(BorderControlRow, realm.id) is not None and await session.get(BorderControlRow, rival.id) is not None
    assert tally.borders == 2


async def test_a_realm_whose_own_temples_shelter_its_fugitives_lays_down_a_law_of_sanctuary(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    ruler = await mortal(session, "Arden", world, town.id)
    realm = await crown(session, world, town, ruler)
    await write_values(session, ValueHolder.PERSONAL, ruler.id, {ValueAxis.LAW: 90})
    temple = await entity(session, "Shrine of Velmor", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    fugitive = await mortal(session, "Oss", world, town.id)
    session.add(
        SanctuaryRow(
            fugitive_entity_id=fugitive.id,
            host_entity_id=temple.id,
            kind=SanctuaryKind.TEMPLE,
            fugitive_kind=FugitiveKind.OUTLAW,
            pursuer_entity_id=realm.id,
            fee=0,
            granted_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    tally = SanctuaryTally()
    await keep_sanctuaries(await at(session, 2, phase="belonging", sanctuary={"law_chance": 100, "seek_chance": 0}), tally)
    law = await session.get(SanctuaryLawRow, realm.id)
    assert law is not None and law.restricted and law.fee_pct == 0 and tally.laws == 1
