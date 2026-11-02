import re
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.text import replace_name
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.rarities import name_similarity_policy
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.motifs import motif_words
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.language.alphabet import first_word, fold_letter, is_consonant, is_vowel
from aerona.language.generator import NameKind
from aerona.language.similarity import letter_distance, normalize_name
from aerona.prompts.contexts.narrative import DialectWarning, NameProblem
from aerona.prompts.schemas.shared import NamingItemOutput
from aerona.rules.registry import Rules

FRESH_SEED = "fresh-name"
PARENTHESIZED = re.compile(r"^([^()]+?)\s*\((.+)\)\s*$")


def letters_of(word: str) -> str:
    return "".join(fold_letter(character) for character in word.casefold())


def is_weak(name: str, rules: Rules) -> bool:
    if len(name.split()) != 1:
        return False
    letters = letters_of(name)
    return len(letters) < rules.naming.weak_name_letters or (bool(letters) and is_vowel(letters[0]) and len(letters) < rules.naming.weak_vowel_start_letters)


def dialect_letters(root: str, phonology: Phonology) -> list[str]:
    vowels = {fold_letter(vowel.casefold()) for vowel in phonology.vowels}
    consonants = {fold_letter(letter.casefold()) for consonant in phonology.consonants for letter in consonant}
    word = letters_of(root)
    wrong = {letter for letter in word if (is_vowel(letter) and letter not in vowels) or (is_consonant(letter) and letter not in consonants)}
    return sorted(wrong | set(phonology.forbidden_in(word)))


def tired_in(name: str, tired: Collection[str]) -> list[str]:
    words = set(motif_words(name))
    return sorted(word for word in tired if word in words)


async def god_lookalike(session: AsyncSession, rules: Rules, name: str, ignore_node_id: int | None = None) -> str | None:
    if len(name.split()) != 1:
        return None
    settings = rules.naming
    root = rules.language.root_letters
    target = normalize_name(name)
    gods = [
        *(await session.execute(select(SonRow.id, SonRow.name))),
        *(await session.execute(select(ForeignGodRow.id, ForeignGodRow.name))),
        *(await session.execute(select(CreatorRow.id, CreatorRow.name))),
    ]
    for node_id, other in gods:
        current = normalize_name(other)
        if node_id == ignore_node_id or current == target or len(other.split()) != 1:
            continue
        if len(target) <= settings.god_similar_max_length and letter_distance(current, target) <= 1:
            return str(other)
        if current[:root] == target[:root] and letter_distance(current, target) < settings.god_root_min_distance:
            return str(other)
    return None


async def name_problems(
    session: AsyncSession, rules: Rules, entity: EntityRow, name: str, *, phonology: Phonology | None, tired: Collection[str]
) -> DialectWarning | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    root = first_word(cleaned)
    problems: list[NameProblem] = []
    letters = dialect_letters(root, phonology) if phonology is not None and len(letters_of(root)) >= rules.language.dialect_root_min_letters else []
    if letters:
        problems.append(NameProblem.DIALECT)
    similar = await NameRepository(session).similar_name(cleaned, name_similarity_policy(rules), ignore_node_id=entity.id)
    similar = similar or await god_lookalike(session, rules, cleaned)
    if similar is not None and normalize_name(similar) != normalize_name(entity.name):
        problems.append(NameProblem.SIMILAR)
    if is_weak(cleaned, rules):
        problems.append(NameProblem.WEAK)
    worn = tired_in(cleaned, tired)
    if worn:
        problems.append(NameProblem.TIRED)
    if not problems:
        return None
    return DialectWarning(id=entity.id, name=cleaned, root=root, letters=letters, problems=problems, similar_to=similar, tired_words=worn)


async def fresh_name(session: AsyncSession, rules: Rules, entity: EntityRow, *, phonology: Phonology | None, tired: Collection[str]) -> str | None:
    namer = Namer(session, rules)
    for attempt in range(rules.naming.fresh_name_attempts):
        seed = seed_of(FRESH_SEED, entity.id, attempt)
        candidate = await namer.from_speaker(entity.id, seed, NameKind.GENERAL) or await namer.person([], seed, entity.world_id)
        if candidate and await name_problems(session, rules, entity, candidate, phonology=phonology, tired=tired) is None:
            return candidate
    return None


def renamed_item(item: NamingItemOutput, name: str) -> NamingItemOutput:
    return item.model_copy(update={"name": name, "description": replace_name(item.description, item.name.strip(), name)})


def type_named_subtype(subtype: str, entity_type: EntityType) -> str | None:
    cleaned = subtype.strip()
    label = ENTITY_TYPES[entity_type].label.casefold()
    match = PARENTHESIZED.match(cleaned)
    head = (match.group(1) if match else cleaned).strip().casefold()
    if head not in {label, entity_type.value.replace("_", " ")}:
        return cleaned
    return match.group(2).strip() if match else None
