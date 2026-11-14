from sqlalchemy import Select, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultOfficeRow
from aerona.db.tables.sacred import DoctrineSacramentRow, SacramentRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.sacred import SacramentKind, SacramentProtection
from aerona.engine.context import TickContext
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.sacred.places import at_war, church_of, plagued_regions, realm_of_town, region_of, town_of


async def hardship(ctx: TickContext, town: EntityRow, plagued: set[int]) -> bool:
    region = await region_of(ctx.session, town)
    if region is not None and region.id in plagued:
        return True
    realm = await realm_of_town(ctx.session, town.id)
    return realm is not None and await at_war(ctx.session, realm)


async def priest_of(ctx: TickContext, cult_id: int) -> int | None:
    found = await ctx.session.scalar(
        select(CultOfficeRow.holder_entity_id)
        .where(CultOfficeRow.cult_entity_id == cult_id, CultOfficeRow.holder_entity_id.is_not(None))
        .order_by(CultOfficeRow.kind, CultOfficeRow.id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def perform(ctx: TickContext, mortal: EntityRow, kind: SacramentKind, plagued: set[int], *, priest_id: int | None = None) -> SacramentRow | None:
    table = ctx.rules.sacraments
    town = await town_of(ctx.session, mortal)
    cult = await church_of(ctx.session, town) if town is not None else None
    if town is None or cult is None or await ctx.session.get(DoctrineSacramentRow, (cult.id, kind)) is None:
        return None
    priest = priest_id if priest_id is not None else await priest_of(ctx, cult.id)
    doctrine = await ctx.session.get(CultDoctrineRow, cult.id)
    clergy = doctrine.clergy_count if doctrine is not None else 0
    chance = table.coverage if clergy > 0 or priest_id is not None else 0
    if priest_id is None and await hardship(ctx, town, plagued):
        chance = round_half_up(chance * (PERCENT - table.hardship_pct) / PERCENT)
    missed = priest is None or not ctx.rng(f"sacrament.{kind.value}.{mortal.id}").chance(chance)
    row = SacramentRow(
        mortal_entity_id=mortal.id,
        kind=kind,
        cult_entity_id=cult.id,
        priest_entity_id=None if missed else priest,
        epoch=ctx.epoch,
        missed=missed,
        locked=[],
    )
    ctx.session.add(row)
    if missed:
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FAITH_UNMET, ctx.epoch, intensity=table.missed_anxiety, subject_id=cult.id)
    await ctx.session.flush()
    return row


def received(protection: SacramentProtection, *, missed: bool) -> Select[int, int]:
    return (
        select(SacramentRow.mortal_entity_id, DoctrineSacramentRow.strength)
        .join(DoctrineSacramentRow, (DoctrineSacramentRow.cult_entity_id == SacramentRow.cult_entity_id) & (DoctrineSacramentRow.kind == SacramentRow.kind))
        .where(DoctrineSacramentRow.protection == protection, SacramentRow.missed.is_(missed))
    )


async def guarded(ctx: TickContext, mortal_id: int, protection: SacramentProtection) -> tuple[int, bool]:
    strengths = [strength for _, strength in await ctx.session.execute(received(protection, missed=False).where(SacramentRow.mortal_entity_id == mortal_id))]
    lacking = await ctx.session.scalar(received(protection, missed=True).where(SacramentRow.mortal_entity_id == mortal_id).limit(1))
    return max(strengths, default=0), lacking is not None


def warded_hosts() -> Select[int]:
    return received(SacramentProtection.POSSESSION, missed=False).with_only_columns(SacramentRow.mortal_entity_id)


async def last_rites(ctx: TickContext, mortal: EntityRow) -> SacramentRow | None:
    existing = await ctx.session.scalar(
        select(SacramentRow).where(SacramentRow.mortal_entity_id == mortal.id, SacramentRow.kind == SacramentKind.LAST_RITES).limit(1)
    )
    if existing is not None or held(mortal.id):
        return existing
    return await perform(ctx, mortal, SacramentKind.LAST_RITES, await plagued_regions(ctx.session))


async def rite_chance(ctx: TickContext, mortal: EntityRow, chance: float) -> float:
    table = ctx.rules.sacraments
    await last_rites(ctx, mortal)
    strength, lacking = await guarded(ctx, mortal.id, SacramentProtection.ROUTING)
    eased = chance * (PERCENT - table.routing_pct * strength / PERCENT) / PERCENT
    return min(PERCENT, eased + (table.missed_rite_pct if lacking else 0))


async def unrest_shift(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.sacraments
    await last_rites(ctx, mortal)
    strength, lacking = await guarded(ctx, mortal.id, SacramentProtection.UNREST)
    return round_half_up(-table.unrest_relief * strength / PERCENT) + (table.missed_unrest if lacking else 0)
