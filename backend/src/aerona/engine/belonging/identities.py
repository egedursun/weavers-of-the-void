from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import MovementRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.folkways import PurityRankRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CollectiveActKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.engine.belonging.effects import approach
from aerona.engine.belonging.values import GUILDS, Value, values_of
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int

COMMUNITIES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
FAITH_CAUSES = frozenset({WarCause.HOLY_WAR, WarCause.SCHISM, WarCause.DIVINE_GRUDGE})
Pushes = dict[int, dict[IdentityLayer, tuple[int, SalienceDriver]]]


@dataclass
class IdentityTally:
    communities: int = 0
    mortals: int = 0
    stirred: int = 0
    crossed: int = 0


def push(pushes: Pushes, community: int, layer: IdentityLayer, amount: int, driver: SalienceDriver) -> None:
    current = pushes[community].get(layer)
    total = (current[0] if current is not None else 0) + amount
    strongest = driver if current is None or abs(amount) >= abs(current[0]) else current[1]
    pushes[community][layer] = (total, strongest)


async def war_pushes(ctx: TickContext, atlas: RegionAtlas, communities: list[EntityRow], pushes: Pushes) -> None:
    table = ctx.rules.identities
    holy = set(
        await ctx.session.scalars(
            select(WarSideRow.entity_id)
            .join(WarRow, WarRow.id == WarSideRow.war_id)
            .where(WarRow.status == WarStatus.ONGOING, WarRow.cause.in_(list(FAITH_CAUSES)), WarSideRow.left_epoch.is_(None))
        )
    )
    targets: dict[int, set[int]] = defaultdict(set)
    for region, target in await ctx.session.execute(
        select(ArmyProfileRow.region_entity_id, ArmyProfileRow.target_entity_id)
        .join(EntityRow, EntityRow.id == ArmyProfileRow.army_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, ArmyProfileRow.region_entity_id.is_not(None), ArmyProfileRow.target_entity_id.is_not(None))
    ):
        if region is not None and target is not None:
            targets[region].add(target)
    for community in communities:
        realm = await realm_of(ctx.session, community.id)
        if realm is not None and realm in holy:
            push(pushes, community.id, IdentityLayer.FAITH, table.holy_war, SalienceDriver.HOLY_WAR)
        region = atlas.top_region(community.id)
        if region is not None and targets.get(region, set()) & {community.id, *([realm] if realm is not None else [])}:
            push(pushes, community.id, IdentityLayer.PEOPLE, table.invasion, SalienceDriver.INVASION)
            push(pushes, community.id, IdentityLayer.POLITY, table.invasion, SalienceDriver.INVASION)


async def hunger_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes) -> None:
    lands = set(
        await ctx.session.scalars(
            select(NotableYearRow.region_entity_id).where(NotableYearRow.kind == NotableYearKind.HUNGER, NotableYearRow.epoch >= ctx.epoch - 1)
        )
    )
    for land in sorted(item for item in lands if item is not None):
        for community in atlas.communities_in(land):
            push(pushes, community, IdentityLayer.CLASS, ctx.rules.identities.famine, SalienceDriver.FAMINE)


async def movement_pushes(ctx: TickContext, pushes: Pushes) -> None:
    table = ctx.rules.identities
    for row in await ctx.session.scalars(select(MovementRow).where(MovementRow.ended_epoch.is_(None)).order_by(MovementRow.id)):
        if row.act is CollectiveActKind.STRIKE:
            push(pushes, row.settlement_entity_id, IdentityLayer.PROFESSION, table.strike, SalienceDriver.STRIKE)
            continue
        if row.cult_entity_id is not None:
            push(pushes, row.settlement_entity_id, IdentityLayer.FAITH, table.rhetoric, SalienceDriver.RHETORIC)
        if row.faction_entity_id is not None:
            profile = await ctx.session.get(FactionProfileRow, row.faction_entity_id)
            layer = IdentityLayer.PROFESSION if profile is not None and profile.kind in GUILDS else IdentityLayer.CIRCLE
            push(pushes, row.settlement_entity_id, layer, table.rhetoric, SalienceDriver.RHETORIC)


async def apart_pushes(ctx: TickContext, communities: list[EntityRow], pushes: Pushes) -> None:
    table = ctx.rules.identities
    quarters = set(await ctx.session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.kind == DistrictKind.FOREIGN_QUARTER)))
    castes = set(await ctx.session.scalars(select(DistrictRow.settlement_entity_id).where(DistrictRow.purity_rank_id.is_not(None))))
    apart = set(
        await ctx.session.scalars(select(PurityRankRow.people_entity_id).where((PurityRankRow.commensal.is_(True)) | (PurityRankRow.endogamous.is_(True))))
    )
    for community in communities:
        if community.id in quarters:
            push(pushes, community.id, IdentityLayer.PEOPLE, table.segregation, SalienceDriver.SEGREGATION)
        folk = await people_of(ctx.session, community)
        if (folk is not None and folk.id in apart) or community.id in castes:
            push(pushes, community.id, IdentityLayer.CLASS, table.segregation, SalienceDriver.SEGREGATION)


