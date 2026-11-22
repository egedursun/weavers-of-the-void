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
from aerona.domain.enums.made import RealmAwareness, RealmEntry, RealmPurpose
from aerona.domain.enums.minds import MindSeat, MindUpkeep
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.made.control import RealmDraft, make_realm
from aerona.engine.made.kinds import AWARE_ESCAPE, PURPOSES, entry_refused
from aerona.engine.minds.profiles import profile_of
from aerona.engine.minds.seat_loss import lose_seat
from aerona.engine.networks.book import running
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.recording.record import StepDraft, record

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
    await record(
        ctx,
        "realm.ended",
        roles={IncidentRole.SUBJECT: realm.dimension_id, IncidentRole.OWNER: realm.host_node_id},
        facts={"purpose": realm.realm_purpose},
        steps=(StepDraft(StepAction.CLOSE, target=realm.dimension_id, outcome=StepOutcome.DESTROYED),),
    )


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
    refused = await entry_refused(ctx, realm, mind_id)
    if refused is not None:
        raise ValidationFailedError(f"{refused[0].upper()}{refused[1:]}.")
    mind = await profile_of(ctx.session, ctx.rules, mind_id, ctx.epoch)
    mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
    if realm.host_node_id is not None and realm.host_node_id != mind_id:
        await connect(ctx.session, mind_id, realm.host_node_id, BondKind.HOSTED_BY, ctx.epoch, description="runs in a realm this hosts")
    await ctx.session.flush()
    await record(
        ctx,
        "realm.entered",
        roles={IncidentRole.ACTOR: mind_id, IncidentRole.DESTINATION: realm.dimension_id},
        facts={"purpose": realm.realm_purpose, "time_ratio": realm.time_ratio_pct},
        steps=(StepDraft(StepAction.ENTER, actor=mind_id, locus_kind=StepLocus.REALM, locus_node=realm.dimension_id),),
    )
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
    await record(
        ctx,
        "realm.withdrawal",
        roles={IncidentRole.ACTOR: people_id, IncidentRole.DESTINATION: realm.dimension_id},
        facts={"moved": moved, "purpose": realm.realm_purpose},
        steps=(StepDraft(StepAction.ENTER, actor=people_id, locus_kind=StepLocus.REALM, locus_node=realm.dimension_id, amount=moved, unit=FactUnit.PEOPLE),),
    )
    return moved


async def escapes(ctx: TickContext, realm: MadeRealmRow, minds: list[MindProfileRow]) -> None:
    if realm.realm_purpose is not RealmPurpose.CONFINEMENT or realm.sealed:
        return
    for mind in minds:
        chance = ctx.rules.made_realms.escape_pct * AWARE_ESCAPE[realm.aware_inside] // PERCENT
        if held(mind.node_id) or not ctx.rng(f"realm.escape.{mind.node_id}.{ctx.epoch}").chance(chance):
            continue
        mind.seat, mind.seat_node_id = MindSeat.BODY, mind.node_id
        await record(
            ctx,
            "realm.escape",
            roles={IncidentRole.ACTOR: mind.node_id, IncidentRole.ORIGIN: realm.dimension_id},
            facts={"chance": chance, "awareness": realm.aware_inside},
            steps=(StepDraft(StepAction.ESCAPE, actor=mind.node_id, locus_kind=StepLocus.REALM, locus_node=realm.dimension_id, outcome=StepOutcome.ESCAPED),),
        )


async def admit_by_entry(ctx: TickContext, realm: MadeRealmRow, keeper: EntityRow | None) -> int:
    if keeper is None or realm.entry not in {RealmEntry.DEATH, RealmEntry.BIRTH}:
        return 0
    kin = (EntityRow.entity_type == EntityType.MORTAL, EntityRow.affiliated_entity_id == keeper.id)
    if realm.entry is RealmEntry.BIRTH:
        found = select(EntityRow.id).where(*kin, EntityRow.birth_epoch == ctx.epoch, EntityRow.status == EntityStatus.CANON)
    else:
        found = select(EntityRow.id).where(*kin, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch)
    admitted = 0
    for being in list(await ctx.session.scalars(found)):
        if held(being):
            continue
        mind = await profile_of(ctx.session, ctx.rules, being, ctx.epoch)
        if mind.seat is not MindSeat.REALM:
            mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
            admitted += 1
    return admitted


