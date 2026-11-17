from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import LegendProfileRow, RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import RumourChannel
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import WitnessMode
from aerona.domain.enums.war import WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.lore import rumours
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, settlement, tuned

SURE = tuned(Rules(), rumours={"route_chance": 100, "pilgrimage_chance": 100, "journey_chance": 100, "spy_chance": 100})


async def happening(session: AsyncSession, kind: str, epoch: int, *actors: int, magnitude: int = 60) -> IncidentRow:
    incident = IncidentRow(kind=kind, epoch=epoch, magnitude=magnitude, note=f"a {kind}")
    session.add(incident)
    await session.flush()
    for position, actor in enumerate(actors):
        session.add(IncidentParticipantRow(incident_id=incident.id, node_id=actor, role=IncidentRole.ACTOR, position=position))
    await session.flush()
    return incident


async def carried(session: AsyncSession, incident_id: int) -> dict[int, RumourRow]:
    rows = await session.scalars(select(RumourRow).where(RumourRow.incident_id == incident_id))
    return {row.carrier_entity_id: row for row in rows}


async def test_witnesses_carry_word_and_it_travels_the_trade_road_losing_truth(realm: Realm) -> None:
    session = realm.session
    home = await settlement(realm, "Ashford")
    market = await settlement(realm, "Brindle", location_id=realm.far_region.id)
    await link(session, home.id, market.id, BondKind.TRADES_WITH)
    incident = await happening(session, "war.battle.field_victory", 3, home.id)
    ctx = context(session, SURE, epoch=3)
    atlas = await RegionAtlas.load(session)
    assert await rumours.seed(ctx, atlas) == 1
    counts = await rumours.spread(ctx, atlas)
    heard = await carried(session, incident.id)
    assert counts["route"] == 1
    assert heard[home.id].channel is RumourChannel.WITNESS and heard[home.id].fidelity == Rules().records.fidelity_saw
    assert heard[market.id].channel is RumourChannel.ROUTE
    assert heard[market.id].source_entity_id == home.id
    assert heard[market.id].hops == 1
    assert heard[market.id].fidelity < 100 - Rules().rumours.hop_loss + 1


async def test_quiet_and_small_happenings_are_not_told(realm: Realm) -> None:
    session = realm.session
    home = await settlement(realm, "Ashford")
    await happening(session, "speech", 3, home.id)
    await happening(session, "war.battle.field_victory", 3, home.id, magnitude=1)
    assert await rumours.seed(context(session, SURE, epoch=3), await RegionAtlas.load(session)) == 0


async def test_hearing_of_an_atrocity_turns_a_far_people_against_its_doer_by_how_true_the_tale_is(realm: Realm) -> None:
    session = realm.session
    butcher = await settlement(realm, "Gorre")
    victim = await settlement(realm, "Mirefold")
    listener = await settlement(realm, "Tallow", location_id=realm.far_region.id)
    incident = await happening(session, "captives.fates", 3, butcher.id, victim.id)
    session.add(RumourRow(incident_id=incident.id, carrier_entity_id=listener.id, channel=RumourChannel.ROUTE, fidelity=50, hops=1, epoch=3))
    await session.flush()
    counts = await rumours.react(context(session, SURE, epoch=3), await RegionAtlas.load(session))
    memory = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == listener.id, MemoryRow.subject_node_id == butcher.id))
    assert counts["atrocities"] == 1
    assert memory is not None and memory.kind is MemoryKind.ILL_WILL
    assert memory.magnitude == -Rules().rumours.atrocity_hatred * 50 / 100


