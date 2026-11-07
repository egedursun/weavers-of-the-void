import math
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import Discovery
from aerona.domain.models.entity_stats import CultStats, FactionStats, TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.worlds import declare_holy_world
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.births import NOTABLE_ROLES, pick_class, raise_notable
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

FACTION_KINDS: dict[SocialClass, tuple[str, str]] = {
    SocialClass.MERCHANT: ("merchant guild", "Guild"),
    SocialClass.ARTISAN: ("craft guild", "Guild"),
    SocialClass.PRIEST: ("council of priests", "Council"),
    SocialClass.SCRIBE: ("council of scribes", "Council"),
    SocialClass.WARRIOR: ("warrior band", "Band"),
    SocialClass.FARMER: ("farmers' union", "Union"),
    SocialClass.NOBLE: ("council of lords", "Council"),
    SocialClass.SERF_OR_SLAVE: ("brotherhood of the bound", "Brotherhood"),
    SocialClass.OUTCAST: ("beggars' brotherhood", "Brotherhood"),
    SocialClass.MONASTIC: ("monastic order", "Order"),
}
TRADITIONS: dict[SocialClass, str] = {
    SocialClass.FARMER: "harvest feast",
    SocialClass.ARTISAN: "masters' oath",
    SocialClass.MERCHANT: "fair",
    SocialClass.PRIEST: "offering rite",
    SocialClass.WARRIOR: "trial of age",
    SocialClass.SCRIBE: "day of remembrance",
    SocialClass.NOBLE: "tourney",
    SocialClass.SERF_OR_SLAVE: "day of release",
    SocialClass.OUTCAST: "feast of alms",
    SocialClass.MONASTIC: "vigil",
}
CULT_SUBTYPE = "temple order"


@dataclass(frozen=True)
class WorldPulse:
    world_id: int
    communities: int
    godless: int
    factions: int
    cults: int
    named_mortals: int
    sons: int
    engine_records: int
    this_epoch: int
    per_epoch: int
    quota: int
    window: int


@dataclass(frozen=True)
class SonShare:
    world_id: int
    sons: int
    share: int


async def _count(session: AsyncSession, world_id: int, types: frozenset[EntityType]) -> int:
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(types)))
    )
    return int(await session.scalar(statement) or 0)


async def _engine_records(session: AsyncSession, world_id: int, since: int) -> int:
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.origin == EntityOrigin.ENGINE, EntityRow.birth_epoch > since)
    )
    return int(await session.scalar(statement) or 0)


async def _godless(session: AsyncSession, world_id: int) -> int:
    worshipping = select(BondRow.source_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
            EntityRow.id.not_in(worshipping),
        )
    )
    return int(await session.scalar(statement) or 0)


async def world_pulse(session: AsyncSession, rules: Rules, world_id: int, epoch: int) -> WorldPulse:
    settings = rules.world_balance
    window = settings.activity_window
    records = await _engine_records(session, world_id, epoch - window)
    sons = int(
        await session.scalar(select(func.count()).select_from(SonRow).where(SonRow.current_world_id == world_id, SonRow.status == SonStatus.ACTIVE)) or 0
    )
    return WorldPulse(
        world_id=world_id,
        communities=await _count(session, world_id, COMMUNITY_TYPES),
        godless=await _godless(session, world_id),
        factions=await _count(session, world_id, frozenset({EntityType.FACTION})),
        cults=await _count(session, world_id, frozenset({EntityType.CULT})),
        named_mortals=await _count(session, world_id, frozenset({EntityType.MORTAL})),
        sons=sons,
        engine_records=records,
        this_epoch=await _engine_records(session, world_id, epoch - 1),
        per_epoch=round_half_up(records / window),
        quota=settings.record_quota,
        window=window,
    )


async def living_worlds(session: AsyncSession) -> list[WorldRow]:
    return list(await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))


def share_weight(rules: Rules, pulse: WorldPulse) -> float:
    settings = rules.world_balance
    return float(math.pow(pulse.communities + pulse.godless * settings.godless_weight_pct / 100, settings.son_share_exponent_pct / 100))


