from dataclasses import dataclass
from math import ceil

from sqlalchemy import select

from aerona.catalog.operations import ECHELON_LABELS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.operations import EchelonRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.military import RESTING, ArmyRole, Stance
from aerona.domain.enums.operations import EchelonLevel, EchelonOrder
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.military.command import command_areas
from aerona.engine.military.units import stacks_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.relations.persuasion import office_holder
from aerona.engine.services.war import ongoing_wars
from aerona.rules.registry import Rules

L = EchelonLevel
STAFF_ROLES = (ArmyRole.SUB_COMMANDER, ArmyRole.QUARTERMASTER)


@dataclass
class CommandTally:
    armies: int = 0
    formed: int = 0
    assigned: int = 0
    groups: int = 0
    standing: int = 0
    ordered: int = 0


@dataclass(frozen=True)
class CommandReport:
    order: EchelonOrder
    ordered: int
    standing: int


def points_for(rules: Rules, staff: int) -> int:
    table = rules.order_of_battle
    return table.base_points + staff * table.staff_points_pct // PERCENT


async def staff_of(ctx: TickContext, army_id: int | None, commander_id: int | None) -> int:
    areas = await command_areas(ctx.session, commander_id)
    officers = 0
    if army_id is not None:
        officers = len(
            list(
                await ctx.session.scalars(
                    select(ArmyOfficerRow.id).where(
                        ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role.in_(STAFF_ROLES), ArmyOfficerRow.until_epoch.is_(None)
                    )
                )
            )
        )
    return clamp_int(sum(areas.values()) // max(1, len(areas)) + officers * ctx.rules.order_of_battle.officer_staff, 0, PERCENT)


async def signals(ctx: TickContext, commander_id: int | None) -> bool:
    if commander_id is None:
        return False
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .join(BondRow, BondRow.target_node_id == ItemProfileRow.item_entity_id)
        .where(
            BondRow.source_node_id == commander_id,
            BondRow.kind == BondKind.OWNS,
            BondRow.state == BondState.ACTIVE,
            ItemProfileRow.item_class == ItemClass.COMMUNICATOR,
        )
        .limit(1)
    )
    return found is not None


async def range_of(ctx: TickContext, commander_id: int | None) -> int:
    table = ctx.rules.order_of_battle
    return table.base_range + (table.signal_range if await signals(ctx, commander_id) else 0)


def refresh(row: EchelonRow, values: dict[str, object]) -> None:
    for key, value in values.items():
        if key not in row.locked:
            setattr(row, key, value)


async def echelons_of(ctx: TickContext, army_id: int) -> list[EchelonRow]:
    return list(await ctx.session.scalars(select(EchelonRow).where(EchelonRow.army_entity_id == army_id).order_by(EchelonRow.id)))


async def sub_commanders(ctx: TickContext, army_id: int) -> list[int]:
    rows = await ctx.session.scalars(
        select(ArmyOfficerRow.mortal_entity_id)
        .where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role == ArmyRole.SUB_COMMANDER, ArmyOfficerRow.until_epoch.is_(None))
        .order_by(ArmyOfficerRow.id)
    )
    return list(rows)


def needed(rules: Rules, stacks: int) -> dict[EchelonLevel, int]:
    table = rules.order_of_battle
    brigades = max(1, ceil(stacks / table.stacks_per_brigade))
    divisions = max(1, ceil(brigades / table.brigades_per_division))
    corps = ceil(divisions / table.divisions_per_corps) if divisions > table.divisions_per_corps else 0
    return {L.CORPS: corps, L.DIVISION: divisions, L.BRIGADE: brigades}


