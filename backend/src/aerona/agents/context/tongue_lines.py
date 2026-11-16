from sqlalchemy import func, select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import agree, an, several, spoken
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.tongues import DecipherWorkRow, DivineTongueRow, LanguagePolicyRow
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.tongues import LanguageModality, LanguageStage
from aerona.engine.tongues.modality import own_tongue


async def son_tongue_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    row = await session.get(DivineTongueRow, son.id)
    language = await session.get(EntityRow, row.language_entity_id) if row is not None else None
    if language is None:
        return []
    words = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == language.id)) or 0)
    knowers = int(
        await session.scalar(select(func.count()).select_from(SkillRow).where(SkillRow.skill == SkillKind.LANGUAGES, SkillRow.subject_node_id == language.id))
        or 0
    )
    return [
        f"Your sacred tongue is {language.name} ({several(words, 'word', 'words')}); "
        f"{several(knowers, 'mortal', 'mortals')} {agree(knowers, 'has', 'have')} learned it"
    ]


async def mortal_tongue_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    tongue = await own_tongue(session, me)
    profile = await session.get(LanguageProfileRow, tongue.id) if tongue is not None else None
    if tongue is not None and profile is not None:
        written = f"written in {an(profile.writing_system.value)} script" if profile.writing_system is not None else "unwritten"
        kind = "" if profile.modality is LanguageModality.VOCAL else f" ({spoken(profile.modality)})"
        stage = "" if profile.stage is LanguageStage.NATURAL else f", {an(profile.stage.value)}"
        found.append(f"your people speak {tongue.name}{kind}{stage}, {written}")
        for policy in await session.scalars(
            select(LanguagePolicyRow).where(LanguagePolicyRow.language_entity_id == tongue.id).order_by(LanguagePolicyRow.holder_entity_id)
        ):
            holder = await session.get(EntityRow, policy.holder_entity_id)
            if holder is not None:
                found.append(f"{holder.name} holds {tongue.name} {spoken(policy.policy)} ({policy.strength})")
    sacred = select(DivineTongueRow.language_entity_id)
    for language_id in await session.scalars(
        select(SkillRow.subject_node_id).where(SkillRow.holder_node_id == me.id, SkillRow.skill == SkillKind.LANGUAGES, SkillRow.subject_node_id.in_(sacred))
    ):
        language = await session.get(EntityRow, language_id)
        if language is not None:
            found.append(f"you know words of {language.name}, a sacred tongue; rites you cast in its god's name are stronger")
    for work in await session.scalars(select(DecipherWorkRow).where(DecipherWorkRow.scholar_entity_id == me.id)):
        language = await session.get(EntityRow, work.language_entity_id)
        if language is not None:
            found.append(f"you work at the dead script of {language.name} ({work.progress} of 100, {several(work.errors, 'misreading', 'misreadings')})")
    return found
