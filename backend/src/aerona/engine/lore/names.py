import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.discovery import EpithetRow, NameExonymRow, NameMeaningRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.lore import LexemeRow, lexeme_key
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import TreatyBreachRow, TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.renown import DeedRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, PartOfSpeech
from aerona.domain.enums.culture import LanguageRegister
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.polity import TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.lore.language import register_barrier, register_tongues
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.services.community_relations import change_relation
from aerona.engine.tongues.grammar import compounds, head_first, misread_factor
from aerona.language.generator import NameKind

TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
GLOSS_JOIN = "-"


COMPOUND_LENGTH = 6


async def tongue_of(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    found = await spoken_language(session, entity.id)
    if found is None and entity.location_id is not None:
        found = await spoken_language(session, entity.location_id)
    return found


async def lexicon(session: AsyncSession, language_id: int) -> list[LexemeRow]:
    rows = await session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language_id).order_by(LexemeRow.id))
    return sorted(rows, key=lambda row: (-len(row.word), row.id))


def split(name: str, words: list[LexemeRow]) -> list[LexemeRow]:
    text = name.casefold()
    found: list[tuple[int, LexemeRow]] = []
    taken: set[int] = set()
    for row in words:
        key = row.word.casefold()
        if len(key) < 2:
            continue
        start = text.find(key)
        while start >= 0:
            span = set(range(start, start + len(key)))
            if not span & taken:
                found.append((start, row))
                taken |= span
                break
            start = text.find(key, start + 1)
    return [row for _, row in sorted(found, key=lambda item: item[0])]


async def feature_of(session: AsyncSession, entity: EntityRow, atlas: RegionAtlas) -> str:
    if entity.entity_type in {EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT}:
        region = atlas.top_region(entity.id)
        land = await session.get(RegionEnvironmentRow, region) if region is not None else None
        if land is not None and land.dominant_terrain is not None:
            return land.dominant_terrain.value.replace("_", " ")
    if entity.entity_type is EntityType.MORTAL and entity.social_class is not None:
        return entity.social_class.value.replace("_", " ")
    return ENTITY_TYPES[entity.entity_type].noun


async def coin(ctx: TickContext, language: EntityRow, word: str, meaning: str) -> LexemeRow:
    found = await ctx.session.scalar(select(LexemeRow).where(LexemeRow.language_entity_id == language.id, LexemeRow.word_key == lexeme_key(word)).limit(1))
    if found is not None:
        return found
    row = LexemeRow(
        language_entity_id=language.id,
        word=word,
        meaning=meaning,
        part_of_speech=PartOfSpeech.NOUN,
        etymology=None,
        example=None,
        added_by_kind=ActorKind.ENGINE,
        added_by_node_id=None,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def coined(ctx: TickContext, language: EntityRow, token: str, entity: EntityRow, feature: str) -> list[LexemeRow]:
    compound = await compounds(ctx.session, language.id) and len(token) >= COMPOUND_LENGTH
    if compound and ctx.rng(f"name.compound.{entity.id}").chance(ctx.rules.grammar.compound_pct):
        half = len(token) // 2
        kind_word = entity.entity_type.value.replace("_", " ")
        head, modifier = (token[:half], token[half:]) if await head_first(ctx.session, language.id) else (token[half:], token[:half])
        return [await coin(ctx, language, modifier, feature), await coin(ctx, language, head, kind_word)]
    return [await coin(ctx, language, token, feature)]


async def give_meanings(ctx: TickContext) -> int:
    limit = ctx.rules.name_meanings.named_per_epoch
    named = select(NameMeaningRow.node_id)
    candidates = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(named)).order_by(EntityRow.id.desc()).limit(limit)
    )
    atlas = await RegionAtlas.load(ctx.session)
    given = 0
    for entity in list(candidates):
        if held(entity.id):
            continue
        language = await tongue_of(ctx.session, entity)
        morphemes: list[str] = []
        glosses: list[str] = []
        if language is not None:
            parts = split(entity.name, await lexicon(ctx.session, language.id))
            if not parts and not held(language.id):
                token = next(iter(TOKEN.findall(entity.name)), None)
                if token is not None:
                    parts = await coined(ctx, language, token, entity, await feature_of(ctx.session, entity, atlas))
            morphemes = [row.word for row in parts]
            glosses = [row.meaning for row in parts]
        ctx.session.add(
            NameMeaningRow(
                node_id=entity.id,
                language_entity_id=language.id if language is not None else None,
                name=entity.name,
                gloss=GLOSS_JOIN.join(glosses),
                morphemes=morphemes,
                epoch=ctx.epoch,
                locked=[],
            )
        )
        given += 1
    await ctx.session.flush()
    return given


