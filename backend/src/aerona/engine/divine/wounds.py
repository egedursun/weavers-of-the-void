from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.divine import AvatarRow, DivineWoundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import DivineWoundKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import ExistenceMode, SonDeathCause
from aerona.domain.models.profiles import ExistenceProfile
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, god_of, living_gods
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int

W = DivineWoundKind
WOUND_LABELS = {
    W.SEVERED_DOMAIN: "Severed domain",
    W.SHATTERED_MANIFESTATION: "Shattered manifestation",
    W.STOLEN_NAME: "Stolen true name",
    W.VOID_WOUND: "Wound of the void",
}


async def open_wounds(session: AsyncSession, god_id: int, kind: DivineWoundKind | None = None) -> list[DivineWoundRow]:
    statement = select(DivineWoundRow).where(DivineWoundRow.god_node_id == god_id, DivineWoundRow.healed < PERCENT)
    if kind is not None:
        statement = statement.where(DivineWoundRow.kind == kind)
    return list(await session.scalars(statement.order_by(DivineWoundRow.id)))


def set_mode(god: God, mode: ExistenceMode | None) -> None:
    god.existence_profile = (god.existence_profile or ExistenceProfile()).model_copy(update={"mode": mode})


async def scatter(session: AsyncSession, god: God, row: DivineWoundRow) -> None:
    earlier = [wound for wound in await open_wounds(session, god.id, W.SHATTERED_MANIFESTATION) if wound.id != row.id]
    row.prior_mode = earlier[0].prior_mode if earlier else (god.existence_profile.mode if god.existence_profile else None)
    set_mode(god, ExistenceMode.SCATTERED)


async def gather(session: AsyncSession, row: DivineWoundRow) -> None:
    if row.kind is not W.SHATTERED_MANIFESTATION:
        return
    if [wound for wound in await open_wounds(session, row.god_node_id, W.SHATTERED_MANIFESTATION) if wound.id != row.id]:
        return
    god = await god_of(session, row.god_node_id)
    if god is not None and not held(god.id):
        set_mode(god, row.prior_mode)


