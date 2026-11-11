from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.urban import RACKETS_OF
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.urban import CrimeStanceRow, PayrollRow, RacketRow, TurfRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.intrigue import HookSource
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import OathKind
from aerona.domain.enums.urban import CrimeStance
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.disease.stigma import values_for
from aerona.engine.economy.purse import give_coin
from aerona.engine.intrigue.secrets import grant_hook, learn
from aerona.engine.lifecycle.wounds import slay
from aerona.engine.notes import note
from aerona.engine.polity.oaths import break_on, oaths_of, swear
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.urban.turf import crime_orgs

TRAITOR_DEATH = "was killed for breaking the code of silence"


@dataclass
class CrimeTally:
    rackets: int = 0
    income: int = 0
    bought: int = 0
    traitors: int = 0
    sworn: int = 0
    stances: int = 0


async def turf_in(ctx: TickContext, faction_id: int, settlement_id: int) -> int:
    districts = select(DistrictRow.id).where(DistrictRow.settlement_entity_id == settlement_id)
    return sum(
        row.strength for row in await ctx.session.scalars(select(TurfRow).where(TurfRow.faction_entity_id == faction_id, TurfRow.district_id.in_(districts)))
    )


async def keep_rackets(ctx: TickContext, faction: EntityRow, profile: FactionProfileRow, tally: CrimeTally) -> None:
    table = ctx.rules.crime_orgs
    town_id = profile.home_entity_id
    if town_id is None:
        return
    turf = await turf_in(ctx, faction.id, town_id)
    if turf <= 0:
        return
    kinds = RACKETS_OF.get(profile.kind, ())
    held_kinds = set(
        await ctx.session.scalars(select(RacketRow.racket).where(RacketRow.faction_entity_id == faction.id, RacketRow.settlement_entity_id == town_id))
    )
    missing = [kind for kind in kinds if kind not in held_kinds]
    if missing and ctx.rng(f"racket.{faction.id}").chance(table.racket_pct):
        ctx.session.add(RacketRow(faction_entity_id=faction.id, settlement_entity_id=town_id, racket=missing[0], income=0, since_epoch=ctx.epoch, locked=[]))
        tally.rackets += 1
        await ctx.session.flush()
    for racket in await ctx.session.scalars(select(RacketRow).where(RacketRow.faction_entity_id == faction.id, RacketRow.settlement_entity_id == town_id)):
        if "income" not in racket.locked:
            racket.income = round_half_up(turf * table.income_per_turf / PERCENT)
        if "treasury" not in profile.locked:
            profile.treasury += racket.income
        tally.income += racket.income


async def buy_officials(ctx: TickContext, faction: EntityRow, profile: FactionProfileRow, tally: CrimeTally) -> None:
    table = ctx.rules.crime_orgs
    realm = await realm_of_community(ctx.session, profile.home_entity_id) if profile.home_entity_id is not None else None
    if realm is not None and ctx.rng(f"payroll.{faction.id}").chance(table.payroll_pct):
        bought = set(await ctx.session.scalars(select(PayrollRow.official_entity_id).where(PayrollRow.faction_entity_id == faction.id)))
        official = await ctx.session.scalar(
            select(OfficeRow.holder_entity_id)
            .where(OfficeRow.polity_entity_id == realm, OfficeRow.holder_entity_id.is_not(None), OfficeRow.holder_entity_id.not_in(bought or {0}))
            .order_by(OfficeRow.id)
            .limit(1)
        )
        if official is not None and not held(official):
            ctx.session.add(PayrollRow(faction_entity_id=faction.id, official_entity_id=official, bribe=table.bribe, since_epoch=ctx.epoch, locked=[]))
            await grant_hook(ctx, faction.id, official, HookSource.FAVOUR, strong=False)
            tally.bought += 1
            await ctx.session.flush()
    for row in await ctx.session.scalars(select(PayrollRow).where(PayrollRow.faction_entity_id == faction.id)):
        official_row = await ctx.session.get(EntityRow, row.official_entity_id)
        if official_row is None or profile.treasury < row.bribe:
            continue
        profile.treasury -= row.bribe
        await give_coin(ctx.session, ctx.rules, official_row, row.bribe)


async def swear_silence(ctx: TickContext, faction: EntityRow, tally: CrimeTally) -> None:
    members = await ctx.session.scalars(select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id == faction.id))
    for mortal_id in sorted(members):
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is None or held(mortal.id) or await oaths_of(ctx, mortal.id, OathKind.SILENCE):
            continue
        await swear(ctx, mortal, OathKind.SILENCE, recipient_id=faction.id, note_text=f"the code of {faction.name}")
        tally.sworn += 1


