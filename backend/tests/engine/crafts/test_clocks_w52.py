from aerona.catalog.life.crafts import LADDER, LONGITUDE_CLOCKS, PRECISION
from aerona.db.tables.crafts import PublicClockRow
from aerona.domain.enums.crafts import ClockKind
from aerona.engine.crafts.timekeeping import clock_navigation
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, settlement

RULES = Rules()


def test_eight_clocks_and_the_ones_that_keep_longitude() -> None:
    assert len(ClockKind) == 8 and set(PRECISION) == set(ClockKind)
    assert {ClockKind.CHRONOMETER, ClockKind.ELECTRONIC} == LONGITUDE_CLOCKS and LADDER[0][0] is ClockKind.ELECTRONIC


async def test_a_chronometer_cuts_sea_losses_beyond_its_precision(realm: Realm) -> None:
    port = await settlement(realm, "Port")
    other = await settlement(realm, "Cove")
    realm.session.add(
        PublicClockRow(settlement_entity_id=port.id, kind=ClockKind.MECHANICAL, precision=PRECISION[ClockKind.CHRONOMETER], built_epoch=1, locked=[])
    )
    await realm.session.flush()
    plain = await clock_navigation(realm.session, RULES, (port.id, other.id))
    clock = await realm.session.get(PublicClockRow, port.id)
    assert clock is not None
    clock.kind = ClockKind.CHRONOMETER
    keeping = await clock_navigation(realm.session, RULES, (port.id, other.id))
    assert abs(keeping - plain * (1 - RULES.clocks.chronometer_loss_cut_pct / 100)) < 1e-9
