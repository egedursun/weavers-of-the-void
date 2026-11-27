from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.tongues import NumeralBase
from aerona.engine.context import TickContext
from aerona.engine.crafts.reckoning import system_of
from aerona.engine.lore.language import speakers
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import record
from aerona.engine.tongues.sounds import contacts_of

TALLY_NUMERACY = 10


async def prestige_of(session: AsyncSession, language_id: int) -> int:
    row = await session.get(LanguageStandingRow, language_id)
    return row.prestige if row is not None else 0


async def set_base(ctx: TickContext, language: EntityRow, profile: LanguageProfileRow, base: NumeralBase, *, source_id: int | None) -> bool:
    if profile.numeral_base is base:
        return False
    old = profile.numeral_base
    profile.numeral_base = base
    roles = {IncidentRole.SUBJECT: language.id}
    if source_id is not None:
        roles[IncidentRole.TEACHER] = source_id
    await record(ctx, "language.base_changed", roles=roles, facts={"old": old, "new": base})
    return True


async def base_contact(ctx: TickContext) -> int:
    changed = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id):
            continue
        own = await prestige_of(ctx.session, language.id)
        best: tuple[int, int, NumeralBase] | None = None
        for other_id in sorted(await contacts_of(ctx, language.id)):
            other = await ctx.session.get(LanguageProfileRow, other_id)
            if other is None or other.numeral_base is profile.numeral_base:
                continue
            standing = await prestige_of(ctx.session, other_id)
            if standing > own and (best is None or standing > best[0]):
                best = (standing, other_id, other.numeral_base)
        if best is None or not ctx.rng(f"tongues.base.{language.id}.{ctx.epoch}").chance(ctx.rules.tongues.base_contact_pct):
            continue
        changed += await set_base(ctx, language, profile, best[2], source_id=best[1])
    return changed


async def derived_base(session: AsyncSession, language: EntityRow, profile: LanguageProfileRow) -> NumeralBase:
    if profile.parent_language_id is not None:
        parent = await session.get(LanguageProfileRow, profile.parent_language_id)
        if parent is not None:
            return parent.numeral_base
    if profile.writing_system is None:
        numeracy = [row.numeracy for community in await speakers(session, language.id) if (row := await system_of(session, community)) is not None]
        if not numeracy or max(numeracy) < TALLY_NUMERACY:
            return NumeralBase.BODY_TALLY
    return NumeralBase.DECIMAL


BASES_FIXUP = "tongues.w52_bases"


async def backfill_bases(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, BASES_FIXUP):
        return 0
    set_count = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        profile = await ctx.session.get(LanguageProfileRow, language.id)
        if profile is None or held(language.id) or language.origin is not EntityOrigin.ENGINE or profile.numeral_base is not NumeralBase.DECIMAL:
            continue
        base = await derived_base(ctx.session, language, profile)
        if base is not NumeralBase.DECIMAL:
            profile.numeral_base = base
            set_count += 1
    ctx.session.add(AppliedFixupRow(key=BASES_FIXUP, result={"bases": set_count}))
    await ctx.session.flush()
    return set_count
