from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow, VeteranGrantRow, VeteranPolicyRow
from aerona.db.tables.means import ContainerStockRow, NavigationKitRow, SecurityRow, WaterLiftRow, WritingCustomRow, WrittenWorkRow
from aerona.db.tables.orders import (
    BillOfExchangeRow,
    ChainHoldingRow,
    EconomicOrderKindRow,
    EconomicOrderRow,
    ExchangeRateRow,
    HoardRow,
    OrderTransitionRow,
    PuttingOutRow,
    SavingRow,
    TouristFlowRow,
)
from aerona.db.tables.world_views import WorldViewRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
MEANS = "section-means"
ORDERS = "section-orders"
HONOURS = "section-honours"

MEANS_MECHANICS = (
    Mechanic(
        key="writing_media",
        spec_item="S7.1/RP6",
        title="Writing media: each people writes on its own medium, and a work's medium decides how it rots in the damp, burns or bakes in fire and is copied",
        subsystem=S.KNOWLEDGE,
        phases=("written_media", "settlement_life", "research_cycles"),
        surface=Surface(drawer=MEANS, chart="chart-writing"),
        backfill="written_media: every people takes its medium and every written work its medium from the next epoch",
        tables=(WritingCustomRow.__tablename__, WrittenWorkRow.__tablename__),
        targets=("people", "item", "settlement", "structure"),
        couplings=(
            Coupling(S.ENVIRONMENT, "the damp of a land rots works on bark, leaf, papyrus and paper", E.MODIFIER, "writing_media.rot_pct"),
            Coupling(S.ENVIRONMENT, "a fire burns works of a burning medium", E.TRIGGER, "writing_media.fire_loss"),
            Coupling(S.ENVIRONMENT, "a fire bakes works on clay harder", E.TRIGGER, "writing_media.clay_baking"),
            Coupling(S.KNOWLEDGE, "works on a medium that copies quickly gain copies", E.FLOW, "writing_media.copy_gain"),
            Coupling(S.KNOWLEDGE, "printing multiplies the copies made", E.MODIFIER, "writing_media.printing_pct"),
            Coupling(S.KNOWLEDGE, "every copy spares a work some decay", E.MODIFIER, "writing_media.copy_shield_pct"),
            Coupling(S.KNOWLEDGE, "a worn work teaches less to those who read it", E.MODIFIER, "writing_media.reading_pct"),
        ),
    ),
    Mechanic(
        key="vaults",
        spec_item="S7.1/RP6",
        title=(
            "Locks and vaults: stores of towns that work metal are locked and sealed, master smiths improve their locks, "
            "and thieves contend against lock, seal, guards and traps"
        ),
        subsystem=S.INTRIGUE,
        phases=("vaults", "intrigue"),
        surface=Surface(drawer=MEANS, chart="chart-vaults"),
        backfill="vaults: treasuries, archives and stores of metalworking towns take locks from the next epoch",
        tables=(SecurityRow.__tablename__,),
        targets=("structure", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "metalworking lets a town lock its stores", E.TRIGGER, "security.metal_level"),
            Coupling(S.ECONOMY, "a master smith improves the locks of its town", E.FLOW, "security.smith_gain"),
            Coupling(S.INTRIGUE, "a good lock thwarts a theft", E.MODIFIER, "security.lock_pct"),
            Coupling(S.INTRIGUE, "a seal betrays a theft and names the thief", E.TRIGGER, "security.seal_pct"),
            Coupling(S.INTRIGUE, "guards thwart thefts", E.MODIFIER, "security.guard_pct"),
            Coupling(S.BODY, "a trap harms the thief who springs it", E.FLOW, "security.trap_harm"),
            Coupling(S.INTRIGUE, "a thief's intrigue undoes a lock's hold", E.MODIFIER, "security.thief_pct"),
            Coupling(S.ECONOMY, "a town's first locks are of this quality", E.FLOW, "security.seed_quality"),
            Coupling(S.ECONOMY, "a store is guarded from the epoch it is first secured", E.FLOW, "security.seed_guards"),
            Coupling(S.ECONOMY, "a smith of this skill improves locks", E.TRIGGER, "security.smith_skill"),
        ),
    ),
    Mechanic(
        key="water_lifting",
        spec_item="S7.2/RP6",
        title=(
            "Water-lifting devices: dry towns and deep mines raise shadufs, norias, screws, chain and steam pumps that "
            "water fields above the river, drain mines and serve the town"
        ),
        subsystem=S.ECONOMY,
        phases=("water_lifting", "harvest", "resource_economy", "settlement_life"),
        surface=Surface(drawer=MEANS, chart="chart-water"),
        backfill="water_lifting: dry towns and mining towns raise the devices they know from the next epoch",
        tables=(WaterLiftRow.__tablename__,),
        targets=("settlement",),
        couplings=(
            Coupling(S.ENVIRONMENT, "a land below this rainfall needs water lifted", E.TRIGGER, "water_lifting.dry_below"),
            Coupling(S.ECONOMY, "lifted water raises the harvest of a dry land", E.MODIFIER, "water_lifting.irrigation_pct"),
            Coupling(S.ECONOMY, "lifted water raises a dry harvest at most so far", E.MODIFIER, "water_lifting.irrigation_cap"),
            Coupling(S.ECONOMY, "a mine this deep floods without pumps", E.TRIGGER, "water_lifting.deep_from"),
            Coupling(S.ECONOMY, "a flooded mine loses its yield", E.MODIFIER, "water_lifting.flooded_pct"),
            Coupling(S.DEMOGRAPHY, "lifted water cleans a town", E.MODIFIER, "water_lifting.sanitation_gain"),
            Coupling(S.ECONOMY, "towns that need water raise devices", E.TRIGGER, "water_lifting.build_chance"),
            Coupling(S.ECONOMY, "a town keeps this many devices of a kind", E.MODIFIER, "water_lifting.most_devices"),
        ),
    ),
    Mechanic(
        key="navigation_instruments",
        spec_item="S7.3/RP6",
        title=(
            "Navigation instruments: ports take up the compass, astrolabe, log-line and charts, navigators refine them, and "
            "their accuracy spares sea roads danger and lets ships cross the open sea"
        ),
        subsystem=S.ECONOMY,
        phases=("pilots", "trade_flow"),
        surface=Surface(drawer=MEANS, chart="chart-pilots"),
        backfill="pilots: ports take up the instruments they know from the next epoch",
        tables=(NavigationKitRow.__tablename__,),
        targets=("settlement",),
        couplings=(
            Coupling(
                S.COSMOS, "a compass points true only where the world's magnetism is strong enough", E.RULE_SWITCH, "navigation_instruments.magnetism_from"
            ),
            Coupling(S.ECONOMY, "instruments first come at this quality", E.FLOW, "navigation_instruments.seed_quality"),
            Coupling(S.KNOWLEDGE, "a navigator of this skill refines a port's instruments", E.TRIGGER, "navigation_instruments.refine_skill"),
            Coupling(S.KNOWLEDGE, "a skilled navigator refines the instruments of its port", E.FLOW, "navigation_instruments.refine_gain"),
            Coupling(S.ECONOMY, "each instrument adds its own share to a port's accuracy", E.MODIFIER, "navigation_instruments.compass_loss_cut_pct"),
            Coupling(S.ECONOMY, "a sounding line finds the shallows", E.MODIFIER, "navigation_instruments.sounding_line_loss_cut_pct"),
            Coupling(S.KNOWLEDGE, "skilled navigators keep wayfinding lore without instruments", E.MODIFIER, "navigation_instruments.wayfinding_loss_cut_pct"),
            Coupling(S.ECONOMY, "lighthouses and beacons on a shore guide ships home", E.MODIFIER, "navigation_instruments.beacons_loss_cut_pct"),
            Coupling(S.KNOWLEDGE, "a running network fixes a ship's place", E.MODIFIER, "navigation_instruments.positioning_loss_cut_pct"),
            Coupling(S.KNOWLEDGE, "the best navigator adds to a port's accuracy", E.MODIFIER, "navigation_instruments.skill_pct"),
            Coupling(S.ECONOMY, "accuracy spares sea roads their danger", E.MODIFIER, "navigation_instruments.danger_pct"),
            Coupling(S.ECONOMY, "a sea road this long leaves sight of shore", E.TRIGGER, "navigation_instruments.shore_hops"),
            Coupling(S.ECONOMY, "ships of this accuracy cross the open sea safely", E.TRIGGER, "navigation_instruments.open_sea_from"),
            Coupling(S.ECONOMY, "an open-sea road without accuracy is more dangerous", E.MODIFIER, "navigation_instruments.adrift_pct"),
        ),
    ),
    Mechanic(
        key="building_materials",
        spec_item="F3/RP6",
        title=(
            "Building materials: structures of mud brick, fired brick, dressed stone, rubble, timber, lime mortar, "
            "hydraulic concrete, thatch, tile and glass weather, burn and turn sieges by their material, and a town that "
            "forgets its technique cannot repair them"
        ),
        subsystem=S.ECONOMY,
        phases=("structure_upkeep", "settlement_life", "campaigns"),
        surface=Surface(drawer=MEANS, chart="chart-building"),
        backfill="migration c3567396253d: structures keep their recorded material and new works take the best building material their makers can work",
        targets=("structure",),
        couplings=(
            Coupling(
                S.ENVIRONMENT, "the damp of a land wears structures whose material does not resist water", E.MODIFIER, "building_materials.weathering_pct"
            ),
            Coupling(S.ENVIRONMENT, "a fire harms structures by how readily their material burns", E.TRIGGER, "building_materials.fire_harm"),
            Coupling(S.WAR, "a hard material turns aside siege harm", E.MODIFIER, "building_materials.siege_pct"),
        ),
    ),
    Mechanic(
        key="containers",
        spec_item="S6.4/RP6",
        title=(
            "Containers: potters, coopers and weavers make amphorae, barrels, sacks, crates, jars and chests that break "
            "with use, carry a town's trade, keep its stores and leave stamped marks for diggers"
        ),
        subsystem=S.ECONOMY,
        phases=("containers", "trade_flow", "industry_aftermath", "excavations"),
        surface=Surface(drawer=MEANS, chart="chart-containers"),
        backfill="containers: towns with skilled makers fill their stocks from the next epoch",
        tables=(ContainerStockRow.__tablename__,),
        targets=("settlement",),
        couplings=(
            Coupling(S.ECONOMY, "skilled makers make containers from their raw goods", E.FLOW, "containers.made_per_skill"),
            Coupling(S.ECONOMY, "a maker needs this skill", E.TRIGGER, "containers.skill_floor"),
            Coupling(S.ECONOMY, "each container carries part of a trade road's capacity", E.MODIFIER, "containers.per_capacity"),
            Coupling(S.ECONOMY, "a town short of containers fills less of its roads", E.MODIFIER, "containers.shortage_pct"),
            Coupling(S.ECONOMY, "containers break with use", E.FLOW, "containers.breakage_pct"),
            Coupling(S.ECONOMY, "sealed jars and barrels spare stores from spoiling", E.MODIFIER, "containers.sealed_pct"),
        ),
    ),
)

