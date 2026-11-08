from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.ECONOMY


@dataclass(frozen=True)
class MethodRules:
    switch_margin_pct: int = rule(10, 0, 100, G, "How much more profit a production method must promise before a place changes to it (%)")
    nature_pollution_pct: int = rule(60, 0, 400, G, "How much a creed of harmony with nature weighs the pollution of a method against its profit (%)")
    energy_price: int = rule(4, 0, 100, G, "Value one unit of scarce energy costs when a place weighs a method")
    labour_price: int = rule(2, 0, 100, G, "Value each hand a method needs above the oldest way costs a place when it weighs a method")
    wear_price_pct: int = rule(100, 0, 400, G, "How much the price of tools weighs a method that wears them out (%)")
    displace_pct: int = rule(40, 0, 100, G, "Share of a method's gain in output that frees artisans from their craft (%)")
    displace_cap_pct: int = rule(20, 0, 100, G, "Most of a place's artisans one change of method can put out of work (%)")
    guild_progress: int = rule(15, 0, 100, G, "How far a labour-saving method pushes a craft guild's demand to protect its craft")
    nature_value_at: int = rule(30, -100, 100, G, "Love of nature from which an owner shuns methods that foul the land")
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
    heat_per_coal: int = rule(3, 0, 20, G, "Heat one unit of coal gives")
    heat_per_peat: int = rule(1, 0, 20, G, "Heat one unit of peat gives")
    heat_per_dung: int = rule(1, 0, 20, G, "Heat one unit of dried dung gives")
    magic_density_pct: int = rule(20, 0, 200, G, "Magic energy the land's magic density gives (%)")
    magic_per_ley: int = rule(8, 0, 100, G, "Magic energy each ley line through the land gives")
    divine_per_shrine: int = rule(6, 0, 100, G, "Divine energy each level of a shrine workshop gives")
    divine_per_100_clergy: int = rule(8, 0, 100, G, "Divine energy a hundred clergy give")
    magic_heat_pct: int = rule(50, 0, 400, G, "Heat each unit of spare magic gives when fuel runs short (%)")
    magic_per_mage: int = rule(6, 0, 100, G, "Magic energy each mage of a place gives")
    mage_skill_at: int = rule(3, 1, 20, G, "Spellcraft from which a mortal counts as a mage of the place")
    weather_wind_pct: int = rule(100, 0, 400, G, "How strongly the year's winds raise or lower wind energy (%)")
    light_per_1000: int = rule(2, 0, 100, G, "Lamp fuel a thousand people burn each epoch to light their evenings")
    light_work_pct: int = rule(20, 0, 200, G, "How much full light lifts what workshops can make (%)")
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
    void_rite: int = rule(8, 0, 100, G, "Air and soil pollution a rite of the void leaves on the land")


@dataclass(frozen=True)
class StoreRules:
    fish_pct: int = rule(30, 0, 100, G, "Share of unpreserved fish that spoils each sampled year (%)")
    bread_pct: int = rule(25, 0, 100, G, "Share of unpreserved bread that spoils each sampled year (%)")
    grain_pct: int = rule(6, 0, 100, G, "Share of unpreserved grain that spoils each sampled year (%)")
    medicine_pct: int = rule(5, 0, 100, G, "Share of unpreserved remedies that spoil each sampled year (%)")
    meat_pct: int = rule(30, 0, 100, G, "Share of unpreserved meat that spoils each sampled year (%)")
    milk_pct: int = rule(60, 0, 100, G, "Share of unpreserved milk that spoils each sampled year (%)")
    fruit_pct: int = rule(25, 0, 100, G, "Share of unpreserved fruit that spoils each sampled year (%)")
    cheese_pct: int = rule(3, 0, 100, G, "Share of unpreserved cheese that spoils each sampled year (%)")
    tubers_pct: int = rule(5, 0, 100, G, "Share of unpreserved tubers that spoil each sampled year (%)")
    eggs_pct: int = rule(40, 0, 100, G, "Share of unpreserved eggs that spoil each sampled year (%)")
    herbs_pct: int = rule(15, 0, 100, G, "Share of unpreserved herbs that spoil each sampled year (%)")
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
    fine_cloth_comfort: int = rule(8, 0, 50, G, "How much fine cloth in the stores lifts the need for comfort")
    noble_fine_pct: int = rule(40, 0, 400, G, "How much more nobles want luxuries when they are fine or better (%)")
    noble_coarse_satisfaction: int = rule(4, 0, 50, G, "Satisfaction nobles lose each epoch when only coarse luxuries are to be had")


