from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.made import DataStoreRow, SurveillanceProfileRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.made import SurveillanceFocus
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import polities, realm_towns
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.made.kinds import WATCHES
from aerona.engine.made.trust import trust_of
from aerona.engine.minds.values import liberty_of
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_percent, round_half_up

WATCH_STEPS = ("forbidden", "warranted", "broad", "total")


async def capacity_of(ctx: TickContext, polity_id: int) -> int:
    table = ctx.rules.surveillance
    networks = int(await ctx.session.scalar(select(func.count()).where(NetworkProfileRow.owner_node_id == polity_id)) or 0)
    stores = int(await ctx.session.scalar(select(func.count()).where(DataStoreRow.owner_node_id == polity_id)) or 0)
    spies = int(await ctx.session.scalar(select(func.count()).where(SpyNetworkRow.owner_entity_id == polity_id)) or 0)
    raw = networks * table.network_capacity + stores * table.store_capacity + spies * table.spy_capacity
    law = str(await law_param(ctx.session, polity_id, LawKind.SURVEILLANCE_LAW, "level") or "warranted")
    allowed = WATCH_STEPS.index(law) * table.law_caps if law in WATCH_STEPS else PERCENT
    capped = min(raw, allowed)
    privacy = str(await law_param(ctx.session, polity_id, LawKind.NETWORK_LAW, "level") or "")
    return clamp_percent(capped - capped * table.privacy_cut_pct // PERCENT if privacy == "open" else capped)


async def profile_for(ctx: TickContext, polity_id: int) -> SurveillanceProfileRow:
    row = await ctx.session.get(SurveillanceProfileRow, polity_id)
    if row is None:
        row = SurveillanceProfileRow(polity_entity_id=polity_id, capacity=0, reach_pct=0, focus=SurveillanceFocus.CRIME, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def watch(ctx: TickContext, polity_id: int) -> int:
    table = ctx.rules.surveillance
    row = await profile_for(ctx, polity_id)
    towns = await realm_towns(ctx.session, polity_id)
    if "capacity" not in row.locked:
        row.capacity = await capacity_of(ctx, polity_id)
    if "reach_pct" not in row.locked:
        row.reach_pct = clamp_percent(row.capacity * PERCENT // max(1, len(towns) * 10))
    row.updated_epoch = ctx.epoch
    watched = 0
    for town in towns:
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is None or held(town.id) or not row.reach_pct:
            continue
        await WATCHES[row.focus](ctx, town, profile, row.reach_pct)
        if await liberty_of(ctx.session, town.id) > 0 and "unrest" not in profile.locked:
            profile.unrest = clamp_percent(profile.unrest + round_half_up(table.chill * row.reach_pct / PERCENT))
        trust = await trust_of(ctx, town.id)
        if "information_trust" not in trust.locked:
            trust.information_trust = clamp_percent(trust.information_trust - round_half_up(table.trust_loss * row.reach_pct / PERCENT))
        watched += 1
    return watched


@reads(
    "table.bonds",
    "table.data_stores",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.network_profiles",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.spy_networks",
    "table.surveillance_profiles",
)
@writes("table.information_trust", "table.settlement_profiles", "table.surveillance_profiles")
async def keep_watch(ctx: TickContext) -> None:
    for polity, _ in await polities(ctx.session):
        if held(polity.id):
            continue
        ctx.count("towns_watched", await watch(ctx, polity.id))
    await ctx.session.flush()
