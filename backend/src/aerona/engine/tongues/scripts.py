from dataclasses import dataclass

from aerona.catalog.tongues import SCRIPT_CHAIN, SCRIPT_SIGNS, WRITABLE
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.tongues import ScriptRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, WritingSystem
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.tongues import ScriptChangeCause
from aerona.engine.context import TickContext
from aerona.engine.lore.language import speakers, standardisation_of
from aerona.engine.notes import note
from aerona.engine.primitives.queries import canon, has_flag
from aerona.engine.primitives.society import class_shares
from aerona.engine.tongues.sounds import contacts_of
from aerona.language.writing import WRITING_SYSTEM_PHRASES


@dataclass
class ScriptTally:
    recorded: int = 0
    evolved: int = 0
    borrowed: int = 0


def script_name(language: EntityRow, system: WritingSystem) -> str:
    return f"{language.name} {system.value}"[:NAME_MAX_LENGTH]


async def record_script(
    ctx: TickContext,
    language: EntityRow,
    profile: LanguageProfileRow,
    system: WritingSystem,
    *,
    cause: ScriptChangeCause,
    parent: ScriptRow | None = None,
    extra_signs: int = 0,
) -> ScriptRow:
    row = ScriptRow(
        name=script_name(language, system),
        system=system,
        parent_script_id=parent.id if parent is not None else None,
        origin_language_id=language.id,
        signs=(parent.signs if parent is not None and parent.system is system else SCRIPT_SIGNS[system]) + extra_signs,
        cause=cause,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    profile.script_id, profile.writing_system, profile.script_epoch = row.id, system, ctx.epoch
    return row


async def script_of(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow) -> ScriptRow | None:
    if profile.script_id is not None:
        found = await ctx.session.get(ScriptRow, profile.script_id)
        if found is not None:
            return found
    if profile.writing_system is None:
        return None
    return await record_script(ctx, language, profile, profile.writing_system, cause=ScriptChangeCause.INVENTION)


async def merchant_share(ctx: TickContext, language_id: int) -> float:
    shares = [(await class_shares(ctx.session, ctx.rules, community))[SocialClass.MERCHANT] for community in await speakers(ctx.session, language_id)]
    return sum(shares) / len(shares) if shares else 0.0


async def evolve(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow, tally: ScriptTally) -> ScriptRow | None:
    table = ctx.rules.script_evolution
    current = await script_of(ctx, language, profile)
    following = SCRIPT_CHAIN[current.system] if current is not None else None
    if current is None or following is None or "system" in current.locked:
        return None
    if await merchant_share(ctx, language.id) >= table.merchant_share:
        cause = ScriptChangeCause.SIMPLIFICATION
    elif await standardisation_of(ctx.session, language.id) >= table.reform_standard:
        cause = ScriptChangeCause.REFORM
    else:
        return None
    if not ctx.rng(f"script.evolve.{language.id}.{ctx.epoch}").chance(table.evolve_pct):
        return None
    row = await record_script(ctx, language, profile, following, cause=cause, parent=current)
    tally.evolved += 1
    await note(
        ctx,
        f"The script of {language.name} became {WRITING_SYSTEM_PHRASES[following]} through {spoken(cause)}.",
        key="tongues.script_evolved",
        ids=[language.id],
        kind=ChronicleKind.CULTURE,
    )
    return row


async def borrow(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow, tally: ScriptTally) -> ScriptRow | None:
    table = ctx.rules.script_evolution
    if not WRITABLE[profile.modality]:
        return None
    for lender_id in sorted(await contacts_of(ctx, language.id)):
        lender = await ctx.session.get(EntityRow, lender_id)
        lent = await ctx.session.get(LanguageProfileRow, lender_id)
        source = await script_of(ctx, lender, lent) if lender is not None and lent is not None else None
        if source is None or not ctx.rng(f"script.borrow.{language.id}.{lender_id}.{ctx.epoch}").chance(table.borrow_pct):
            continue
        row = await record_script(ctx, language, profile, source.system, cause=ScriptChangeCause.BORROWING, parent=source, extra_signs=table.borrowed_signs)
        tally.borrowed += 1
        await note(
            ctx,
            f"{language.name} came to be written in the script of {lender.name if lender is not None else 'a neighbour'}, with signs added for its own sounds.",
            key="tongues.script_borrowed",
            ids=[language.id, lender_id],
            kind=ChronicleKind.CULTURE,
        )
        return row
    return None


async def evolve_scripts(ctx: TickContext, tally: ScriptTally) -> None:
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id) or await has_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE):
            continue
        if profile.writing_system is None:
            await borrow(ctx, language, profile, tally)
            continue
        if profile.script_id is None:
            await script_of(ctx, language, profile)
            tally.recorded += 1
        await evolve(ctx, language, profile, tally)
    await ctx.session.flush()
