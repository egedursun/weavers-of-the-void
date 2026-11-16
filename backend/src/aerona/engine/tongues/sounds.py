from dataclasses import dataclass

from sqlalchemy import delete, func, select

from aerona.catalog.tongues import KIND_WEIGHTS, LENITION
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.discovery import NameMeaningRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow, lexeme_key
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.tongues import SoundChangeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import SoundChangeCause, SoundChangeKind, SoundEnvironment, WordRegister
from aerona.domain.models.phonology import Phonology
from aerona.engine.context import TickContext
from aerona.engine.lore.language import speakers, tongues_of
from aerona.engine.networks.book import networked_with
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.queries import canon, has_flag

FIXED_REGISTERS = frozenset({WordRegister.ARCHAIC, WordRegister.SACRED, WordRegister.POETIC})
SHORTEST = 2
PLACE_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.REGION, EntityType.PLACE})
NAME = "name"
GLOSS_MAX = 2000


@dataclass
class SoundTally:
    changes: int = 0
    rederived: int = 0
    reconstructed: int = 0
    renamed: int = 0


@dataclass(frozen=True)
class Change:
    kind: SoundChangeKind
    source: str
    target: str
    environment: SoundEnvironment


def fits(lower: str, start: int, end: int, environment: SoundEnvironment, vowels: frozenset[str]) -> bool:
    if environment is SoundEnvironment.INITIAL:
        return start == 0
    if environment is SoundEnvironment.FINAL:
        return end == len(lower)
    if environment is SoundEnvironment.BETWEEN_VOWELS:
        return start > 0 and end < len(lower) and lower[start - 1] in vowels and lower[end] in vowels
    return True


def apply_change(word: str, change: Change, vowels: frozenset[str]) -> str:
    source = change.source.casefold()
    if not source or not word:
        return word
    lower = word.casefold()
    built: list[str] = []
    index = 0
    while index < len(lower):
        end = index + len(source)
        if lower.startswith(source, index) and fits(lower, index, end, change.environment, vowels):
            built.append(change.target)
            index = end
            continue
        built.append(lower[index])
        index += 1
    result = "".join(built)
    if len(result) < SHORTEST or not any(letter in vowels for letter in result):
        return word
    return result[0].upper() + result[1:] if word[0].isupper() else result


def derive(proto: str, changes: list[Change], vowels: frozenset[str]) -> str:
    word = proto
    for change in changes:
        word = apply_change(word, change, vowels)
    return word


def vowels_of(phonology: Phonology) -> frozenset[str]:
    return frozenset(item.casefold() for item in phonology.vowels)


def as_change(row: SoundChangeRow) -> Change:
    return Change(row.kind, row.source, row.target, row.environment)


async def changes_of(ctx: TickContext, language_id: int) -> list[SoundChangeRow]:
    found = await ctx.session.scalars(
        select(SoundChangeRow).where(SoundChangeRow.language_entity_id == language_id).order_by(SoundChangeRow.position, SoundChangeRow.id)
    )
    return list(found)


def invent(ctx: TickContext, language: EntityRow, phonology: Phonology) -> Change | None:
    rng = ctx.rng(f"sound.invent.{language.id}.{ctx.epoch}")
    consonants = [item.casefold() for item in phonology.consonants if item]
    vowels = [item.casefold() for item in phonology.vowels if item]
    kinds = [kind for kind, weight in KIND_WEIGHTS.items() for _ in range(weight)]
    kind = rng.pick(kinds)
    if kind is SoundChangeKind.LENITION:
        soft = [item for item in consonants if item in LENITION]
        if not soft:
            return None
        source = rng.pick(soft)
        return Change(kind, source, LENITION[source], SoundEnvironment.BETWEEN_VOWELS)
    if kind is SoundChangeKind.VOWEL_SHIFT and len(vowels) > 1:
        source = rng.pick(vowels)
        return Change(kind, source, rng.pick([item for item in vowels if item != source]), rng.pick(list(SoundEnvironment)))
    if kind is SoundChangeKind.LOSS and vowels:
        return Change(kind, rng.pick(vowels), "", SoundEnvironment.FINAL)
    if len(consonants) > 1:
        source = rng.pick(consonants)
        target = rng.pick([item for item in consonants if item != source])
        environment = SoundEnvironment.ANYWHERE if kind is SoundChangeKind.MERGER else rng.pick(list(SoundEnvironment))
        return Change(SoundChangeKind.MERGER if kind is SoundChangeKind.MERGER else SoundChangeKind.SHIFT, source, target, environment)
    return None


async def prestigious(ctx: TickContext, language: EntityRow, contacts: set[int]) -> int | None:
    own = await ctx.session.get(LanguageStandingRow, language.id)
    floor = (own.prestige if own is not None else 0) + ctx.rules.sound_changes.prestige_gap
    rows = await ctx.session.scalars(
        select(LanguageStandingRow).where(LanguageStandingRow.language_entity_id.in_(sorted(contacts)), LanguageStandingRow.prestige >= floor)
    )
    best = max(rows, key=lambda row: (row.prestige, -row.language_entity_id), default=None)
    return best.language_entity_id if best is not None else None


