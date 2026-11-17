from collections import Counter
from collections.abc import Sequence

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.constants.engine import ENGINE_SEED_SEPARATOR, PERSON_NAME_ATTEMPTS, WORLD_LANGUAGE_FALLBACKS
from aerona.db.read_memo import memo_of, memoized, table_names
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.node import NameRegistryRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.models.phonology import LanguageSignature
from aerona.engine.primitives.queries import spoken_language
from aerona.language.alphabet import fold_word
from aerona.language.corpus import CorpusSources, world_alphabet
from aerona.language.generator import NameKind, NamingVoice, generate_name
from aerona.language.lineage import phonology_lineage
from aerona.language.phonology import Phonology
from aerona.language.signature import derive_signature
from aerona.language.similarity import NamePool
from aerona.language.voice import build_voice, phonology_for
from aerona.rules.registry import Rules

ALPHABET_TABLES = table_names((LexemeRow, EntityRow))


POOLS_KEY = "aerona.name_pools"


def pools_of(sync: Session) -> dict[int, tuple[Rules, NamePool]]:
    pools: dict[int, tuple[Rules, NamePool]] = sync.info.setdefault(POOLS_KEY, {})
    return pools


def grow_pools(sync: Session, instance: object) -> None:
    if not isinstance(instance, NameRegistryRow):
        return
    for _rules, pool in sync.info.get(POOLS_KEY, {}).values():
        pool.add(instance.display)


def shrink_pools(sync: Session, *_: object) -> None:
    if any(isinstance(item, NameRegistryRow) for item in sync.deleted):
        sync.info.pop(POOLS_KEY, None)


def drop_pools(sync: Session, *_: object) -> None:
    sync.info.pop(POOLS_KEY, None)


def drop_pools_on_write(state: ORMExecuteState) -> None:
    if not state.is_select and getattr(getattr(state.statement, "table", None), "name", None) == NameRegistryRow.__tablename__:
        drop_pools(state.session)


event.listen(Session, "transient_to_pending", grow_pools)
event.listen(Session, "before_flush", shrink_pools)
event.listen(Session, "after_soft_rollback", drop_pools)
event.listen(Session, "do_orm_execute", drop_pools_on_write)


async def registered_pool(session: AsyncSession, rules: Rules) -> NamePool:
    pools = pools_of(session.sync_session)
    known = pools.get(id(rules))
    if known is not None and known[0] is rules:
        return known[1]
    pending = [item.display for item in session.sync_session.new if isinstance(item, NameRegistryRow)]
    pool = NamePool([*await session.scalars(select(NameRegistryRow.display)), *pending], rules)
    pools_of(session.sync_session)[id(rules)] = (rules, pool)
    return pool


async def alphabet_of_world(session: AsyncSession, rules: Rules, world_id: int) -> frozenset[str] | None:
    memo = memo_of(session, "world_alphabet", ALPHABET_TABLES)
    key = (id(rules), world_id)
    known: tuple[Rules, frozenset[str] | None] | None = memo.get(key) if memo is not None else None
    if known is not None and known[0] is rules:
        return known[1]
    statement = select(LexemeRow.word).join(EntityRow, EntityRow.id == LexemeRow.language_entity_id).where(EntityRow.world_id == world_id)
    found = world_alphabet(list(await session.scalars(statement)), rules)
    after = memo_of(session, "world_alphabet", ALPHABET_TABLES)
    if after is not None:
        after[key] = (rules, found)
    return found


@memoized(LanguageProfileRow)
async def language_parents(session: AsyncSession) -> tuple[tuple[int, int | None], ...]:
    return tuple(
        (entity_id, parent) for entity_id, parent in await session.execute(select(LanguageProfileRow.entity_id, LanguageProfileRow.parent_language_id))
    )


