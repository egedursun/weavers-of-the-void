from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow, WarAimRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.military import AgentStatus, SpyCover, SpyOwnerKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import TREASURY_LOCK, receive_coin
from aerona.engine.environment.book import region_environment, scar_region
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.spy_depth import compromise, motivate
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import held_captive, take_captive

OWNER_KINDS = {EntityType.POLITY: SpyOwnerKind.POLITY, EntityType.FACTION: SpyOwnerKind.FACTION, EntityType.CULT: SpyOwnerKind.CULT}
OWNER_COVERS = {
    SpyOwnerKind.POLITY: SpyCover.ENVOY,
    SpyOwnerKind.FACTION: SpyCover.MERCHANT,
    SpyOwnerKind.CULT: SpyCover.PRIEST,
    SpyOwnerKind.COMPANY: SpyCover.MERCHANT,
    SpyOwnerKind.MADE_MIND: SpyCover.ENVOY,
}
MADE_ORIGINS = frozenset({MindOrigin.MADE, MindOrigin.GROWN, MindOrigin.TRAINED, MindOrigin.COPIED})
COVER_EXPOSURE = {SpyCover.MERCHANT: 100, SpyCover.PRIEST: 80, SpyCover.ENVOY: 60, SpyCover.BEGGAR: 90}
COVER_ACCESS = {SpyCover.MERCHANT: 100, SpyCover.PRIEST: 110, SpyCover.ENVOY: 130, SpyCover.BEGGAR: 70}
BOND_FIXUP = "military.spy_networks_typed"


async def owner_kind(session: AsyncSession, owner: EntityRow) -> SpyOwnerKind:
    if await session.get(CompanyProfileRow, owner.id) is not None:
        return SpyOwnerKind.COMPANY
    mind = await session.get(MindProfileRow, owner.id)
    if mind is not None and mind.origin in MADE_ORIGINS:
        return SpyOwnerKind.MADE_MIND
    return OWNER_KINDS.get(owner.entity_type, SpyOwnerKind.COMMUNITY)


async def cover_for(session: AsyncSession, owner: EntityRow) -> SpyCover:
    return OWNER_COVERS.get(await owner_kind(session, owner), SpyCover.BEGGAR)


async def side_for(ctx: TickContext, owner: EntityRow) -> int | None:
    kind = await owner_kind(ctx.session, owner)
    if kind is SpyOwnerKind.COMPANY:
        return owner.affiliated_entity_id or owner.location_id
    if kind is SpyOwnerKind.POLITY:
        profile = await ctx.session.get(PolityProfileRow, owner.id)
        return profile.core_entity_id if profile is not None else None
    if kind is SpyOwnerKind.FACTION:
        return owner.affiliated_entity_id or owner.location_id
    return owner.id


def cover_exposure(network: SpyNetworkRow, amount: int) -> int:
    return round_half_up(amount * COVER_EXPOSURE.get(network.cover, PERCENT) / PERCENT)


def cover_access(network: SpyNetworkRow, amount: int) -> int:
    return round_half_up(amount * COVER_ACCESS.get(network.cover, PERCENT) / PERCENT)


async def agents_of(ctx: TickContext, network: SpyNetworkRow, *, active: bool = True) -> list[SpyAgentRow]:
    statement = select(SpyAgentRow).where(SpyAgentRow.network_id == network.id)
    if active:
        statement = statement.where(SpyAgentRow.status == AgentStatus.ACTIVE)
    return list(await ctx.session.scalars(statement.order_by(SpyAgentRow.id)))


async def retire_agents(ctx: TickContext, network: SpyNetworkRow) -> int:
    retired = 0
    for agent in await agents_of(ctx, network):
        if "status" in agent.locked or held(agent.mortal_entity_id):
            continue
        fallen = agent.mortal_entity_id is not None and await living_entity(ctx.session, agent.mortal_entity_id) is None
        if not fallen and ctx.epoch - agent.since_epoch < ctx.rules.espionage.agent_service_epochs:
            continue
        agent.status, agent.ended_epoch = (AgentStatus.DEAD if fallen else AgentStatus.RETIRED), ctx.epoch
        retired += 1
        if "agents" not in network.locked:
            network.agents = max(0, network.agents - 1)
    return retired


