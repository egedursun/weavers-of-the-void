from collections.abc import Mapping

from sqlalchemy import func, select

from aerona.catalog.life.domain import GANG_KINDS, LICENSABLE_KINDS
from aerona.catalog.urban import ROUGH_QUARTERS
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.urban import CrimeStanceRow, RacketRow, TurfRow
from aerona.db.tables.youth import YouthGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.urban import CrimeStance, RacketKind
from aerona.domain.enums.youth import YouthPurpose
from aerona.engine.context import TickContext
from aerona.engine.demography.control import move_cohort
from aerona.engine.demography.events import enslaved
from aerona.engine.kinds.society import add_organisations
from aerona.engine.phases.factions import found_faction
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record

GANGS_FIXUP = "underworld.w52"
LAWLESS = 40


async def forbids_bondage(ctx: TickContext, realm_id: int) -> bool:
    status = await law_param(ctx.session, realm_id, LawKind.SLAVERY, "status")
    return status in {None, "banned"}


async def stance_for(ctx: TickContext, realm_id: int, profile: FactionProfileRow, values: Mapping[ValueAxis, int]) -> tuple[CrimeStance, int]:
    law, wealth, trade = values.get(ValueAxis.LAW, 0), values.get(ValueAxis.WEALTH, 0), values.get(ValueAxis.XENOPHILIA, 0)
    if profile.kind is FactionKind.TRAFFICKING_RING and await forbids_bondage(ctx, realm_id):
        return CrimeStance.SUPPRESS, ctx.rules.underworld.forbidden_strength
    if law >= wealth:
        return CrimeStance.SUPPRESS, PERCENT // 2
    if profile.kind in LICENSABLE_KINDS and trade > law:
        return CrimeStance.LICENSE, PERCENT // 2
    if wealth > trade:
        return CrimeStance.TOLERATE, PERCENT // 2
    if values.get(ValueAxis.MERCY, 0) > law:
        return CrimeStance.INTEGRATE, PERCENT // 2
    return CrimeStance.CO_OPT, PERCENT // 2


async def income_of(ctx: TickContext, faction_id: int) -> int:
    found = await ctx.session.scalar(select(func.coalesce(func.sum(RacketRow.income), 0)).where(RacketRow.faction_entity_id == faction_id))
    return int(found or 0)


async def tolerate(ctx: TickContext, stance: CrimeStanceRow, profile: FactionProfileRow) -> None:
    table = ctx.rules.underworld
    realm = await ctx.session.get(PolityProfileRow, stance.polity_entity_id)
    bribe = round_half_up(await income_of(ctx, stance.faction_entity_id) * table.tolerate_bribe_pct / PERCENT * stance.strength / PERCENT)
    if realm is not None:
        move_amount(profile, realm, "treasury", min(bribe, max(0, profile.treasury)))
        if "corruption" not in realm.locked:
            realm.corruption = clamp_int(realm.corruption + table.tolerate_corruption, 0, PERCENT)
    if "stance" not in stance.locked and ctx.rng(f"crime_outcry.{stance.faction_entity_id}.{ctx.epoch}").chance(table.outcry_pct):
        stance.stance = CrimeStance.SUPPRESS
        town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id) if profile.home_entity_id is not None else None
        if town is not None and "unrest" not in town.locked:
            town.unrest = clamp_int(town.unrest + table.tolerate_corruption, 0, PERCENT)
        await record(
            ctx,
            "polity.crime_stance",
            roles={IncidentRole.AUTHORITY: stance.polity_entity_id, IncidentRole.TARGET: stance.faction_entity_id},
            facts={"stance": stance.stance},
        )


async def license_trade(ctx: TickContext, stance: CrimeStanceRow, profile: FactionProfileRow) -> None:
    table = ctx.rules.underworld
    realm = await ctx.session.get(PolityProfileRow, stance.polity_entity_id)
    tax = round_half_up(await income_of(ctx, stance.faction_entity_id) * table.license_tax_pct / PERCENT)
    if realm is not None:
        move_amount(profile, realm, "treasury", min(tax, max(0, profile.treasury)))
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id) if profile.home_entity_id is not None else None
    if town is not None and "crime" not in town.locked:
        town.crime = clamp_int(town.crime - table.license_crime, 0, PERCENT)


async def rough_towns(ctx: TickContext) -> list[EntityRow]:
    towns = await ctx.session.scalars(
        select(EntityRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, SettlementProfileRow.crime >= LAWLESS)
        .order_by(EntityRow.id)
    )
    return [town for town in towns if not held(town.id)]


