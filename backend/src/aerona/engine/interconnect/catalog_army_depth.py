from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow, ArmyTemplateRow, ArmyUnitRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.warfare import BattleRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

CAMPAIGN = ("campaigns",)
UPKEEP = ("war_upkeep",)
S = Subsystem
E = EdgeKind
ARMY = "ArmyCard"
WORKS = "ArmyWorks"
SCARS = "RegionScars"

ARMY_DEPTH_MECHANICS = (
    Mechanic(
        key="land_eaten_out",
        spec_item="S5.1/RP2",
        title="Each region feeds only so many soldiers: farmed land, the season, its harvest, what plunder left and its roads set the limit",
        subsystem=S.ECONOMY,
        phases=CAMPAIGN,
        surface=Surface(drawer=WORKS),
        backfill="computed",
        fields=("supply_limit", "harvest_pct", "farmed"),
        tables=(RegionEnvironmentRow.__tablename__, RelationshipRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("army", "region"),
        couplings=(
            Coupling(S.WAR, "an army above the limit starves soldiers away each season", E.MODIFIER, "logistics.over_supply_attrition_pct"),
            Coupling(S.ENVIRONMENT, "it eats the land out, leaving a plunder scar", E.FLOW, "army_depth.oversupply_scar"),
            Coupling(S.SOCIAL, "the communities it eats out think less of its owner", E.MODIFIER, "army_depth.oversupply_resentment"),
            Coupling(S.ECONOMY, "roads bring food from further away", E.MODIFIER, "army_depth.road_supply_pct"),
        ),
    ),
    Mechanic(
        key="field_works",
        spec_item="S5.1/RP2",
        title="Earthworks an entrenched army digs stay on the land when it leaves, and shelter whoever defends there",
        subsystem=S.ENVIRONMENT,
        phases=CAMPAIGN,
        surface=Surface(drawer=SCARS),
        backfill="none: earthworks are left by armies from now on",
        fields=("entrenchment", "scars.earthworks"),
        tables=(RegionEnvironmentRow.__tablename__, ArmyProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("army", "region"),
        couplings=(
            Coupling(S.WAR, "a defender behind earthworks holds harder", E.MODIFIER, "logistics.entrench_defence_pct"),
            Coupling(S.WAR, "sappers and a commander strong in siegecraft dig faster", E.MODIFIER, "army_depth.sapper_dig_pct"),
            Coupling(S.WAR, "charges against earthworks lose their weight", E.MODIFIER, "army_depth.earthworks_charge_pct"),
            Coupling(S.ECONOMY, "dug ground yields less harvest until it wears away", E.MODIFIER, "army_depth.earthworks_fertility_pct"),
        ),
    ),
    Mechanic(
        key="combat_engineering",
        spec_item="S5.1/RP2",
        title="Sappers bridge rivers without a ford, lay military roads and blow bridges behind a retreat",
        subsystem=S.WAR,
        phases=CAMPAIGN,
        surface=Surface(drawer=WORKS),
        backfill="none",
        fields=("scars.military_road", "scars.bridge_down"),
        tables=(RegionEnvironmentRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("army", "region"),
        couplings=(
            Coupling(S.ENVIRONMENT, "a laid road speeds marches and carries supply like a built one", E.MODIFIER, "army_depth.road_at"),
            Coupling(S.WAR, "a blown bridge slows pursuit to a ford until it is rebuilt", E.MODIFIER, "army_depth.bridge_down_decay"),
            Coupling(S.WAR, "pontoons spare the ford's delay", E.MODIFIER, "army_depth.sappers_needed"),
        ),
    ),
    Mechanic(
        key="drill_and_sparring",
        spec_item="S5.1/RP2",
        title="Standing armies drill their stacks toward their own discipline, and officers now and then take sparring injuries",
        subsystem=S.BODY,
        phases=UPKEEP,
        surface=Surface(drawer=ARMY),
        backfill="none",
        fields=("discipline", "drill"),
        tables=(ArmyUnitRow.__tablename__, ArmyProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("army",),
        couplings=(
            Coupling(S.WAR, "drill raises each stack's discipline up to the army's", E.MODIFIER, "army_depth.drill_discipline"),
            Coupling(S.BODY, "sparring hurts an officer now and then", E.TRIGGER, "army_depth.sparring_injury_pct"),
        ),
    ),
    Mechanic(
        key="patrols",
        spec_item="S5.1/RP2",
        title="Garrisoned and entrenched armies patrol their region and take bandit danger off the routes through it",
        subsystem=S.ECONOMY,
        phases=("trade_flow",),
        surface=Surface(drawer=WORKS),
        backfill="computed",
        fields=("danger_bandits",),
        tables=(ArmyProfileRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("army", "route"),
        couplings=(Coupling(S.ECONOMY, "routes through a patrolled region lose less to bandits", E.MODIFIER, "army_depth.patrol_pct"),),
    ),
    Mechanic(
        key="standards_captured",
        spec_item="S5.1/RP2",
        title="A routed or massacred side may lose its standard: the captor keeps it as a trophy, gains war score and the losers lose heart",
        subsystem=S.CULTURE,
        phases=CAMPAIGN,
        surface=Surface(drawer="BattleReport"),
        backfill="none",
        fields=("standard_entity_id", "renown"),
        tables=(BattleRow.__tablename__, ItemProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("army", "item"),
        couplings=(
            Coupling(S.WAR, "losing the standard shakes every stack of the side", E.MODIFIER, "army_depth.standard_shock"),
            Coupling(S.WAR, "the captor gains war score", E.FLOW, "army_depth.standard_score"),
            Coupling(S.CULTURE, "a taken standard gains renown as a trophy", E.FLOW, "army_depth.standard_renown"),
        ),
    ),
    Mechanic(
        key="army_templates",
        spec_item="S5.1/RP2",
        title="A realm's marshal keeps named army templates; raised armies fill from them and outdated ones are refitted as new arms arrive",
        subsystem=S.POLITY,
        phases=UPKEEP,
        surface=Surface(drawer="ArmyTemplates"),
        backfill="none: marshals draw a template the first epoch they hold office",
        fields=("composition", "doctrine", "obsolete", "active"),
        tables=(ArmyTemplateRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("polity",),
        couplings=(
            Coupling(S.WAR, "a raised army fills its template's share before its doctrine", E.MODIFIER, "army_depth.template_share"),
            Coupling(S.KNOWLEDGE, "new arms outdate a template until the marshal refits it", E.TRIGGER),
        ),
    ),
    Mechanic(
        key="commander_areas",
        spec_item="S5.1/RP2",
        title="Commanders lead best in fire, shock, manoeuvre, siege or logistics, drawn from their skills and battle traits",
        subsystem=S.MIND,
        phases=CAMPAIGN,
        surface=Surface(drawer="CommanderAreas"),
        backfill="computed",
        fields=("fire", "shock", "manoeuvre", "siege", "logistics"),
        tables=(),
        exposure=Exposure.CONTEXT,
        targets=("army", "mortal"),
        couplings=(
            Coupling(S.WAR, "each arm strikes harder under a commander strong in its area", E.MODIFIER, "army_depth.command_area_pct"),
            Coupling(S.ECONOMY, "a commander gifted at logistics stretches the stores", E.MODIFIER, "army_depth.logistics_food_pct"),
            Coupling(S.WAR, "manoeuvre saves a routed side from the pursuit", E.MODIFIER),
        ),
    ),
)
