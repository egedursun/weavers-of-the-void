from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy import select

from aerona.catalog.units import STYLE_UNITS, UNITS
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, CaptiveCohortRow, CommanderTraitRow, OccupationRow, SpyNetworkRow, WarAimRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow, WarSideRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import ArmourType, CaptiveFate, CommanderTrait, ShieldType, SpyCover, Stance, StarvationStage, UnitKind, WarAimKind
from aerona.domain.enums.war import SiegeStatus, WarEnding, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.military.captivity import settle_into
from aerona.engine.military.units import profile_of, stacks_of, sync
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.control import lock
from aerona.engine.polity.treaties import allies_called
from aerona.engine.polity.wars import comrades
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.war_resolution import WarSettlement, end_war

Values = Mapping[str, int | str | bool | None]
PERCENT_FIELDS = frozenset({"cohesion", "disease", "entrenchment"})
POSITIVE_FIELDS = frozenset({"supply_days", "war_chest", "loot", "baggage"})
LINK_FIELDS = {"region_id": "region_entity_id", "target_id": "target_entity_id", "blockade_id": "blockade_entity_id"}
STACK_PERCENT = frozenset({"quality", "experience", "morale", "fatigue", "condition"})
STACK_CHOICES: dict[str, Callable[[str], Any]] = {"kind": UnitKind, "armour": ArmourType, "shield": ShieldType}
SIEGE_PERCENT = frozenset({"disease_inside", "disease_outside"})
SIEGE_POSITIVE = frozenset({"supplies", "water", "breaches", "sallies", "rounds"})
SIEGE_CHOICES: dict[str, Callable[[str], Any]] = {"starvation": StarvationStage, "status": SiegeStatus}
NETWORK_PERCENT = frozenset({"depth", "exposure", "intel"})


