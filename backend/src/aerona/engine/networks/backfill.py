from collections import defaultdict

from sqlalchemy import select

from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.communication import SignalState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole
from aerona.domain.models.entity_stats import NetworkStats
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import polities, realm_towns
from aerona.engine.lore.civics import holders_know
from aerona.engine.networks.book import carrier_days
from aerona.engine.primitives.records import RecordSpec, create_record

RELAY_FIXUP = "networks.relay_backfill"
RELAY_POWER = 5


async def relay(
    ctx: TickContext, owner: EntityRow, places: list[int], name: str, *, carrier: NetworkCarrier = NetworkCarrier.RELAY, capacity: int | None = None
) -> bool:
    if not places or held(owner.id):
        return False
    anchor = await ctx.session.get(EntityRow, places[0])
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.NETWORK,
            name=name,
            body=f"A relay network of {owner.name}, kept from before networks were counted.",
            stats=NetworkStats(reach=len(places)),
            power=RELAY_POWER,
            location_id=anchor.id if anchor is not None and anchor.entity_type in {EntityType.REGION, EntityType.SETTLEMENT} else None,
            world_id=anchor.world_id if anchor is not None else owner.world_id,
        ),
    )
    profile = NetworkProfileRow(network_entity_id=entity.id, carrier=carrier, owner_node_id=owner.id, founded_epoch=ctx.epoch, locked=[])
    profile.delay_days = carrier_days(ctx.rules, carrier)
    if capacity is not None:
        profile.capacity = capacity
    ctx.session.add(profile)
    for index, place in enumerate(places):
        role = NetworkRole.HUB if index == 0 else NetworkRole.STATION
        ctx.session.add(
            NetworkNodeRow(network_entity_id=entity.id, member_node_id=place, role=role, dependency_pct=0, security=0, joined_epoch=ctx.epoch, locked=[])
        )
    await ctx.session.flush()
    return True


async def signal_relays(ctx: TickContext) -> int:
    chains: dict[int, list[int]] = defaultdict(list)
    for link in await ctx.session.scalars(select(SignalLinkRow).where(SignalLinkRow.state == SignalState.ACTIVE).order_by(SignalLinkRow.id)):
        for region in (link.from_region_id, link.to_region_id):
            if region not in chains[link.owner_node_id]:
                chains[link.owner_node_id].append(region)
    made = 0
    for owner_id, regions in sorted(chains.items()):
        owner = await ctx.session.get(EntityRow, owner_id)
        if (
            owner is not None
            and not await founded(ctx, owner.id, f"the signal chain of {owner.name}")
            and await relay(ctx, owner, regions, f"the signal chain of {owner.name}")
        ):
            made += 1
    return made


async def post_relays(ctx: TickContext) -> int:
    made = 0
    for polity, _ in await polities(ctx.session):
        towns = [town.id for town in await realm_towns(ctx.session, polity.id)]
        known = await holders_know(ctx.session, [polity.id, *towns], Technique.POSTAL_SERVICE)
        if len(towns) > 1 and known and not await founded(ctx, polity.id, f"the post of {polity.name}"):
            made += int(await relay(ctx, polity, towns, f"the post of {polity.name}"))
    return made


async def founded(ctx: TickContext, owner_id: int, name: str) -> bool:
    found = await ctx.session.scalar(
        select(NetworkProfileRow.network_entity_id)
        .join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id)
        .where(NetworkProfileRow.owner_node_id == owner_id, EntityRow.name == name)
        .limit(1)
    )
    return found is not None


async def keep_relays(ctx: TickContext) -> int:
    return await signal_relays(ctx) + await post_relays(ctx)


async def relay_backfill(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, RELAY_FIXUP) is not None:
        return 0
    result = {"signal_relays": await signal_relays(ctx), "post_relays": await post_relays(ctx)}
    ctx.session.add(AppliedFixupRow(key=RELAY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
