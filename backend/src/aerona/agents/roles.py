from enum import StrEnum


class AgentRole(StrEnum):
    GENESIS = "Genesis"
    CREATOR_PORTRAIT = "Creator portrait"
    SUMMONING = "Son summoning"
    SON_POWERS = "Son powers"
    AWAKENING = "Awakening of the peoples"
    REVELATION = "Revelation"
    SON_TURN = "Son turn"
    MORTAL_TURN = "Mortal turn"
    FATE = "Fate"
    FATE_EXTRA = "Fate extra judgment"
    CHRONICLER = "Chronicler"
    CHRONICLE_FIX = "Chronicle completion"
    LOST_CHRONICLE = "Lost chronicle"
    NAMING = "Naming"
    VOICES = "Voices of the peoples"
    DEEPENING = "Deepening"
    CREATOR_EPIC = "Creator epic"
    CREATOR_DEPTH = "Creator deepening"
    FOREIGN_GOD_DEPTH = "Foreign god deepening"
    SON_EPIC = "Son epic"
    ENTITY_IMAGE_PROMPTS = "Entity image prompts"
    COSMOS_IMAGE_PROMPTS = "Cosmos image prompts"
    COUNCIL = "Council of the gods"
    SON_CHAT = "Son chat"
    TRANSLATION = "Translation"
    WORLD_BIRTH = "World birth"
    BOND_SUGGESTION = "Fate bond suggestion"
    BOND_NAMING = "Fate related bond naming"
    LOCALISATION = "Localisation"


def turn_label(role: AgentRole, name: str) -> str:
    return f"{role}: {name}"


def role_of(label: str) -> str:
    return label.split(":", 1)[0].strip()