async def punish_informers(ctx: TickContext, faction: EntityRow, tally: CrimeTally) -> None:
    if not ctx.rng(f"informer.{faction.id}").chance(ctx.rules.crime_orgs.traitor_pct):
        return
    member = await ctx.session.scalar(
        select(FactionMembershipRow)
        .where(FactionMembershipRow.faction_entity_id == faction.id, FactionMembershipRow.rank != FactionRank.LEADER)
        .order_by(FactionMembershipRow.joined_epoch.desc(), FactionMembershipRow.mortal_entity_id)
        .limit(1)
    )
    mortal = await ctx.session.get(EntityRow, member.mortal_entity_id) if member is not None else None
    if mortal is None or held(mortal.id):
        return
    tally.traitors += 1
    await break_on(ctx, [mortal.id], OathKind.SILENCE, f"talked about {faction.name}", recipient_id=faction.id)
    for stance in await ctx.session.scalars(select(CrimeStanceRow).where(CrimeStanceRow.faction_entity_id == faction.id)):
        if "strength" not in stance.locked:
            stance.strength = clamp_int(stance.strength + ctx.rules.crime_orgs.suppress_loss, 0, PERCENT)
    if await slay(ctx, mortal, Harm(ctx.rules.casualties.wound_hp, HarmCause.PUNISHMENT, TRAITOR_DEATH, killer_id=faction.id)):
        await note(ctx, f"{mortal.name} talked, and {faction.name} kept its code.", key="crime.informer_killed", ids=[mortal.id, faction.id])


async def take_stance(ctx: TickContext, faction: EntityRow, profile: FactionProfileRow, tally: CrimeTally) -> None:
    town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id) if profile.home_entity_id is not None else None
    realm_id = await realm_of_community(ctx.session, town.settlement_entity_id) if town is not None else None
    if town is None or realm_id is None or held(realm_id) or town.crime < ctx.rules.turf.claim_crime:
        return
    if await ctx.session.get(CrimeStanceRow, (realm_id, faction.id)) is not None or not ctx.rng(f"crime_stance.{faction.id}").chance(
        ctx.rules.crime_orgs.stance_pct
    ):
        return
    realm = await ctx.session.get(EntityRow, realm_id)
    values = await values_for(ctx, realm) if realm is not None else {}
    stance = CrimeStance.SUPPRESS if values.get(ValueAxis.LAW, 0) >= values.get(ValueAxis.WEALTH, 0) else CrimeStance.CO_OPT
    ctx.session.add(
        CrimeStanceRow(polity_entity_id=realm_id, faction_entity_id=faction.id, stance=stance, strength=PERCENT // 2, since_epoch=ctx.epoch, locked=[])
    )
    tally.stances += 1


async def inform(ctx: TickContext, stance: CrimeStanceRow, town_id: int) -> bool:
    if not ctx.rng(f"crime_informant.{stance.faction_entity_id}").chance(ctx.rules.crime_orgs.informant_pct * stance.strength / PERCENT):
        return False
    secret = await ctx.session.scalar(
        select(SecretRow)
        .join(EntityRow, EntityRow.id == SecretRow.holder_node_id)
        .where(EntityRow.location_id == town_id, SecretRow.exposed_epoch.is_(None))
        .order_by(SecretRow.id)
        .limit(1)
    )
    return secret is not None and await learn(ctx, secret, stance.polity_entity_id)


async def bear_stances(ctx: TickContext) -> None:
    table = ctx.rules.crime_orgs
    for stance in list(await ctx.session.scalars(select(CrimeStanceRow).order_by(CrimeStanceRow.polity_entity_id, CrimeStanceRow.faction_entity_id))):
        if held(stance.polity_entity_id, stance.faction_entity_id):
            continue
        profile = await ctx.session.get(FactionProfileRow, stance.faction_entity_id)
        if profile is None or profile.home_entity_id is None:
            continue
        weight = stance.strength / PERCENT
        if stance.stance is CrimeStance.SUPPRESS:
            paid = int(
                bool(list(await ctx.session.scalars(select(PayrollRow.official_entity_id).where(PayrollRow.faction_entity_id == stance.faction_entity_id))))
            )
            shield = 1 - paid * table.payroll_shield_pct / PERCENT
            for turf in await ctx.session.scalars(select(TurfRow).where(TurfRow.faction_entity_id == stance.faction_entity_id)):
                if "strength" not in turf.locked:
                    turf.strength = clamp_int(round_half_up(turf.strength - table.suppress_loss * weight * shield), 0, PERCENT)
        else:
            town = await ctx.session.get(SettlementProfileRow, profile.home_entity_id)
            if town is not None and "crime" not in town.locked:
                town.crime = clamp_int(round_half_up(town.crime - table.co_opt_crime * weight), 0, PERCENT)
            await inform(ctx, stance, profile.home_entity_id)


async def run_underworld(ctx: TickContext, tally: CrimeTally) -> None:
    for faction, profile in await crime_orgs(ctx.session):
        await keep_rackets(ctx, faction, profile, tally)
        await buy_officials(ctx, faction, profile, tally)
        await swear_silence(ctx, faction, tally)
        await punish_informers(ctx, faction, tally)
        await take_stance(ctx, faction, profile, tally)
    await ctx.session.flush()
    await bear_stances(ctx)
    await ctx.session.flush()
