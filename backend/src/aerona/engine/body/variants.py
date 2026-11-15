from collections.abc import Iterable
from dataclasses import dataclass, fields

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.biology import (
    BIOLOGY_VARIANTS,
    CHEMISTRY_VARIANTS,
    FOLK_DIET_VARIANTS,
    PLAN_VARIANTS,
    SOCIALITY_VARIANTS,
    SPECIES_DIET_VARIANTS,
    TRAIT_VARIANTS,
)
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memo_of
from aerona.db.tables.biology import BIOLOGY_FLAGS, BIOLOGY_SHARE_MAX, BIOLOGY_SHARES, BiologyRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import DecisionBias
from aerona.domain.enums.intervention import Disaster
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up

BIOLOGY_TABLES = frozenset({BiologyRow.__tablename__})
HOLDER_TYPES = frozenset({EntityType.PEOPLE, EntityType.SPECIES})
MIDDLE = 50


@dataclass(frozen=True)
class BiologyView:
    variants: tuple[BiologyVariant, ...] = ()
    food_need_pct: int = PERCENT
    fertility_pct: int = PERCENT
    death_pct: int = PERCENT
    disease_pct: int = PERCENT
    morale_loss_pct: int = PERCENT
    fire_harm_pct: int = PERCENT
    storm_harm_pct: int = PERCENT
    breathes: bool = True
    drinks: bool = True
    ages: bool = True

    def factor(self, key: str) -> float:
        value: int = getattr(self, key)
        return value / PERCENT

    def disaster(self, disaster: Disaster) -> float:
        if disaster is Disaster.STORM:
            return self.factor("storm_harm_pct")
        if disaster is Disaster.PLAGUE:
            return self.factor("disease_pct")
        return 1.0


ORDINARY = BiologyView()


def variants_of(values: Iterable[str]) -> tuple[BiologyVariant, ...]:
    known = BiologyVariant._value2member_map_
    return tuple(sorted({BiologyVariant(value) for value in values if value in known}, key=list(BiologyVariant).index))


def derived_effects(variants: Iterable[BiologyVariant]) -> dict[str, object]:
    chosen = list(variants)
    values: dict[str, object] = {}
    for key in BIOLOGY_SHARES:
        product = 1.0
        for variant in chosen:
            product *= getattr(BIOLOGY_VARIANTS[variant], key) / PERCENT
        values[key] = clamp_int(round_half_up(product * PERCENT), 0, BIOLOGY_SHARE_MAX)
    for key in BIOLOGY_FLAGS:
        values[key] = all(getattr(BIOLOGY_VARIANTS[variant], key) for variant in chosen)
    return values


def view_from(row: BiologyRow) -> BiologyView:
    values = {item.name: getattr(row, item.name) for item in fields(BiologyView) if item.name != "variants"}
    return BiologyView(variants=variants_of(row.variants), **values)


def people_variants(biology: PeopleBiologyRow) -> list[BiologyVariant]:
    found = {PLAN_VARIANTS.get(biology.body_plan), CHEMISTRY_VARIANTS.get(biology.biochemistry), FOLK_DIET_VARIANTS.get(biology.diet)}
    found |= {TRAIT_VARIANTS.get(trait) for trait in TRAIT_VARIANTS if trait.value in biology.traits}
    return list(variants_of(variant.value for variant in found if variant is not None))


def species_variants(profile: SpeciesProfileRow) -> list[BiologyVariant]:
    found = {
        PLAN_VARIANTS.get(profile.body_plan),
        CHEMISTRY_VARIANTS.get(profile.biochemistry),
        SPECIES_DIET_VARIANTS.get(profile.diet),
        SOCIALITY_VARIANTS.get(profile.sociality),
    }
    return list(variants_of(variant.value for variant in found if variant is not None))


