from enum import StrEnum


class EraChannel(StrEnum):
    FARMING = "farming"
    MINING = "mining"
    INDUSTRY = "industry"
    DISEASE = "disease"
    MESSAGES = "messages"
    MARCH = "march"
    SEA_ROUTES = "sea_routes"
    WORLD_ROUTES = "world_routes"
    FORTIFICATION = "fortification"
    POLLUTION = "pollution"
    OPINION = "opinion"
    RESEARCH = "research"
    SECULARISATION = "secularisation"
    FIREPOWER = "firepower"
    RITES = "rites"
    SPOILAGE = "spoilage"
    DOOM = "doom"
    LEARNING = "learning"
    HEALTH = "health"


class ProgrammeStage(StrEnum):
    PLANNING = "planning"
    BUILDING = "building"
    TESTING = "testing"
    COMPLETE = "complete"
    ABANDONED = "abandoned"
    SUSPENDED = "suspended"


class TechFamily(StrEnum):
    AGRICULTURE = "agriculture"
    MATERIALS = "materials"
    ENERGY = "energy"
    TRANSPORT = "transport"
    COMMUNICATION = "communication"
    MEDICINE = "medicine"
    WARFARE = "warfare"
    COMPUTATION = "computation"
    LIFE = "life"
    CONSTRUCTION = "construction"
    ADMINISTRATION = "administration"
    SPACE = "space"
    MIND = "mind"
    KNOWLEDGE = "knowledge"