async def son_shares(session: AsyncSession, rules: Rules, epoch: int) -> list[SonShare]:
    active = int(await session.scalar(select(func.count()).select_from(SonRow).where(SonRow.status == SonStatus.ACTIVE)) or 0)
    pulses = [pulse for pulse in [await world_pulse(session, rules, world.id, epoch) for world in await living_worlds(session)] if pulse.communities > 0]
    weights = {pulse.world_id: share_weight(rules, pulse) for pulse in pulses}
    total = sum(weights.values()) or 1.0
    exact = {pulse.world_id: active * weights[pulse.world_id] / total for pulse in pulses}
    shares = {world_id: math.floor(value) for world_id, value in exact.items()}
    remaining = active - sum(shares.values())
    for world_id in sorted(exact, key=lambda key: (-(exact[key] % 1), key)):
        if remaining <= 0:
            break
        shares[world_id] += 1
        remaining -= 1
    return [SonShare(pulse.world_id, pulse.sons, shares[pulse.world_id]) for pulse in pulses]


def _protected(rules: Rules, son: SonRow, epoch: int) -> bool:
    return son.chained or (son.manually_assigned_epoch is not None and epoch - son.manually_assigned_epoch < rules.god_hand.assignment_protection_epochs)


async def _ties(session: AsyncSession, rules: Rules, son: SonRow, world: WorldRow) -> float:
    statement = (
        select(func.count())
        .select_from(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == son.id, EntityRow.world_id == world.id)
    )
    worshippers = int(await session.scalar(statement) or 0)
    return worshippers + (rules.world_balance.godless_weight_pct if world.patron_son_id == son.id else 0)


async def balance_sons(ctx: TickContext) -> int:
    settings = ctx.rules.world_balance
    moved = 0
    for _ in range(settings.son_moves):
        shares = await son_shares(ctx.session, ctx.rules, ctx.epoch)
        if len(shares) < 2:
            break
        receivers = sorted(
            (share for share in shares if share.share - share.sons >= settings.son_gap), key=lambda share: (share.sons - share.share, share.world_id)
        )
        donors = sorted(
            (share for share in shares if share.sons - share.share >= settings.son_gap and share.sons > 1),
            key=lambda share: (share.share - share.sons, share.world_id),
        )
        if not receivers or not donors:
            break
        donor_world = await ctx.session.get(WorldRow, donors[0].world_id)
        receiver_world = await ctx.session.get(WorldRow, receivers[0].world_id)
        if donor_world is None or receiver_world is None:
            break
        sons = await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == donor_world.id).order_by(SonRow.id))
        movable = [son for son in sons if not _protected(ctx.rules, son, ctx.epoch)]
        if not movable:
            break
        ranked = [(await _ties(ctx.session, ctx.rules, son, donor_world), son.id, son) for son in movable]
        son = min(ranked, key=lambda item: (item[0], item[1]))[2]
        son.current_world_id = receiver_world.id
        await ctx.session.flush()
        text = f"{son.name} left {donor_world.name}, crowded with their siblings, for {receiver_world.name}, whose people need gods."
        await ctx.chronicle(ChronicleKind.COSMIC, text, template_key="world_balance.son_moved", son_id=son.id, world_id=receiver_world.id)
        moved += 1
    return moved


async def guardian_candidate(session: AsyncSession, world: WorldRow) -> SonRow | None:
    statement = (
        select(BondRow.target_node_id, func.count(BondRow.id))
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world.id)
        .group_by(BondRow.target_node_id)
    )
    counted: list[tuple[SonRow, int]] = []
    for target_id, count in await session.execute(statement):
        son = await session.get(SonRow, target_id)
        if son is not None and son.status is SonStatus.ACTIVE:
            counted.append((son, int(count)))
    if counted:
        return max(counted, key=lambda item: (item[0].current_world_id == world.id, item[1], -item[0].id))[0]
    here = await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == world.id).order_by(SonRow.id))
    return max(here, key=lambda son: (son.fame, -son.id), default=None)