async def keep_realm(ctx: TickContext, realm: MadeRealmRow) -> None:
    table = ctx.rules.made_realms
    keeper = await ctx.session.get(EntityRow, realm.keeper_node_id) if realm.keeper_node_id is not None else None
    if await host_ended(ctx, realm):
        await end_realm(ctx, realm)
        return
    if await host_down(ctx, realm) and "frozen_until_epoch" not in realm.locked:
        if realm.frozen_until_epoch <= ctx.epoch:
            await record(
                ctx,
                "realm.frozen",
                roles={IncidentRole.SUBJECT: realm.dimension_id, IncidentRole.OWNER: realm.host_node_id},
                facts={"epochs": table.freeze_epochs},
            )
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
    await admit_by_entry(ctx, realm, keeper)
    if not frozen:
        await PURPOSES[realm.realm_purpose](ctx, realm, minds, keeper)
    working = sum(1 for mind in minds if not mind.dormant)
    if realm.realm_purpose is RealmPurpose.LABOUR and keeper is not None and not frozen and working and not held(keeper.id):
        await shift_points(ctx.session, keeper, round_half_up(table.labour_yield * working * ratio / PERCENT))


UNHOUSED_SEATS = (MindSeat.STRUCTURE, MindSeat.NETWORK, MindSeat.OBJECT)


async def realm_on(ctx: TickContext, host_id: int) -> MadeRealmRow | None:
    query = select(MadeRealmRow).where(MadeRealmRow.host_node_id == host_id, MadeRealmRow.sealed.is_(False)).order_by(MadeRealmRow.dimension_id)
    return await ctx.session.scalar(query.limit(1))


async def house_minds(ctx: TickContext) -> int:
    query = select(MindProfileRow).where(MindProfileRow.seat.in_(UNHOUSED_SEATS), MindProfileRow.seat_node_id.is_not(None)).order_by(MindProfileRow.node_id)
    housed = 0
    for mind in list(await ctx.session.scalars(query)):
        host_id = mind.seat_node_id
        if host_id is None or held(mind.node_id, host_id) or "seat" in (mind.locked or []):
            continue
        if not ctx.rng(f"realm.dwell.{mind.node_id}.{ctx.epoch}").chance(ctx.rules.made_realms.dwelling_pct):
            continue
        realm = await realm_on(ctx, host_id)
        if realm is None:
            host = await ctx.session.get(EntityRow, host_id)
            name = f"the realm within {host.name}" if host is not None else "a made realm"
            draft = RealmDraft(name, mind.node_id, host_id, RealmPurpose.DWELLING, PERCENT, RealmEntry.TRANSFER, RealmAwareness.KNOWS, MindUpkeep.MAINTENANCE)
            realm = await make_realm(ctx, draft)
        try:
            await enter_realm(ctx, mind.node_id, realm.dimension_id)
        except ValidationFailedError:
            continue
        housed += 1
    return housed


@reads("table.entities", "table.made_realm_profiles", "table.made_realms", "table.mind_profiles", "table.mortal_profiles", "table.network_profiles")
@writes("table.entities", "table.made_realms", "table.mind_profiles", "table.mortal_profiles")
async def keep_realms(ctx: TickContext) -> None:
    ctx.count("minds_housed", await house_minds(ctx))
    for realm in list(await ctx.session.scalars(select(MadeRealmRow).order_by(MadeRealmRow.dimension_id))):
        if held(realm.dimension_id):
            continue
        await keep_realm(ctx, realm)
        ctx.count("made_realms_kept")
    await ctx.session.flush()
