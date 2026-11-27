from dataclasses import dataclass

from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory

K = ChronicleKind
N = NotificationCategory


@dataclass(frozen=True)
class NotificationCategorySpec:
    category: NotificationCategory
    label: str
    severity: int
    enabled_by_default: bool
    forced: bool = False


@dataclass(frozen=True)
class ChronicleKindSpec:
    kind: ChronicleKind
    label: str
    visible: bool = True
    notification: NotificationCategory | None = None


NOTIFICATION_SEVERITY_MIN = 1
NOTIFICATION_SEVERITY_MAX = 4

NOTIFICATION_CATEGORIES: dict[NotificationCategory, NotificationCategorySpec] = {
    spec.category: spec
    for spec in (
        NotificationCategorySpec(N.REBELLION, "Son's rebellion", 3, True),
        NotificationCategorySpec(N.DEATH, "Death", 3, True),
        NotificationCategorySpec(N.BIRTH, "Legendary birth", 3, True),
        NotificationCategorySpec(N.PROPHECY, "Prophecy fulfilled", 3, True),
        NotificationCategorySpec(N.APOCALYPSE, "Omen of doomsday", 4, True),
        NotificationCategorySpec(N.HORROR, "Cosmic horror", 3, True),
        NotificationCategorySpec(N.WAR, "War", 2, True),
        NotificationCategorySpec(N.PRAYER, "Prayer to you", 2, True),
        NotificationCategorySpec(N.COSMOS, "Cosmic event", 2, True),
        NotificationCategorySpec(N.ASCENSION, "Ascension", 2, True),
        NotificationCategorySpec(N.DISASTER, "Disaster and sky", 2, False),
        NotificationCategorySpec(N.EPOCH, "Epoch ended", 1, True),
        NotificationCategorySpec(N.ACHIEVEMENT, "Achievement", 2, True),
        NotificationCategorySpec(N.SOCIETY, "Society, lineage and debt", 2, True),
        NotificationCategorySpec(N.REPUTATION, "In the sons' eyes", 2, True),
        NotificationCategorySpec(N.ERROR, "System error", 3, True),
        NotificationCategorySpec(N.NOTE, "The god's note", 1, True, forced=True),
        NotificationCategorySpec(N.WORK, "Work done in the background", 1, True),
    )
}

