from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import BeingPhase
from aerona.domain.enums.economy import MaterialOrigin
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.book import ensure_body
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.deposits import new_substance
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import set_stats, stat

VAST = (EntityType.COSMIC_BEING, EntityType.OUTER_BEING)
FORCE_MAX = 10
REMAINS_PREFIX = "cosmic_wounds.remains."


@dataclass
class WoundTally:
    healed: int = 0
    remains: int = 0


async def effective_might(session: AsyncSession, being: EntityRow, might: int) -> int:
    body = await session.get(BodyRow, being.id)
    if body is None:
        return might
    return round_half_up(might * body.vital / PERCENT * (0.5 + body.presence / (2 * PERCENT)))


async def can_roam(session: AsyncSession, rules_floor: int, being: EntityRow) -> bool:
    body = await session.get(BodyRow, being.id)
    return body is None or body.mobility >= rules_floor


async def can_see(session: AsyncSession, rules_floor: int, being: EntityRow) -> bool:
    body = await session.get(BodyRow, being.id)
    return body is None or body.sight >= rules_floor


async def wound_being(ctx: TickContext, being: EntityRow, damage: float, cause: HarmCause, why: str, *, killer_id: int | None = None) -> WoundOutcome | None:
    if being.entity_type not in VAST or being.status is not EntityStatus.CANON or held(being.id) or damage <= 0:
        return None
    await ensure_body(ctx.session, ctx.rules, being, ctx.epoch)
    scaled = damage * ctx.rules.cosmic_wounds.damage_pct / PERCENT
    wounding = await apply_hits(ctx, being, Harm(scaled, cause, why, killer_id=killer_id, source_node_id=killer_id))
    if wounding.outcome is WoundOutcome.DIED:
        await note(ctx, f"{being.name} was slain: {why}.", key="cosmic_wounds.slain", ids=[being.id], world_id=being.world_id, kind=ChronicleKind.MIRACLE)
    return wounding.outcome


async def strike(ctx: TickContext, being_id: int, force: int, why: str) -> WoundOutcome:
    being = await ctx.session.get(EntityRow, being_id)
    if being is None:
        raise NotFoundError("No such being.")
    if being.entity_type not in VAST:
        raise ValidationFailedError(f"{being.name} is no cosmic or outer being.")
    outcome = await wound_being(ctx, being, ctx.rules.cosmic_wounds.strike_harm * force, HarmCause.GOD, why)
    if outcome is None:
        raise ValidationFailedError(f"{being.name} cannot be struck now.")
    return outcome


async def regrow(ctx: TickContext, being: EntityRow, tally: WoundTally) -> None:
    body = await ensure_body(ctx.session, ctx.rules, being, ctx.epoch)
    hp = stat(being, "hp")
    if hp is None or hp >= body.hp_max:
        return
    profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
    rate = ctx.rules.cosmic_wounds.heal_pct
    if profile is not None and profile.phase is BeingPhase.BOUND:
        rate = round_half_up(rate * ctx.rules.cosmic_wounds.bound_heal_pct / PERCENT)
    set_stats(being, hp=min(body.hp_max, hp + round_half_up(body.hp_max * rate / PERCENT)))
    tally.healed += 1


async def leave_remains(ctx: TickContext, being: EntityRow, tally: WoundTally) -> None:
    key = f"{REMAINS_PREFIX}{being.id}"
    if await ctx.session.get(AppliedFixupRow, key) is not None:
        return
    place = await ctx.session.get(EntityRow, being.location_id) if being.location_id is not None else None
    if place is not None:
        await new_substance(ctx, MaterialOrigin.GOD_REMAINS, place, source_node_id=being.id)
        tally.remains += 1
    ctx.session.add(AppliedFixupRow(key=key, result={"remains": place.id if place is not None else None}))


async def tend_beings(ctx: TickContext) -> WoundTally:
    tally = WoundTally()
    for being in list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type.in_(VAST)).order_by(EntityRow.id))):
        if held(being.id):
            continue
        if being.status is EntityStatus.CANON:
            await regrow(ctx, being, tally)
        elif being.status is EntityStatus.DEAD and await ctx.session.get(BodyRow, being.id) is not None:
            await leave_remains(ctx, being, tally)
    return tally
