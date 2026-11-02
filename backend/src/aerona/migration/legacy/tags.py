from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EngineKind, EntityFlag, MortalRole, ProphecyReading
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic, SocialClass
from aerona.domain.enums.war import WarEnding
from aerona.domain.models.phonology import LanguageSignature
from aerona.migration.legacy.values import as_int
from aerona.migration.legacy.vocabulary import Vocabulary

SEPARATOR = ":"
HANDLED_PREFIXES = frozenset({"corpse", "native_world"})
KEPT_PREFIXES = frozenset({"victory", "holy", "partner"})
LIST_FIELDS = {"thread": "threads", "side": "sides", "war": "wars", "syncretic": "syncretic", "addicted": "addicted", "bargain": "bargains"}
SYNCRETIC_FIELD = "syncretic"
OLD_GODS_FIELD = "old_gods"
INTEGER_FIELDS = {"tier": "tier", "fold": "fold_count", "resurrection": "resurrection_son"}
ENUM_FIELDS: dict[str, tuple[str, type[StrEnum], str]] = {
    "outcome": ("war_ending", WarEnding, "outcome"),
    "branch": ("knowledge_branch", KnowledgeBranch, "branch"),
    "law": ("natural_law", NaturalLaw, "natural_law"),
    "script": ("writing_system", WritingSystem, "script"),
    "class": ("social_class", SocialClass, "social_class"),
    "reading": ("prophecy_reading", ProphecyReading, "reading"),
}


@dataclass
class TagReading:
    flags: list[EntityFlag] = field(default_factory=list)
    free: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    threads: list[int] = field(default_factory=list)
    sides: list[int] = field(default_factory=list)
    wars: list[int] = field(default_factory=list)
    outcome: WarEnding | None = None
    war_ongoing: bool = False
    war_ended: bool = False
    standby: bool = False
    captive: bool = False
    tier: int | None = None
    branch: KnowledgeBranch | None = None
    traits: list[CreatureTrait] = field(default_factory=list)
    mechanics: list[ResourceMechanic] = field(default_factory=list)
    sacred_son: int | None = None
    natural_law: NaturalLaw | None = None
    signature: LanguageSignature | None = None
    script: WritingSystem | None = None
    syncretic: list[int] = field(default_factory=list)
    old_gods: list[int] = field(default_factory=list)
    addicted: list[int] = field(default_factory=list)
    affiliation: tuple[str, int] | None = None
    social_class: SocialClass | None = None
    title: str | None = None
    resurrection_son: int | None = None
    fold_count: int | None = None
    bargains: list[int] = field(default_factory=list)
    purified: list[tuple[int, int]] = field(default_factory=list)
    reading: ProphecyReading | None = None
    engine_kind: EngineKind | None = None
    mortal_role: MortalRole | None = None


def parse_signature(vocabulary: Vocabulary, value: str) -> LanguageSignature | None:
    separators = vocabulary.json_keys["signature_separators"]
    keys = vocabulary.json_keys["signature"]
    pairs: dict[str, str] = {}
    for part in value.split(separators["pair"]):
        key, assignment, content = part.partition(separators["assignment"])
        if assignment:
            pairs[key.strip()] = content.strip()
    consonants = pairs.get(keys["consonants"])
    if not consonants:
        return None
    bias = as_int(pairs.get(keys["length_bias"])) or 0
    return LanguageSignature(consonants=consonants, cluster=pairs.get(keys["cluster"], ""), ending=pairs.get(keys["ending"], ""), length_bias=bias)


