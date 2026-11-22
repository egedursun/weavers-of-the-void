from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.economy import CurrencyIssuer, GoodsFlow, MoneyBacking

CURRENCY_ISSUER = total(
    CurrencyIssuer,
    {
        CurrencyIssuer.COMMUNITY: Defined(
            "Community", checked_by=(), used_by=("catalog.money.issuer_kind_of", "db.tables.economy.CurrencyRow", "engine.monetary.authorities.RULER_ISSUERS")
        ),
        CurrencyIssuer.POLITY: Defined("Polity", checked_by=(), used_by=("catalog.money.issuer_kind_of", "engine.monetary.authorities.RULER_ISSUERS")),
        CurrencyIssuer.BANK: Defined("Bank", checked_by=(), used_by=("catalog.money.issuer_kind_of",)),
        CurrencyIssuer.TEMPLE: Defined("Temple", checked_by=(), used_by=("catalog.money.issuer_kind_of",)),
        CurrencyIssuer.COMPANY: Defined("Company", checked_by=(), used_by=("catalog.money.issuer_kind_of",)),
    },
)

GOODS_FLOW = total(
    GoodsFlow,
    {
        GoodsFlow.EXTRACTION: Defined(
            "Extraction",
            checked_by=(),
            used_by=(
                "engine.constructs.orders.do_gather",
                "engine.cosmos.features.add_stock",
                "engine.ecology.beasts.corpse",
                "engine.ecology.fossils.reveal",
                "engine.ecology.ranges.harvest_hunt",
                "engine.economy.extraction.byproduct",
                "engine.economy.extraction.extract",
                "engine.transform.creatures.colossal_remains",
            ),
        ),
        GoodsFlow.HARVEST: Defined(
            "Harvest",
            checked_by=("engine.divine.activity.harvests",),
            used_by=("engine.economy.household.gather_commons", "engine.economy.household.harvest_goods", "engine.nature.plants.keep_plant_defences"),
        ),
        GoodsFlow.PRODUCTION: Defined(
            "Production",
            checked_by=(),
            used_by=(
                "engine.constructs.orders.do_serve",
                "engine.constructs.remaking.keep_remade",
                "engine.crafts.chemistry.run_works",
                "engine.crafts.spirits.yield_reagents",
                "engine.ecology.domestication.produce",
                "engine.economy.refining.run_step",
                "engine.lore.traditions.apply_effect",
                "engine.made.replicators.yield_to",
                "engine.means.containers.make_containers",
                "engine.orders.putting_out.work_put_out",
            ),
        ),
        GoodsFlow.INPUT: Defined(
            "Input",
            checked_by=(),
            used_by=(
                "engine.constructs.orders.renew",
                "engine.crafts.chemistry.run_works",
                "engine.economy.money.mint",
                "engine.economy.refining.consume_inputs",
                "engine.economy.refining.launch_ships",
                "engine.equipment.stores.forge",
                "engine.industry.methods.feed",
                "engine.industry.stores.burn_fuel",
                "engine.living.profiles.fed",
                "engine.made.replicators.feed",
                "engine.mind.inspiration.make_masterwork",
                "engine.orders.putting_out.work_put_out",
                "engine.phases.society_economy.forge_weapons",
                "engine.vehicles.production.build",
            ),
        ),
        GoodsFlow.CONSUMPTION: Defined(
            "Consumption",
            checked_by=(),
            used_by=(
                "engine.body.treatment.supplied",
                "engine.cosmos.routes.provision",
                "engine.cosmos.world_views.DRAWN_FROM",
                "engine.cuisine.dishes.cook_one",
                "engine.customs.intoxicants.brew",
                "engine.demography.basket.starve_herds",
                "engine.ecology.domestication.feed",
                "engine.economy.household.burn_substitutes",
                "engine.economy.household.eat",
                "engine.economy.household.wear",
                "engine.gatherings.hold.serve",
                "engine.intrigue.schemes.poison_well",
                "engine.lore.items.repair",
                "engine.lore.rites.pay_reagents",
                "engine.lore.traditions.feast",
                "engine.vehicles.groups.burn_fuel",
            ),
        ),
        GoodsFlow.TRADE: Defined(
            "Trade",
            checked_by=("engine.orders.exchange.balance_of",),
            used_by=(
                "engine.cosmos.commerce.carry",
                "engine.cosmos.routes.load_voyage",
                "engine.cosmos.voyages.unload",
                "engine.economy.routes.haul",
                "engine.finance.policy.smuggle",
                "engine.finance.speculation.open_hoard",
                "engine.finance.speculation.settle_hoards",
                "engine.orders.putting_out.draw_chain",
            ),
        ),
        GoodsFlow.TRIBUTE: Defined(
            "Tribute", checked_by=(), used_by=("engine.ecology.beasts.tribute", "engine.orders.economy.gather", "engine.polity.treaties.pay_tribute")
        ),
        GoodsFlow.AID: Defined(
            "Aid",
            checked_by=(),
            used_by=(
                "engine.agrarian.resilience.send_grain",
                "engine.collective.storylets.apply_effect",
                "engine.divine.grammar.on_commodity",
                "engine.orders.economy.give_out",
                "engine.phases.mind.famine_aid",
                "engine.polity.mandates.begin",
            ),
        ),
        GoodsFlow.LOOT: Defined(
            "Loot",
            checked_by=(),
            used_by=(
                "engine.ecology.beast_acts.void_trophy",
                "engine.ecology.beasts.loot",
                "engine.ecology.beasts.raid",
                "engine.ecology.beasts.rob_hoard",
                "engine.economy.money.inject_hoard",
                "engine.vehicles.groups.salvage",
            ),
        ),
        GoodsFlow.LOSS: Defined(
            "Loss",
            checked_by=("engine.folkways.mishaps.land_losses",),
            used_by=(
                "engine.collective.crowds.flee",
                "engine.collective.crowds.storm",
                "engine.collective.storylets.apply_effect",
                "engine.divine.grammar.on_commodity",
                "engine.ecology.foodweb.raid_herds",
                "engine.ecology.pests.gnaw_ore",
                "engine.economy.routes.haul",
                "engine.environment.long_seasons.bite",
                "engine.military.sabotage.release_blight",
                "engine.military.sabotage.steal_supplies",
                "engine.nature.symbiosis.plague_herds",
                "engine.phases.espionage.sabotage",
                "engine.sacred.foresight.heed",
                "engine.sacred.mysteries.keep_vigil",
                "engine.structures.damage.lose_grain",
            ),
        ),
        GoodsFlow.SIEGE: Defined(
            "Siege",
            checked_by=(),
            used_by=("engine.economy.equipment.siege_engines", "engine.military.siege_depth.mason_repair", "engine.phases.warfare._siege"),
        ),
        GoodsFlow.WAR: Defined(
            "War",
            checked_by=(),
            used_by=("engine.economy.equipment._issue", "engine.military.logistics.restock", "engine.military.units.rearm", "engine.operations.supply.draw"),
        ),
        GoodsFlow.CONSTRUCTION: Defined(
            "Construction",
            checked_by=(),
            used_by=(
                "engine.constructs.orders.do_replicate",
                "engine.economy.markets.raise_district",
                "engine.economy.refining.build_workshops",
                "engine.structures.construction.advance",
                "engine.structures.construction.charge_builder",
                "engine.structures.upkeep.pay_goods",
            ),
        ),
        GoodsFlow.OVERFLOW: Defined("Overflow", checked_by=(), used_by=("engine.economy.household.enforce_storage",)),
        GoodsFlow.DECAY: Defined("Decay", checked_by=(), used_by=("engine.industry.stores.spoil",)),
        GoodsFlow.PLAYER: Defined(
            "Player",
            checked_by=(),
            used_by=(
                "engine.economy.control.grant_stock",
                "engine.economy.control_depth.set_stock",
                "engine.phases.society_economy.send_famine",
                "engine.phases.society_economy.send_plenty",
                "engine.phases.society_economy.set_stores",
                "services.player.finance.open_speculation",
                "services.player.finance.remove_speculation",
            ),
        ),
        GoodsFlow.TOOL: Defined(
            "Tool", checked_by=(), used_by=("engine.industry.stores.wear_tools", "tools.mortal.cosmos.build_ship", "tools.mortal.materials.chosen_material")
        ),
        GoodsFlow.SEED: Defined("Seed", checked_by=(), used_by=("engine.economy.survey.seed_communities", "engine.phases.society_economy.seed_stocks")),
        GoodsFlow.OFFERING: Defined(
            "Offering",
            checked_by=(),
            used_by=(
                "engine.cosmos.world_views.DRAWN_FROM",
                "engine.faith.works.tithe",
                "engine.gods.economy._pay_demand",
                "engine.lore.traditions.feast",
                "engine.phases.faith.sacrifices",
                "engine.sacred.bureau.answer",
                "engine.sacred.bureau.file_petitions",
                "engine.sacred.spirits.bless",
                "engine.sacred.spirits.bring_offerings",
            ),
        ),
    },
)

MONEY_BACKING = total(
    MoneyBacking,
    {
        MoneyBacking.METAL: Defined(
            "Metal",
            checked_by=(),
            used_by=(
                "db.tables.economy.CurrencyRow",
                "engine.economy.control_depth.NewCoin",
                "engine.economy.money.found_currency",
                "engine.economy.money.reform",
                "services.player.economy_depth.CreateCurrency",
            ),
        ),
        MoneyBacking.COMMODITY: Defined("Commodity", checked_by=(), used_by=()),
        MoneyBacking.DECREE: Defined("Decree", checked_by=(), used_by=("engine.economy.money.found_currency", "engine.economy.money.reform")),
        MoneyBacking.TRUST: Defined("Trust", checked_by=(), used_by=()),
        MoneyBacking.SOURCE: Defined("Source", checked_by=(), used_by=()),
    },
)
