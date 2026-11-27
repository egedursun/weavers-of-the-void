from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.gathering import CollectionKind, CollectionRole, GatheringKind, GuestRole
from aerona.domain.enums.mind import SkillKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.site import ExcavationStage, SiteRoomKind
from aerona.domain.enums.structure import StructureKind

G = GatheringKind
C = CollectionKind
R = SiteRoomKind

GATHERING_COLLECTIONS = total(
    GatheringKind,
    {
        G.FEAST: C.FEAST,
        G.WEDDING: C.WEDDING,
        G.FUNERAL: C.FUNERAL,
        G.CORONATION: C.CORONATION,
        G.TOURNAMENT: C.TOURNAMENT,
        G.HUNT: C.HUNT,
        G.PILGRIMAGE: C.PILGRIMAGE,
        G.COUNCIL: C.COUNCIL,
        G.SUMMIT: C.SUMMIT,
        G.FESTIVAL: C.CEREMONY,
        G.FAIR: C.COMPETITION,
        G.GAMES: C.COMPETITION,
        G.PERFORMANCE: C.PERFORMANCE,
        G.TRIAL: C.TRIAL,
        G.EXECUTION: C.TRIAL,
        G.PROCESSION: C.PROCESSION,
        G.MILESTONE: C.CEREMONY,
        G.WAKE: C.FUNERAL,
        G.EXAMINATION: C.COMPETITION,
        G.BROADCAST: C.PERFORMANCE,
        G.CONVENTION: C.SUMMIT,
        G.ELECTION: C.COUNCIL,
        G.LAUNCH: C.CEREMONY,
        G.RALLY: C.PROCESSION,
        G.STRIKE: C.COUNCIL,
        G.TESTING: C.COMPETITION,
        G.EXHIBITION: C.PERFORMANCE,
        G.TRADE_FAIR: C.COMPETITION,
        G.SUMMIT_OF_GODS: C.COUNCIL,
        G.NETWORK_GATHERING: C.SUMMIT,
        G.REALM_GATHERING: C.CEREMONY,
        G.MOURNING: C.FUNERAL,
        G.INITIATION: C.CEREMONY,
        G.SPORT_MATCH: C.COMPETITION,
        G.COMMEMORATION: C.CEREMONY,
        G.MUSTER: C.WAR,
        G.REUNION: C.FEAST,
        G.GIFT_EXCHANGE: C.FEAST,
    },
)

GATHERING_THOUGHTS = total(
    GatheringKind,
    {
        G.FEAST: ThoughtKind.ATTENDED_FEAST,
        G.WEDDING: ThoughtKind.AMONG_FRIENDS,
        G.FUNERAL: ThoughtKind.MOURNED,
        G.CORONATION: ThoughtKind.BELONGED,
        G.TOURNAMENT: ThoughtKind.HAD_ADVENTURE,
        G.HUNT: ThoughtKind.WALKED_IN_NATURE,
        G.PILGRIMAGE: ThoughtKind.PRAYED_IN_PEACE,
        G.COUNCIL: ThoughtKind.RESPECTED,
        G.SUMMIT: ThoughtKind.FELT_PURPOSE,
        G.FESTIVAL: ThoughtKind.BELONGED,
        G.FAIR: ThoughtKind.PROSPERED,
        G.GAMES: ThoughtKind.ENJOYED_LEISURE,
        G.PERFORMANCE: ThoughtKind.HEARD_GREAT_MUSIC,
        G.TRIAL: ThoughtKind.LIVED_IN_ORDER,
        G.EXECUTION: ThoughtKind.WITNESSED_ATROCITY,
        G.PROCESSION: ThoughtKind.FOUND_FAITH,
        G.MILESTONE: ThoughtKind.AMONG_KIN,
        G.WAKE: ThoughtKind.MADE_PEACE_WITH_LOSS,
        G.EXAMINATION: ThoughtKind.FELT_PURPOSE,
        G.BROADCAST: ThoughtKind.ENJOYED_LEISURE,
        G.CONVENTION: ThoughtKind.FELT_PURPOSE,
        G.ELECTION: ThoughtKind.RESPECTED,
        G.LAUNCH: ThoughtKind.FELT_PURPOSE,
        G.RALLY: ThoughtKind.BELONGED,
        G.TESTING: ThoughtKind.FELT_PURPOSE,
        G.STRIKE: ThoughtKind.RESPECTED,
        G.EXHIBITION: ThoughtKind.SAW_BEAUTY,
        G.TRADE_FAIR: ThoughtKind.PROSPERED,
        G.SUMMIT_OF_GODS: ThoughtKind.FOUND_FAITH,
        G.NETWORK_GATHERING: ThoughtKind.FOUND_ANSWERS,
        G.REALM_GATHERING: ThoughtKind.FELT_STIMULATED,
        G.MOURNING: ThoughtKind.MOURNED,
        G.INITIATION: ThoughtKind.BELONGED,
        G.SPORT_MATCH: ThoughtKind.FELT_STIMULATED,
        G.COMMEMORATION: ThoughtKind.BELONGED,
        G.MUSTER: ThoughtKind.FELT_PURPOSE,
        G.REUNION: ThoughtKind.AMONG_KIN,
        G.GIFT_EXCHANGE: ThoughtKind.AMONG_FRIENDS,
    },
)