async def inflict(
    ctx: TickContext,
    god: God,
    kind: DivineWoundKind,
    cause: WoundCause,
    *,
    severity: int,
    cause_node_id: int | None = None,
    domain: Domain | None = None,
) -> DivineWoundRow | None:
    if held(god.id):
        return None
    if kind is W.SEVERED_DOMAIN:
        severed = {row.domain for row in await open_wounds(ctx.session, god.id, W.SEVERED_DOMAIN)}
        choices = [item for item in domains_of(god) if item not in severed]
        domain = domain if domain in choices else (ctx.rng(f"sever.{god.id}").pick(choices) if choices else None)
        if domain is None:
            return None
    row = DivineWoundRow(
        god_node_id=god.id,
        kind=kind,
        domain=domain if kind is W.SEVERED_DOMAIN else None,
        severity=clamp_int(severity, 1, PERCENT),
        healed=0,
        cause=cause,
        cause_node_id=cause_node_id,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if kind is W.SHATTERED_MANIFESTATION:
        for avatar in await ctx.session.scalars(select(AvatarRow).where(AvatarRow.god_node_id == god.id)):
            await ctx.session.delete(avatar)
        await scatter(ctx.session, god, row)
        await ctx.session.flush()
    tail = f" ({row.domain.value})" if row.domain is not None else ""
    await note(
        ctx,
        f"{god.name} suffered a divine wound: {WOUND_LABELS[kind].lower()}{tail}.",
        key=f"divine.wound_{kind.value}",
        son_id=god.id if isinstance(god, SonRow) else None,
        kind=ChronicleKind.CHALLENGE,
    )
    return row


async def strike(ctx: TickContext, loser: God, winner_id: int | None, cause: WoundCause, margin: int) -> DivineWoundRow | None:
    table = ctx.rules.divine_wounds
    rng = ctx.rng(f"divine_wound.{loser.id}.{winner_id}")
    if not rng.chance(table.wound_chance + margin * table.chance_per_margin):
        return None
    kinds = [W.SEVERED_DOMAIN, W.SHATTERED_MANIFESTATION, W.STOLEN_NAME]
    weights = [table.severed_weight, table.shattered_weight, table.name_weight]
    kind = rng.weighted(kinds, weights)
    return await inflict(ctx, loser, kind, cause, severity=table.base_severity + margin * table.severity_per_margin, cause_node_id=winner_id)


OUTER_TYPES = frozenset({EntityType.OUTER_BEING, EntityType.COSMIC_BEING})


async def death_cause(session: AsyncSession, god_id: int) -> SonDeathCause:
    wounds = sorted(await open_wounds(session, god_id), key=lambda row: (-(row.severity - row.healed), row.id))
    for wound in wounds:
        if wound.cause is WoundCause.CREATOR:
            return SonDeathCause.KILLED_BY_CREATOR
        if wound.cause is WoundCause.OUTER_BARGAIN:
            return SonDeathCause.COSMIC_HORROR
        if wound.cause_node_id is None:
            continue
        if await session.get(SonRow, wound.cause_node_id) is not None:
            return SonDeathCause.KILLED_BY_SIBLING
        if await session.get(ForeignGodRow, wound.cause_node_id) is not None:
            return SonDeathCause.FOREIGN_GOD
        outsider = await session.get(EntityRow, wound.cause_node_id)
        if outsider is not None and outsider.entity_type in OUTER_TYPES:
            return SonDeathCause.COSMIC_HORROR
    return SonDeathCause.FADING


async def worst(session: AsyncSession, god_id: int, kind: DivineWoundKind) -> int:
    found = await session.scalar(
        select(func.max(DivineWoundRow.severity)).where(DivineWoundRow.god_node_id == god_id, DivineWoundRow.kind == kind, DivineWoundRow.healed < PERCENT)
    )
    return int(found or 0)


async def name_exposure(session: AsyncSession, god_id: int, pct: int) -> float:
    return max(0.0, 1 - await worst(session, god_id, W.STOLEN_NAME) * pct / PERCENT / PERCENT)


async def sanity_ceiling(session: AsyncSession, god_id: int, pct: int) -> int:
    return clamp_int(PERCENT - await worst(session, god_id, W.VOID_WOUND) * pct / PERCENT, 0, PERCENT)


async def manifestation_broken(session: AsyncSession, god_id: int) -> bool:
    return await worst(session, god_id, W.SHATTERED_MANIFESTATION) > 0


async def devotion_rites(ctx: TickContext, god_id: int) -> int:
    book = await ctx.divine()
    count = 0
    casters = await ctx.session.scalars(select(CastingRow.caster_entity_id).where(CastingRow.epoch == ctx.epoch, CastingRow.succeeded.is_(True)))
    for caster in casters:
        if caster is not None and god_id in (await book.faithful_of(ctx.session, caster))[0]:
            count += 1
    return count


async def heal_wounds(ctx: TickContext) -> int:
    table = ctx.rules.divine_wounds
    closed = 0
    for god in await living_gods(ctx.session):
        wounds = await open_wounds(ctx.session, god.id)
        if not wounds or held(god.id):
            continue
        rites = await devotion_rites(ctx, god.id)
        gain = god.faith / max(1, table.faith_per_heal) + rites * table.rite_heal + table.base_heal
        for row in wounds:
            if "healed" in row.locked:
                continue
            row.healed = clamp_int(row.healed + gain * PERCENT / max(1, row.severity), 0, PERCENT)
            if row.healed >= PERCENT:
                closed += 1
                await gather(ctx.session, row)
                await note(
                    ctx,
                    f"{god.name}'s {WOUND_LABELS[row.kind].lower()} healed.",
                    key="divine.wound_healed",
                    son_id=god.id if isinstance(god, SonRow) else None,
                    kind=ChronicleKind.CHALLENGE,
                )
    return closed


async def avatar_slain(ctx: TickContext, avatar_id: int) -> DivineWoundRow | None:
    row = await ctx.session.get(AvatarRow, avatar_id)
    if row is None:
        return None
    god = await god_of(ctx.session, row.god_node_id)
    await ctx.session.delete(row)
    if god is None:
        return None
    table = ctx.rules.divine_wounds
    return await inflict(ctx, god, W.SHATTERED_MANIFESTATION, WoundCause.AVATAR_SLAIN, severity=table.avatar_severity)
