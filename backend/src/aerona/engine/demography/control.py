from collections.abc import Mapping
from enum import StrEnum

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.demography import CohortRow, PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import AgeBand, CohortCondition, FuneralCustom, InheritanceCustom, MartialStyle, MotifSource, NaturalTrait
from aerona.domain.enums.ecology import Biochemistry, Diet, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.nature import Thermoregulation
from aerona.domain.enums.physics import AirNeed
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionForm
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.demography.bound import sync_bound_share
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, row_for, seed
from aerona.engine.demography.keys import DORMANT_KEY
from aerona.engine.demography.peoples import ensure_profiles
from aerona.engine.demography.rites import rite_tradition, set_rite
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.queries import add_flag, connect, remove_flag
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import headcount_bounds, set_stats
from aerona.engine.primitives.transfers import move_amount

FOUNDED_POWER = 2
FOUNDED_SUBTYPE = "people"

BIOLOGY_NUMBERS = {"maturity_years": (1, 1000), "adult_years": (1, 10000), "elder_years": (1, 10000), "fertility_pct": (0, 500)}
CULTURE_NUMBERS = {
    "cohesion": (0, PERCENT),
    "literacy": (0, PERCENT),
    "urbanisation": (0, PERCENT),
    "ornament": (0, PERCENT),
    "geometry": (0, PERCENT),
    "colour": (0, PERCENT),
    "scale": (0, PERCENT),
    "symmetry": (0, PERCENT),
}
BIOLOGY_CHOICES: dict[str, type[StrEnum]] = {
    "acclimatised": TemperatureBand,
    "staple": CommodityKind,
    "body_plan": BodyPlan,
    "size_class": SizeClass,
    "diet": Diet,
    "biochemistry": Biochemistry,
    "air": AirNeed,
    "thermoregulation": Thermoregulation,
}
BIOLOGY_GRAVITY = ("gravity_low", "gravity_high")
GRAVITY_HUNDREDTHS = (1, 10000)
CULTURE_CHOICES: dict[str, type[StrEnum]] = {
    "martial_style": MartialStyle,
    "inheritance": InheritanceCustom,
    "funeral_rite": FuneralCustom,
    "remains_treatment": RemainsTreatment,
}
CULTURE_FLAGS = ("slavery_lawful",)
UNION_CHOICES: dict[str, tuple[str, type[StrEnum]]] = {
    "union_form": ("form", UnionForm),
    "plural_side": ("plural_side", PluralSide),
    "endogamy": ("endogamy", PartnerScope),
}
DORMANCY_REASON = "player.dormancy"
BIOLOGY_LISTS: dict[str, type[StrEnum]] = {"traits": NaturalTrait}
CULTURE_LISTS: dict[str, type[StrEnum]] = {"staples": CommodityKind, "motif_sources": MotifSource}
CULTURE_LINKS = {"liturgical_language_id": EntityType.LANGUAGE, "trade_language_id": EntityType.LANGUAGE, "funeral_rite_id": EntityType.TRADITION}
RECORD_KEYS = {"martial_wins": 0, "martial_losses": 1}
RECORD_LOCK = "martial_record"
RECORD_MAX = 100000
IMMUNITY_KEY = "immunities"
EDITABLE = frozenset(
    {
        *BIOLOGY_NUMBERS,
        *CULTURE_NUMBERS,
        *BIOLOGY_CHOICES,
        *BIOLOGY_GRAVITY,
        *CULTURE_CHOICES,
        *CULTURE_FLAGS,
        *BIOLOGY_LISTS,
        *CULTURE_LISTS,
        *CULTURE_LINKS,
        IMMUNITY_KEY,
        RECORD_LOCK,
    }
)
Value = int | str | bool | list[int] | list[str] | None


async def people(ctx: TickContext, people_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, people_id)
    if entity is None or entity.entity_type is not EntityType.PEOPLE or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such people.")
    return entity


async def ground_of(ctx: TickContext, entity: EntityRow) -> RegionEnvironmentRow | None:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(entity.id)
    return await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None


async def profiles(ctx: TickContext, entity: EntityRow) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    return await ensure_profiles(ctx.session, ctx.rules, entity, await ground_of(ctx, entity))


def lock(row: PeopleBiologyRow | PeopleCultureRow, key: str) -> None:
    if key not in row.locked:
        row.locked = [*row.locked, key]


def label(key: str) -> str:
    return key.removesuffix("_id").replace("_", " ").capitalize()