HONOURED_ROLES = MappingProxyType(
    {
        G.WEDDING: GuestRole.WEDDED,
        G.FUNERAL: GuestRole.MOURNED,
        G.WAKE: GuestRole.MOURNED,
        G.CORONATION: GuestRole.CROWNED,
        G.TRIAL: GuestRole.ACCUSED,
        G.EXECUTION: GuestRole.ACCUSED,
        G.MILESTONE: GuestRole.HONOURED,
        G.ELECTION: GuestRole.HONOURED,
        G.LAUNCH: GuestRole.HONOURED,
        G.MOURNING: GuestRole.MOURNED,
        G.INITIATION: GuestRole.HONOURED,
    }
)
FOR_THE_DEAD = frozenset(kind for kind, role in HONOURED_ROLES.items() if role is GuestRole.MOURNED)

CONTEST_KINDS = frozenset({G.TOURNAMENT, G.GAMES, G.SPORT_MATCH})
HOSTED_FEASTS = frozenset({G.FEAST, G.WEDDING, G.CORONATION, G.FESTIVAL})
UNDER_AGE_HOSTS = frozenset({G.CORONATION})

KEY_COLLECTIONS = MappingProxyType(
    {
        "war.outbreak": C.WAR,
        "war.battle": C.BATTLE,
        "war.sea_battle": C.BATTLE,
        "seafaring.sea_fight": C.BATTLE,
        "war.siege": C.SIEGE,
        "necromancy.siege": C.SIEGE,
        "duel.honour": C.DUEL,
        "structures.duel": C.DUEL,
        "war.trial_by_combat": C.DUEL,
        "pantheon.duel": C.DUEL,
        "war.god_duel": C.DUEL,
        "treaty.champions": C.DUEL,
        "monsters.raid": C.BEAST_ATTACK,
        "monsters.herd_raid": C.BEAST_ATTACK,
        "trade_route.beast_raid": C.BEAST_ATTACK,
        "faction.raid": C.RAID,
        "lore.godless_persecuted": C.PERSECUTION,
        "movements.revolt": C.INSURRECTION,
        "society.class_uprising": C.INSURRECTION,
        "society.poverty_uprising": C.INSURRECTION,
        "war.partisans": C.INSURRECTION,
        "polity.coup": C.COUP,
        "polity.succession_war": C.SUCCESSION_CRISIS,
        "statecraft.crisis": C.SUCCESSION_CRISIS,
        "travel.expedition_sent": C.JOURNEY,
        "travel.arrival": C.JOURNEY,
        "travel.pilgrimage_site": C.PILGRIMAGE,
        "kin.marriage": C.WEDDING,
        "mortal.mourning": C.FUNERAL,
        "statecraft.summit": C.SUMMIT,
        "disasters.plague_spread": C.PLAGUE,
        "disasters.city_plague": C.PLAGUE,
        "society.famine": C.FAMINE,
        "migration.famine": C.MIGRATION,
        "settlements.resettled": C.MIGRATION,
        "polity.founded": C.FOUNDING,
        "titles.seat_founded": C.FOUNDING,
        "mind.conversion": C.CONVERSION_WAVE,
        "native_faith.turned": C.CONVERSION_WAVE,
        "religion.schism": C.SCHISM,
        "faction.schism": C.SCHISM,
        "ethics.schism": C.SCHISM,
        "intrigue.scheme_exposed": C.INVESTIGATION,
        "item.regalia_seized": C.THEFT,
        "sons.rebel_theft": C.THEFT,
    }
)

