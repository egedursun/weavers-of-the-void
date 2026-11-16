from sqlalchemy import func, select

from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.cycles.stress import aspirant_leader
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.queries import living_entity


async def sinecures(ctx: TickContext, polity_id: int) -> list[OfficeRow]:
    statement = (
        select(OfficeRow)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.sinecure.is_(True))
        .order_by(OfficeRow.since_epoch.desc(), OfficeRow.id.desc())
    )
    return list(await ctx.session.scalars(statement))


async def found_sinecure(ctx: TickContext, profile: PolityProfileRow, polity: EntityRow) -> OfficeRow | None:
    table = ctx.rules.offices_made
    leader = await aspirant_leader(ctx, polity.id)
    if leader is None or held(leader.id):
        return None
    office = OfficeRow(
        polity_entity_id=polity.id,
        kind=OfficeKind.MINISTER,
        holder_entity_id=leader.id,
        since_epoch=ctx.epoch,
        powers=[],
        sinecure=True,
        locked=[],
    )
    ctx.session.add(office)
    if "treasury" not in profile.locked:
        profile.treasury = max(0, profile.treasury - table.cost)
    await ctx.session.flush()
    await note(ctx, f"{polity.name} made a new office to hold {leader.name} and those like them.", key="office.created", ids=[polity.id, leader.id])
    return office


async def abolish_sinecure(ctx: TickContext, office: OfficeRow, polity: EntityRow) -> None:
    holder = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
    if holder is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=holder.id,
            subject_id=polity.id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-ctx.rules.offices_made.grievance,
            epoch=ctx.epoch,
            note="the office I held was abolished",
        )
    await ctx.session.delete(office)
    await ctx.session.flush()
    await note(ctx, f"{polity.name} abolished an office to save its treasury.", key="office.abolished", ids=[polity.id] + ([holder.id] if holder else []))


@reads("table.entities", "table.offices", "table.polity_profiles", "table.polity_stress")
@writes("table.memories", "table.offices", "table.polity_profiles")
async def office_creation(ctx: TickContext) -> None:
    table = ctx.rules.offices_made
    for stress, profile in await ctx.session.execute(
        select(PolityStressRow, PolityProfileRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == PolityStressRow.polity_entity_id)
        .order_by(PolityStressRow.polity_entity_id)
    ):
        polity = await living_entity(ctx.session, profile.polity_entity_id)
        if polity is None or held(polity.id) or "offices" in profile.locked:
            continue
        made = await sinecures(ctx, polity.id)
        upkeep = len(made) * table.upkeep
        if upkeep and "treasury" not in profile.locked:
            profile.treasury = max(0, profile.treasury - upkeep)
        if stress.fiscal_distress >= table.fiscal_distress and made:
            await abolish_sinecure(ctx, made[0], polity)
            ctx.count("offices_abolished")
        elif stress.elite_overproduction >= table.elite_pressure and profile.treasury >= table.cost and len(made) < table.most:
            if await found_sinecure(ctx, profile, polity) is not None:
                ctx.count("offices_created")
    await ctx.session.flush()


async def office_count(ctx: TickContext, polity_id: int) -> int:
    return int(await ctx.session.scalar(select(func.count()).select_from(OfficeRow).where(OfficeRow.polity_entity_id == polity_id)) or 0)