async def guard_patronless(ctx: TickContext) -> int:
    worlds = await living_worlds(ctx.session)
    if len(worlds) < 2:
        return 0
    guarded = 0
    for world in worlds:
        patron = await ctx.session.get(SonRow, world.patron_son_id) if world.patron_son_id is not None else None
        if patron is not None and patron.status is not SonStatus.DEAD:
            continue
        if not await _count(ctx.session, world.id, SOCIETY_TYPES):
            continue
        son = await guardian_candidate(ctx.session, world)
        if son is None:
            continue
        await declare_holy_world(ctx, son, world, automatic=True)
        guarded += 1
    return guarded


async def _dominant(ctx: TickContext, community: EntityRow) -> SocialClass:
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    return max(shares.items(), key=lambda item: (item[1], item[0].value))[0]


async def raise_faction(ctx: TickContext, world_id: int) -> EntityRow | None:
    settings = ctx.rules.world_balance
    candidates = [
        community for community in await canon(ctx.session, SOCIETY_TYPES, world_id) if (stat(community, "population") or 0) >= settings.faction_population
    ]
    community = max(candidates, key=lambda item: (stat(item, "population") or 0, -item.id), default=None)
    if community is None:
        return None
    subtype, suffix = FACTION_KINDS[await _dominant(ctx, community)]
    rng = ctx.rng(seed_of("balance_faction", community.id))

    def roll() -> int:
        return clamp_int(settings.faction_stat + rng.die(settings.faction_stat_die), 0, 100)

    faction = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=f"{community.name} {suffix}",
            body=f"The first organised power within {community.name}.",
            stats=FactionStats(strength=roll(), wealth=roll(), sway=roll()),
            power=max(1, community.power_level - 1),
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=subtype,
        ),
    )
    await connect(ctx.session, faction.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, description="rose from within")
    await bind_language_and_faith(ctx, faction, source=community)
    await note(ctx, f"The first {subtype} of the world was founded in {community.name}.", key="world_balance.faction", ids=[community.id, faction.id])
    return faction


async def raise_cult(ctx: TickContext, world_id: int) -> EntityRow | None:
    settings = ctx.rules.world_balance
    pious = []
    for community in await canon(ctx.session, SOCIETY_TYPES, world_id):
        patron = await living_patron(ctx.session, community)
        if patron is not None and (stat(community, "piety") or 0) >= settings.cult_piety:
            pious.append((community, patron))
    if not pious:
        return None
    community, patron = max(pious, key=lambda item: (stat(item[0], "piety") or 0, stat(item[0], "population") or 0, -item[0].id))
    rng = ctx.rng(seed_of("balance_cult", community.id))
    followers = max(settings.cult_followers_minimum, round_half_up((stat(community, "population") or 0) * settings.cult_followers_pct / 100))
    cult = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"{patron.name}'s {community.name} Order",
            body=f"The most devout of {community.name} founded a temple order in the name of {patron.name}.",
            stats=CultStats(
                followers=followers,
                zeal=clamp_int(settings.cult_zeal + rng.die(settings.faction_stat_die), 0, 100),
                influence=clamp_int(settings.cult_zeal + rng.die(settings.faction_stat_die), 0, 100),
            ),
            power=max(1, community.power_level - 1),
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=CULT_SUBTYPE,
        ),
    )
    await connect(ctx.session, cult.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, description="rose from within")
    await connect(ctx.session, cult.id, patron.id, BondKind.WORSHIPS, ctx.epoch, description="founding faith")
    await bind_language_and_faith(ctx, cult, source=community)
    await note(
        ctx,
        f"The most devout of {community.name} founded the world's first temple order in the name of {patron.name}.",
        key="world_balance.cult",
        ids=[community.id, cult.id],
        son_id=patron.id,
    )
    return cult


