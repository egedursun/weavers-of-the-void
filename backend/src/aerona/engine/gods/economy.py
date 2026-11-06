from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.travel import travel_method_profile
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmic_state import AddictionImmunityRow, ResourceMechanicRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.society import AddictionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import FactionStats, ResourceStats
from aerona.engine.context import TickContext
from aerona.engine.economy.extraction import reconcile, write_reserve
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.gods.pacts import Terms, bargained, keep_pact, pact_for, strike_pact, terms_of
from aerona.engine.gods.queries import cosmos_row, owners_of, world_count
from aerona.engine.gods.stats import Trait, add_trait, headcount_floor, headcount_trait, set_trait, trait, trait_or
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import top_region
from aerona.engine.primitives.stats import headcount

PIRATE_METHODS = frozenset({TravelMethod.LIGHT_SAIL, TravelMethod.SLINGSHOT_ORBIT, TravelMethod.COSMIC_MOUNT})
WITHDRAWAL_TRAITS = (Trait.PROSPERITY, Trait.DEFENSE, Trait.STRENGTH, Trait.PIETY)
MARKET_TARGET_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
MULTI_WORLD_MINIMUM = 2


async def mechanic_params(session: AsyncSession, resource_id: int) -> dict[ResourceMechanic, ResourceMechanicRow]:
    rows = await session.scalars(select(ResourceMechanicRow).where(ResourceMechanicRow.entity_id == resource_id))
    return {row.mechanic: row for row in rows}


def magnitude_or(params: dict[ResourceMechanic, ResourceMechanicRow], mechanic: ResourceMechanic, default: int) -> int:
    row = params.get(mechanic)
    return row.magnitude if row is not None and row.magnitude is not None else default


def epochs_or(params: dict[ResourceMechanic, ResourceMechanicRow], mechanic: ResourceMechanic, default: int) -> int:
    row = params.get(mechanic)
    return row.epochs if row is not None and row.epochs is not None else default


async def shift_reserve(session: AsyncSession, resource: EntityRow, abundance_points: int) -> None:
    profile = await session.get(ResourceProfileRow, resource.id)
    if profile is None:
        add_trait(resource, Trait.ABUNDANCE, abundance_points)
        return
    reconcile(resource, profile)
    write_reserve(resource, profile, profile.reserve + round(abundance_points * profile.initial_reserve / PERCENT))


async def mechanics_of(session: AsyncSession, resource: EntityRow) -> set[ResourceMechanic]:
    found = set(await session.scalars(select(ResourceMechanicRow.mechanic).where(ResourceMechanicRow.entity_id == resource.id)))
    if resource.resource_mechanic is not None:
        found.add(resource.resource_mechanic)
    return found


async def _oldest_ownership(session: AsyncSession, owner_id: int, resource_id: int) -> int | None:
    statement = select(func.min(BondRow.epoch)).where(
        BondRow.source_node_id == owner_id, BondRow.target_node_id == resource_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE
    )
    value: int | None = await session.scalar(statement)
    return value


async def _immune(ctx: TickContext, owner_id: int, resource_id: int) -> bool:
    row = await ctx.session.get(AddictionImmunityRow, (owner_id, resource_id))
    return row is not None and ctx.epoch - row.recovered_epoch < ctx.rules.economy.addiction_immunity_epochs


ADDICTION_HOLD = "addiction"


def held(row: AddictionRow | None) -> bool:
    return row is not None and ADDICTION_HOLD in row.locked


async def _addictive(ctx: TickContext, resource: EntityRow, owners: list[EntityRow], hook_epochs: int) -> None:
    economy = ctx.rules.economy
    if trait_or(resource, Trait.ABUNDANCE, 0) < economy.withdrawal_min_abundance:
        return
    for owner in owners:
        if await _immune(ctx, owner.id, resource.id):
            continue
        since = await _oldest_ownership(ctx.session, owner.id, resource.id)
        row = await ctx.session.get(AddictionRow, (owner.id, resource.id))
        if held(row):
            continue
        if row is None:
            row = AddictionRow(community_entity_id=owner.id, resource_entity_id=resource.id, owned_epochs=0, locked=[])
            ctx.session.add(row)
        row.owned_epochs = max(0, ctx.epoch - since) if since is not None else 0
        if since is not None and ctx.epoch - since >= hook_epochs and row.addicted_since_epoch is None:
            row.addicted_since_epoch = ctx.epoch
            row.withdrawal_since_epoch = None
            line = god_lines.ECONOMY_ADDICTED
            await ctx.chronicle(
                ChronicleKind.RESOURCE, line.render(owner=owner.name, resource=resource.name), template_key=line.key, entity_ids=[owner.id, resource.id]
            )


