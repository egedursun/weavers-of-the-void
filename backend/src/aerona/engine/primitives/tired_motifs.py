from collections import Counter, OrderedDict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.names import normalize_name
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import CreationMotifRow, EntityRow
from aerona.db.tables.motifs import MotifOverrideMode, MotifOverrideRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import MotifCategory
from aerona.engine.primitives.motifs import motif_words
from aerona.prompts.contexts.common import MotifShare, TiredImages
from aerona.rules.registry import Rules

PERCENT = 100
PHRASE_SEPARATORS = (" ", "_", "-")


@dataclass(frozen=True)
class TiredMotif:
    key: str
    ratio: float
    pinned: bool = False

    @property
    def percent(self) -> int:
        return round(self.ratio * PERCENT)


def is_phrase(motif: str, category: MotifCategory | None) -> bool:
    return category is MotifCategory.PHRASE or any(separator in motif.strip() for separator in PHRASE_SEPARATORS)


def appears_in(motif: str, canon_text: str) -> bool:
    words = motif_words(motif)
    return bool(words) and " ".join(words) in canon_text


def select_tired(counts: Counter[str], total: int, percent: int, rules: Rules) -> list[TiredMotif]:
    language = rules.language
    if total < language.motif_min_records:
        return []
    floor = max(language.motif_min_repeats, total * percent / PERCENT)
    return [TiredMotif(key, count / total) for key, count in counts.items() if count >= floor]


async def _multi_world(session: AsyncSession) -> bool:
    return int(await session.scalar(select(func.count()).select_from(WorldRow)) or 0) > 1


async def canon_text(session: AsyncSession, world_id: int | None) -> str:
    cosmos = await CosmosRepository(session).get()
    parts: list[str] = []
    if cosmos is not None:
        parts.extend([cosmos.cosmology, cosmos.seed_idea, cosmos.tone])
    creator = await CosmosRepository(session).creator()
    if creator is not None and creator.epic is not None:
        parts.extend([creator.epic.title, creator.epic.body, creator.epic.verse])
    if world_id is not None:
        world = await session.get(WorldRow, world_id)
        if world is not None:
            parts.extend([world.cosmology or "", world.description or ""])
    laws = select(EntityRow).where(EntityRow.entity_type.in_([EntityType.NATURAL_LAW, EntityType.LAW]), EntityRow.status == EntityStatus.CANON)
    if world_id is not None:
        laws = laws.where(EntityRow.world_id == world_id)
    parts.extend(f"{law.name} {law.description}" for law in await session.scalars(laws))
    return normalize_name(" ".join(part for part in parts if part))


async def _recent_tags(session: AsyncSession, rules: Rules, world_id: int | None) -> tuple[Counter[str], Counter[str], int, int]:
    recent = select(CreationMotifRow.entity_id).group_by(CreationMotifRow.entity_id)
    if world_id is not None:
        recent = recent.where(CreationMotifRow.world_id == world_id)
    ordered = recent.order_by(func.max(CreationMotifRow.epoch).desc(), CreationMotifRow.entity_id.desc()).limit(rules.language.motif_window)
    recent_ids = list(await session.scalars(ordered))
    singles: Counter[str] = Counter()
    phrases: Counter[str] = Counter()
    single_docs: set[int] = set()
    phrase_docs: set[int] = set()
    if recent_ids:
        columns = select(CreationMotifRow.entity_id, CreationMotifRow.motif, CreationMotifRow.category)
        rows = await session.execute(columns.where(CreationMotifRow.entity_id.in_(recent_ids)))
        seen: set[tuple[int, str]] = set()
        for entity_id, motif, category in rows:
            key = " ".join(motif_words(motif))
            if not key or (entity_id, key) in seen:
                continue
            seen.add((entity_id, key))
            if is_phrase(motif, category):
                phrases[key] += 1
                phrase_docs.add(entity_id)
            else:
                singles[key] += 1
                single_docs.add(entity_id)
    return singles, phrases, max(len(single_docs), len(recent_ids)), max(len(phrase_docs), len(recent_ids))


async def overrides(session: AsyncSession, world_id: int | None) -> dict[str, MotifOverrideMode]:
    statement = select(MotifOverrideRow).where(MotifOverrideRow.world_id.is_(None) if world_id is None else MotifOverrideRow.world_id == world_id)
    return {row.motif: row.mode for row in await session.scalars(statement)}


async def _epoch_tags(session: AsyncSession, world_id: int | None, first: int, last: int) -> tuple[Counter[str], int]:
    statement = select(CreationMotifRow.entity_id, CreationMotifRow.motif).where(CreationMotifRow.epoch >= first, CreationMotifRow.epoch <= last)
    if world_id is not None:
        statement = statement.where(CreationMotifRow.world_id == world_id)
    counts: Counter[str] = Counter()
    documents: set[int] = set()
    seen: set[tuple[int, str]] = set()
    for entity_id, motif in await session.execute(statement):
        key = " ".join(motif_words(motif))
        documents.add(entity_id)
        if key and (entity_id, key) not in seen:
            seen.add((entity_id, key))
            counts[key] += 1
    return counts, len(documents)


def rising_tags(recent: Counter[str], recent_total: int, earlier: Counter[str], earlier_total: int, rules: Rules) -> list[TiredMotif]:
    language = rules.language
    if not recent_total:
        return []
    found = []
    for key, count in recent.items():
        share = count / recent_total
        before = earlier[key] / earlier_total if earlier_total else 0.0
        if count < language.motif_min_repeats or share * PERCENT < language.motif_rising_min_pct:
            continue
        if before == 0 or share * PERCENT >= before * language.motif_rising_ratio_pct:
            found.append(TiredMotif(key, share))
    return found


