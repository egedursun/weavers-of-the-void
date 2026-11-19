from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.tables.tongues import DivineTongueRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.tongues import LanguageStage, WordRegister
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record as record_incident
from aerona.language.generator import NameKind

DIVINE_SUBTYPE = "divine tongue"
TONGUE_POWER = 5
FIRST_LEVEL = 20


@dataclass
class TongueTally:
    given: int = 0
    taught: int = 0


async def tongue_of(session: AsyncSession, god_id: int | None) -> int | None:
    row = await session.get(DivineTongueRow, god_id) if god_id is not None else None
    return row.language_entity_id if row is not None else None


async def knows(session: AsyncSession, mortal_id: int, language_id: int | None) -> bool:
    if language_id is None:
        return False
    found = await session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill == SkillKind.LANGUAGES, SkillRow.subject_node_id == language_id)
    )
    return bool(found)


async def rite_factor(session: AsyncSession, percent: int, caster_id: int, god_id: int | None) -> float:
    return 1 + percent / PERCENT if await knows(session, caster_id, await tongue_of(session, god_id)) else 1.0


async def meanings_for(ctx: TickContext, son: SonRow) -> list[str]:
    powers = await ctx.session.scalars(select(SonPowerRow.name).where(SonPowerRow.son_id == son.id).order_by(SonPowerRow.slot))
    domains = [domain.value for domain in (son.domain_primary, son.domain_secondary) if domain is not None]
    return list(dict.fromkeys([*domains, *(name.strip() for name in powers if name.strip())]))[: ctx.rules.divine_tongues.words]


async def give_tongue(ctx: TickContext, son: SonRow) -> DivineTongueRow | None:
    existing = await ctx.session.get(DivineTongueRow, son.id)
    if existing is not None:
        return existing
    name = await ctx.session.get(TrueNameRow, son.id)
    language = await ctx.session.get(EntityRow, name.language_node_id) if name is not None and name.language_node_id is not None else None
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        language = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.LANGUAGE,
                name=f"Tongue of {son.name}",
                body=f"The sacred tongue of {son.name}, the language of its true name.",
                stats=LanguageStats(spread=0, complexity=PERCENT // 2, sacredness=PERCENT),
                power=TONGUE_POWER,
                world_id=son.current_world_id,
                subtype=DIVINE_SUBTYPE,
                sacred_to_son_id=son.id,
                pending=False,
            ),
        )
        profile = await language_profile(ctx.session, language)
        profile.stage = LanguageStage.DIVINE
        namer = Namer(ctx.session, ctx.rules)
        for index, meaning in enumerate(await meanings_for(ctx, son)):
            word = await namer.from_language(language, seed_of("divine.word", son.id, index), NameKind.GENERAL)
            if word:
                await add_lexeme(
                    ctx.session,
                    LexemeRow(
                        language_entity_id=language.id,
                        word=word,
                        meaning=meaning,
                        part_of_speech=PartOfSpeech.NOUN,
                        etymology=f"spoken by {son.name}",
                        added_by_kind=ActorKind.SON,
                        added_by_node_id=son.id,
                        epoch=ctx.epoch,
                        register=WordRegister.SACRED,
                    ),
                )
    if name is not None and name.language_node_id is None and "language_node_id" not in name.locked:
        name.language_node_id = language.id
    row = DivineTongueRow(god_node_id=son.id, language_entity_id=language.id, since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def teach(ctx: TickContext, god_id: int, mortal: EntityRow) -> bool:
    language_id = await tongue_of(ctx.session, god_id)
    if language_id is None or held(mortal.id) or await knows(ctx.session, mortal.id, language_id):
        return False
    ctx.session.add(
        SkillRow(
            holder_node_id=mortal.id,
            skill=SkillKind.LANGUAGES,
            subject_node_id=language_id,
            level=FIRST_LEVEL,
            peak=FIRST_LEVEL,
            last_used_epoch=ctx.epoch,
            source=SkillSource.TEACHING,
        )
    )
    await ctx.session.flush()
    await record_incident(ctx, "tongues.revealed", roles={IncidentRole.LEARNER: mortal.id, IncidentRole.SUBJECT: language_id})
    return True


async def maybe_teach(ctx: TickContext, god_id: int, mortal: EntityRow) -> bool:
    if not ctx.rng(f"tongue.dream.{god_id}.{mortal.id}.{ctx.epoch}").chance(ctx.rules.divine_tongues.learn_pct):
        return False
    return await teach(ctx, god_id, mortal)


async def give_tongues(ctx: TickContext, tally: TongueTally) -> None:
    for son in list(await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id))):
        if held(son.id) or await ctx.session.get(DivineTongueRow, son.id) is not None:
            continue
        if await give_tongue(ctx, son) is not None:
            tally.given += 1
    await ctx.session.flush()
