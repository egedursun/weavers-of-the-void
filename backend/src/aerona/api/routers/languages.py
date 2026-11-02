from fastapi import APIRouter, Path
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.translator import translate
from aerona.api.actions import Alias, mount_all
from aerona.api.background import require_llm
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.api.schemas.records import EntitySummary, NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import PartOfSpeech, WritingSystem
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.phonology import LanguageSignature
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.language.alphabet import fold_word
from aerona.language.generator import NameKind
from aerona.language.lexicon import Cognate, LexiconEntry, cognates
from aerona.prompts.schemas.council import TranslationOutput
from aerona.services.images.records import cover_of
from aerona.services.name_report import NameReport, name_report

router = APIRouter(tags=["languages"])

ALIASES = (Alias("POST", "/languages/{language_id}/words", "language:words", path_fields={"language_id": "language_id"}),)

TRANSLATE_MAX_LENGTH = 2000
SAMPLE_SEED = "language_sample"
SAMPLE_PREVIEW_MAX = 30
SAMPLE_SALT_MAX = 40
SAMPLE_KINDS = (NameKind.PERSON, NameKind.PLACE, NameKind.PEOPLE)
VISIBLE = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.DESTROYED)


class Lexeme(ApiModel):
    id: int
    word: str
    meaning: str
    part_of_speech: PartOfSpeech | None
    etymology: str | None
    example: str | None
    added_by_kind: ActorKind
    added_by: NodeRef | None
    epoch: int


class LanguageView(ApiModel):
    language: EntitySummary
    description: str
    cover: str | None
    speakers: list[NodeRef]
    words: list[Lexeme]
    word_total: int


class LanguageNode(ApiModel):
    language: EntitySummary
    writing_system: WritingSystem | None
    parent_language_id: int | None
    words: int
    speakers: int
    sample_names: list[str]
    signature: LanguageSignature | None
    alphabet: list[str]
    cognates: list[Cognate]


class SampleNamesRequest(RequestModel):
    count: int = Field(default=6, ge=1, le=SAMPLE_PREVIEW_MAX)
    salt: str = Field(default="", max_length=SAMPLE_SALT_MAX)


class SampleNames(ApiModel):
    language_id: int
    names: list[str]


class KnowledgeView(ApiModel):
    knowledge: EntitySummary
    description: str
    branch: KnowledgeBranch | None
    level: int | None
    spread: int | None
    knowers: list[NodeRef]
    inventor: NodeRef | None
    prerequisites: list[NodeRef]


class TranslateRequest(RequestModel):
    text: str = Field(min_length=1, max_length=TRANSLATE_MAX_LENGTH)


async def bonded_to(session: AsyncSession, kind: BondKind, target_ids: list[int]) -> dict[int, list[int]]:
    rows = await session.execute(
        select(BondRow.target_node_id, BondRow.source_node_id).where(
            BondRow.kind == kind, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(target_ids)
        )
    )
    found: dict[int, list[int]] = {}
    for target, source in rows:
        found.setdefault(target, []).append(source)
    return found


async def prerequisites_of(session: AsyncSession, knowledge_ids: list[int]) -> dict[int, list[int]]:
    rows = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(knowledge_ids), EntityRow.entity_type == EntityType.KNOWLEDGE)
        .order_by(BondRow.id)
    )
    found: dict[int, list[int]] = {}
    for source, target in rows:
        found.setdefault(source, []).append(target)
    return found


@router.get("/languages", response_model=list[LanguageView])
async def list_languages(services: ServicesDep) -> list[LanguageView]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        languages = list(
            await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status.in_(VISIBLE)).order_by(EntityRow.id))
        )
        speakers = await bonded_to(session, BondKind.SPEAKS, [language.id for language in languages])
        views: list[LanguageView] = []
        for language in languages:
            words = list(
                await session.scalars(
                    select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id).limit(rules.server.lexicon_words_per_language)
                )
            )
            total = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == language.id)) or 0)
            refs = await node_refs(session, [*speakers.get(language.id, []), *(word.added_by_node_id for word in words if word.added_by_node_id)])
            views.append(
                LanguageView(
                    language=EntitySummary.model_validate(language),
                    description=language.description,
                    cover=await cover_of(session, language.id),
                    speakers=[refs[node] for node in speakers.get(language.id, []) if node in refs],
                    words=[
                        Lexeme(
                            id=word.id,
                            word=word.word,
                            meaning=word.meaning,
                            part_of_speech=word.part_of_speech,
                            etymology=word.etymology,
                            example=word.example,
                            added_by_kind=word.added_by_kind,
                            added_by=refs.get(word.added_by_node_id) if word.added_by_node_id else None,
                            epoch=word.epoch,
                        )
                        for word in words
                    ],
                    word_total=total,
                )
            )
        return views


