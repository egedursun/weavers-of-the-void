from sqlalchemy import select

from aerona.catalog.discovery import DANGEROUS_TECHNIQUES, ITEM_CLASSES, ITEM_MATERIALS
from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.discovery import ArtifactStudyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import key_parts
from aerona.engine.lore.dangers import strike
from aerona.engine.lore.research import has_technique
from aerona.engine.lore.research_depth import RESEARCHERS, add_progress, field_skill
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up

SKILL_FLOOR = 10


def item_technique(item: ItemProfileRow) -> Technique | None:
    material, _ = key_parts(item.material)
    if material is not None and material in ITEM_MATERIALS:
        return ITEM_MATERIALS[material]
    return ITEM_CLASSES.get(item.item_class)


async def student_of(ctx: TickContext, owner_id: int) -> EntityRow | None:
    owner = await ctx.session.get(EntityRow, owner_id)
    if owner is None or owner.status is not EntityStatus.CANON:
        return None
    if owner.entity_type in RESEARCHERS:
        return owner
    if owner.entity_type is EntityType.MORTAL and owner.location_id is not None:
        home = await ctx.session.get(EntityRow, owner.location_id)
        return home if home is not None and home.entity_type in RESEARCHERS and home.status is EntityStatus.CANON else None
    return None


async def study(ctx: TickContext, holder: EntityRow, item: ItemProfileRow, technique: Technique) -> bool:
    table = ctx.rules.discovery
    row = await ctx.session.get(ArtifactStudyRow, (holder.id, item.item_entity_id))
    if row is None:
        row = ArtifactStudyRow(holder_entity_id=holder.id, item_entity_id=item.item_entity_id, technique=technique, progress=0, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if row.progress >= PERCENT or "progress" in row.locked:
        return False
    skill = max(SKILL_FLOOR, await field_skill(ctx.session, holder.id, TECHNIQUES[row.technique].branch))
    row.progress = clamp_int(row.progress + round_half_up(table.study_progress * skill / PERCENT), 0, PERCENT)
    row.epoch = ctx.epoch
    if row.progress < PERCENT:
        return False
    await add_progress(ctx, holder.id, row.technique, table.reverse_progress)
    item_entity = await ctx.session.get(EntityRow, item.item_entity_id)
    studied = item_entity.name if item_entity is not None else "a made thing"
    await note(
        ctx,
        f"The scholars of {holder.name} took {studied} apart and learned {TECHNIQUES[row.technique].label.lower()} from it.",
        key="discovery.reverse_engineered",
        ids=[holder.id, item.item_entity_id],
        kind=ChronicleKind.KNOWLEDGE,
    )
    danger = DANGEROUS_TECHNIQUES.get(row.technique)
    rng = ctx.rng(f"research.reverse_incident.{holder.id}.{item.item_entity_id}")
    if danger is not None and rng.chance(table.discovery_incident_pct):
        await strike(ctx, holder, rng.pick(list(danger.incidents)), technique=row.technique)
    return True


async def reverse_engineer(ctx: TickContext) -> dict[str, int]:
    items = {row.item_entity_id: row for row in await ctx.session.scalars(select(ItemProfileRow))}
    owned = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(items)))
        .order_by(BondRow.target_node_id)
    )
    studied = finished = 0
    for owner_id, item_id in owned.all():
        item = items[item_id]
        technique = item_technique(item)
        holder = await student_of(ctx, owner_id) if technique is not None else None
        if technique is None or holder is None or held(holder.id) or await has_technique(ctx.session, holder.id, technique):
            continue
        studied += 1
        finished += int(await study(ctx, holder, item, technique))
    await ctx.session.flush()
    return {"artefacts_studied": studied, "artefacts_understood": finished}
