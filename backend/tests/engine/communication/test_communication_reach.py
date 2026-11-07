from sqlalchemy import select

from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import OpinionSubject
from aerona.domain.enums.demography import Aesthetic, InheritanceCustom, MarriageCustom, MartialStyle
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import SkillKind, SkillSource, ValueAxis
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import ArmyStats, EventStats, PolityStats
from aerona.engine.communication.dispatches import enemy_army_near, welcome
from aerona.engine.intrigue.beliefs import believe, fade_beliefs
from aerona.engine.intrigue.sources import SourceTally, scout_reports
from aerona.engine.mind.book import holder_kind, set_skill, write_values
from aerona.engine.settlement.life import ruler_discontent
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement, tuned


async def armies_at_war(realm: Realm) -> tuple[int, int, int, int]:
    first = await settlement(realm, "Ardent")
    second = await settlement(realm, "Bramble")
    await link(realm.session, first.id, second.id, BondKind.ENEMY)
    event = await make(realm.session, "War of the Fords", EntityType.EVENT, EventStats(), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, world_id=realm.world.id, cause=WarCause.GRUDGE, started_epoch=1)
    realm.session.add(war)
    await realm.session.flush()
    scouts = await make(realm.session, "Ardent Riders", EntityType.ARMY, ArmyStats(), world_id=realm.world.id, location_id=realm.region.id)
    host = await make(realm.session, "Bramble Host", EntityType.ARMY, ArmyStats(), world_id=realm.world.id, location_id=realm.region.id)
    for army, owner, kind, count in ((scouts, first, UnitKind.LIGHT_CAVALRY, 50), (host, second, UnitKind.SPEARMEN, 300)):
        realm.session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner.id, raised_epoch=1, war_id=war.id))
        realm.session.add(ArmyProfileRow(army_entity_id=army.id, region_entity_id=realm.region.id))
        realm.session.add(ArmyUnitRow(army_entity_id=army.id, kind=kind, count=count))
    await realm.session.flush()
    return first.id, second.id, scouts.id, host.id


async def test_a_town_that_disapproves_of_its_ruler_grows_restless(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"disapproval_unrest_pct": 10}))
    town = await settlement(realm, "Cairnwick")
    polity = await make(realm.session, "Realm of Cairnwick", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    ruler = await mortal(realm, "Dorran", location_id=town.id)
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PublicOpinionRow(community_node_id=town.id, subject_node_id=ruler.id, subject=OpinionSubject.RULER, approval=-80, locked=[]))
    await realm.session.flush()
    assert await ruler_discontent(ctx, town.id) == 8


async def test_a_hierarchical_court_cools_to_a_letter_without_an_envoy(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"precedence_pct": 30}))
    sender = await settlement(realm, "Elderbrook")
    recipient = await people(realm, "Faircrown")
    kind = holder_kind(recipient)
    assert kind is not None
    await write_values(realm.session, kind, recipient.id, {ValueAxis.HIERARCHY: 100})
    letter = MessageRow(epoch=1, sender_node_id=sender.id, recipient_node_id=recipient.id, intent=MessageIntent.DISPATCH, text="")
    assert round(await welcome(ctx, letter), 2) == 0.7


async def test_an_enemy_army_seizes_messages_and_scouts_report_what_they_see(realm: Realm) -> None:
    ctx = context(realm.session, tuned(belief_state={"feint_pct": 0}))
    first, second, scouts, host = await armies_at_war(realm)
    friend = await settlement(realm, "Kestrel")
    letter = MessageRow(epoch=1, sender_node_id=first, recipient_node_id=friend.id, intent=MessageIntent.DISPATCH, text="")
    assert await enemy_army_near(ctx, letter) == second
    await scout_reports(ctx, SourceTally())
    seen = await realm.session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == first, BeliefRow.subject_node_id == host))
    assert seen is not None and seen.source is BeliefSource.SCOUT and 250 <= seen.value <= 350
    assert scouts != host


async def test_a_cunning_commander_lights_false_campfires(realm: Realm) -> None:
    ctx = context(realm.session, tuned(belief_state={"feint_pct": 100, "campfire_pct": 50}))
    first, _, _, host = await armies_at_war(realm)
    commander = await mortal(realm, "Galen")
    await set_skill(realm.session, commander.id, SkillKind.DECEPTION, 100, epoch=1, source=SkillSource.PRACTICE)
    army = await realm.session.get(ArmyRow, host)
    assert army is not None
    army.commander_entity_id = commander.id
    await realm.session.flush()
    await scout_reports(ctx, SourceTally())
    seen = await realm.session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == first, BeliefRow.subject_node_id == host))
    assert seen is not None and seen.false and seen.source is BeliefSource.DECEPTION and seen.value >= 400


async def test_a_literate_people_keeps_its_beliefs_in_records(realm: Realm) -> None:
    ctx = context(realm.session, tuned(belief_state={"decay": 10, "records_pct": 50, "records_at": 40}), epoch=5)
    folk = await people(realm, "Hollowfolk")
    town = await settlement(realm, "Ivybridge")
    realm.session.add(
        PeopleCultureRow(
            people_entity_id=folk.id,
            cohesion=50,
            literacy=100,
            urbanisation=0,
            aesthetic=next(iter(Aesthetic)),
            martial_style=next(iter(MartialStyle)),
            marriage=next(iter(MarriageCustom)),
            inheritance=next(iter(InheritanceCustom)),
        )
    )
    await realm.session.flush()
    row = await believe(context(realm.session, epoch=3), folk.id, town.id, "wealth", 40, source=BeliefSource.SPY, confidence=80)
    assert row is not None
    await realm.session.flush()
    await fade_beliefs(ctx)
    assert row.source is BeliefSource.RECORDS and row.confidence == 75
