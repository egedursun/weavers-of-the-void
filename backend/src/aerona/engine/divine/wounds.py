from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.divine import NEGLECT_KINDS, STRUCK_KINDS, WOUND_CAUSES, WOUND_LABELS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.fixups import fixup_due
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.divine import AvatarRow, DivineStandingRow, DivineWoundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import DivineWoundKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import HoldingKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import ExistenceMode, SonDeathCause
from aerona.domain.models.profiles import ExistenceProfile
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, faithful_communities, god_of, living_gods
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.standing import ended_ids
from aerona.engine.recording.record import record

W = DivineWoundKind
NEGLECT_FIXUP = "divine_wounds.w52"


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
    if kind is W.LOST_WORSHIPPERS:
        await lose_worshippers(ctx, god, row.severity)
    if kind is W.SHATTERED_MANIFESTATION:
        for avatar in await ctx.session.scalars(select(AvatarRow).where(AvatarRow.god_node_id == god.id)):
            await ctx.session.delete(avatar)
        await scatter(ctx.session, god, row)
        await ctx.session.flush()
    tail = f" ({spoken(row.domain)})" if row.domain is not None else ""
    await record(
        ctx,
        f"divine.wound_{kind.value}",
        roles={IncidentRole.SUBJECT: god.id, IncidentRole.ACTOR: cause_node_id},
        facts={"wound": kind, "wound_label": WOUND_LABELS[kind].lower(), "tail": tail, "cause": cause, "cause_label": WOUND_CAUSES[cause].label},
        kind=ChronicleKind.CHALLENGE,
        son_id=god.id if isinstance(god, SonRow) else None,
    )
    return row


async def strike(ctx: TickContext, loser: God, winner_id: int | None, cause: WoundCause, margin: int) -> DivineWoundRow | None:
    table = ctx.rules.divine_wounds
    rng = ctx.rng(f"divine_wound.{loser.id}.{'unknown' if winner_id is None else winner_id}")
    if not rng.chance(table.wound_chance + margin * table.chance_per_margin):
        return None
    weights = [table.severed_weight, table.shattered_weight, table.name_weight, *[table.wider_weight] * (len(STRUCK_KINDS) - 3)]
    kind = rng.weighted(list(STRUCK_KINDS), weights)
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


async def manifestation_broken(session: AsyncSession, god_id: int, split_at: int = PERCENT // 2) -> bool:
    return await worst(session, god_id, W.SHATTERED_MANIFESTATION) > 0 or await worst(session, god_id, W.SPLIT_ASPECT) >= split_at


async def bound_factor(session: AsyncSession, god_id: int) -> float:
    return max(0.0, 1 - await worst(session, god_id, W.BOUND) / PERCENT)


async def lose_worshippers(ctx: TickContext, god: God, severity: int) -> None:
    lost = 0
    for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], targets=[god.id]):
        if lost * PERCENT >= severity * ctx.rules.divine_wounds.worshippers_per_severity or held(bond.source_node_id):
            continue
        bond.state, bond.closed_epoch, bond.closed_reason = BondState.PAST, ctx.epoch, "turned from a wounded god"
        lost += 1


