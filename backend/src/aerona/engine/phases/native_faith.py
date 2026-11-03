from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.society import ReverenceRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import AGENT_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import believers_faith, worshippers
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.faith import change_religion, patron_son
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import add_flag, canon, flags_by_entity, living_son, remove_flag
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

NATIVE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
PIETY_KEY = "piety"
STANCE_BONDS = (BondKind.TRADES_WITH, BondKind.ALLY, BondKind.ENEMY)


def awake(god: ForeignGodRow) -> bool:
    return god.status is ForeignGodStatus.AWAKE


async def reverers(session: AsyncSession, god_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(ReverenceRow, ReverenceRow.entity_id == EntityRow.id)
        .where(ReverenceRow.god_node_id == god_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(await session.scalars(statement))


async def native_god_faith(session: AsyncSession, rules: Rules, god_id: int) -> float:
    full = believers_faith(rules, await worshippers(session, god_id))
    return full + believers_faith(rules, await reverers(session, god_id)) * rules.native_faith.syncretic_weight_pct / PERCENT


async def holds_god(session: AsyncSession, entity_id: int, god_id: int) -> bool:
    if await session.get(ReverenceRow, (entity_id, god_id)) is not None:
        return True
    statement = select(BondRow.id).where(
        BondRow.source_node_id == entity_id, BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
    )
    return await session.scalar(statement.limit(1)) is not None


async def struck_places(session: AsyncSession, epoch: int) -> set[int]:
    statement = (
        select(EntityRow.location_id)
        .join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == epoch, EntityFlagRow.flag == EntityFlag.DISASTER)
    )
    return {item for item in await session.scalars(statement) if item is not None}


def faded(son: SonRow | None) -> bool:
    return son is None or son.status is not SonStatus.ACTIVE or son.rebel


async def adopt_old_god(ctx: TickContext, native: EntityRow, god: ForeignGodRow, syncretic: bool, reason: str) -> None:
    if syncretic:
        ctx.session.add(ReverenceRow(entity_id=native.id, god_node_id=god.id, since_epoch=ctx.epoch))
        await add_flag(ctx.session, native.id, EntityFlag.SYNCRETIC, ctx.epoch)
        await ctx.session.flush()
        return
    await BondRepository(ctx.session).connect(BondDraft(native.id, god.id, BondKind.WORSHIPS, ctx.epoch, reason))
    await remove_flag(ctx.session, native.id, EntityFlag.GODLESS)
    await remove_flag(ctx.session, native.id, EntityFlag.SEEKING_GOD)
    await add_flag(ctx.session, native.id, EntityFlag.RETURNED_TO_OLD_GOD, ctx.epoch)


async def turn_natives(ctx: TickContext, god: ForeignGodRow, struck: set[int]) -> int:
    table = ctx.rules.native_faith
    world = await ctx.session.get(WorldRow, god.world_id)
    world_name = world.name if world is not None else "its world"
    colonies = await flags_by_entity(ctx.session, EntityFlag.COLONY)
    godless = await flags_by_entity(ctx.session, EntityFlag.GODLESS)
    turned = 0
    for native in await canon(ctx.session, NATIVE_TYPES, god.world_id):
        if turned >= table.turn_cap:
            break
        if native.id in colonies or await holds_god(ctx.session, native.id, god.id):
            continue
        patron = await patron_son(ctx.session, native)
        lost = faded(patron)
        if not (stat_or(native, PIETY_KEY, table.weak_piety) < table.weak_piety or lost or native.id in godless):
            continue
        hit = native.id in struck or native.location_id in struck
        chance = (table.turn_chance + (table.disaster_bonus if hit else 0) + (table.patronless_bonus if lost else 0)) * (
            1 if awake(god) else table.sleeping_pull_pct / PERCENT
        )
        rng = ctx.rng(f"turn.{god.id}.{native.id}")
        if not rng.chance(chance):
            continue
        syncretic = patron is not None and patron.status is not SonStatus.DEAD and rng.chance(table.syncretic_share)
        await adopt_old_god(ctx, native, god, syncretic, "turned to the old god")
        turned += 1
        if syncretic and patron is not None:
            text = f"{native.name} began to bring offerings both to {patron.name} and to {world_name}'s old god {god.name}."
        else:
            former = f"turned away from {patron.name} and " if patron is not None else ""
            dreaming = "" if awake(god) else "; even asleep, the god walked in their dreams"
            text = f"{native.name} {former}returned to {world_name}'s old god {god.name}{dreaming}."
        await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="native_faith.turned", entity_ids=[native.id], son_id=patron.id if patron else None)
        await note(ctx, text, key="native_faith.turned_note", ids=[native.id], kind=ChronicleKind.FOREIGN_GOD)
    return turned


async def pantheon_home(session: AsyncSession, entity: EntityRow) -> SonRow | None:
    world = await session.get(WorldRow, entity.world_id)
    guardian = await living_son(session, world.patron_son_id if world is not None else None)
    if guardian is not None and guardian.status is SonStatus.ACTIVE:
        return guardian
    found: SonRow | None = await session.scalar(
        select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == entity.world_id).order_by(SonRow.id).limit(1)
    )
    return found


