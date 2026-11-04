from dataclasses import dataclass

from aerona.domain.enums.entity import EntityType


@dataclass(frozen=True)
class SpecialField:
    key: str
    label: str


@dataclass(frozen=True)
class SpecialSection:
    heading: str
    description: str
    fields: tuple[SpecialField, ...]


def _fields(*pairs: tuple[str, str]) -> tuple[SpecialField, ...]:
    return tuple(SpecialField(key, label) for key, label in pairs)


SPECIAL_SECTIONS: dict[EntityType, SpecialSection] = {
    EntityType.MORTAL: SpecialSection(
        "Character",
        "This mortal's inner world",
        _fields(
            ("temperament", "Temperament"),
            ("goal", "Goal in life"),
            ("fear", "Greatest fear"),
            ("secret", "The secret they tell no one"),
            ("speech", "How they speak"),
            ("relationships", "Important relationships: loved ones, enemies, people they owe"),
        ),
    ),
    EntityType.PEOPLE: SpecialSection(
        "Way of life and culture",
        "The texture of this people's social order and culture",
        _fields(
            ("governance", "Form of government and who has a say"),
            ("values", "Most sacred values"),
            ("taboos", "Taboos and punishments"),
            ("cuisine", "Cuisine: what they eat, what they never eat, table manners"),
            ("dress", "Dress and adornment: material, colour, who may not wear what"),
            ("music", "Music and sound: their instruments, melodies, at what moment one falls silent"),
            ("architecture", "Architectural style: what they build with and in what form"),
            ("art", "Their art: what it depicts, what is forbidden to depict"),
            ("calendar", "Calendar and festivals: what they count the year by, which celestial event they celebrate"),
            ("warfare", "Way of war and weapons"),
            ("death", "What they do with their dead"),
        ),
    ),
    EntityType.SETTLEMENT: SpecialSection(
        "City",
        "The texture of this settlement",
        _fields(
            ("governance", "Who rules, how"),
            ("economy", "What it lives on, what it sells"),
            ("quarters", "Important quarters and buildings"),
            ("problem", "Its biggest problem"),
            ("smell", "Its smell and its sound"),
        ),
    ),
    EntityType.FACTION: SpecialSection(
        "Organisation",
        "How this faction works",
        _fields(("purpose", "Real purpose"), ("hierarchy", "Hierarchy"), ("methods", "Methods"), ("symbol", "Symbol and colours"), ("weakness", "Weak point")),
    ),
    EntityType.CULT: SpecialSection(
        "Faith",
        "This cult's teaching",
        _fields(
            ("doctrine", "Core teaching"),
            ("rites", "Rites"),
            ("ranks", "Ranks"),
            ("prohibitions", "Prohibitions for its disciples"),
            ("promise", "Its promise to its disciples"),
        ),
    ),
    EntityType.SPECIES: SpecialSection(
        "Its nature",
        "This species' nature",
        _fields(
            ("behaviour", "Behaviour"),
            ("life_cycle", "Life cycle"),
            ("feeding", "How it feeds, told from the diet, size and habits given in its typed nature; never change them"),
            ("special_ability", "Special ability"),
            ("weakness", "Weakness"),
        ),
    ),
    EntityType.ITEM: SpecialSection(
        "The item's past",
        "This item's story",
        _fields(
            ("making", "How and from what it was made"),
            ("owners", "Chain of owners"),
            ("powers", "Known powers"),
            ("price", "The price of using it"),
        ),
    ),
    EntityType.LANGUAGE: SpecialSection(
        "Language structure",
        "This language's structure",
        _fields(
            ("sound", "Sound system"),
            ("grammar", "Grammar: suffixes, syntax"),
            ("script", "Its script or lack of one"),
            ("idioms", "Untranslatable concepts"),
        ),
    ),
    EntityType.KNOWLEDGE: SpecialSection(
        "Practice",
        "How this knowledge is applied",
        _fields(
            ("masters", "Who knows it, how it is taught"),
            ("tools", "Its tools and materials"),
            ("secret", "The part kept secret"),
            ("danger", "Its misuse"),
        ),
    ),
}


def special_section(entity_type: EntityType) -> SpecialSection | None:
    return SPECIAL_SECTIONS.get(entity_type)
