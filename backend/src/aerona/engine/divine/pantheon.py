from collections.abc import Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus, PantheonStructure, PantheonTie
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import domains_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat_or

STRUCTURE_TIES: Mapping[PantheonStructure, tuple[PantheonTie, PantheonTie]] = total(
    PantheonStructure,
    {
        PantheonStructure.COUNCIL: (PantheonTie.ALLY, PantheonTie.ALLY),
        PantheonStructure.FAMILY: (PantheonTie.ELDER, PantheonTie.YOUNGER),
        PantheonStructure.COURT: (PantheonTie.RULER_OF, PantheonTie.SERVANT_OF),
        PantheonStructure.RIVALS: (PantheonTie.RIVAL, PantheonTie.RIVAL),
        PantheonStructure.SINGLE_HIGH_GOD: (PantheonTie.RULER_OF, PantheonTie.SERVANT_OF),
        PantheonStructure.DUAL: (PantheonTie.PARTNER, PantheonTie.PARTNER),
        PantheonStructure.LOOSE: (PantheonTie.KIN, PantheonTie.KIN),
    },
)
TIE_WARMTH: Mapping[PantheonTie, int] = total(
    PantheonTie,
    {
        PantheonTie.ELDER: 1,
        PantheonTie.YOUNGER: 1,
        PantheonTie.PARTNER: 2,
        PantheonTie.KIN: 1,
        PantheonTie.RULER_OF: 0,
        PantheonTie.SERVANT_OF: 1,
        PantheonTie.RIVAL: -2,
        PantheonTie.ALLY: 1,
    },
)


def structure_for(gods: list[ForeignGodRow]) -> PantheonStructure:
    if len(gods) == 1:
        return PantheonStructure.SINGLE_HIGH_GOD
    if len(gods) == 2:
        return PantheonStructure.DUAL
    strongest, second = sorted((god.power for god in gods), reverse=True)[:2]
    if strongest >= second * 2:
        return PantheonStructure.COURT
    stances = [god.stance for god in gods]
    if max(stances) - min(stances) > PERCENT:
        return PantheonStructure.RIVALS
    domains = {god.domain_primary for god in gods}
    return PantheonStructure.FAMILY if len(domains) == len(gods) else PantheonStructure.COUNCIL


async def form_pantheons(ctx: TickContext) -> int:
    formed = 0
    gods = list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status != ForeignGodStatus.DEAD).order_by(ForeignGodRow.id)))
    by_world: dict[int, list[ForeignGodRow]] = {}
    for god in gods:
        by_world.setdefault(god.world_id, []).append(god)
    for world_id, members in by_world.items():
        row = await ctx.session.get(PantheonStructureRow, world_id)
        if row is None:
            row = PantheonStructureRow(world_id=world_id, since_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            formed += 1
        if "structure" not in row.locked:
            row.structure = structure_for(members)
        head = max(members, key=lambda god: (god.power, -god.id))
        if "head_node_id" not in row.locked:
            row.head_node_id = head.id
        first, rest = STRUCTURE_TIES[row.structure]
        for god in members:
            if god.id == head.id or held(god.id):
                continue
            for holder, other, tie in ((head.id, god.id, first), (god.id, head.id, rest)):
                tie_row = await ctx.session.get(PantheonTieRow, (holder, other))
                if tie_row is None:
                    ctx.session.add(PantheonTieRow(god_node_id=holder, other_node_id=other, tie=tie, since_epoch=ctx.epoch, locked=[]))
    return formed


async def warm_ties(ctx: TickContext) -> None:
    for tie in list(await ctx.session.scalars(select(PantheonTieRow))):
        god = await ctx.session.get(ForeignGodRow, tie.god_node_id)
        if god is None or held(god.id):
            continue
        god.stance = clamp_int(god.stance - TIE_WARMTH[tie.tie] * ctx.rules.pantheon_life.tie_pull, -PERCENT * 2, PERCENT * 2)


async def worshipped_by(ctx: TickContext, god_id: int) -> list[int]:
    return [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], targets=[god_id])]