KEY_PREFIX_COLLECTIONS = MappingProxyType({"trials.": C.TRIAL, "excavation.": C.EXCAVATION})

NEST_PARENTS = MappingProxyType(
    {
        C.BATTLE: (C.WAR,),
        C.SIEGE: (C.WAR,),
        C.OCCUPATION: (C.WAR,),
        C.DUEL: (C.TOURNAMENT, C.BATTLE, C.WAR, C.TRIAL),
        C.RAID: (C.WAR, C.INSURRECTION),
        C.PURGE: (C.SUCCESSION_CRISIS, C.INSURRECTION, C.COUP),
        C.TRIAL: (C.PURGE, C.INVESTIGATION),
        C.MIGRATION: (C.FAMINE, C.WAR, C.PLAGUE),
        C.FUNERAL: (C.WAR, C.PLAGUE, C.FAMINE),
        C.CORONATION: (C.SUCCESSION_CRISIS, C.FOUNDING),
        C.PILGRIMAGE: (C.CONVERSION_WAVE,),
        C.PERSECUTION: (C.SCHISM, C.CONVERSION_WAVE),
        C.TOURNAMENT: (C.FEAST, C.CORONATION, C.WEDDING),
        C.PERFORMANCE: (C.FEAST, C.CEREMONY, C.WEDDING),
        C.HUNT: (C.FEAST,),
    }
)

