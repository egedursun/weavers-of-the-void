from sqlalchemy import select

from aerona.catalog.dominion import BARGAINING_MODES, PRAYER_TONES, WORSHIP_MODES
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import PrayerTone, WorshipMode
from aerona.engine.dominion.worship import WorshipTally, mode_of, prayer_essence, prayer_tone
from tests.engine.divine.pantheon import god
from tests.engine.society.factories import Realm, context, mortal, settlement, tuned


def test_a_people_that_trades_bargains_with_a_god_it_neither_loves_nor_fears() -> None:
    rules = tuned()
    assert mode_of(rules, 10, 10, trading=30) is WorshipMode.BARGAIN
    assert mode_of(rules, 10, 10, trading=0) is WorshipMode.DEVOTION
    assert mode_of(rules, 10, 90, trading=30) is WorshipMode.APPEASEMENT
    assert WORSHIP_MODES[WorshipMode.BARGAIN].bargains and {WorshipMode.BARGAIN} == BARGAINING_MODES
    assert PRAYER_TONES[PrayerTone.PRAISE].praises and PRAYER_TONES[PrayerTone.REQUEST].asks


async def test_a_bargaining_people_asks_and_a_loving_one_praises_and_praise_feeds_the_god(realm: Realm) -> None:
    session = realm.session
    son = await god(realm, "Orrun", Domain.SEA, Domain.SKY)
    town = await settlement(realm, "Shore")
    pilgrim = await mortal(realm, "Pilgrim", location_id=town.id)
    standing = DivineStandingRow(
        community_entity_id=town.id, god_node_id=son.id, awe=0, love=70, fear=0, neglect=0, mode=WorshipMode.DEVOTION, epoch=3, locked=[]
    )
    session.add(standing)
    await session.flush()
    rules = tuned(worship={"praise_essence": 4, "praise_renown": 2})
    assert await prayer_tone(session, pilgrim, son.id, rules) is PrayerTone.PRAISE
    standing.mode = WorshipMode.BARGAIN
    assert await prayer_tone(session, pilgrim, son.id, rules) is PrayerTone.REQUEST
    session.add(MessageRow(epoch=3, sender_node_id=pilgrim.id, recipient_node_id=son.id, intent=MessageIntent.PRAYER, text="hear us", tone=PrayerTone.PRAISE))
    await session.flush()
    essence = son.essence
    tally = WorshipTally()
    await prayer_essence(context(session, rules, epoch=3), tally)
    assert son.essence == essence + 4 and tally.essence == 4
    stood = await session.scalar(select(DivineStandingRow).where(DivineStandingRow.god_node_id == son.id))
    assert stood is not None and stood.awe == 2
