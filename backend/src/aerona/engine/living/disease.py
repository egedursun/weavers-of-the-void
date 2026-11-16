from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.disease import DiseaseCureRow, DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import CureSource, OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.living import CultivationMethod, LineTrait
from aerona.engine.context import TickContext
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.living.lines import LineDraft, make_line
from aerona.engine.living.traits import traits_of
from aerona.engine.notes import note
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.primitives.distance import RegionAtlas


async def design_disease(ctx: TickContext, maker: EntityRow, name: str, *, target_id: int | None, lethality: int, virulence: int) -> EntityRow:
    region = (await RegionAtlas.load(ctx.session)).top_region(maker.id)
    if region is None:
        raise ValidationFailedError("A disease needs a land to be made in.")
    line = await make_line(ctx, LineDraft(f"the strain behind {name}", CultivationMethod.ENGINEERING, maker.id, maker.id, (), ()))
    disease = await create_disease(ctx, region, DiseaseDesign(name, {"lethality": lethality, "virulence": virulence}, hold=False), son_id=None)
    profile = await ctx.session.get(DiseaseProfileRow, disease.id)
    if profile is not None:
        profile.designed_line_id, profile.target_node_id = line.id, target_id
    await note(ctx, f"{maker.name} made a disease by design: {disease.name}.", key="living.disease_designed", ids=[maker.id, disease.id])
    return disease


async def design_cure(ctx: TickContext, maker: EntityRow, disease_id: int, line_id: int) -> DiseaseCureRow:
    if maker.location_id is None:
        raise ValidationFailedError("A cure needs a town to be given in.")
    potency = (await traits_of(ctx.session, line_id)).get(LineTrait.POTENCY, 0)
    if potency < ctx.rules.designed_disease.cure_potency_floor:
        raise ValidationFailedError("The line is not potent enough to yield a cure.")
    found = await ctx.session.get(DiseaseCureRow, (disease_id, maker.location_id))
    if found is not None:
        raise ValidationFailedError("The town already holds a cure for it.")
    row = DiseaseCureRow(disease_entity_id=disease_id, community_entity_id=maker.location_id, source=CureSource.CULTURED, since_epoch=ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"{maker.name} cultured a cure.", key="living.cure_cultured", ids=[maker.id, disease_id])
    return row


async def loose_designed(ctx: TickContext) -> int:
    table = ctx.rules.designed_disease
    loosed = 0
    active = select(OutbreakRow.disease_entity_id).where(OutbreakRow.status == OutbreakStatus.ACTIVE)
    rows = await ctx.session.scalars(
        select(DiseaseProfileRow).where(DiseaseProfileRow.designed_line_id.is_not(None), DiseaseProfileRow.disease_entity_id.not_in(active))
    )
    for profile in list(rows):
        disease = await ctx.session.get(EntityRow, profile.disease_entity_id)
        line = await ctx.session.get(LivingLineRow, profile.designed_line_id)
        maker = await ctx.session.get(EntityRow, line.maker_node_id) if line is not None and line.maker_node_id is not None else None
        if disease is None or disease.status is not EntityStatus.CANON or maker is None or held(disease.id) or held(maker.id):
            continue
        if not ctx.rng(f"living.loose.{disease.id}.{ctx.epoch}").chance(table.escape_chance):
            continue
        await strike_plague(ctx, maker, table.escape_severity, disease=disease, path=SpreadPath.LOOSED)
        await note(ctx, f"{disease.name} got loose among the ones who made it.", key="living.disease_loosed", ids=[maker.id, disease.id])
        loosed += 1
    return loosed
