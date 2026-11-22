from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.ecology import OPEN
from aerona.constants.units import PERCENT
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import HELD, fall, towns_near
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.mythic.ballads import sing_of_slaying
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import RoleValue, StepDraft, record

MIDDLING = 50


@dataclass
class ContractTally:
    posted: int = 0
    taken: int = 0
    slain: int = 0
    failed: int = 0
    withdrawn: int = 0


async def open_contract(ctx: TickContext, beast_id: int) -> MonsterContractRow | None:
    return await ctx.session.scalar(
        select(MonsterContractRow).where(MonsterContractRow.beast_entity_id == beast_id, MonsterContractRow.status.in_(list(OPEN))).limit(1)
    )


async def post_contracts(ctx: TickContext, tally: ContractTally) -> None:
    table = ctx.rules.monster_contracts
    atlas = await RegionAtlas.load(ctx.session)
    made = select(ConstructRow.entity_id)
    beasts = await ctx.session.execute(
        select(EntityRow, BeastProfileRow)
        .join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, BeastProfileRow.raids >= table.post_raids, EntityRow.id.not_in(made))
        .order_by(EntityRow.id)
    )
    for beast, row in list(beasts):
        if row.temper in HELD or held(beast.id) or await open_contract(ctx, beast.id) is not None:
            continue
        near = [town for town in await towns_near(ctx, atlas, row) if not held(town.id)]
        if not near:
            continue
        town = max(near, key=lambda item: (stat_or(item, "population", 0), -item.id))
        ctx.session.add(MonsterContractRow(community_entity_id=town.id, beast_entity_id=beast.id, bounty=table.bounty, posted_epoch=ctx.epoch, locked=[]))
        tally.posted += 1
        roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: town.id, IncidentRole.TARGET: beast.id}
        await record(ctx, "contract.posted", roles=roles, facts={"bounty": table.bounty, "raids": row.raids}, place=town.id)
    await ctx.session.flush()


async def busy_hunters(ctx: TickContext) -> set[int]:
    rows = await ctx.session.scalars(
        select(MonsterContractRow.hunter_entity_id).where(MonsterContractRow.status == ContractStatus.TAKEN, MonsterContractRow.hunter_entity_id.is_not(None))
    )
    return {int(item) for item in rows if item is not None}


async def hunter_for(ctx: TickContext, beast: EntityRow, busy: set[int]) -> EntityRow | None:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == beast.world_id,
            SkillRow.skill == SkillKind.HUNTING,
            SkillRow.subject_node_id.is_(None),
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
    )
    return next((row for row in rows if row.id not in busy and not held(row.id)), None)


async def take_contracts(ctx: TickContext, tally: ContractTally) -> None:
    table = ctx.rules.monster_contracts
    busy = await busy_hunters(ctx)
    for row in list(
        await ctx.session.scalars(select(MonsterContractRow).where(MonsterContractRow.status == ContractStatus.POSTED).order_by(MonsterContractRow.id))
    ):
        beast = await living_entity(ctx.session, row.beast_entity_id)
        if beast is None or "status" in row.locked or not ctx.rng(f"contract.take.{row.id}.{ctx.epoch}").chance(table.take_chance):
            continue
        hunter = await hunter_for(ctx, beast, busy)
        if hunter is None:
            continue
        row.hunter_entity_id, row.status = hunter.id, ContractStatus.TAKEN
        busy.add(hunter.id)
        tally.taken += 1
        roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: hunter.id, IncidentRole.TARGET: beast.id, IncidentRole.GIVER: row.community_entity_id}
        await record(ctx, "contract.taken", roles=roles, facts={"bounty": row.bounty})


def hunt_chance(ctx: TickContext, row: MonsterContractRow, hunter: EntityRow, beast: EntityRow) -> int:
    table = ctx.rules.monster_contracts
    edge = row.study / 2 + stat_or(hunter, "strength", MIDDLING) / 4 - stat_or(beast, "danger", MIDDLING) / 2
    return clamp_int(table.hunt_base + edge, 0, PERCENT)