async def rising(session: AsyncSession, rules: Rules, world_id: int | None) -> list[TiredMotif]:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return []
    language = rules.language
    last = cosmos.epoch - 1
    split = last - language.motif_recent_epochs
    recent, recent_total = await _epoch_tags(session, world_id, split + 1, last)
    earlier, earlier_total = await _epoch_tags(session, world_id, split - language.motif_previous_epochs + 1, split)
    return rising_tags(recent, recent_total, earlier, earlier_total, rules)


async def cosmos_wide(session: AsyncSession, rules: Rules) -> list[TiredMotif]:
    worlds = list(await session.scalars(select(WorldRow.id)))
    if len(worlds) < 2:
        return []
    spread: Counter[str] = Counter()
    ratio: dict[str, float] = {}
    for world in worlds:
        singles, _, single_total, _ = await _recent_tags(session, rules, world)
        for motif in select_tired(singles, single_total, rules.language.motif_threshold_pct, rules):
            spread[motif.key] += 1
            ratio[motif.key] = max(ratio.get(motif.key, 0.0), motif.ratio)
    return [TiredMotif(key, ratio[key]) for key, count in spread.items() if count * PERCENT >= len(worlds) * rules.language.motif_spread_world_pct]


async def measure(session: AsyncSession, rules: Rules, world_id: int | None) -> list[TiredMotif]:
    singles, phrases, single_total, phrase_total = await _recent_tags(session, rules, world_id)
    tired = select_tired(singles, single_total, rules.language.motif_threshold_pct, rules)
    tired += select_tired(phrases, phrase_total, rules.language.motif_pair_threshold_pct, rules)
    known = {motif.key for motif in tired}
    for extra in [*await rising(session, rules, world_id), *await cosmos_wide(session, rules)]:
        if extra.key not in known:
            known.add(extra.key)
            tired.append(extra)
    exempt = await canon_text(session, world_id)
    manual = await overrides(session, world_id)
    kept = [motif for motif in tired if not appears_in(motif.key, exempt) and manual.get(motif.key) is not MotifOverrideMode.ALLOWED]
    present = {motif.key for motif in kept}
    kept += [TiredMotif(key, 1.0, pinned=True) for key, mode in manual.items() if mode is MotifOverrideMode.PINNED and key not in present]
    kept.sort(key=lambda motif: (not motif.pinned, -motif.ratio, motif.key))
    return kept[: rules.language.motifs_in_prompt]


class MotifCache:
    def __init__(self) -> None:
        self._entries: OrderedDict[tuple[int | None, int, int], list[TiredMotif]] = OrderedDict()

    def clear(self) -> None:
        self._entries.clear()

    async def tired(self, session: AsyncSession, rules: Rules, world_id: int | None) -> list[TiredMotif]:
        cosmos = await CosmosRepository(session).get()
        epoch = cosmos.epoch if cosmos is not None else 0
        marker = int(await session.scalar(select(func.count()).select_from(CreationMotifRow)) or 0)
        marker += int(await session.scalar(select(func.count()).select_from(MotifOverrideRow)) or 0)
        key = (world_id, epoch, marker)
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]
        found = await measure(session, rules, world_id)
        self._entries[key] = found
        while len(self._entries) > rules.language.motif_cache_per_world:
            self._entries.popitem(last=False)
        return found

    async def for_world(self, session: AsyncSession, rules: Rules, world_id: int | None) -> list[TiredMotif]:
        global_list = await self.tired(session, rules, None)
        if world_id is None or not await _multi_world(session):
            return global_list
        own = await self.tired(session, rules, world_id)
        merged: dict[str, TiredMotif] = {motif.key: motif for motif in global_list}
        for motif in own:
            merged.setdefault(motif.key, motif)
        return sorted(merged.values(), key=lambda motif: (not motif.pinned, -motif.ratio, motif.key))[: rules.language.motifs_in_prompt]

    async def foreign_images(self, session: AsyncSession, rules: Rules, world_id: int | None) -> list[str]:
        cosmos = await CosmosRepository(session).get()
        primary = cosmos.primary_world_id if cosmos is not None else None
        if world_id is None or primary is None or world_id == primary or not await _multi_world(session):
            return []
        own_canon = await canon_text(session, world_id)
        main = await self.tired(session, rules, primary)
        return [motif.key for motif in main if not (words := motif_words(motif.key)) or words[0] not in own_canon]

    async def context(self, session: AsyncSession, rules: Rules, world_id: int | None) -> TiredImages:
        motifs = await self.for_world(session, rules, world_id)
        return TiredImages(
            motifs=[MotifShare(key=motif.key, percent=motif.percent) for motif in motifs],
            foreign_images=await self.foreign_images(session, rules, world_id),
        )


async def set_override(session: AsyncSession, world_id: int | None, motif: str, mode: MotifOverrideMode | None) -> None:
    key = " ".join(motif_words(motif))
    if not key:
        raise ValidationFailedError("A motif needs a word.")
    statement = select(MotifOverrideRow).where(
        MotifOverrideRow.motif == key, MotifOverrideRow.world_id.is_(None) if world_id is None else MotifOverrideRow.world_id == world_id
    )
    existing = await session.scalar(statement)
    if mode is None:
        if existing is not None:
            await session.delete(existing)
    elif existing is None:
        session.add(MotifOverrideRow(world_id=world_id, motif=key, mode=mode))
    else:
        existing.mode = mode
    await session.flush()