def drain(god: God, amount: int) -> None:
    if isinstance(god, SonRow):
        god.essence = max(0, god.essence - amount)
    else:
        god.faith = max(0, god.faith - amount)


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
        remembered = 1 - await worst(ctx.session, god.id, W.FORGOTTEN_NAME) / PERCENT / 2
        gain = (god.faith / max(1, table.faith_per_heal) + rites * table.rite_heal + table.base_heal) * remembered
        drained = await worst(ctx.session, god.id, W.DRAINED_ESSENCE)
        if drained:
            drain(god, drained * table.drain_pct // PERCENT)
        for row in wounds:
            if "healed" in row.locked or row.epoch == ctx.epoch:
                continue
            row.healed = clamp_int(row.healed + gain * PERCENT / max(1, row.severity), 0, PERCENT)
            if row.healed >= PERCENT:
                closed += 1
                await gather(ctx.session, row)
                await record(
                    ctx,
                    "divine.wound_healed",
                    roles={IncidentRole.SUBJECT: god.id},
                    facts={"wound": row.kind, "wound_label": WOUND_LABELS[row.kind].lower()},
                    kind=ChronicleKind.CHALLENGE,
                    son_id=god.id if isinstance(god, SonRow) else None,
                )
    return closed


async def avatar_slain(ctx: TickContext, avatar_id: int, slayer_id: int | None = None) -> DivineWoundRow | None:
    row = await ctx.session.get(AvatarRow, avatar_id)
    if row is None:
        return None
    god = await god_of(ctx.session, row.god_node_id)
    await ctx.session.delete(row)
    if god is None:
        return None
    slayer = await ctx.session.get(EntityRow, slayer_id) if slayer_id is not None else None
    cause = WoundCause.MORTAL_SLAYER if slayer is not None and slayer.entity_type is EntityType.MORTAL else WoundCause.AVATAR_SLAIN
    return await inflict(ctx, god, W.SHATTERED_MANIFESTATION, cause, severity=cause_severity(ctx, cause), cause_node_id=slayer_id)


def cause_severity(ctx: TickContext, cause: WoundCause, fallback: int = PERCENT // 2) -> int:
    found = WOUND_CAUSES[cause].severity
    return found(ctx.rules) if found is not None else fallback


async def neglect_wounds(ctx: TickContext) -> int:
    table = ctx.rules.divine_wounds
    wounded = 0
    for god in await living_gods(ctx.session):
        if held(god.id):
            continue
        regard = int(await ctx.session.scalar(select(func.count()).select_from(DivineStandingRow).where(DivineStandingRow.god_node_id == god.id)) or 0)
        if not regard:
            continue
        faithful = len(await faithful_communities(ctx.session, god.id))
        kind = W.FORGOTTEN_NAME if not faithful else W.LOST_WORSHIPPERS if faithful * PERCENT < regard * table.neglect_share else None
        if kind is None or await open_wounds(ctx.session, god.id, kind):
            continue
        if faithful and not ctx.rng(f"divine_wound.neglect.{god.id}.{ctx.epoch}").chance(table.neglect_pct):
            continue
        if await inflict(ctx, god, kind, WoundCause.NEGLECT, severity=table.neglect_severity) is not None:
            wounded += 1
    return wounded


async def worship_wounds(ctx: TickContext) -> int:
    table = ctx.rules.divine_wounds
    wounded = 0
    for god in await living_gods(ctx.session):
        if held(god.id):
            continue
        worship = list(
            await ctx.session.scalars(
                select(BondRow)
                .where(
                    BondRow.target_node_id == god.id,
                    BondRow.kind == BondKind.WORSHIPS,
                    BondRow.state == BondState.ACTIVE,
                    BondRow.source_node_id.not_in(ended_ids()),
                )
                .order_by(BondRow.id)
            )
        )
        cults = sorted({bond.source_node_id for bond in worship})
        splitter = worship[-1].source_node_id if worship else None
        temples = select(CultHoldingRow.holding_entity_id).where(CultHoldingRow.cult_entity_id.in_(cults), CultHoldingRow.kind == HoldingKind.TEMPLE)
        ruined = await ctx.session.scalar(
            select(EntityRow.id).where(EntityRow.id.in_(temples), EntityRow.status != EntityStatus.CANON, EntityRow.end_epoch == ctx.epoch).limit(1)
        )
        found = (
            (ruined is not None, W.DESECRATED_SEAT, WoundCause.NEGLECT),
            (len(cults) >= table.split_cults, W.SPLIT_WORSHIP, WoundCause.SCHISM),
        )
        for met, kind, cause in found:
            if not met or await open_wounds(ctx.session, god.id, kind):
                continue
            if not ctx.rng(f"divine_wound.{kind.value}.{god.id}.{ctx.epoch}").chance(table.worship_wound_pct):
                continue
            if (
                await inflict(ctx, god, kind, cause, severity=table.worship_wound_severity, cause_node_id=ruined if kind is W.DESECRATED_SEAT else splitter)
                is not None
            ):
                wounded += 1
    return wounded


async def betrayed(ctx: TickContext, god_id: int, traitor_id: int) -> DivineWoundRow | None:
    god = await god_of(ctx.session, god_id)
    if god is None or not ctx.rng(f"divine_wound.betrayal.{god_id}.{traitor_id}.{ctx.epoch}").chance(ctx.rules.divine_wounds.betrayal_pct):
        return None
    return await inflict(ctx, god, W.STOLEN_NAME, WoundCause.BETRAYAL, severity=ctx.rules.divine_wounds.betrayal_severity, cause_node_id=traitor_id)


DEALT_CAUSES = frozenset(cause for cause, spec in WOUND_CAUSES.items() if spec.dealt)


async def mark_neglect(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, NEGLECT_FIXUP):
        return 0
    rows = list(
        await ctx.session.scalars(
            select(DivineWoundRow)
            .where(DivineWoundRow.kind.in_(sorted(NEGLECT_KINDS)), DivineWoundRow.cause_node_id.is_(None), DivineWoundRow.cause.in_(sorted(DEALT_CAUSES)))
            .order_by(DivineWoundRow.id)
        )
    )
    moved = 0
    for row in rows:
        if "cause" not in row.locked and not held(row.god_node_id):
            row.cause = WoundCause.NEGLECT
            moved += 1
    ctx.session.add(AppliedFixupRow(key=NEGLECT_FIXUP, result={"wounds": moved}))
    await ctx.session.flush()
    return moved
