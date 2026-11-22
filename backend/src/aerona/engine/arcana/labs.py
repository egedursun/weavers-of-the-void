from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import LabTextRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.lore.items import profile_of
from aerona.engine.mind.book import skill_level
from aerona.engine.mortal.learning import school_level
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record

TEXT_POWER = 2


@dataclass
class StudyTally:
    learned: int = 0
    written: int = 0


async def write_lab_text(ctx: TickContext, rite: EntityRow, author: EntityRow) -> LabTextRow | None:
    if author.entity_type is not EntityType.MORTAL or held(author.id):
        return None
    table = ctx.rules.spell_grammar
    skill = await skill_level(ctx.session, author.id, SkillKind.SPELLCRAFT)
    book = await create_record(
        ctx,
        RecordSpec(
            name=f"Lab text of {rite.name}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(),
            body=f"{author.name} set down how to work {rite.name}.",
            power=TEXT_POWER,
            world_id=author.world_id,
            location_id=author.location_id,
            maker_entity_id=author.id,
        ),
    )
    await profile_of(ctx, book, ItemClass.BOOK)
    await connect(ctx.session, author.id, book.id, BondKind.OWNS, ctx.epoch, description="wrote it")
    fidelity = clamp_int(table.lab_fidelity_floor + (PERCENT - table.lab_fidelity_floor) * skill / PERCENT, 0, PERCENT)
    row = LabTextRow(book_entity_id=book.id, rite_entity_id=rite.id, author_entity_id=author.id, fidelity=fidelity, epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def readers_of(ctx: TickContext, book_id: int) -> list[EntityRow]:
    owner_id = await ctx.session.scalar(
        select(BondRow.source_node_id).where(BondRow.target_node_id == book_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).limit(1)
    )
    owner = await ctx.session.get(EntityRow, owner_id) if owner_id is not None else None
    if owner is None or owner.status is not EntityStatus.CANON:
        return []
    place = owner.location_id if owner.entity_type is EntityType.MORTAL else owner.id
    near = [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if mortal.location_id == place]
    return near


async def learn(ctx: TickContext, reader: EntityRow, text: LabTextRow) -> bool:
    table = ctx.rules.spell_grammar
    if held(reader.id) or await skill_level(ctx.session, reader.id, SkillKind.SPELLCRAFT) <= 0:
        return False
    if await school_level(ctx.session, reader.id, text.rite_entity_id) >= table.lab_skill:
        return False
    if not ctx.rng(f"lab.{text.book_entity_id}.{reader.id}.{ctx.epoch}").chance(round_half_up(table.lab_learn_pct * text.fidelity / PERCENT)):
        return False
    row = await ctx.session.scalar(
        select(SkillRow).where(SkillRow.holder_node_id == reader.id, SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id == text.rite_entity_id)
    )
    if row is None:
        ctx.session.add(
            SkillRow(
                holder_node_id=reader.id,
                skill=SkillKind.SPELLCRAFT,
                subject_node_id=text.rite_entity_id,
                level=table.lab_skill,
                peak=table.lab_skill,
                last_used_epoch=ctx.epoch,
                source=SkillSource.TEACHING,
            )
        )
    else:
        row.level = max(row.level, table.lab_skill)
        row.peak = max(row.peak, row.level)
    return True


async def study(ctx: TickContext, tally: StudyTally) -> None:
    studied = 0
    for text in list(await ctx.session.scalars(select(LabTextRow).order_by(LabTextRow.book_entity_id))):
        for reader in await readers_of(ctx, text.book_entity_id):
            if ctx.rules.spell_grammar.learners_max and studied >= ctx.rules.spell_grammar.learners_max:
                return
            studied += 1
            tally.learned += int(await learn(ctx, reader, text))
    await ctx.session.flush()


async def write_down_rites(ctx: TickContext, tally: StudyTally) -> None:
    written = select(LabTextRow.author_entity_id, LabTextRow.rite_entity_id)
    done = {(author, rite) for author, rite in (await ctx.session.execute(written)).all()}
    masters = select(SkillRow.holder_node_id, SkillRow.subject_node_id).where(
        SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id.is_not(None), SkillRow.level >= ctx.rules.spell_grammar.lab_mastery
    )
    for author_id, rite_id in (await ctx.session.execute(masters.order_by(SkillRow.holder_node_id, SkillRow.subject_node_id))).all():
        if rite_id is None or (author_id, rite_id) in done:
            continue
        author = await ctx.session.get(EntityRow, author_id)
        rite = await ctx.session.get(EntityRow, rite_id)
        if author is None or rite is None or author.status is not EntityStatus.CANON or rite.status is not EntityStatus.CANON:
            continue
        if await write_lab_text(ctx, rite, author) is not None:
            done.add((author_id, rite_id))
            tally.written += 1