ORDERS_MECHANICS = (
    Mechanic(
        key="saving",
        spec_item="S6.4/RP6",
        title="Saving and hoards: patient households put by more, bury it where life is unsafe, bank or invest it otherwise; lost hoards are found by diggers",
        subsystem=S.HOUSEHOLD,
        phases=("saving", "excavations"),
        surface=Surface(drawer=ORDERS, chart="chart-savings"),
        backfill="saving: households begin to save from the next epoch",
        tables=(SavingRow.__tablename__, HoardRow.__tablename__),
        targets=("settlement", "mortal", "region", "place"),
        couplings=(
            Coupling(S.HOUSEHOLD, "a household saves this share of its surplus", E.FLOW, "saving.base_share"),
            Coupling(S.MIND, "patience moves how much a household saves", E.MODIFIER, "saving.patience_pct"),
            Coupling(S.LAW, "insecurity makes households bury what they save", E.RULE_SWITCH, "saving.insecure_from"),
            Coupling(S.WAR, "war makes a town insecure", E.MODIFIER, "saving.war_insecurity"),
            Coupling(S.ECONOMY, "lost hoards are found by those who dig", E.TRIGGER, "saving.find_chance"),
        ),
    ),
    Mechanic(
        key="exchange",
        spec_item="S6.4/RP6",
        title=(
            "Exchange rates and money changers: rates between coins follow their purity, trust, supply and trade balance, "
            "changers profit from spreads, shocks swell debts in foreign coin, and bills of exchange let merchants pay "
            "without carrying coin"
        ),
        subsystem=S.ECONOMY,
        phases=("money_changing", "trade_flow"),
        surface=Surface(drawer=ORDERS, chart="chart-rates"),
        backfill="money_changing: markets between coins set their rates from the next epoch",
        tables=(ExchangeRateRow.__tablename__, BillOfExchangeRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("change_money",),
        targets=("settlement", "mortal", "faction"),
        couplings=(
            Coupling(S.ECONOMY, "a changer asks a spread on every exchange", E.MODIFIER, "exchange_rates.base_spread"),
            Coupling(S.ECONOMY, "a weak coin widens the spread", E.MODIFIER, "exchange_rates.trust_spread"),
            Coupling(S.ECONOMY, "a trade surplus lifts a coin's worth", E.MODIFIER, "exchange_rates.balance_pct"),
            Coupling(S.ECONOMY, "coin issued lowers a coin's worth", E.MODIFIER, "exchange_rates.supply_pct"),
            Coupling(S.ECONOMY, "a sharp rise in a rate is a shock to debtors", E.TRIGGER, "exchange_rates.shock_pct"),
            Coupling(S.ECONOMY, "a shock swells debts in foreign coin at most so far", E.MODIFIER, "exchange_rates.shock_cap"),
            Coupling(S.ECONOMY, "a coin that cannot be changed taxes trade across it", E.MODIFIER, "exchange_rates.unconvertible_pct"),
            Coupling(S.KNOWLEDGE, "a merchant with accounting changes money", E.TRIGGER, "exchange_rates.changer_skill"),
            Coupling(S.ECONOMY, "the changer keeps a share of the spread", E.FLOW, "exchange_rates.changer_share"),
            Coupling(S.ECONOMY, "a bill of exchange is drawn for this much", E.FLOW, "exchange_rates.bill_amount"),
            Coupling(S.ECONOMY, "a bill of exchange spares a road's losses", E.MODIFIER, "exchange_rates.bill_loss_pct"),
            Coupling(S.ECONOMY, "a road holds this many open bills", E.MODIFIER, "exchange_rates.bills_per_route"),
        ),
    ),
    Mechanic(
        key="economic_orders",
        spec_item="S4.6/RP6",
        title="Economic orders: a realm's ownership, allocation, labour and distribution move goods, favour classes and change in stages against their losers",
        subsystem=S.POLITY,
        phases=("economic_orders",),
        surface=Surface(drawer=ORDERS, chart="chart-economic-order"),
        backfill="economic_orders: each realm reads its order from its laws, stores and guilds from the next epoch",
        tables=(EconomicOrderRow.__tablename__, EconomicOrderKindRow.__tablename__, OrderTransitionRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("set_economic_order", "begin_transition", "move_economic_order"),
        targets=("polity", "settlement", "people", "faction"),
        couplings=(
            Coupling(S.ECONOMY, "a centre's stores lose part of what it gathers", E.MODIFIER, "economic_orders.redistribution_storage_loss_pct"),
            Coupling(S.ECONOMY, "a commanded economy without planning falls short", E.TRIGGER, "economic_orders.command_efficiency_floor"),
            Coupling(S.POLITY, "officials add to a realm's planning", E.MODIFIER, "economic_orders.planning_per_official"),
            Coupling(S.KNOWLEDGE, "writing at the capital adds to planning", E.MODIFIER, "economic_orders.planning_per_record"),
            Coupling(S.POLITY, "each stage of a change of order takes this long", E.MODIFIER, "economic_orders.transition_stage_years"),
            Coupling(S.SOCIAL, "losers of an uncompensated change gather grievance", E.FLOW, "economic_orders.uncompensated_grievance"),
            Coupling(S.DEMOGRAPHY, "the aggrieved flee a change of order", E.TRIGGER, "economic_orders.flight_per_grievance_pct"),
            Coupling(S.ECONOMY, "a fallen centre takes its towns' prosperity with it", E.FLOW, "economic_orders.centre_collapse_spread_pct"),
            Coupling(S.ECONOMY, "towns send this share of their food to the centre", E.FLOW, "economic_orders.redistribution_share"),
            Coupling(S.ECONOMY, "towns owe this share of their food in dues", E.FLOW, "economic_orders.dues_share"),
            Coupling(S.SOCIAL, "distribution favours some classes and spares others", E.MODIFIER, "economic_orders.class_shift"),
            Coupling(S.ECONOMY, "a realm pays this for each holding under full compensation", E.FLOW, "economic_orders.holding_price"),
            Coupling(S.ECONOMY, "a change of order moves this many holdings each epoch", E.FLOW, "economic_orders.transfers_per_stage"),
            Coupling(S.ECONOMY, "a change of order is done after this many holdings", E.TRIGGER, "economic_orders.transfers_to_finish"),
            Coupling(S.SOCIAL, "grievance adds to resistance", E.MODIFIER, "economic_orders.resistance_pct"),
            Coupling(S.POLITY, "a change of order breaks against this much resistance", E.TRIGGER, "economic_orders.fail_from"),
            Coupling(S.POLITY, "a broken change of order costs stability", E.FLOW, "economic_orders.failure_stability"),
        ),
    ),
    Mechanic(
        key="putting_out",
        spec_item="S6.4/RP6",
        title=(
            "Putting-out and chains: merchant bodies hand raw goods to village households to make cloth or tools at home, step "
            "toward factories, and buy shares in the making of goods in towns they trade with"
        ),
        subsystem=S.ECONOMY,
        phases=("putting_out",),
        surface=Surface(drawer=ORDERS, chart="chart-putting-out"),
        backfill="putting_out: merchant bodies put work out and buy into chains from the next epoch",
        tables=(PuttingOutRow.__tablename__, ChainHoldingRow.__tablename__),
        targets=("faction", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "merchant bodies put work out to villages", E.TRIGGER, "putting_out.found_chance"),
            Coupling(S.ECONOMY, "work put out hands this much raw goods each epoch", E.FLOW, "putting_out.volume"),
            Coupling(S.ECONOMY, "the merchant keeps a margin on work put out", E.FLOW, "putting_out.merchant_margin"),
            Coupling(S.ECONOMY, "a village gains prosperity from work put out", E.FLOW, "putting_out.village_pay"),
            Coupling(S.ECONOMY, "merchant bodies buy into chains", E.TRIGGER, "putting_out.chain_chance"),
            Coupling(S.ECONOMY, "a share in a chain draws output home", E.FLOW, "putting_out.chain_share"),
            Coupling(S.KNOWLEDGE, "work put out steps a town toward factories", E.FLOW, "putting_out.proto_progress"),
        ),
    ),
    Mechanic(
        key="tourism",
        spec_item="S6.4/RP6",
        title=(
            "Tourism: the wealthy travel to wonders, baths, holy places, famous battlefields and great cities, spending in "
            "their towns, spreading their fame and carrying home ways and sickness"
        ),
        subsystem=S.CULTURE,
        phases=("tourism",),
        surface=Surface(drawer=ORDERS, chart="chart-tourism"),
        backfill="tourism: wealthy towns send travellers from the next epoch",
        tables=(TouristFlowRow.__tablename__,),
        targets=("settlement", "structure", "place", "region"),
        couplings=(
            Coupling(S.ECONOMY, "towns this prosperous send travellers", E.TRIGGER, "tourism.wealthy_from"),
            Coupling(S.ECONOMY, "a wealthy town sends this many travellers", E.FLOW, "tourism.visitors"),
            Coupling(S.ECONOMY, "each traveller spends at the sight's town", E.FLOW, "tourism.spend"),
            Coupling(S.CULTURE, "visitors spread a sight's fame", E.FLOW, "tourism.renown"),
            Coupling(S.CULTURE, "travellers carry home the ways they saw", E.TRIGGER, "tourism.word_chance"),
            Coupling(S.DEMOGRAPHY, "travellers carry home sickness", E.TRIGGER, "tourism.sickness_chance"),
        ),
    ),
)

HONOURS_MECHANICS = (
    Mechanic(
        key="unit_honours",
        spec_item="S5.1/RP6",
        title=(
            "Named units and honours: units raised from one land take a name after their first battle, gather honours and "
            "massacres on their standards, grow in esprit that steadies them, and are mourned when disbanded and raised "
            "again from their veterans"
        ),
        subsystem=S.WAR,
        phases=("campaigns",),
        surface=Surface(drawer=HONOURS, chart="chart-units"),
        backfill="migration c3567396253d: units take their names after their next battle",
        tables=(NamedUnitRow.__tablename__, UnitHonourRow.__tablename__),
        targets=("army", "polity", "settlement", "people"),
        couplings=(
            Coupling(S.WAR, "a unit takes its name with this esprit", E.FLOW, "unit_honours.seed_esprit"),
            Coupling(S.WAR, "a battle that takes this share of a unit is a massacre it remembers", E.TRIGGER, "unit_honours.massacre_share"),
            Coupling(S.WAR, "honours raise a unit's esprit", E.FLOW, "unit_honours.honour_esprit"),
            Coupling(S.WAR, "surviving a battle raises esprit", E.FLOW, "unit_honours.survival_esprit"),
            Coupling(S.WAR, "a massacre lowers esprit", E.FLOW, "unit_honours.massacre_esprit"),
            Coupling(S.WAR, "esprit steadies a unit's side in battle", E.MODIFIER, "unit_honours.morale_pct"),
            Coupling(S.POLITY, "disbanding an honoured unit costs renown", E.FLOW, "unit_honours.disband_renown"),
            Coupling(S.WAR, "a unit raised again from its veterans regains part of its esprit", E.MODIFIER, "unit_honours.reconstitute_pct"),
            Coupling(S.LANGUAGE, "a unit with enough honours earns a nickname in the tongue of its land", E.TRIGGER, "unit_honours.nickname_honours"),
            Coupling(S.CULTURE, "each honour is borne on the standard of its army or realm and raises its renown", E.FLOW, "unit_honours.standard_renown"),
        ),
    ),
    Mechanic(
        key="veterans",
        spec_item="S5.1/RP6",
        title=(
            "Veterans after war: realms grant their veterans land in a colony on the frontier or pensions from the "
            "treasury, unpaid pensions breed grievance, and veterans band into associations that press for their due and "
            "back their old commanders"
        ),
        subsystem=S.WAR,
        phases=("veterans", "factions"),
        surface=Surface(drawer=HONOURS, chart="chart-veterans"),
        backfill="veterans: wars that end from the next epoch bring grants",
        tables=(VeteranGrantRow.__tablename__, VeteranPolicyRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("grant_veterans",),
        targets=("polity", "settlement", "faction"),
        couplings=(
            Coupling(S.CULTURE, "a martial people grants its veterans land", E.RULE_SWITCH, "veterans.land_martial_from"),
            Coupling(S.DEMOGRAPHY, "this many veterans found a colony", E.TRIGGER, "veterans.colony_veterans"),
            Coupling(S.POLITY, "a veteran colony holds to the ruler who granted it", E.FLOW, "veterans.colony_loyalty"),
            Coupling(S.ECONOMY, "each veteran's pension costs the treasury", E.FLOW, "veterans.pension_cost"),
            Coupling(S.ECONOMY, "a pension is paid this long", E.MODIFIER, "veterans.paid_years"),
            Coupling(S.SOCIAL, "unpaid pensions sour the realm's towns", E.FLOW, "veterans.unpaid_grievance"),
            Coupling(S.SOCIAL, "veterans of a town band into an association", E.TRIGGER, "veterans.association_from"),
        ),
    ),
)

WORLD_VIEWS = "section-world-view"

WORLD_VIEW_MECHANICS = (
    Mechanic(
        key="world_views",
        spec_item="F45",
        title=(
            "World natures: each world carries the nature of its kind as values the god can set, and harvests, "
            "extraction, eating, fire, seasons, disasters, roads, towns and wars read it"
        ),
        subsystem=S.COSMOS,
        phases=(
            "world_views",
            "society_economy",
            "resource_economy",
            "natural_disasters",
            "world_physics",
            "horror",
            "sky",
            "settlement_life",
            "campaigns",
        ),
        surface=Surface(drawer=WORLD_VIEWS, chart="chart-world-view"),
        backfill="migration 39ded63f7c3f: every world takes the nature of its kind at the next start or epoch",
        tables=(WorldViewRow.__tablename__,),
        tools=("shift_world_nature",),
        targets=("world", "settlement", "region", "army", "resource"),
        couplings=(
            Coupling(S.ENVIRONMENT, "a harvest under starlight", E.MODIFIER, "world_views.star_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under the glow of lava", E.MODIFIER, "world_views.lava_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under light made by magic", E.MODIFIER, "world_views.magic_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under the sun inside a hollow world", E.MODIFIER, "world_views.inner_sun_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under the light of a god", E.MODIFIER, "world_views.divine_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under the light cycles of a ship", E.MODIFIER, "world_views.ship_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest under the fading light of a dead god", E.MODIFIER, "world_views.fading_light_pct"),
            Coupling(S.ENVIRONMENT, "a harvest where there is no light", E.MODIFIER, "world_views.dark_light_pct"),
            Coupling(S.ECONOMY, "a world without soil still yields this share", E.MODIFIER, "world_views.soilless_harvest_pct"),
            Coupling(S.DEMOGRAPHY, "every hundred townsfolk need this much of what their world binds them to", E.FLOW, "world_views.need_per_100"),
            Coupling(S.ECONOMY, "each lifted unit of water meets the need of this many townsfolk", E.MODIFIER, "world_views.water_lift_share"),
            Coupling(S.ENVIRONMENT, "rain enough frees a town from other water", E.RULE_SWITCH, "world_views.rain_water_from"),
            Coupling(S.FAITH, "piety enough sustains a town on a world fed by belief", E.RULE_SWITCH, "world_views.belief_from"),
            Coupling(S.SOCIAL, "a town short of what binds it grows restless", E.FLOW, "world_views.shortfall_unrest"),
            Coupling(S.ECONOMY, "a town short of what binds it loses prosperity", E.FLOW, "world_views.shortfall_prosperity"),
            Coupling(S.ECONOMY, "a floating or sealed town pays upkeep", E.FLOW, "world_views.float_upkeep"),
            Coupling(S.ECONOMY, "an unpaid upkeep costs prosperity", E.FLOW, "world_views.upkeep_unpaid_prosperity"),
            Coupling(S.WAR, "a land army wastes where wars are fought at sea, in the sky or by boarding", E.FLOW, "world_views.terrain_attrition_pct"),
            Coupling(S.COSMOS, "a son moves a share of a world's nature at most this far", E.MODIFIER, "world_views.son_step"),
            Coupling(S.COSMOS, "moving a world's nature costs a son essence", E.FLOW, "world_views.son_cost"),
        ),
    ),
)

BIOLOGY = "section-biology"

BIOLOGY_MECHANICS = (
    Mechanic(
        key="biology_variants",
        spec_item="F46",
        title=(
            "Biology variants: each people and species carries the variants of its body as values the god can set, and eating, births, deaths, "
            "sickness, battle fear, fire, storms, ageing and the leanings of minds read them"
        ),
        subsystem=S.DEMOGRAPHY,
        phases=(
            "biology_variants",
            "population_growth",
            "society_economy",
            "ecology",
            "campaigns",
            "settlement_life",
            "natural_disasters",
            "world_views",
            "mortal_aging",
            "biases",
        ),
        surface=Surface(drawer=BIOLOGY, chart="chart-biology"),
        backfill="migration 4490378d89b2: every people and species takes the variants its body shows at the next start or epoch",
        tables=(BiologyRow.__tablename__,),
        tools=("shape_biology",),
        targets=("people", "species", "settlement", "mortal", "army", "beast"),
        couplings=(
            Coupling(S.FAITH, "the leanings of a biology reach the minds of its people", E.MODIFIER, "biology_variants.bias_pct"),
            Coupling(S.COSMOS, "reshaping a body costs a son essence", E.FLOW, "biology_variants.son_cost"),
        ),
    ),
)