def percent(key: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
    return value


def positive(key: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be negative.")
    return value


def choice(key: str, parser: Callable[[str], Any], value: object) -> Any:
    try:
        return parser(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error


async def army_profile(ctx: TickContext, army_id: int) -> tuple[EntityRow, ArmyProfileRow]:
    army = await living_entity(ctx.session, army_id)
    if army is None or army.entity_type is not EntityType.ARMY:
        raise NotFoundError("No such living army.")
    owner_row = await ctx.session.get(ArmyRow, army.id)
    owner = await living_entity(ctx.session, owner_row.owner_entity_id) if owner_row is not None else None
    return army, await profile_of(ctx, army, owner)


async def edit_army(ctx: TickContext, army_id: int, values: Values, *, release: list[str]) -> ArmyProfileRow:
    _, profile = await army_profile(ctx, army_id)
    for key, value in values.items():
        if key in PERCENT_FIELDS:
            setattr(profile, key, percent(key, value))
        elif key in POSITIVE_FIELDS:
            setattr(profile, key, positive(key, value))
        elif key in LINK_FIELDS:
            setattr(profile, LINK_FIELDS[key], int(value) if isinstance(value, int) and not isinstance(value, bool) else None)
        elif key == "stance":
            profile.stance = choice(key, Stance, value)
        elif key == "doctrine":
            if str(value) not in STYLE_UNITS:
                raise ValidationFailedError(f"{value} is not a known way of war.")
            profile.doctrine = str(value)
        elif key == "forced_march":
            profile.forced_march = bool(value)
        else:
            raise ValidationFailedError(f"Unknown army field: {key}.")
        profile.locked = lock(profile.locked, key)
    for key in release:
        profile.locked = [item for item in profile.locked if item != key]
    await ctx.session.flush()
    return profile


async def stack(ctx: TickContext, unit_id: int) -> ArmyUnitRow:
    row = await ctx.session.get(ArmyUnitRow, unit_id)
    if row is None:
        raise NotFoundError("No such stack.")
    return row


async def edit_stack(ctx: TickContext, unit_id: int, values: Values) -> ArmyUnitRow:
    row = await stack(ctx, unit_id)
    for key, value in values.items():
        if key in STACK_PERCENT:
            setattr(row, key, percent(key, value))
        elif key in {"count", "wounded"}:
            setattr(row, key, positive(key, value))
        elif key in STACK_CHOICES:
            setattr(row, key, choice(key, STACK_CHOICES[key], value))
        elif key == "helmet":
            row.helmet = bool(value)
        else:
            raise ValidationFailedError(f"Unknown stack field: {key}.")
    await resync(ctx, row.army_entity_id)
    return row


async def add_stack(ctx: TickContext, army_id: int, kind: UnitKind, count: int) -> ArmyUnitRow:
    army, _ = await army_profile(ctx, army_id)
    spec = UNITS[kind]
    row = ArmyUnitRow(
        army_entity_id=army.id,
        kind=kind,
        count=positive("count", count),
        quality=PERCENT // 2,
        armour=spec.armour,
        shield=spec.shield,
        helmet=True,
        weapons=[],
        experience=0,
        morale=ctx.rules.morale.base,
        fatigue=0,
        wounded=0,
        condition=PERCENT,
        social_class=spec.social_class,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await resync(ctx, army.id)
    return row


async def remove_stack(ctx: TickContext, unit_id: int) -> int:
    row = await stack(ctx, unit_id)
    army_id = row.army_entity_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    await resync(ctx, army_id)
    return army_id


async def resync(ctx: TickContext, army_id: int) -> None:
    army = await living_entity(ctx.session, army_id)
    if army is not None:
        sync(army, await stacks_of(ctx.session, army_id), ctx.rules)
    await ctx.session.flush()


async def edit_siege(ctx: TickContext, siege_id: int, values: Values) -> SiegeRow:
    row = await ctx.session.get(SiegeRow, siege_id)
    if row is None:
        raise NotFoundError("No such siege.")
    for key, value in values.items():
        if key in SIEGE_PERCENT:
            setattr(row, key, percent(key, value))
        elif key in SIEGE_POSITIVE:
            setattr(row, key, positive(key, value))
        elif key == "walls_level":
            row.walls_level = min(5, positive(key, value))
        elif key in SIEGE_CHOICES:
            setattr(row, key, choice(key, SIEGE_CHOICES[key], value))
        else:
            raise ValidationFailedError(f"Unknown siege field: {key}.")
    if row.status is not SiegeStatus.ONGOING and row.ended_epoch is None:
        row.ended_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def ongoing(ctx: TickContext, war_id: int) -> WarRow:
    war = await ctx.session.get(WarRow, war_id)
    if war is None:
        raise NotFoundError("No such war.")
    if war.status is WarStatus.ENDED:
        raise ConflictError("That war is over.")
    return war


async def set_aim(ctx: TickContext, war_id: int, side_id: int, kind: WarAimKind, *, target_id: int | None, achieved: int) -> WarAimRow:
    war = await ongoing(ctx, war_id)
    if await ctx.session.get(WarSideRow, (war.id, side_id)) is None:
        raise ValidationFailedError("That side does not fight in this war.")
    row = await ctx.session.scalar(select(WarAimRow).where(WarAimRow.war_id == war.id, WarAimRow.side_entity_id == side_id, WarAimRow.kind == kind).limit(1))
    if row is None:
        row = WarAimRow(war_id=war.id, side_entity_id=side_id, kind=kind, params={}, achieved=0)
        ctx.session.add(row)
    row.target_entity_id = target_id
    row.achieved = percent("achieved", achieved)
    await ctx.session.flush()
    return row


async def drop_aim(ctx: TickContext, aim_id: int) -> None:
    row = await ctx.session.get(WarAimRow, aim_id)
    if row is None:
        raise NotFoundError("No such war aim.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def impose_peace(ctx: TickContext, war_id: int, victor_id: int, terms: list[WarAimKind]) -> WarSettlement:
    war = await ongoing(ctx, war_id)
    rows = await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None)))
    sides = {row.entity_id: row.side for row in rows}
    if victor_id not in sides:
        raise ValidationFailedError("The victor must fight in this war.")
    loser_id = next((side for side, flag in sorted(sides.items()) if flag is not sides[victor_id]), None)
    if loser_id is None:
        raise ConflictError("This war has no other side to submit.")
    for kind in terms:
        query = select(WarAimRow).where(WarAimRow.war_id == war.id, WarAimRow.side_entity_id == victor_id, WarAimRow.kind == kind)
        found = await ctx.session.scalar(query.limit(1))
        await set_aim(ctx, war.id, victor_id, kind, target_id=found.target_entity_id if found is not None else loser_id, achieved=PERCENT)
    return await end_war(ctx, war, WarEnding.VICTORY, victor_id=victor_id, loser_id=loser_id, reason="peace imposed by decree")


async def call_allies(ctx: TickContext, war_id: int, side_id: int) -> int:
    war = await ongoing(ctx, war_id)
    row = await ctx.session.get(WarSideRow, (war.id, side_id))
    if row is None:
        raise ValidationFailedError("That side does not fight in this war.")
    present = {side.entity_id for side in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id))}
    book = await RealmBook.load(ctx.session)
    joined = 0
    for ally_id in [*comrades(book, side_id), *await allies_called(ctx, side_id)]:
        ally = await living_entity(ctx.session, ally_id)
        if ally_id in present or ally is None or ally.status is not EntityStatus.CANON or ally.entity_type not in {EntityType.PEOPLE, EntityType.SETTLEMENT}:
            continue
        ctx.session.add(WarSideRow(war_id=war.id, entity_id=ally_id, side=row.side, joined_epoch=ctx.epoch))
        present.add(ally_id)
        joined += 1
    await ctx.session.flush()
    return joined


