from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import SPEED_MAX, MindProfileRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import ENDED_STATUSES, EntityStatus, EntityType
from aerona.domain.enums.made import RealmPurpose
from aerona.domain.enums.minds import MindSeat, MindUpkeep
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.profiles import profile_of
from aerona.engine.minds.seat_loss import lose_seat
from aerona.engine.networks.book import running
from aerona.engine.notes import note
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.queries import connect

SELF_KEPT = frozenset({MindUpkeep.NONE, MindUpkeep.PLACE})


async def host_down(ctx: TickContext, realm: MadeRealmRow) -> bool:
    if realm.host_node_id is None:
        return False
    network = await ctx.session.get(NetworkProfileRow, realm.host_node_id)
    if network is not None:
        return not running(network, ctx.epoch)
    host = await ctx.session.get(EntityRow, realm.host_node_id)
    return host is not None and host.status is not EntityStatus.CANON


async def host_ended(ctx: TickContext, realm: MadeRealmRow) -> bool:
    if realm.host_node_id is None or realm.sealed or await ctx.session.get(NetworkProfileRow, realm.host_node_id) is not None:
        return False
    host = await ctx.session.get(EntityRow, realm.host_node_id)
    return host is None or host.status in ENDED_STATUSES


async def end_realm(ctx: TickContext, realm: MadeRealmRow) -> None:
    for mind in await minds_inside(ctx, realm):
        if not held(mind.node_id) and "seat" not in mind.locked:
            await lose_seat(ctx, mind)
    dimension = await ctx.session.get(DimensionRow, realm.dimension_id)
    if dimension is not None:
        dimension.stability = 0
    realm.sealed = True
    await note(ctx, "A made realm ended with what held it.", key="realm.ended", ids=[realm.dimension_id])


async def minds_inside(ctx: TickContext, realm: MadeRealmRow) -> list[MindProfileRow]:
    statement = (
        select(MindProfileRow).where(MindProfileRow.seat == MindSeat.REALM, MindProfileRow.seat_node_id == realm.dimension_id).order_by(MindProfileRow.node_id)
    )
    return list(await ctx.session.scalars(statement))


async def realm_of(ctx: TickContext, realm_id: int) -> MadeRealmRow:
    row = await ctx.session.get(MadeRealmRow, realm_id)
    if row is None:
        raise ValidationFailedError("No such made realm.")
    if row.sealed:
        raise ValidationFailedError("That realm is sealed; no one goes in or out.")
    return row


async def enter_realm(ctx: TickContext, mind_id: int, realm_id: int) -> MindProfileRow:
    realm = await realm_of(ctx, realm_id)
    if held(mind_id):
        raise ValidationFailedError("That mind is held against the world.")
    mind = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
    if realm.host_node_id is not None and realm.host_node_id != mind_id:
        await connect(ctx.session, mind_id, realm.host_node_id, BondKind.HOSTED_BY, ctx.epoch, description="runs in a realm this hosts")
    await ctx.session.flush()
    await note(ctx, "A mind went into a made realm.", key="realm.entered", ids=[mind_id, realm.dimension_id])
    return mind


async def withdraw(ctx: TickContext, people_id: int, realm_id: int) -> int:
    realm = await realm_of(ctx, realm_id)
    among = await folk_among(ctx.session, [people_id])
    living = (among, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    folk = await ctx.session.scalars(select(EntityRow.id).where(*living))
    moved = 0
    for mortal in list(folk):
        if held(mortal):
            continue
        mind = await profile_of(ctx.session, ctx.rules, mortal, ctx.epoch)
        mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
        moved += 1
    await note(ctx, "A people withdrew into a made realm.", key="realm.withdrawal", ids=[people_id, realm.dimension_id])
    return moved


async def escapes(ctx: TickContext, realm: MadeRealmRow, minds: list[MindProfileRow]) -> None:
    if realm.realm_purpose is not RealmPurpose.CONFINEMENT or realm.sealed:
        return
    for mind in minds:
        if held(mind.node_id) or not ctx.rng(f"realm.escape.{mind.node_id}.{ctx.epoch}").chance(ctx.rules.made_realms.escape_pct):
            continue
        mind.seat, mind.seat_node_id = MindSeat.BODY, mind.node_id
        await note(ctx, "A mind got out of the realm it was confined in.", key="realm.escape", ids=[mind.node_id, realm.dimension_id])


async def keep_realm(ctx: TickContext, realm: MadeRealmRow) -> None:
    table = ctx.rules.made_realms
    keeper = await ctx.session.get(EntityRow, realm.keeper_node_id) if realm.keeper_node_id is not None else None
    if await host_ended(ctx, realm):
        await end_realm(ctx, realm)
        return
    if await host_down(ctx, realm) and "frozen_until_epoch" not in realm.locked:
        if realm.frozen_until_epoch <= ctx.epoch:
            await note(ctx, "A made realm stood still when what held it went down.", key="realm.frozen", ids=[realm.dimension_id])
        realm.frozen_until_epoch = ctx.epoch + table.freeze_epochs
    unpaid = realm.upkeep not in SELF_KEPT and keeper is not None and await points_of(ctx.session, keeper) < table.upkeep_wealth
    if unpaid and "fidelity" not in realm.locked:
        realm.fidelity = clamp_percent(realm.fidelity - 1)
    frozen = realm.frozen_until_epoch > ctx.epoch
    ratio = clamp_int(realm.time_ratio_pct, max(table.time_ratio_min, ctx.rules.minds.speed_min), table.time_ratio_max)
    minds = await minds_inside(ctx, realm)
    for mind in minds:
        if held(mind.node_id):
            continue
        if "dormant" not in mind.locked:
            mind.dormant = frozen
        if "speed_pct" not in mind.locked:
            mind.speed_pct = clamp_int(ratio, 1, SPEED_MAX)
    await escapes(ctx, realm, minds)
    working = sum(1 for mind in minds if not mind.dormant)
    if realm.realm_purpose is RealmPurpose.LABOUR and keeper is not None and not frozen and working and not held(keeper.id):
        await shift_points(ctx.session, keeper, round_half_up(table.labour_yield * working * ratio / PERCENT))


@reads("table.entities", "table.made_realm_profiles", "table.made_realms", "table.mind_profiles", "table.mortal_profiles", "table.network_profiles")
@writes("table.entities", "table.made_realms", "table.mind_profiles", "table.mortal_profiles")
async def keep_realms(ctx: TickContext) -> None:
    for realm in list(await ctx.session.scalars(select(MadeRealmRow).order_by(MadeRealmRow.dimension_id))):
        if held(realm.dimension_id):
            continue
        await keep_realm(ctx, realm)
        ctx.count("made_realms_kept")
    await ctx.session.flush()
