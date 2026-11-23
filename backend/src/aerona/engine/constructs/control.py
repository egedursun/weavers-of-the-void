from sqlalchemy import select

from aerona.catalog.life.constructs import ASSIGN_HUNTER_CONTRACT_STATUSS
from aerona.catalog.orders import TIMED_CONDITIONS
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.constructs import (
    CONSTRUCT_FIELDS,
    ORDER_FIELDS,
    REMADE_FIELDS,
    SET_FIELDS,
    ConstructRow,
    InstructionOrderRow,
    InstructionSetRow,
    RemadeRow,
)
from aerona.db.tables.contracts import CONTRACT_FIELDS, MonsterContractRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.sacred import SIGN_FIELDS, BirthSignRow
from aerona.domain.enums.constructs import CommandToken, ConstructEnd, ContractStatus, MindWill, OrderCondition, OrderKind, OrderTime
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import BindingKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import WillCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.collective.control import of_type, saved
from aerona.engine.constructs.making import Design, make_construct
from aerona.engine.constructs.orders import holder_of, unmake
from aerona.engine.constructs.remaking import remake
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.ecology.contracts import open_contract
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.minds.phase import change_will
from aerona.engine.minds.profiles import profile_of
from aerona.engine.recording.record import record
from aerona.engine.sacred.astrology import SignTally, sign_birth

MORTALS = frozenset({EntityType.MORTAL})
BEASTS = frozenset({EntityType.BEAST})
TOWNS = frozenset({EntityType.SETTLEMENT})
SPIRITS = frozenset({EntityType.SPIRIT})
OWNERS = frozenset({EntityType.BEAST, EntityType.ARMY})


async def build_construct(
    ctx: TickContext, maker_id: int, *, material: MaterialKind | None, source: MagicSource | None, token: CommandToken | None, name: str | None
) -> ConstructRow:
    maker = await of_type(ctx, maker_id, MORTALS, "a mortal maker")
    return await make_construct(ctx, maker, Design(material=material, source=source, token=token, name=name))


async def ensoul(ctx: TickContext, construct_id: int, spirit_id: int | None) -> ConstructRow:
    row = await found(ctx, ConstructRow, construct_id, "construct")
    if row.soul_entity_id is not None:
        old = await ctx.session.get(SpiritProfileRow, row.soul_entity_id)
        if old is not None and old.bound_entity_id == construct_id:
            old.binding, old.bound_entity_id = BindingKind.NONE, None
    if spirit_id is not None:
        await of_type(ctx, spirit_id, SPIRITS, "a spirit")
        profile = await found(ctx, SpiritProfileRow, spirit_id, "spirit")
        profile.binding, profile.bound_entity_id = BindingKind.BEAST, construct_id
    apply(row, {"soul_entity_id": spirit_id}, [])
    await ctx.session.flush()
    return row


async def unmake_construct(ctx: TickContext, construct_id: int) -> None:
    await found(ctx, ConstructRow, construct_id, "construct")
    construct = await of_type(ctx, construct_id, BEASTS, "a construct")
    await unmake(ctx, construct, ConstructEnd.UNMADE_BY_GODS)
    await ctx.session.flush()


async def write_rules(ctx: TickContext, owner_id: int, token: CommandToken, token_id: int | None, holder_id: int | None) -> InstructionSetRow:
    await of_type(ctx, owner_id, OWNERS, "a construct or an army")
    if token_id is not None:
        await node_exists(ctx, token_id, "token")
    if holder_id is not None:
        await node_exists(ctx, holder_id, "holder")
    return await saved(ctx, InstructionSetRow(owner_entity_id=owner_id, command_token=token, token_entity_id=token_id, holder_node_id=holder_id, locked=[]))


async def refresh_holder(ctx: TickContext, set_id: int) -> InstructionSetRow:
    row = await found(ctx, InstructionSetRow, set_id, "instruction set")
    row.holder_node_id = await holder_of(ctx, row)
    beast = await ctx.session.get(BeastProfileRow, row.owner_entity_id)
    if beast is not None and row.holder_node_id is not None and "bound_to_node_id" not in beast.locked:
        beast.bound_to_node_id = row.holder_node_id
    await ctx.session.flush()
    return row


