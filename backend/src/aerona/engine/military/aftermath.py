from sqlalchemy import select

from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, BattleCasualtyRow, BattleStackRow
from aerona.db.tables.warfare import ArmyRow, BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.demography import AgeBand, CohortCondition
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import ScarKind, TerrainKind, WeatherKind
from aerona.domain.enums.military import CasualtyFate, UnitKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import cohorts_of, row_for
from aerona.engine.environment.book import add_scar
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.battle import BattleResult, Side, target_class
from aerona.engine.military.units import drill_fields
from aerona.engine.primitives.levies import levies_from
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, shift_stat, stat
from aerona.engine.primitives.strength import equipment
from aerona.engine.primitives.transfers import move_amount

EXOTIC = frozenset({TerrainKind.FLESH, TerrainKind.VOID_SHORE, TerrainKind.CRYSTAL_FIELD})
RECOVERING = CohortCondition.SICK


def record_stacks(ctx: TickContext, battle: BattleRow, result: BattleResult) -> int:
    made = 0
    for side in (result.attacker, result.defender):
        for stack in side.stacks:
            ctx.session.add(
                BattleStackRow(
                    battle_id=battle.id,
                    side_entity_id=side.entity.id,
                    army_entity_id=stack.row.army_entity_id,
                    kind=stack.row.kind,
                    label=stack.spec.label,
                    start=stack.start,
                    lost=stack.lost,
                    wounded=stack.walking + stack.stretcher,
                    routed=stack.routed,
                    killed=stack.killed,
                    walking=stack.walking,
                    stretcher=stack.stretcher,
                    captured=stack.captured,
                    missing=stack.missing,
                    deserted=stack.deserted,
                    reserve=stack.reserve,
                    organisation=stack.row.organisation,
                    ammunition_spent=stack.spent,
                    formation=stack.row.formation,
                    morale_state=stack.row.morale_state,
                    target_class=target_class(ctx.rules, stack),
                )
            )
            made += 1
    return made


def note_casualty(ctx: TickContext, battle_id: int | None, mortal: EntityRow, *, side_id: int | None, fate: CasualtyFate, harm: int, note: str) -> None:
    if battle_id is None:
        return
    ctx.session.add(BattleCasualtyRow(battle_id=battle_id, mortal_entity_id=mortal.id, side_entity_id=side_id, fate=fate, harm=harm, note=note[:240]))


def morale_sheet(result: BattleResult) -> dict[str, dict[str, int]]:
    sheet: dict[str, dict[str, int]] = {}
    for side in (result.attacker, result.defender):
        parts = dict(side.morale_parts)
        parts["terror_taken"] = -(result.defender.terror_dealt if side is result.attacker else result.attacker.terror_dealt)
        parts["willpower"] = side.willpower
        sheet[str(side.entity.id)] = parts
    return sheet


def magic_sheet(result: BattleResult) -> dict[str, int]:
    sides = (result.attacker, result.defender)
    return {
        "fog": sum(1 for side in sides if side.fog),
        "healed": sum(side.healed for side in sides),
        "raised": sum(side.raised_dead for side in sides),
        "terror": sum(side.terror_dealt for side in sides),
        "backlash": sum(side.backlash for side in sides),
    }


async def send_home_wounded(ctx: TickContext, side: Side, wounded: int) -> int:
    owner = side.entity
    if wounded <= 0:
        return 0
    if not levies_from(owner) or owner.status is not EntityStatus.CANON:
        return 0
    before = headcount(owner)
    with flowing(FlowCategory.CREATION):
        after = put_stat(ctx.rules, owner, headcount_key(owner), before + wounded)
    returned = (after or before) - before
    if returned <= 0:
        return 0
    rows = await cohorts_of(ctx.session, owner.id)
    moved = 0
    for key in sorted(rows, key=lambda item: -rows[item].count):
        band, sex, social, condition = key
        if moved >= returned or band is not AgeBand.ADULT or social is not SocialClass.WARRIOR or condition is not CohortCondition.NONE:
            continue
        part = min(rows[key].count, returned - moved)
        if move_amount(rows[key], row_for(ctx.session, rows, owner.id, (band, sex, social, RECOVERING), ctx.epoch), "count", part):
            moved += part
    return returned