async def _pay_demand(ctx: TickContext, owner: EntityRow, commodity: CommodityKind | None, units: int, cost: int) -> bool:
    if commodity is None:
        riches = trait(owner, Trait.PROSPERITY)
        riches = trait(owner, Trait.WEALTH) if riches is None else riches
        riches = ctx.rules.economy.sentient_owner_default if riches is None else riches
        if riches < ctx.rules.economy.sentient_owner_prosperity:
            return False
        add_trait(owner, Trait.PROSPERITY, -cost)
        add_trait(owner, Trait.WEALTH, -cost)
        return True
    if await holding(ctx.session, owner.id, commodity) < units:
        return False
    await goods_of(ctx.session, ctx.epoch).take(owner.id, commodity, units, GoodsFlow.OFFERING)
    return True


async def _abandon(ctx: TickContext, resource: EntityRow, owner: EntityRow, demand: str) -> None:
    rng = ctx.rng(f"sentient.leave.{resource.id}")
    bonds = BondRepository(ctx.session)
    await bonds.close_between(owner.id, resource.id, [BondKind.OWNS], ctx.epoch, "abandoned")
    statement = select(EntityRow).where(
        EntityRow.world_id == resource.world_id,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        EntityRow.id != owner.id,
    )
    others = list(await ctx.session.scalars(statement.order_by(EntityRow.id)))
    chosen = rng.pick(others) if others else None
    if chosen is not None:
        await bonds.connect(BondDraft(chosen.id, resource.id, BondKind.OWNS, ctx.epoch, god_lines.ECONOMY_SENTIENT_BOND))
    line = god_lines.ECONOMY_SENTIENT_LEFT
    clause = god_lines.ECONOMY_SENTIENT_CHOSEN.format(owner=chosen.name) if chosen is not None else ""
    await ctx.chronicle(
        ChronicleKind.RESOURCE,
        line.render(resource=resource.name, demand=demand, owner=owner.name, chosen=clause),
        template_key=line.key,
        entity_ids=[resource.id, owner.id] + ([chosen.id] if chosen is not None else []),
    )


async def _sentient(ctx: TickContext, resource: EntityRow, owners: list[EntityRow], cost: int) -> None:
    economy = ctx.rules.economy
    pact = await pact_for(ctx.session, resource.id)
    if pact is not None:
        owner_id = pact[1].obligor_node_id
        if await keep_pact(ctx, resource, pact, owners, pay=_pay_demand, shift=shift_reserve) == "broken":
            breaker = next((item for item in owners if item.id == owner_id), None)
            if breaker is not None:
                await _abandon(ctx, resource, breaker, terms_of(pact[1], ctx.rules.sentient_pacts.every_epochs).demand)
        return
    rng = ctx.rng(f"sentient.{resource.id}")
    if not owners or not rng.chance(economy.sentient_resource_choose_chance):
        return
    owner = rng.pick(owners)
    demand, wanted, units = rng.pick(god_lines.SENTIENT_DEMANDS)
    commodity = CommodityKind(wanted) if wanted is not None else None
    if rng.chance(economy.sentient_resource_keep_chance) and await _pay_demand(ctx, owner, commodity, units, cost):
        line = god_lines.ECONOMY_SENTIENT_PAID
        await ctx.chronicle(
            ChronicleKind.RESOURCE,
            line.render(resource=resource.name, demand=demand, owner=owner.name),
            template_key=line.key,
            entity_ids=[resource.id, owner.id],
        )
        return
    negotiator, skill = await best_negotiator(ctx.session, owner)
    if negotiator is not None and rng.chance(skill * economy.sentient_bargain_pct_per_level):
        terms = bargained(ctx, Terms(demand, commodity, units, cost, ctx.rules.sentient_pacts.every_epochs), skill)
        await strike_pact(ctx, resource, owner, terms, negotiator=negotiator)
        struck = await pact_for(ctx.session, resource.id)
        if struck is not None and await keep_pact(ctx, resource, struck, owners, pay=_pay_demand, shift=shift_reserve) == "broken":
            await _abandon(ctx, resource, owner, demand)
        return
    await _abandon(ctx, resource, owner, demand)


