from collections.abc import Awaitable, Callable

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.networks import NetworkOutageRow, NetworkProfileRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.faith import BindingKind, SpiritAlignment
from aerona.domain.enums.networks import OutageCause
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int

Keep = Callable[[TickContext, int, int], Awaitable[None]]


async def realm_of_caster(ctx: TickContext, caster_id: int) -> int | None:
    return await ctx.session.scalar(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == caster_id).order_by(OfficeRow.id).limit(1))


async def network_of_caster(ctx: TickContext, caster_id: int) -> int | None:
    return await ctx.session.scalar(
        select(NetworkProfileRow.network_entity_id).where(NetworkProfileRow.owner_node_id == caster_id).order_by(NetworkProfileRow.network_entity_id).limit(1)
    )


async def line_of_caster(ctx: TickContext, caster_id: int) -> int | None:
    return await ctx.session.scalar(
        select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == caster_id, HouseMemberRow.by_marriage.is_(False)).limit(1)
    )


async def wider_binding(ctx: TickContext, caster_id: int) -> tuple[BindingKind, int] | None:
    for kind, find in ((BindingKind.REALM, realm_of_caster), (BindingKind.NETWORK, network_of_caster), (BindingKind.LINE, line_of_caster)):
        found = await find(ctx, caster_id)
        if found is not None and not held(found):
            return kind, found
    return None


def sign_of(alignment: SpiritAlignment) -> int:
    return -1 if alignment is SpiritAlignment.VENGEFUL else 1


WIDER_KEEPS: Handlers[BindingKind, Keep] = Handlers(BindingKind)


@WIDER_KEEPS.on(BindingKind.REALM)
async def keep_realm(ctx: TickContext, realm_id: int, sign: int) -> None:
    profile = await ctx.session.get(PolityProfileRow, realm_id)
    if profile is not None and "legitimacy" not in profile.locked:
        profile.legitimacy = clamp_int(profile.legitimacy + sign * ctx.rules.spirits.bound_step, 0, PERCENT)


@WIDER_KEEPS.on(BindingKind.NETWORK)
async def keep_network(ctx: TickContext, network_id: int, sign: int) -> None:
    if sign < 0:
        outage = NetworkOutageRow(network_entity_id=network_id, cause=OutageCause.RITE, epoch=ctx.epoch)
        outage.epochs, outage.severity = 1, ctx.rules.spirits.haunt_severity
        ctx.session.add(outage)
        return
    for outage in list(await ctx.session.scalars(select(NetworkOutageRow).where(NetworkOutageRow.network_entity_id == network_id))):
        outage.epochs = max(0, outage.epochs - 1)


@WIDER_KEEPS.on(BindingKind.LINE)
async def keep_line(ctx: TickContext, house_id: int, sign: int) -> None:
    profile = await ctx.session.get(HouseProfileRow, house_id)
    if profile is not None and "prestige" not in profile.locked:
        profile.prestige = clamp_int(profile.prestige + sign * ctx.rules.spirits.bound_step, 0, PERCENT)


async def keep_bound_spirits(ctx: TickContext) -> int:
    kept = 0
    rows = await ctx.session.scalars(
        select(SpiritProfileRow)
        .where(SpiritProfileRow.binding.in_(list(WIDER_KEEPS)), SpiritProfileRow.bound_entity_id.is_not(None))
        .order_by(SpiritProfileRow.spirit_entity_id)
    )
    for spirit in list(rows):
        bound = spirit.bound_entity_id
        if bound is None or held(bound):
            continue
        await WIDER_KEEPS[spirit.binding](ctx, bound, sign_of(spirit.alignment))
        kept += 1
    return kept