async def settle(ctx: TickContext, row: MonsterContractRow, status: ContractStatus) -> None:
    row.status, row.closed_epoch = status, ctx.epoch


async def slay(ctx: TickContext, row: MonsterContractRow, hunter: EntityRow, beast: EntityRow) -> None:
    table = ctx.rules.monster_contracts
    await connect(ctx.session, hunter.id, beast.id, BondKind.KILLED, ctx.epoch, description="slew it for a bounty")
    await retire_in(ctx, beast, f"slain by {hunter.name} for a bounty")
    beast_row = await ctx.session.get(BeastProfileRow, beast.id)
    if beast_row is not None:
        await fall(ctx, beast, beast_row)
    town = await living_entity(ctx.session, row.community_entity_id)
    if town is not None and not held(town.id) and await take_coin(ctx.session, ctx.rules, town, row.bounty):
        await give_coin(ctx.session, ctx.rules, hunter, row.bounty)
    profile = await ctx.session.get(MortalProfileRow, hunter.id)
    if profile is not None and "renown" not in profile.locked:
        profile.renown = clamp_int(profile.renown + table.renown, 0, PERCENT)
    await settle(ctx, row, ContractStatus.SLAIN)
    await sing_of_slaying(ctx, hunter, beast, "hunting for a bounty")
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.ACTOR: hunter.id,
        IncidentRole.VICTIM: beast.id,
        IncidentRole.GIVER: town.id if town is not None else None,
    }
    steps = (StepDraft(StepAction.FINISH, actor=hunter.id, target=beast.id, outcome=StepOutcome.KILLED),)
    await record(ctx, "contract.slain", roles=roles, facts={"bounty": row.bounty, "renown": table.renown, "study": row.study}, steps=steps)


async def hunt(ctx: TickContext, row: MonsterContractRow, hunter: EntityRow, beast: EntityRow, tally: ContractTally) -> None:
    table = ctx.rules.monster_contracts
    if "study" not in row.locked:
        row.study = clamp_int(row.study + round_half_up(table.study_step * stat_or(hunter, "intellect", MIDDLING) / PERCENT * 2), 0, PERCENT)
    if ctx.rng(f"contract.hunt.{row.id}.{ctx.epoch}").chance(hunt_chance(ctx, row, hunter, beast)):
        await slay(ctx, row, hunter, beast)
        tally.slain += 1
        return
    hp = stat_or(hunter, "hp", 0)
    set_stats(hunter, hp=max(1, hp - table.wound))
    if hp - table.wound <= 1:
        await settle(ctx, row, ContractStatus.FAILED)
        tally.failed += 1
        roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: hunter.id, IncidentRole.TARGET: beast.id}
        await record(ctx, "contract.failed", roles=roles, facts={"wound": table.wound, "study": row.study, "bounty": row.bounty})


async def keep_hunts(ctx: TickContext, tally: ContractTally) -> None:
    for row in list(await ctx.session.scalars(select(MonsterContractRow).where(MonsterContractRow.status.in_(list(OPEN))).order_by(MonsterContractRow.id))):
        if "status" in row.locked:
            continue
        beast = await living_entity(ctx.session, row.beast_entity_id)
        beast_row = await ctx.session.get(BeastProfileRow, row.beast_entity_id)
        if beast is None or beast_row is None or beast_row.temper in HELD:
            await settle(ctx, row, ContractStatus.WITHDRAWN)
            tally.withdrawn += 1
            continue
        if row.status is not ContractStatus.TAKEN or held(beast.id):
            continue
        hunter = await living_entity(ctx.session, row.hunter_entity_id)
        if hunter is None:
            row.hunter_entity_id, row.status = None, ContractStatus.POSTED
            continue
        if not held(hunter.id):
            await hunt(ctx, row, hunter, beast, tally)


async def keep_contracts(ctx: TickContext, tally: ContractTally) -> None:
    await post_contracts(ctx, tally)
    await take_contracts(ctx, tally)
    await keep_hunts(ctx, tally)
    await ctx.session.flush()