async def return_one(ctx: TickContext, believer: EntityRow, god: ForeignGodRow) -> str | None:
    syncretic = await ctx.session.get(ReverenceRow, (believer.id, god.id))
    if syncretic is not None:
        await ctx.session.delete(syncretic)
        await remove_flag(ctx.session, believer.id, EntityFlag.SYNCRETIC)
        await ctx.session.flush()
        patron = await patron_son(ctx.session, believer)
        return f"{believer.name} left off its offerings to {god.name}; it worships only {patron.name if patron else 'the pantheon'} now."
    home = await pantheon_home(ctx.session, believer)
    if home is None or not await change_religion(ctx.session, believer, home.id, ctx.epoch, f"left {god.name} and returned to the pantheon"):
        return None
    await remove_flag(ctx.session, believer.id, EntityFlag.RETURNED_TO_OLD_GOD)
    return f"{believer.name} left the old god {god.name} and turned to {home.name}."


async def return_to_pantheon(ctx: TickContext, gods: list[ForeignGodRow]) -> int:
    table = ctx.rules.native_faith
    returned = 0
    for god in gods:
        believers = [*await worshippers(ctx.session, god.id), *await reverers(ctx.session, god.id)]
        for believer in believers:
            if returned >= table.return_cap:
                return returned
            multiplier = 1 if awake(god) else table.return_defeated_mult_pct / PERCENT
            if not ctx.rng(f"return.{god.id}.{believer.id}").chance(table.return_chance * multiplier):
                continue
            text = await return_one(ctx, believer, god)
            if text is None:
                continue
            god.stance = clamp_int(god.stance - table.stance_loss, RELATION_MIN, RELATION_MAX)
            returned += 1
            await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="native_faith.returned", entity_ids=[believer.id])
            await note(ctx, text, key="native_faith.returned_note", ids=[believer.id], kind=ChronicleKind.FOREIGN_GOD)
    return returned


async def stance_shift(ctx: TickContext, god: ForeignGodRow) -> int:
    table = ctx.rules.native_faith
    delta = 0
    bonds = BondRepository(ctx.session)
    for believer in await worshippers(ctx.session, god.id):
        if await patron_son(ctx.session, believer) is not None:
            delta += table.stance_syncretic
        for kind in STANCE_BONDS:
            for bond in await bonds.outgoing(believer.id, kind) + await bonds.incoming(believer.id, kind):
                other = await ctx.session.get(EntityRow, bond.other_end(believer.id))
                if other is None or await patron_son(ctx.session, other) is None:
                    continue
                delta += -table.stance_war if kind is BondKind.ENEMY else table.stance_peace
    delta += table.stance_syncretic * len(await reverers(ctx.session, god.id))
    return max(-table.stance_step, min(table.stance_step, delta))


async def feed_god(ctx: TickContext, god: ForeignGodRow) -> None:
    table = ctx.rules.native_faith
    faith = await native_god_faith(ctx.session, ctx.rules, god.id)
    god.faith = round(faith)
    target = max(0, min(PERCENT, table.power_floor + faith / table.power_faith_divisor))
    gap = target - god.power
    god.power = clamp_int(god.power + max(-table.power_step, min(table.power_step, gap)), 0, PERCENT)
    if god.contacted:
        god.stance = clamp_int(god.stance + await stance_shift(ctx, god), RELATION_MIN, RELATION_MAX)


@reads(
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.bonds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
    "table.reverences",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.incident_participants",
    "table.incidents",
    "table.reverences",
)
@reads("people.piety", "people.population", "settlement.piety", "settlement.population")
async def native_faith(ctx: TickContext) -> None:
    gods = list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status != ForeignGodStatus.DEAD).order_by(ForeignGodRow.id)))
    struck = await struck_places(ctx.session, ctx.epoch)
    turned = 0
    for god in gods:
        turned += await turn_natives(ctx, god, struck)
        await feed_god(ctx, god)
    ctx.count("turned", turned)
    ctx.count("returned", await return_to_pantheon(ctx, gods))


async def syncretize(session: AsyncSession, rules: Rules, entity_id: int, god_id: int) -> str:
    entity = await session.get(EntityRow, entity_id)
    god = await session.get(ForeignGodRow, god_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in AGENT_TYPES:
        raise ValidationFailedError("Choose a living community or mortal.")
    if god is None or god.status is ForeignGodStatus.DEAD:
        raise ValidationFailedError("Choose a living old god.")
    if await holds_god(session, entity.id, god.id):
        raise ValidationFailedError(f"{entity.name} already worships {god.name}.")
    ctx = await manual_context(session, "syncretize", rules, key=f"{entity_id}:{god_id}")
    patron = await patron_son(session, entity)
    await adopt_old_god(ctx, entity, god, patron is not None, "the Creator wove the two faiths together")
    text = f"The Creator wove the faith of {entity.name} together with the old rites of {god.name}."
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key="native_faith.syncretized", entity_ids=[entity.id])
    return text


async def run_native_faith(session: AsyncSession, rules: Rules) -> None:
    await native_faith(await manual_context(session, "native_faith", rules))


PHASES = (Phase("native_faith", native_faith),)