async def best_negotiator(session: AsyncSession, owner: EntityRow) -> tuple[EntityRow | None, int]:
    statement = (
        select(EntityRow, SkillRow.level)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            SkillRow.skill == SkillKind.NEGOTIATION,
            SkillRow.subject_node_id.is_(None),
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type == EntityType.MORTAL,
            or_(EntityRow.location_id == owner.id, EntityRow.id == owner.id),
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
        .limit(1)
    )
    found = (await session.execute(statement)).first()
    return (found[0], found[1]) if found is not None else (None, 0)


async def _sacred(ctx: TickContext, resource: EntityRow, owners: list[EntityRow], wrath: int) -> None:
    economy = ctx.rules.economy
    son = await ctx.session.get(SonRow, resource.sacred_to_son_id) if resource.sacred_to_son_id is not None else None
    if son is None or son.status is SonStatus.DEAD:
        return
    rng = ctx.rng(f"sacred.{resource.id}")
    entities = EntityRepository(ctx.session)
    for owner in owners:
        if await patron_node(ctx.session, owner) == son.id:
            continue
        son.wrath = clamp_int(son.wrath + wrath, 0, PERCENT)
        if rng.chance(economy.sacred_resource_curse_chance) and not await entities.has_flag(owner.id, EntityFlag.CURSED):
            await entities.add_flag(owner.id, EntityFlag.CURSED, ctx.epoch)
            await BondRepository(ctx.session).connect(
                BondDraft(son.id, owner.id, BondKind.CURSED, ctx.epoch, god_lines.ECONOMY_SACRED_BOND.format(resource=resource.name))
            )
            line = god_lines.ECONOMY_SACRED_CURSE
            await ctx.chronicle(
                ChronicleKind.CURSE,
                line.render(son=son.name, owner=owner.name, resource=resource.name),
                template_key=line.key,
                entity_ids=[owner.id],
                son_id=son.id,
            )


async def depletion_price(ctx: TickContext, resource: EntityRow, doom: int | None = None) -> None:
    entities = EntityRepository(ctx.session)
    if trait_or(resource, Trait.ABUNDANCE, 0) > 0 or await entities.has_flag(resource.id, EntityFlag.DEPLETED):
        return
    await entities.add_flag(resource.id, EntityFlag.DEPLETED, ctx.epoch)
    place = await ctx.session.get(EntityRow, resource.location_id) if resource.location_id is not None else None
    if place is not None:
        await entities.add_flag(place.id, EntityFlag.CURSED, ctx.epoch)
    await advance_doom(ctx.session, ctx.rules, doom if doom is not None else ctx.rules.economy.depletion_apocalypse)
    line = god_lines.ECONOMY_DEPLETED
    clause = god_lines.ECONOMY_DEPLETED_PLACE.format(place=place.name) if place is not None else ""
    await ctx.chronicle(ChronicleKind.RESOURCE, line.render(resource=resource.name, place=clause), template_key=line.key, entity_ids=[resource.id])


async def _has_access(ctx: TickContext, entity: EntityRow, resource: EntityRow) -> bool:
    if resource.status is not EntityStatus.CANON or trait_or(resource, Trait.ABUNDANCE, 0) < ctx.rules.economy.withdrawal_min_abundance:
        return False
    owners = await owners_of(ctx.session, resource.id)
    if any(owner.id == entity.id for owner in owners):
        return True
    bonds = BondRepository(ctx.session)
    return any([await bonds.exists_between(entity.id, owner.id, BondKind.TRADES_WITH) for owner in owners])


