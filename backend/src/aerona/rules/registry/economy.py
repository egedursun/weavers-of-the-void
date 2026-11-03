from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EconomyRules:
    depletion_apocalypse: int = rule(6, 0, 100, RuleGroup.APOCALYPSE, "Contribution of a depleted costly resource to the apocalypse")
    cosmic_deposit_chance: int = rule(6, 0, 100, RuleGroup.ECONOMY, "A people finds a cosmic resource deposit (% per epoch)")
    sentient_resource_choose_chance: int = rule(35, 0, 100, RuleGroup.ECONOMY, "A sentient resource chooses its owner (%)")
    sentient_resource_keep_chance: int = rule(60, 0, 100, RuleGroup.ECONOMY, "A wealthy owner keeps the resource (%)")
    sacred_resource_curse_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "The resource's god curses its foreign owner (%)")
    withdrawal_recovery_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "One suffering withdrawal recovers from addiction (%)")
    market_found_chance: int = rule(25, 0, 100, RuleGroup.ECONOMY, "A cosmic market is founded (%)")
    market_move_chance: int = rule(60, 0, 100, RuleGroup.ECONOMY, "The market moves to another region (%)")
    market_trade_chance: int = rule(20, 0, 100, RuleGroup.ECONOMY, "The market forms new trade links (%)")
    pirate_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "Pirates spawn on a busy route (%)")
    decay_loss: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Per-epoch abundance loss of a decaying resource")
    fixed_regen_clawback: int = rule(4, 0, 100, RuleGroup.ECONOMY, "Per-epoch regeneration clawed back from a fixed-quantity resource")
    addiction_epochs: int = rule(2, 0, 100, RuleGroup.ECONOMY, "Epochs of owning the resource needed to become addicted")
    addiction_immunity_epochs: int = rule(
        6, 0, 1000, RuleGroup.ECONOMY, "Epochs during which a community that recovered from addiction cannot become addicted to the same resource again"
    )
    sentient_owner_prosperity: int = rule(45, 0, 100, RuleGroup.ECONOMY, "Prosperity of an owner able to meet a sentient resource's demand")
    sentient_owner_default: int = rule(40, 0, 100, RuleGroup.ECONOMY, "Prosperity assumed for an owner with unknown prosperity and wealth")
    sentient_demand_cost: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Prosperity and wealth cost of a sentient resource's demand")
    sacred_wrath: int = rule(5, 0, 100, RuleGroup.ECONOMY, "God's wrath gain when a foreigner mines a sacred resource")
    withdrawal_min_abundance: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Minimum resource abundance an addict can make do with")
    withdrawal_loss: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Prosperity, defense, strength and faith loss in withdrawal")
    withdrawal_population_kept_pct: int = rule(95, 0, 100, RuleGroup.ECONOMY, "Share of population kept in withdrawal (%)")
    fold_abundance_cost: int = rule(12, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic resource abundance spent by space folding")
    fold_addiction_count: int = rule(2, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Addiction to the resource after this many space folds")
    monopoly_gain: int = rule(3, 0, 100, RuleGroup.ECONOMY, "Per-epoch wealth, prosperity and sway gain of a cosmic monopoly")
    traffic_window_epochs: int = rule(3, 0, 100, RuleGroup.ECONOMY, "Number of recent epochs counted for route traffic")
    market_power: int = rule(4, 1, 12, RuleGroup.ECONOMY, "Power level of a wandering market")
    market_strength: int = rule(20, 0, 100, RuleGroup.ECONOMY, "Strength of a wandering market")
    market_wealth: int = rule(70, 0, 100, RuleGroup.ECONOMY, "Wealth of a wandering market")
    market_sway: int = rule(55, 0, 100, RuleGroup.ECONOMY, "Sway of a wandering market")
    market_reach: int = rule(6, 0, 1000, RuleGroup.ECONOMY, "Maximum communities a wandering market enlivens")
    market_prosperity: int = rule(2, 0, 100, RuleGroup.ECONOMY, "Prosperity contribution of a wandering market to communities on its world")
    pirate_min_traffic: int = rule(2, 0, 1000, RuleGroup.ECONOMY, "Minimum journeys in recent epochs for pirates to spawn")
    pirate_power: int = rule(4, 1, 12, RuleGroup.ECONOMY, "Power level of void pirates")
    pirate_strength: int = rule(55, 0, 100, RuleGroup.ECONOMY, "Base strength of void pirates")
    pirate_strength_die: int = rule(25, 1, 100, RuleGroup.ECONOMY, "Strength die of void pirates")
    pirate_wealth: int = rule(40, 0, 100, RuleGroup.ECONOMY, "Wealth of void pirates")
    pirate_sway: int = rule(30, 0, 100, RuleGroup.ECONOMY, "Sway of void pirates")
    pirate_route_danger: int = rule(2, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Danger pirates add to routes per epoch")
    pirate_route_danger_cap: int = rule(95, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Highest route danger pirates can cause")
    market_max: int = rule(1, 0, 20, RuleGroup.ECONOMY, "Maximum simultaneous wandering markets in the cosmos (0 disables)")
    pirate_max: int = rule(1, 0, 20, RuleGroup.ECONOMY, "Maximum simultaneous void-pirate communities in the cosmos (0 disables)")
    pirate_danger_decay: int = rule(
        1,
        0,
        100,
        RuleGroup.COSMOS_AND_TRAVEL,
        "When no pirates remain, per-epoch decrease of danger on pirate routes (sail, slingshot, mount); does not drop below the highest danger a new route can have",
    )
    deposit_power: int = rule(7, 1, 12, RuleGroup.ECONOMY, "Power level of a new cosmic resource deposit")
    deposit_abundance: int = rule(40, 0, 100, RuleGroup.ECONOMY, "Base abundance of a new cosmic resource deposit")
    deposit_abundance_die: int = rule(30, 1, 100, RuleGroup.ECONOMY, "Abundance die of a new cosmic resource deposit")
    deposit_value: int = rule(90, 0, 100, RuleGroup.ECONOMY, "Value of a cosmic resource deposit")
    deposit_might: int = rule(80, 0, 100, RuleGroup.ECONOMY, "Might of a cosmic resource deposit")
    consumption_grain_per_1000: int = rule(500, 0, 100000, RuleGroup.ECONOMY, "Units of grain a thousand people use in an epoch")
    consumption_livestock_per_1000: int = rule(150, 0, 100000, RuleGroup.ECONOMY, "Units of livestock a thousand people use in an epoch")
    consumption_fish_per_1000: int = rule(100, 0, 100000, RuleGroup.ECONOMY, "Units of fish a thousand people use in an epoch")
    consumption_bread_per_1000: int = rule(200, 0, 100000, RuleGroup.ECONOMY, "Units of bread a thousand people use in an epoch")
    consumption_fodder_per_1000: int = rule(50, 0, 100000, RuleGroup.ECONOMY, "Units of fodder a thousand people use in an epoch")
    consumption_timber_per_1000: int = rule(25, 0, 100000, RuleGroup.ECONOMY, "Units of timber a thousand people use in an epoch")
    consumption_fuel_per_1000: int = rule(30, 0, 100000, RuleGroup.ECONOMY, "Units of fuel a thousand people use in an epoch")
    consumption_ore_per_1000: int = rule(0, 0, 100000, RuleGroup.ECONOMY, "Units of ore a thousand people use in an epoch")
    consumption_stone_per_1000: int = rule(10, 0, 100000, RuleGroup.ECONOMY, "Units of stone a thousand people use in an epoch")
    consumption_cloth_per_1000: int = rule(20, 0, 100000, RuleGroup.ECONOMY, "Units of cloth a thousand people use in an epoch")
    consumption_tools_per_1000: int = rule(8, 0, 100000, RuleGroup.ECONOMY, "Units of tools a thousand people use in an epoch")
    consumption_weapons_per_1000: int = rule(5, 0, 100000, RuleGroup.ECONOMY, "Units of weapons a thousand people use in an epoch")
    consumption_armour_per_1000: int = rule(3, 0, 100000, RuleGroup.ECONOMY, "Units of armour a thousand people use in an epoch")
    consumption_mounts_per_1000: int = rule(2, 0, 100000, RuleGroup.ECONOMY, "Units of mounts a thousand people use in an epoch")
    consumption_siege_materiel_per_1000: int = rule(1, 0, 100000, RuleGroup.ECONOMY, "Units of siege materiel a thousand people use in an epoch")
    consumption_medicine_per_1000: int = rule(5, 0, 100000, RuleGroup.ECONOMY, "Units of medicine a thousand people use in an epoch")
    consumption_luxuries_per_1000: int = rule(10, 0, 100000, RuleGroup.ECONOMY, "Units of luxuries a thousand people use in an epoch")
    consumption_incense_per_1000: int = rule(4, 0, 100000, RuleGroup.ECONOMY, "Units of incense a thousand people use in an epoch")
    consumption_sacred_goods_per_1000: int = rule(3, 0, 100000, RuleGroup.ECONOMY, "Units of sacred goods a thousand people use in an epoch")
    consumption_magical_reagents_per_1000: int = rule(2, 0, 100000, RuleGroup.ECONOMY, "Units of magical reagents a thousand people use in an epoch")
    supply_index_epoch: int = rule(
        100, 1, 1000, RuleGroup.ECONOMY, "Supply index that stands for one epoch of a community's needs (the food, ore and goods gauges)"
    )
    storage_base_index: int = rule(150, 0, 10000, RuleGroup.ECONOMY, "Supply index a community can store without granaries or warehouses")
    storage_per_granary_level: int = rule(100, 0, 10000, RuleGroup.ECONOMY, "Extra food supply index stored per granary level")
    storage_per_warehouse_level: int = rule(100, 0, 10000, RuleGroup.ECONOMY, "Extra supply index of other goods stored per warehouse level")
    farm_units_per_1000_farmers: int = rule(1300, 0, 100000, RuleGroup.ECONOMY, "Units of food a thousand farmers raise in an epoch at a neutral harvest")
    fodder_share_pct: int = rule(20, 0, 100, RuleGroup.ECONOMY, "Share of pasture output cut as fodder rather than raised as livestock (%)")
    prosthetic_tools_per_1000_maimed: int = rule(30, 0, 10000, RuleGroup.ECONOMY, "Tools a thousand maimed need each epoch for crutches, hooks and false limbs")
    sentient_bargain_pct_per_level: int = rule(
        6, 0, 100, RuleGroup.ECONOMY, "Chance per level of a negotiator's skill to talk a sentient resource's demand down to half (%)"
    )
    commons_timber_per_1000_farmers: int = rule(
        250, 0, 100000, RuleGroup.ECONOMY, "Timber a thousand farmers cut from their own land in an epoch at full forest cover"
    )
    commons_stone_per_1000_farmers: int = rule(
        120, 0, 100000, RuleGroup.ECONOMY, "Stone a thousand farmers gather from their own land in an epoch on the roughest ground"
    )
