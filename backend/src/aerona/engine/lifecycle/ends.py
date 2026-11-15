from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import LabTextRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import CastingRow, IdeologyAdherentRow, IdeologyProfileRow, RiteProfileRow
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.divine import BreachPointRow
from aerona.db.tables.ecology import SpeciesHostRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.states import GONE
from aerona.engine.lore.research_depth import RESEARCHERS
from aerona.engine.lore.theories import adhere
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or

S = LifecycleState
C = LifecycleCause
KIND_OF_TYPE = {
    EntityType.IDEOLOGY: LifecycleKind.IDEOLOGY,
    EntityType.THEORY: LifecycleKind.THEORY,
    EntityType.RITE: LifecycleKind.RITE,
    EntityType.DISEASE: LifecycleKind.DISEASE,
    EntityType.OUTER_BEING: LifecycleKind.OUTER_BEING,
}


@dataclass(frozen=True)
class Living:
    holders: int
    texts: int


@dataclass
class EndTally:
    seeded: int = 0
    dormant: int = 0
    ended: int = 0
    revived: int = 0
    corrupted: int = 0


async def canon_count(session: AsyncSession, ids: list[int]) -> int:
    if not ids:
        return 0
    found = await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON))
    return int(found or 0)


async def ideology_living(session: AsyncSession, holder_id: int, _epoch: int, _window: int) -> Living:
    adherents = list(await session.scalars(select(IdeologyAdherentRow.adherent_entity_id).where(IdeologyAdherentRow.ideology_entity_id == holder_id)))
    profile = await session.get(IdeologyProfileRow, holder_id)
    return Living(await canon_count(session, adherents), await canon_count(session, list(profile.texts) if profile is not None else []))


async def theory_living(session: AsyncSession, holder_id: int, _epoch: int, _window: int) -> Living:
    adherents = list(await session.scalars(select(TheoryAdherentRow.adherent_entity_id).where(TheoryAdherentRow.theory_entity_id == holder_id)))
    profile = await session.get(TheoryProfileRow, holder_id)
    book = [profile.founding_book_id] if profile is not None and profile.founding_book_id is not None else []
    return Living(await canon_count(session, adherents), await canon_count(session, book))


async def rite_living(session: AsyncSession, holder_id: int, epoch: int, window: int) -> Living:
    casters = set(
        await session.scalars(
            select(CastingRow.caster_entity_id).where(
                CastingRow.rite_entity_id == holder_id, CastingRow.epoch >= epoch - window, CastingRow.caster_entity_id.is_not(None)
            )
        )
    )
    profile = await session.get(RiteProfileRow, holder_id)
    if profile is not None and profile.inventor_entity_id is not None:
        casters.add(profile.inventor_entity_id)
    books = list(await session.scalars(select(LabTextRow.book_entity_id).where(LabTextRow.rite_entity_id == holder_id)))
    return Living(await canon_count(session, [int(item) for item in casters if item is not None]), await canon_count(session, books))


async def disease_living(session: AsyncSession, holder_id: int, _epoch: int, _window: int) -> Living:
    outbreaks = await session.scalar(
        select(func.count()).select_from(OutbreakRow).where(OutbreakRow.disease_entity_id == holder_id, OutbreakRow.status != OutbreakStatus.ENDED)
    )
    endemic = await session.scalar(select(func.count()).select_from(EndemicDiseaseRow).where(EndemicDiseaseRow.disease_entity_id == holder_id))
    hosts = list(
        await session.scalars(select(SpeciesHostRow.species_entity_id).where(SpeciesHostRow.disease_entity_id == holder_id, SpeciesHostRow.immune.is_(False)))
    )
    return Living(int(outbreaks or 0) + int(endemic or 0) + await canon_count(session, hosts), 0)


async def outer_living(session: AsyncSession, holder_id: int, _epoch: int, _window: int) -> Living:
    breaches = await session.scalar(select(func.count()).select_from(BreachPointRow).where(BreachPointRow.outer_entity_id == holder_id))
    cults = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.OUTER_CULT)
    worshippers = list(
        await session.scalars(
            select(BondRow.source_node_id).where(
                BondRow.target_node_id == holder_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(cults)
            )
        )
    )
    return Living(int(breaches or 0) + await canon_count(session, worshippers), 0)


LIVING = {
    LifecycleKind.IDEOLOGY: ideology_living,
    LifecycleKind.THEORY: theory_living,
    LifecycleKind.RITE: rite_living,
    LifecycleKind.DISEASE: disease_living,
    LifecycleKind.OUTER_BEING: outer_living,
}


async def living_of(ctx: TickContext, kind: LifecycleKind, holder_id: int) -> Living:
    return await LIVING[kind](ctx.session, holder_id, ctx.epoch, ctx.rules.lifecycle_ends.practice_epochs)


