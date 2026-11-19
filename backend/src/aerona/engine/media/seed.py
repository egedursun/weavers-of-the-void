from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.media import MediaOutletRow, RecordMediumRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.media import RecordForm
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.lore.printing import printed

SIGNAL_REACH = 60
PRINT_REACH = 30


async def medium_for(ctx: TickContext, holder_id: int, form: RecordForm, reach: int) -> RecordMediumRow:
    found = await ctx.session.scalar(
        select(RecordMediumRow).where(RecordMediumRow.holder_node_id == holder_id, RecordMediumRow.form == form).order_by(RecordMediumRow.id).limit(1)
    )
    if found is not None:
        return found
    made = RecordMediumRow(holder_node_id=holder_id, name=f"{spoken(form)} of the realm", form=form, reach=reach, locked=[])
    ctx.session.add(made)
    await ctx.session.flush()
    return made


async def seed_towers(ctx: TickContext) -> int:
    seated = set(await ctx.session.scalars(select(MediaOutletRow.seat_entity_id)))
    made = 0
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == StructureKind.BROADCAST_TOWER, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for tower, profile in list(rows):
        town = profile.host_entity_id
        if town is None or town in seated or held(tower.id) or held(town):
            continue
        owner = await realm_of(ctx.session, town) or town
        medium = await medium_for(ctx, owner, RecordForm.SIGNAL, SIGNAL_REACH)
        ctx.session.add(
            MediaOutletRow(
                owner_node_id=owner, seat_entity_id=town, medium_id=medium.id, name=tower.name, reach=SIGNAL_REACH, founded_epoch=ctx.epoch, locked=[]
            )
        )
        seated.add(town)
        made += 1
    return made


async def seed_presses(ctx: TickContext) -> int:
    holders = set(await ctx.session.scalars(select(RecordMediumRow.holder_node_id).where(RecordMediumRow.form == RecordForm.PRINTED)))
    made = 0
    for folk in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if folk.id in holders or held(folk.id) or not await printed(ctx.session, folk.id):
            continue
        ctx.session.add(RecordMediumRow(holder_node_id=folk.id, name="printed word", form=RecordForm.PRINTED, reach=PRINT_REACH, locked=[]))
        made += 1
    return made


async def seed_media(ctx: TickContext) -> int:
    made = await seed_towers(ctx) + await seed_presses(ctx)
    await ctx.session.flush()
    return made
