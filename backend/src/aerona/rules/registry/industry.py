from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.ECONOMY


@dataclass(frozen=True)
class MethodRules:
    switch_margin_pct: int = rule(10, 0, 100, G, "How much more profit a production method must promise before a place changes to it (%)")
    nature_pollution_pct: int = rule(60, 0, 400, G, "How much a creed of harmony with nature weighs the pollution of a method against its profit (%)")
    energy_price: int = rule(4, 0, 100, G, "Value one unit of scarce energy costs when a place weighs a method")
    wear_price_pct: int = rule(100, 0, 400, G, "How much the price of tools weighs a method that wears them out (%)")
    displace_pct: int = rule(40, 0, 100, G, "Share of a method's gain in output that frees artisans from their craft (%)")
    displace_cap_pct: int = rule(20, 0, 100, G, "Most of a place's artisans one change of method can put out of work (%)")
    guild_progress: int = rule(15, 0, 100, G, "How far a labour-saving method pushes a craft guild's demand to protect its craft")
    guild_priority: int = rule(10, 0, 100, G, "Priority a labour-saving method adds to a craft guild's demand to protect its craft")


@dataclass(frozen=True)
class EnergyRules:
    muscle_per_100_workers: int = rule(10, 0, 100, G, "Muscle energy a hundred working hands give each epoch")
    muscle_per_10_beasts: int = rule(2, 0, 50, G, "Muscle energy ten head of livestock give as draught beasts")
    water_stream: int = rule(8, 0, 200, G, "Water energy a stream gives a place on its banks")
    water_river: int = rule(20, 0, 200, G, "Water energy a river gives a place on its banks")
    water_great_river: int = rule(40, 0, 400, G, "Water energy a great river gives a place on its banks")
    wind_base: int = rule(4, 0, 100, G, "Wind energy any open land gives")
    wind_coast: int = rule(12, 0, 200, G, "Wind energy a coast adds")
    wind_heights_pct: int = rule(20, 0, 200, G, "Wind energy rough high ground adds, by roughness (%)")
    heat_per_fuel: int = rule(2, 0, 20, G, "Heat one unit of fuel gives")
    heat_per_timber: int = rule(1, 0, 20, G, "Heat one unit of raw timber gives when there is no fuel")
    magic_density_pct: int = rule(20, 0, 200, G, "Magic energy the land's magic density gives (%)")
    magic_per_ley: int = rule(8, 0, 100, G, "Magic energy each ley line through the land gives")
    divine_per_shrine: int = rule(6, 0, 100, G, "Divine energy each level of a shrine workshop gives")
    divine_per_100_clergy: int = rule(8, 0, 100, G, "Divine energy a hundred clergy give")
    extraction_per_100_workers: int = rule(1, 0, 20, G, "How many times its need a method draws for each hundred workers at a site")
    cold_heat_per_1000: int = rule(4, 0, 100, G, "Heat a thousand people on cold land need to survive each epoch")
    frozen_heat_pct: int = rule(200, 100, 800, G, "How much more heat frozen land needs than cold land (%)")
    shortfall_note_pct: int = rule(40, 0, 100, G, "Share of an energy need left unmet before the chronicle tells of it (%)")
    frostbite_pct: int = rule(30, 0, 100, G, "Chance a named mortal of a freezing place takes frostbite when heat runs short (%)")
    frostbite_cap: int = rule(3, 0, 50, G, "Most named mortals of one place who take frostbite in one epoch")