async def recruit(ctx: TickContext, network: SpyNetworkRow) -> SpyAgentRow | None:
    owner = await living_entity(ctx.session, network.owner_entity_id)
    if owner is None:
        return None
    taken = set(await ctx.session.scalars(select(SpyAgentRow.mortal_entity_id).where(SpyAgentRow.mortal_entity_id.is_not(None))))
    homes = {owner.id, owner.location_id or 0, network.side_entity_id or 0}
    candidates = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, homes))
        .order_by(EntityRow.id)
        .limit(50)
    )
    mortal = None
    for item in sorted(candidates, key=lambda row: (row.mortal_role is not MortalRole.SPY, row.id)):
        if item.id not in taken and await held_captive(ctx.session, item.id) is None:
            mortal = item
            break
    if mortal is None:
        return None
    trained = ctx.rules.espionage.spy_role_skill if mortal.mortal_role is MortalRole.SPY else 0
    agent = SpyAgentRow(
        network_id=network.id,
        mortal_entity_id=mortal.id,
        cover=network.cover,
        skill=clamp_int(network.depth // 2 + PERCENT // 5 + trained, 0, PERCENT),
        exposure=0,
        status=AgentStatus.ACTIVE,
        since_epoch=ctx.epoch,
        locked=[],
    )
    await motivate(ctx, network, agent, mortal)
    ctx.session.add(agent)
    await ctx.session.flush()
    network.agent_ids = sorted({*network.agent_ids, mortal.id})
    return agent


async def catch_agent(ctx: TickContext, network: SpyNetworkRow, target: EntityRow) -> EntityRow | None:
    agents = await agents_of(ctx, network)
    if not agents:
        return None
    agent = max(agents, key=lambda row: (row.exposure, row.id))
    agent.status, agent.ended_epoch = AgentStatus.CAUGHT, ctx.epoch
    await compromise(ctx, network, agent)
    network.agent_ids = [item for item in network.agent_ids if item != agent.mortal_entity_id]
    network.agents = max(0, network.agents - 1)
    mortal = await living_entity(ctx.session, agent.mortal_entity_id)
    if mortal is None or await held_captive(ctx.session, mortal.id) is not None:
        return None
    await take_captive(ctx, target, mortal, None, description=f"a spy of {network.owner_entity_id}", home_id=network.side_entity_id)
    return mortal


async def burn_district(ctx: TickContext, target: EntityRow) -> DistrictKind | None:
    district = await ctx.session.scalar(
        select(DistrictRow).where(DistrictRow.settlement_entity_id == target.id).order_by(DistrictRow.condition.desc()).limit(1)
    )
    depth = ctx.rules.espionage.arson_damage
    if district is not None:
        district.condition = clamp_int(district.condition - depth, 0, PERCENT)
        return district.kind
    ground = await region_environment(ctx.session, target.id)
    if ground is not None:
        await scar_region(ctx.session, ctx.rules, ground, ScarKind.BURNED, depth // 2)
    return None


async def wound_ruler(ctx: TickContext, victim: EntityRow, owner: EntityRow) -> bool:
    harm = Harm(ctx.rules.espionage.assassin_hp, HarmCause.POISON, f"struck by an assassin of {owner.name}", killer_id=owner.id)
    return (await apply_hits(ctx, victim, harm, lethal=False)) is not None


async def plant_claimant(ctx: TickContext, owner: EntityRow, target: EntityRow) -> EntityRow | None:
    realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == target.id).limit(1))
    if realm_id is None:
        return None
    ruler = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    existing = set(await ctx.session.scalars(select(ClaimRow.claimant_entity_id).where(ClaimRow.polity_entity_id == realm_id, ClaimRow.ended_epoch.is_(None))))
    members = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm_id)))
    nobles = await ctx.session.scalars(
        select(HouseMemberRow.mortal_entity_id)
        .join(EntityRow, EntityRow.id == HouseMemberRow.mortal_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, members))
        .order_by(EntityRow.importance.desc(), EntityRow.id)
    )
    pick = next((mortal_id for mortal_id in nobles if mortal_id != ruler and mortal_id not in existing and not held(mortal_id)), None)
    claimant = await living_entity(ctx.session, pick)
    if claimant is None:
        return None
    house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == claimant.id).limit(1))
    ctx.session.add(
        ClaimRow(
            claimant_entity_id=claimant.id,
            house_entity_id=house_id,
            polity_entity_id=realm_id,
            office=OfficeKind.RULER,
            strength=ctx.rules.espionage.planted_claim,
            basis=ClaimBasis.FABRICATED,
            pressed=False,
            since_epoch=ctx.epoch,
        )
    )
    return claimant


