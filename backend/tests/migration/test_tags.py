from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityFlag, MortalRole
from aerona.domain.enums.society import CreatureTrait, ResourceMechanic, SocialClass
from aerona.domain.enums.war import WarEnding
from aerona.domain.models.phonology import LanguageSignature
from aerona.migration.legacy.tags import TagReader, parse_signature
from aerona.migration.legacy.vocabulary import Vocabulary


def legacy_tag(vocabulary: Vocabulary, prefix: str, value: object) -> str:
    return f"{vocabulary.prefix(prefix)}:{value}"


def legacy_flag(vocabulary: Vocabulary, flag: EntityFlag) -> str:
    return next(legacy for legacy, english in vocabulary.tags.flags.items() if english == flag.value)


def test_prefixed_tags_become_typed_values(vocabulary: Vocabulary) -> None:
    tags = [
        legacy_tag(vocabulary, "side", 4),
        legacy_tag(vocabulary, "side", 9),
        legacy_tag(vocabulary, "thread", 3),
        legacy_tag(vocabulary, "tier", 3),
        legacy_tag(vocabulary, "outcome", vocabulary.encode("war_ending", "tribute")),
        legacy_tag(vocabulary, "trait", vocabulary.encode("creature_trait", "venomous")),
        legacy_tag(vocabulary, "mechanic", f"{vocabulary.encode('resource_mechanic', 'sacred')}:2"),
        legacy_tag(vocabulary, "class", vocabulary.encode("social_class", "priest")),
        legacy_tag(vocabulary, "script", vocabulary.encode("writing_system", "knot")),
        legacy_tag(vocabulary, "purified", "12:40"),
        legacy_tag(vocabulary, "faction_link", f"{vocabulary.encode('faction_link_kind', 'guild')}:15"),
        vocabulary.tags.war_ended,
    ]
    reading = TagReader(vocabulary).read(tags)
    assert reading.sides == [4, 9]
    assert reading.threads == [3]
    assert reading.tier == 3
    assert reading.outcome is WarEnding.TRIBUTE
    assert reading.traits == [CreatureTrait.VENOMOUS]
    assert reading.mechanics == [ResourceMechanic.SACRED]
    assert reading.sacred_son == 2
    assert reading.social_class is SocialClass.PRIEST
    assert reading.script is WritingSystem.KNOT
    assert reading.purified == [(12, 40)]
    assert reading.affiliation == ("guild", 15)
    assert reading.war_ended
    assert reading.unknown == []


def test_plain_tags_split_into_flags_kept_and_free(vocabulary: Vocabulary) -> None:
    ruler = next(legacy for legacy, english in vocabulary.mortal_roles.tags.items() if english == MortalRole.RULER.value)
    kept = vocabulary.tags.system_kept[1]
    reading = TagReader(vocabulary).read([legacy_flag(vocabulary, EntityFlag.CURSED), ruler, kept, "salt"])
    assert reading.flags == [EntityFlag.CURSED]
    assert reading.mortal_role is MortalRole.RULER
    assert reading.kept == [ruler, kept]
    assert reading.free == ["salt"]


def test_bad_values_of_known_prefixes_are_reported(vocabulary: Vocabulary) -> None:
    broken = [legacy_tag(vocabulary, "tier", "high"), legacy_tag(vocabulary, "branch", "nothing")]
    assert TagReader(vocabulary).read(broken).unknown == broken


def test_signature_parses_into_structured_phonology(vocabulary: Vocabulary) -> None:
    keys = vocabulary.json_keys["signature"]
    separators = vocabulary.json_keys["signature_separators"]
    text = separators["pair"].join(
        f"{keys[name]}{separators['assignment']}{value}" for name, value in (("consonants", "hlsn"), ("cluster", "ln"), ("ending", "al"), ("length_bias", "-1"))
    )
    assert parse_signature(vocabulary, text) == LanguageSignature(consonants="hlsn", cluster="ln", ending="al", length_bias=-1)
    assert parse_signature(vocabulary, "nothing") is None
