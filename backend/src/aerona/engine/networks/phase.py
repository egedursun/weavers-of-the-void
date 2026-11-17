from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkOutageRow, NetworkProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.networks import NetworkRole, OutageCause
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepLocus, StepOutcome
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.values import liberty_of
from aerona.engine.networks.backfill import keep_relays, relay_backfill
from aerona.engine.networks.book import carrier_days, running, shake_ledger
from aerona.engine.networks.energy import CARRIER_ENERGY, starved
from aerona.engine.networks.kinds import ACCESS_REACH, CARRIER_FAILURE, CAUSE_EPOCHS, ROLE_SHOCK
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.stats import set_stats, shift_stat
from aerona.engine.recording.record import StepDraft
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.community_relations import change_relation
from aerona.engine.technology.profiles import family_level


async def members(ctx: TickContext, network_id: int) -> list[NetworkNodeRow]:
    return list(await ctx.session.scalars(select(NetworkNodeRow).where(NetworkNodeRow.network_entity_id == network_id).order_by(NetworkNodeRow.id)))


async def besieged(ctx: TickContext, rows: list[NetworkNodeRow]) -> bool:
    ids = [row.member_node_id for row in rows]
    found = (
        await ctx.session.scalar(select(SiegeRow.id).where(SiegeRow.besieged_entity_id.in_(ids), SiegeRow.status == SiegeStatus.ONGOING).limit(1))
        if ids
        else None
    )
    return found is not None