async def begin_tradition(ctx: TickContext, community: EntityRow) -> EntityRow | None:
    settings = ctx.rules.world_balance
    subtype = TRADITIONS[await _dominant(ctx, community)]
    celebrated = (
        select(EntityRow.id)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == community.id,
            BondRow.kind == BondKind.CELEBRATES,
            BondRow.state == BondState.ACTIVE,
            EntityRow.subtype == subtype,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    if await ctx.session.scalar(celebrated.limit(1)) is not None:
        return None
    tradition = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TRADITION,
            name=f"{community.name} {subtype.title()}",
            body=f"{community.name} began to gather on the same day every year for a new {subtype}.",
            stats=TraditionStats(spread=settings.tradition_spread, rigidity=settings.tradition_rigidity),
            power=1,
            world_id=community.world_id,
            subtype=subtype,
        ),
    )
    await connect(ctx.session, community.id, tradition.id, BondKind.CELEBRATES, ctx.epoch)
    await note(ctx, f"{community.name} began a new {subtype}.", key="world_balance.tradition", ids=[community.id, tradition.id])
    return tradition


async def birth(ctx: TickContext, community: EntityRow) -> EntityRow:
    rng = ctx.rng(seed_of("balance_birth", community.id))
    social_class = pick_class(rng.random(), await class_shares(ctx.session, ctx.rules, community.id))
    return await raise_notable(ctx, community, social_class, rng.pick(NOTABLE_ROLES[social_class]))


async def revive(ctx: TickContext, world: WorldRow, *, forced: bool = False) -> list[int]:
    settings = ctx.rules.world_balance
    pulse = await world_pulse(ctx.session, ctx.rules, world.id, ctx.epoch)
    created: list[int] = []
    if not pulse.communities:
        return created
    rng = ctx.rng(seed_of("revive", world.id))
    if pulse.factions < settings.faction_minimum and (forced or rng.chance(settings.faction_chance)):
        faction = await raise_faction(ctx, world.id)
        created.extend([faction.id] if faction is not None else [])
    if pulse.cults < settings.cult_minimum and (forced or rng.chance(settings.cult_chance)):
        cult = await raise_cult(ctx, world.id)
        created.extend([cult.id] if cult is not None else [])
    current = await world_pulse(ctx.session, ctx.rules, world.id, ctx.epoch)
    gap = min(settings.revival_cap, max(1 if forced else 0, settings.record_quota - current.this_epoch))
    communities = unheld(await canon(ctx.session, SOCIETY_TYPES, world.id))
    for index in range(gap):
        if not communities:
            break
        if not forced and not rng.chance(settings.revival_chance):
            continue
        community = rng.pick(communities)
        record = (await begin_tradition(ctx, community) if index % 2 else None) or await birth(ctx, community)
        created.append(record.id)
    return created


@reads(
    "mortal.beauty",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.allele_pools",
    "table.bonds",
    "table.community_societies",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.world_maps",
)
@writes(
    "mortal.lifespan",
    "mortal.strength",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
)
async def world_balance(ctx: TickContext) -> None:
    ctx.count("guardians", await guard_patronless(ctx))
    worlds = await living_worlds(ctx.session)
    if len(worlds) < 2:
        return
    revived = 0
    for world in unheld(worlds):
        if await revive(ctx, world):
            revived += 1
    ctx.count("revived", revived)
    await ctx.session.flush()


async def revive_world(ctx: TickContext, world_id: int) -> list[int]:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} is forgotten.")
    if not (await world_pulse(ctx.session, ctx.rules, world.id, ctx.epoch)).communities:
        raise ValidationFailedError(f"{world.name} has no community to revive; create a people or a settlement first.")
    return await revive(ctx, world, forced=True)


async def appoint_guardian(ctx: TickContext, world_id: int, son_id: int) -> str:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} is forgotten; no one can guard it.")
    son = await ctx.session.get(SonRow, son_id)
    if son is None or son.status is SonStatus.DEAD:
        raise ValidationFailedError("The guardian must be a living son.")
    if world.patron_son_id == son.id:
        raise ValidationFailedError(f"{son.name} already guards {world.name}.")
    return await declare_holy_world(ctx, son, world)


PHASES = (Phase("world_balance", world_balance),)