def number(key: str, value: Value, low: int, high: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValidationFailedError(f"{label(key)} runs from {low} to {high}.")
    return value


def choice[E: StrEnum](key: str, value: Value, kind: type[E]) -> E:
    try:
        return kind(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a known {label(key).lower()}.") from error


def choices[E: StrEnum](key: str, value: Value, kind: type[E]) -> list[str]:
    if not isinstance(value, list):
        raise ValidationFailedError(f"{label(key)} takes a list.")
    return sorted({choice(key, item, kind).value for item in value})


async def linked(ctx: TickContext, key: str, value: Value, kind: EntityType) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{label(key)} takes a record.")
    found = await ctx.session.get(EntityRow, value)
    if found is None or found.entity_type is not kind:
        raise ValidationFailedError(f"{label(key)} must be {an(spoken(kind))}.")
    return found.id


async def diseases(ctx: TickContext, value: Value) -> list[int]:
    if not isinstance(value, list):
        raise ValidationFailedError("Immunities take a list of diseases.")
    found: list[int] = []
    for item in value:
        disease = await ctx.session.get(EntityRow, item) if isinstance(item, int) and not isinstance(item, bool) else None
        if disease is None or disease.entity_type is not EntityType.DISEASE:
            raise ValidationFailedError(f"{item} is not a disease.")
        found.append(disease.id)
    return sorted(set(found))


def set_record(culture: PeopleCultureRow, key: str, value: Value) -> None:
    count = number(key, value, 0, RECORD_MAX)
    record = {name: list(entry) for name, entry in (culture.martial_record or {}).items()}
    entry = [*record.get(culture.martial_style.value, []), 0, 0][:2]
    entry[RECORD_KEYS[key]] = count
    record[culture.martial_style.value] = entry
    culture.martial_record = record


def set_biology(biology: PeopleBiologyRow, key: str, value: Value) -> bool:
    if key in BIOLOGY_NUMBERS:
        setattr(biology, key, number(key, value, *BIOLOGY_NUMBERS[key]))
    elif key in BIOLOGY_CHOICES:
        setattr(biology, key, choice(key, value, BIOLOGY_CHOICES[key]))
    elif key in BIOLOGY_GRAVITY:
        setattr(biology, key, number(key, value, *GRAVITY_HUNDREDTHS) / PERCENT)
        if biology.gravity_low > biology.gravity_high:
            raise ValidationFailedError("A people cannot bear less gravity than the least it needs.")
    elif key in BIOLOGY_LISTS:
        setattr(biology, key, choices(key, value, BIOLOGY_LISTS[key]))
    else:
        return False
    lock(biology, key)
    return True


async def apply(ctx: TickContext, entity: EntityRow, rows: tuple[PeopleBiologyRow, PeopleCultureRow], key: str, value: Value) -> None:
    biology, culture = rows
    if set_biology(biology, key, value):
        return
    if key in CULTURE_NUMBERS:
        setattr(culture, key, number(key, value, *CULTURE_NUMBERS[key]))
        lock(culture, key)
    elif key == "funeral_rite":
        set_rite(culture, choice(key, value, FuneralCustom))
        await rite_tradition(ctx.session, ctx.rules, entity, culture, ctx.epoch)
        lock(culture, key)
    elif key in CULTURE_CHOICES:
        setattr(culture, key, choice(key, value, CULTURE_CHOICES[key]))
        lock(culture, key)
    elif key in CULTURE_FLAGS:
        setattr(culture, key, bool(value))
        lock(culture, key)
    elif key in CULTURE_LISTS:
        setattr(culture, key, choices(key, value, CULTURE_LISTS[key]))
        lock(culture, key)
    elif key in CULTURE_LINKS:
        setattr(culture, key, await linked(ctx, key, value, CULTURE_LINKS[key]))
        lock(culture, key)
    elif key == IMMUNITY_KEY:
        biology.immunities = await diseases(ctx, value)
        lock(biology, key)
    elif key in RECORD_KEYS:
        set_record(culture, key, value)
        lock(culture, RECORD_LOCK)
    else:
        raise ValidationFailedError(f"Unknown field: {key}.")


async def edit_people(ctx: TickContext, people_id: int, values: Mapping[str, Value], *, release: list[str]) -> tuple[PeopleBiologyRow, PeopleCultureRow]:
    entity = await people(ctx, people_id)
    rows = await profiles(ctx, entity)
    for key, value in values.items():
        await apply(ctx, entity, rows, key, value)
    biology, culture = rows
    for key in release:
        if key not in EDITABLE and key not in RECORD_KEYS:
            raise ValidationFailedError(f"Unknown field: {key}.")
        freed = RECORD_LOCK if key in RECORD_KEYS else key
        biology.locked = [item for item in biology.locked if item != freed]
        culture.locked = [item for item in culture.locked if item != freed]
    await ctx.session.flush()
    return biology, culture


async def found_people(
    ctx: TickContext, *, name: str, region_id: int, population: int, species_id: int | None, language_id: int | None, values: Mapping[str, Value]
) -> EntityRow:
    region = await ctx.session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION or region.status is not EntityStatus.CANON:
        raise NotFoundError("No such land.")
    limits = ctx.rules.limits
    if population < limits.people_population_floor:
        raise ValidationFailedError(f"A people numbers at least {limits.people_population_floor}.")
    population = min(population, limits.people_population_cap)
    species = await linked(ctx, "species", species_id, EntityType.SPECIES)
    language = await linked(ctx, "language", language_id, EntityType.LANGUAGE)
    founded = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=name,
            body=f"A people raised by the will of the Creator in {region.name}.",
            stats=PeopleStats(population=population),
            power=FOUNDED_POWER,
            location_id=region.id,
            world_id=region.world_id,
            subtype=FOUNDED_SUBTYPE,
        ),
    )
    if species is not None:
        await connect(ctx.session, founded.id, species, BondKind.DESCENDS_FROM, ctx.epoch, description="raised from this kind")
    if language is not None:
        await connect(ctx.session, founded.id, language, BondKind.SPEAKS, ctx.epoch)
    await bind_language_and_faith(ctx, founded)
    rows = await profiles(ctx, founded)
    for key, value in values.items():
        if key not in UNION_CHOICES:
            await apply(ctx, founded, rows, key, value)
    union = await ctx.session.get(UnionCustomRow, founded.id)
    for key, (column, kind) in UNION_CHOICES.items():
        if key in values and union is not None:
            setattr(union, column, choice(key, values[key], kind))
            union.locked = sorted({*union.locked, column})
    await rite_tradition(ctx.session, ctx.rules, founded, rows[1], ctx.epoch)
    await ctx.session.flush()
    return founded


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
        landed = condition if condition is not None else (CohortCondition.ENSLAVED if target is SocialClass.SERF_OR_SLAVE else state)
        if target is not SocialClass.SERF_OR_SLAVE and landed is CohortCondition.ENSLAVED:
            landed = CohortCondition.NONE
        destination = (age, sex, target, landed)
        if move_amount(rows[key], row_for(ctx.session, rows, community.id, destination, ctx.epoch), "count", part):
            moved += part
    await resync_society(ctx, community, rows)
    await ctx.session.flush()
    return moved