async def body_variants(session: AsyncSession, holder_id: int) -> list[BiologyVariant]:
    biology = await session.get(PeopleBiologyRow, holder_id)
    if biology is not None:
        return people_variants(biology)
    profile = await session.get(SpeciesProfileRow, holder_id)
    return species_variants(profile) if profile is not None else []


async def biology_views(session: AsyncSession) -> dict[int, BiologyView]:
    memo = memo_of(session, "biology_views", BIOLOGY_TABLES)
    if memo is not None and "all" in memo:
        known: dict[int, BiologyView] = memo["all"]
        return known
    found = {row.holder_entity_id: view_from(row) for row in await session.scalars(select(BiologyRow))}
    if memo is not None:
        memo["all"] = found
    return found


async def biology_of(session: AsyncSession, holder_id: int | None) -> BiologyView:
    if holder_id is None:
        return ORDINARY
    return (await biology_views(session)).get(holder_id, ORDINARY)


async def holder_of(session: AsyncSession, entity: EntityRow | None) -> EntityRow | None:
    if entity is None:
        return None
    if entity.entity_type in HOLDER_TYPES:
        return entity
    if entity.entity_type is EntityType.BEAST:
        beast = await session.get(BeastProfileRow, entity.id)
        kind = beast.species_entity_id if beast is not None else None
        return await session.get(EntityRow, kind) if kind is not None else None
    return await people_of(session, entity)


async def folk_biology(session: AsyncSession, entity: EntityRow | None) -> BiologyView:
    holder = await holder_of(session, entity)
    return await biology_of(session, holder.id if holder is not None else None)


async def seed_biology(session: AsyncSession, holder_id: int, epoch: int) -> BiologyRow:
    row = await session.get(BiologyRow, holder_id)
    if row is None:
        variants = await body_variants(session, holder_id)
        row = BiologyRow(
            holder_entity_id=holder_id, variants=[variant.value for variant in variants], updated_epoch=epoch, locked=[], **derived_effects(variants)
        )
        session.add(row)
        await session.flush()
    return row


def rederive(row: BiologyRow) -> int:
    changed = 0
    for key, value in derived_effects(variants_of(row.variants)).items():
        if key not in row.locked and getattr(row, key) != value:
            setattr(row, key, value)
            changed += 1
    return changed


async def reset_biology(session: AsyncSession, holder_id: int, epoch: int) -> BiologyRow:
    row = await seed_biology(session, holder_id, epoch)
    row.variants = [variant.value for variant in await body_variants(session, holder_id)]
    for key, value in derived_effects(variants_of(row.variants)).items():
        setattr(row, key, value)
    row.locked = []
    row.updated_epoch = epoch
    await session.flush()
    return row


@dataclass
class BiologyTally:
    seeded: int = 0
    rederived: int = 0


async def holders(session: AsyncSession) -> list[int]:
    peoples = set(await session.scalars(select(PeopleBiologyRow.people_entity_id)))
    species = set(await session.scalars(select(SpeciesProfileRow.species_entity_id)))
    return sorted(peoples | species)


async def keep_biology(ctx: TickContext, tally: BiologyTally) -> None:
    rows = {row.holder_entity_id: row for row in await ctx.session.scalars(select(BiologyRow))}
    for holder_id in await holders(ctx.session):
        if held(holder_id):
            continue
        row = rows.get(holder_id)
        if row is None:
            await seed_biology(ctx.session, holder_id, ctx.epoch)
            tally.seeded += 1
            continue
        moved = rederive(row)
        if moved:
            row.updated_epoch = ctx.epoch
            tally.rederived += moved
    await ctx.session.flush()


def bias_target(view: BiologyView, bias: DecisionBias, weight: int, bias_pct: int) -> int:
    damped = any(bias in BIOLOGY_VARIANTS[variant].damped for variant in view.variants)
    shift = sum(BIOLOGY_VARIANTS[variant].shifts.get(bias, 0) for variant in view.variants)
    base = MIDDLE if damped else weight
    return clamp_int(round_half_up(base + shift * bias_pct / PERCENT), 0, PERCENT)