async def contacts_of(ctx: TickContext, language_id: int) -> set[int]:
    found: set[int] = set()
    communities = set(await speakers(ctx.session, language_id))
    for community in sorted(communities | await networked_with(ctx.session, communities)):
        found |= await tongues_of(ctx.session, community)
    found.discard(language_id)
    return found


async def migrated(ctx: TickContext, language_id: int) -> bool:
    communities = await speakers(ctx.session, language_id)
    if not communities:
        return False
    moved = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.kind == BondKind.MIGRATED_TO, BondRow.target_node_id.in_(communities), BondRow.epoch >= ctx.epoch - 1).limit(1)
    )
    return moved is not None


async def borrowed(ctx: TickContext, lender_id: int) -> Change | None:
    rows = await changes_of(ctx, lender_id)
    return as_change(rows[-1]) if rows else None


async def acquire(ctx: TickContext, language: EntityRow, tally: SoundTally) -> SoundChangeRow | None:
    table = ctx.rules.sound_changes
    profile = await ctx.session.get(LanguageProfileRow, language.id)
    if profile is None:
        return None
    contacts = await contacts_of(ctx, language.id)
    moved = await migrated(ctx, language.id)
    rng = ctx.rng(f"sound.acquire.{language.id}.{ctx.epoch}")
    chance = table.base_pct + table.contact_pct * len(contacts) + (table.migration_pct if moved else 0)
    if not rng.chance(chance):
        return None
    lender = await prestigious(ctx, language, contacts)
    change: Change | None = None
    cause = SoundChangeCause.DRIFT
    if lender is not None:
        change, cause = await borrowed(ctx, lender), SoundChangeCause.PRESTIGE
    elif contacts and rng.chance(table.contact_pct * len(contacts)):
        change, cause = await borrowed(ctx, rng.pick(sorted(contacts))), SoundChangeCause.CONTACT
    if change is None:
        change, cause = invent(ctx, language, profile.phonology), SoundChangeCause.MIGRATION if moved else SoundChangeCause.DRIFT
    if change is None or change in {as_change(row) for row in await changes_of(ctx, language.id)}:
        return None
    row = await add_change(ctx, language.id, change, cause)
    tally.changes += 1
    tally.rederived += await rederive(ctx, language.id)
    tally.renamed += await weather_names(ctx, language.id, change, vowels_of(profile.phonology))
    return row


async def weather_names(ctx: TickContext, language_id: int, change: Change, vowels: frozenset[str]) -> int:
    rows = await ctx.session.execute(
        select(NameMeaningRow, EntityRow)
        .join(EntityRow, EntityRow.id == NameMeaningRow.node_id)
        .where(NameMeaningRow.language_entity_id == language_id, EntityRow.entity_type.in_(list(PLACE_TYPES)), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    names = NameRepository(ctx.session)
    renamed = 0
    for meaning, place in list(rows):
        if held(place.id) or NAME in (meaning.locked or []):
            continue
        if not ctx.rng(f"sound.place_name.{place.id}.{ctx.epoch}").chance(ctx.rules.sound_changes.name_pct):
            continue
        form = apply_change(place.name, change, vowels)
        if len(form) < SHORTEST or form == place.name or await names.is_taken(form, ignore_node_id=place.id):
            continue
        old = place.name
        await EntityRepository(ctx.session).rename(place, form)
        meaning.name = form
        meaning.gloss = clipped_gloss(f"{meaning.gloss}; once called {old}".lstrip("; "))
        renamed += 1
        await note(ctx, f"In the mouths of its folk, {old} became {form}.", key="tongues.place_renamed", ids=[place.id, language_id])
    return renamed


def clipped_gloss(text: str) -> str:
    return text[-GLOSS_MAX:] if len(text) > GLOSS_MAX else text


async def add_change(ctx: TickContext, language_id: int, change: Change, cause: SoundChangeCause) -> SoundChangeRow:
    position = int(await ctx.session.scalar(select(func.count()).select_from(SoundChangeRow).where(SoundChangeRow.language_entity_id == language_id)) or 0)
    row = SoundChangeRow(
        language_entity_id=language_id,
        kind=change.kind,
        source=change.source,
        target=change.target,
        environment=change.environment,
        cause=cause,
        position=position,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await fold(ctx, language_id)
    return row


async def fold(ctx: TickContext, language_id: int) -> None:
    rows = await changes_of(ctx, language_id)
    excess = len(rows) - ctx.rules.sound_changes.most
    if excess <= 0:
        return
    profile = await ctx.session.get(LanguageProfileRow, language_id)
    vowels = vowels_of(profile.phonology) if profile is not None else frozenset()
    oldest = [as_change(row) for row in rows[:excess]]
    for lexeme in await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language_id)):
        if lexeme.proto_word is not None:
            lexeme.proto_word = derive(lexeme.proto_word, oldest, vowels)
    await ctx.session.execute(delete(SoundChangeRow).where(SoundChangeRow.id.in_([row.id for row in rows[:excess]])))
    for index, row in enumerate(rows[excess:]):
        row.position = index


async def rederive(ctx: TickContext, language_id: int) -> int:
    profile = await ctx.session.get(LanguageProfileRow, language_id)
    if profile is None:
        return 0
    vowels = vowels_of(profile.phonology)
    changes = [as_change(row) for row in await changes_of(ctx, language_id)]
    changed = 0
    lexicon = list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language_id).order_by(LexemeRow.id)))
    taken = {lexeme.word_key for lexeme in lexicon}
    for lexeme in lexicon:
        if lexeme.register in FIXED_REGISTERS:
            continue
        if lexeme.proto_word is None:
            lexeme.proto_word = lexeme.word
        form = derive(lexeme.proto_word, changes, vowels)
        key = lexeme_key(form)
        if form == lexeme.word or key in taken:
            continue
        taken.add(key)
        lexeme.word = form
        changed += 1
    await ctx.session.flush()
    return changed


