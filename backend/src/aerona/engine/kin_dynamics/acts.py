from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import KinDisowningRow, KinDynamicRow, KinFavourRow, KinRivalryRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.domain.enums.kin_dynamics import DisownReason, RivalryCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.kin_dynamics.book import KinTally, rivalry_between
from aerona.engine.polity.houses import HouseBook, found_house
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

DR = DisownReason
GRUDGE = total(DisownReason, {DR.DISOBEDIENCE: 20, DR.MARRIAGE: 25, DR.FAITH: 30, DR.CRIME: 40, DR.RIVALRY: 30})
FINAL = frozenset({DisownReason.CRIME})


async def favour(ctx: TickContext, dynamic: KinDynamicRow, parent: int, child: int, tally: KinTally, *, strength: int = 50) -> KinFavourRow:
    query = select(KinFavourRow).where(KinFavourRow.parent_node_id == parent, KinFavourRow.child_node_id == child)
    row = await ctx.session.scalar(query.limit(1))
    if row is None:
        row = KinFavourRow(dynamic_id=dynamic.id, parent_node_id=parent, child_node_id=child, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "strength" not in (row.locked or []):
        row.strength = clamp_int(max(row.strength or 0, strength), 0, PERCENT)
    await ctx.session.flush()
    tally.favoured += 1
    await record(ctx, "kin.favoured", roles={IncidentRole.ACTOR: parent, IncidentRole.TARGET: child}, facts={"strength": row.strength})
    return row


async def rival(ctx: TickContext, dynamic: KinDynamicRow, first: int, second: int, cause: RivalryCause, *, tally: KinTally) -> KinRivalryRow:
    found = await rivalry_between(ctx.session, first, second)
    if found is not None:
        return found
    pair = sorted((first, second))
    row = KinRivalryRow(dynamic_id=dynamic.id, first_node_id=pair[0], second_node_id=pair[1], cause=cause, since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    tally.rivalries += 1
    await record(ctx, "kin.rivalry_began", roles={IncidentRole.ACTOR: pair[0], IncidentRole.TARGET: pair[1]}, facts={"cause": cause})
    return row


async def disown(ctx: TickContext, dynamic: KinDynamicRow, parent: int, member: EntityRow, reason: DisownReason, *, tally: KinTally) -> KinDisowningRow:
    row = KinDisowningRow(dynamic_id=dynamic.id, disowner_node_id=parent, disowned_node_id=member.id, reason=reason, epoch=ctx.epoch, locked=[])
    row.reversible = reason not in FINAL
    ctx.session.add(row)
    if dynamic.house_entity_id is not None:
        kept = await ctx.session.get(HouseMemberRow, (dynamic.house_entity_id, member.id))
        if kept is not None:
            await ctx.session.delete(kept)
    await change_relation(ctx, member.id, parent, -GRUDGE[reason], MemoryKind.BETRAYED_ME, note="cast out of the family")
    await ctx.session.flush()
    tally.disowned += 1
    await record(ctx, "kin.disowned", roles={IncidentRole.ACTOR: parent, IncidentRole.TARGET: member.id}, facts={"reason": reason})
    if ctx.rng(f"kin.line.{row.id}").chance(ctx.rules.kin_dynamics.line_chance_pct):
        await found_house(ctx, await HouseBook.load(ctx), member)
    return row


async def reconcile(ctx: TickContext, row: KinDisowningRow, tally: KinTally) -> bool:
    if not row.reversible or row.reconciled_epoch is not None or "reconciled_epoch" in (row.locked or []):
        return False
    row.reconciled_epoch = ctx.epoch
    dynamic = await ctx.session.get(KinDynamicRow, row.dynamic_id)
    member = await living_entity(ctx.session, row.disowned_node_id)
    house = dynamic.house_entity_id if dynamic is not None else None
    if house is not None and member is not None and await ctx.session.get(HouseMemberRow, (house, member.id)) is None:
        ctx.session.add(HouseMemberRow(house_entity_id=house, mortal_entity_id=member.id, joined_epoch=ctx.epoch))
    tally.reconciled += 1
    await record(
        ctx, "kin.reconciled", roles={IncidentRole.ACTOR: row.disowner_node_id, IncidentRole.TARGET: row.disowned_node_id}, facts={"reason": row.reason}
    )
    return True


async def split_house(ctx: TickContext, dynamic: KinDynamicRow, row: KinRivalryRow, leaver: EntityRow, tally: KinTally) -> EntityRow | None:
    if dynamic.house_entity_id is None:
        return None
    book = await HouseBook.load(ctx)
    profile = book.profiles.get(dynamic.house_entity_id)
    if profile is None or "branches" in (profile.locked or []):
        return None
    cadet = await found_house(ctx, book, leaver, parent=dynamic.house_entity_id, polity_id=profile.polity_entity_id)
    kept = await ctx.session.get(HouseMemberRow, (dynamic.house_entity_id, leaver.id))
    if kept is not None:
        await ctx.session.delete(kept)
    row.ended_epoch = ctx.epoch
    tally.splits += 1
    await record(
        ctx,
        "kin.house_split",
        roles={IncidentRole.ACTOR: leaver.id, IncidentRole.SUBJECT: dynamic.house_entity_id, IncidentRole.SUCCESSOR: cadet.id},
        facts={"cause": row.cause},
    )
    return cadet