@dataclass(frozen=True)
class SubstitutionRules:
    price_pct: int = rule(100, 0, 400, G, "How strongly the local price orders what people eat and burn first (%)")
    liking_pct: int = rule(100, 0, 400, G, "How strongly a people's liking for a food orders what they eat first (%)")


@dataclass(frozen=True)
class OwnershipRules:
    coin_pct: int = rule(1, 0, 100, G, "Coin each hundred value of goods sold or used brings a site's ledger (%)")
    wage_per_1000_workers: int = rule(20, 0, 1000, G, "Coin a thousand workers at a site are paid each epoch")
    upkeep_per_level: int = rule(4, 0, 100, G, "Value each level of a workshop costs its owner to keep each epoch")
    invest_pct: int = rule(20, 0, 100, G, "Share of a site's profit that goes into its settlement's investment pool (%)")
    wealth_per_value: int = rule(60, 1, 1000, G, "Value of profit that raises a mortal owner's wealth by one point")
    prosperity_per_value: int = rule(80, 1, 1000, G, "Value of wages or profit that raises a community's prosperity by one point")
    lobby_tax_pct: int = rule(12, 0, 100, G, "Share of revenue paid in taxes from which owners lobby for lower taxes (%)")
    lobby_progress: int = rule(10, 0, 100, G, "How far one epoch of heavy taxes pushes an owning faction's demand for lower taxes")
    law_progress: int = rule(10, 0, 100, G, "How far a law that bars a better method pushes an owning faction to abolish it")
    war_owner_pct: int = rule(25, 0, 400, G, "How much each owner of works starved of a resource raises the chance of a war to seize it (%)")
    price_per_level: int = rule(40, 0, 1000, G, "Value a workshop fetches for each of its levels when it is bought")


@dataclass(frozen=True)
class DrinkRules:
    needed_at: int = rule(40, 0, 100, G, "Liking for a drink from which a people needs drink rather than enjoys it")
    per_1000: int = rule(4, 1, 100, G, "Drink a thousand people want each epoch")
    need_pct: int = rule(60, 0, 100, G, "How strongly a lack of drink weighs on a people that needs it (%)")
    pleasure: int = rule(8, 0, 50, G, "How much plentiful drink lifts the pleasure of a people that only enjoys it")


@dataclass(frozen=True)
class MineRules:
    depth_pct: int = rule(100, 0, 400, G, "How much more often a mine caves in as it goes deeper, at full depth (%)")
    support_pct: int = rule(60, 0, 100, G, "How much hard rock holds the galleries up, at full hardness (%)")
    pumped_flood_pct: int = rule(50, 0, 100, G, "How much pumped shafts keep water out of a mine (%)")
    fire_cave_pct: int = rule(30, 0, 400, G, "How much more often fire-set galleries cave in (%)")
    coal_forest_at: int = rule(40, 0, 100, G, "Ancient forest cover from which a land holds coal measures under it")
    coal_seam_pct: int = rule(35, 0, 100, G, "Chance a land with coal measures holds a seam waiting to be found (%)")


@dataclass(frozen=True)
class FoodChainRules:
    milk_pct: int = rule(25, 0, 100, G, "Share of what herds yield that is milk (%)")
    dung_per_10: int = rule(3, 0, 50, G, "Dung ten units of herd yield leave for burning")
    tuber_pct: int = rule(15, 0, 100, G, "Share of a temperate harvest grown as tubers (%)")
    tuber_cold_pct: int = rule(45, 0, 100, G, "Share of a cold or poor-soiled harvest grown as tubers (%)")
    poor_soil_at: int = rule(35, 0, 100, G, "Soil fertility under which a harvest leans on tubers")
    fruit_pct: int = rule(12, 0, 100, G, "Share of a warm, moist harvest that is fruit from orchards (%)")
    fruit_moisture_at: int = rule(40, 0, 100, G, "Moisture from which orchards bear")
    peat_per_1000: int = rule(40, 0, 1000, G, "Peat a thousand farmers cut from wholly wet land each epoch")


@dataclass(frozen=True)
class ContrabandRules:
    void_corruption_at: int = rule(60, 0, 100, G, "Corruption from which a substance counts as a void material a ban on magic forbids")
    book_value: int = rule(30, 0, 1000, G, "Coin a forbidden book fetches its smugglers")
    book_crime: int = rule(3, 0, 50, G, "Crime a smuggled forbidden book adds where it is banned")
    slave_chance: int = rule(25, 0, 100, G, "Chance outlaws buy captives where slavery is banned and sell them where it is allowed (%)")
    slave_value_per_10: int = rule(4, 0, 1000, G, "Coin ten captives sold into slavery fetch their smugglers")
    slave_crime: int = rule(5, 0, 50, G, "Crime a smuggled band of captives adds where slavery is banned")
