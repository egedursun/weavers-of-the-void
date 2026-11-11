from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.tongues import (
    DecipherView,
    DivineTongueView,
    MeaningShiftView,
    NodeTonguesView,
    PolicyView,
    ScriptView,
    SoundChangeView,
    TongueGrammarView,
    TongueMechanicsView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.tongues import (
    DecipherWorkRow,
    DivineTongueRow,
    LanguageGrammarRow,
    LanguagePolicyRow,
    MeaningShiftRow,
    ScriptRow,
    SoundChangeRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.tongues import LanguageModality, LanguageStage

router = APIRouter(tags=["tongues"])
NodeId = Annotated[int, Path(ge=1)]
LINEAGE_DEPTH = 12


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def script_views(session: AsyncSession, rows: list[ScriptRow]) -> list[ScriptView]:
    refs = await refs_for(session, [row.origin_language_id for row in rows])
    return [
        ScriptView(
            id=row.id,
            name=row.name,
            system=row.system,
            parent_script_id=row.parent_script_id,
            origin_language=at(refs, row.origin_language_id),
            signs=row.signs,
            cause=row.cause,
            epoch=row.epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def lineage_of(session: AsyncSession, script_id: int | None) -> list[ScriptRow]:
    chain: list[ScriptRow] = []
    seen: set[int] = set()
    while script_id is not None and script_id not in seen and len(chain) < LINEAGE_DEPTH:
        seen.add(script_id)
        row = await session.get(ScriptRow, script_id)
        if row is None:
            break
        chain.append(row)
        script_id = row.parent_script_id
    return chain


async def policy_views(session: AsyncSession, rows: list[LanguagePolicyRow]) -> list[PolicyView]:
    refs = await refs_for(session, [value for row in rows for value in (row.holder_entity_id, row.language_entity_id)])
    return [
        PolicyView(
            holder=at(refs, row.holder_entity_id),
            language=at(refs, row.language_entity_id),
            policy=row.policy,
            strength=row.strength,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def divine_view(session: AsyncSession, row: DivineTongueRow | None) -> DivineTongueView | None:
    if row is None:
        return None
    refs = await refs_for(session, [row.god_node_id, row.language_entity_id])
    return DivineTongueView(god=at(refs, row.god_node_id), language=at(refs, row.language_entity_id), since_epoch=row.since_epoch, locked=list(row.locked))


async def shift_views(session: AsyncSession, language_id: int) -> list[MeaningShiftView]:
    rows = list(
        await session.execute(
            select(MeaningShiftRow, LexemeRow.word)
            .join(LexemeRow, LexemeRow.id == MeaningShiftRow.lexeme_id)
            .where(LexemeRow.language_entity_id == language_id)
            .order_by(MeaningShiftRow.epoch.desc(), MeaningShiftRow.id.desc())
        )
    )
    absorbed_ids = [shift.replaced_by_id for shift, _ in rows if shift.replaced_by_id is not None]
    absorbed = dict((await session.execute(select(LexemeRow.id, LexemeRow.word).where(LexemeRow.id.in_(absorbed_ids)))).all()) if absorbed_ids else {}
    refs = await refs_for(session, [shift.cause_node_id for shift, _ in rows])
    return [
        MeaningShiftView(
            id=shift.id,
            lexeme_id=shift.lexeme_id,
            word=word,
            shift=shift.shift,
            old_meaning=shift.old_meaning,
            new_meaning=shift.new_meaning,
            absorbed_word=absorbed.get(shift.replaced_by_id) if shift.replaced_by_id is not None else None,
            cause=at(refs, shift.cause_node_id),
            epoch=shift.epoch,
        )
        for shift, word in rows
    ]


async def mechanics_of(session: AsyncSession, language_id: int) -> TongueMechanicsView:
    profile = await session.get(LanguageProfileRow, language_id)
    grammar = await session.get(LanguageGrammarRow, language_id)
    work = await session.get(DecipherWorkRow, language_id)
    changes = await session.scalars(
        select(SoundChangeRow).where(SoundChangeRow.language_entity_id == language_id).order_by(SoundChangeRow.position, SoundChangeRow.id)
    )
    policies = list(await session.scalars(select(LanguagePolicyRow).where(LanguagePolicyRow.language_entity_id == language_id)))
    lineage = await script_views(session, await lineage_of(session, profile.script_id if profile is not None else None))
    scholar = await refs_for(session, [work.scholar_entity_id if work is not None else None])
    return TongueMechanicsView(
        modality=profile.modality if profile is not None else LanguageModality.VOCAL,
        stage=profile.stage if profile is not None else LanguageStage.NATURAL,
        writing_system=profile.writing_system if profile is not None else None,
        script=lineage[0] if lineage else None,
        lineage=lineage,
        grammar=TongueGrammarView.model_validate(grammar) if grammar is not None else None,
        changes=[SoundChangeView.model_validate(row) for row in changes],
        decipher=DecipherView(
            progress=work.progress,
            corpus=work.corpus,
            bilingual=work.bilingual,
            errors=work.errors,
            scholar=at(scholar, work.scholar_entity_id),
            started_epoch=work.started_epoch,
            updated_epoch=work.updated_epoch,
            locked=list(work.locked),
        )
        if work is not None
        else None,
        policies=await policy_views(session, policies),
        shifts=await shift_views(session, language_id),
        sacred_to=await divine_view(session, await session.scalar(select(DivineTongueRow).where(DivineTongueRow.language_entity_id == language_id))),
    )


@router.get("/tongues/of/{node_id}", response_model=NodeTonguesView)
async def node_tongues(services: ServicesDep, node_id: NodeId) -> NodeTonguesView:
    async with reader(services) as session:
        refs = await node_refs(session, [node_id])
        if node_id not in refs:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        is_language = entity is not None and entity.entity_type is EntityType.LANGUAGE
        held = list(await session.scalars(select(LanguagePolicyRow).where(LanguagePolicyRow.holder_entity_id == node_id)))
        divine = select(DivineTongueRow.language_entity_id)
        known = await session.scalars(
            select(SkillRow.subject_node_id).where(
                SkillRow.holder_node_id == node_id, SkillRow.skill == SkillKind.LANGUAGES, SkillRow.subject_node_id.in_(divine)
            )
        )
        known_refs = await refs_for(session, list(known))
        return NodeTonguesView(
            node=refs[node_id],
            language=await mechanics_of(session, node_id) if is_language else None,
            held_policies=await policy_views(session, held),
            divine_tongue=await divine_view(session, await session.get(DivineTongueRow, node_id)),
            known_divine=list(known_refs.values()),
        )


@router.get("/tongues/scripts", response_model=list[ScriptView])
async def all_scripts(services: ServicesDep) -> list[ScriptView]:
    async with reader(services) as session:
        return await script_views(session, list(await session.scalars(select(ScriptRow).order_by(ScriptRow.id))))