async def withdrawal(ctx: TickContext) -> None:
    economy = ctx.rules.economy
    rng = ctx.rng("withdrawal")
    rows = list(await ctx.session.scalars(select(AddictionRow).where(AddictionRow.addicted_since_epoch.is_not(None))))
    for row in rows:
        if held(row):
            continue
        entity = await ctx.session.get(EntityRow, row.community_entity_id)
        resource = await ctx.session.get(EntityRow, row.resource_entity_id)
        if entity is None or resource is None or entity.status is not EntityStatus.CANON or await _has_access(ctx, entity, resource):
            continue
        for key in WITHDRAWAL_TRAITS:
            add_trait(entity, key, -economy.withdrawal_loss)
        count_key = headcount_trait(entity)
        if count_key is not None:
            kept = trait_or(entity, count_key, 0) * economy.withdrawal_population_kept_pct / PERCENT
            set_trait(entity, count_key, max(headcount_floor(ctx.rules, count_key), kept))
        if rng.chance(economy.withdrawal_recovery_chance):
            row.addicted_since_epoch = None
            row.withdrawal_since_epoch = None
            await ctx.session.merge(AddictionImmunityRow(community_entity_id=entity.id, resource_entity_id=resource.id, recovered_epoch=ctx.epoch))
            line = god_lines.ECONOMY_RECOVERED
        else:
            row.withdrawal_since_epoch = row.withdrawal_since_epoch or ctx.epoch
            line = god_lines.ECONOMY_WITHDRAWAL
        await ctx.chronicle(
            ChronicleKind.RESOURCE, line.render(entity=entity.name, resource=resource.name), template_key=line.key, entity_ids=[entity.id, resource.id]
        )


@reads(
    "faction.wealth",
    "mortal.strength",
    "people.piety",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "resource.abundance",
    "settlement.prosperity",
    "table.addiction_immunities",
    "table.addictions",
    "table.bonds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
    "table.resource_mechanics",
    "table.resource_profiles",
)
@writes(
    "mortal.strength",
    "people.piety",
    "people.population",
    "resource.abundance",
    "settlement.prosperity",
    "table.addictions",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.resource_profiles",
    "table.sons",
)
async def resource_mechanics(ctx: TickContext) -> None:
    economy = ctx.rules.economy
    resources = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.RESOURCE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for resource in resources:
        mechanics = await mechanics_of(ctx.session, resource)
        if not mechanics:
            continue
        owners = await owners_of(ctx.session, resource.id)
        params = await mechanic_params(ctx.session, resource.id)
        if ResourceMechanic.DECAYING in mechanics:
            await shift_reserve(ctx.session, resource, -magnitude_or(params, ResourceMechanic.DECAYING, economy.decay_loss))
        if ResourceMechanic.FIXED in mechanics:
            await shift_reserve(ctx.session, resource, -magnitude_or(params, ResourceMechanic.FIXED, economy.fixed_regen_clawback))
        if ResourceMechanic.ADDICTIVE in mechanics:
            await _addictive(ctx, resource, owners, epochs_or(params, ResourceMechanic.ADDICTIVE, economy.addiction_epochs))
        if ResourceMechanic.SENTIENT in mechanics:
            await _sentient(ctx, resource, owners, magnitude_or(params, ResourceMechanic.SENTIENT, economy.sentient_demand_cost))
        if ResourceMechanic.SACRED in mechanics:
            await _sacred(ctx, resource, owners, magnitude_or(params, ResourceMechanic.SACRED, economy.sacred_wrath))
        if ResourceMechanic.DEPLETION_PRICE in mechanics:
            await depletion_price(ctx, resource, magnitude_or(params, ResourceMechanic.DEPLETION_PRICE, economy.depletion_apocalypse))
    await withdrawal(ctx)
    await ctx.session.flush()


async def deposits(session: AsyncSession) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_TRAVEL_RESOURCE, EntityRow.status == EntityStatus.CANON)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def spend_cosmic_resource(ctx: TickContext, traveller: EntityRow, amount: int | None = None) -> EntityRow | None:
    economy = ctx.rules.economy
    cost = economy.fold_abundance_cost if amount is None else amount
    bonds = BondRepository(ctx.session)
    for deposit in await deposits(ctx.session):
        if trait_or(deposit, Trait.ABUNDANCE, 0) < cost:
            continue
        owners = await owners_of(ctx.session, deposit.id)
        trades = any([await bonds.exists_between(traveller.id, owner.id, BondKind.TRADES_WITH) for owner in owners])
        if traveller.id not in {owner.id for owner in owners} and not trades:
            continue
        add_trait(deposit, Trait.ABUNDANCE, -cost)
        traveller.fold_count += 1
        if traveller.fold_count >= economy.fold_addiction_count:
            row = await ctx.session.get(AddictionRow, (traveller.id, deposit.id))
            if row is None:
                ctx.session.add(
                    AddictionRow(community_entity_id=traveller.id, resource_entity_id=deposit.id, owned_epochs=0, addicted_since_epoch=ctx.epoch, locked=[])
                )
            elif row.addicted_since_epoch is None and not held(row):
                row.addicted_since_epoch = ctx.epoch
        await ctx.session.flush()
        return deposit
    return None


