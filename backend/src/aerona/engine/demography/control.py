from collections.abc import Mapping

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.demography import CohortRow, PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import Aesthetic, AgeBand, CohortCondition, InheritanceCustom, MarriageCustom, MartialStyle
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, row_for, seed
from aerona.engine.demography.mobility import sync_bound_share
from aerona.engine.demography.peoples import ensure_profiles
from aerona.engine.demography.promotion import DORMANT_KEY
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.queries import add_flag, remove_flag
from aerona.engine.primitives.stats import headcount_bounds, set_stats

BIOLOGY_NUMBERS = {"maturity_years": (1, 1000), "adult_years": (1, 10000), "elder_years": (1, 10000), "fertility_pct": (0, 500)}
CULTURE_NUMBERS = {"cohesion": (0, PERCENT), "literacy": (0, PERCENT), "urbanisation": (0, PERCENT)}
CULTURE_CHOICES = {"aesthetic": Aesthetic, "martial_style": MartialStyle, "marriage": MarriageCustom, "inheritance": InheritanceCustom}
CULTURE_FLAGS = ("endogamous", "slavery_lawful")
DORMANCY_REASON = "player.dormancy"


async def people(ctx: TickContext, people_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, people_id)
    if entity is None or entity.entity_type is not EntityType.PEOPLE or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such people.")
    return entity


async def profiles(ctx: TickContext, entity: EntityRow) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(entity.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    return await ensure_profiles(ctx.session, ctx.rules, entity, ground)


def lock(row: PeopleBiologyRow | PeopleCultureRow, key: str) -> None:
    if key not in row.locked:
        row.locked = [*row.locked, key]


async def edit_people(
    ctx: TickContext, people_id: int, values: Mapping[str, int | str | bool], *, release: list[str]
) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    entity = await people(ctx, people_id)
    biology, culture = await profiles(ctx, entity)
    for key, value in values.items():
        if key in BIOLOGY_NUMBERS or key in CULTURE_NUMBERS:
            low, high = BIOLOGY_NUMBERS.get(key) or CULTURE_NUMBERS[key]
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high}.")
            target: PeopleBiologyRow | PeopleCultureRow = biology if key in BIOLOGY_NUMBERS else culture
            setattr(target, key, value)
            lock(target, key)
        elif key in CULTURE_CHOICES:
            try:
                setattr(culture, key, CULTURE_CHOICES[key](str(value)))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
            lock(culture, key)
        elif key in CULTURE_FLAGS:
            setattr(culture, key, bool(value))
            lock(culture, key)
        else:
            raise ValidationFailedError(f"Unknown field: {key}.")
    for key in release:
        biology.locked = [item for item in biology.locked if item != key]
        culture.locked = [item for item in culture.locked if item != key]
    await ctx.session.flush()
    return biology, culture


async def move_cohort(
    ctx: TickContext,
    community_id: int,
    *,
    count: int,
    source: SocialClass,
    target: SocialClass,
    band: AgeBand | None,
    condition: CohortCondition | None,
    from_condition: CohortCondition | None = None,
) -> int:
    community = await ctx.session.get(EntityRow, community_id)
    if community is None or community.entity_type not in {EntityType.PEOPLE, EntityType.SETTLEMENT}:
        raise NotFoundError("No such people or settlement.")
    rows = await seed(ctx.session, ctx.rules, community, ctx.epoch) or await cohorts_of(ctx.session, community.id)
    moved = 0
    for key in sorted(rows, key=lambda item: -rows[item].count):
        if moved >= count:
            break
        age, sex, social_class, state = key
        if social_class is not source or (band is not None and age is not band) or rows[key].count <= 0:
            continue
        if from_condition is not None and state is not from_condition:
            continue
        part = min(rows[key].count, count - moved)
        rows[key].count -= part
        landed = condition if condition is not None else (CohortCondition.ENSLAVED if target is SocialClass.SERF_OR_SLAVE else state)
        if target is not SocialClass.SERF_OR_SLAVE and landed is CohortCondition.ENSLAVED:
            landed = CohortCondition.NONE
        destination = (age, sex, target, landed)
        row_for(ctx.session, rows, community.id, destination, ctx.epoch).count += part
        moved += part
    await resync_society(ctx, community, rows)
    await ctx.session.flush()
    return moved


async def resync_society(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow]) -> None:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    if society is not None:
        total = sum(row.count for row in rows.values()) or 1
        for social_class in SocialClass:
            share = sum(row.count for key, row in rows.items() if key[2] is social_class) * PERCENT / total
            setattr(society, f"share_{social_class.value}", round(share, 2))
    sync_bound_share(society, rows)


async def set_cohort(ctx: TickContext, community_id: int, key: CohortKey, count: int) -> int:
    community = await ctx.session.get(EntityRow, community_id)
    if community is None or community.entity_type not in {EntityType.PEOPLE, EntityType.SETTLEMENT} or community.status is not EntityStatus.CANON:
        raise NotFoundError("No such people or settlement.")
    if count < 0:
        raise ValidationFailedError("A cohort cannot hold fewer than nobody.")
    rows = await seed(ctx.session, ctx.rules, community, ctx.epoch) or await cohorts_of(ctx.session, community.id)
    row_for(ctx.session, rows, community.id, key, ctx.epoch).count = count
    total = sum(row.count for row in rows.values())
    floor, ceiling = headcount_bounds(ctx.rules, community)
    if not floor <= total <= ceiling:
        raise ValidationFailedError(f"The community would hold {total} people; it must hold between {floor} and {ceiling}.")
    set_stats(community, population=total)
    await resync_society(ctx, community, rows)
    await ctx.session.flush()
    return total


async def set_dormancy(ctx: TickContext, mortal_id: int, *, dormant: bool | None, hold: bool | None) -> bool:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON:
        raise NotFoundError("No such living mortal.")
    if dormant is True:
        await add_flag(ctx.session, mortal.id, EntityFlag.DORMANT, ctx.epoch)
    elif dormant is False:
        await remove_flag(ctx.session, mortal.id, EntityFlag.DORMANT)
    if hold is True:
        await ctx.session.execute(
            delete(ModifierRow).where(
                ModifierRow.target_node_id == mortal.id, ModifierRow.target_key == DORMANT_KEY, ModifierRow.source_kind == ModifierSource.PIN
            )
        )
        await add_modifier(ctx.session, ModifierDraft(mortal.id, DORMANT_KEY, ModifierOp.ADD, 0, ModifierSource.PIN, DORMANCY_REASON, start_epoch=ctx.epoch))
    elif hold is False:
        await ctx.session.execute(
            delete(ModifierRow).where(
                ModifierRow.target_node_id == mortal.id, ModifierRow.target_key == DORMANT_KEY, ModifierRow.source_kind == ModifierSource.PIN
            )
        )
    await ctx.session.flush()
    return mortal.id in await dormant_of(ctx, [mortal.id])


async def dormant_of(ctx: TickContext, ids: list[int]) -> set[int]:
    return set(await ctx.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DORMANT, EntityFlagRow.entity_id.in_(ids))))
