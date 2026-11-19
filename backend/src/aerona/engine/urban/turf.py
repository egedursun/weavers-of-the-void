from collections import defaultdict
from dataclasses import dataclass
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.urban import DistrictServiceRow, TurfRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import CRIME_KINDS
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.urban import UrbanService
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import slay
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

TURF_DEATH = "fell in a turf war"


@dataclass
class TurfTally:
    claimed: int = 0
    lost: int = 0
    wars: int = 0
    dead: int = 0


async def crime_orgs(session: AsyncSession) -> list[tuple[EntityRow, FactionProfileRow]]:
    rows = await session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(CRIME_KINDS)), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows.all() if not held(entity.id)]


async def watch_of(session: AsyncSession, district_id: int) -> int:
    row = await session.get(DistrictServiceRow, (district_id, UrbanService.WATCH))
    return row.coverage if row is not None else 0


async def claim(ctx: TickContext, faction: EntityRow, profile: FactionProfileRow, tally: TurfTally) -> None:
    table = ctx.rules.turf
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id) if profile.home_entity_id is not None else None
    if town is None or town.crime < table.claim_crime or held(town.settlement_entity_id):
        return
    districts = list(
        await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.settlement_entity_id).order_by(DistrictRow.id))
    )
    free = [district for district in districts if await ctx.session.get(TurfRow, (district.id, faction.id)) is None]
    if not free or not ctx.rng(f"turf_claim.{faction.id}").chance(table.claim_pct):
        return
    target = min(free, key=lambda district: (district.land_value, district.id))
    ctx.session.add(TurfRow(district_id=target.id, faction_entity_id=faction.id, strength=table.growth * 2, since_epoch=ctx.epoch, locked=[]))
    tally.claimed += 1


async def tend(ctx: TickContext, row: TurfRow, tally: TurfTally) -> None:
    table = ctx.rules.turf
    if "strength" in row.locked:
        return
    watch = await watch_of(ctx.session, row.district_id)
    row.strength = clamp_int(round_half_up(row.strength + table.growth - watch / PERCENT * table.watch_loss), 0, PERCENT)
    if row.strength <= 0:
        await ctx.session.delete(row)
        tally.lost += 1


async def casualties(ctx: TickContext, faction_id: int, share_pct: int) -> int:
    dead = 0
    members = list(
        await ctx.session.scalars(
            select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == faction_id).order_by(FactionMembershipRow.mortal_entity_id)
        )
    )
    count = max(1, ceil(len(members) * share_pct / PERCENT)) if share_pct > 0 else 0
    for member in ctx.rng(f"turf_dead.{faction_id}").shuffled(members)[:count]:
        mortal = await ctx.session.get(EntityRow, member.mortal_entity_id)
        if mortal is not None and not held(mortal.id) and await slay(ctx, mortal, Harm(ctx.rules.casualties.wound_hp, HarmCause.DUEL, TURF_DEATH)):
            dead += 1
    return dead


async def turf_war(ctx: TickContext, district: DistrictRow, rows: list[TurfRow], tally: TurfTally) -> None:
    table = ctx.rules.turf
    if len(rows) < 2 or not ctx.rng(f"turf_war.{district.id}").chance(table.war_pct):
        return
    winner, loser = sorted(rows, key=lambda row: (-row.strength, row.faction_entity_id))[:2]
    if "strength" not in loser.locked:
        loser.strength = clamp_int(loser.strength - table.war_loss, 0, PERCENT)
    town = await ctx.session.get(SettlementProfileRow, district.settlement_entity_id)
    if town is not None and "public_order" not in town.locked:
        town.public_order = clamp_int(town.public_order - table.war_order, 0, PERCENT)
    tally.wars += 1
    tally.dead += await casualties(ctx, loser.faction_entity_id, table.war_deaths)
    await record(
        ctx,
        "crime.turf_war",
        roles={IncidentRole.ACTOR: winner.faction_entity_id, IncidentRole.OPPONENT: loser.faction_entity_id},
        facts={"district": district.kind, "strength_lost": table.war_loss, "order_lost": table.war_order},
        place=district.settlement_entity_id,
    )


async def hold_turf(ctx: TickContext, tally: TurfTally) -> None:
    for faction, profile in await crime_orgs(ctx.session):
        await claim(ctx, faction, profile, tally)
    await ctx.session.flush()
    by_district: dict[int, list[TurfRow]] = defaultdict(list)
    for row in list(await ctx.session.scalars(select(TurfRow).order_by(TurfRow.district_id, TurfRow.faction_entity_id))):
        if held(row.faction_entity_id):
            continue
        await tend(ctx, row, tally)
        if row.strength > 0:
            by_district[row.district_id].append(row)
    for district_id, rows in sorted(by_district.items()):
        district = await ctx.session.get(DistrictRow, district_id)
        if district is not None and not held(district.settlement_entity_id):
            await turf_war(ctx, district, rows, tally)
    await ctx.session.flush()