async def _claim_deposits(ctx: TickContext) -> None:
    bonds = BondRepository(ctx.session)
    for deposit in await deposits(ctx.session):
        if await owners_of(ctx.session, deposit.id):
            continue
        statement = select(EntityRow).where(
            EntityRow.world_id == deposit.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES))
        )
        candidates = list(await ctx.session.scalars(statement.order_by(EntityRow.id)))
        region = await top_region(ctx.session, deposit)
        local = [entity for entity in candidates if region is not None and (await top_region(ctx.session, entity)) == region]
        pool = local or candidates
        if not pool:
            continue
        owner = max(pool, key=lambda entity: (headcount(entity), -entity.id))
        await bonds.connect(BondDraft(owner.id, deposit.id, BondKind.OWNS, ctx.epoch, god_lines.ECONOMY_DEPOSIT_CLAIM_BOND))
        line = god_lines.ECONOMY_DEPOSIT_CLAIMED
        await ctx.chronicle(
            ChronicleKind.RESOURCE, line.render(owner=owner.name, deposit=deposit.name), template_key=line.key, entity_ids=[owner.id, deposit.id]
        )


async def open_regions(session: AsyncSession, world_id: int | None = None) -> list[EntityRow]:
    open_worlds = select(WorldRow.id).where(WorldRow.discovery != Discovery.FORGOTTEN)
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON, EntityRow.world_id.in_(open_worlds))
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def create_deposit(ctx: TickContext, region: EntityRow) -> EntityRow | None:
    cosmos = await cosmos_row(ctx.session)
    if cosmos is None or cosmos.travel_resource is None:
        return None
    economy = ctx.rules.economy
    resource = cosmos.travel_resource
    world = await ctx.session.get(WorldRow, region.world_id)
    deposit = await EntityRepository(ctx.session).create(
        EntityDraft(
            name=await NameRepository(ctx.session).unique_name(god_lines.DEPOSIT_NAME.format(resource=resource.name, region=region.name)),
            entity_type=EntityType.RESOURCE,
            description=god_lines.DEPOSIT_DESCRIPTION.format(
                resource=resource.name, world=world.name if world else "", region=region.name, rule=resource.rule
            ).strip(),
            stats=ResourceStats(
                abundance=clamp_int(economy.deposit_abundance + ctx.rng("deposit").die(economy.deposit_abundance_die), 0, PERCENT),
                value=economy.deposit_value,
                might=economy.deposit_might,
            ),
            power_level=economy.deposit_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=region.world_id,
            location_id=region.id,
            engine_kind=EngineKind.COSMIC_TRAVEL_RESOURCE,
            subtype=god_lines.DEPOSIT_SUBTYPE,
            resource_mechanic=ResourceMechanic.ADDICTIVE,
            pending_name=True,
            split_title=False,
        )
    )
    ctx.session.add(ResourceMechanicRow(entity_id=deposit.id, mechanic=ResourceMechanic.FIXED))
    await set_resource_yield(ctx.session, ctx.rules, deposit.id, CommodityKind.MAGICAL_REAGENTS)
    line = god_lines.ECONOMY_DEPOSIT_BORN
    await ctx.chronicle(
        ChronicleKind.RESOURCE,
        line.render(resource=resource.name, world=world.name if world else "", region=region.name),
        template_key=line.key,
        entity_ids=[deposit.id],
    )
    await ctx.session.flush()
    return deposit


async def _new_deposits(ctx: TickContext) -> None:
    cosmos = await cosmos_row(ctx.session)
    if cosmos is None or cosmos.travel_resource is None:
        return
    rng = ctx.rng("deposits")
    held = {deposit.world_id for deposit in await deposits(ctx.session)}
    for world in await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        if world.id in held:
            continue
        settled = select(func.count(EntityRow.id)).where(
            EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(MARKET_TARGET_TYPES))
        )
        if not int(await ctx.session.scalar(settled) or 0) or not rng.chance(ctx.rules.economy.cosmic_deposit_chance):
            continue
        regions = await open_regions(ctx.session, world.id)
        if regions:
            await create_deposit(ctx, rng.pick(regions))