async def contact_tongues(ctx: TickContext, entity: EntityRow, own: int | None) -> list[EntityRow]:
    found: dict[int, EntityRow] = {}
    anchor = entity.id if entity.entity_type in COMMUNITY_TYPES else entity.location_id or entity.id
    for partner in sorted(await trade_partners(ctx.session, anchor)):
        tongue = await spoken_language(ctx.session, partner)
        if tongue is not None and tongue.id != own:
            found.setdefault(tongue.id, tongue)
    return list(found.values())[: ctx.rules.name_meanings.exonym_contacts]


async def translate(ctx: TickContext, meaning: NameMeaningRow, target: EntityRow) -> tuple[str, str]:
    words = {lexeme_key(row.meaning): row.word for row in await lexicon(ctx.session, target.id)}
    glosses = meaning.gloss.split(GLOSS_JOIN) if meaning.gloss else []
    parts = [words.get(lexeme_key(gloss), morpheme) for morpheme, gloss in zip(meaning.morphemes, glosses, strict=False)]
    form = "".join(parts).capitalize() if parts else meaning.name
    return form, meaning.gloss


async def give_exonyms(ctx: TickContext) -> int:
    given = 0
    meanings = await ctx.session.scalars(select(NameMeaningRow).where(NameMeaningRow.epoch == ctx.epoch))
    for meaning in [row for row in meanings if row.morphemes]:
        entity = await ctx.session.get(EntityRow, meaning.node_id)
        if entity is None or held(entity.id):
            continue
        for tongue in await contact_tongues(ctx, entity, meaning.language_entity_id):
            if await ctx.session.get(NameExonymRow, (entity.id, tongue.id)) is not None:
                continue
            form, gloss = await translate(ctx, meaning, tongue)
            ctx.session.add(NameExonymRow(node_id=entity.id, language_entity_id=tongue.id, form=form, gloss=gloss, epoch=ctx.epoch, locked=[]))
            given += 1
    await ctx.session.flush()
    return given


async def give_epithets(ctx: TickContext) -> int:
    threshold = ctx.rules.name_meanings.epithet_renown
    named = select(EpithetRow.mortal_entity_id)
    renowned = await ctx.session.scalars(
        select(MortalProfileRow.entity_id)
        .where(MortalProfileRow.renown >= threshold, MortalProfileRow.entity_id.not_in(named))
        .order_by(MortalProfileRow.entity_id)
    )
    namer = Namer(ctx.session, ctx.rules)
    given = 0
    for mortal_id in list(renowned):
        mortal = await ctx.session.get(EntityRow, mortal_id)
        deed = await ctx.session.scalar(select(DeedRow).where(DeedRow.doer_node_id == mortal_id).order_by(DeedRow.magnitude.desc(), DeedRow.id).limit(1))
        if mortal is None or mortal.status is not EntityStatus.CANON or deed is None or held(mortal_id):
            continue
        meaning = (deed.act.value if deed.act is not None else deed.axis.value).replace("_", " ")
        await entitle(ctx, mortal, meaning, namer)
        given += 1
    await ctx.session.flush()
    return given


