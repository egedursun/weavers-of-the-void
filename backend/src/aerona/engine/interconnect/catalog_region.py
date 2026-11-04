from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionHazardRow, RegionMemoryRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

DANGERS = "section-region-dangers"
SANCTITY = "section-region-sanctity"
KNOWLEDGE = "section-region-knowledge"
HAZARDS = "section-region-hazards"
RIVER = "section-region-river"
DANGER_LAYER = "map-layer-danger"
RAIN_LAYER = "map-layer-rainfall"
SCAR_LAYER = "map-layer-scars"
SACRED_LAYER = "map-layer-sacred"
BACKFILL = "region_survey: every region's dangers, sacredness, memory of its battles, disasters, saints and fallen gods, and every realm's maps"
S = Subsystem
LANDS = ("region", "settlement", "people")

REGION_MECHANICS = (
    Mechanic(
        key="region_dangers",
        spec_item="S6.1",
        title="Danger is typed: beasts, bandits, monsters, phenomena, disease, avalanches, quicksand and volcanic ground, each bred by the land",
        subsystem=S.ENVIRONMENT,
        phases=("region_survey", "tradition_cycles"),
        surface=Surface(drawer=DANGERS, layer=DANGER_LAYER),
        backfill=BACKFILL,
        fields=("danger", "source", "strength", "held", "origin"),
        tables=(RegionDangerRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("curse_region",),
        targets=("region",),
        couplings=(
            Coupling(S.ECOLOGY, "fierce wild kinds and named beasts make the land dangerous", EdgeKind.MODIFIER, "regional_danger.beasts_species_pct"),
            Coupling(S.POLITY, "land no realm controls breeds bandits", EdgeKind.MODIFIER, "regional_danger.bandits_lawless_pct"),
            Coupling(S.MAGIC, "wild magic and leak wounds breed phenomena", EdgeKind.MODIFIER, "regional_danger.phenomena_magic_pct"),
            Coupling(S.DEMOGRAPHY, "disease load becomes a danger", EdgeKind.MODIFIER, "regional_danger.disease_load_pct"),
            Coupling(S.CULTURE, "hospitality laws drive the bandits away", EdgeKind.MODIFIER, "traditions.hospitality_danger"),
        ),
    ),
    Mechanic(
        key="danger_harm",
        spec_item="S6.1",
        title="Each danger source takes settlers and livestock by its own weight; beasts and monsters leave the maimed",
        subsystem=S.ENVIRONMENT,
        phases=("danger_harm",),
        surface=Surface(drawer=DANGERS, layer=DANGER_LAYER),
        backfill="none: danger harms settlers from the next epoch",
        templates=("danger.",),
        fields=("population", "head"),
        tables=(RegionDangerRow.__tablename__,),
        flows=("people.population", "settlement.population"),
        targets=LANDS,
        couplings=(
            Coupling(S.DEMOGRAPHY, "dangers kill settlers", EdgeKind.FLOW, "regional_danger.settlers_loss_pct"),
            Coupling(S.ECONOMY, "dangers take livestock", EdgeKind.FLOW, "regional_danger.livestock_loss_pct"),
            Coupling(S.BODY, "beasts and monsters leave the maimed", EdgeKind.FLOW, "regional_danger.settlers_maimed_pct"),
        ),
    ),
    Mechanic(
        key="danger_on_the_road",
        spec_item="S6.1",
        title="Travellers, armies and merchants pay the land's dangers: journey risk, attrition and ambush, thinner trade",
        subsystem=S.ENVIRONMENT,
        phases=("travel", "campaigns", "trade_flow"),
        surface=Surface(drawer=DANGERS, layer=DANGER_LAYER),
        backfill="none: computed from the dangers each epoch",
        fields=("danger", "size", "morale", "capacity"),
        tables=(RegionDangerRow.__tablename__,),
        targets=("region", "army", "trade_route", "mortal"),
        couplings=(
            Coupling(S.DEMOGRAPHY, "travellers set out into dangerous land", EdgeKind.MODIFIER, "regional_danger.traveller_risk_pct"),
            Coupling(S.WAR, "armies lose men to the land and its ambushes", EdgeKind.FLOW, "regional_danger.army_attrition_pct"),
            Coupling(S.ECONOMY, "merchants avoid dangerous roads", EdgeKind.MODIFIER, "regional_danger.merchant_route_pct"),
        ),
    ),
    Mechanic(
        key="terrain_hazards",
        spec_item="S6.1",
        title="Avalanches in the coldest season, spring floods, summer wildfire and whiteouts strike in sampled years with crush, burn and frostbite",
        subsystem=S.ENVIRONMENT,
        phases=("terrain_hazards",),
        surface=Surface(drawer=HAZARDS),
        backfill="none: hazards strike from the next epoch",
        templates=("hazard.",),
        fields=("population", "size", "scars"),
        tables=(RegionHazardRow.__tablename__,),
        flows=("people.population", "settlement.population"),
        targets=("region", "settlement", "people", "army", "mortal"),
        couplings=(
            Coupling(S.BODY, "hazards crush, burn and freeze the named", EdgeKind.FLOW, "hazards.injury_damage"),
            Coupling(S.DEMOGRAPHY, "hazards kill settlers", EdgeKind.FLOW, "hazards.avalanche_deaths_permille"),
            Coupling(S.WAR, "hazards strike armies in the field", EdgeKind.FLOW, "hazards.avalanche_army_pct"),
        ),
    ),
    Mechanic(
        key="region_sanctity",
        spec_item="S6.1",
        title="Holy ground from temples, pilgrimage sites, nexuses, saints' graves and fallen gods draws pilgrims and wards off hauntings",
        subsystem=S.FAITH,
        phases=("region_survey", "sacred_pilgrims", "hauntings"),
        surface=Surface(drawer=SANCTITY, layer=SACRED_LAYER),
        backfill=BACKFILL,
        fields=("sacredness", "prosperity", "piety", "zeal"),
        tables=(RegionEnvironmentRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("sanctify_region",),
        targets=LANDS,
        couplings=(
            Coupling(S.ECONOMY, "pilgrims bring wealth to holy towns", EdgeKind.FLOW, "terrain.pilgrim_prosperity"),
            Coupling(S.FAITH, "holy ground deepens piety and zeal", EdgeKind.MODIFIER, "terrain.pilgrim_piety"),
            Coupling(S.MAGIC, "holy ground wards off phenomena", EdgeKind.MODIFIER, "regional_danger.phenomena_sacred_pct"),
        ),
    ),
    Mechanic(
        key="region_memory",
        spec_item="S6.1",
        title="The land remembers battles, massacres, sacks, disasters, plagues, famines, saints, miracles and fallen gods by magnitude",
        subsystem=S.CULTURE,
        phases=("region_survey", "hauntings"),
        surface=Surface(drawer=SANCTITY),
        backfill=BACKFILL,
        fields=("kind", "magnitude", "held"),
        tables=(RegionMemoryRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("region",),
        couplings=(
            Coupling(S.FAITH, "dark memories raise hauntings", EdgeKind.MODIFIER, "terrain.haunt_darkness_pct"),
            Coupling(S.MAGIC, "dark memories breed phenomena", EdgeKind.MODIFIER, "regional_danger.phenomena_darkness_pct"),
            Coupling(S.FAITH, "holy memories make holy ground", EdgeKind.MODIFIER, "terrain.sacred_memory_pct"),
        ),
    ),
    Mechanic(
        key="map_knowledge",
        spec_item="S6.1",
        title="Each realm knows the lands it holds, borders, discovered or holds maps of; explorers push the edge; unmapped land loses armies",
        subsystem=S.KNOWLEDGE,
        phases=("region_survey", "campaigns"),
        surface=Surface(drawer=KNOWLEDGE),
        backfill=BACKFILL,
        fields=("level", "held"),
        tables=(PolityMapKnowledgeRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("polity", "region", "army"),
        couplings=(
            Coupling(S.WAR, "armies lose their way in unmapped land", EdgeKind.FLOW, "terrain.lost_chance_pct"),
            Coupling(S.POLITY, "a realm's land and maps chart the world", EdgeKind.MODIFIER, "terrain.knowledge_owned"),
        ),
    ),
    Mechanic(
        key="river_course",
        spec_item="S6.1",
        title="A god or the player turns a river into a neighbouring region: the old valley dries, the new one waters its places",
        subsystem=S.ENVIRONMENT,
        phases=("environment_derive",),
        surface=Surface(drawer=RIVER),
        backfill="none: rivers keep their courses until turned",
        fields=("river_class", "water_source"),
        tables=(RegionEnvironmentRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("redirect_river",),
        targets=("region", "place"),
        couplings=(
            Coupling(S.ECONOMY, "a river waters the harvest and carries boats", EdgeKind.MODIFIER, "terrain.redirect_leaves_stream"),
            Coupling(S.DEMOGRAPHY, "places lose or gain their water", EdgeKind.MODIFIER),
        ),
    ),
    Mechanic(
        key="environment_layers",
        spec_item="S6.1",
        title="Rainfall, danger, scar and sacred layers on the map, kept with every epoch's snapshot so the past shows the land as it was",
        subsystem=S.ENVIRONMENT,
        phases=("region_survey",),
        surface=Surface(layer=RAIN_LAYER, chart=SCAR_LAYER),
        backfill="none: snapshots taken before this keep today's land",
        fields=("rainfall", "danger", "scars", "sacredness"),
        targets=("region",),
    ),
)