async def follow_shares(ctx: TickContext, community: EntityRow, shares: Mapping[SocialClass, float]) -> int:
    rows = await cohorts_of(ctx.session, community.id)
    total = sum(row.count for row in rows.values())
    if total <= 0 or held(community.id):
        return 0
    have = {item: sum(row.count for key, row in rows.items() if key[2] is item) for item in SocialClass}
    want = {item: int(total * shares.get(item, 0.0) / PERCENT) for item in SocialClass}
    free = [item for item in SocialClass if item is not SocialClass.SERF_OR_SLAVE]
    needs = {item: want[item] - have[item] for item in free if want[item] > have[item]}
    moved = 0
    for source in free:
        extra = have[source] - want[source]
        for target in sorted(needs):
            if extra <= 0:
                break
            count = min(extra, needs[target])
            if count <= 0:
                continue
            done = shift_class(ctx, community.id, rows, source=source, target=target, count=count)
            extra -= done
            needs[target] -= done
            moved += done
    if moved:
        await resync_society(ctx, community, rows)
    return moved


def shift_class(ctx: TickContext, community_id: int, rows: dict[CohortKey, CohortRow], *, source: SocialClass, target: SocialClass, count: int) -> int:
    moved = 0
    for key in sorted(rows, key=lambda item: (-rows[item].count, tuple(part.value for part in item))):
        if moved >= count:
            break
        age, sex, social_class, state = key
        if social_class is not source or rows[key].count <= 0 or state is CohortCondition.ENSLAVED:
            continue
        part = min(rows[key].count, count - moved)
        if move_amount(rows[key], row_for(ctx.session, rows, community_id, (age, sex, target, state), ctx.epoch), "count", part):
            moved += part
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
        raise ValidationFailedError(f"The community would hold {several(total, 'person', 'people')}; it must hold between {floor} and {ceiling}.")
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
