from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import Select, select

from aerona.catalog.sacred import SACRAMENT_COSTS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultOfficeRow
from aerona.db.tables.folkways import PurityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import DoctrineSacramentRow, SacramentRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.folkways import PurityState
from aerona.domain.enums.mind import ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sacred import SacramentKind, SacramentProtection
from aerona.domain.enums.society import Commodity
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import at_war, church_of, patron_of, plagued_regions, realm_of_town, region_of, town_of


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
    else:
        await keep_rite(ctx, mortal, kind, town, cult_id=cult.id, priest=priest)
    await ctx.session.flush()
    return row


async def keep_rite(ctx: TickContext, mortal: EntityRow, kind: SacramentKind, town: EntityRow, *, cult_id: int, priest: int | None) -> None:
    cost = min(SACRAMENT_COSTS[kind](ctx.rules), await stock(ctx.session, ctx.rules, town.id, Commodity.GOODS)) if not held(town.id) else 0
    if cost > 0:
        await shift_stock(ctx.session, ctx.rules, town.id, Commodity.GOODS, -cost, epoch=ctx.epoch, flow=GoodsFlow.OFFERING)
    await RITE_EFFECTS[kind](ctx, mortal)
    await record(
        ctx,
        "sacrament.given",
        roles={IncidentRole.PATIENT: mortal.id, IncidentRole.SUBJECT: cult_id, IncidentRole.OFFICIANT: priest},
        facts={"rite": kind},
    )


async def cleanse(ctx: TickContext, mortal: EntityRow) -> None:
    purity = await ctx.session.get(PurityRow, mortal.id)
    if purity is not None and "state" not in purity.locked:
        purity.state, purity.source, purity.until_epoch = PurityState.PURE, None, None
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is not None and "stress" not in profile.locked:
        profile.stress = max(0, profile.stress - ctx.rules.sacraments.purification_guilt)


async def ordain(ctx: TickContext, mortal: EntityRow) -> None:
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    values[ValueAxis.PIETY] = clamp_int(values.get(ValueAxis.PIETY, 0) + ctx.rules.sacraments.ordination_piety, -PERCENT, PERCENT)
    await write_values(ctx.session, ValueHolder.PERSONAL, mortal.id, values)


async def no_more(_ctx: TickContext, _mortal: EntityRow) -> None:
    return None


RITE_EFFECTS: Mapping[SacramentKind, Callable[[TickContext, EntityRow], Awaitable[None]]] = total(
    SacramentKind,
    {
        SacramentKind.BIRTH_BLESSING: no_more,
        SacramentKind.INITIATION: no_more,
        SacramentKind.MARRIAGE: no_more,
        SacramentKind.LAST_RITES: no_more,
        SacramentKind.PURIFICATION: cleanse,
        SacramentKind.ORDINATION: ordain,
    },
)


async def curse_ward(ctx: TickContext, bearer_id: int) -> int:
    rows = await ctx.session.execute(
        received(SacramentProtection.CURSE, missed=False).add_columns(SacramentRow.cult_entity_id).where(SacramentRow.mortal_entity_id == bearer_id)
    )
    strengths = [strength for _, strength, cult_id in rows if cult_id is not None and await patron_of(ctx, cult_id) is not None]
    return round_half_up(ctx.rules.sacraments.curse_ward_pct * max(strengths, default=0) / PERCENT)


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
