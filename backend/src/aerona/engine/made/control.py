from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.made import (
    AugmentEffectRow,
    AugmentRow,
    CompanyHoldingRow,
    DataStoreContentRow,
    DataStoreRow,
    MadeRealmRow,
    MadeRelicRow,
    PatternRightRow,
    ReplicatorLineRow,
    ReplicatorPresenceRow,
    SalvageSiteRow,
)
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.networks import NetworkGatewayRow, NetworkNodeRow, NetworkOutageRow, NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import DimensionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import (
    Authenticity,
    CompanyHoldingKind,
    DataContent,
    EffectTarget,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    RelicState,
    RelicUse,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindUpkeep
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole, OutageCause
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import NetworkStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.networks.book import carrier_days, shake_ledger
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.records import RecordSpec, create_record

NETWORK_POWER = 5


async def living(ctx: TickContext, node_id: int, what: str) -> EntityRow:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError(f"No living {what} by that number.")
    return entity


async def found_network(ctx: TickContext, owner_id: int | None, name: str, carrier: NetworkCarrier, place_id: int | None) -> NetworkProfileRow:
    place = await living(ctx, place_id, "place") if place_id is not None else None
    owner = await living(ctx, owner_id, "owner") if owner_id is not None else None
    anchor = place or owner
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.NETWORK,
            name=name,
            body=f"A network founded in epoch {ctx.epoch}.",
            stats=NetworkStats(reach=0),
            power=NETWORK_POWER,
            location_id=anchor.id if anchor is not None and anchor.entity_type is not EntityType.POLITY else None,
            world_id=anchor.world_id if anchor is not None else None,
        ),
    )
    row = NetworkProfileRow(network_entity_id=entity.id, carrier=carrier, owner_node_id=owner_id, founded_epoch=ctx.epoch, locked=[])
    row.delay_days = carrier_days(ctx.rules, carrier)
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"{entity.name} was founded.", key="network.founded", ids=[entity.id])
    return row


async def network_of(ctx: TickContext, network_id: int) -> NetworkProfileRow:
    row = await ctx.session.get(NetworkProfileRow, network_id)
    if row is None:
        raise NotFoundError("No such network.")
    return row


