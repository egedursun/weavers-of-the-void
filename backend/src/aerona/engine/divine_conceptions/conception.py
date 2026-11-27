from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.total import total
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.divine_conceptions import DivineConceptionRow, GodReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine_conceptions import CreatorPlace, DivineCount, DivineNearness, DivinePersonhood, GodReading
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import active_bonds

C = DivineCount
N = DivineNearness
SEED_FIXUP = "divine_conceptions.legacy"
PAIR = 2
OUTSIDERS = total(
    DivineCount,
    {
        C.ONE: GodReading.DEMON,
        C.ONE_ABOVE_MANY: GodReading.SERVANT,
        C.MANY: GodReading.UNKNOWN,
        C.PAIRS: GodReading.UNKNOWN,
        C.ALL_IS_DIVINE: GodReading.TRUE,
        C.NONE: GodReading.UNKNOWN,
    },
)
THEODICY = total(DivineNearness, {N.DISTANT: 0.5, N.PRESENT: 1.0, N.WITHIN: 0.75})
OPEN_COUNTS = frozenset({C.MANY, C.PAIRS, C.ALL_IS_DIVINE, C.ONE_ABOVE_MANY})


async def gods_of(session: AsyncSession, cult_id: int) -> list[int]:
    return sorted({bond.target_node_id for bond in await active_bonds(session, [BondKind.WORSHIPS], sources=[cult_id])})


async def tenets_of(session: AsyncSession, cult_id: int) -> set[TenetKind]:
    return set(await session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult_id)))


def count_for(worshipped: int, tenets: set[TenetKind], world_gods: int) -> DivineCount:
    if worshipped == 0:
        return C.ALL_IS_DIVINE if TenetKind.ANCESTOR_VENERATION in tenets else C.NONE
    if TenetKind.EXCLUSIVITY in tenets or world_gods <= 1:
        return C.ONE
    if TenetKind.SYNCRETIC_OPENNESS in tenets:
        return C.MANY
    return C.PAIRS if world_gods == PAIR else C.ONE_ABOVE_MANY


def nearness_for(tenets: set[TenetKind]) -> DivineNearness:
    if TenetKind.ANCESTOR_VENERATION in tenets:
        return N.PRESENT
    if TenetKind.ASCETICISM in tenets or TenetKind.MONASTIC_LEARNING in tenets:
        return N.WITHIN
    return N.DISTANT


def personhood_for(tenets: set[TenetKind]) -> DivinePersonhood:
    return DivinePersonhood.FORCES if TenetKind.SANCTIFIED_MAGIC in tenets else DivinePersonhood.PERSONS


async def conceive(ctx: TickContext, cult: EntityRow) -> DivineConceptionRow:
    gods, tenets = await gods_of(ctx.session, cult.id), await tenets_of(ctx.session, cult.id)
    world_gods = await ctx.session.scalar(select(func.count(SonRow.id)).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == cult.world_id)) or 0
    row = DivineConceptionRow(
        cult_entity_id=cult.id,
        count=count_for(len(gods), tenets, world_gods),
        nearness=nearness_for(tenets),
        personhood=personhood_for(tenets),
        creator_place=CreatorPlace.UNKNOWN,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await read_gods(ctx, row)
    return row


async def read_gods(ctx: TickContext, row: DivineConceptionRow) -> None:
    worshipped = set(await gods_of(ctx.session, row.cult_entity_id))
    sons = list(await ctx.session.scalars(select(SonRow.id).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)))
    for god in sorted(set(sons) | worshipped):
        current = await ctx.session.get(GodReadingRow, (row.cult_entity_id, god))
        reading = GodReading.TRUE if god in worshipped else OUTSIDERS[row.count]
        if current is None:
            ctx.session.add(GodReadingRow(cult_entity_id=row.cult_entity_id, god_node_id=god, reading=reading, locked=[]))
        elif "reading" not in current.locked and god in worshipped:
            current.reading = GodReading.TRUE


async def faiths(ctx: TickContext) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return [cult for cult in await ctx.session.scalars(query) if not held(cult.id)]


async def conceive_all(ctx: TickContext) -> int:
    made = 0
    for cult in await faiths(ctx):
        if await ctx.session.get(DivineConceptionRow, cult.id) is None:
            await conceive(ctx, cult)
            made += 1
    if await fixup_due(ctx.session, SEED_FIXUP):
        ctx.session.add(AppliedFixupRow(key=SEED_FIXUP, result={"conceived": made}))
        await ctx.session.flush()
    return made


async def theodicy_factor(session: AsyncSession, cult_id: int) -> float:
    row = await session.get(DivineConceptionRow, cult_id)
    if row is None:
        return 1.0
    return 0.0 if row.count is C.NONE else THEODICY[row.nearness]


async def syncretism_fit(session: AsyncSession, rules_fit: int, holder: int | None, newcomer: int | None) -> float:
    rows = [await session.get(DivineConceptionRow, cult) if cult is not None else None for cult in (holder, newcomer)]
    counts = [row.count for row in rows if row is not None]
    if C.ONE in counts:
        return 1 - rules_fit / 100
    if len(counts) == len(rows) and all(count in OPEN_COUNTS for count in counts):
        return 1 + rules_fit / 100
    return 1.0
