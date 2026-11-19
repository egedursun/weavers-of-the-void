from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionPlaceRow, CollectionRow, GatheringGuestRow, GatheringRow
from aerona.db.tables.sites import BattlefieldFeatureRow, ExcavationRow, ExcavationStageRow, RoomContentRow, SiteHolderRow, SiteRoomRow
from aerona.db.tables.storyteller import StorytellerRow, TensionRecordRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
MIGRATION = "migration 959c964d1a42"
GATHERINGS_SECTION = "section-gatherings"
HISTORIES_SECTION = "section-histories"
STORYTELLER_SECTION = "section-storyteller"
SITE_SECTION = "section-site"

GATHERING_MECHANICS = (
    Mechanic(
        key="gatherings",
        spec_item="F25",
        title=(
            "Gatherings: feasts, weddings, funerals, coronations, tournaments, hunts, councils, summits, festivals, fairs, games, "
            "performances, trials, executions, pilgrimages, processions, milestones and wakes"
        ),
        subsystem=S.SOCIAL,
        phases=("gatherings",),
        surface=Surface(drawer=GATHERINGS_SECTION),
        backfill=f"{MIGRATION}: gatherings begin with the first epoch after the upgrade; nothing past is invented",
        templates=("gathering.", "kin.betrothal", "tools.son.convene_gathering"),
        fields=("strength", "zeal"),
        tables=(GatheringRow.__tablename__, GatheringGuestRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("hold_gathering", "convene_gathering"),
        targets=("mortal", "people", "settlement", "cult", "polity", "place"),
        couplings=(
            Coupling(S.SOCIAL, "attendees grow friendlier and more familiar, fall in love and are betrothed", EdgeKind.MODIFIER, "gatherings.romance_pct"),
            Coupling(S.INTRIGUE, "secrets are learned and schemes advance where owners and agents meet", EdgeKind.TRIGGER, "gatherings.secret_pct"),
            Coupling(S.INTRIGUE, "a murder scheme strikes harder at a target who attends", EdgeKind.MODIFIER, "gatherings.strike_boost_pct"),
            Coupling(S.BODY, "bouts of a tournament and beasts of a hunt wound those who take part", EdgeKind.TRIGGER, "gatherings.bout_hp"),
            Coupling(S.ECONOMY, "a feast spends the host's coin for each guest", EdgeKind.FLOW, "gatherings.feast_cost"),
            Coupling(
                S.ECONOMY,
                "a feast serves food from its host's stores, and its prestige follows how well it fed its guests",
                EdgeKind.FLOW,
                "gatherings.feast_food",
            ),
            Coupling(
                S.LAW,
                "a host whose land keeps the law of hospitality, or whose culture holds killing a guest unthinkable, never turns on its guests",
                EdgeKind.RULE_SWITCH,
                "gatherings.massacre_shameful_pct",
            ),
            Coupling(S.MIND, "a milestone leaves a lasting memory of its host with those who came", EdgeKind.MODIFIER, "gatherings.milestone_memory"),
            Coupling(S.POLITY, "a summit signs peaces among realms on good terms", EdgeKind.TRIGGER, "gatherings.summit_treaty_friendship"),
            Coupling(S.CULTURE, "a festival held as a gathering binds its community", EdgeKind.MODIFIER, "gatherings.festival_cohesion"),
            Coupling(S.FAITH, "pilgrimages hallow their place and processions kindle a cult's zeal", EdgeKind.MODIFIER, "gatherings.pilgrim_sacredness"),
            Coupling(S.MIND, "each gathering leaves a thought with those who came", EdgeKind.MODIFIER, "gatherings.thought_intensity"),
        ),
    ),
    Mechanic(
        key="event_collections",
        spec_item="F10/RP2",
        title="Histories: incidents gathered into wars, battles, sieges, duels, plagues, gatherings and every other kind, nested and closed",
        subsystem=S.CORE,
        phases=("event_collections",),
        surface=Surface(drawer=HISTORIES_SECTION),
        backfill=f"{MIGRATION}: histories gather the incidents of each epoch from the upgrade on",
        tables=(CollectionRow.__tablename__, CollectionMemberRow.__tablename__, CollectionIncidentRow.__tablename__, CollectionPlaceRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("mortal", "people", "settlement", "polity", "place", "region"),
        couplings=(
            Coupling(
                S.CORE, "the chronicler tells the incidents of an age as parts of the histories they belong to", EdgeKind.FLOW, "collections.join_window_years"
            ),
            Coupling(S.LAW, "many executions in one realm in one epoch make a purge", EdgeKind.TRIGGER, "collections.purge_at"),
        ),
    ),
    Mechanic(
        key="storyteller",
        spec_item="F27",
        title="Storyteller: the tension of each world against its aim, the pace of spontaneous disruptions, recoveries, variety and the spotlight",
        subsystem=S.CORE,
        phases=("storyteller",),
        surface=Surface(drawer=STORYTELLER_SECTION),
        backfill=f"{MIGRATION}: every world gets a cyclic storyteller on its first epoch after the upgrade",
        templates=("storyteller.recovery",),
        tables=(StorytellerRow.__tablename__, TensionRecordRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("world",),
        couplings=(
            Coupling(S.ECOLOGY, "beasts appear more or less often", EdgeKind.MODIFIER, "storyteller.boost_max_pct"),
            Coupling(
                S.WAR, "feuds turn to raids more or less often, and peace comes sooner after hard years", EdgeKind.MODIFIER, "storyteller.boost_per_point_pct"
            ),
            Coupling(S.DEMOGRAPHY, "plagues strike more or less often; healers are born more often after hard years", EdgeKind.MODIFIER, "storyteller.band"),
            Coupling(S.POLITY, "ambitious regents seize thrones more or less often", EdgeKind.MODIFIER, "storyteller.variety_pct"),
            Coupling(S.ECONOMY, "a heated world's hardest pressed community is given a full harvest", EdgeKind.TRIGGER, "storyteller.harvest_gift"),
            Coupling(S.SOCIAL, "the spotlit record is chosen more often by agents and the chronicler", EdgeKind.MODIFIER, "storyteller.spotlight_weight_pct"),
            Coupling(S.CULTURE, "a quiet world is revived only when the storyteller finds it quiet", EdgeKind.RULE_SWITCH, "storyteller.revival_band"),
        ),
    ),
    Mechanic(
        key="site_rooms",
        spec_item="S6.2/RP2",
        title="Sites with rooms: towers, vaults, lairs, hamlets, monasteries, fortresses, caverns and ruins walked room by room, and who holds them",
        subsystem=S.ENVIRONMENT,
        phases=("site_rooms", "heroes"),
        surface=Surface(drawer=SITE_SECTION),
        backfill=f"{MIGRATION}: every site of a roomed kind is furnished once on its first epoch after the upgrade",
        templates=("site.delved",),
        fields=("strength", "cunning"),
        tables=(SiteRoomRow.__tablename__, RoomContentRow.__tablename__, SiteHolderRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("delve_site",),
        targets=("place", "structure", "settlement"),
        couplings=(
            Coupling(S.BODY, "a room not passed wounds the one who walks it", EdgeKind.TRIGGER, "sites.delve_hp"),
            Coupling(S.ECONOMY, "things won in a room pass to the one who cleared it", EdgeKind.FLOW, "sites.room_item_pct"),
            Coupling(S.FAITH, "spirits of a cleared room are laid to rest", EdgeKind.TRIGGER, "sites.spirit_rest_pct"),
            Coupling(S.WAR, "a feud raid walks the rooms of the town it strikes, led by its avenger's ruler", EdgeKind.TRIGGER, "sites.raid_company"),
        ),
    ),
    Mechanic(
        key="excavations",
        spec_item="S6.2/RP2",
        title="Digs at ruins, places where gods died, craters, burial grounds, earlier creations and wrecks, stage by stage, with their risks and finds",
        subsystem=S.KNOWLEDGE,
        phases=("excavations",),
        surface=Surface(drawer=SITE_SECTION),
        backfill=f"{MIGRATION}: digs begin from the first epoch after the upgrade",
        templates=("excavation.",),
        tables=(ExcavationRow.__tablename__, ExcavationStageRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("dig_site",),
        targets=("place",),
        couplings=(
            Coupling(S.KNOWLEDGE, "a find teaches a lost technique to the sponsor", EdgeKind.FLOW, "excavations.find_power"),
            Coupling(S.BODY, "a collapse buries the leader of the dig", EdgeKind.TRIGGER, "excavations.collapse_hp"),
            Coupling(S.FAITH, "a dig may loose a spirit or a curse", EdgeKind.TRIGGER, "excavations.risk_pct"),
        ),
    ),
    Mechanic(
        key="battlefields",
        spec_item="S6.2/RP2",
        title="Battlefield features: mass graves that stir up spirits, fields of salvage gleaned for arms and old earthworks that keep their land fortified",
        subsystem=S.WAR,
        phases=("battlefields",),
        surface=Surface(drawer=SITE_SECTION),
        backfill=f"{MIGRATION}: features are laid by the battles of the epochs after the upgrade",
        templates=("battlefield.haunted",),
        tables=(BattlefieldFeatureRow.__tablename__,),
        exposure=Exposure.NONE,
        targets=("place",),
        couplings=(
            Coupling(S.FAITH, "a mass grave stirs up spirits", EdgeKind.TRIGGER, "excavations.grave_haunt_pct"),
            Coupling(S.ECONOMY, "the nearest community gleans arms from a field of salvage", EdgeKind.FLOW, "excavations.salvage_take_pct"),
            Coupling(S.WAR, "old earthworks from a siege keep the earthworks of their land from wearing away", EdgeKind.MODIFIER, "excavations.feature_decay"),
        ),
    ),
)