async def crossing_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    for first_id, second_id in await ctx.session.execute(select(MarriageRow.first_id, MarriageRow.second_id).where(MarriageRow.end_epoch.is_(None))):
        first, second = await ctx.session.get(EntityRow, first_id), await ctx.session.get(EntityRow, second_id)
        if first is None or second is None or first.location_id is None or first.location_id != second.location_id:
            continue
        mine, theirs = await values_of(ctx.session, atlas, first), await values_of(ctx.session, atlas, second)
        for layer in (IdentityLayer.PEOPLE, IdentityLayer.FAITH):
            if mine[layer][0] is not None and theirs[layer][0] is not None and mine[layer][0] != theirs[layer][0]:
                push(pushes, first.location_id, layer, -table.crossing, SalienceDriver.CROSSING)
                tally.crossed += 1


async def guild_pushes(ctx: TickContext, atlas: RegionAtlas, pushes: Pushes, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    guilds = await ctx.session.execute(
        select(EntityRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(GUILDS)), EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        .order_by(EntityRow.id)
    )
    for (guild,) in guilds.all():
        members = await ctx.session.scalars(
            select(EntityRow)
            .join(BondRow, BondRow.source_node_id == EntityRow.id)
            .where(BondRow.target_node_id == guild.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
            .order_by(EntityRow.id)
        )
        values = [await values_of(ctx.session, atlas, member) for member in members]
        for layer in (IdentityLayer.PEOPLE, IdentityLayer.FAITH):
            if guild.location_id is not None and len({row[layer][0] for row in values if row[layer][0] is not None}) > 1:
                push(pushes, guild.location_id, layer, -table.crossing, SalienceDriver.CROSSING)
                tally.crossed += 1


def write(row: HeldIdentityRow, value: Value, salience: int, driver: SalienceDriver, epoch: int) -> None:
    if "value_node_id" not in row.locked:
        row.value_node_id = value[0]
    if "value_label" not in row.locked:
        row.value_label = value[1]
    if "salience" not in row.locked:
        row.salience = salience
    if "driver" not in row.locked:
        row.driver = driver
    row.updated_epoch = epoch


async def keep_holder(ctx: TickContext, atlas: RegionAtlas, holder: EntityRow, targets: dict[IdentityLayer, tuple[int, SalienceDriver]], pct: int) -> None:
    values = await values_of(ctx.session, atlas, holder)
    for layer in IdentityLayer:
        row = await ctx.session.get(HeldIdentityRow, (holder.id, layer))
        target, driver = targets[layer]
        if row is None:
            row = HeldIdentityRow(
                holder_entity_id=holder.id, layer=layer, strength=50, salience=ctx.rules.identities.base_salience, updated_epoch=ctx.epoch, locked=[]
            )
            ctx.session.add(row)
        write(row, values[layer], approach(row.salience, target, pct), driver, ctx.epoch)


async def keep_identities(ctx: TickContext, tally: IdentityTally) -> None:
    table = ctx.rules.identities
    atlas = await RegionAtlas.load(ctx.session)
    communities = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITIES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    pushes: Pushes = defaultdict(dict)
    await war_pushes(ctx, atlas, communities, pushes)
    await hunger_pushes(ctx, atlas, pushes)
    await movement_pushes(ctx, pushes)
    await apart_pushes(ctx, communities, pushes)
    await guild_pushes(ctx, atlas, pushes, tally)
    await crossing_pushes(ctx, atlas, pushes, tally)
    for community in communities:
        if held(community.id):
            continue
        stirred = pushes.get(community.id, {})
        targets = {
            layer: (clamp_int(table.base_salience + stirred[layer][0], 0, 100), stirred[layer][1])
            if layer in stirred
            else (table.base_salience, SalienceDriver.BASELINE)
            for layer in IdentityLayer
        }
        await keep_holder(ctx, atlas, community, targets, table.decay_pct)
        tally.communities += 1
        tally.stirred += len(stirred)
    await ctx.session.flush()
    mortals = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        if held(mortal.id):
            continue
        home = mortal.location_id
        rows = {row.layer: row for row in await ctx.session.scalars(select(HeldIdentityRow).where(HeldIdentityRow.holder_entity_id == home))} if home else {}
        targets = {
            layer: (rows[layer].salience, rows[layer].driver) if layer in rows else (table.base_salience, SalienceDriver.BASELINE) for layer in IdentityLayer
        }
        await keep_holder(ctx, atlas, mortal, targets, table.mortal_pct)
        tally.mortals += 1
    await ctx.session.flush()