def grace(ctx: TickContext, kind: LifecycleKind) -> int:
    table = ctx.rules.lifecycle_ends
    return {LifecycleKind.DISEASE: table.eradication_epochs, LifecycleKind.RITE: table.practice_epochs}.get(kind, 1)


def lapsed(kind: LifecycleKind, living: Living) -> tuple[LifecycleState, LifecycleCause]:
    if kind is LifecycleKind.DISEASE:
        return S.ERADICATED, C.NO_HOSTS
    if kind is LifecycleKind.OUTER_BEING:
        return S.BANISHED, C.SEALED
    if living.texts:
        return S.DORMANT, C.NO_PRACTITIONERS if kind is LifecycleKind.RITE else C.NO_ADHERENTS
    return (S.LOST if kind is LifecycleKind.RITE else S.EXTINCT), C.NO_TEXTS


def still_present(ctx: TickContext, kind: LifecycleKind, holder: EntityRow, living: Living) -> bool:
    if kind is LifecycleKind.OUTER_BEING:
        return living.holders > 0 or stat_or(holder, "interest", 0) >= ctx.rules.lifecycle_ends.banish_interest
    return living.holders > 0


async def seed_state(session: AsyncSession, holder: EntityRow, epoch: int) -> LifecycleStateRow | None:
    kind = KIND_OF_TYPE.get(holder.entity_type)
    if kind is None:
        return None
    row = await session.get(LifecycleStateRow, holder.id)
    if row is None:
        row = LifecycleStateRow(holder_entity_id=holder.id, kind=kind, since_epoch=epoch, updated_epoch=epoch, locked=[])
        session.add(row)
        await session.flush()
    return row


async def move(ctx: TickContext, holder: EntityRow, row: LifecycleStateRow, state: LifecycleState, cause: LifecycleCause) -> bool:
    if row.state is state and row.cause is cause:
        return False
    before = row.state
    row.state, row.cause, row.since_epoch, row.updated_epoch = state, cause, ctx.epoch, ctx.epoch
    if state is S.ACTIVE and before in GONE:
        row.idle_epochs = 0
    told = state.value.replace("_", " ")
    reason = cause.value.replace("_", " ")
    await note(ctx, f"{holder.name} is now {told}: {reason}.", key=f"lifecycle.{state.value}", ids=[holder.id], world_id=holder.world_id)
    return True


async def revive_ideology(ctx: TickContext, holder: EntityRow) -> bool:
    profile = await ctx.session.get(IdeologyProfileRow, holder.id)
    texts = sorted(profile.texts) if profile is not None else []
    for text in texts:
        owner = await ctx.session.scalar(
            select(BondRow.source_node_id).where(BondRow.target_node_id == text, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).limit(1)
        )
        keeper = await ctx.session.get(EntityRow, owner) if owner is not None else None
        place = (
            await ctx.session.get(EntityRow, keeper.location_id)
            if keeper is not None and keeper.entity_type is EntityType.MORTAL and keeper.location_id
            else keeper
        )
        if place is None or place.entity_type not in RESEARCHERS or place.status is not EntityStatus.CANON or held(place.id):
            continue
        if await ctx.session.get(IdeologyAdherentRow, (holder.id, place.id)) is None:
            ctx.session.add(
                IdeologyAdherentRow(
                    ideology_entity_id=holder.id, adherent_entity_id=place.id, strength=ctx.rules.lifecycle_ends.revival_strength, since_epoch=ctx.epoch
                )
            )
            await ctx.session.flush()
        return True
    return False


async def rediscover_theory(ctx: TickContext, holder: EntityRow) -> bool:
    profile = await ctx.session.get(TheoryProfileRow, holder.id)
    if profile is None:
        return False
    found = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type.in_(list(RESEARCHERS)), EntityRow.status == EntityStatus.CANON, EntityRow.world_id == holder.world_id)
            .order_by(EntityRow.id)
        )
    )
    open_minds = [item for item in found if not held(item.id)]
    if not open_minds:
        return False
    finder = ctx.rng(f"lifecycle.rediscover.{holder.id}.{ctx.epoch}").pick(open_minds)
    await adhere(ctx, holder.id, finder.id, ctx.rules.theories.found_strength // 2, profile.domain)
    return True


async def school_practised(ctx: TickContext, profile: RiteProfileRow) -> bool:
    kin = select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.school == profile.school, RiteProfileRow.rite_entity_id != profile.rite_entity_id)
    found = await ctx.session.scalar(
        select(CastingRow.id).where(CastingRow.rite_entity_id.in_(kin), CastingRow.epoch >= ctx.epoch - ctx.rules.lifecycle_ends.practice_epochs).limit(1)
    )
    return found is not None