async def form(ctx: TickContext, army: EntityRow, army_row: ArmyRow, region_id: int | None, tally: CommandTally) -> EchelonRow:
    rows = await echelons_of(ctx, army.id)
    top = next((row for row in rows if row.level is L.ARMY), None)
    staff = await staff_of(ctx, army.id, army_row.commander_entity_id)
    span = await range_of(ctx, army_row.commander_entity_id)
    if top is None:
        top = EchelonRow(owner_entity_id=army_row.owner_entity_id, army_entity_id=army.id, level=L.ARMY, name=army.name, formed_epoch=ctx.epoch, locked=[])
        ctx.session.add(top)
        await ctx.session.flush()
        rows.append(top)
        tally.formed += 1
    refresh(
        top,
        {
            "commander_entity_id": army_row.commander_entity_id,
            "hq_region_entity_id": region_id,
            "staff": staff,
            "command_range": span,
            "command_points": points_for(ctx.rules, staff),
        },
    )
    stacks = [row for row in await stacks_of(ctx.session, army.id) if row.count > 0]
    wanted = needed(ctx.rules, len(stacks))
    deputies = await sub_commanders(ctx, army.id)
    for level in (L.CORPS, L.DIVISION, L.BRIGADE):
        present = [row for row in rows if row.level is level]
        for index in range(len(present), wanted[level]):
            row = EchelonRow(
                owner_entity_id=army_row.owner_entity_id,
                army_entity_id=army.id,
                level=level,
                name=f"{ECHELON_LABELS[level]} {index + 1} of {army.name}",
                formed_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(row)
            rows.append(row)
            tally.formed += 1
    await ctx.session.flush()
    link(rows, top)
    for index, row in enumerate(item for item in rows if item.level is not L.ARMY):
        commander = deputies[index] if index < len(deputies) else None
        sub_staff = await staff_of(ctx, None, commander) if commander is not None else staff // 2
        refresh(
            row,
            {
                "commander_entity_id": commander,
                "hq_region_entity_id": region_id,
                "staff": sub_staff,
                "command_range": span,
                "command_points": points_for(ctx.rules, sub_staff),
            },
        )
    tally.assigned += assign(ctx.rules, stacks, [row for row in rows if row.level is L.BRIGADE])
    return top


def link(rows: list[EchelonRow], top: EchelonRow) -> None:
    corps = [row for row in rows if row.level is L.CORPS]
    divisions = [row for row in rows if row.level is L.DIVISION]
    brigades = [row for row in rows if row.level is L.BRIGADE]
    for children, parents in ((corps, [top]), (divisions, corps or [top]), (brigades, divisions or [top])):
        for index, child in enumerate(children):
            if "parent_id" in child.locked and child.parent_id is not None:
                continue
            child.parent_id = parents[index * len(parents) // max(1, len(children))].id


def assign(rules: Rules, stacks: list[ArmyUnitRow], brigades: list[EchelonRow]) -> int:
    if not brigades:
        return 0
    known = {row.id for row in brigades}
    room = {row.id: 0 for row in brigades}
    for stack in stacks:
        if stack.echelon_id in known:
            room[stack.echelon_id] += 1
    moved = 0
    for stack in stacks:
        if stack.echelon_id in known or "echelon_id" in stack.locked:
            continue
        target = min(brigades, key=lambda row: (room[row.id], row.id))
        if room[target.id] >= rules.order_of_battle.stacks_per_brigade and len(brigades) > 1:
            target = min(brigades, key=lambda row: room[row.id])
        stack.echelon_id = target.id
        room[target.id] += 1
        moved += 1
    return moved


async def group(ctx: TickContext, owner: EntityRow, tops: list[EchelonRow], atlas: RegionAtlas, tally: CommandTally) -> None:
    if len(tops) < ctx.rules.order_of_battle.armies_for_group or held(owner.id):
        return
    row = await ctx.session.scalar(
        select(EchelonRow).where(EchelonRow.owner_entity_id == owner.id, EchelonRow.level == L.ARMY_GROUP).order_by(EchelonRow.id).limit(1)
    )
    marshal = await office_holder(ctx.session, owner.id, OfficeKind.MARSHAL, OfficeKind.RULER)
    if row is None:
        row = EchelonRow(
            owner_entity_id=owner.id, army_entity_id=None, level=L.ARMY_GROUP, name=f"Army group of {owner.name}", formed_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
        tally.formed += 1
    staff = await staff_of(ctx, None, marshal)
    refresh(
        row,
        {
            "commander_entity_id": marshal,
            "hq_region_entity_id": atlas.top_region(owner.id),
            "staff": staff,
            "command_range": await range_of(ctx, marshal),
            "command_points": points_for(ctx.rules, staff),
        },
    )
    for top in tops:
        if "parent_id" not in top.locked:
            top.parent_id = row.id
        hops = atlas.region_hops(row.hq_region_entity_id, top.hq_region_entity_id)
        refresh(top, {"in_range": hops is None or hops <= row.command_range})
    tally.groups += 1


async def organise(ctx: TickContext, tally: CommandTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    fighting = {side for item in await ongoing_wars(ctx.session) for side in item.sides}
    tops: dict[int, list[EchelonRow]] = {}
    owners: dict[int, EntityRow] = {}
    rows = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    for army_row in list(rows):
        army = await ctx.session.get(EntityRow, army_row.entity_id)
        owner = await ctx.session.get(EntityRow, army_row.owner_entity_id)
        if army is None or owner is None or held(army.id):
            continue
        profile = await ctx.session.get(ArmyProfileRow, army.id)
        top = await form(ctx, army, army_row, profile.region_entity_id if profile is not None else atlas.top_region(army.id), tally)
        tally.armies += 1
        if owner.id in fighting:
            tops.setdefault(owner.id, []).append(top)
            owners[owner.id] = owner
    for owner_id, items in tops.items():
        await group(ctx, owners[owner_id], items, atlas, tally)


def wanted_order(profile: ArmyProfileRow, attacking: bool, short: bool) -> EchelonOrder:
    if short:
        return EchelonOrder.RESUPPLY
    if profile.stance in RESTING:
        return EchelonOrder.HOLD
    if attacking and profile.stance is not Stance.RETREAT:
        return EchelonOrder.ATTACK
    return EchelonOrder.MANOEUVRE


def cost_of(rules: Rules, order: EchelonOrder) -> int:
    table = rules.order_of_battle
    return table.attack_cost if order is EchelonOrder.ATTACK else table.order_cost


async def issue_orders(ctx: TickContext, army_id: int, profile: ArmyProfileRow, *, attacking: bool, short: bool, tally: CommandTally) -> CommandReport:
    rows = await echelons_of(ctx, army_id)
    order = wanted_order(profile, attacking, short)
    if not rows or held(army_id):
        return CommandReport(order, 0, 0)
    by_id = {row.id: row for row in rows}
    top = next((row for row in rows if row.level is L.ARMY), rows[0])
    parent = await ctx.session.get(EchelonRow, top.parent_id) if top.parent_id is not None else None
    for row in rows:
        if "points_spent" not in row.locked:
            row.points_spent = 0
    if parent is not None and "points_spent" not in parent.locked:
        parent.points_spent = 0
    refresh(top, {"order": spend(ctx.rules, parent, top, order) if parent is not None else order})
    for level in (L.CORPS, L.DIVISION, L.BRIGADE):
        for row in (item for item in rows if item.level is level):
            above = by_id.get(row.parent_id or -1) or top
            given = above.order if above.order is not EchelonOrder.STANDING else EchelonOrder.STANDING
            refresh(row, {"order": spend(ctx.rules, above, row, given) if given is not EchelonOrder.STANDING else EchelonOrder.STANDING})
    brigades = [row for row in rows if row.level is L.BRIGADE]
    ordered = sum(1 for row in brigades if row.order is not EchelonOrder.STANDING)
    standing = len(brigades) - ordered
    tally.ordered += ordered
    tally.standing += standing
    await apply_orders(ctx, army_id, profile, brigades)
    return CommandReport(order, ordered, standing)


def spend(rules: Rules, above: EchelonRow, row: EchelonRow, order: EchelonOrder) -> EchelonOrder:
    if "order" in row.locked:
        return row.order
    cost = cost_of(rules, order)
    if not row.in_range or above.points_spent + cost > above.command_points:
        return EchelonOrder.STANDING
    if "points_spent" not in above.locked:
        above.points_spent += cost
    return order


async def apply_orders(ctx: TickContext, army_id: int, profile: ArmyProfileRow, brigades: list[EchelonRow]) -> None:
    table = ctx.rules.order_of_battle
    orders = {row.id: row.order for row in brigades}
    for stack in await stacks_of(ctx.session, army_id):
        order = orders.get(stack.echelon_id or -1)
        if order is None or "organisation" in stack.locked:
            continue
        if order is EchelonOrder.STANDING:
            stack.organisation = clamp_int(stack.organisation - table.standing_organisation, 0, PERCENT)
        elif order is EchelonOrder.MANOEUVRE:
            stack.organisation = clamp_int(stack.organisation + table.manoeuvre_organisation, 0, PERCENT)
    if any(order is EchelonOrder.HOLD for order in orders.values()) and "entrenchment" not in profile.locked:
        profile.entrenchment = clamp_int(profile.entrenchment + table.hold_entrench, 0, PERCENT)


async def command_edge(ctx: TickContext, army_id: int) -> float:
    table = ctx.rules.order_of_battle
    brigades = {row.id: row.order for row in await echelons_of(ctx, army_id) if row.level is L.BRIGADE}
    stacks = [row for row in await stacks_of(ctx.session, army_id) if row.count > 0 and row.echelon_id in brigades]
    total = sum(row.count for row in stacks)
    if total <= 0:
        return 1.0
    attack = sum(row.count for row in stacks if brigades[row.echelon_id or -1] is EchelonOrder.ATTACK) / total
    standing = sum(row.count for row in stacks if brigades[row.echelon_id or -1] is EchelonOrder.STANDING) / total
    return max(0.1, 1 + attack * table.attack_edge_pct / PERCENT - standing * table.standing_edge_pct / PERCENT)
