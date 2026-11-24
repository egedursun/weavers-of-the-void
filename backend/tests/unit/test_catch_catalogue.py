from aerona.catalog.catch import GEAR, GROUNDS, grounds_in
from aerona.catalog.laws import LAW_EFFECTS, LAW_PARAMS
from aerona.catalog.market_ranks import RANKS, by_order, higher_markets, widest_reach
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.polity import LawProfileRow
from aerona.domain.enums.agrarian import CentralityRank
from aerona.domain.enums.crafts import CatchGround, CatchMedium, Gear
from aerona.domain.enums.polity import LawArea, LawKind
from aerona.engine.couplings.closures import bans_gear
from aerona.rules.registry import Rules


def test_every_ground_lies_in_a_medium_and_allows_its_gear() -> None:
    assert set().union(*(grounds_in(medium) for medium in CatchMedium)) == set(CatchGround)
    assert set(grounds_in(CatchMedium.UNDER_WATER)) == {CatchGround.DIVING}
    assert all(spec.gear for spec in GROUNDS.values())
    assert {gear for spec in GROUNDS.values() for gear in spec.gear} == set(Gear)
    assert GEAR[Gear.NETS].rate(Rules()) == Rules().grounds.nets_pct


def test_market_ranks_keep_their_order_and_reach() -> None:
    rules = Rules()
    order = [CentralityRank.DAILY, CentralityRank.WEEKLY, CentralityRank.REGIONAL, CentralityRank.SEASONAL, CentralityRank.RARE, CentralityRank.METROPOLITAN]
    assert by_order() == order
    assert higher_markets(CentralityRank.DAILY) == set(order[1:])
    assert higher_markets(CentralityRank.RARE) == {CentralityRank.METROPOLITAN}
    assert higher_markets(CentralityRank.METROPOLITAN) == frozenset()
    assert widest_reach(rules) == rules.central_places.metropolitan_range
    assert not RANKS[CentralityRank.DAILY].market


def test_a_gear_ban_cuts_only_the_gear_it_names() -> None:
    nets = CatchGroundRow(source_entity_id=1, region_entity_id=2, ground=CatchGround.FISHERY, gear=Gear.NETS, first_stock=10, locked=[])
    lines = CatchGroundRow(source_entity_id=1, region_entity_id=3, ground=CatchGround.FISHERY, gear=Gear.LINES, first_stock=10, locked=[])
    ban = LawProfileRow(law_entity_id=9, kind=LawKind.GEAR_BAN, area=LawArea.PROPERTY, params={"gear": "lines"}, locked=[])
    assert bans_gear(ban, lines) and not bans_gear(ban, nets)
    unnamed = LawProfileRow(law_entity_id=10, kind=LawKind.GEAR_BAN, area=LawArea.PROPERTY, params={}, locked=[])
    assert bans_gear(unnamed, nets) and not bans_gear(unnamed, lines)
    season = LawProfileRow(law_entity_id=11, kind=LawKind.CLOSED_SEASON, area=LawArea.PROPERTY, params={}, locked=[])
    assert bans_gear(season, lines)
    assert set(LAW_PARAMS[LawKind.GEAR_BAN]["gear"].choices) == {gear.value for gear in Gear}
    assert "{gear}" in LAW_EFFECTS[LawKind.GEAR_BAN]
