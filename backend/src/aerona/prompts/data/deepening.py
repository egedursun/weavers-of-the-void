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
            ("fear", "What they fear most, if anything"),
            ("secret", "What they keep to themselves, if anything"),
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
            ("taboos", "What they hold forbidden, if anything"),
            ("cuisine", "Food: what they take in, what they never take, and the customs around it"),
            ("dress", "What they wear or bear, if anything: its make, its look and who may not wear what"),
            ("music", "Their arts of sound or signal, if any: what they make and when they refrain from it"),
            ("architecture", "Architectural style: what they build with and in what form"),
            ("art", "Their art: what it depicts, what is forbidden to depict"),
            ("calendar", "Their calendar and what they mark, if anything"),
            ("warfare", "How they fight, if they do, and with what"),
            ("death", "Their customs around death, if any"),
        ),
    ),
    EntityType.SETTLEMENT: SpecialSection(
        "City",
        "The texture of this settlement",
        _fields(
            ("governance", "Who rules, how"),
            ("economy", "What it lives on, what it sells"),
            ("quarters", "Important quarters and buildings"),
            ("problem", "What troubles it most, if anything"),
            ("smell", "What it is like to be there"),
        ),
    ),
    EntityType.FACTION: SpecialSection(
        "Organisation",
        "How this faction works",
        _fields(
            ("purpose", "Real purpose"),
            ("hierarchy", "Hierarchy"),
            ("methods", "Methods"),
            ("symbol", "Its signs, if any"),
            ("weakness", "Its weak point, if any"),
        ),
    ),
    EntityType.CULT: SpecialSection(
        "Faith",
        "This cult's teaching",
        _fields(
            ("doctrine", "Core teaching"),
            ("rites", "Rites"),
            ("ranks", "Ranks"),
            ("prohibitions", "What it forbids its disciples, if anything"),
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
            ("special_ability", "What it can do that others cannot, if anything"),
            ("weakness", "Its weakness, if any"),
        ),
    ),
    EntityType.ITEM: SpecialSection(
        "The item's past",
        "This item's story",
        _fields(
            ("making", "How and from what it was made"),
            ("owners", "Chain of owners"),
            ("powers", "Known powers, if any"),
            ("price", "What using it does"),
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
            ("secret", "What part of it is kept from others, if any"),
            ("danger", "How it can be misused, if at all"),
        ),
    ),
}


def special_section(entity_type: EntityType) -> SpecialSection | None:
    return SPECIAL_SECTIONS.get(entity_type)
