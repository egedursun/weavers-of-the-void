from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class CityPlanRules:
    cells_per_level: int = rule(3, 1, 8, S, "Hexes of the city plan each level of a district covers")
    ring_spacing: int = rule(1, 1, 6, S, "Hexes between the rings of the city plan's zones, from the seat of government outward")
    household: int = rule(5, 1, 50, S, "People living in one dwelling of a district")
    residential_housing_pct: int = rule(160, 0, 400, S, "Homes a residential quarter holds against another district of its level (%)")
    farmland_housing_pct: int = rule(80, 0, 400, S, "Homes farmland holds against a district of its level that is only homes (%)")
    market_housing_pct: int = rule(80, 0, 400, S, "Homes a market quarter holds against a district of its level that is only homes (%)")
    craft_quarter_housing_pct: int = rule(90, 0, 400, S, "Homes a craft quarter holds against a district of its level that is only homes (%)")
    industrial_housing_pct: int = rule(30, 0, 400, S, "Homes an industrial district holds against a district of its level that is only homes (%)")
    business_housing_pct: int = rule(40, 0, 400, S, "Homes a business district holds against a district of its level that is only homes (%)")
    research_housing_pct: int = rule(40, 0, 400, S, "Homes a research district holds against a district of its level that is only homes (%)")
    transport_hub_housing_pct: int = rule(30, 0, 400, S, "Homes a transport hub holds against a district of its level that is only homes (%)")
    military_base_housing_pct: int = rule(50, 0, 400, S, "Homes a military base holds against a district of its level that is only homes (%)")
    university_housing_pct: int = rule(60, 0, 400, S, "Homes a university district holds against a district of its level that is only homes (%)")
    entertainment_housing_pct: int = rule(40, 0, 400, S, "Homes an entertainment district holds against a district of its level that is only homes (%)")
    suburb_housing_pct: int = rule(110, 0, 400, S, "Homes a suburb holds against a district of its level that is only homes (%)")
    arcology_housing_pct: int = rule(250, 0, 400, S, "Homes an arcology holds against a district of its level that is only homes (%)")
    temple_quarter_housing_pct: int = rule(70, 0, 400, S, "Homes a temple quarter holds against a district of its level that is only homes (%)")
    harbour_housing_pct: int = rule(70, 0, 400, S, "Homes a harbour quarter holds against a district of its level that is only homes (%)")
    citadel_housing_pct: int = rule(50, 0, 400, S, "Homes a citadel holds against a district of its level that is only homes (%)")
    slums_housing_pct: int = rule(150, 0, 400, S, "Homes the slums hold against a district of its level that is only homes (%)")
    camp_housing_pct: int = rule(180, 0, 400, S, "Shelters a camp of the displaced crowds in against a district of its level that is only homes (%)")
    lazaretto_housing_pct: int = rule(
        60, 0, 400, S, "Beds a lazaretto holds for the sick and those held apart against a district of its level that is only homes (%)"
    )
    palace_housing_pct: int = rule(40, 0, 400, S, "Homes a palace quarter holds against a district of its level that is only homes (%)")
    foreign_quarter_housing_pct: int = rule(110, 0, 400, S, "Homes a foreign quarter holds against a district of its level that is only homes (%)")
    necropolis_housing_pct: int = rule(0, 0, 400, S, "Homes a necropolis holds against a district of its level that is only homes (%)")
    civic_quarter_housing_pct: int = rule(50, 0, 400, S, "Homes a civic quarter holds against a district of its level that is only homes (%)")
    gardens_housing_pct: int = rule(30, 0, 400, S, "Homes gardens hold against a district of its level that is only homes (%)")
    civic_quarter_at: int = rule(
        3, 1, 20, S, "Schools, healers, arenas, theatres, libraries and almshouses a town needs before it gathers them into a civic quarter"
    )
    gardens_prosperity: int = rule(60, 0, 100, S, "Prosperity a town with parks or fountains needs before it lays out gardens")
    modern_quarter_at: int = rule(1, 1, 20, S, "Works of one kind of quarter a town needs before it lays out that quarter")
    industrial_worker_pct: int = rule(15, 0, 100, S, "Worker share at which a town lays out an industrial district (%)")
    business_share_pct: int = rule(20, 0, 100, S, "Share of professionals and merchants at which a city lays out a business district (%)")
    garden_amenity: int = rule(10, 0, 100, S, "Desirability gardens give the districts near them")
    civic_reach_pct: int = rule(120, 100, 300, S, "How much further a service in the civic quarter reaches, against a service elsewhere (%)")
    almshouse_shelter: int = rule(40, 0, 10000, S, "Homeless each level of an almshouse shelters each epoch")
    almshouse_calm: int = rule(2, 0, 100, S, "Unrest each almshouse calms each epoch")
    almshouse_need_pct: int = rule(5, 0, 100, S, "Share of its people homeless past which a town wants an almshouse (%)")
