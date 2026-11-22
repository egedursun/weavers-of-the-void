from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.customs import CALM_MARKED_MARK_MEANINGS, EVENT_BONDS, READ_MARK_MARK_MEANINGS, READ_MARK_MARK_MEANINGS_2
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import BodyMarkRow, MarkCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import MarkKind, MarkMeaning
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.profile import is_held
from aerona.engine.mortal.standing import add_renown
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

MARKABLE = tuple(kind for kind in MarkKind if kind is not MarkKind.BRAND)


@dataclass
class MarkTally:
    seeded: int = 0
    placed: int = 0


async def customs_of(ctx: TickContext, people_id: int) -> dict[MarkMeaning, MarkKind]:
    rows = await ctx.session.scalars(select(MarkCustomRow).where(MarkCustomRow.people_entity_id == people_id).order_by(MarkCustomRow.kind))
    return {row.meaning: row.kind for row in rows}


async def seed_customs(ctx: TickContext, people: EntityRow, tally: MarkTally) -> dict[MarkMeaning, MarkKind]:
    found = await customs_of(ctx, people.id)
    if found or held(people.id):
        return found
    rng = ctx.rng(seed_of("marks", people.id))
    meanings = [meaning for meaning in MarkMeaning if meaning is not MarkMeaning.CRIME]
    for kind in rng.sample(list(MARKABLE), min(len(MARKABLE), ctx.rules.marks.customs_per_people)):
        meaning = rng.pick([item for item in meanings if item not in found] or meanings)
        ctx.session.add(MarkCustomRow(people_entity_id=people.id, kind=kind, meaning=meaning, locked=[]))
        found[meaning] = kind
    tally.seeded += 1
    return found


async def place(ctx: TickContext, mortal: EntityRow, kind: MarkKind, meaning: MarkMeaning, tally: MarkTally) -> BodyMarkRow:
    row = BodyMarkRow(holder_node_id=mortal.id, kind=kind, meaning=meaning, placed_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await read_mark(ctx, mortal, meaning)
    tally.placed += 1
    return row


async def read_mark(ctx: TickContext, mortal: EntityRow, meaning: MarkMeaning) -> None:
    table = ctx.rules.marks
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None:
        return
    if meaning in READ_MARK_MARK_MEANINGS and not is_held(profile, "renown"):
        await add_renown(ctx.session, mortal.id, table.renown_per_deed, ctx.epoch, rules=ctx.rules)
    elif meaning in READ_MARK_MARK_MEANINGS_2 and not is_held(profile, "loyalty_community"):
        profile.loyalty_community = clamp_int(profile.loyalty_community + table.belonging_per_mark, 0, PERCENT)
    elif meaning is MarkMeaning.CRIME and not is_held(profile, "honour"):
        profile.honour = clamp_int(profile.honour - table.shame_per_brand, 0, PERCENT)


async def happened(ctx: TickContext, mortal: EntityRow, meaning: MarkMeaning) -> bool:
    bond = EVENT_BONDS.get(meaning)
    if bond is not None:
        query = select(BondRow.id).where(BondRow.source_node_id == mortal.id, BondRow.kind == bond, BondRow.epoch == ctx.epoch)
        return await ctx.session.scalar(query.limit(1)) is not None
    if meaning is MarkMeaning.CLAN:
        return mortal.birth_epoch == ctx.epoch
    if meaning is MarkMeaning.MOURNING:
        kin = await close_kin_of(ctx.session, mortal.id)
        dead = select(EntityRow.id).where(EntityRow.id.in_(kin), EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch)
        return bool(kin) and await ctx.session.scalar(dead.limit(1)) is not None
    if meaning is MarkMeaning.PROTECTION:
        return mortal.birth_epoch == ctx.epoch
    return False


async def calm_marked(ctx: TickContext) -> None:
    table = ctx.rules.marks
    calming = CALM_MARKED_MARK_MEANINGS
    for holder in sorted(set(await ctx.session.scalars(select(BodyMarkRow.holder_node_id).where(BodyMarkRow.meaning.in_(calming))))):
        profile = await ctx.session.get(MortalProfileRow, holder)
        if profile is not None and not held(holder) and not is_held(profile, "stress"):
            profile.stress = clamp_int(profile.stress - table.calm_per_charm, 0, PERCENT)


async def keep_marks(ctx: TickContext, tally: MarkTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        customs = await seed_customs(ctx, people, tally)
        if not customs:
            continue
        here = await present_among(ctx.session, [people.id])
        for mortal in list(
            await ctx.session.scalars(
                select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        ):
            if held(mortal.id) or (await people_of(ctx.session, mortal) or people).id != people.id:
                continue
            for meaning, kind in sorted(customs.items(), key=lambda item: item[0].value):
                if meaning is not MarkMeaning.AGE_SET and await happened(ctx, mortal, meaning):
                    await place(ctx, mortal, kind, meaning, tally)
    await calm_marked(ctx)
    await ctx.session.flush()