async def entitle(ctx: TickContext, mortal: EntityRow, meaning: str, namer: Namer | None = None) -> EpithetRow | None:
    row = await ctx.session.get(EpithetRow, mortal.id)
    if row is not None and "epithet" in row.locked:
        return None
    language = await tongue_of(ctx.session, mortal)
    word = meaning
    if language is not None:
        known = await ctx.session.scalar(select(LexemeRow.word).where(LexemeRow.language_entity_id == language.id, LexemeRow.meaning == meaning).limit(1))
        coined = known or await (namer or Namer(ctx.session, ctx.rules)).from_language(language, seed_of("epithet", mortal.id, meaning), NameKind.GENERAL)
        if coined:
            word = (await coin(ctx, language, coined, meaning)).word
    if row is None:
        row = EpithetRow(mortal_entity_id=mortal.id, locked=[])
        ctx.session.add(row)
    row.epithet, row.gloss, row.deed = word.capitalize(), f"the one of {meaning}", meaning
    row.language_entity_id, row.epoch = language.id if language is not None else None, ctx.epoch
    await note(ctx, f"The world began to call {mortal.name} {word.capitalize()}.", key="names.epithet", ids=[mortal.id], kind=ChronicleKind.CULTURE)
    return row


async def misreadings(ctx: TickContext) -> int:
    table = ctx.rules.name_meanings
    misread = 0
    treaties = list(
        await ctx.session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE).order_by(TreatyProfileRow.treaty_entity_id))
    )
    sworn: dict[int, list[int]] = {profile.treaty_entity_id: [] for profile in treaties}
    for treaty_id, party_id in await ctx.session.execute(
        select(TreatyPartyRow.treaty_entity_id, TreatyPartyRow.party_node_id)
        .where(TreatyPartyRow.treaty_entity_id.in_(list(sworn)))
        .order_by(TreatyPartyRow.treaty_entity_id, TreatyPartyRow.party_node_id)
    ):
        sworn[treaty_id].append(party_id)
    readings: dict[tuple[int, int], tuple[float, float]] = {}
    for profile in treaties:
        parties = sworn[profile.treaty_entity_id]
        if len(parties) < 2 or held(profile.treaty_entity_id) or any(held(party) for party in parties[:2]):
            continue
        first, second = parties[0], parties[1]
        if (first, second) not in readings:
            barrier = await register_barrier(ctx.session, ctx.rules, first, second, ctx.epoch, ours=LanguageRegister.COURT, theirs=LanguageRegister.COURT)
            tongues = (await register_tongues(ctx.session, first, LanguageRegister.COURT), await register_tongues(ctx.session, second, LanguageRegister.COURT))
            readings[(first, second)] = (barrier, await misread_factor(ctx.session, ctx.rules, *tongues))
        understood, gap = readings[(first, second)]
        if not ctx.rng(f"treaty.misread.{profile.treaty_entity_id}.{ctx.epoch}").chance(table.misread_pct * (1 - understood) * gap):
            continue
        clause = await ctx.session.scalar(
            select(TreatyClauseRow.id).where(TreatyClauseRow.treaty_entity_id == profile.treaty_entity_id).order_by(TreatyClauseRow.id).limit(1)
        )
        ctx.session.add(
            TreatyBreachRow(treaty_entity_id=profile.treaty_entity_id, clause_id=clause, breaker_node_id=None, epoch=ctx.epoch, note="a clause was misread")
        )
        for one, other in ((first, second), (second, first)):
            await change_relation(ctx, one, other, -table.misread_relation, MemoryKind.ILL_WILL, note="read the treaty otherwise")
        misread += 1
    return misread


async def names(ctx: TickContext) -> dict[str, int]:
    return {
        "names_given_meaning": await give_meanings(ctx),
        "exonyms": await give_exonyms(ctx),
        "epithets": await give_epithets(ctx),
        "clauses_misread": await misreadings(ctx),
    }
