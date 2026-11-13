from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow
from aerona.db.tables.equipment import EquipmentModelRow, EquipmentStoreRow, UnitDesignEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.integrity import MegastructureRow, StructureSectionRow
from aerona.db.tables.military import UnitDesignRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.vehicles import DesignMountRow, DesignSectionRow, VehicleGroupRow, VehicleGroupSectionRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
DRAWER = "section-made-kinds"

MADE_KIND_MECHANICS = (
    Mechanic(
        key="equipment_models",
        spec_item="S7.6",
        title="Equipment models: each holder forges named weapons, armour and materiel of its own families and materials into stores its armies draw on",
        subsystem=S.WAR,
        phases=("equipment_forging",),
        surface=Surface(drawer=DRAWER),
        backfill="equipment_forging: every holder with a forge draws its first models and fills its stores on the first epoch after the upgrade",
        templates=(),
        tables=(EquipmentModelRow.__tablename__, EquipmentStoreRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("forge_model", "shape_equipment"),
        targets=("polity", "settlement", "people", "army"),
        couplings=(
            Coupling(S.ECONOMY, "forges turn weapons, armour and materiel goods into pieces of a model", E.FLOW, "armament.forge_share_pct"),
            Coupling(S.WAR, "the pieces a stack carries set its damage, piercing and protection", E.MODIFIER, "armament.battle_wear"),
            Coupling(S.WAR, "a beaten army drops pieces the victor takes into store", E.FLOW, "armament.capture_pct"),
        ),
    ),
    Mechanic(
        key="unit_types",
        spec_item="S5.14",
        title=(
            "Kinds of soldier: each realm draws its own named types for its battlefield "
            "roles, refits them as better equipment is known and teaches them to allies"
        ),
        subsystem=S.WAR,
        phases=("unit_types",),
        surface=Surface(drawer=DRAWER),
        backfill="unit_types: every realm draws its kinds of soldier for the roles its template asks for on the first epoch after the upgrade",
        templates=("unit_types.",),
        tables=(UnitDesignRow.__tablename__, UnitDesignEquipmentRow.__tablename__, UnitDesignTechniqueRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("draft_unit_type", "design_unit"),
        targets=("polity", "settlement", "people"),
        couplings=(
            Coupling(S.WAR, "armies muster their realm's own kinds of soldier when their makers know the techniques", E.TRIGGER, "unit_types.draw_pct"),
            Coupling(S.KNOWLEDGE, "better equipment known leads to a refitted kind", E.TRIGGER, "unit_types.refit_pct"),
            Coupling(S.POLITY, "allies learn each other's kinds of soldier", E.FLOW, "unit_types.spread_pct"),
        ),
    ),
    Mechanic(
        key="vehicles",
        spec_item="S7.7",
        title=(
            "Vehicle types and groups: frames, sections of differing criticality, weapon mounts "
            "and techniques; yards build groups that march, sail and fight with armies"
        ),
        subsystem=S.WAR,
        phases=("vehicle_works",),
        surface=Surface(drawer=DRAWER),
        backfill="vehicle_works: every design is completed with its frame's sections and mounts and yards build to it from the first epoch after the upgrade",
        templates=("designs.",),
        tables=(
            DesignRow.__tablename__,
            DesignSectionRow.__tablename__,
            DesignMountRow.__tablename__,
            VehicleGroupRow.__tablename__,
            VehicleGroupSectionRow.__tablename__,
        ),
        exposure=Exposure.TOOL,
        tools=("draw_design", "shape_vehicle_type", "commission_vessel"),
        targets=("polity", "settlement", "army"),
        couplings=(
            Coupling(S.ECONOMY, "yards turn timber, ore and coin into vehicles", E.FLOW, "vehicles.yard_points"),
            Coupling(S.WAR, "the slowest land vehicle sets an army's pace", E.MODIFIER, "vehicles.walk_pace"),
            Coupling(S.WAR, "battle hits strike vehicle sections; critical ones lose the vehicle", E.MODIFIER, "vehicles.battle_hits_pct"),
            Coupling(S.WAR, "the victor takes disabled vehicles as prizes", E.FLOW, "vehicles.prize_pct"),
        ),
    ),
    Mechanic(
        key="structure_integrity",
        spec_item="S7.9",
        title=(
            "Structures stand in sections: gates, walls, keeps, sanctums and foundations fail by "
            "criticality, fire spreads by material and collapse runs down from the foundation"
        ),
        subsystem=S.WAR,
        phases=("megastructures",),
        surface=Surface(drawer=DRAWER),
        backfill="none: a structure's sections are laid from its kind's layout the first time it is struck or edited",
        templates=("structures.",),
        tables=(StructureSectionRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("structure",),
        couplings=(
            Coupling(S.WAR, "a fallen keep opens the siege", E.TRIGGER, "integrity.keep_breaches"),
            Coupling(S.FAITH, "a ruined sanctum shames its faithful", E.MODIFIER, "integrity.desecration_piety"),
            Coupling(S.KNOWLEDGE, "a broken archive loses volumes", E.FLOW, "integrity.archive_loss_pct"),
            Coupling(S.ECONOMY, "destroyed stores lose grain", E.FLOW, "integrity.stores_loss_pct"),
        ),
    ),
    Mechanic(
        key="megastructures",
        spec_item="S7.10",
        title=(
            "Megastructures: star collectors, beacons, orbital rings, planetary engines and habitat rings "
            "work on their stars, routes and worlds while their control cores hold"
        ),
        subsystem=S.COSMOS,
        phases=("megastructures",),
        surface=Surface(drawer=DRAWER),
        backfill="megastructures: every megastructure keeps its state from the first epoch after the upgrade",
        templates=("megastructures.",),
        tables=(MegastructureRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("structure", "world"),
        couplings=(
            Coupling(S.COSMOS, "a star collector dims its star", E.MODIFIER, "megastructures.collector_dim"),
            Coupling(S.ECONOMY, "a star collector pays its owner", E.FLOW, "megastructures.collector_coin"),
            Coupling(S.COSMOS, "a planetary engine moves its world", E.MODIFIER, "megastructures.engine_step_pct"),
            Coupling(S.FAITH, "the star's faithful resent its collector", E.MODIFIER, "megastructures.collector_regard"),
        ),
    ),
    Mechanic(
        key="dishes",
        spec_item="S7.12",
        title=(
            "Dishes: each people invents named dishes from its stores and ways of cooking; "
            "towns cook them to feed, calm and honour, armies carry the ones that keep"
        ),
        subsystem=S.CULTURE,
        phases=("kitchens",),
        surface=Surface(drawer=DRAWER),
        backfill="kitchens: every people comes to cook its first dishes over the epochs after the upgrade",
        templates=("cuisine.",),
        tables=(DishRow.__tablename__, DishIngredientRow.__tablename__, CommunityDishRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("create_dish", "shape_dish"),
        targets=("people", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "cooking spends a town's food", E.FLOW, "cuisine.portion"),
            Coupling(S.SOCIAL, "a delightful dish calms unrest", E.MODIFIER, "cuisine.delight_pct"),
            Coupling(S.FAITH, "rite dishes deepen piety", E.MODIFIER, "cuisine.rite_pct"),
            Coupling(S.WAR, "rations lengthen an army's supply", E.MODIFIER, "cuisine.ration_days"),
        ),
    ),
    Mechanic(
        key="attraction",
        spec_item="S3.1b",
        title="Attraction: whom each mortal is drawn to and how strongly, settled from the rules of its world and gating courtship and bonds",
        subsystem=S.SOCIAL,
        phases=("attraction",),
        surface=Surface(drawer=DRAWER),
        backfill="attraction: every mortal's leanings are settled on the first epoch after the upgrade",
        templates=(),
        tables=(MortalProfileRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("mortal",),
        couplings=(Coupling(S.HOUSEHOLD, "courtship and bonds form only where attraction runs", E.MODIFIER, "attraction.caste_cut_pct"),),
    ),
    Mechanic(
        key="cognitive_decline",
        spec_item="S3.1b",
        title="Cognitive decline: the old may lose their memory by degrees, forgetting skills, teaching less and losing office",
        subsystem=S.BODY,
        phases=("cognitive_decline",),
        surface=Surface(drawer=DRAWER),
        backfill="none: decline begins among the old from the first epoch after the upgrade",
        templates=(),
        tables=(),
        exposure=Exposure.CONTEXT,
        targets=("mortal",),
        couplings=(Coupling(S.KNOWLEDGE, "a failing mind forgets what it learned and cannot teach", E.MODIFIER),),
    ),
    Mechanic(
        key="cosmic_wounds",
        spec_item="S10.17",
        title=(
            "Wounds of cosmic and outer beings: a vast body takes injuries and lasting conditions that cut its might, sight and roaming until it heals or falls"
        ),
        subsystem=S.COSMOS,
        phases=("being_wounds",),
        surface=Surface(drawer=DRAWER),
        backfill="none: a being's body is grown the first time it is struck",
        templates=("cosmic_wounds.",),
        tables=(),
        exposure=Exposure.TOOL,
        tools=("strike_being",),
        levers=("cosmic_wound:strike",),
        targets=("cosmic_being", "outer_being"),
        couplings=(
            Coupling(S.COSMOS, "a wounded being loses might", E.MODIFIER, "cosmic_wounds.damage_pct"),
            Coupling(S.COSMOS, "a being too wounded to roam stays where it is", E.RULE_SWITCH, "cosmic_wounds.roam_floor"),
            Coupling(S.WAR, "armies that meet an incursion wound it", E.FLOW, "cosmic_wounds.army_wound"),
        ),
    ),
)
