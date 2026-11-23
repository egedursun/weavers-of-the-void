from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.prehistory import PrehistoryEventRow
from aerona.db.tables.transform import StarModifierRow, TransformationRow, TransformProspectRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
LIFE = "section-lifecycle"
WORLD_END = "section-world-end"
FOSSILS = "section-fossils"
PREHISTORY = "section-prehistory"
TRANSFORMS = "section-transformations"
GROUNDS = "section-grounds"

LIFECYCLE_MECHANICS = (
    Mechanic(
        key="lifecycle_ends",
        spec_item="F47",
        title=(
            "Lifecycle ends: ideologies and rites fall dormant or are lost, theories are forgotten and found again, diseases die out and "
            "come back from sealed remains, and outer beings are banished and return through the leak"
        ),
        subsystem=S.KNOWLEDGE,
        phases=("lifecycle_ends",),
        surface=Surface(drawer=LIFE, chart="chart-lifecycle"),
        backfill="migration 8ad812bbd71a: every ideology, theory, rite, disease and outer being takes its state at the next start or epoch",
        tables=(LifecycleStateRow.__tablename__,),
        tools=("wake_lore",),
        targets=("ideology", "theory", "rite", "disease", "outer_being"),
        couplings=(
            Coupling(S.CULTURE, "a dormant ideology is taken up again from its texts", E.TRIGGER, "lifecycle_ends.revival_pct"),
            Coupling(S.CULTURE, "the first hold of a revived ideology", E.MODIFIER, "lifecycle_ends.revival_strength"),
            Coupling(S.KNOWLEDGE, "a forgotten theory is found again", E.TRIGGER, "lifecycle_ends.rediscover_pct"),
            Coupling(S.MAGIC, "a caster still knows a rite this long after casting it", E.RULE_SWITCH, "lifecycle_ends.practice_years"),
            Coupling(S.MAGIC, "a faded text corrupts the rite rebuilt from it", E.MODIFIER, "lifecycle_ends.corruption_pct"),
            Coupling(S.MAGIC, "a corrupted rite backfires more often", E.MODIFIER, "lifecycle_ends.corrupted_backlash"),
            Coupling(S.DEMOGRAPHY, "a disease without hosts this long is eradicated", E.RULE_SWITCH, "lifecycle_ends.eradication_years"),
            Coupling(S.GODS, "an outer being below this interest with no breach or cult is banished", E.RULE_SWITCH, "lifecycle_ends.banish_interest"),
            Coupling(S.COSMOS, "the leak of its world brings a banished being back", E.TRIGGER, "lifecycle_ends.return_pct"),
            Coupling(S.GODS, "destroying an outer being costs the Creator essence", E.FLOW, "lifecycle_ends.destroy_cost"),
            Coupling(S.GODS, "waking lore costs a son essence", E.FLOW, "lifecycle_ends.son_cost"),
        ),
    ),
    Mechanic(
        key="decays",
        spec_item="F47",
        title=(
            "Decays: favours and stale secrets fade, reputations fade unless told, prestige and tyranny ease, "
            "war weariness heals in peace and warping fades away from magic"
        ),
        subsystem=S.SOCIAL,
        phases=("intrigue", "renown_hearsay", "ruler_currencies", "polity_cycles", "warping"),
        surface=Surface(drawer=LIFE, chart="chart-lifecycle"),
        backfill="none: decays begin from the next epoch",
        couplings=(
            Coupling(S.INTRIGUE, "a favour owed fades each epoch", E.FLOW, "intrigue.favour_decay_pct"),
            Coupling(S.MIND, "favours fade faster where friendship is little worth", E.MODIFIER, "intrigue.weak_reciprocity_pct"),
            Coupling(S.HOUSEHOLD, "kin take on the favours of a dead debtor where family is valued", E.RULE_SWITCH, "intrigue.inherited_from"),
            Coupling(S.INTRIGUE, "a stale secret loses its severity", E.FLOW, "intrigue.obsolete_pct"),
            Coupling(S.CULTURE, "an account of its subject holds back the fading of a reputation", E.MODIFIER, "local_renown.account_slow_pct"),
            Coupling(S.POLITY, "prestige fades without new renown", E.FLOW, "currencies.prestige_fade"),
            Coupling(S.LAW, "mercy and restitution ease tyranny", E.MODIFIER, "currencies.amends_pct"),
            Coupling(S.WAR, "a realm at peace sheds its weariness", E.FLOW, "war_weariness.recovery_pct"),
            Coupling(S.BODY, "many maimed veterans slow that healing", E.MODIFIER, "war_weariness.maimed_slow_pct"),
            Coupling(S.BODY, "the maimed count at which the slowing is full", E.MODIFIER, "war_weariness.maimed_full"),
            Coupling(S.CULTURE, "accounts of its wars slow that healing", E.MODIFIER, "war_weariness.memory_slow_pct"),
            Coupling(S.MAGIC, "warping fades away from magic", E.FLOW, "warping.fade"),
            Coupling(S.MAGIC, "warping never fades below a lasting stage", E.RULE_SWITCH, "warping.permanent_stage"),
        ),
    ),
    Mechanic(
        key="world_ends",
        spec_item="F47",
        title=(
            "World ends: a world shattered, swallowed, frozen dead, sunk into the void, forgotten or transfigured, with what it ends for "
            "lives, roads, peoples abroad and the anchors of gods"
        ),
        subsystem=S.COSMOS,
        phases=("world_ends",),
        surface=Surface(drawer=WORLD_END, chart="chart-world-end"),
        backfill="none: worlds come to their end from the next epoch",
        tables=(WorldEndRow.__tablename__,),
        targets=("world",),
        couplings=(
            Coupling(S.COSMOS, "a world lit only by a dead star freezes dead after this long", E.TRIGGER, "world_ends.frozen_epochs"),
            Coupling(S.GODS, "ending a world costs the Creator essence", E.FLOW, "world_ends.end_cost"),
        ),
    ),
    Mechanic(
        key="dreamt_pasts",
        spec_item="F48/RP9",
        title="Prehistory: a past run before a world joins the cosmos, borrowed from its source, mirrored, or dreamt again each epoch",
        subsystem=S.COSMOS,
        phases=("dreamt_pasts",),
        surface=Surface(drawer=PREHISTORY, chart="chart-prehistory"),
        backfill=(
            "dreamt_pasts: dream worlds dream their past again from the next epoch; worlds with written lore take a past backfilled from it at the next start"
        ),
        tables=(PrehistoryEventRow.__tablename__,),
        tools=("plan_prehistory",),
        targets=("world",),
        couplings=(
            Coupling(S.CULTURE, "a digest keeps this many happenings of a past for Fate, the chronicler and the book", E.RULE_SWITCH, "prehistory.digest_size"),
            Coupling(S.GODS, "a son spends essence to give a world it made a past", E.FLOW, "prehistory.son_seed_cost"),
        ),
    ),
    Mechanic(
        key="transformations",
        spec_item="F49",
        title="Transformations: a son falls or is corrupted, a people loses its sapience, a faith or a realm forges a people, a star or a world gains a god",
        subsystem=S.COSMOS,
        phases=("transformations",),
        surface=Surface(drawer=TRANSFORMS, chart="chart-transformations"),
        backfill="transformations: past deifications, uplifts and raised spirits are entered in the record of transformations at the next start",
        tables=(TransformationRow.__tablename__, TransformProspectRow.__tablename__, StarModifierRow.__tablename__),
        tools=("press_transformation", "seek_true_name"),
        targets=(
            "son",
            "people",
            "cult",
            "polity",
            "house",
            "phenomenon",
            "world",
            "star",
            "ideology",
            "beast",
            "outer_being",
            "spirit",
            "mortal",
            "title",
            "tradition",
            "theory",
        ),
        couplings=(
            Coupling(S.GODS, "a son fading in a mortal body falls into it after this many epochs instead of dying", E.TRIGGER, "transform.fall_epochs"),
            Coupling(
                S.GODS, "a son at or below this sanity after bargaining with the outside may be corrupted", E.RULE_SWITCH, "transform.corruption_warning_sanity"
            ),
            Coupling(S.COSMOS, "a dead star god dims its star by this much", E.FLOW, "transform.star_god_dim_pct"),
            Coupling(
                S.DEMOGRAPHY, "a people losing its sapience becomes this many members per point of abundance", E.FLOW, "transform.people_to_species_density"
            ),
        ),
    ),
    Mechanic(
        key="fossils",
        spec_item="S6.2/RP7",
        title=(
            "Fossils: remains of what died out lie in beds, are found by digging and upheaval, and are read as remains of legend, "
            "sacred relics or evidence of deep time"
        ),
        subsystem=S.ENVIRONMENT,
        phases=("fossils",),
        surface=Surface(drawer=FOSSILS, chart="chart-fossils"),
        backfill="none: fossil beds are laid from what died out from the next epoch",
        tables=(FossilBedRow.__tablename__,),
        tools=("lay_bare_fossils", "study_fossils"),
        targets=("region", "settlement", "people"),
        couplings=(
            Coupling(S.ECOLOGY, "a bed of what died out is laid with this richness", E.MODIFIER, "fossils.richness"),
            Coupling(S.ECOLOGY, "a bed of megafauna, a beast or a previous creation", E.MODIFIER, "fossils.megafauna_richness"),
            Coupling(S.DEMOGRAPHY, "an old world keeps the remains of peoples that died out", E.RULE_SWITCH, "fossils.old_world_epochs"),
            Coupling(S.ENVIRONMENT, "a bed is found by chance", E.TRIGGER, "fossils.find_pct"),
            Coupling(S.ECONOMY, "mines and quarries find beds", E.TRIGGER, "fossils.mine_pct"),
            Coupling(S.ENVIRONMENT, "quakes and floods lay beds bare", E.TRIGGER, "fossils.erosion_pct"),
            Coupling(S.MIND, "a people reads a find in its way from this value", E.RULE_SWITCH, "fossils.reading_from"),
            Coupling(S.CULTURE, "a find read as remains of legend makes legends believed", E.MODIFIER, "fossils.legend_credence"),
            Coupling(S.FAITH, "a find read as sacred relics draws followers to cults", E.MODIFIER, "fossils.relic_followers_pct"),
            Coupling(S.KNOWLEDGE, "evidence of deep time strengthens theories", E.MODIFIER, "fossils.deep_time_strength"),
            Coupling(S.ECONOMY, "a found bed yields luxuries", E.FLOW, "fossils.luxury_per_10"),
            Coupling(S.GODS, "laying bare remains costs a son essence", E.FLOW, "fossils.son_cost"),
        ),
    ),
    Mechanic(
        key="collections",
        spec_item="S7.2/RP7",
        title=(
            "Collections: museums, temple treasuries, royal collections and cabinets gather prized things, works, finds and living kinds, "
            "give grandeur, help research and draw travellers, and are looted and given back"
        ),
        subsystem=S.CULTURE,
        phases=("collections", "ruler_currencies", "research_cycles", "tourism", "campaigns"),
        surface=Surface(drawer=GROUNDS, chart="chart-grounds"),
        backfill="none: collections are founded and gathered from the next epoch",
        tables=(MuseumCollectionRow.__tablename__, MuseumPieceRow.__tablename__),
        tools=("found_museum",),
        targets=("settlement", "polity", "people"),
        couplings=(
            Coupling(S.POLITY, "a ruler owning this many prized things keeps a royal collection", E.RULE_SWITCH, "museums.royal_from"),
            Coupling(S.ECOLOGY, "living kinds taken in as specimens each year", E.FLOW, "museums.specimens_per_epoch"),
            Coupling(S.POLITY, "each piece adds grandeur", E.MODIFIER, "museums.prestige_per_piece"),
            Coupling(S.KNOWLEDGE, "pieces help the research of their field", E.MODIFIER, "museums.research_pct"),
            Coupling(S.KNOWLEDGE, "most pieces that help one field", E.MODIFIER, "museums.research_cap"),
            Coupling(S.WAR, "a sacked town loses its pieces", E.FLOW, "museums.loot_pct"),
            Coupling(S.GODS, "founding a museum costs a son essence", E.FLOW, "museums.son_cost"),
        ),
    ),
    Mechanic(
        key="gardens",
        spec_item="S7.2/RP7",
        title=(
            "Designed landscapes: gardens, parks, groves and cemeteries feed beauty and nature, help healers, give grandeur, shelter the kinds "
            "planted in them and please gods of growing and wild things"
        ),
        subsystem=S.ECOLOGY,
        phases=("gardens", "mind_survey", "body_healing", "ecology", "ruler_currencies", "tourism"),
        surface=Surface(drawer=GROUNDS, chart="chart-grounds"),
        backfill="none: gardens are laid out from the next epoch",
        tables=(GardenRow.__tablename__,),
        tools=(
            "lay_out_garden",
            "found_garden",
        ),
        targets=("settlement",),
        couplings=(
            Coupling(S.ECONOMY, "a garden costs its town upkeep", E.FLOW, "gardens.upkeep"),
            Coupling(S.ECOLOGY, "a new garden starts in this condition", E.MODIFIER, "gardens.condition"),
            Coupling(S.ECONOMY, "a tended garden grows finer", E.FLOW, "gardens.tended"),
            Coupling(S.ECONOMY, "a neglected garden falls into ruin", E.FLOW, "gardens.neglect"),
            Coupling(S.ECONOMY, "a prosperous town lays out a pleasure garden", E.RULE_SWITCH, "gardens.pleasure_from"),
            Coupling(S.ECOLOGY, "kinds of its land a garden takes in", E.MODIFIER, "gardens.planted"),
            Coupling(S.MIND, "gardens feed the need for beauty", E.MODIFIER, "gardens.beauty_per_garden"),
            Coupling(S.MIND, "gardens feed the need for nature", E.MODIFIER, "gardens.nature_per_garden"),
            Coupling(S.BODY, "a physic garden spares wounded lives", E.MODIFIER, "gardens.physic_heal_pct"),
            Coupling(S.ECOLOGY, "a planted kind does not fall below this", E.RULE_SWITCH, "gardens.refuge_floor"),
            Coupling(S.GODS, "a sacred grove pleases gods of growing and wild things", E.FLOW, "gardens.grove_standing"),
            Coupling(S.POLITY, "a garden gives its realm grandeur", E.MODIFIER, "gardens.prestige_pct"),
            Coupling(S.GODS, "laying out a garden costs a son essence", E.FLOW, "gardens.son_cost"),
        ),
    ),
)