async def has_gang(ctx: TickContext, town_id: int) -> bool:
    found = await ctx.session.scalar(
        select(FactionProfileRow.faction_entity_id)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.home_entity_id == town_id, FactionProfileRow.kind == FactionKind.STREET_GANG, EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    return found is not None


async def street_youth(ctx: TickContext, town_id: int) -> bool:
    gangs = await ctx.session.scalar(
        select(YouthGroupRow.id).where(YouthGroupRow.settlement_entity_id == town_id, YouthGroupRow.purpose == YouthPurpose.CRIME).limit(1)
    )
    rough = await ctx.session.scalar(
        select(DistrictRow.id).where(DistrictRow.settlement_entity_id == town_id, DistrictRow.kind.in_(list(ROUGH_QUARTERS))).limit(1)
    )
    return gangs is not None or rough is not None


async def raise_gangs(ctx: TickContext, *, certain: bool = False) -> int:
    raised = 0
    for town in await rough_towns(ctx):
        if await has_gang(ctx, town.id) or not await street_youth(ctx, town.id):
            continue
        if certain or ctx.rng(f"gang.{town.id}.{ctx.epoch}").chance(ctx.rules.underworld.gang_recruit_pct):
            gang = await found_faction(ctx, town, FactionKind.STREET_GANG)
            profile = await ctx.session.get(FactionProfileRow, gang.id)
            if profile is not None:
                profile.home_entity_id = town.id
            raised += 1
    return raised


async def grow_gangs(ctx: TickContext) -> int:
    table = ctx.rules.underworld
    grown = 0
    gangs = await ctx.session.scalars(
        select(FactionProfileRow).where(FactionProfileRow.kind == FactionKind.STREET_GANG).order_by(FactionProfileRow.faction_entity_id)
    )
    for profile in list(gangs):
        if held(profile.faction_entity_id) or "kind" in profile.locked:
            continue
        strong = list(
            await ctx.session.scalars(
                select(TurfRow).where(
                    TurfRow.faction_entity_id == profile.faction_entity_id,
                    TurfRow.strength >= table.gang_grow_turf,
                    TurfRow.since_epoch <= ctx.epoch - table.epochs(table.gang_grow_years),
                )
            )
        )
        if strong:
            profile.kind = FactionKind.CRIME_FAMILY
            grown += 1
            await record(ctx, "underworld.gang_grown", roles={IncidentRole.SUBJECT: profile.faction_entity_id}, facts={"kind": profile.kind})
    return grown


async def traffic(ctx: TickContext) -> int:
    table = ctx.rules.underworld
    taken = 0
    rings = await ctx.session.scalars(
        select(RacketRow).where(RacketRow.racket == RacketKind.TRAFFICKING).order_by(RacketRow.faction_entity_id, RacketRow.settlement_entity_id)
    )
    for racket in list(rings):
        town = await ctx.session.get(EntityRow, racket.settlement_entity_id)
        if town is None or held(town.id, racket.faction_entity_id) or stat_or(town, "population", 0) <= table.trafficked:
            continue
        if not ctx.rng(f"traffic.{racket.faction_entity_id}.{town.id}.{ctx.epoch}").chance(table.trafficking_route_pct):
            continue
        moved = await move_cohort(ctx, town.id, count=table.trafficked, source=SocialClass.FARMER, target=SocialClass.SERF_OR_SLAVE, band=None, condition=None)
        await enslaved(ctx, town, moved)
        if moved > 0:
            taken += moved
            await record(
                ctx,
                "underworld.trafficked",
                roles={IncidentRole.ACTOR: racket.faction_entity_id, IncidentRole.VICTIM: town.id},
                facts={"taken": moved},
                place=town.id,
            )
    return taken


async def backfill_gangs(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, GANGS_FIXUP) is not None:
        return 0
    kinds = await add_organisations(ctx.session, GANG_KINDS)
    raised = await raise_gangs(ctx, certain=True)
    ctx.session.add(AppliedFixupRow(key=GANGS_FIXUP, result={"gangs": raised, "kinds": kinds}))
    await ctx.session.flush()
    return raised


async def keep_underworld(ctx: TickContext) -> int:
    return await backfill_gangs(ctx) + await raise_gangs(ctx) + await grow_gangs(ctx) + await traffic(ctx)
