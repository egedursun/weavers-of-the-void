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
    }
)

CONTEST_KINDS = frozenset({G.TOURNAMENT, G.GAMES})
HOSTED_FEASTS = frozenset({G.FEAST, G.WEDDING, G.CORONATION, G.FESTIVAL})

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
        IncidentRole.TARGET: CollectionRole.VICTIM,
        IncidentRole.WITNESS: CollectionRole.WITNESS,
        IncidentRole.PLACE: CollectionRole.PLACE,
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

ROOM_PLACES = MappingProxyType(
    {
        PlaceKind.LAIR: (R.GATE, R.HALL, R.LAIR, R.STORE),
        PlaceKind.CAVE: (R.GATE, R.CHAMBER, R.LAIR),
        PlaceKind.CAVERN_SYSTEM: (R.GATE, R.STAIR, R.CHAMBER, R.CHAMBER, R.LAIR, R.HEART),
        PlaceKind.RUIN: (R.GATE, R.HALL, R.CELL, R.LIBRARY, R.VAULT),
        PlaceKind.SHRINE_SITE: (R.GATE, R.HALL, R.SHRINE),
        PlaceKind.GOD_CORPSE: (R.GATE, R.CHAMBER, R.CRYPT, R.HEART),
        PlaceKind.BURIAL_GROUND: (R.GATE, R.CRYPT, R.CRYPT, R.VAULT),
        PlaceKind.MINE_SITE: (R.GATE, R.STAIR, R.CHAMBER, R.STORE),
    }
)

ROOM_STRUCTURES = MappingProxyType(
    {
        StructureKind.TOWER: (R.GATE, R.STAIR, R.LIBRARY, R.LABORATORY, R.CHAMBER),
        StructureKind.WATCHTOWER: (R.GATE, R.STAIR, R.ARMOURY),
        StructureKind.MONASTERY: (R.GATE, R.HALL, R.CELL, R.LIBRARY, R.SHRINE),
        StructureKind.CITADEL: (R.GATE, R.HALL, R.ARMOURY, R.VAULT, R.CHAMBER),
        StructureKind.FORT: (R.GATE, R.HALL, R.ARMOURY, R.STORE),
        StructureKind.PALACE: (R.GATE, R.HALL, R.CHAMBER, R.VAULT),
        StructureKind.PRISON: (R.GATE, R.CELL, R.CELL, R.HALL),
        StructureKind.TEMPLE: (R.GATE, R.HALL, R.SHRINE, R.VAULT),
        StructureKind.SHRINE: (R.GATE, R.SHRINE),
        StructureKind.NECROPOLIS: (R.GATE, R.CRYPT, R.CRYPT, R.HEART),
        StructureKind.TOMB: (R.GATE, R.CRYPT, R.VAULT),
        StructureKind.LIBRARY: (R.GATE, R.HALL, R.LIBRARY, R.VAULT),
        StructureKind.ALCHEMIST_LAB: (R.GATE, R.LABORATORY, R.STORE),
        StructureKind.WONDER: (R.GATE, R.HALL, R.STAIR, R.HEART),
    }
)

ROOM_SETTLEMENTS = MappingProxyType({SizeTier.HAMLET: (R.GATE, R.HOUSE, R.HOUSE, R.HALL, R.STORE)})

ITEM_ROOMS = frozenset({R.VAULT, R.STORE, R.ARMOURY, R.LIBRARY, R.CRYPT, R.HEART})
GUARDED_ROOMS = frozenset({R.LAIR, R.HEART, R.VAULT, R.CRYPT})

EXCAVATION_PLACES = frozenset({PlaceKind.RUIN, PlaceKind.GOD_CORPSE, PlaceKind.CRATER, PlaceKind.BURIAL_GROUND})
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
