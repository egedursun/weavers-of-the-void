from aerona.catalog.lore import FUNCTIONS, slot_fit
from aerona.domain.enums.culture import CalendarSlot, RiteStage, TraditionFunction


def test_twenty_functions_each_with_a_slot_fit_and_a_cost() -> None:
    assert len(FUNCTIONS) == len(TraditionFunction) == 23
    assert slot_fit(TraditionFunction.FAIR, None) is CalendarSlot.MARKET
    assert slot_fit(TraditionFunction.COMMEMORATION, None) is CalendarSlot.REMEMBRANCE
    assert slot_fit(TraditionFunction.RITE_OF_PASSAGE, RiteStage.NAMING) is CalendarSlot.NEW_YEAR
