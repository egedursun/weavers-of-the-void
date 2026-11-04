from enum import StrEnum

STRUCTURE_LEVEL_MAX = 5


class StructureGroup(StrEnum):
    FAITH = "faith"
    KNOWLEDGE = "knowledge"
    DEFENCE = "defence"
    CIVIC = "civic"
    COMMERCE = "commerce"
    PRODUCTION = "production"
    INFRASTRUCTURE = "infrastructure"
    MEMORY = "memory"
    COSMIC = "cosmic"


class StructureKind(StrEnum):
    TEMPLE = "temple"
    SHRINE = "shrine"
    MONASTERY = "monastery"
    NECROPOLIS = "necropolis"
    LIBRARY = "library"
    SCHOOL = "school"
    OBSERVATORY = "observatory"
    ACADEMY = "academy"
    HOSPITAL = "hospital"
    WALL = "wall"
    GATE = "gate"
    TOWER = "tower"
    CITADEL = "citadel"
    WATCHTOWER = "watchtower"
    FORT = "fort"
    PALACE = "palace"
    COURT = "court"
    PRISON = "prison"
    MARKET = "market"
    HARBOUR = "harbour"
    WAREHOUSE = "warehouse"
    GRANARY = "granary"
    CARAVANSERAI = "caravanserai"
    BANK = "bank"
    FORGE = "forge"
    MILL = "mill"
    TANNERY = "tannery"
    MINE = "mine"
    QUARRY = "quarry"
    SHIPYARD = "shipyard"
    WORKSHOP = "workshop"
    ALCHEMIST_LAB = "alchemist_lab"
    ROAD = "road"
    BRIDGE = "bridge"
    AQUEDUCT = "aqueduct"
    SEWER = "sewer"
    CANAL = "canal"
    IRRIGATION = "irrigation"
    DAM = "dam"
    MONUMENT = "monument"
    TOMB = "tomb"
    ARENA = "arena"
    THEATRE = "theatre"
    WONDER = "wonder"
    COSMIC_GATE = "cosmic_gate"
    COSMIC_ARCHIVE = "cosmic_archive"


class ConstructionState(StrEnum):
    PLANNED = "planned"
    BUILDING = "building"
    COMPLETE = "complete"
    DAMAGED = "damaged"
    RUINED = "ruined"


STANDING_STATES = frozenset({ConstructionState.COMPLETE, ConstructionState.DAMAGED})
UNFINISHED_STATES = frozenset({ConstructionState.PLANNED, ConstructionState.BUILDING})


class BuilderKind(StrEnum):
    COMMUNITY = "community"
    POLITY = "polity"
    FACTION = "faction"
    CULT = "cult"
    PATRON = "patron"
    GOD = "god"


class ConstructionStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class BuildScale(StrEnum):
    MINOR = "minor"
    MAJOR = "major"
    GRAND = "grand"
    WONDER = "wonder"


class StaffScale(StrEnum):
    NONE = "none"
    FEW = "few"
    SOME = "some"
    MANY = "many"


class CapacityUnit(StrEnum):
    NONE = "none"
    TONS = "tons"
    VOLUMES = "volumes"
    GARRISON = "garrison"
    BEDS = "beds"
    BERTHS = "berths"
    SEATS = "seats"
    CELLS = "cells"
    WORSHIPPERS = "worshippers"
    PUPILS = "pupils"
    STALLS = "stalls"
    HANDS = "hands"
    LOADS = "loads"
    TRAVELLERS = "travellers"