INCIDENT_ROLES = total(
    IncidentRole,
    {
        IncidentRole.SUBJECT: CollectionRole.MEMBER,
        IncidentRole.ACTOR: CollectionRole.LEADER,
        IncidentRole.CO_ACTOR: CollectionRole.MEMBER,
        IncidentRole.TARGET: CollectionRole.VICTIM,
        IncidentRole.VICTIM: CollectionRole.VICTIM,
        IncidentRole.BENEFICIARY: CollectionRole.MEMBER,
        IncidentRole.OPPONENT: CollectionRole.LOSER,
        IncidentRole.ALLY: CollectionRole.MEMBER,
        IncidentRole.LEADER: CollectionRole.LEADER,
        IncidentRole.MEMBER: CollectionRole.MEMBER,
        IncidentRole.GIVER: CollectionRole.MEMBER,
        IncidentRole.RECEIVER: CollectionRole.MEMBER,
        IncidentRole.BUYER: CollectionRole.MEMBER,
        IncidentRole.SELLER: CollectionRole.MEMBER,
        IncidentRole.LENDER: CollectionRole.MEMBER,
        IncidentRole.BORROWER: CollectionRole.MEMBER,
        IncidentRole.MAKER: CollectionRole.FOUNDER,
        IncidentRole.OWNER: CollectionRole.MEMBER,
        IncidentRole.HEIR: CollectionRole.MEMBER,
        IncidentRole.PREDECESSOR: CollectionRole.MEMBER,
        IncidentRole.SUCCESSOR: CollectionRole.LEADER,
        IncidentRole.ACCUSER: CollectionRole.MEMBER,
        IncidentRole.ACCUSED: CollectionRole.ACCUSED,
        IncidentRole.JUDGE: CollectionRole.LEADER,
        IncidentRole.ADVOCATE: CollectionRole.MEMBER,
        IncidentRole.TEACHER: CollectionRole.LEADER,
        IncidentRole.LEARNER: CollectionRole.MEMBER,
        IncidentRole.HEALER: CollectionRole.MEMBER,
        IncidentRole.PATIENT: CollectionRole.VICTIM,
        IncidentRole.PARENT: CollectionRole.MEMBER,
        IncidentRole.CHILD: CollectionRole.MEMBER,
        IncidentRole.SPOUSE: CollectionRole.MEMBER,
        IncidentRole.OFFICIANT: CollectionRole.LEADER,
        IncidentRole.HOST: CollectionRole.HOST,
        IncidentRole.GUEST: CollectionRole.GUEST,
        IncidentRole.ENVOY: CollectionRole.MEMBER,
        IncidentRole.MEDIATOR: CollectionRole.MEMBER,
        IncidentRole.AUTHORITY: CollectionRole.LEADER,
        IncidentRole.PATRON: CollectionRole.MEMBER,
        IncidentRole.INSTRUMENT: CollectionRole.MEMBER,
        IncidentRole.PRODUCT: CollectionRole.PRODUCT,
        IncidentRole.ORIGIN: CollectionRole.PLACE,
        IncidentRole.DESTINATION: CollectionRole.PLACE,
        IncidentRole.PLACE: CollectionRole.PLACE,
        IncidentRole.WITNESS: CollectionRole.WITNESS,
        IncidentRole.TELLER: CollectionRole.WITNESS,
    },
)

GUEST_ROLES = total(
    GuestRole,
    {
        GuestRole.HOST: CollectionRole.HOST,
        GuestRole.GUEST: CollectionRole.GUEST,
        GuestRole.HONOURED: CollectionRole.GUEST,
        GuestRole.CONTESTANT: CollectionRole.MEMBER,
        GuestRole.PERFORMER: CollectionRole.MEMBER,
        GuestRole.ACCUSED: CollectionRole.ACCUSED,
        GuestRole.MOURNED: CollectionRole.VICTIM,
        GuestRole.WEDDED: CollectionRole.LEADER,
        GuestRole.CROWNED: CollectionRole.LEADER,
        GuestRole.ENVOY: CollectionRole.MEMBER,
    },
)

HOST_ROLES: Mapping[GatheringKind, CollectionRole] = MappingProxyType({G.WEDDING: CollectionRole.LEADER, G.CORONATION: CollectionRole.LEADER})

