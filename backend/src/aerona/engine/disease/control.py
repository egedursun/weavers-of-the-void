from collections.abc import Mapping

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.disease import DiseaseCureRow, DiseaseProfileRow, ImmunityRow, OutbreakRow, QuarantineRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import ClimateAffinity, CureSource, DiseaseVector, OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import ensure_profile, new_disease
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.primitives.stats import set_stats

PROFILE_NUMBERS = {
    "virulence": (1, PERCENT),
    "lethality": (1, PERCENT),
    "chronic_rate": (0, PERCENT),
    "incubation": (0, 20),
    "immunity_epochs": (1, 1000),
    "mutation_rate": (0, PERCENT),
    "stigma": (0, PERCENT),
    "cure_level": (0, 20),
}
PROFILE_CHOICES = {"vector": DiseaseVector, "climate_affinity": ClimateAffinity}


async def living(ctx: TickContext, entity_id: int, types: frozenset[EntityType], label: str) -> EntityRow:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type not in types or entity.status is not EntityStatus.CANON:
        raise NotFoundError(f"No such {label}.")
    return entity


async def loose(ctx: TickContext, target_id: int, *, disease_id: int | None, severity: int, son_id: int | None) -> tuple[EntityRow, EntityRow]:
    target = await living(ctx, target_id, frozenset({EntityType.REGION, *COMMUNITY_TYPES}), "land or community")
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    if disease_id is not None:
        disease = await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    else:
        region_id = target.id if target.entity_type is EntityType.REGION else book.atlas.top_region(target.id)
        region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
        if region is None:
            raise ValidationFailedError("A disease needs a land to rise in.")
        disease = await new_disease(ctx, book, region, path=SpreadPath.LOOSED, son_id=son_id, cursed=son_id is not None)
    event, _ = await strike_plague(ctx, target, max(1, min(PERCENT, severity)), disease=disease, path=SpreadPath.LOOSED)
    return disease, event


async def edit_disease(ctx: TickContext, disease_id: int, values: Mapping[str, int | str]) -> DiseaseProfileRow:
    disease = await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    profile = await ensure_profile(ctx.session, ctx, disease)
    for key, value in values.items():
        if key in PROFILE_NUMBERS:
            low, high = PROFILE_NUMBERS[key]
            if not isinstance(value, int) or not low <= value <= high:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high}.")
            setattr(profile, key, value)
        elif key in PROFILE_CHOICES:
            try:
                setattr(profile, key, PROFILE_CHOICES[key](str(value)))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
        else:
            raise ValidationFailedError(f"Unknown disease field: {key}.")
        if key not in profile.locked:
            profile.locked = [*profile.locked, key]
    set_stats(disease, virulence=profile.virulence, lethality=profile.lethality)
    await ctx.session.flush()
    return profile


async def cure(ctx: TickContext, disease_id: int, community_id: int) -> DiseaseCureRow:
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    await living(ctx, community_id, frozenset(COMMUNITY_TYPES), "community")
    row = await ctx.session.get(DiseaseCureRow, (disease_id, community_id))
    if row is None:
        row = DiseaseCureRow(disease_entity_id=disease_id, community_entity_id=community_id, source=CureSource.GRANTED, since_epoch=ctx.epoch)
        ctx.session.add(row)
    await ctx.session.flush()
    return row


async def revoke_cure(ctx: TickContext, disease_id: int, community_id: int) -> bool:
    row = await ctx.session.get(DiseaseCureRow, (disease_id, community_id))
    if row is None:
        return False
    await ctx.session.delete(row)
    await ctx.session.flush()
    return True


async def quarantine(ctx: TickContext, region_id: int, *, epochs: int | None, son_id: int | None) -> QuarantineRow | None:
    await living(ctx, region_id, frozenset({EntityType.REGION}), "region")
    row = await ctx.session.get(QuarantineRow, region_id)
    if epochs == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    span = epochs if epochs is not None else ctx.rules.epidemiology.quarantine_epochs
    if row is None:
        row = QuarantineRow(region_entity_id=region_id, started_epoch=ctx.epoch, until_epoch=ctx.epoch + span, ordered_by_son_id=son_id)
        ctx.session.add(row)
    else:
        row.until_epoch = ctx.epoch + span
    await ctx.session.flush()
    return row


async def grant_immunity(ctx: TickContext, community_id: int, disease_id: int, immune_pct: int) -> int:
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    await living(ctx, community_id, frozenset(COMMUNITY_TYPES), "community")
    if not 0 <= immune_pct <= PERCENT:
        raise ValidationFailedError(f"Immunity runs from 0 to {PERCENT}.")
    for band in AgeBand:
        row = await ctx.session.get(ImmunityRow, (community_id, disease_id, band))
        if row is None:
            row = ImmunityRow(community_entity_id=community_id, disease_entity_id=disease_id, age_band=band, immune_pct=0, since_epoch=ctx.epoch)
            ctx.session.add(row)
        row.immune_pct = immune_pct
        row.since_epoch = ctx.epoch
    await ctx.session.flush()
    return immune_pct


async def end_outbreak(ctx: TickContext, outbreak_id: int) -> OutbreakRow:
    row = await ctx.session.get(OutbreakRow, outbreak_id)
    if row is None:
        raise NotFoundError("No such outbreak.")
    row.status = OutbreakStatus.ENDED
    row.ended_epoch = ctx.epoch
    await ctx.session.flush()
    return row