async def repairable(ctx: TickContext, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> bool:
    if profile.tech_level <= 1:
        return True
    best = max([await family_level(ctx.session, row.member_node_id, TechFamily.COMMUNICATION) for row in rows] or [0])
    return best >= profile.tech_level


async def cut(ctx: TickContext, network: EntityRow, profile: NetworkProfileRow, cause: OutageCause, severity: int) -> None:
    table = ctx.rules.networks
    epochs = max(1, table.outage_epochs * CAUSE_EPOCHS[cause] // PERCENT)
    if "down_until_epoch" not in profile.locked:
        profile.down_until_epoch = ctx.epoch + epochs
    ctx.session.add(NetworkOutageRow(network_entity_id=network.id, cause=cause, epoch=ctx.epoch, epochs=epochs, severity=severity))
    await shake_ledger(ctx.session, ctx.rules, network.id)
    await record_incident(ctx, "network.outage", roles={IncidentRole.SUBJECT: network.id}, facts={"cause": cause, "epochs": epochs, "severity": severity})


async def outage_cause(ctx: TickContext, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> OutageCause | None:
    table = ctx.rules.networks
    rng = ctx.rng(f"network.outage.{profile.network_entity_id}.{ctx.epoch}")
    if await besieged(ctx, rows) and rng.chance(table.war_outage):
        return OutageCause.WAR
    if not await repairable(ctx, profile, rows) and rng.chance(table.decay_outage):
        return OutageCause.DECAY
    for row in rows:
        if await starved(ctx.session, row.member_node_id, CARRIER_ENERGY[profile.carrier], table.shortage_pct):
            return OutageCause.SHORTAGE
    if rng.chance(table.outage_base * (PERCENT - profile.reliability) / PERCENT):
        return CARRIER_FAILURE[profile.carrier]
    return None


async def shock(ctx: TickContext, row: NetworkNodeRow) -> None:
    table = ctx.rules.networks
    town = await ctx.session.get(EntityRow, row.member_node_id)
    if town is None or town.status is not EntityStatus.CANON or held(town.id):
        return
    share = row.dependency_pct / PERCENT * ROLE_SHOCK[row.role] / PERCENT
    settled = await ctx.session.get(SettlementProfileRow, town.id)
    if settled is not None and "public_order" not in settled.locked:
        settled.public_order = clamp_percent(settled.public_order - round_half_up(table.shock_order * share))
    shift_stat(town, "prosperity", -round_half_up(table.shock_prosperity * share), ctx.rules.society.default_stat)


async def depend(ctx: TickContext, profile: NetworkProfileRow, rows: list[NetworkNodeRow], live: bool) -> None:
    table = ctx.rules.networks
    for row in rows:
        if held(row.member_node_id) or "dependency_pct" in row.locked:
            continue
        if live:
            row.dependency_pct = clamp_percent(
                row.dependency_pct + table.dependency_gain * profile.capacity // PERCENT * ACCESS_REACH[profile.access] // PERCENT
            )
        else:
            await shock(ctx, row)
            row.dependency_pct = clamp_percent(row.dependency_pct - table.dependency_loss)


async def grow(ctx: TickContext, network: EntityRow, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> None:
    table = ctx.rules.networks
    owner = await ctx.session.get(PolityProfileRow, profile.owner_node_id) if profile.owner_node_id is not None else None
    if owner is None or held(owner.polity_entity_id) or owner.treasury < table.growth_cost:
        return
    if not ctx.rng(f"network.grow.{network.id}.{ctx.epoch}").chance(table.growth_chance):
        return
    joined = {row.member_node_id for row in rows}
    towns = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == owner.polity_entity_id)
    town = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.id.in_(towns), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(joined or {0})
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if town is None or held(town.id):
        return
    owner.treasury -= table.growth_cost
    ctx.session.add(
        NetworkNodeRow(
            network_entity_id=network.id,
            member_node_id=town.id,
            role=NetworkRole.STATION,
            dependency_pct=0,
            security=profile.security,
            joined_epoch=ctx.epoch,
            locked=[],
        )
    )
    await record_incident(
        ctx,
        "network.grew",
        roles={IncidentRole.SUBJECT: network.id, IncidentRole.DESTINATION: town.id},
        steps=(
            StepDraft(
                StepAction.CONNECT,
                actor=owner.polity_entity_id,
                target=town.id,
                instrument_kind=InstrumentKind.NETWORK,
                instrument_node=network.id,
                locus_kind=StepLocus.NETWORK_NODE,
                locus_key=NetworkRole.STATION.value,
                amount=table.growth_cost,
                unit=FactUnit.COIN,
                outcome=StepOutcome.SUCCESS,
                record_table=NetworkNodeRow.__tablename__,
            ),
        ),
        place=town.id,
    )


async def censor(ctx: TickContext, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> None:
    if profile.censorship <= 0 or profile.owner_node_id is None:
        return
    from_values = select(EntityRow).where(EntityRow.id.in_([row.member_node_id for row in rows]))
    for town in await ctx.session.scalars(from_values):
        if held(town.id, profile.owner_node_id):
            continue
        liberty = await liberty_of(ctx.session, town.id)
        if liberty > 0:
            loss = round_half_up(ctx.rules.networks.censorship_distrust * profile.censorship / PERCENT * liberty / PERCENT)
            if loss:
                await change_relation(ctx, town.id, profile.owner_node_id, -loss, MemoryKind.ILL_WILL)


async def keep_ledger(ctx: TickContext, network: EntityRow, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> None:
    if not profile.carries_money or len(rows) < 2 or held(network.id):
        return
    issued = select(CurrencyRow).where(CurrencyRow.issuer_entity_id == network.id, CurrencyRow.metal.is_(None))
    ledger = await ctx.session.scalar(issued.limit(1))
    trust = (profile.security + profile.reliability) // 2
    if ledger is None:
        ledger = CurrencyRow(
            issuer_entity_id=network.id,
            item_entity_id=None,
            name=f"the ledger of {network.name}",
            metal=None,
            purity=PERCENT,
            supply=0,
            trust=trust,
            minted_epoch=ctx.epoch,
            held=False,
        )
        ctx.session.add(ledger)
        await ctx.session.flush()
        await record_incident(ctx, "network.ledger", roles={IncidentRole.SUBJECT: network.id}, facts={"trust": trust})
    elif not ledger.held:
        ledger.trust = clamp_percent(ledger.trust + (trust - ledger.trust) * ctx.rules.money.trust_drift_pct / PERCENT)
    for row in rows:
        society = await ctx.session.get(CommunitySocietyRow, row.member_node_id)
        if society is not None and society.currency_id is None and not held(row.member_node_id):
            society.currency_id = ledger.id


async def converge(ctx: TickContext, profile: NetworkProfileRow, rows: list[NetworkNodeRow]) -> None:
    if not profile.carries_money or len(rows) < 2:
        return
    pull = ctx.rules.networks.price_pull_pct * profile.capacity / PERCENT / PERCENT
    societies = [
        row for row in [await ctx.session.get(CommunitySocietyRow, member.member_node_id) for member in rows] if row is not None and not held(row.entity_id)
    ]
    for commodity in Commodity:
        column = f"price_{commodity.value}"
        prices = [getattr(society, column) for society in societies]
        if not prices:
            continue
        mean = sum(prices) / len(prices)
        for society in societies:
            setattr(society, column, max(0, round_half_up(getattr(society, column) + (mean - getattr(society, column)) * pull)))


@reads(
    "table.community_societies",
    "table.custom_kinds",
    "table.entities",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.network_nodes",
    "table.network_profiles",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.sieges",
    "table.signal_links",
)
@writes(
    "table.applied_fixups",
    "table.community_relations",
    "table.community_societies",
    "table.entities",
    "table.network_nodes",
    "table.network_outages",
    "table.network_profiles",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def networks(ctx: TickContext) -> None:
    ctx.count("relay_networks_founded", await relay_backfill(ctx))
    ctx.count("relay_networks_kept", await keep_relays(ctx))
    for profile in list(await ctx.session.scalars(select(NetworkProfileRow).order_by(NetworkProfileRow.network_entity_id))):
        network = await ctx.session.get(EntityRow, profile.network_entity_id)
        if network is None or network.status is not EntityStatus.CANON or held(network.id):
            continue
        rows = await members(ctx, network.id)
        if "delay_days" not in profile.locked:
            profile.delay_days = carrier_days(ctx.rules, profile.carrier)
        if running(profile, ctx.epoch):
            cause = await outage_cause(ctx, profile, rows)
            if cause is not None:
                await cut(ctx, network, profile, cause, clamp_int(PERCENT - profile.reliability, 1, PERCENT))
        live = running(profile, ctx.epoch)
        await depend(ctx, profile, rows, live)
        if live:
            await grow(ctx, network, profile, rows)
            await converge(ctx, profile, rows)
            await keep_ledger(ctx, network, profile, rows)
        await censor(ctx, profile, rows)
        set_stats(network, reach=len(rows))
        ctx.count("networks_kept")
    await ctx.session.flush()