async def monopoly(ctx: TickContext) -> None:
    economy = ctx.rules.economy
    entities = EntityRepository(ctx.session)
    owner_sets = [{owner.id for owner in await owners_of(ctx.session, deposit.id)} for deposit in await deposits(ctx.session)]
    holders = set.union(*owner_sets) if owner_sets else set()
    sole = next(iter(holders)) if len(holders) == 1 and all(owner_sets) else None
    for holder in await entities.with_flag(EntityFlag.COSMIC_MONOPOLY):
        if holder.id != sole:
            await entities.remove_flag(holder.id, EntityFlag.COSMIC_MONOPOLY)
            line = god_lines.ECONOMY_MONOPOLY_BROKEN
            await ctx.chronicle(ChronicleKind.RESOURCE, line.render(owner=holder.name), template_key=line.key, entity_ids=[holder.id])
    if sole is None:
        return
    owner = await ctx.session.get(EntityRow, sole)
    if owner is None:
        return
    if await entities.add_flag(owner.id, EntityFlag.COSMIC_MONOPOLY, ctx.epoch):
        line = god_lines.ECONOMY_MONOPOLY
        await ctx.chronicle(ChronicleKind.RESOURCE, line.render(owner=owner.name), template_key=line.key, entity_ids=[owner.id])
    add_trait(owner, Trait.WEALTH, economy.monopoly_gain)
    add_trait(owner, Trait.SWAY, economy.monopoly_gain)
    add_trait(owner, Trait.INFLUENCE, economy.monopoly_gain)
    add_prosperity(ctx.rules, owner, economy.monopoly_gain)


async def passable_routes(session: AsyncSession, world_id: int | None = None) -> list[RouteRow]:
    statement = select(RouteRow).where(RouteRow.active.is_(True), RouteRow.known.is_(True))
    if world_id is not None:
        statement = statement.where(or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id))
    return list(await session.scalars(statement.order_by(RouteRow.id)))


async def faction_kind(session: AsyncSession, kind: EngineKind) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.engine_kind == kind, EntityRow.status == EntityStatus.CANON)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def found_faction(ctx: TickContext, kind: EngineKind, region: EntityRow) -> EntityRow:
    economy = ctx.rules.economy
    existing = len(await faction_kind(ctx.session, kind))
    market = kind is EngineKind.WANDERING_MARKET
    base = god_lines.MARKET_NAME if market else god_lines.PIRATES_NAME
    stats = (
        FactionStats(strength=economy.market_strength, wealth=economy.market_wealth, sway=economy.market_sway)
        if market
        else FactionStats(
            strength=clamp_int(economy.pirate_strength + ctx.rng("pirates").die(economy.pirate_strength_die), 0, PERCENT),
            wealth=economy.pirate_wealth,
            sway=economy.pirate_sway,
        )
    )
    faction = await EntityRepository(ctx.session).create(
        EntityDraft(
            name=await NameRepository(ctx.session).unique_name(base if not existing else f"{base} {existing + 1}"),
            entity_type=EntityType.FACTION,
            description=god_lines.MARKET_DESCRIPTION if market else god_lines.PIRATES_DESCRIPTION,
            stats=stats,
            power_level=economy.market_power if market else economy.pirate_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=region.world_id,
            location_id=region.id,
            engine_kind=kind,
            subtype=god_lines.MARKET_SUBTYPE if market else god_lines.PIRATES_SUBTYPE,
            pending_name=True,
            split_title=False,
        )
    )
    line = god_lines.ECONOMY_MARKET_BORN if market else god_lines.ECONOMY_PIRATES_BORN
    await ctx.chronicle(ChronicleKind.TRADE, line.render(region=region.name), template_key=line.key, entity_ids=[faction.id, region.id])
    return faction