CR = CollectionRole
LEADS = frozenset({CR.LEADER})
HOSTS = frozenset({CR.HOST})
MEMBERS = frozenset({CR.MEMBER})
VICTIMS = frozenset({CR.VICTIM})
ACCUSED = frozenset({CR.ACCUSED})
FOUNDERS = frozenset({CR.FOUNDER})
PRODUCTS = frozenset({CR.PRODUCT})
SIDES = frozenset({CR.LEADER, CR.LOSER, CR.WINNER})
PARTIES = frozenset({CR.LEADER, CR.VICTIM, CR.LOSER, CR.WINNER})
FINDS = frozenset({CR.LEADER, CR.FINDER})
WEDDED = frozenset({CR.LEADER, CR.HOST})
TITLE_ROLES: Mapping[CollectionKind, tuple[frozenset[CollectionRole], ...]] = total(
    CollectionKind,
    {
        C.WAR: (LEADS, HOSTS, MEMBERS, PRODUCTS),
        C.BATTLE: (SIDES, HOSTS, MEMBERS, PRODUCTS),
        C.SIEGE: (VICTIMS, LEADS, MEMBERS, PRODUCTS),
        C.DUEL: (PARTIES,),
        C.ABDUCTION: (VICTIMS, LEADS),
        C.BEAST_ATTACK: (LEADS, VICTIMS),
        C.RAID: (LEADS, VICTIMS),
        C.PERSECUTION: (ACCUSED, VICTIMS, MEMBERS, PRODUCTS),
        C.PURGE: (VICTIMS, LEADS, MEMBERS, PRODUCTS),
        C.INSURRECTION: (LEADS, MEMBERS, PRODUCTS),
        C.COUP: (LEADS, MEMBERS, PRODUCTS),
        C.SUCCESSION_CRISIS: (SIDES, MEMBERS, PRODUCTS),
        C.OCCUPATION: (VICTIMS, LEADS, MEMBERS, PRODUCTS),
        C.JOURNEY: (LEADS, MEMBERS, PRODUCTS),
        C.PILGRIMAGE: (LEADS, HOSTS, MEMBERS, PRODUCTS),
        C.COMPETITION: (HOSTS, SIDES, MEMBERS, PRODUCTS),
        C.PERFORMANCE: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.PROCESSION: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.CEREMONY: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.WEDDING: (WEDDED, MEMBERS, PRODUCTS),
        C.FUNERAL: (VICTIMS, HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.CORONATION: (LEADS, HOSTS, MEMBERS, PRODUCTS),
        C.FEAST: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.TOURNAMENT: (HOSTS, SIDES, MEMBERS, PRODUCTS),
        C.HUNT: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.COUNCIL: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.SUMMIT: (HOSTS, LEADS, MEMBERS, PRODUCTS),
        C.PLAGUE: (LEADS, MEMBERS, PRODUCTS, VICTIMS),
        C.FAMINE: (MEMBERS, PRODUCTS, VICTIMS, LEADS),
        C.MIGRATION: (LEADS, MEMBERS, PRODUCTS),
        C.FOUNDING: (PRODUCTS, MEMBERS, FOUNDERS, LEADS),
        C.THEFT: (MEMBERS, PRODUCTS, VICTIMS, LEADS),
        C.INVESTIGATION: (ACCUSED, VICTIMS, LEADS, MEMBERS, PRODUCTS),
        C.TRIAL: (ACCUSED, LEADS, MEMBERS, PRODUCTS, HOSTS),
        C.CONVERSION_WAVE: (LEADS, MEMBERS, PRODUCTS),
        C.SCHISM: (LEADS, MEMBERS, PRODUCTS),
        C.EXCAVATION: (FINDS, MEMBERS, PRODUCTS),
        C.HEROQUEST: (LEADS, MEMBERS, PRODUCTS),
        C.RIOT: (LEADS, MEMBERS, PRODUCTS, VICTIMS),
        C.PANIC: (LEADS, MEMBERS, PRODUCTS, VICTIMS),
        C.MOVEMENT: (FOUNDERS, LEADS, MEMBERS, PRODUCTS),
        C.STORYLET: (LEADS, MEMBERS, PRODUCTS),
    },
)

ROOM_PLACES = MappingProxyType(
    {
        PlaceKind.LAIR: (R.GATE, R.HALL, R.LAIR, R.STORE),
        PlaceKind.CAVE: (R.GATE, R.CHAMBER, R.LAIR),
        PlaceKind.CAVERN_SYSTEM: (R.GATE, R.STAIR, R.CHAMBER, R.CHAMBER, R.LAIR, R.HEART),
        PlaceKind.RUIN: (R.GATE, R.HALL, R.CISTERN, R.CELL, R.LIBRARY, R.VAULT),
        PlaceKind.SHRINE_SITE: (R.GATE, R.HALL, R.SHRINE),
        PlaceKind.DEAD_GOD_SITE: (R.GATE, R.CHAMBER, R.CRYPT, R.HEART),
        PlaceKind.BURIAL_GROUND: (R.GATE, R.CRYPT, R.CRYPT, R.VAULT),
        PlaceKind.MINE_SITE: (R.GATE, R.STAIR, R.CHAMBER, R.FORGE, R.STORE),
        PlaceKind.WRECK_SITE: (R.GATE, R.HALL, R.STORE, R.VAULT),
        PlaceKind.MEGASTRUCTURE_RUIN: (R.GATE, R.STAIR, R.HALL, R.LABORATORY, R.VAULT, R.HEART),
        PlaceKind.CANYON: (R.GATE, R.CHAMBER, R.LAIR),
    }
)

ROOM_STRUCTURES = MappingProxyType(
    {
        StructureKind.TOWER: (R.GATE, R.STAIR, R.LIBRARY, R.LABORATORY, R.CHAMBER),
        StructureKind.WATCHTOWER: (R.GATE, R.STAIR, R.ARMOURY),
        StructureKind.MONASTERY: (R.GATE, R.HALL, R.CELL, R.LIBRARY, R.SHRINE),
        StructureKind.CITADEL: (R.GATE, R.HALL, R.ARMOURY, R.VAULT, R.CHAMBER),
        StructureKind.FORT: (R.GATE, R.HALL, R.ARMOURY, R.CISTERN, R.STORE),
        StructureKind.CISTERN: (R.GATE, R.STAIR, R.CISTERN, R.CISTERN),
        StructureKind.RESERVOIR: (R.GATE, R.STAIR, R.CISTERN),
        StructureKind.FORGE: (R.GATE, R.FORGE, R.STORE),
        StructureKind.FOUNDRY: (R.GATE, R.HALL, R.FORGE, R.FORGE, R.STORE),
        StructureKind.PALACE: (R.GATE, R.HALL, R.CHAMBER, R.VAULT),
        StructureKind.PRISON: (R.GATE, R.CELL, R.CELL, R.HALL),
        StructureKind.TEMPLE: (R.GATE, R.HALL, R.SHRINE, R.VAULT),
        StructureKind.SHRINE: (R.GATE, R.SHRINE),
        StructureKind.NECROPOLIS: (R.GATE, R.CRYPT, R.CRYPT, R.HEART),
        StructureKind.TOMB: (R.GATE, R.CRYPT, R.VAULT),
        StructureKind.LIBRARY: (R.GATE, R.HALL, R.LIBRARY, R.VAULT),
        StructureKind.ALCHEMIST_LAB: (R.GATE, R.LABORATORY, R.STORE),
        StructureKind.WONDER: (R.GATE, R.HALL, R.STAIR, R.HEART),
        StructureKind.MILITARY_BASE: (R.GATE, R.HALL, R.ARMOURY, R.STORE),
        StructureKind.MISSILE_SILO: (R.GATE, R.STAIR, R.ARMOURY, R.HEART),
        StructureKind.DATA_CENTRE: (R.GATE, R.HALL, R.LIBRARY, R.VAULT),
        StructureKind.AI_CORE: (R.GATE, R.STAIR, R.LIBRARY, R.HEART),
        StructureKind.CLONING_FACILITY: (R.GATE, R.LABORATORY, R.CELL, R.STORE),
    }
)

ROOM_SETTLEMENTS = total(
    SizeTier,
    {
        SizeTier.HAMLET: (R.GATE, R.HOUSE, R.HOUSE, R.HALL, R.STORE),
        SizeTier.VILLAGE: (R.GATE, R.HOUSE, R.HOUSE, R.HOUSE, R.HALL, R.SHRINE, R.STORE),
        SizeTier.TOWN: (R.GATE, R.HOUSE, R.HOUSE, R.HOUSE, R.HALL, R.SHRINE, R.STORE, R.ARMOURY, R.VAULT),
        SizeTier.CITY: (R.GATE, R.HOUSE, R.HOUSE, R.HOUSE, R.HOUSE, R.HALL, R.SHRINE, R.LIBRARY, R.STORE, R.ARMOURY, R.CELL, R.VAULT),
        SizeTier.METROPOLIS: (
            R.GATE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HALL,
            R.HALL,
            R.SHRINE,
            R.LIBRARY,
            R.STORE,
            R.ARMOURY,
            R.CELL,
            R.CRYPT,
            R.VAULT,
        ),
        SizeTier.MEGALOPOLIS: (
            R.GATE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HALL,
            R.HALL,
            R.SHRINE,
            R.LIBRARY,
            R.LABORATORY,
            R.STORE,
            R.ARMOURY,
            R.CELL,
            R.CRYPT,
            R.VAULT,
        ),
        SizeTier.WORLD_CITY: (
            R.GATE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HOUSE,
            R.HALL,
            R.HALL,
            R.HALL,
            R.SHRINE,
            R.LIBRARY,
            R.LABORATORY,
            R.STORE,
            R.ARMOURY,
            R.CELL,
            R.CRYPT,
            R.VAULT,
            R.HEART,
        ),
    },
)


@dataclass(frozen=True)
class RoomSpec:
    items: bool = False
    guarded: bool = False
    records: bool = False
    wet: bool = False


ROOMS: Mapping[SiteRoomKind, RoomSpec] = total(
    SiteRoomKind,
    {
        R.GATE: RoomSpec(),
        R.HALL: RoomSpec(),
        R.STAIR: RoomSpec(),
        R.CELL: RoomSpec(),
        R.CHAMBER: RoomSpec(),
        R.VAULT: RoomSpec(items=True, guarded=True),
        R.SHRINE: RoomSpec(records=True),
        R.LAIR: RoomSpec(guarded=True),
        R.LIBRARY: RoomSpec(items=True, records=True),
        R.ARMOURY: RoomSpec(items=True),
        R.CRYPT: RoomSpec(items=True, guarded=True),
        R.LABORATORY: RoomSpec(records=True),
        R.HOUSE: RoomSpec(),
        R.STORE: RoomSpec(items=True),
        R.HEART: RoomSpec(items=True, guarded=True),
        R.CISTERN: RoomSpec(wet=True),
        R.FORGE: RoomSpec(items=True),
    },
)
ITEM_ROOMS = frozenset(kind for kind, spec in ROOMS.items() if spec.items)
GUARDED_ROOMS = frozenset(kind for kind, spec in ROOMS.items() if spec.guarded)
RECORD_ROOMS = frozenset(kind for kind, spec in ROOMS.items() if spec.records)
WET_ROOMS = frozenset(kind for kind, spec in ROOMS.items() if spec.wet)

EXCAVATION_PLACES = frozenset(
    {
        PlaceKind.RUIN,
        PlaceKind.DEAD_GOD_SITE,
        PlaceKind.CRATER,
        PlaceKind.BURIAL_GROUND,
        PlaceKind.WRECK_SITE,
        PlaceKind.MEGASTRUCTURE_RUIN,
        PlaceKind.DEBRIS_FIELD,
    }
)
EXCAVATION_FLAGS = frozenset({EntityFlag.PREVIOUS_CREATION, EntityFlag.RUIN})

STAGE_ORDER = (
    ExcavationStage.SURVEY,
    ExcavationStage.CLEARING,
    ExcavationStage.DIGGING,
    ExcavationStage.DEEP_LAYERS,
    ExcavationStage.INNER_SANCTUM,
)

STAGE_SKILLS = total(
    ExcavationStage,
    {
        ExcavationStage.SURVEY: SkillKind.LORE,
        ExcavationStage.CLEARING: SkillKind.ENGINEERING,
        ExcavationStage.DIGGING: SkillKind.ENGINEERING,
        ExcavationStage.DEEP_LAYERS: SkillKind.LORE,
        ExcavationStage.INNER_SANCTUM: SkillKind.SPELLCRAFT,
    },
)

STAGE_TECHNIQUES = MappingProxyType(
    {
        ExcavationStage.CLEARING: Technique.ARCH,
        ExcavationStage.DEEP_LAYERS: Technique.CARTOGRAPHY,
        ExcavationStage.INNER_SANCTUM: Technique.WARDING,
    }
)