async def inherit(ctx: TickContext, parent_id: int, child_id: int) -> int:
    rows = await changes_of(ctx, parent_id)
    for row in rows:
        ctx.session.add(
            SoundChangeRow(
                language_entity_id=child_id,
                kind=row.kind,
                source=row.source,
                target=row.target,
                environment=row.environment,
                cause=SoundChangeCause.INHERITED,
                position=row.position,
                epoch=row.epoch,
                locked=[],
            )
        )
    protos = {
        lexeme.meaning: lexeme.proto_word or lexeme.word
        for lexeme in await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == parent_id))
    }
    for lexeme in await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == child_id)):
        if lexeme.meaning in protos:
            lexeme.proto_word = protos[lexeme.meaning]
    await ctx.session.flush()
    return len(rows)


async def scholars_of(ctx: TickContext, tongues: list[int]) -> list[EntityRow]:
    communities = sorted({community for tongue in tongues for community in await speakers(ctx.session, tongue)})
    if not communities:
        return []
    learned = select(SkillRow.holder_node_id).where(SkillRow.skill == SkillKind.LANGUAGES, SkillRow.level >= ctx.rules.sound_changes.reconstruct_skill)
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id.in_(learned),
            await present_among(ctx.session, communities),
        )
        .order_by(EntityRow.id)
    )
    return [row for row in found if not held(row.id)]


async def reconstruct(ctx: TickContext, tally: SoundTally) -> None:
    table = ctx.rules.sound_changes
    for parent in await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE).order_by(EntityRow.id)):
        if held(parent.id) or not await has_flag(ctx.session, parent.id, EntityFlag.DEAD_LANGUAGE):
            continue
        daughters = [
            row.entity_id
            for row in await ctx.session.scalars(select(LanguageProfileRow).where(LanguageProfileRow.parent_language_id == parent.id))
            if row.entity_id != parent.id
        ]
        if len(daughters) < SHORTEST:
            continue
        scholars = await scholars_of(ctx, daughters)
        if not scholars or not ctx.rng(f"sound.reconstruct.{parent.id}.{ctx.epoch}").chance(table.reconstruct_pct):
            continue
        known = set(await ctx.session.scalars(select(LexemeRow.meaning).where(LexemeRow.language_entity_id == parent.id)))
        first = {row.meaning: row for row in await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == daughters[0]))}
        second = {row.meaning: row for row in await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == daughters[1]))}
        shared = sorted(meaning for meaning in set(first) & set(second) if meaning not in known)
        if not shared:
            continue
        meaning = shared[0]
        source = first[meaning]
        word = source.proto_word or source.word
        ctx.session.add(
            LexemeRow(
                language_entity_id=parent.id,
                word=word,
                meaning=meaning,
                part_of_speech=source.part_of_speech,
                etymology=f"reconstructed by {scholars[0].name} from {source.word} and {second[meaning].word}",
                added_by_kind=ActorKind.MORTAL,
                added_by_node_id=scholars[0].id,
                epoch=ctx.epoch,
                proto_word=word,
                register=WordRegister.ARCHAIC,
            )
        )
        tally.reconstructed += 1


async def shift_sounds(ctx: TickContext, tally: SoundTally) -> None:
    table = ctx.rules.sound_changes
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        if tally.changes >= table.per_epoch:
            break
        if held(language.id) or await has_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE):
            continue
        await acquire(ctx, language, tally)
    await reconstruct(ctx, tally)
    await ctx.session.flush()