async def move_market(ctx: TickContext, market: EntityRow, region: EntityRow) -> None:
    old_world = market.world_id
    await EntityRepository(ctx.session).move(market, region.id, ctx.epoch)
    bonds = BondRepository(ctx.session)
    for bond in await bonds.touching(market.id, [BondState.ACTIVE]):
        if bond.kind is not BondKind.TRADES_WITH:
            continue
        other = await ctx.session.get(EntityRow, bond.other_end(market.id))
        if other is not None and other.world_id == old_world and old_world != region.world_id:
            await bonds.deactivate(bond, ctx.epoch, "market moved")
    world = await ctx.session.get(WorldRow, region.world_id)
    line = god_lines.ECONOMY_MARKET_MOVED
    await ctx.chronicle(
        ChronicleKind.TRADE,
        line.render(market=market.name, world=world.name if world else "", region=region.name),
        template_key=line.key,
        entity_ids=[market.id, region.id],
    )


async def _markets(ctx: TickContext, routes: list[RouteRow]) -> None:
    economy = ctx.rules.economy
    rng = ctx.rng("markets")
    markets = await faction_kind(ctx.session, EngineKind.WANDERING_MARKET)
    if len(markets) < economy.market_max and routes and rng.chance(economy.market_found_chance):
        regions = await open_regions(ctx.session)
        if regions:
            markets.append(await found_faction(ctx, EngineKind.WANDERING_MARKET, rng.pick(regions)))
    bonds = BondRepository(ctx.session)
    for market in markets:
        linked = {
            route.world_b_id if route.world_a_id == market.world_id else route.world_a_id for route in await passable_routes(ctx.session, market.world_id)
        }
        targets = [region for world_id in sorted(linked) for region in await open_regions(ctx.session, world_id)]
        if targets and rng.chance(economy.market_move_chance):
            await move_market(ctx, market, rng.pick(targets))
        statement = select(EntityRow).where(
            EntityRow.world_id == market.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(MARKET_TARGET_TYPES))
        )
        for community in list(await ctx.session.scalars(statement.order_by(EntityRow.id)))[: economy.market_reach]:
            add_prosperity(ctx.rules, community, economy.market_prosperity)
            if not await bonds.exists_between(market.id, community.id, BondKind.TRADES_WITH) and rng.chance(economy.market_trade_chance):
                await bonds.connect(BondDraft(market.id, community.id, BondKind.TRADES_WITH, ctx.epoch, god_lines.MARKET_TRADE_BOND))


async def _pirates(ctx: TickContext, traffic: int) -> None:
    economy = ctx.rules.economy
    travel = ctx.rules.travel
    rng = ctx.rng("pirates")
    pirates = await faction_kind(ctx.session, EngineKind.VOID_PIRATES)
    if len(pirates) < economy.pirate_max and traffic >= economy.pirate_min_traffic and rng.chance(economy.pirate_chance):
        regions = await open_regions(ctx.session)
        if regions:
            region = max(regions, key=lambda entity: (trait_or(entity, Trait.DANGER, 0), -entity.id))
            pirates.append(await found_faction(ctx, EngineKind.VOID_PIRATES, region))
    routes = [route for route in await passable_routes(ctx.session) if route.method in PIRATE_METHODS]
    for route in routes:
        if pirates:
            route.danger = min(economy.pirate_route_danger_cap, route.danger + economy.pirate_route_danger)
        elif economy.pirate_danger_decay > 0:
            base = travel_method_profile(ctx.rules, route.method).danger
            floor = clamp_int(base + travel.route_danger_die - travel.route_danger_shift, travel.route_danger_min, travel.route_danger_max)
            if route.danger > floor:
                route.danger = max(floor, route.danger - economy.pirate_danger_decay)


@reads(
    "people.prosperity",
    "settlement.prosperity",
    "table.bonds",
    "table.cosmos",
    "table.epoch_year_cursors",
    "table.journeys",
    "table.name_registry",
    "table.nodes",
    "table.routes",
)
@writes(
    "people.prosperity",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.routes",
)
async def cosmic_economy(ctx: TickContext) -> None:
    if await world_count(ctx.session) < MULTI_WORLD_MINIMUM:
        return
    await _claim_deposits(ctx)
    await _new_deposits(ctx)
    await monopoly(ctx)
    routes = await passable_routes(ctx.session)
    window = ctx.epoch - ctx.rules.economy.traffic_window_epochs
    traffic = int(await ctx.session.scalar(select(func.count(JourneyRow.id)).where(JourneyRow.start_epoch > window)) or 0)
    await _markets(ctx, routes)
    await _pirates(ctx, traffic)
    await ctx.session.flush()