async def give_order(
    ctx: TickContext,
    set_id: int,
    kind: OrderKind,
    *,
    target_id: int | None,
    priority: int,
    condition: OrderCondition,
    until_epoch: int | None,
    times: OrderTime | None = None,
    giver_id: int | None = None,
) -> InstructionOrderRow:
    rules = await found(ctx, InstructionSetRow, set_id, "instruction set")
    if target_id is not None:
        await node_exists(ctx, target_id, "target")
    if condition is OrderCondition.UNTIL_DATE and until_epoch is None:
        raise ValidationFailedError("An order kept until a date needs the epoch it ends.")
    if condition in TIMED_CONDITIONS and times is None:
        raise ValidationFailedError("An order kept at set times needs the times it runs.")
    row = InstructionOrderRow(
        set_id=set_id, kind=kind, target_node_id=target_id, priority=priority, condition=condition, until_epoch=until_epoch, times=times, locked=[]
    )
    saved_row = await saved(ctx, row)
    await record(
        ctx,
        "orders.given",
        roles={IncidentRole.SUBJECT: rules.owner_entity_id, IncidentRole.AUTHORITY: giver_id, IncidentRole.TARGET: target_id},
        facts={"order": kind, "condition": condition},
    )
    return saved_row


async def remake_mortal(ctx: TickContext, mortal_id: int) -> RemadeRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    if await ctx.session.get(RemadeRow, mortal.id) is not None:
        raise ValidationFailedError(f"{mortal.name} is already remade.")
    return await remake(ctx, mortal, None)


async def post_contract(ctx: TickContext, town_id: int, beast_id: int, bounty: int) -> MonsterContractRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    beast = await of_type(ctx, beast_id, BEASTS, "a beast")
    if await ctx.session.get(ConstructRow, beast.id) is not None:
        raise ValidationFailedError(f"{beast.name} is a construct; command it through its orders.")
    if await open_contract(ctx, beast.id) is not None:
        raise ValidationFailedError(f"A contract on {beast.name} is already open.")
    return await saved(ctx, MonsterContractRow(community_entity_id=town.id, beast_entity_id=beast.id, bounty=bounty, posted_epoch=ctx.epoch, locked=[]))


async def assign_hunter(ctx: TickContext, contract_id: int, hunter_id: int) -> MonsterContractRow:
    row = await found(ctx, MonsterContractRow, contract_id, "contract")
    if row.status not in ASSIGN_HUNTER_CONTRACT_STATUSS:
        raise ValidationFailedError("That contract is closed.")
    await of_type(ctx, hunter_id, MORTALS, "a mortal hunter")
    apply(row, {"hunter_entity_id": hunter_id, "status": ContractStatus.TAKEN}, [])
    await ctx.session.flush()
    return row


async def cast_sign(ctx: TickContext, mortal_id: int) -> BirthSignRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    existing = await ctx.session.get(BirthSignRow, mortal.id)
    if existing is not None:
        await ctx.session.delete(existing)
        await ctx.session.flush()
    row = await sign_birth(ctx, mortal, SignTally())
    await ctx.session.flush()
    return row


async def rules_of(ctx: TickContext, owner_id: int) -> InstructionSetRow | None:
    return await ctx.session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == owner_id).order_by(InstructionSetRow.id).limit(1))


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "construct": (ConstructRow, CONSTRUCT_FIELDS, "construct"),
    "instruction_set": (InstructionSetRow, SET_FIELDS, "instruction set"),
    "instruction_order": (InstructionOrderRow, ORDER_FIELDS, "order"),
    "remade": (RemadeRow, REMADE_FIELDS, "remade mortal"),
    "monster_contract": (MonsterContractRow, CONTRACT_FIELDS, "contract"),
    "birth_sign": (BirthSignRow, SIGN_FIELDS, "birth sign"),
}


async def set_construct_will(ctx: TickContext, construct_id: int, values: Values, release: list[str]) -> None:
    profile = await profile_of(ctx.session, ctx.rules, construct_id, ctx.epoch)
    if "will" in values:
        change_will(ctx, profile, MindWill(values["will"]), WillCause.GIFT)
        profile.locked = sorted({*profile.locked, "will"})
    if "will" in release:
        profile.locked = [item for item in profile.locked if item != "will"]


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    if kind == "construct" and ("will" in values or "will" in release):
        await set_construct_will(ctx, int(str(key)), values, release)
        values = {name: value for name, value in values.items() if name != "will"}
        release = [name for name in release if name != "will"]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
