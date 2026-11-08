from sqlalchemy import select

from aerona.db.tables.affairs import CourtPositionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.statecraft import CourtPosition
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.court import CourtTally, tend_courts
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

QUIET = tuned(affairs={"talent_pct": 0})


async def court_of(realm: Realm, name: str) -> tuple[EntityRow, EntityRow, EntityRow]:
    town = await settlement(realm, f"{name} Town")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=50, unrest=10, locked=[], foreigners={}))
    ruler = await mortal(realm, f"Ruler of {name}", location_id=town.id, hp=60)
    polity = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            core_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await realm.session.flush()
    return polity, town, ruler


async def courtier(realm: Realm, name: str, town: EntityRow, ruler: EntityRow, **values: int) -> EntityRow:
    found = await mortal(realm, name, location_id=town.id, intellect=10, strength=10, charisma=10)
    set_stats(found, **{"wisdom": 10, "creativity": 10, **values})
    realm.session.add(RelationshipRow(holder_node_id=found.id, subject_node_id=ruler.id, friendship=20, kinds=[], since_epoch=1, last_epoch=1))
    await realm.session.flush()
    return found


async def holder(realm: Realm, polity: EntityRow, position: CourtPosition) -> int | None:
    row = await realm.session.get(CourtPositionRow, (polity.id, position))
    return row.holder_entity_id if row is not None else None


async def standing(realm: Realm, mortal_id: int) -> MortalProfileRow:
    row = await realm.session.get(MortalProfileRow, mortal_id)
    assert row is not None
    return row


async def test_each_court_position_goes_to_the_courtier_best_at_its_work_and_does_its_duty(realm: Realm) -> None:
    ctx = context(realm.session, QUIET)
    polity, town, ruler = await court_of(realm, "Velmar")
    steward = await courtier(realm, "Steward", town, ruler, intellect=90)
    tutor = await courtier(realm, "Tutor", town, ruler, intellect=80)
    champion = await courtier(realm, "Champion", town, ruler, strength=90)
    physician = await courtier(realm, "Physician", town, ruler, wisdom=90)
    chronicler = await courtier(realm, "Chronicler", town, ruler, creativity=90)
    reveller = await courtier(realm, "Reveller", town, ruler, charisma=90)
    heir = await mortal(realm, "Heir", location_id=town.id, intellect=40)
    realm.session.add(DesignatedHeirRow(ruler_entity_id=ruler.id, heir_entity_id=heir.id, epoch=1))
    await realm.session.flush()
    tally = CourtTally()
    await tend_courts(ctx, tally)
    assert tally.appointed == 6
    assert await holder(realm, polity, CourtPosition.STEWARD) == steward.id
    assert await holder(realm, polity, CourtPosition.TUTOR) == tutor.id
    assert await holder(realm, polity, CourtPosition.CHAMPION) == champion.id
    assert await holder(realm, polity, CourtPosition.PHYSICIAN) == physician.id
    assert await holder(realm, polity, CourtPosition.CHRONICLER) == chronicler.id
    assert await holder(realm, polity, CourtPosition.MASTER_OF_REVELS) == reveller.id
    table = ctx.rules.affairs
    assert stat(heir, "intellect") == 40 + table.tutor_gain
    assert stat(ruler, "hp") == 60 + table.physician_heal
    record = await standing(realm, ruler.id)
    assert (record.honour or 0) >= table.champion_honour
    assert (record.renown or 0) >= table.chronicler_renown


async def test_a_tutor_without_an_heir_or_with_a_held_heir_teaches_nobody(realm: Realm) -> None:
    ctx = context(realm.session, QUIET)
    polity, town, ruler = await court_of(realm, "Corlan")
    await courtier(realm, "Steward", town, ruler, intellect=90)
    await courtier(realm, "Champion", town, ruler, strength=90)
    await courtier(realm, "Physician", town, ruler, wisdom=90)
    await courtier(realm, "Tutor", town, ruler, intellect=80)
    heir = await mortal(realm, "Heir", location_id=town.id, intellect=40)
    await tend_courts(ctx, CourtTally())
    assert stat(heir, "intellect") == 40
    realm.session.add(DesignatedHeirRow(ruler_entity_id=ruler.id, heir_entity_id=heir.id, epoch=1))
    await realm.session.flush()
    token = HELD_SCOPE.set(HeldScope(None, frozenset({heir.id})))
    try:
        await tend_courts(context(realm.session, QUIET, epoch=4), CourtTally())
    finally:
        HELD_SCOPE.reset(token)
    assert stat(heir, "intellect") == 40
    assert await holder(realm, polity, CourtPosition.TUTOR) is not None


async def test_a_shining_court_draws_the_most_important_mortal_of_its_other_towns(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"talent_pct": 100000}))
    polity, town, ruler = await court_of(realm, "Astren")
    await courtier(realm, "Steward", town, ruler, intellect=90)
    second = await settlement(realm, "Far Hamlet")
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=second.id))
    plain = await mortal(realm, "Plain", location_id=second.id)
    gifted = await mortal(realm, "Gifted", location_id=second.id)
    plain.importance, gifted.importance = 1, 9
    await realm.session.flush()
    tally = CourtTally()
    await tend_courts(ctx, tally)
    assert tally.drawn == 1 and gifted.location_id == town.id and plain.location_id == second.id
    assert await realm.session.scalar(select(ChronicleRow).where(ChronicleRow.template_key == "affairs.court_talent")) is not None