async def lexicon_of(session: AsyncSession, language_id: int) -> list[LexiconEntry]:
    rows = await session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language_id).order_by(LexemeRow.id))
    return [LexiconEntry(word=row.word, meaning=row.meaning) for row in rows]


async def sample_names(namer: Namer, language: EntityRow, count: int, salt: str = "") -> list[str]:
    names: list[str] = []
    for index in range(count):
        name = await namer.from_language(language, seed_of(SAMPLE_SEED, language.id, salt, index), SAMPLE_KINDS[index % len(SAMPLE_KINDS)])
        if name is not None:
            names.append(name)
    return names


@router.get("/languages/tree", response_model=list[LanguageNode])
async def language_tree(services: ServicesDep) -> list[LanguageNode]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        rows = await session.execute(
            select(EntityRow, LanguageProfileRow)
            .join(LanguageProfileRow, LanguageProfileRow.entity_id == EntityRow.id, isouter=True)
            .where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status.in_(VISIBLE))
            .order_by(EntityRow.id)
        )
        pairs = list(rows)
        namer = Namer(session, rules, persist=False)
        ids = [language.id for language, _ in pairs]
        grouped = await session.execute(
            select(LexemeRow.language_entity_id, func.count()).where(LexemeRow.language_entity_id.in_(ids)).group_by(LexemeRow.language_entity_id)
        )
        counts = {language_id: int(count) for language_id, count in grouped}
        speakers = await bonded_to(session, BondKind.SPEAKS, ids)
        lexicons = {language_id: await lexicon_of(session, language_id) for language_id in ids}
        nodes: list[LanguageNode] = []
        for language, profile in pairs:
            parent = profile.parent_language_id if profile else None
            letters = frozenset(fold_word(profile.alphabet)) if profile and profile.alphabet else await namer.world_alphabet(language.world_id)
            nodes.append(
                LanguageNode(
                    language=EntitySummary.model_validate(language),
                    writing_system=profile.writing_system if profile else None,
                    parent_language_id=parent,
                    words=int(counts.get(language.id, 0)),
                    speakers=len(speakers.get(language.id, [])),
                    sample_names=await sample_names(namer, language, rules.server.language_sample_names),
                    signature=(await namer.voice(language)).signature,
                    alphabet=sorted(letters or ()),
                    cognates=cognates(lexicons[language.id], lexicons.get(parent, []), rules) if parent is not None else [],
                )
            )
        return nodes


@router.get("/languages/dialect-fit", response_model=NameReport)
async def dialect_fit(services: ServicesDep) -> NameReport:
    async with reader(services) as session:
        return await name_report(session, await world_rules(services, session))


@router.post("/languages/{language_id}/sample-names", response_model=SampleNames)
async def preview_sample_names(request: SampleNamesRequest, services: ServicesDep, language_id: int = Path(ge=1)) -> SampleNames:
    async with reader(services) as session:
        language = await session.get(EntityRow, language_id)
        if language is None or language.entity_type is not EntityType.LANGUAGE:
            raise NotFoundError("No such language.")
        namer = Namer(session, await world_rules(services, session), persist=False)
        return SampleNames(language_id=language_id, names=await sample_names(namer, language, request.count, request.salt))


@router.post("/languages/{language_id}/translate", response_model=TranslationOutput)
async def translate_text(request: TranslateRequest, services: ServicesDep, language_id: int = Path(ge=1)) -> TranslationOutput:
    require_llm(services, "Translation")
    return await translate(services.agents, language_id, request.text)


@router.get("/knowledge", response_model=list[KnowledgeView])
async def list_knowledge(services: ServicesDep) -> list[KnowledgeView]:
    async with reader(services) as session:
        rows = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
        knowers = await bonded_to(session, BondKind.KNOWS, [row.id for row in rows])
        bases = await prerequisites_of(session, [row.id for row in rows])
        refs = await node_refs(
            session,
            [
                *(node for ids in knowers.values() for node in ids),
                *(node for ids in bases.values() for node in ids),
                *(row.maker_entity_id or row.creator_son_id or 0 for row in rows),
            ],
        )
        return [
            KnowledgeView(
                knowledge=EntitySummary.model_validate(row),
                description=row.description,
                branch=row.knowledge_branch,
                level=getattr(row.stats, "level", None),
                spread=getattr(row.stats, "spread", None),
                knowers=[refs[node] for node in knowers.get(row.id, []) if node in refs],
                inventor=refs.get(row.maker_entity_id or row.creator_son_id or 0),
                prerequisites=[refs[node] for node in bases.get(row.id, []) if node in refs],
            )
            for row in rows
        ]


mount_all(router, ALIASES, tag="languages")
