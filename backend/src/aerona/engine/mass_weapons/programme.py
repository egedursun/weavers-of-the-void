from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mass_weapons import MassHarm, MassReach, ProgrammeStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.lore.research import techniques_of
from aerona.engine.mass_weapons.book import REACH_RANK, ArsenalTally, can_build, knows_how, league_partners, postures_of, rivals_of, technique_for
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

NEXT = {ProgrammeStage.SOUGHT: ProgrammeStage.BUILDING, ProgrammeStage.BUILDING: ProgrammeStage.READY}


async def begin(ctx: TickContext, holder: EntityRow, harm: MassHarm, reach: MassReach, tally: ArsenalTally) -> MassWeaponRow:
    query = select(MassWeaponRow).where(MassWeaponRow.holder_entity_id == holder.id, MassWeaponRow.harm == harm, MassWeaponRow.reach == reach)
    found = await ctx.session.scalar(query.order_by(MassWeaponRow.id).limit(1))
    if found is not None:
        return found
    weapon = MassWeaponRow(holder_entity_id=holder.id, harm=harm, reach=reach, begun_epoch=ctx.epoch, seen_by=[], locked=[])
    ctx.session.add(weapon)
    await ctx.session.flush()
    tally.begun += 1
    await reveal(ctx, weapon, tally)
    return weapon


async def reveal(ctx: TickContext, weapon: MassWeaponRow, tally: ArsenalTally) -> None:
    table = ctx.rules.mass_weapons
    watchers = await rivals_of(ctx.session, weapon.holder_entity_id)
    partners = await league_partners(ctx.session, weapon.holder_entity_id)
    seen = set(weapon.seen_by or [])
    for watcher in sorted(watchers | partners):
        if watcher in seen:
            continue
        if watcher in partners or ctx.rng(f"arsenal.seen.{weapon.id}.{watcher}.{weapon.stage.value}").chance(table.stage_visibility_pct):
            seen.add(watcher)
            await answer_rival(ctx, weapon, watcher, tally)
    if "seen_by" not in (weapon.locked or []):
        weapon.seen_by = sorted(seen)
    await record(
        ctx,
        "war.mass_weapon_stage",
        roles={IncidentRole.ACTOR: weapon.holder_entity_id},
        facts={"harm": weapon.harm, "reach": weapon.reach, "stage": weapon.stage, "watchers": len(seen)},
    )


async def answer_rival(ctx: TickContext, weapon: MassWeaponRow, rival_id: int, tally: ArsenalTally) -> None:
    rival = await living_entity(ctx.session, rival_id)
    if rival is None or rival.entity_type is not EntityType.POLITY or held(rival.id):
        return
    if not await knows_how(ctx.session, rival.id, weapon.harm, weapon.reach):
        return
    if ctx.rng(f"arsenal.race.{weapon.id}.{rival.id}").chance(ctx.rules.mass_weapons.arms_race_pct):
        await begin(ctx, rival, weapon.harm, weapon.reach, tally)


async def lend_credibility(ctx: TickContext, holder_id: int, amount: int) -> None:
    for posture in await postures_of(ctx.session, holder_id):
        if "credibility" not in (posture.locked or []):
            posture.credibility = clamp_int(posture.credibility + amount, 0, PERCENT)


async def test(ctx: TickContext, weapon: MassWeaponRow, tally: ArsenalTally) -> None:
    weapon.stage, weapon.tested_epoch = ProgrammeStage.TESTED, ctx.epoch
    await lend_credibility(ctx, weapon.holder_entity_id, ctx.rules.mass_weapons.test_credibility)
    tally.tested += 1
    await record(ctx, "war.mass_weapon_tested", roles={IncidentRole.ACTOR: weapon.holder_entity_id}, facts={"harm": weapon.harm, "reach": weapon.reach})
    await reveal(ctx, weapon, tally)


async def work_on(ctx: TickContext, weapon: MassWeaponRow, tally: ArsenalTally) -> None:
    table = ctx.rules.mass_weapons
    holder = await living_entity(ctx.session, weapon.holder_entity_id)
    if holder is None or "readiness" in (weapon.locked or []) or not await can_build(ctx.session, holder.id, weapon.harm, weapon.reach):
        return
    if not await take_coin(ctx.session, ctx.rules, holder, table.programme_cost * REACH_RANK[weapon.reach]):
        return
    weapon.readiness = clamp_int(weapon.readiness + table.readiness_step, 0, PERCENT)
    if weapon.readiness < PERCENT:
        return
    weapon.readiness = 0
    if weapon.stage in NEXT and "stage" not in (weapon.locked or []):
        weapon.stage = NEXT[weapon.stage]
        tally.staged += 1
        await reveal(ctx, weapon, tally)
    if weapon.stage in {ProgrammeStage.READY, ProgrammeStage.TESTED} and "count" not in (weapon.locked or []):
        weapon.count += 1
        tally.built += 1


async def tend_programmes(ctx: TickContext, tally: ArsenalTally) -> None:
    for weapon in list(await ctx.session.scalars(select(MassWeaponRow).order_by(MassWeaponRow.id))):
        if held(weapon.holder_entity_id):
            continue
        await work_on(ctx, weapon, tally)
        ready = weapon.stage is ProgrammeStage.READY and weapon.count > 0 and "stage" not in (weapon.locked or [])
        if ready and ctx.rng(f"arsenal.test.{weapon.id}.{ctx.epoch}").chance(ctx.rules.mass_weapons.test_chance_pct):
            await test(ctx, weapon, tally)


async def seek_arms(ctx: TickContext, tally: ArsenalTally) -> None:
    query = (
        select(EntityRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for realm in list(await ctx.session.scalars(query)):
        if held(realm.id) or not await rivals_of(ctx.session, realm.id):
            continue
        known = await techniques_of(ctx.session, realm.id)
        choices = [(harm, reach) for harm in MassHarm for reach in (MassReach.REGION, MassReach.SETTLEMENT) if technique_for(harm, reach) in known]
        choice = ctx.rng(f"arsenal.seek.which.{realm.id}.{ctx.epoch}").pick_or_none(choices)
        if choice is not None and ctx.rng(f"arsenal.seek.{realm.id}.{ctx.epoch}").chance(ctx.rules.mass_weapons.seek_chance_pct):
            await begin(ctx, realm, choice[0], choice[1], tally)