@dataclass(frozen=True)
class PollutionRules:
    per_batch_pct: int = rule(10, 0, 200, G, "Pollution each batch made by a method adds per point of its foulness, in tenths (%)")
    crowd_air_per_10000: int = rule(2, 0, 50, G, "Air pollution ten thousand people crowded together add each epoch")
    crowd_water_per_10000: int = rule(3, 0, 50, G, "Water pollution ten thousand people crowded together add each epoch")
    recover_air: int = rule(6, 0, 50, G, "Air pollution that clears each epoch")
    recover_water: int = rule(4, 0, 50, G, "Water pollution that clears each epoch")
    recover_soil: int = rule(1, 0, 50, G, "Soil pollution that clears each epoch")
    forest_recover_pct: int = rule(50, 0, 400, G, "How much more forest cover clears pollution (%)")
    sanitation_pct: int = rule(50, 0, 100, G, "How much full sanitation keeps crowding from fouling the water (%)")
    disease_air_pct: int = rule(15, 0, 100, G, "How much air pollution adds to the land's disease load (%)")
    disease_water_pct: int = rule(30, 0, 100, G, "How much water pollution adds to the land's disease load (%)")
    fertility_soil_pct: int = rule(50, 0, 100, G, "How much full soil pollution takes from the land's fertility (%)")
    fish_water_pct: int = rule(60, 0, 100, G, "How much full water pollution takes from the catch (%)")
    opinion_at: int = rule(30, 0, 100, G, "Pollution at which people who hold nature sacred turn against the polluters")
    opinion_shift: int = rule(-4, -50, 0, G, "How much they turn against each polluter each epoch")
    blight_at: int = rule(80, 0, 100, G, "Soil pollution at which the land is blighted")
    blight_depth: int = rule(10, 0, 100, G, "Blight extreme soil pollution scars into the land each epoch")
    rite_clean: int = rule(10, 0, 100, G, "Pollution a purification rite clears from the land")


@dataclass(frozen=True)
class StoreRules:
    fish_pct: int = rule(30, 0, 100, G, "Share of unpreserved fish that spoils each epoch (%)")
    bread_pct: int = rule(25, 0, 100, G, "Share of unpreserved bread that spoils each epoch (%)")
    grain_pct: int = rule(6, 0, 100, G, "Share of unpreserved grain that spoils each epoch (%)")
    medicine_pct: int = rule(5, 0, 100, G, "Share of unpreserved remedies that spoil each epoch (%)")
    vermin_pct: int = rule(60, 0, 400, G, "How much crop pests in the land raise the spoilage of stored grain (%)")
    granary_pct: int = rule(15, 0, 100, G, "How much each level of a granary lowers spoilage (%)")
    hunters_pct: int = rule(40, 0, 100, G, "How much tame pest hunters lower the spoilage of stored grain (%)")
    preserve_pct: int = rule(30, 0, 100, G, "Share of perishables a preserving method keeps from spoiling each epoch, before its output (%)")
    tools_per_10_batches: int = rule(1, 0, 50, G, "Tools ten batches wear out per point of a method's wear")
    tools_per_1000_farmers: int = rule(3, 0, 100, G, "Tools a thousand farmers wear out each epoch per point of their method's wear")
    tools_per_1000_workers: int = rule(4, 0, 100, G, "Tools a thousand workers at a site wear out each epoch per point of their method's wear")


@dataclass(frozen=True)
class QualityRules:
    common_at: int = rule(20, 0, 100, G, "Quality from which goods are common rather than poor")
    fine_at: int = rule(45, 0, 100, G, "Quality from which goods are fine")
    superior_at: int = rule(65, 0, 100, G, "Quality from which goods are superior")
    exceptional_at: int = rule(80, 0, 100, G, "Quality from which goods are exceptional")
    masterwork_at: int = rule(90, 0, 100, G, "Quality from which goods are masterworks")
    artifact_at: int = rule(97, 0, 100, G, "Quality from which goods are artifacts")
    premium_step_pct: int = rule(25, 0, 200, G, "How much each tier above common raises the price of goods, and each below lowers it (%)")
    fine_meal_sustenance: int = rule(10, 0, 50, G, "How much a fine meal lifts the need for food")
    noble_fine_pct: int = rule(40, 0, 400, G, "How much more nobles want luxuries when they are fine or better (%)")
    noble_coarse_satisfaction: int = rule(4, 0, 50, G, "Satisfaction nobles lose each epoch when only coarse luxuries are to be had")


@dataclass(frozen=True)
class SubstitutionRules:
    price_pct: int = rule(100, 0, 400, G, "How strongly the local price orders what people eat and burn first (%)")
    liking_pct: int = rule(100, 0, 400, G, "How strongly a people's liking for a food orders what they eat first (%)")