async def recover_wounded(ctx: TickContext) -> int:
    epochs = max(1, ctx.rules.battle_magic.recovery_epochs)
    recovered = 0
    rows = list(
        await ctx.session.scalars(
            select(CohortRow).where(CohortRow.condition == RECOVERING, CohortRow.social_class == SocialClass.WARRIOR, CohortRow.count > 0)
        )
    )
    for row in rows:
        if held(row.community_entity_id):
            continue
        healed = max(1, row.count // epochs)
        cohorts = await cohorts_of(ctx.session, row.community_entity_id)
        veterans = row_for(ctx.session, cohorts, row.community_entity_id, (row.age_band, row.sex, row.social_class, CohortCondition.VETERAN), ctx.epoch)
        if move_amount(row, veterans, "count", healed):
            recovered += healed
    return recovered


async def raise_the_dead(ctx: TickContext, side: Side) -> int:
    if side.raised_dead <= 0:
        return 0
    found = next((stack.row for stack in side.stacks if stack.row.kind is UnitKind.GHOST_HOST and stack.row.army_entity_id == side.army.id), None)
    if found is None:
        found = ArmyUnitRow(
            army_entity_id=side.army.id,
            kind=UnitKind.GHOST_HOST,
            count=0,
            quality=PERCENT // 2,
            weapons=["claw"],
            experience=0,
            morale=PERCENT,
            fatigue=0,
            wounded=0,
            condition=PERCENT,
            origin_entity_id=side.entity.id,
            locked=[],
            **drill_fields(ctx.rules, UNITS[UnitKind.GHOST_HOST]),
        )
        ctx.session.add(found)
    with flowing(FlowCategory.CREATION):
        found.count += side.raised_dead
        shift_stat(side.army, "size", side.raised_dead)
    return side.raised_dead


async def take_baggage(ctx: TickContext, winner: Side, loser: Side) -> int:
    taken = winner.baggage_taken
    if taken <= 0:
        return 0
    profile = await ctx.session.get(ArmyProfileRow, loser.army.id)
    if profile is not None:
        lost_loot = min(profile.loot, taken)
        profile.loot -= lost_loot
        profile.baggage = max(0, profile.baggage - (taken - lost_loot))
    mine = await ctx.session.get(ArmyProfileRow, winner.army.id)
    if mine is not None:
        mine.loot += taken
    return taken


async def street_toll(ctx: TickContext, terrain: TerrainKind | None, place: EntityRow | None) -> int:
    if terrain is not TerrainKind.URBAN or place is None or stat(place, "population") is None:
        return 0
    dead = round_half_up((stat(place, "population") or 0) * ctx.rules.battle_terrain.street_civilian_pct / PERCENT)
    if dead:
        with flowing(FlowCategory.CASUALTY):
            shift_stat(place, "population", -dead)
    return dead


async def marsh_fever(ctx: TickContext, terrain: TerrainKind | None, sides: tuple[Side, Side]) -> int:
    if terrain is not TerrainKind.MARSH:
        return 0
    for side in sides:
        side.profile.disease = clamp_int(side.profile.disease + ctx.rules.battle_terrain.marsh_disease, 0, PERCENT)
    return len(sides)


async def exotic_toll(ctx: TickContext, terrain: TerrainKind | None, region: RegionEnvironmentRow | None, mortals: list[EntityRow]) -> int:
    if terrain not in EXOTIC:
        return 0
    table = ctx.rules.battle_terrain
    shaken = 0
    for mortal in mortals:
        if mortal.status is EntityStatus.CANON and mortal.sanity is not None:
            mortal.sanity = clamp_int(mortal.sanity - table.exotic_sanity_loss, 0, PERCENT)
            shaken += 1
    if region is not None:
        add_scar(region, ScarKind.LEAK_WOUND, table.exotic_leak_depth)
    return shaken


async def flaring_items(ctx: TickContext, weather: WeatherKind | None, side: Side, heroes: list[EntityRow]) -> int:
    if weather is not WeatherKind.MAGIC_STORM:
        return 0
    table = ctx.rules.battle_weather
    flared = 0
    for hero in heroes:
        items = [item for item in await equipment(ctx.session, hero.id) if (stat(item, "might") or 0) > 0]
        if not items:
            continue
        flared += 1
        side.leadership += table.item_flare
        side.morale_parts["flaring_items"] = side.morale_parts.get("flaring_items", 0) + table.item_flare
        if ctx.rng(f"flare.{hero.id}.{ctx.epoch}").chance(table.item_flare_risk):
            await apply_hits(ctx, hero, Harm(table.item_flare_hp, HarmCause.BATTLE, "burned by a flaring relic in a magic storm"), lethal=False)
    return flared


async def owner_army(ctx: TickContext, army_id: int) -> EntityRow | None:
    row = await ctx.session.get(ArmyRow, army_id)
    return await living_entity(ctx.session, row.owner_entity_id) if row is not None else None


async def cohesion_after(ctx: TickContext, result: BattleResult) -> None:
    table = ctx.rules.campaign_depth
    if result.winner is None or result.loser is None:
        return
    for side, delta in ((result.winner, table.cohesion_victory), (result.loser, -table.cohesion_defeat)):
        side.profile.cohesion = clamp_int(side.profile.cohesion + delta, 0, PERCENT)
