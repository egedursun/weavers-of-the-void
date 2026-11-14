from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow, InstructionSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import CommandToken, InstructionBinding
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import UnitKind
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.lore.items import profile_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.sacred.places import realm_for, ruler_of

DISPEL_SHARE = 2


@dataclass
class SealTally:
    sealed: int = 0
    stilled: int = 0


async def realm_of_army(ctx: TickContext, army_id: int) -> int | None:
    army = await ctx.session.get(ArmyRow, army_id)
    owner = await living_entity(ctx.session, army.owner_entity_id) if army is not None else None
    return await realm_for(ctx.session, owner) if owner is not None else None


async def seal_holder(ctx: TickContext, rules: InstructionSetRow) -> int | None:
    found = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == rules.token_entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    return int(found) if found is not None else None


async def forge_seal(ctx: TickContext, army: EntityRow, ruler: EntityRow) -> InstructionSetRow:
    item = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=f"Seal of {army.name}",
            body=f"The seal that commands the constructs of {army.name}.",
            stats=ItemStats(),
            power=1,
            location_id=ruler.location_id,
            world_id=ruler.world_id,
        ),
    )
    await profile_of(ctx, item, ItemClass.SEAL)
    await connect(ctx.session, ruler.id, item.id, BondKind.OWNS, ctx.epoch, description="the seal of a construct host")
    rules = InstructionSetRow(
        owner_entity_id=army.id,
        binding=InstructionBinding.SEAL,
        command_token=CommandToken.ITEM,
        token_entity_id=item.id,
        holder_node_id=ruler.id,
        kill_switch=False,
        literalness=PERCENT,
        locked=[],
    )
    ctx.session.add(rules)
    await ctx.session.flush()
    return rules


async def keep_seals(ctx: TickContext, tally: SealTally) -> None:
    stacks = await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.kind == UnitKind.CONSTRUCTS, ArmyUnitRow.count > 0).order_by(ArmyUnitRow.id))
    by_army: dict[int, list[ArmyUnitRow]] = {}
    for unit in stacks:
        by_army.setdefault(unit.army_entity_id, []).append(unit)
    for army_id, units in sorted(by_army.items()):
        army = await living_entity(ctx.session, army_id)
        if army is None or held(army.id):
            continue
        realm = await realm_of_army(ctx, army.id)
        ruler = await living_entity(ctx.session, await ruler_of(ctx.session, realm))
        rules = await ctx.session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == army.id).order_by(InstructionSetRow.id).limit(1))
        if rules is None:
            if ruler is None:
                continue
            rules = await forge_seal(ctx, army, ruler)
            tally.sealed += 1
        holder = await seal_holder(ctx, rules)
        if "holder_node_id" not in rules.locked:
            rules.holder_node_id = holder
        if ruler is not None and holder == ruler.id:
            continue
        for unit in units:
            if "organisation" not in unit.locked and unit.organisation > 0:
                unit.organisation = 0
                tally.stilled += 1
        await note(ctx, f"The constructs of {army.name} stood still without their seal.", key="construct.seal_lost", ids=[army.id])


async def unbind(ctx: TickContext, aim: EntityRow, force: int) -> str | None:
    row = await ctx.session.get(ConstructRow, aim.id)
    if row is not None and not held(aim.id) and "power" not in row.locked:
        row.power = clamp_int(row.power - force // DISPEL_SHARE, 0, PERCENT)
        return f"drained the power of {aim.name}"
    harmed = 0
    for unit in await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == aim.id, ArmyUnitRow.kind == UnitKind.CONSTRUCTS)):
        if not held(aim.id) and "condition" not in unit.locked:
            unit.condition = clamp_int(unit.condition - force // DISPEL_SHARE, 0, PERCENT)
            harmed += 1
    return f"unbound the constructs of {aim.name}" if harmed else None