async def set_weariness(ctx: TickContext, war_id: int, side_id: int, weariness: int) -> WarSideRow:
    row = await ctx.session.get(WarSideRow, (war_id, side_id))
    if row is None:
        raise NotFoundError("That side does not fight in this war.")
    row.weariness = percent("weariness", weariness)
    await ctx.session.flush()
    return row


async def edit_occupation(ctx: TickContext, region_id: int, *, control: int | None, resistance: int | None, end: bool) -> OccupationRow | None:
    row = await ctx.session.get(OccupationRow, region_id)
    if row is None:
        raise NotFoundError("That land is not occupied.")
    if end:
        await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    if control is not None:
        row.control = percent("control", control)
    if resistance is not None:
        row.resistance = percent("resistance", resistance)
    await ctx.session.flush()
    return row


async def settle_cohort(ctx: TickContext, cohort_id: int, fate: CaptiveFate, count: int | None) -> CaptiveCohortRow:
    row = await ctx.session.get(CaptiveCohortRow, cohort_id)
    if row is None:
        raise NotFoundError("No such band of captives.")
    if count is not None:
        row.count = positive("count", count)
    if fate is CaptiveFate.HELD:
        row.fate, row.settled_epoch = fate, None
    elif row.fate is CaptiveFate.HELD:
        home = await living_entity(ctx.session, row.origin_entity_id)
        captor = await living_entity(ctx.session, row.captor_entity_id)
        if fate in {CaptiveFate.RELEASED, CaptiveFate.RANSOMED, CaptiveFate.EXCHANGED}:
            settle_into(ctx, home, row.count)
        elif fate in {CaptiveFate.ENSLAVED, CaptiveFate.LABOUR}:
            settle_into(ctx, captor, row.count)
        row.fate, row.settled_epoch = fate, ctx.epoch
    await ctx.session.flush()
    return row


async def set_trait(ctx: TickContext, mortal_id: int, trait: CommanderTrait, *, held: bool) -> bool:
    mortal = await living_entity(ctx.session, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    row = await ctx.session.get(CommanderTraitRow, (mortal.id, trait))
    if held and row is None:
        ctx.session.add(CommanderTraitRow(mortal_entity_id=mortal.id, trait=trait, since_epoch=ctx.epoch))
    elif not held and row is not None:
        await ctx.session.delete(row)
    await ctx.session.flush()
    return held


async def edit_network(ctx: TickContext, network_id: int, values: Values, *, dismantle: bool) -> SpyNetworkRow | None:
    row = await ctx.session.get(SpyNetworkRow, network_id)
    if row is None:
        raise NotFoundError("No such spy network.")
    if dismantle:
        await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    for key, value in values.items():
        if key in NETWORK_PERCENT:
            setattr(row, key, percent(key, value))
        elif key == "agents":
            row.agents = positive(key, value)
        elif key == "cover":
            row.cover = choice(key, SpyCover, value)
        elif key == "spymaster_id":
            row.spymaster_entity_id = int(value) if isinstance(value, int) and not isinstance(value, bool) else None
        else:
            raise ValidationFailedError(f"Unknown network field: {key}.")
    await ctx.session.flush()
    return row
