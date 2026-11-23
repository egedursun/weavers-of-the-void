from typing import Protocol

from sqlalchemy import select

from aerona.catalog.war_w52 import ARMY_ROLES, CHASING, STAFFED_ROLES, UNRESOLVED_FATES, WINTERING
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow, ArmyUnitRow, BattleCasualtyRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.honours import UnitHonourKind
from aerona.domain.enums.military import ArmyRole, CasualtyFate, Stance
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.engine.belonging.fugitives_w52 import flee
from aerona.engine.context import TickContext
from aerona.engine.honours.units import HonourTally, bestow, name_unit
from aerona.engine.lore.taboos import dead_season
from aerona.engine.military.aftermath import record_stacks
from aerona.engine.military.battle import BattleResult
from aerona.engine.military.engineering import RIVERS
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.mind.book import traits_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.records import death_path


class Marching(Protocol):
    @property
    def army(self) -> EntityRow: ...

    @property
    def owner(self) -> EntityRow: ...

    @property
    def profile(self) -> ArmyProfileRow: ...


async def officer(ctx: TickContext, army_id: int, role: ArmyRole) -> ArmyOfficerRow | None:
    return await ctx.session.scalar(
        select(ArmyOfficerRow)
        .where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role == role, ArmyOfficerRow.until_epoch.is_(None))
        .order_by(ArmyOfficerRow.id)
        .limit(1)
    )


def role_effect(ctx: TickContext, role: ArmyRole) -> int:
    key = ARMY_ROLES[role].effect_rule
    return int(getattr(ctx.rules.armies, key)) if key is not None else 0


async def appoint(ctx: TickContext, army_id: int, mortal_id: int, role: ArmyRole) -> ArmyOfficerRow:
    current = await officer(ctx, army_id, role)
    if current is not None and current.mortal_entity_id != mortal_id:
        current.until_epoch = ctx.epoch
    if current is not None and current.mortal_entity_id == mortal_id:
        return current
    row = ArmyOfficerRow(army_entity_id=army_id, mortal_entity_id=mortal_id, role=role, since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def staff_army(ctx: TickContext, army: EntityRow, owner: EntityRow) -> int:
    if held(army.id):
        return 0
    taken = set(await ctx.session.scalars(select(ArmyOfficerRow.mortal_entity_id).where(ArmyOfficerRow.until_epoch.is_(None))))
    homes = {owner.id, owner.location_id or 0}
    appointed = 0
    for role, mortal_role in STAFFED_ROLES.items():
        if await officer(ctx, army.id, role) is not None:
            continue
        found = await ctx.session.scalar(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.mortal_role == mortal_role,
                await present_among(ctx.session, homes),
                EntityRow.id.not_in(taken or {0}),
            )
            .order_by(EntityRow.id)
            .limit(1)
        )
        if found is None or held(found.id):
            continue
        await appoint(ctx, army.id, found.id, role)
        taken.add(found.id)
        appointed += 1
    return appointed