async def join_network(ctx: TickContext, network_id: int, member_id: int, role: NetworkRole) -> NetworkNodeRow:
    await network_of(ctx, network_id)
    await living(ctx, member_id, "member")
    row = NetworkNodeRow(network_entity_id=network_id, member_node_id=member_id, role=role, dependency_pct=0, security=0, joined_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def link_networks(ctx: TickContext, first_id: int, second_id: int, *, toll: int, filter_pct: int, owner_id: int | None) -> NetworkGatewayRow:
    if first_id == second_id:
        raise ValidationFailedError("A gateway joins two different networks.")
    await network_of(ctx, first_id)
    await network_of(ctx, second_id)
    row = NetworkGatewayRow(
        first_network_id=first_id, second_network_id=second_id, toll=max(0, toll), filter_pct=clamp_percent(filter_pct), owner_node_id=owner_id
    )
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def cut_network(ctx: TickContext, network_id: int, cause: OutageCause, epochs: int, severity: int) -> NetworkOutageRow:
    network = await network_of(ctx, network_id)
    network.down_until_epoch = max(network.down_until_epoch, ctx.epoch + max(1, epochs))
    row = NetworkOutageRow(network_entity_id=network_id, cause=cause, epoch=ctx.epoch, epochs=max(1, epochs), severity=clamp_percent(severity))
    ctx.session.add(row)
    await shake_ledger(ctx.session, ctx.rules, network_id)
    await ctx.session.flush()
    await note(ctx, "A network went down.", key="network.cut", ids=[network_id])
    return row


async def add_effect(ctx: TickContext, augment_id: int, target: EffectTarget, key: str, amount: int) -> AugmentEffectRow:
    if await ctx.session.get(AugmentRow, augment_id) is None:
        raise NotFoundError("No such augment.")
    row = AugmentEffectRow(augment_id=augment_id, target=target, target_key=key, amount=clamp_int(amount, -PERCENT, PERCENT), locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


EFFECT_FIELDS = ("target", "target_key", "amount")


async def edit_effect(ctx: TickContext, effect_id: int, values: Values, release: list[str]) -> AugmentEffectRow:
    row = apply(await found(ctx, AugmentEffectRow, effect_id, "effect"), allowed(values, EFFECT_FIELDS, "effect"), release)
    await ctx.session.flush()
    return row


async def drop_effect(ctx: TickContext, effect_id: int) -> int:
    row = await ctx.session.get(AugmentEffectRow, effect_id)
    if row is None:
        raise NotFoundError("No such effect.")
    augment = row.augment_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    return augment


@dataclass(frozen=True)
class RealmDraft:
    name: str
    keeper_id: int | None
    host_id: int | None
    purpose: RealmPurpose
    time_ratio_pct: int
    entry: RealmEntry
    aware: RealmAwareness
    upkeep: MindUpkeep


async def make_realm(ctx: TickContext, draft: RealmDraft) -> MadeRealmRow:
    table = ctx.rules.made_realms
    dimension = await create_dimension(ctx.session, ctx.rules, DimensionDraft(name=draft.name, kind=DimensionKind.MADE, epoch=ctx.epoch))
    row = MadeRealmRow(
        dimension_id=dimension.id,
        host_node_id=draft.host_id,
        keeper_node_id=draft.keeper_id,
        realm_purpose=draft.purpose,
        time_ratio_pct=clamp_int(draft.time_ratio_pct, table.time_ratio_min, table.time_ratio_max),
        fidelity=PERCENT,
        entry=draft.entry,
        aware_inside=draft.aware,
        upkeep=draft.upkeep,
        frozen_until_epoch=0,
        sealed=False,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"{dimension.name} was made.", key="realm.made", ids=[dimension.id])
    return row


async def open_store(ctx: TickContext, holder_id: int, owner_id: int | None, security: int) -> DataStoreRow:
    await living(ctx, holder_id, "holder")
    row = DataStoreRow(holder_node_id=holder_id, security=clamp_percent(security), owner_node_id=owner_id, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def put_content(ctx: TickContext, store_id: int, content: DataContent, subject_id: int | None, reference: int | None) -> DataStoreContentRow:
    if await ctx.session.get(DataStoreRow, store_id) is None:
        raise NotFoundError("No such store.")
    row = DataStoreContentRow(store_id=store_id, content=content, subject_node_id=subject_id, reference=reference, epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def take_content(ctx: TickContext, content_id: int) -> int:
    row = await ctx.session.get(DataStoreContentRow, content_id)
    if row is None:
        raise NotFoundError("No such content.")
    store = row.store_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    return store


async def mark_record(ctx: TickContext, account_id: int, authenticity: Authenticity) -> AccountRow:
    row = await ctx.session.get(AccountRow, account_id)
    if row is None:
        raise NotFoundError("No such record.")
    row.authenticity = authenticity
    row.locked = sorted({*row.locked, "authenticity"})
    await ctx.session.flush()
    return row


async def hold_for(ctx: TickContext, company_id: int, holding_id: int, kind: CompanyHoldingKind) -> CompanyHoldingRow:
    if await ctx.session.get(CompanyProfileRow, company_id) is None:
        raise NotFoundError("No such company.")
    await living(ctx, holding_id, "holding")
    row = CompanyHoldingRow(company_entity_id=company_id, holding_node_id=holding_id, kind=kind, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


@dataclass(frozen=True)
class LineDraft:
    name: str
    scale: ReplicatorScale
    feedstock: MaterialKind
    output: ReplicatorOutput
    growth_pct: int
    error_pct: int
    containment: int
    kill_switch: bool
    owner_id: int | None
    maker_id: int | None
    place_id: int
    mass: int


async def found_line(ctx: TickContext, draft: LineDraft) -> ReplicatorLineRow:
    if held(draft.place_id):
        raise ValidationFailedError("That place is held against the world.")
    row = ReplicatorLineRow(
        name=draft.name,
        scale=draft.scale,
        feedstock=draft.feedstock,
        output=draft.output,
        growth_pct=clamp_percent(draft.growth_pct),
        error_pct=clamp_percent(draft.error_pct),
        set_id=None,
        containment=clamp_percent(draft.containment),
        kill_switch=draft.kill_switch,
        owner_node_id=draft.owner_id,
        maker_node_id=draft.maker_id,
        mind_node_id=None,
        stage=ReplicatorStage.WORKING,
        drifted_from_id=None,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    ctx.session.add(ReplicatorPresenceRow(line_id=row.id, place_node_id=draft.place_id, mass=max(1, draft.mass), growth=PERCENT, locked=[]))
    await ctx.session.flush()
    await note(ctx, f"{row.name} began to make itself.", key="replicator.founded", ids=[draft.place_id])
    return row


async def line_of(ctx: TickContext, line_id: int) -> ReplicatorLineRow:
    row = await ctx.session.get(ReplicatorLineRow, line_id)
    if row is None:
        raise NotFoundError("No such line.")
    return row


async def stop_line(ctx: TickContext, line_id: int) -> ReplicatorLineRow:
    row = await line_of(ctx, line_id)
    row.stage = ReplicatorStage.STOPPED
    row.locked = sorted({*row.locked, "stage"})
    await ctx.session.flush()
    await note(ctx, f"{row.name} was stopped.", key="replicator.stopped", ids=[])
    return row


async def seed_line(ctx: TickContext, line_id: int, place_id: int, mass: int) -> ReplicatorPresenceRow:
    await line_of(ctx, line_id)
    row = ReplicatorPresenceRow(line_id=line_id, place_node_id=place_id, mass=max(1, mass), growth=PERCENT, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def lift_presence(ctx: TickContext, presence_id: int) -> int:
    row = await ctx.session.get(ReplicatorPresenceRow, presence_id)
    if row is None:
        raise NotFoundError("No such presence.")
    line = row.line_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    return line


async def grant_pattern(ctx: TickContext, commodity: Commodity, holder_id: int | None, fee: int, is_open: bool) -> PatternRightRow:
    row = PatternRightRow(commodity=commodity, holder_node_id=holder_id, licence_fee=max(0, fee), open=is_open, since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def mark_relic(ctx: TickContext, thing_id: int, make_knowledge: int, repair_knowledge: int) -> MadeRelicRow:
    await living(ctx, thing_id, "thing")
    row = await ctx.session.get(MadeRelicRow, thing_id)
    if row is None:
        row = MadeRelicRow(
            thing_node_id=thing_id, function_state=RelicState.WORKING, understood_pct=0, use=RelicUse.AS_MADE, updated_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    row.make_knowledge, row.repair_knowledge, row.is_relic = max(0, make_knowledge), max(0, repair_knowledge), True
    await ctx.session.flush()
    return row


async def open_salvage(ctx: TickContext, site_id: int, holder_id: int | None, yield_left: int) -> SalvageSiteRow:
    await living(ctx, site_id, "site")
    row = await ctx.session.get(SalvageSiteRow, site_id)
    if row is None:
        row = SalvageSiteRow(site_entity_id=site_id, last_salvaged_epoch=None, locked=[])
        ctx.session.add(row)
    row.rights_holder_node_id, row.yield_left = holder_id, max(0, yield_left)
    await ctx.session.flush()
    return row


async def reset_mind(ctx: TickContext, mind_id: int) -> None:
    row = await ctx.session.get(MindProfileRow, mind_id)
    if row is None:
        raise NotFoundError("No such mind.")
    await ctx.session.delete(row)
    await ctx.session.flush()