class TagReader:
    def __init__(self, vocabulary: Vocabulary) -> None:
        self._vocabulary = vocabulary
        self._prefixes = {legacy: english for english, legacy in vocabulary.tags.prefixes.items()}
        self._flags = {legacy.casefold(): EntityFlag(english) for legacy, english in vocabulary.tags.flags.items()}
        self._kept = {item.casefold() for item in vocabulary.tags.system_kept}
        self._variants = {legacy.casefold(): canonical.casefold() for legacy, canonical in vocabulary.tags.flag_variants.items()}
        self._engine_tags = {legacy.casefold(): EngineKind(english) for legacy, english in vocabulary.engine_kind_tags.items()}
        self._role_tags = {legacy.casefold(): MortalRole(english) for legacy, english in vocabulary.mortal_roles.tags.items()}
        self._handlers: dict[str, Callable[[TagReading, str], bool]] = {
            "trait": self._trait,
            "mechanic": self._mechanic,
            "signature": self._signature,
            "faction_link": self._affiliation,
            "title": self._title,
            "purified": self._purified,
        }

    def read(self, tags: Iterable[object]) -> TagReading:
        reading = TagReading()
        for raw in tags:
            text = str(raw).strip() if raw is not None else ""
            if not text:
                continue
            head, separator, tail = text.partition(SEPARATOR)
            english = self._prefixes.get(head.strip()) if separator else None
            if english is not None:
                if not self._prefixed(reading, english, tail.strip()):
                    reading.unknown.append(text)
                continue
            self._plain(reading, text)
        return reading

    def _plain(self, reading: TagReading, text: str) -> None:
        folded = self._variants.get(text.casefold(), text.casefold())
        vocabulary = self._vocabulary
        if folded == vocabulary.tags.war_ongoing.casefold():
            reading.war_ongoing = True
            return
        if folded == vocabulary.tags.war_ended.casefold():
            reading.war_ended = True
            return
        if folded == vocabulary.tags.standby.casefold():
            reading.standby = True
            return
        if folded == vocabulary.tags.captive.casefold():
            reading.captive = True
            return
        role = self._role_tags.get(folded)
        if role is not None and reading.mortal_role is None:
            reading.mortal_role = role
        flag = self._flags.get(folded)
        if flag is not None:
            if flag not in reading.flags:
                reading.flags.append(flag)
            return
        engine = self._engine_tags.get(folded)
        if engine is not None:
            reading.engine_kind = reading.engine_kind or engine
        if folded in self._kept or engine is not None or role is not None:
            reading.kept.append(text)
            return
        reading.free.append(text)

    def _prefixed(self, reading: TagReading, english: str, value: str) -> bool:
        if english in HANDLED_PREFIXES:
            return True
        if english in KEPT_PREFIXES:
            reading.kept.append(f"{self._vocabulary.prefix(english)}{SEPARATOR}{value}")
            return True
        if english in LIST_FIELDS:
            return self._listed_field(reading, english, value)
        if english in ENUM_FIELDS:
            enum_name, kind, attribute = ENUM_FIELDS[english]
            decoded = self._vocabulary.decode_as(enum_name, value, kind)
            setattr(reading, attribute, decoded)
            return decoded is not None
        if english in INTEGER_FIELDS:
            number = as_int(value)
            setattr(reading, INTEGER_FIELDS[english], number)
            return number is not None
        handler = self._handlers.get(english)
        return handler(reading, value) if handler is not None else False

    def _listed_field(self, reading: TagReading, english: str, value: str) -> bool:
        if english == SYNCRETIC_FIELD and value[:1].isalpha() and as_int(value[1:]) is not None:
            return self._listed(reading, OLD_GODS_FIELD, value[1:])
        return self._listed(reading, LIST_FIELDS[english], value)

    @staticmethod
    def _listed(reading: TagReading, attribute: str, value: str) -> bool:
        number = as_int(value)
        if number is None:
            return False
        target: list[int] = getattr(reading, attribute)
        if number not in target:
            target.append(number)
        return True

    def _trait(self, reading: TagReading, value: str) -> bool:
        trait = self._vocabulary.decode_as("creature_trait", value, CreatureTrait)
        if trait is not None and trait not in reading.traits:
            reading.traits.append(trait)
        return trait is not None

    def _signature(self, reading: TagReading, value: str) -> bool:
        reading.signature = parse_signature(self._vocabulary, value)
        return reading.signature is not None

    def _affiliation(self, reading: TagReading, value: str) -> bool:
        kind, _, community = value.partition(SEPARATOR)
        community_id = as_int(community)
        if community_id is None:
            return False
        reading.affiliation = (self._vocabulary.decode("faction_link_kind", kind) or kind, community_id)
        return True

    @staticmethod
    def _title(reading: TagReading, value: str) -> bool:
        reading.title = value or None
        return bool(value)

    @staticmethod
    def _purified(reading: TagReading, value: str) -> bool:
        resource, _, epoch = value.partition(SEPARATOR)
        resource_id, recovered = as_int(resource), as_int(epoch)
        if resource_id is None or recovered is None:
            return False
        reading.purified.append((resource_id, recovered))
        return True

    def _mechanic(self, reading: TagReading, value: str) -> bool:
        key, _, owner = value.partition(SEPARATOR)
        if self._vocabulary.decode("natural_law", key) == NaturalLaw.NONE.value:
            if EntityFlag.MECHANICS_WEIGHED not in reading.flags:
                reading.flags.append(EntityFlag.MECHANICS_WEIGHED)
            return True
        mechanic = self._vocabulary.decode_as("resource_mechanic", key, ResourceMechanic)
        if mechanic is None:
            return False
        if EntityFlag.MECHANICS_WEIGHED not in reading.flags:
            reading.flags.append(EntityFlag.MECHANICS_WEIGHED)
        if mechanic not in reading.mechanics:
            reading.mechanics.append(mechanic)
        if mechanic is ResourceMechanic.SACRED:
            reading.sacred_son = as_int(owner)
        return True