CHRONICLE_KINDS: dict[ChronicleKind, ChronicleKindSpec] = {
    spec.kind: spec
    for spec in (
        ChronicleKindSpec(K.CREATION, "Creation"),
        ChronicleKindSpec(K.SPEECH, "Speech"),
        ChronicleKindSpec(K.CHALLENGE, "Challenge"),
        ChronicleKindSpec(K.PRAYER, "Prayer", notification=N.PRAYER),
        ChronicleKindSpec(K.ORDER, "Order"),
        ChronicleKindSpec(K.FATE, "Fate"),
        ChronicleKindSpec(K.DEATH, "Death", notification=N.DEATH),
        ChronicleKindSpec(K.BIRTH, "Birth"),
        ChronicleKindSpec(K.SYSTEM, "System"),
        ChronicleKindSpec(K.MESSAGE, "Message"),
        ChronicleKindSpec(K.CREATOR_HAND, "The Creator's hand"),
        ChronicleKindSpec(K.WORLD, "The world's course"),
        ChronicleKindSpec(K.ENGINE_RAW, "Engine note", visible=False),
        ChronicleKindSpec(K.KNOWLEDGE, "Knowledge"),
        ChronicleKindSpec(K.RESOURCE, "Resource"),
        ChronicleKindSpec(K.CULTURE, "Culture"),
        ChronicleKindSpec(K.TRADE, "Trade"),
        ChronicleKindSpec(K.EXPLORATION, "Exploration"),
        ChronicleKindSpec(K.DIPLOMACY, "Diplomacy", notification=N.SOCIETY),
        ChronicleKindSpec(K.PRODUCTION, "Production"),
        ChronicleKindSpec(K.LANGUAGE, "Language"),
        ChronicleKindSpec(K.MIRACLE, "Miracle"),
        ChronicleKindSpec(K.CIVILIZATION, "Civilization", notification=N.SOCIETY),
        ChronicleKindSpec(K.CREATOR_REPUTATION, "The Creator's reputation", notification=N.REPUTATION),
        ChronicleKindSpec(K.CONSTRUCTION, "Construction"),
        ChronicleKindSpec(K.EXISTENCE, "Existence", notification=N.ASCENSION),
        ChronicleKindSpec(K.DREAM, "Dream"),
        ChronicleKindSpec(K.STAR, "Star", notification=N.COSMOS),
        ChronicleKindSpec(K.DIVINE_SIGN, "Divine sign"),
        ChronicleKindSpec(K.CLIMATE, "Climate", notification=N.DISASTER),
        ChronicleKindSpec(K.COSMIC, "Cosmic", notification=N.COSMOS),
        ChronicleKindSpec(K.DEBT, "Debt", notification=N.SOCIETY),
        ChronicleKindSpec(K.FOREIGN_GOD, "Foreign god", notification=N.COSMOS),
        ChronicleKindSpec(K.WORLD_AGE, "World age"),
        ChronicleKindSpec(K.COUNCIL, "Council"),
        ChronicleKindSpec(K.PREVIOUS_CREATION, "Previous creation", notification=N.COSMOS),
        ChronicleKindSpec(K.SKY, "Sky", notification=N.DISASTER),
        ChronicleKindSpec(K.GIFT, "Gift"),
        ChronicleKindSpec(K.WORSHIP, "Worship"),
        ChronicleKindSpec(K.WORLD_BIRTH, "World birth", notification=N.COSMOS),
        ChronicleKindSpec(K.PROPHECY, "Prophecy"),
        ChronicleKindSpec(K.COVENANT, "Covenant"),
        ChronicleKindSpec(K.ARMY, "Army"),
        ChronicleKindSpec(K.ASCENSION, "Ascension", notification=N.ASCENSION),
        ChronicleKindSpec(K.MIGRATION, "Migration"),
        ChronicleKindSpec(K.LEGENDARY_QUEST, "Legendary quest", notification=N.COSMOS),
        ChronicleKindSpec(K.WAR, "War", notification=N.WAR),
        ChronicleKindSpec(K.WAR_OF_GODS, "War of gods", notification=N.WAR),
        ChronicleKindSpec(K.COSMIC_LAW, "Cosmic law", notification=N.COSMOS),
        ChronicleKindSpec(K.HORROR, "Cosmic horror", notification=N.HORROR),
        ChronicleKindSpec(K.OUTER_BEING, "Outer Being", notification=N.HORROR),
        ChronicleKindSpec(K.IMMORTALITY, "Immortality", notification=N.HORROR),
        ChronicleKindSpec(K.REBELLION, "Rebellion", notification=N.REBELLION),
        ChronicleKindSpec(K.APOCALYPSE, "Doomsday", notification=N.APOCALYPSE),
        ChronicleKindSpec(K.RESURRECTION, "Resurrection", notification=N.ASCENSION),
        ChronicleKindSpec(K.LINEAGE, "Lineage", notification=N.SOCIETY),
        ChronicleKindSpec(K.DISASTER, "Disaster", notification=N.DISASTER),
        ChronicleKindSpec(K.ADVENTURE, "Adventure"),
        ChronicleKindSpec(K.INTRIGUE, "Intrigue"),
        ChronicleKindSpec(K.RESCUE, "Rescue"),
        ChronicleKindSpec(K.MERGED_SPECIES, "Merged species"),
        ChronicleKindSpec(K.ESCAPE, "Escape"),
        ChronicleKindSpec(K.DOMESTICATION, "Domestication"),
        ChronicleKindSpec(K.AGE_CHANGE, "Change of age"),
        ChronicleKindSpec(K.EXPEDITION, "Expedition"),
        ChronicleKindSpec(K.SPIRIT, "Spirit"),
        ChronicleKindSpec(K.CURSE, "Curse"),
        ChronicleKindSpec(K.DENIAL, "Denial"),
        ChronicleKindSpec(K.RANSOM, "Ransom"),
        ChronicleKindSpec(K.PROHIBITION, "Prohibition"),
    )
}

FEED_NOTIFICATIONS: dict[FeedCategory, NotificationCategory | None] = {
    FeedCategory.WAR: N.WAR,
    FeedCategory.DISASTER: N.DISASTER,
    FeedCategory.SKY: N.DISASTER,
    FeedCategory.LEAK: N.HORROR,
    FeedCategory.VOYAGE: N.COSMOS,
    FeedCategory.GATE: N.COSMOS,
    FeedCategory.CIVILIZATION: N.SOCIETY,
    FeedCategory.LIFE: None,
    FeedCategory.WORLD: None,
}


def chronicle_notification(kind: ChronicleKind, feed: FeedCategory | None) -> NotificationCategory | None:
    if kind is ChronicleKind.WORLD:
        return FEED_NOTIFICATIONS.get(feed) if feed is not None else None
    return CHRONICLE_KINDS[kind].notification


def is_visible(kind: ChronicleKind) -> bool:
    return CHRONICLE_KINDS[kind].visible
