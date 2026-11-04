import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.gods.essence import spend
from aerona.engine.gods.worship import cult_effect
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.essence import Overflow, overflow_to_land
from aerona.engine.primitives.ledger import EssenceItem, LedgerKey, read, record_essence
from aerona.engine.primitives.queries import flags_by_entity
from aerona.rules.registry import Rules

CALLING_TEXT = (
    "DOOM BECAME A CALLING: {world}'s sky opened and the things outside were called by their names. The world was not destroyed; but it is no longer alone."
)


async def cosmos_of(session: AsyncSession) -> CosmosRow:
    return await CosmosRepository(session).require_cosmos()


async def creator_of(session: AsyncSession) -> CreatorRow:
    return await CosmosRepository(session).require_creator()


async def living_worlds(session: AsyncSession) -> list[WorldRow]:
    return list(await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))


async def godless_by_world(session: AsyncSession) -> dict[int, int]:
    godless = await flags_by_entity(session, EntityFlag.GODLESS)
    if not godless:
        return {}
    rows = await session.execute(select(EntityRow.world_id, func.count()).where(EntityRow.id.in_(godless)).group_by(EntityRow.world_id))
    return {world_id: int(count) for world_id, count in rows}


async def leakiest_world(session: AsyncSession) -> WorldRow | None:
    worlds = await living_worlds(session)
    if not worlds:
        return None
    godless = await godless_by_world(session)
    return min(worlds, key=lambda world: (-world.leakage, -godless.get(world.id, 0), world.id))


async def doom_calling(ctx: TickContext) -> bool:
    worlds = await living_worlds(ctx.session)
    if not worlds:
        return False
    average = sum(world.leakage for world in worlds) / len(worlds)
    if average < ctx.rules.cosmic_horror.calling_threshold:
        return False
    target = await leakiest_world(ctx.session)
    if target is None:
        return False
    target.leakage = PERCENT
    await note(ctx, CALLING_TEXT.format(world=target.name), key="doom.calling", kind=ChronicleKind.APOCALYPSE, world_id=target.id)
    return True


async def overflow_to_sons(session: AsyncSession, rules: Rules, budget: int) -> int:
    if budget <= 0:
        return 0
    fill = rules.essence.overflow_sons_fill_pct
    eligible = [
        son
        for son in await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.rebel.is_(False)).order_by(SonRow.id))
        if son.essence < max_essence(rules, son.might) * fill // PERCENT
    ]
    given = 0
    while given < budget:
        open_sons = [son for son in eligible if son.essence < max_essence(rules, son.might) * fill // PERCENT]
        if not open_sons:
            break
        poorest = max(open_sons, key=lambda son: (1 - son.essence / max(1, max_essence(rules, son.might)), -son.id))
        poorest.essence += 1
        given += 1
    await session.flush()
    return given


@reads(
    "people.piety",
    "people.population",
    "region.fertility",
    "settlement.piety",
    "settlement.population",
    "table.bonds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
)
@writes("region.fertility", "table.chronicle", "table.creator", "table.entities", "table.epoch_year_cursors", "table.incidents")
async def creator_essence(ctx: TickContext) -> None:
    rules = ctx.rules
    balance = rules.balance
    essence = rules.essence
    creator = await creator_of(ctx.session)
    faith_income = read(ctx, LedgerKey.TOTAL_FAITH) // rules.world_epoch_transition.faith_essence_divisor
    income = balance.creator_essence_regen + faith_income
    record_essence(ctx, EssenceItem.REGEN, balance.creator_essence_regen)
    record_essence(ctx, EssenceItem.FAITH, faith_income)
    overflow = 0
    if creator.essence > balance.creator_essence_soft_cap:
        shrink = 1 - essence.over_cap_decline_pct / PERCENT * (1 - balance.creator_essence_soft_cap / creator.essence)
        kept = math.floor(income * essence.over_cap_income_pct / PERCENT * shrink)
        record_essence(ctx, EssenceItem.HALVED, kept - income)
        income = kept
        overflow = math.ceil((creator.essence - balance.creator_essence_soft_cap) * essence.overflow_pct / PERCENT)
    stolen = read(ctx, LedgerKey.STOLEN_ESSENCE)
    godless = len(await flags_by_entity(ctx.session, EntityFlag.GODLESS))
    gnawed = godless * essence.godless_gnaw
    cult = await cult_effect(ctx.session, rules)
    creator.essence = max(0, creator.essence + income - overflow - stolen - gnawed) + cult.essence
    record_essence(ctx, EssenceItem.OVERFLOW, -overflow)
    record_essence(ctx, EssenceItem.STOLEN, -stolen)
    record_essence(ctx, EssenceItem.GNAWED, -gnawed)
    record_essence(ctx, EssenceItem.CULT, cult.essence)
    if overflow > 0:
        to_sons = await overflow_to_sons(ctx.session, rules, overflow * essence.overflow_sons_pct // PERCENT)
        record_essence(ctx, EssenceItem.TO_SONS, -to_sons)
        await overflow_to_land(ctx.session, rules, overflow - to_sons)
        if overflow >= rules.world_epoch_transition.essence_overflow_note:
            await note(
                ctx, f"{overflow} units of the Creator's overflowing essence seeped into the world; the most barren lands grew fertile.", key="essence.overflow"
            )


@reads("table.cosmos")
@writes("table.chronicle", "table.chronicle_entities", "table.cosmos", "table.incident_participants", "table.incidents")
async def advance_epoch(ctx: TickContext) -> None:
    cosmos = await cosmos_of(ctx.session)
    years = ctx.rules.time.years_per_epoch
    cosmos.epoch = ctx.epoch + 1
    cosmos.epoch_start_year = cosmos.epoch_start_year + years
    primary = await ctx.session.get(WorldRow, cosmos.primary_world_id) if cosmos.primary_world_id is not None else None
    star = await ctx.session.get(EntityRow, primary.epoch_star_entity_id) if primary is not None and primary.epoch_star_entity_id is not None else None
    star_text = f" Star of the epoch: {star.name}." if star is not None else ""
    await ChronicleRepository(ctx.session).append(
        ChronicleDraft(
            epoch=cosmos.epoch,
            kind=ChronicleKind.SYSTEM,
            text=f"Epoch {cosmos.epoch} began (world year {cosmos.epoch_start_year}).{star_text}",
            entity_ids=[star.id] if star is not None else [],
            template_key="transition.epoch_began",
        )
    )


async def pour_essence(ctx: TickContext, amount: int) -> Overflow:
    if amount <= 0:
        raise ValidationFailedError("Pour at least one unit of essence.")
    spend(await creator_of(ctx.session), amount, "the pour")
    result = await overflow_to_land(ctx.session, ctx.rules, amount)
    await note(
        ctx,
        f"The Creator poured {amount} essence into the land; {result.given} measures of fertility rose in the most barren regions.",
        key="essence.poured",
        ids=list(result.regions),
    )
    return result


ESSENCE_PHASES = (Phase("creator_essence", creator_essence),)
ADVANCE_PHASES = (Phase("advance_epoch", advance_epoch),)
PHASES = ESSENCE_PHASES + ADVANCE_PHASES