async def syncretise(ctx: TickContext) -> int:
    table = ctx.rules.pantheon_life
    merged = 0
    sons = list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id)))
    for god in list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id))):
        their = set(await worshipped_by(ctx, god.id))
        for son in sons:
            if held(god.id, son.id) or not set(domains_of(god)) & set(domains_of(son)):
                continue
            for people_id in sorted(their & set(await worshipped_by(ctx, son.id))):
                people = await ctx.session.get(EntityRow, people_id)
                if people is None or people.entity_type is not EntityType.PEOPLE:
                    continue
                known = await ctx.session.scalar(
                    select(SyncretismRow.id).where(
                        SyncretismRow.foreign_god_id == god.id, SyncretismRow.son_id == son.id, SyncretismRow.people_entity_id == people_id
                    )
                )
                if known is not None or not ctx.rng(f"syncretism.{god.id}.{son.id}.{people_id}.{ctx.epoch}").chance(table.merge_pct):
                    continue
                dominant = son.id if son.faith >= god.faith else god.id
                ctx.session.add(
                    SyncretismRow(foreign_god_id=god.id, son_id=son.id, people_entity_id=people_id, dominant_node_id=dominant, since_epoch=ctx.epoch, locked=[])
                )
                await note(ctx, f"{people.name} came to hold {son.name} and {god.name} as one.", key="divine.syncretism", ids=[people_id])
                merged += 1
    return merged


async def blend(ctx: TickContext) -> None:
    for row in list(await ctx.session.scalars(select(SyncretismRow).order_by(SyncretismRow.id))):
        son, god = await ctx.session.get(SonRow, row.son_id), await ctx.session.get(ForeignGodRow, row.foreign_god_id)
        if son is None or god is None or held(son.id, god.id):
            continue
        flow = ctx.rules.pantheon_life.blend_faith
        if row.dominant_node_id == son.id and god.faith > 0:
            god.faith, son.faith = max(0, god.faith - flow), son.faith + min(flow, god.faith)
        elif row.dominant_node_id == god.id and son.faith > 0:
            son.faith, god.faith = max(0, son.faith - flow), god.faith + min(flow, son.faith)


async def fade_and_return(ctx: TickContext) -> int:
    table = ctx.rules.pantheon_life
    moved = 0
    for god in list(
        await ctx.session.scalars(
            select(ForeignGodRow).where(ForeignGodRow.status.in_([ForeignGodStatus.AWAKE, ForeignGodStatus.ASLEEP])).order_by(ForeignGodRow.id)
        )
    ):
        if held(god.id):
            continue
        faithful = await worshipped_by(ctx, god.id)
        if god.status is ForeignGodStatus.AWAKE and not faithful:
            god.faith = max(0, god.faith - table.fade)
            if god.faith == 0:
                god.status = ForeignGodStatus.ASLEEP
                await note(ctx, f"Forgotten by all, {god.name} fell asleep.", key="divine.god_forgotten", world_id=god.world_id)
                moved += 1
        elif god.status is ForeignGodStatus.ASLEEP and len(faithful) >= table.revival_faithful:
            god.status = ForeignGodStatus.AWAKE
            await note(ctx, f"Called by those who remembered, {god.name} woke again.", key="divine.god_returned", world_id=god.world_id)
            moved += 1
    return moved


async def compete(ctx: TickContext) -> int:
    table = ctx.rules.pantheon_life
    moved = 0
    gods = list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)))
    for index, first in enumerate(gods):
        for second in gods[index + 1 :]:
            if first.domain_primary is not second.domain_primary or held(first.id, second.id):
                continue
            shared = set(await worshipped_by(ctx, first.id)) & set(await worshipped_by(ctx, second.id))
            for people_id in sorted(shared):
                people = await ctx.session.get(EntityRow, people_id)
                if people is None or held(people_id):
                    continue
                winner, loser = (first, second) if first.power >= second.power else (second, first)
                if stat_or(people, "prosperity", PERCENT // 2) < table.delivered_at:
                    winner, loser = loser, winner
                if not ctx.rng(f"compete.{first.id}.{second.id}.{people_id}.{ctx.epoch}").chance(table.switch_pct):
                    continue
                bond = await ctx.session.scalar(
                    select(BondRow).where(
                        BondRow.source_node_id == people_id,
                        BondRow.target_node_id == loser.id,
                        BondRow.kind == BondKind.WORSHIPS,
                        BondRow.state == BondState.ACTIVE,
                    )
                )
                if bond is not None:
                    bond.state, bond.closed_epoch, bond.closed_reason = BondState.PAST, ctx.epoch, f"turned to {winner.name}"
                    moved += 1
    return moved


async def keep_pantheons(ctx: TickContext) -> None:
    ctx.count("pantheons_formed", await form_pantheons(ctx))
    await warm_ties(ctx)
    ctx.count("syncretisms", await syncretise(ctx))
    await blend(ctx)
    ctx.count("gods_faded_or_returned", await fade_and_return(ctx))
    ctx.count("worshippers_won", await compete(ctx))
