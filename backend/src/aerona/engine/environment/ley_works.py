from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, StructureLeyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.engine.context import TickContext
from aerona.engine.environment.ley import LeyWeb
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.primitives.words import names_word
from aerona.engine.structures.profiles import design_of
from aerona.engine.structures.spec import resolve

LEY_WORK_KINDS = frozenset({EngineKind.TEMPLE, EngineKind.OBSERVATORY})
LEY_FIXUP = "environment.ley_attunement"
LEY_WORDS = ("gate", "tower", "temple", "observatory", "shrine")


async def ley_row(session: AsyncSession, work: EntityRow, *, attuned: bool | None = None) -> StructureLeyRow:
    row = await session.get(StructureLeyRow, work.id)
    if row is None:
        row = StructureLeyRow(
            structure_entity_id=work.id,
            attuned=work.engine_kind in LEY_WORK_KINDS if attuned is None else attuned,
            on_ley_line=False,
            at_nexus=False,
            updated_epoch=0,
            locked=[],
        )
        session.add(row)
        await session.flush()
    return row


async def backfill_attunement(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, LEY_FIXUP):
        return 0
    attuned = 0
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        if await ctx.session.get(StructureLeyRow, work.id) is not None:
            continue
        text = (work.subtype or "").lower()
        row = await ley_row(ctx.session, work, attuned=work.engine_kind in LEY_WORK_KINDS or names_word(text, LEY_WORDS))
        attuned += int(row.attuned)
    ctx.session.add(AppliedFixupRow(key=LEY_FIXUP, result={"attuned": attuned}))
    await ctx.session.flush()
    return attuned


async def empower_works(ctx: TickContext, web: LeyWeb) -> int:
    settings = ctx.rules.environment
    atlas = await RegionAtlas.load(ctx.session)
    nexus = {place.entity_id for place in await ctx.session.scalars(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.nexus.is_(True)))}
    degree = web.degree()
    empowered = 0
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        row = await ley_row(ctx.session, work)
        region_id = atlas.top_region(work.id)
        if "on_ley_line" not in row.locked:
            row.on_ley_line = region_id is not None and degree[region_id] > 0
        if "at_nexus" not in row.locked:
            row.at_nexus = work.location_id in nexus
        row.updated_epoch = ctx.epoch
        profile = await ctx.session.get(StructureProfileRow, work.id)
        if profile is not None:
            if "on_ley_line" not in profile.locked:
                profile.on_ley_line = row.on_ley_line
            if "attuned" not in row.locked:
                row.attuned = resolve(profile.kind, await design_of(ctx.session, profile)).ley
        if not row.attuned or not row.on_ley_line:
            continue
        gain = settings.ley_function_gain * (settings.nexus_function_mult if row.at_nexus else 1)
        current = stat_or(work, "function", settings.ley_function_base)
        if current >= settings.ley_function_cap:
            continue
        set_stats(work, function=clamp_int(current + gain, 0, settings.ley_function_cap))
        empowered += 1
    return empowered
