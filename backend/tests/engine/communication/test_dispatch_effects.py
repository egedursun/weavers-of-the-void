from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.polity import PolityProfileRow, TreatyBreachRow, TreatyClauseRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats, TreatyStats
from aerona.engine.communication.dispatches import DispatchTally, courtesies, finest_good, tend_dispatches
from aerona.engine.communication.post import COMMODITY, TREATY, send
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.services.community_relations import change_relation, relation
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

HOSTILE = tuned(communication={"envoy_harm_pct": 100}, dispatches={"misread_pct": 100})


async def deliver_now(realm: Realm, row: MessageRow | None) -> DispatchTally:
    assert row is not None
    row.arrival_epoch = 3
    await realm.session.flush()
    tally = DispatchTally()
    await tend_dispatches(context(realm.session, HOSTILE), tally)
    return tally


async def enmity(realm: Realm, first: int, second: int, named: str) -> BondRow | None:
    found = await realm.session.scalar(
        select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.description.contains(named), BondRow.source_node_id.in_([first, second]))
    )
    return found if found is not None and {found.source_node_id, found.target_node_id} == {first, second} else None


async def test_a_hostile_court_mistreats_envoys_and_each_fate_has_its_consequence(realm: Realm) -> None:
    ctx = context(realm.session, HOSTILE)
    fates: dict[EnvoyFate, int] = {}
    for index in range(9):
        sender = await settlement(realm, f"Sender {index}")
        court = await settlement(realm, f"Court {index}")
        envoy = await mortal(realm, f"Envoy {index}", location_id=sender.id)
        realm.session.add(RelationshipRow(holder_node_id=court.id, subject_node_id=sender.id, friendship=-90, kinds=[], since_epoch=1, last_epoch=1, locked=[]))
        await realm.session.flush()
        row = await send(ctx, sender.id, court.id, DispatchContent.PLEA, Medium.ENVOY, envoy_id=envoy.id)
        tally = await deliver_now(realm, row)
        assert row is not None and row.state is DispatchState.DELIVERED and tally.envoys_harmed == 1
        assert row.envoy_fate in {EnvoyFate.INSULTED, EnvoyFate.IMPRISONED, EnvoyFate.KILLED, EnvoyFate.EXPELLED}
        fates[row.envoy_fate] = envoy.id
        if row.envoy_fate is EnvoyFate.IMPRISONED:
            assert await realm.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == envoy.id)) is not None
        if row.envoy_fate is EnvoyFate.KILLED:
            assert await enmity(realm, sender.id, court.id, envoy.name) is not None
    assert len(fates) >= 2


async def test_a_friendly_court_receives_the_envoy(realm: Realm) -> None:
    ctx = context(realm.session, HOSTILE)
    sender = await settlement(realm, "Amberly")
    court = await settlement(realm, "Bellfast")
    envoy = await mortal(realm, "Cael", location_id=sender.id)
    row = await send(ctx, sender.id, court.id, DispatchContent.PLEA, Medium.ENVOY, envoy_id=envoy.id)
    tally = await deliver_now(realm, row)
    assert row is not None and row.envoy_fate is EnvoyFate.RECEIVED and tally.envoys_harmed == 0