async def reveal_aims(ctx: TickContext, network: SpyNetworkRow, target: EntityRow) -> list[int]:
    if network.intel < ctx.rules.espionage.reveal_intel:
        return []
    aims = list(await ctx.session.scalars(select(WarAimRow.id).where(WarAimRow.side_entity_id == target.id)))
    network.revealed_aims = sorted({*network.revealed_aims, *aims})
    if network.side_entity_id is not None and await at_war(ctx, network.side_entity_id, target.id):
        network.warned_epoch = ctx.epoch
    return aims


async def at_war(ctx: TickContext, first: int, second: int) -> bool:
    mine = {row.war_id: row.side for row in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.entity_id == first, WarSideRow.left_epoch.is_(None)))}
    theirs = await ctx.session.scalars(select(WarSideRow).where(WarSideRow.entity_id == second, WarSideRow.left_epoch.is_(None)))
    return any(row.war_id in mine and mine[row.war_id] is not row.side for row in theirs)


async def blackmail_office(ctx: TickContext, owner: EntityRow, target: EntityRow, network: SpyNetworkRow) -> int | None:
    realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == target.id).limit(1))
    if realm_id is None:
        return None
    office = await ctx.session.scalar(
        select(OfficeRow)
        .where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind != OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
        .limit(1)
    )
    holder = await living_entity(ctx.session, office.holder_entity_id) if office is not None else None
    if office is None or holder is None:
        return None
    table = ctx.rules.espionage
    realm = await ctx.session.get(PolityProfileRow, realm_id)
    if office.kind is OfficeKind.TREASURER and realm is not None:
        if TREASURY_LOCK not in realm.locked:
            drained = min(realm.treasury, table.blackmail_wealth * ctx.rules.taxation.wealth_per_treasury)
            realm.treasury -= drained
            await receive_coin(ctx.session, ctx.rules, owner, drained)
    elif office.kind is OfficeKind.SPYMASTER:
        for row in await ctx.session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == owner.id)):
            row.exposure = 0
    elif office.kind is OfficeKind.MARSHAL:
        network.intel = clamp_int(network.intel + table.intel_gain, 0, PERCENT)
        network.warned_epoch = ctx.epoch
    elif office.kind in {OfficeKind.CHANCELLOR, OfficeKind.AMBASSADOR}:
        await change_relation(ctx, target.id, owner.id, table.blackmail_relation, MemoryKind.GOODWILL, note=f"{holder.name} spoke for them")
    else:
        record, _ = await ensure_profile(ctx.session, holder.id, ctx.epoch)
        room = PERCENT - stat_or(owner, "wealth", PERCENT)
        paid = 0 if is_held(record, "wealth") else min(record.wealth, table.blackmail_wealth, room)
        record.wealth -= paid
        shift_stat(owner, "wealth", paid)
    return holder.id


async def migrate_bonds(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, BOND_FIXUP) is not None:
        return 0
    moved = 0
    bonds = list(await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.SPY_NETWORK, BondRow.state == BondState.ACTIVE)))
    for bond in bonds:
        owner, target = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if owner is None or target is None:
            continue
        row = await ctx.session.scalar(
            select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == owner.id, SpyNetworkRow.target_entity_id == target.id).limit(1)
        )
        if row is None:
            row = SpyNetworkRow(
                owner_entity_id=owner.id,
                target_entity_id=target.id,
                agents=1,
                agent_ids=[],
                depth=10,
                exposure=0,
                cover=await cover_for(ctx.session, owner),
                since_epoch=bond.epoch,
            )
            ctx.session.add(row)
        row.owner_kind = await owner_kind(ctx.session, owner)
        row.side_entity_id = await side_for(ctx, owner)
        row.bond_id = None
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "kept as a typed spy network")
        moved += 1
    for row in list(await ctx.session.scalars(select(SpyNetworkRow))):
        owner = await living_entity(ctx.session, row.owner_entity_id)
        if owner is not None:
            row.owner_kind = await owner_kind(ctx.session, owner)
            row.side_entity_id = row.side_entity_id or await side_for(ctx, owner)
        for mortal_id in row.agent_ids:
            ctx.session.add(
                SpyAgentRow(network_id=row.id, mortal_entity_id=mortal_id, cover=row.cover, skill=PERCENT // 3, since_epoch=row.since_epoch, locked=[])
            )
    ctx.session.add(AppliedFixupRow(key=BOND_FIXUP, result={"moved": moved}))
    await ctx.session.flush()
    return moved
