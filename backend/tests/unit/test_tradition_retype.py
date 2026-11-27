from aerona.catalog.lore import slot_fit
from aerona.db.tables.culture import TraditionProfileRow
from aerona.domain.enums.culture import CalendarSlot, TraditionFunction
from aerona.engine.lore.traditions import retype


def test_a_custom_given_a_new_kind_moves_to_the_time_of_year_of_that_kind() -> None:
    row = TraditionProfileRow(tradition_entity_id=1, kind=TraditionFunction.FESTIVAL, calendar_slot=slot_fit(TraditionFunction.FESTIVAL, None), locked=[])
    retype(row, TraditionFunction.VIGIL)
    assert row.kind is TraditionFunction.VIGIL and row.calendar_slot is slot_fit(TraditionFunction.VIGIL, None)


def test_a_held_time_of_year_stays_when_the_kind_changes() -> None:
    row = TraditionProfileRow(tradition_entity_id=1, kind=TraditionFunction.FESTIVAL, calendar_slot=CalendarSlot.HARVEST, locked=["calendar_slot"])
    retype(row, TraditionFunction.FAST)
    assert row.kind is TraditionFunction.FAST and row.calendar_slot is CalendarSlot.HARVEST
