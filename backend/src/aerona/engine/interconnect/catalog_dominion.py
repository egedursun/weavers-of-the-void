from aerona.db.tables.dominion import (
    CreatureLessonRow,
    DivineCreatureRow,
    DominionRow,
    GodDesignRow,
    GodImageRow,
    GodScaleRow,
    MagicSiteRow,
    MiracleRecordRow,
    RegionDominionRow,
    ThroneRow,
)
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
MIGRATION = "migration ea5f12047d6b"
DOMINION_SECTION = "section-dominion"

DOMINION_MECHANICS = (
    Mechanic(
        key="dominion",
        spec_item="F31",
        title=(
            "Dominion and scales: each god's presence over every region, spreading from temples, "
            "holy sites, thrones, prophets, miracles and worship, contested, and leaning the land"
        ),
        subsystem=S.GODS,
        phases=("dominion",),
        surface=Surface(drawer=DOMINION_SECTION, layer="map-layer-dominion"),
        backfill=f"{MIGRATION}: dominion is weighed from the standing temples, holy sites and worship on the first epoch after the upgrade",
        templates=("dominion.",),
        fields=("danger", "fertility", "magic_density", "prosperity", "growth"),
        tables=(DominionRow.__tablename__, RegionDominionRow.__tablename__, GodScaleRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("son", "foreign_god", "creator", "region", "world"),
        couplings=(
            Coupling(
                S.ENVIRONMENT,
                "the ruling god's scales move danger, fertility, heat and magic density in its regions",
                EdgeKind.MODIFIER,
                "dominion.danger_per_step",
            ),
            Coupling(
                S.ECONOMY, "order and productivity raise the prosperity and harvests of a dominated region", EdgeKind.MODIFIER, "dominion.prosperity_per_step"
            ),
            Coupling(S.DEMOGRAPHY, "growth and death move the population growth of a dominated region", EdgeKind.MODIFIER, "dominion.growth_per_step_pct"),
            Coupling(
                S.ENVIRONMENT, "fortune and misfortune move the odds of disasters in a dominated region", EdgeKind.MODIFIER, "dominion.fortune_per_step_pct"
            ),
            Coupling(S.CORE, "turmoil in a dominated region raises the tension of its world", EdgeKind.MODIFIER, "dominion.tension_per_step"),
            Coupling(S.FAITH, "missionaries convert more easily where their god rules the land", EdgeKind.MODIFIER, "dominion.conversion_pct"),
            Coupling(S.MAGIC, "miracles and rites cost less in one's own dominion and more in another god's", EdgeKind.MODIFIER, "dominion.cheap_pct"),
            Coupling(S.MIND, "worshippers feel their god near and priests of other gods feel out of place", EdgeKind.MODIFIER, "dominion.near_stress"),
            Coupling(S.GODS, "a son draws existence from the regions its dominion rules", EdgeKind.FLOW, "dominion.existence_per_region"),
            Coupling(S.GODS, "a god's own deeds move its scales toward them", EdgeKind.TRIGGER, "dominion.deed_shift_count"),
        ),
    ),
    Mechanic(
        key="thrones_and_sites",
        spec_item="S6.2/RP3",
        title=(
            "Thrones of power and magic sites: thrones held by the god whose dominion rules "
            "their land, and hidden sources, school seats, wards and gateways found by searching mages"
        ),
        subsystem=S.MAGIC,
        phases=("thrones", "magic_sites"),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: thrones and hidden magic sites are laid on every world on the first epoch after the upgrade",
        templates=("dominion.throne_passed", "dominion.magic_site_found"),
        fields=("sacredness", "reagents"),
        tables=(ThroneRow.__tablename__, MagicSiteRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("search_magic_sites",),
        targets=("place", "region", "settlement", "structure", "world"),
        couplings=(
            Coupling(S.GODS, "a held throne gives its god essence and awe and spreads its dominion", EdgeKind.FLOW, "thrones.essence"),
            Coupling(S.GODS, "holding most thrones of a world counts toward a god's ascension", EdgeKind.TRIGGER, "thrones.ascension_share"),
            Coupling(S.MAGIC, "a found source yields reagents to its holder each epoch", EdgeKind.FLOW, "magic_sites.output_pct"),
            Coupling(S.MAGIC, "a rite cast at a site of its school is stronger", EdgeKind.MODIFIER, "magic_sites.school_pct"),
            Coupling(S.COSMOS, "a found gateway opens a route to another world", EdgeKind.TRIGGER, "magic_sites.search_pct"),
            Coupling(S.POLITY, "realms covet the magic sites of their neighbours", EdgeKind.TRIGGER, "magic_sites.war_aim_pct"),
        ),
    ),
    Mechanic(
        key="worship_views",
        spec_item="S9.1/RP3",
        title=(
            "Perceived alignment and worship mode: each people sees its god as benevolent, ambivalent or malevolent and worships it in devotion or appeasement"
        ),
        subsystem=S.FAITH,
        phases=("worship_views",),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: every standing is read for its alignment and mode on the first epoch after the upgrade",
        fields=("splendor", "piety"),
        exposure=Exposure.CONTEXT,
        targets=("son", "foreign_god", "creator", "people", "settlement"),
        couplings=(
            Coupling(S.FAITH, "a feared god gains more faith from offerings meant to keep it away", EdgeKind.FLOW, "worship_views.appeasement_offering_pct"),
            Coupling(S.CULTURE, "temples of a loved god grow splendid and those of a feared god grow grim", EdgeKind.MODIFIER, "worship_views.temple_shift"),
            Coupling(
                S.COMMUNICATION,
                "prayers to a feared god plead for mercy and prayers to a loved god give thanks",
                EdgeKind.RULE_SWITCH,
                "worship_views.appease_fear",
            ),
        ),
    ),
    Mechanic(
        key="miracle_impression",
        spec_item="S9.1/RP3",
        title=(
            "Miracle impressiveness: belief from a miracle grows with its witnesses, magnitude, need, novelty "
            "and legibility, and may be credited to the god who rules the land"
        ),
        subsystem=S.GODS,
        phases=("dominion",),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: miracles are recorded from the upgrade on; nothing past is invented",
        tables=(MiracleRecordRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("miracle",),
        targets=("son", "creator", "mortal", "settlement", "region"),
        couplings=(
            Coupling(S.FAITH, "belief from a miracle becomes faith for the god it is credited to", EdgeKind.FLOW, "miracle_impression.faith_per_belief_pct"),
            Coupling(S.FAITH, "witnesses of a miracle stand in awe of its god", EdgeKind.MODIFIER, "miracle_impression.awe_per_belief_pct"),
            Coupling(S.GODS, "a miracle in another god's land may be credited to that god", EdgeKind.TRIGGER, "miracle_impression.misread_pct"),
        ),
    ),
    Mechanic(
        key="god_images",
        spec_item="S9.1/RP3",
        title="Belief shapes gods: the image its peoples hold pulls a god's temperament and aspects toward it, unless the god resists or embraces it",
        subsystem=S.GODS,
        phases=("god_images",),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: every god's image is read from its standings on the first epoch after the upgrade",
        templates=("dominion.image_turned",),
        fields=("wrath", "mercy", "stance", "domain_secondary"),
        tables=(GodImageRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("shape_image",),
        targets=("son", "foreign_god"),
        couplings=(
            Coupling(S.GODS, "a god's wrath and mercy drift toward what its peoples believe", EdgeKind.MODIFIER, "god_images.base_pull"),
            Coupling(S.GODS, "a believed domain the god lacks becomes its second domain", EdgeKind.TRIGGER, "god_images.domain_pressure_at"),
            Coupling(S.GODS, "resisting the image costs essence and embracing it wins fame", EdgeKind.FLOW, "god_images.resist_cost"),
        ),
    ),
    Mechanic(
        key="divine_creatures",
        spec_item="S9.1/RP3",
        title="Divine creatures: a god's creature chooses its deeds by the leanings its god's rewards and punishments taught it",
        subsystem=S.GODS,
        phases=("divine_creatures",),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: divine creatures exist only once a god raises one",
        tables=(DivineCreatureRow.__tablename__, CreatureLessonRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("raise_divine_creature", "teach_creature"),
        targets=("son", "foreign_god", "creator", "creature"),
        couplings=(
            Coupling(
                S.ECONOMY, "a creature tending fields raises the harvest and one hunting folk feeds on them", EdgeKind.FLOW, "divine_creatures.hunger_gain"
            ),
            Coupling(S.BODY, "a creature heals the sick or strikes its god's foes", EdgeKind.TRIGGER, "divine_creatures.heal"),
            Coupling(
                S.FAITH, "a creature guarding holy sites raises their sacredness and the awe of its god", EdgeKind.MODIFIER, "divine_creatures.love_per_deed"
            ),
        ),
    ),
    Mechanic(
        key="god_design",
        spec_item="S9.1/RP3",
        title=(
            "God design trade-offs: dominion strength, magic aptitude, manifestation and scales are "
            "bought from one budget, and what is left keeps the god's powers"
        ),
        subsystem=S.GODS,
        phases=("dominion",),
        surface=Surface(drawer=DOMINION_SECTION),
        backfill=f"{MIGRATION}: every god's design is weighed from its stats and domains on the first epoch after the upgrade",
        tables=(GodDesignRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("son", "foreign_god", "creator"),
        couplings=(
            Coupling(S.GODS, "a design that spends its budget lowers the god's stats", EdgeKind.MODIFIER, "god_design.stats_floor_pct"),
            Coupling(S.GODS, "dominion strength adds to every region where the god has a source", EdgeKind.MODIFIER, "dominion.strength_weight_pct"),
            Coupling(S.GODS, "each divine rank won by ascension raises essence income", EdgeKind.FLOW, "thrones.rank_essence_pct"),
        ),
    ),
)
