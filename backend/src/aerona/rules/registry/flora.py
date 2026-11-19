from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class FloraRules(Spanned):
    annual_seasons: int = rule(1, 1, 12, G, "Growing seasons an annual plant needs in a year")
    perennial_seasons: int = rule(2, 1, 12, G, "Growing seasons a perennial plant needs in a year")
    tree_seasons: int = rule(2, 1, 12, G, "Growing seasons a tree needs in a year")
    soil_need: int = rule(30, 0, 100, G, "Soil fertility a plant needs before it grows well, unless set")
    growing_season_floor: int = rule(50, 0, 100, G, "Growth a season of the year needs to count as a growing season")
    temperature_slack: int = rule(4, 0, 50, G, "Degrees outside its band a crop bears before it suffers")
    temperature_penalty_pct: int = rule(6, 0, 100, G, "Crop fit lost for each degree beyond a plant's temperature band (%)")
    water_penalty_pct: int = rule(60, 0, 200, G, "Crop fit lost when the rain is as far as can be from a plant's water need (%)")
    weather_degrees: int = rule(12, 0, 60, G, "Degrees a year at the full cold or heat of its weather moves a land's warmth for its crops")
    weather_moisture_pct: int = rule(40, 0, 100, G, "Wetness a year at the full wet of its weather adds to a land's moisture for its crops (%)")
    soil_penalty_pct: int = rule(70, 0, 200, G, "Crop fit lost on soil with no fertility at all against a plant's need (%)")
    season_penalty_pct: int = rule(40, 0, 100, G, "Crop fit lost for each growing season short of a plant's need (%)")
    crop_weight_pct: int = rule(50, 0, 100, G, "Harvest lost when every crop sown in a land fits it not at all (%)")
    side_yield_pct: int = rule(20, 0, 200, G, "Goods besides food a crop gives for each field of food it fills, per point of its rate (%)")
    sole_yield_pct: int = rule(60, 0, 200, G, "Goods a crop grown for nothing but fibre, dye, herbs or the like gives per field, per point of its rate (%)")
    new_crop_share: int = rule(20, 1, 100, G, "Share of a land's fields a newly sown crop takes (%)")
    share_drift: int = rule(5, 0, 100, G, "Share of its fields a land shifts each epoch towards the crops that suit it best (%)")
    min_share: int = rule(2, 0, 100, G, "Share below which a crop drops out of a land's fields (%)")
    crop_cap: int = rule(30, 1, 200, G, "Most crops a land sows at once")
    gather_pct: int = rule(25, 0, 100, G, "Chance each epoch farmers or foragers begin to gather a wild plant growing in their land (%)")
    cultivate_pct: int = rule(10, 0, 100, G, "Chance each epoch a gathered plant is first sown in fields (%)")
    cultivate_level: int = rule(1, 0, 10, G, "Agriculture level a people needs before it sows a gathered plant")
    cultivar_pct: int = rule(5, 0, 100, G, "Chance each epoch a master farmer breeds a cultivar from a long-sown crop (%)")
    cultivar_years: int = span(30, 0, 5000, G, "Years a crop must be sown in a land before a cultivar can be bred from it")
    cultivar_skill: int = rule(40, 0, 100, G, "Farming skill a master farmer needs to breed a cultivar")
    cultivar_yield_pct: int = rule(25, 0, 200, G, "Rate a cultivar gains over the plant it was bred from (%)")
    cultivar_hardiness: int = rule(3, 0, 50, G, "Degrees a cultivar's temperature band widens on each side")
    cultivar_soil: int = rule(10, 0, 100, G, "Soil fertility a cultivar needs less than the plant it was bred from")
    cultivar_cap: int = rule(2, 0, 1000, G, "Most cultivars bred across the cosmos in an epoch, before its sown lands add more")
    cultivar_lands_per_extra: int = rule(5, 0, 100000, G, "Sown lands that let one more cultivar be bred in an epoch (0 for none)")
    spread_pct: int = rule(10, 0, 100, G, "Chance each epoch a sown crop passes to a neighbouring farming land that it suits (%)")
    spread_fit: int = rule(50, 0, 100, G, "Fit a land must offer before a crop passes to it")
    spread_cap: int = rule(100, 0, 100000, G, "Most lands one crop is newly sown in each epoch")
    pest_link_pct: int = rule(20, 0, 100, G, "Chance each epoch a crop pest in a land takes to one of the crops sown there (%)")
    pest_loss: int = rule(10, 0, 100, G, "Harvest a crop pest at full numbers takes from a land, scaled by the share of its host crops")
    blight_loss: int = rule(15, 0, 100, G, "Harvest a raging sickness of a crop takes from a land, scaled by that crop's share")
    sow_cost: int = rule(8, 0, 1000, G, "Essence a son spends to have a plant sown in a land's fields")
    sow_share: int = rule(25, 1, 100, G, "Share of a land's fields a crop a son has sown takes at first (%)")
    poison_well_pct: int = rule(5, 0, 100, G, "Further share of a people a poisoned well kills when the schemer brings poison from stores (%)")

    @property
    def cultivar_epochs(self) -> int:
        return self.epochs(self.cultivar_years)