async def keep_chaplain(ctx: TickContext, army_id: int, profile: ArmyProfileRow, rows: list[ArmyUnitRow]) -> bool:
    if await officer(ctx, army_id, ArmyRole.CHAPLAIN) is None:
        return False
    effect = role_effect(ctx, ArmyRole.CHAPLAIN)
    for row in rows:
        if "morale" not in row.locked:
            row.morale = clamp_int(row.morale + effect // 2, 0, PERCENT)
    if "disease" not in profile.locked:
        profile.disease = clamp_int(profile.disease - effect // 4, 0, PERCENT)
    return True


async def keep_paymaster(ctx: TickContext, army_id: int, profile: ArmyProfileRow) -> bool:
    staff = await officer(ctx, army_id, ArmyRole.PAYMASTER)
    if staff is None:
        return False
    effect = role_effect(ctx, ArmyRole.PAYMASTER)
    traits = await traits_of(ctx.session, staff.mortal_entity_id)
    if TraitKind.GREEDY in traits and TraitKind.HONEST not in traits:
        if "war_chest" not in profile.locked:
            profile.war_chest = max(0, profile.war_chest - round_half_up(profile.war_chest * effect / PERCENT))
        if "mutiny" not in profile.locked:
            profile.mutiny = clamp_int(profile.mutiny + effect // 2, 0, PERCENT)
        return False
    if "mutiny" not in profile.locked:
        honest = 2 if TraitKind.HONEST in traits else 1
        profile.mutiny = clamp_int(profile.mutiny - effect * honest // 2, 0, PERCENT)
    return True


async def keep_staff(ctx: TickContext, march: Marching, rows: list[ArmyUnitRow], *, first: bool) -> None:
    if first:
        await staff_army(ctx, march.army, march.owner)
    await keep_chaplain(ctx, march.army.id, march.profile, rows)
    await keep_paymaster(ctx, march.army.id, march.profile)


async def scouted(ctx: TickContext, army_id: int, dead: int) -> int:
    if dead <= 0 or await officer(ctx, army_id, ArmyRole.SCOUT_MASTER) is None:
        return dead
    return round_half_up(dead * (PERCENT - role_effect(ctx, ArmyRole.SCOUT_MASTER)) / PERCENT)


def winter_cut(ctx: TickContext, profile: ArmyProfileRow, dead: int) -> int:
    if profile.stance is not Stance.WINTER_QUARTERS or dead <= 0:
        return dead
    return round_half_up(dead * (PERCENT - ctx.rules.campaign.winter_quarters_attrition_cut_pct) / PERCENT)


def escorted_chance(ctx: TickContext, profile: ArmyProfileRow, chance: float) -> float:
    if profile.stance is not Stance.ESCORT:
        return chance
    return chance * (PERCENT - ctx.rules.campaign.escort_raid_cut_pct) / PERCENT


async def refine_stance(
    ctx: TickContext,
    army: EntityRow,
    profile: ArmyProfileRow,
    *,
    attacking: bool,
    enemy_profile: ArmyProfileRow | None,
    enemy_army: EntityRow | None,
    season: WorldSeasonRow | None,
    before: Stance,
) -> Stance:
    if "stance" in profile.locked or held(army.id):
        return profile.stance
    chosen = profile.stance
    if chosen in WINTERING and season is not None and dead_season(ctx, season.growth) and enemy_profile is None:
        chosen = Stance.WINTER_QUARTERS
    elif (
        enemy_profile is not None
        and enemy_army is not None
        and chosen in CHASING
        and (enemy_profile.stance is Stance.RETREAT or stat_or(enemy_army, "morale", PERCENT) <= ctx.rules.campaigns.disband_morale)
    ):
        chosen = Stance.PURSUE
    elif (
        attacking
        and enemy_profile is not None
        and enemy_profile.stance is Stance.RAID
        and len(profile.supply_line or []) - 1 >= ctx.rules.logistics.raid_line_length
        and chosen is Stance.MARCH
    ):
        chosen = Stance.ESCORT
    profile.stance = chosen
    if chosen is not before:
        await record(ctx, "army.stance", roles={IncidentRole.SUBJECT: army.id}, facts={"stance": chosen})
    return chosen


async def honour_army(ctx: TickContext, army_id: int, kind: UnitHonourKind, place: str, tally: HonourTally) -> int:
    if held(army_id):
        return 0
    honoured = 0
    for row in list(
        await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id, ArmyUnitRow.count > 0).order_by(ArmyUnitRow.id))
    ):
        named = await name_unit(ctx, row, tally)
        if named is None:
            continue
        await bestow(ctx, named, kind, place, tally, army_id=army_id)
        await record(ctx, "unit.honoured", roles={IncidentRole.SUBJECT: army_id}, facts={"honour": kind, "unit": named.name, "place": place})
        honoured += 1
    return honoured


async def crossed_already(ctx: TickContext, army_id: int, place: str) -> bool:
    named = select(NamedUnitRow.id).join(ArmyUnitRow, ArmyUnitRow.id == NamedUnitRow.unit_id).where(ArmyUnitRow.army_entity_id == army_id)
    found = await ctx.session.scalar(
        select(UnitHonourRow.id)
        .where(UnitHonourRow.named_unit_id.in_(named), UnitHonourRow.kind == UnitHonourKind.CROSSING, UnitHonourRow.note == place)
        .limit(1)
    )
    return found is not None


async def honour_crossing(ctx: TickContext, army: EntityRow, region: RegionEnvironmentRow | None, *, moved: bool, contested: bool) -> int:
    if not moved or not contested or region is None or region.river_class not in RIVERS:
        return 0
    land = await ctx.session.get(EntityRow, region.entity_id)
    place = land.name if land is not None else "a river"
    if await crossed_already(ctx, army.id, place):
        return 0
    return await honour_army(ctx, army.id, UnitHonourKind.CROSSING, place, HonourTally())


async def pursue(ctx: TickContext, result: BattleResult, winner_army_id: int) -> int:
    profile = await ctx.session.get(ArmyProfileRow, winner_army_id)
    if profile is None or profile.stance is not Stance.PURSUE or held(winner_army_id) or result.loser is None:
        return 0
    table = ctx.rules.campaign
    slain = 0
    for stack in result.loser.stacks:
        if stack.row.missing <= 0 or "missing" in stack.row.locked:
            continue
        cut = round_half_up(stack.row.missing * table.pursuit_kill_pct / PERCENT)
        stack.row.missing -= cut
        slain += cut
    if ctx.rng(f"pursuit.ambush.{winner_army_id}.{ctx.epoch}").chance(table.pursuit_ambush_pct):
        army = await living_entity(ctx.session, winner_army_id)
        if army is not None:
            rows = await stacks_of(ctx.session, army.id)
            take(rows, round_half_up((stat(army, "size") or 0) * table.pursuit_ambush_loss_pct / PERCENT))
            sync(army, rows, ctx.rules)
    return slain


async def tell_casualties(ctx: TickContext, battle: BattleRow, result: BattleResult, slain: int) -> None:
    sides = (result.attacker, result.defender)
    stacks = [stack for side in sides for stack in side.stacks]
    await record(
        ctx,
        "battle.casualties",
        roles={IncidentRole.ACTOR: battle.winner_entity_id, IncidentRole.OPPONENT: battle.loser_entity_id},
        facts={
            "killed": sum(stack.killed for stack in stacks) + slain,
            "wounded": sum(stack.walking + stack.stretcher for stack in stacks),
            "captured": sum(stack.captured for stack in stacks),
            "missing": sum(stack.missing for stack in stacks) - slain,
            "deserted": sum(stack.deserted for stack in stacks),
        },
        place=battle.place_entity_id,
    )


async def after_battle(ctx: TickContext, battle: BattleRow, result: BattleResult, winner_army_id: int) -> int:
    record_stacks(ctx, battle, result)
    slain = await pursue(ctx, result, winner_army_id)
    await tell_casualties(ctx, battle, result, slain)
    return slain


async def scatter_named(ctx: TickContext, battle_id: int, mortal: EntityRow, side_id: int, *, rout_pct: int) -> CasualtyFate | None:
    table = ctx.rules.casualties
    rng = ctx.rng(f"scatter.{battle_id}.{mortal.id}")
    if rng.chance(table.loser_missing_pct * rout_pct / PERCENT):
        fate = CasualtyFate.MISSING
    elif rng.chance(table.loser_deserted_pct * rout_pct / PERCENT):
        fate = CasualtyFate.DESERTED
    else:
        return None
    ctx.session.add(BattleCasualtyRow(battle_id=battle_id, mortal_entity_id=mortal.id, side_entity_id=side_id, fate=fate, harm=0, note=None))
    if fate is CasualtyFate.DESERTED:
        await desert_named(ctx, mortal, battle_id, side_id)
    return fate


async def desert_named(ctx: TickContext, mortal: EntityRow, battle_id: int, side_id: int) -> None:
    if ctx.rng(f"deserter.bandit.{mortal.id}.{battle_id}").chance(ctx.rules.casualties.deserted_bandit_pct):
        mortal.mortal_role = MortalRole.BANDIT
        return
    home = mortal.affiliated_entity_id
    if home is not None and await living_entity(ctx.session, home) is not None:
        mortal.location_id = home
    await flee(ctx, mortal, FugitiveKind.DESERTER, side_id)


async def resolve_missing(ctx: TickContext) -> int:
    table = ctx.rules.casualties
    rows = await ctx.session.scalars(
        select(BattleCasualtyRow)
        .join(BattleRow, BattleRow.id == BattleCasualtyRow.battle_id)
        .where(BattleCasualtyRow.fate.in_(list(UNRESOLVED_FATES)), BattleCasualtyRow.resolved_epoch.is_(None), BattleRow.epoch < ctx.epoch)
        .order_by(BattleCasualtyRow.id)
    )
    resolved = 0
    for row in list(rows):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is None:
            row.resolved_epoch = ctx.epoch
            continue
        if held(mortal.id):
            continue
        rng = ctx.rng(f"missing.{row.id}.{ctx.epoch}")
        battle = await ctx.session.get(BattleRow, row.battle_id)
        wild = battle is not None and battle.place_entity_id is not None and await wild_place(ctx, battle.place_entity_id)
        if rng.chance(table.missing_return_pct):
            if row.side_entity_id is not None and await living_entity(ctx.session, row.side_entity_id) is not None:
                mortal.location_id = row.side_entity_id
            note = "battle.missing_returned"
        elif wild or rng.chance(table.deserted_bandit_pct):
            mortal.mortal_role = MortalRole.BANDIT
            note = "battle.missing_turned_bandit"
        else:
            await death_path(ctx, mortal, "was found dead after the rout", None, "missing", forced=True, manner=DeathCause.BATTLE)
            note = "battle.missing_found_dead"
        row.resolved_epoch = ctx.epoch
        row.note = note.removeprefix("battle.missing_").replace("_", " ")
        resolved += 1
        await record(ctx, note, roles={IncidentRole.SUBJECT: mortal.id})
    return resolved


async def wild_place(ctx: TickContext, place_id: int) -> bool:
    land = await ctx.session.get(RegionEnvironmentRow, place_id)
    if land is None:
        place = await ctx.session.get(EntityRow, place_id)
        land = await ctx.session.get(RegionEnvironmentRow, place.location_id) if place is not None and place.location_id is not None else None
    return land is not None and land.forest_cover >= ctx.rules.casualties.wild_cover