async def test_word_of_a_near_enemy_host_mans_the_walls_and_calls_allies(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Keep")
    foe = await settlement(realm, "Raider")
    friend = await settlement(realm, "Friend", location_id=realm.far_region.id)
    await link(session, town.id, friend.id, BondKind.ALLY)
    event = await make(session, "The Raid", EntityType.EVENT, EventStats(severity=50), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, world_id=realm.world.id, cause=WarCause.DECLARED, status=WarStatus.ONGOING, started_epoch=2)
    session.add(war)
    await session.flush()
    session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=town.id, side=WarSide.DEFENDER, joined_epoch=2),
            WarSideRow(war_id=war.id, entity_id=foe.id, side=WarSide.ATTACKER, joined_epoch=2),
        ]
    )
    incident = await happening(session, "war.outbreak", 3, foe.id)
    session.add(RumourRow(incident_id=incident.id, carrier_entity_id=town.id, channel=RumourChannel.ROUTE, fidelity=100, hops=1, epoch=3))
    await session.flush()
    before = stat(town, "defense") or 0
    counts = await rumours.react(context(session, SURE, epoch=3), await RegionAtlas.load(session))
    assert counts["alarms"] == 1
    assert (stat(town, "defense") or 0) == before + Rules().rumours.alarm_defense
    goodwill = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == friend.id, MemoryRow.subject_node_id == town.id))
    assert goodwill is not None and goodwill.magnitude > 0


async def test_garbled_word_that_lingers_hardens_into_a_legend_with_its_source(realm: Realm) -> None:
    session = realm.session
    first = await settlement(realm, "Ashford")
    second = await settlement(realm, "Brindle")
    incident = await happening(session, "monsters.raid", 1, first.id)
    for carrier in (first, second):
        session.add(RumourRow(incident_id=incident.id, carrier_entity_id=carrier.id, channel=RumourChannel.ROUTE, fidelity=20, hops=2, epoch=1, lingered=3))
    await session.flush()
    made = await rumours.legends(context(session, SURE, epoch=5))
    assert len(made) == 1
    profile = await session.get(LegendProfileRow, made[0].id)
    assert profile is not None
    assert profile.source_incident_id == incident.id
    assert profile.distortion == 80
    assert sorted(profile.tellers) == sorted([first.id, second.id])
    assert made[0].entity_type is EntityType.LEGEND
    assert all(row.legend_entity_id == made[0].id for row in (await carried(session, incident.id)).values())


async def test_planted_rumours_are_held_until_released_and_can_be_silenced_everywhere(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Ashford")
    other = await settlement(realm, "Brindle")
    ctx = context(session, SURE, epoch=4)
    row = await rumours.plant(ctx, town.id, incident_id=None, subject_id=other.id, text="They poison wells", fidelity=90, atrocity=True)
    assert row.planted and row.locked == ["fidelity"]
    await rumours.linger(context(session, SURE, epoch=5))
    assert row.fidelity == 90
    await rumours.edit(ctx, row.id, fidelity=None, release=True)
    await rumours.linger(context(session, SURE, epoch=6))
    assert row.fidelity == 90 - Rules().rumours.linger_decay
    copy = await rumours.plant(ctx, other.id, incident_id=row.incident_id, subject_id=None, text="", fidelity=50)
    assert copy.incident_id == row.incident_id
    assert await rumours.suppress(ctx, row.id, everywhere=True) == 2


async def test_old_worlds_remember_recent_happenings_as_rumour_once(realm: Realm) -> None:
    session = realm.session
    town = await settlement(realm, "Ashford")
    await happening(session, "war.battle.field_victory", 2, town.id)
    ctx = context(session, SURE, epoch=4)
    atlas = await RegionAtlas.load(session)
    assert await rumours.backfill(ctx, atlas) == 1
    assert await rumours.backfill(ctx, atlas) == 0
    row = await session.scalar(select(RumourRow))
    assert row is not None and row.fidelity == Rules().records.fidelity_saw - 2 * Rules().rumours.linger_decay


async def test_only_those_who_saw_a_happening_carry_its_first_word(realm: Realm) -> None:
    session = realm.session
    home = await settlement(realm, "Ashford")
    distant = await settlement(realm, "Brindle", location_id=realm.far_region.id)
    incident = await happening(session, "war.battle.field_victory", 3, home.id)
    session.add(
        IncidentParticipantRow(incident_id=incident.id, node_id=distant.id, role=IncidentRole.WITNESS, position=5, witness_mode=WitnessMode.HEARD, fidelity=60)
    )
    await session.flush()
    assert await rumours.seed(context(session, SURE, epoch=3), await RegionAtlas.load(session)) == 1
    heard = await carried(session, incident.id)
    assert home.id in heard and distant.id not in heard
