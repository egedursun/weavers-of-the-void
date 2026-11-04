from dataclasses import dataclass

from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, ResourceMechanic

B = KnowledgeBranch


@dataclass(frozen=True)
class KeyedText[K]:
    key: K
    label: str
    effect: str


KNOWLEDGE_BRANCHES: dict[KnowledgeBranch, KeyedText[KnowledgeBranch]] = {
    item.key: item
    for item in (
        KeyedText(B.AGRICULTURE, "Agriculture", "Knowers' population grows faster; famine and drought strike more softly."),
        KeyedText(B.METALLURGY, "Metallurgy", "Weapons and armour they produce are stronger."),
        KeyedText(B.SEAFARING, "Seafaring", "Trade, war and migration with communities beyond the sea."),
        KeyedText(B.WRITING, "Writing", "Their languages grow complex; what they know spreads faster to partners."),
        KeyedText(B.ARCHITECTURE, "Architecture", "Their structures are grander and sturdier, and withstand earthquakes."),
        KeyedText(B.MEDICINE, "Medicine", "Plagues strike more softly; their mortals live longer."),
        KeyedText(B.MAGIC, "Magic", "Their magic grows and the items they produce gain might."),
        KeyedText(B.WARFARE, "Art of War", "Their armies fight harder."),
        KeyedText(B.ASTRONOMY, "Astronomy", "They read the star of the epoch, sense disasters early and suffer them less."),
        KeyedText(B.TRADE, "Trade", "Their trade routes bring more prosperity."),
        KeyedText(B.SKY_NAVIGATION, "Sky Navigation", "Can discover routes between worlds; journeys are less likely to go astray."),
        KeyedText(B.SHIPBUILDING, "Shipbuilding", "Can build ships that sail between worlds."),
        KeyedText(B.GATE_LORE, "Gate Lore", "Can open and close ancient gates; gate journeys are swift."),
        KeyedText(B.PATHFINDING, "Pathfinding", "Can fold space with the cosmic travel resource."),
        KeyedText(B.VOID_LIVING, "Void Living", "Can settle worlds with thin or no air; loses fewer travellers."),
        KeyedText(B.IMMORTALITY, "Pursuit of Immortality", "Their mortals reach for immortality, and the gods see them as a threat."),
        KeyedText(B.BIOMANCY, "Biomancy", "Combines and alters living things: weaves chimeras and steers mutations."),
        KeyedText(B.FORBIDDEN, "Forbidden Knowledge", "Great power in war and magic, at the price of sanity and a leak into their world."),
    )
}

NATURAL_LAWS: dict[NaturalLaw, KeyedText[NaturalLaw]] = {
    item.key: item
    for item in (
        KeyedText(NaturalLaw.NONE, "None", "Narrative only; no mechanical effect."),
        KeyedText(NaturalLaw.IMMORTALITY, "Immortality", "Mortals do not age; population grows more slowly."),
        KeyedText(NaturalLaw.SHORT_LIFE, "Short life", "Mortals age faster; population grows faster."),
        KeyedText(NaturalLaw.DEAD_RETURN, "Return of the dead", "Fallen heroes may return as ghosts."),
        KeyedText(NaturalLaw.MAGIC_PRICE, "Price of magic", "Peoples steeped in magic pay part of their population to it every epoch."),
        KeyedText(NaturalLaw.WAR_BAN, "War ban", "Wars break out less often but are bloodier."),
        KeyedText(NaturalLaw.BOUNTY, "Bounty", "The fertility of every land rises each epoch."),
        KeyedText(NaturalLaw.DROUGHT, "Drought", "The fertility of every land falls each epoch."),
        KeyedText(NaturalLaw.SEA_BAN, "Sea ban", "Seas cannot be crossed; seafaring is useless."),
        KeyedText(NaturalLaw.ONE_LANGUAGE, "One language", "Languages spread faster through conquest and trade."),
        KeyedText(NaturalLaw.DISASTERS, "Disasters", "Natural disasters happen more often."),
        KeyedText(NaturalLaw.SOULS_REINCARNATE, "Souls reincarnate", "Souls that pass judgement may be born again into a new life."),
    )
}

RESOURCE_MECHANICS: dict[ResourceMechanic, KeyedText[ResourceMechanic]] = {
    item.key: item
    for item in (
        KeyedText(ResourceMechanic.DECAYING, "Decaying", "Rots in storage: its abundance drops each epoch and never regenerates."),
        KeyedText(ResourceMechanic.ADDICTIVE, "Addictive", "Communities that own it become addicted; losing it causes withdrawal."),
        KeyedText(ResourceMechanic.SENTIENT, "Sentient", "Chooses who mines it and makes demands; abandons owners who ignore them."),
        KeyedText(ResourceMechanic.DEPLETION_PRICE, "Depletion price", "When its last drop is drawn a curse falls on its land and doom approaches."),
        KeyedText(ResourceMechanic.FIXED, "Fixed", "A fixed amount in the cosmos that never regenerates."),
        KeyedText(ResourceMechanic.SACRED, "Sacred", "Belongs to a god who is angered when non-worshippers mine it."),
    )
}

BRANCH_PREREQUISITES: dict[KnowledgeBranch, tuple[KnowledgeBranch, ...]] = {
    B.SHIPBUILDING: (B.SEAFARING, B.METALLURGY),
    B.SKY_NAVIGATION: (B.ASTRONOMY,),
    B.GATE_LORE: (B.MAGIC, B.ASTRONOMY),
    B.PATHFINDING: (B.SKY_NAVIGATION, B.GATE_LORE),
    B.VOID_LIVING: (B.SKY_NAVIGATION, B.SHIPBUILDING, B.MEDICINE),
    B.IMMORTALITY: (B.MEDICINE, B.MAGIC),
    B.BIOMANCY: (B.MAGIC, B.MEDICINE, B.AGRICULTURE),
    B.FORBIDDEN: (B.MAGIC,),
}
ENGINE_UNDISCOVERABLE_BRANCHES: frozenset[KnowledgeBranch] = frozenset({B.FORBIDDEN})


def branch_label(branch: KnowledgeBranch) -> str:
    return KNOWLEDGE_BRANCHES[branch].label