async def reconstruct_rite(ctx: TickContext, holder: EntityRow, row: LifecycleStateRow, tally: EndTally) -> bool:
    table = ctx.rules.lifecycle_ends
    profile = await ctx.session.get(RiteProfileRow, holder.id)
    if profile is None or not await school_practised(ctx, profile):
        return False
    fidelity = max(await ctx.session.scalars(select(LabTextRow.fidelity).where(LabTextRow.rite_entity_id == holder.id)), default=0)
    corrupt = ctx.rng(f"lifecycle.corrupt.{holder.id}.{ctx.epoch}").chance((PERCENT - fidelity) * table.corruption_pct / PERCENT)
    if corrupt:
        if "backlash_chance" not in profile.locked:
            profile.backlash_chance = clamp_int(profile.backlash_chance + table.corrupted_backlash, 0, PERCENT)
        tally.corrupted += 1
    row.idle_epochs = 0
    return await move(ctx, holder, row, S.CORRUPTED if corrupt else S.ACTIVE, C.RECONSTRUCTED)


async def wake(ctx: TickContext, holder: EntityRow, row: LifecycleStateRow, tally: EndTally) -> bool:
    if row.kind is LifecycleKind.IDEOLOGY and row.state is S.DORMANT and await revive_ideology(ctx, holder):
        return await move(ctx, holder, row, S.ACTIVE, C.REVIVED)
    if row.kind is LifecycleKind.THEORY and row.state is S.EXTINCT and await rediscover_theory(ctx, holder):
        return await move(ctx, holder, row, S.ACTIVE, C.REDISCOVERED)
    if row.kind is LifecycleKind.RITE and row.state is S.DORMANT:
        return await reconstruct_rite(ctx, holder, row, tally)
    return False


async def open_return(ctx: TickContext, holder: EntityRow) -> None:
    world = await ctx.session.get(WorldRow, holder.world_id) if holder.world_id is not None else None
    if world is None:
        return
    ctx.session.add(
        BreachPointRow(
            outer_entity_id=holder.id,
            world_id=world.id,
            region_entity_id=holder.location_id,
            strength=ctx.rules.outer_beings.breach_strength,
            opened_epoch=ctx.epoch,
        )
    )
    await ctx.session.flush()


async def returns(ctx: TickContext, holder: EntityRow) -> bool:
    world = await ctx.session.get(WorldRow, holder.world_id) if holder.world_id is not None else None
    leak = world.leakage if world is not None else 0
    if not ctx.rng(f"lifecycle.return.{holder.id}.{ctx.epoch}").chance(leak * ctx.rules.lifecycle_ends.return_pct / PERCENT):
        return False
    await open_return(ctx, holder)
    return True


async def tend_one(ctx: TickContext, holder: EntityRow, row: LifecycleStateRow, tally: EndTally) -> None:
    if "state" in row.locked or row.state is S.DESTROYED:
        return
    table = ctx.rules.lifecycle_ends
    living = await living_of(ctx, row.kind, holder.id)
    if still_present(ctx, row.kind, holder, living):
        row.idle_epochs = 0 if "idle_epochs" not in row.locked else row.idle_epochs
        if row.state in GONE:
            cause = {LifecycleKind.DISEASE: C.RERELEASED, LifecycleKind.OUTER_BEING: C.RETURNED}.get(row.kind, C.REVIVED)
            tally.revived += int(await move(ctx, holder, row, S.ACTIVE, cause))
        return
    if row.state in GONE:
        if row.kind is LifecycleKind.OUTER_BEING and row.state is S.BANISHED and await returns(ctx, holder):
            tally.revived += int(await move(ctx, holder, row, S.ACTIVE, C.RETURNED))
        elif ctx.rng(f"lifecycle.wake.{holder.id}.{ctx.epoch}").chance(table.revival_pct if row.kind is not LifecycleKind.THEORY else table.rediscover_pct):
            tally.revived += int(await wake(ctx, holder, row, tally))
        return
    if "idle_epochs" not in row.locked:
        row.idle_epochs += 1
    if row.idle_epochs < grace(ctx, row.kind):
        return
    state, cause = lapsed(row.kind, living)
    if await move(ctx, holder, row, state, cause):
        tally.dormant += int(state is S.DORMANT)
        tally.ended += int(state is not S.DORMANT)


async def keep_ends(ctx: TickContext, tally: EndTally) -> None:
    holders = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type.in_(list(KIND_OF_TYPE)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for holder in holders:
        if held(holder.id):
            continue
        row = await ctx.session.get(LifecycleStateRow, holder.id)
        if row is None:
            row = await seed_state(ctx.session, holder, ctx.epoch)
            tally.seeded += 1
        if row is not None:
            await tend_one(ctx, holder, row, tally)
    await ctx.session.flush()