class Namer:
    def __init__(self, session: AsyncSession, rules: Rules, *, persist: bool = True) -> None:
        self.session = session
        self.rules = rules
        self.persist = persist
        self._pool: NamePool | None = None
        self._voices: dict[int, NamingVoice] = {}
        self._building: set[int] = set()
        self._parents: dict[int, int | None] | None = None
        self._alphabets: dict[int, frozenset[str] | None] = {}

    async def pool(self) -> NamePool:
        if self._pool is None:
            self._pool = (await registered_pool(self.session, self.rules)).copy()
        return self._pool

    async def world_alphabet(self, world_id: int) -> frozenset[str] | None:
        if world_id not in self._alphabets:
            self._alphabets[world_id] = await alphabet_of_world(self.session, self.rules, world_id)
        return self._alphabets[world_id]

    async def _parent_map(self) -> dict[int, int | None]:
        if self._parents is None:
            self._parents = dict(await language_parents(self.session))
        return self._parents

    async def _lexicon(self, language_ids: Sequence[int]) -> list[str]:
        words: list[str] = []
        for language_id in language_ids:
            words.extend(await self.session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language_id).order_by(LexemeRow.id)))
        return words

    async def _phonology(self, language: EntityRow, profile: LanguageProfileRow | None) -> Phonology:
        parents = await self._parent_map()
        words = await self._lexicon(phonology_lineage(language.id, parents, self.rules))
        speakers = select(BondRow.source_node_id).where(
            BondRow.target_node_id == language.id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE
        )
        speaker_names = list(
            await self.session.scalars(select(EntityRow.name).where(EntityRow.id.in_(speakers), EntityRow.pending_name.is_(False)).order_by(EntityRow.id))
        )
        world = await self.session.get(WorldRow, language.world_id)
        place_names = list(
            await self.session.scalars(
                select(EntityRow.name)
                .where(
                    EntityRow.world_id == language.world_id,
                    EntityRow.entity_type.in_([EntityType.REGION, EntityType.PLACE, EntityType.PEOPLE]),
                    EntityRow.pending_name.is_(False),
                    EntityRow.origin != EntityOrigin.ENGINE,
                )
                .order_by(EntityRow.id)
            )
        )
        samples = profile.phonology.sample_names if profile is not None else ()
        if not samples and world is not None and world.phonology is not None:
            samples = world.phonology.sample_names
        sources = CorpusSources(
            world_name=world.name if world is not None else "",
            lexicon_words=words,
            language_name=language.name,
            naming_samples=samples,
            speaker_names=speaker_names,
            world_names=place_names,
        )
        if profile is not None and profile.alphabet:
            alphabet: frozenset[str] | None = frozenset(fold_word(profile.alphabet))
        else:
            alphabet = await self.world_alphabet(language.world_id)
        return phonology_for(sources, alphabet, self.rules)

    async def _parent_signature(self, language: EntityRow) -> LanguageSignature | None:
        parent_id = (await self._parent_map()).get(language.id)
        if parent_id is None or parent_id in self._building:
            return None
        parent = await self.session.get(EntityRow, parent_id)
        if parent is None:
            return None
        self._building.add(language.id)
        try:
            return (await self.voice(parent)).signature
        finally:
            self._building.discard(language.id)

    async def voice(self, language: EntityRow) -> NamingVoice:
        cached = self._voices.get(language.id)
        if cached is not None:
            return cached
        profile = await self.session.get(LanguageProfileRow, language.id)
        phonology = await self._phonology(language, profile)
        stored = profile.signature if profile is not None else None
        parent_signature = await self._parent_signature(language) if stored is None else None
        voice = build_voice(str(language.id), phonology, self.rules, stored, parent_signature)
        if self.persist and profile is not None and stored is None and voice.signature is not None:
            profile.signature = voice.signature
        self._voices[language.id] = voice
        return voice

    async def regenerate_signature(self, language: EntityRow, salt: str) -> LanguageSignature | None:
        profile = await self.session.get(LanguageProfileRow, language.id)
        phonology = await self._phonology(language, profile)
        signature = derive_signature(f"{language.id}:{salt}", phonology, await self._parent_signature(language), self.rules)
        self._voices.pop(language.id, None)
        return signature

    async def from_language(self, language: EntityRow, seed: str, kind: NameKind) -> str | None:
        name = generate_name(await self.voice(language), seed, kind, await self.pool(), self.rules)
        if name is not None:
            (await self.pool()).add(name)
        return name

    async def from_speaker(self, speaker_id: int, seed: str, kind: NameKind) -> str | None:
        language = await spoken_language(self.session, speaker_id)
        if language is None:
            return None
        return await self.from_language(language, seed, kind)

    async def _world_languages(self, world_id: int) -> list[EntityRow]:
        statement = (
            select(EntityRow.id)
            .join(BondRow, BondRow.target_node_id == EntityRow.id)
            .where(
                EntityRow.world_id == world_id,
                EntityRow.entity_type == EntityType.LANGUAGE,
                EntityRow.status == EntityStatus.CANON,
                BondRow.kind == BondKind.SPEAKS,
                BondRow.state == BondState.ACTIVE,
            )
        )
        counts = Counter(await self.session.scalars(statement))
        ranked = sorted(counts, key=lambda language_id: (-counts[language_id], language_id))[:WORLD_LANGUAGE_FALLBACKS]
        languages = [await self.session.get(EntityRow, language_id) for language_id in ranked]
        return [language for language in languages if language is not None]

    async def person(self, sources: Sequence[EntityRow], seed: str, world_id: int | None = None) -> str | None:
        for attempt in range(PERSON_NAME_ATTEMPTS):
            attempt_seed = seed if attempt == 0 else ENGINE_SEED_SEPARATOR.join((seed, str(attempt)))
            for source in sources:
                name = await self.from_speaker(source.id, attempt_seed, NameKind.PERSON)
                if name is not None:
                    return name
        world = world_id if world_id is not None else (sources[0].world_id if sources else None)
        if world is None:
            return None
        for language in await self._world_languages(world):
            for kind in (NameKind.PERSON, NameKind.GENERAL):
                name = await self.from_language(language, ENGINE_SEED_SEPARATOR.join((seed, kind.value)), kind)
                if name is not None:
                    return name
        return None


def seed_of(*parts: object) -> str:
    return ENGINE_SEED_SEPARATOR.join(str(part) for part in parts)