async def test_a_misread_proposal_breaks_the_first_clause_of_its_treaty(realm: Realm) -> None:
    ctx = context(realm.session)
    sender = await settlement(realm, "Corvel")
    reader = await settlement(realm, "Dunlow")
    treaty = await make(realm.session, "Pact of Corvel", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    first = TreatyClauseRow(treaty_entity_id=treaty.id, kind=ClauseKind.TRIBUTE, obligor_node_id=reader.id, params={}, locked=[])
    realm.session.add(first)
    realm.session.add(TreatyClauseRow(treaty_entity_id=treaty.id, kind=ClauseKind.CALL_TO_ARMS, params={}, locked=[]))
    await realm.session.flush()
    row = await send(ctx, sender.id, reader.id, DispatchContent.PROPOSAL, Medium.LETTER, payload={TREATY: treaty.id})
    assert row is not None
    row.misread = True
    row.locked = ["misread"]
    tally = await deliver_now(realm, row)
    breach = await realm.session.scalar(select(TreatyBreachRow).where(TreatyBreachRow.treaty_entity_id == treaty.id))
    assert tally.misread == 1 and breach is not None
    assert breach.clause_id == first.id and breach.breaker_node_id == reader.id and breach.note == "misread"


async def test_a_clear_proposal_breaks_no_clause(realm: Realm) -> None:
    ctx = context(realm.session)
    sender = await settlement(realm, "Eldham")
    reader = await settlement(realm, "Fennick")
    treaty = await make(realm.session, "Pact of Eldham", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    realm.session.add(TreatyClauseRow(treaty_entity_id=treaty.id, kind=ClauseKind.TRIBUTE, params={}, locked=[]))
    await realm.session.flush()
    row = await send(ctx, sender.id, reader.id, DispatchContent.PROPOSAL, Medium.LETTER, payload={TREATY: treaty.id})
    await deliver_now(realm, row)
    assert await realm.session.scalar(select(TreatyBreachRow).where(TreatyBreachRow.treaty_entity_id == treaty.id)) is None


async def test_insults_threats_and_demands_cool_a_court_while_pleas_warm_it(realm: Realm) -> None:
    ctx = context(realm.session)
    rules = ctx.rules
    outcomes = {}
    for content in (DispatchContent.INSULT, DispatchContent.THREAT, DispatchContent.DEMAND, DispatchContent.PLEA):
        sender = await settlement(realm, f"From {content.value}")
        court = await settlement(realm, f"To {content.value}")
        before = await relation(realm.session, rules, court.id, sender.id)
        row = await send(ctx, sender.id, court.id, content, Medium.LETTER)
        await deliver_now(realm, row)
        outcomes[content] = await relation(realm.session, rules, court.id, sender.id) - before
    assert outcomes[DispatchContent.INSULT] < 0
    assert outcomes[DispatchContent.THREAT] < 0
    assert outcomes[DispatchContent.DEMAND] <= 0
    assert outcomes[DispatchContent.PLEA] > 0


async def test_a_forged_declaration_starts_a_war_against_the_named_sender(realm: Realm) -> None:
    ctx = context(realm.session)
    named = await settlement(realm, "Galen")
    deceived = await settlement(realm, "Hollin")
    row = await send(ctx, named.id, deceived.id, DispatchContent.DECLARATION, Medium.LETTER, forged=True)
    await deliver_now(realm, row)
    hostility = await enmity(realm, deceived.id, named.id, named.name)
    assert hostility is not None and "letter" in (hostility.description or "")


async def realm_with_seat(realm: Realm, name: str) -> tuple[int, int]:
    polity = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    seat = await settlement(realm, f"Seat of {name}")
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=seat.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    await realm.session.flush()
    return polity.id, seat.id


async def test_a_ruler_sends_its_finest_good_to_a_realm_it_is_warm_to(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"ruler_gift_pct": 100, "ruler_insult_pct": 0}))
    giver, seat = await realm_with_seat(realm, "Ivel")
    friend, _ = await realm_with_seat(realm, "Jessamy")
    realm.session.add(CommunityStockRow(community_entity_id=seat, commodity=CommodityKind.GRAIN, quantity=5))
    realm.session.add(CommunityStockRow(community_entity_id=seat, commodity=CommodityKind.CLOTH, quantity=50))
    await realm.session.flush()
    assert await finest_good(ctx, giver) == CommodityKind.CLOTH.value
    await change_relation(ctx, giver, friend, 100, MemoryKind.GIFTED_ME)
    tally = DispatchTally()
    await courtesies(ctx, await RegionAtlas.load(realm.session), tally)
    gift = await realm.session.scalar(select(MessageRow).where(MessageRow.sender_node_id == giver, MessageRow.recipient_node_id == friend))
    assert tally.sent >= 1 and gift is not None
    assert gift.content is DispatchContent.GIFT_NOTICE and gift.payload[COMMODITY] == CommodityKind.CLOTH.value


async def test_a_ruler_insults_a_realm_it_is_cold_to_and_a_realm_without_a_seat_has_no_good(realm: Realm) -> None:
    ctx = context(realm.session, tuned(communication={"ruler_gift_pct": 0, "ruler_insult_pct": 100}))
    scorner, _ = await realm_with_seat(realm, "Kestrel")
    scorned, _ = await realm_with_seat(realm, "Lorne")
    seatless = await make(realm.session, "Marrow", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    assert await finest_good(ctx, seatless.id) is None
    assert await finest_good(ctx, scorner) is None
    await change_relation(ctx, scorner, scorned, -100, MemoryKind.ILL_WILL)
    await courtesies(ctx, await RegionAtlas.load(realm.session), DispatchTally())
    insult = await realm.session.scalar(select(MessageRow).where(MessageRow.sender_node_id == scorner, MessageRow.recipient_node_id == scorned))
    assert insult is not None and insult.content is DispatchContent.INSULT
