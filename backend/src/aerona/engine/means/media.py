from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.art_modes import WRITTEN_MODES
from aerona.catalog.lore import KNOWLEDGE_ITEMS
from aerona.catalog.means import CASUAL_MEDIA, MEDIA
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ArtworkProfileRow, BookContentRow, ItemProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.means import WritingCustomRow, WrittenWorkRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.means import WritingMedium
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_techniques
from aerona.engine.lore.printing import printed
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import retire_in


@dataclass
class MediaTally:
    customs: int = 0
    works: int = 0
    worn: int = 0
    lost: int = 0
    copied: int = 0
    burned: int = 0


async def medium_for(ctx: TickContext, people: EntityRow) -> WritingMedium:
    if await branch_level(ctx.session, people.id, KnowledgeBranch.WRITING) <= 0:
        return WritingMedium.KNOTTED_CORD
    if Technique.PAPER in await era_techniques(ctx.session, people.id):
        return WritingMedium.PAPER
    towns = await towns_of_people(ctx.session, people.id)
    herds = await ctx.session.scalar(
        select(CommunityStockRow.quantity)
        .where(CommunityStockRow.community_entity_id.in_(towns), CommunityStockRow.commodity == CommodityKind.LIVESTOCK, CommunityStockRow.quantity > 0)
        .limit(1)
    )
    if herds is not None:
        return WritingMedium.PARCHMENT
    return ctx.rng(seed_of("writing.medium", people.id)).pick(list(CASUAL_MEDIA))


async def seed_customs(ctx: TickContext, tally: MediaTally) -> None:
    known = set(await ctx.session.scalars(select(WritingCustomRow.people_entity_id)))
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if people.id in known or held(people.id):
            continue
        ctx.session.add(WritingCustomRow(people_entity_id=people.id, medium=await medium_for(ctx, people), since_epoch=ctx.epoch, locked=[]))
        tally.customs += 1
    await ctx.session.flush()


WRITTEN_ARTS = WRITTEN_MODES


async def writer_of(ctx: TickContext, work: EntityRow) -> EntityRow:
    art = await ctx.session.get(ArtworkProfileRow, work.id)
    author = await ctx.session.get(EntityRow, art.author_entity_id) if art is not None and art.author_entity_id is not None else None
    return author or work


async def custom_of(ctx: TickContext, work: EntityRow) -> WritingMedium:
    work = await writer_of(ctx, work)
    folk = await people_of(ctx.session, work)
    if folk is None and work.location_id is not None:
        place = await ctx.session.get(EntityRow, work.location_id)
        folk = await people_of(ctx.session, place) if place is not None else None
    row = await ctx.session.get(WritingCustomRow, folk.id) if folk is not None else None
    return row.medium if row is not None else WritingMedium.KNOTTED_CORD


async def register_works(ctx: TickContext, tally: MediaTally) -> None:
    known = set(await ctx.session.scalars(select(WrittenWorkRow.work_entity_id)))
    sources = (
        select(BookContentRow.book_entity_id),
        select(ArtworkProfileRow.artwork_entity_id).where(ArtworkProfileRow.medium.in_(list(WRITTEN_ARTS))),
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_class.in_(list(KNOWLEDGE_ITEMS))),
    )
    found = {work_id for source in sources for work_id in await ctx.session.scalars(source)}
    for work_id in sorted(found - known):
        work = await ctx.session.get(EntityRow, work_id)
        if work is None or work.status is not EntityStatus.CANON or held(work.id):
            continue
        ctx.session.add(WrittenWorkRow(work_entity_id=work.id, medium=await custom_of(ctx, work), written_epoch=ctx.epoch, locked=[]))
        tally.works += 1
    await ctx.session.flush()


async def damp_of(ctx: TickContext, atlas: RegionAtlas, work: EntityRow) -> int:
    region = atlas.top_region(work.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    return ground.moisture if ground is not None else PERCENT // 2


async def wear_works(ctx: TickContext, tally: MediaTally) -> None:
    table = ctx.rules.writing_media
    atlas = await RegionAtlas.load(ctx.session)
    for row in list(await ctx.session.scalars(select(WrittenWorkRow).order_by(WrittenWorkRow.work_entity_id))):
        work = await ctx.session.get(EntityRow, row.work_entity_id)
        if work is None or work.status is not EntityStatus.CANON or held(work.id):
            continue
        spec = MEDIA[row.medium]
        if spec.copies and "copies" not in row.locked:
            scale = table.printing_pct / PERCENT if await printed(ctx.session, work.location_id or work.id) else 1
            row.copies += round_half_up(table.copy_gain * spec.copies * scale)
            tally.copied += 1
        if "condition" not in row.locked:
            shield = max(0.0, 1 - (row.copies - 1) * table.copy_shield_pct / PERCENT)
            rot = round_half_up(spec.rot * await damp_of(ctx, atlas, work) / PERCENT * table.rot_pct / PERCENT * shield)
            row.condition = clamp_int(row.condition - rot, 0, PERCENT)
            tally.worn += rot > 0
        if row.condition <= 0:
            await retire_in(ctx, work, f"its {spec.label.lower()} crumbled away", EntityStatus.DESTROYED)
            tally.lost += 1
            await note(ctx, f"{work.name} crumbled away with its {spec.label.lower()}.", key="writing.lost", ids=[work.id])
    await ctx.session.flush()


async def burn_works(ctx: TickContext, town: EntityRow) -> int:
    table = ctx.rules.writing_media
    burned = 0
    kept = select(EntityRow.id).where(EntityRow.location_id == town.id)
    for row in list(await ctx.session.scalars(select(WrittenWorkRow).where(WrittenWorkRow.work_entity_id.in_(kept)))):
        if held(row.work_entity_id) or "condition" in row.locked:
            continue
        spec = MEDIA[row.medium]
        shift = table.clay_baking if spec.bakes else -table.fire_loss if spec.burns else 0
        row.condition = clamp_int(row.condition + shift, 0, PERCENT)
        burned += shift < 0
    return burned


async def legible(ctx: TickContext, work_id: int) -> float:
    row = await ctx.session.get(WrittenWorkRow, work_id)
    condition = row.condition if row is not None else PERCENT
    return 1 - (PERCENT - condition) * ctx.rules.writing_media.reading_pct / PERCENT / PERCENT


async def keep_media(ctx: TickContext, tally: MediaTally) -> None:
    await seed_customs(ctx, tally)
    await register_works(ctx, tally)
    await wear_works(ctx, tally)
