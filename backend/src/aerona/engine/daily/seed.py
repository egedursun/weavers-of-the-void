from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.customs import SEEDED_STAGES
from aerona.catalog.life_traits import HOUSE_DUTY_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.daily_life import CareCustomRow, HouseworkRow, LeisurePursuitRow, SpaceNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import PurificationRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.daily_life import DistanceNorm, HouseDuty, LeisureKind, PostureForm, TouchNorm, WashFrequency, WashPlace, WasteHandling
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.life_traits import HouseDutyTrait
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.customs.time_budgets import shares_for, sleeps_of
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int

LEANING = 60
LEISURE_AXES: tuple[tuple[ValueAxis, LeisureKind], ...] = (
    (ValueAxis.FRIENDSHIP, LeisureKind.CONVERSATION),
    (ValueAxis.COMPETITION, LeisureKind.SPORT),
    (ValueAxis.LEISURE, LeisureKind.GAMES),
    (ValueAxis.ARTWORK, LeisureKind.MUSIC),
    (ValueAxis.CRAFTSMANSHIP, LeisureKind.CRAFTS),
    (ValueAxis.WEALTH, LeisureKind.COLLECTING),
    (ValueAxis.KNOWLEDGE, LeisureKind.READING),
    (ValueAxis.XENOPHILIA, LeisureKind.EXCURSION),
    (ValueAxis.PIETY, LeisureKind.WORSHIP_EXTRA),
    (ValueAxis.PERSEVERANCE, LeisureKind.REST),
)
LEISURE_SHARES = (50, 30, 20)
CARE_DUTIES = having(HOUSE_DUTY_TRAITS, HouseDutyTrait.CARE_DUTIES)
SERVED_DUTIES = having(HOUSE_DUTY_TRAITS, HouseDutyTrait.SERVED_DUTIES)
KEEPERS = frozenset({HouseholdRole.HEAD, HouseholdRole.SPOUSE, HouseholdRole.HEIR, HouseholdRole.CARER, HouseholdRole.DEPENDENT})


@dataclass
class SeedTally:
    budgets: int = 0
    care: int = 0
    space: int = 0
    leisure: int = 0
    houses: int = 0


async def peoples_lacking(ctx: TickContext, owned: set[int]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [row for row in rows if row.id not in owned and not held(row.id)]


async def kinds_in_towns(ctx: TickContext, people_id: int) -> set[StructureKind]:
    towns = await towns_of_people(ctx.session, people_id)
    if not towns:
        return set()
    return set(await ctx.session.scalars(select(StructureProfileRow.kind).where(StructureProfileRow.host_entity_id.in_(towns))))


def frequency_for(purity: int) -> WashFrequency:
    if purity >= LEANING:
        return WashFrequency.DAILY
    if purity >= PERCENT // 4:
        return WashFrequency.WEEKLY
    if purity >= 0:
        return WashFrequency.SEASONAL
    return WashFrequency.BY_RITE


async def seed_care(ctx: TickContext, tally: SeedTally) -> None:
    owned = set(await ctx.session.scalars(select(CareCustomRow.people_entity_id)))
    for folk in await peoples_lacking(ctx, owned):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        kinds = await kinds_in_towns(ctx, folk.id)
        purified = await ctx.session.scalar(select(PurificationRow.people_entity_id).where(PurificationRow.people_entity_id == folk.id).limit(1))
        place = WashPlace.BATH_HOUSE if StructureKind.BATHHOUSE in kinds else WashPlace.RITE if purified is not None else WashPlace.HOME
        purity = values.get(ValueAxis.PURITY, 0)
        ctx.session.add(
            CareCustomRow(
                people_entity_id=folk.id,
                wash_frequency=frequency_for(purity),
                wash_place=place,
                grooming=clamp_int(PERCENT // 2 + values.get(ValueAxis.HONOUR, 0) // 2, 0, PERCENT),
                cleanliness=clamp_int(PERCENT // 2 + purity // 2, 0, PERCENT),
                waste_handling=WasteHandling.SEWERS if StructureKind.SEWER in kinds else WasteHandling.PITS,
                locked=[],
            )
        )
        tally.care += 1


def distance_for(values: dict[ValueAxis, int]) -> DistanceNorm:
    if values.get(ValueAxis.HIERARCHY, 0) >= LEANING:
        return DistanceNorm.WIDE
    if values.get(ValueAxis.KINSHIP, 0) >= LEANING or values.get(ValueAxis.FRIENDSHIP, 0) >= LEANING:
        return DistanceNorm.CLOSE
    return DistanceNorm.ARM


def touch_for(values: dict[ValueAxis, int]) -> TouchNorm:
    if values.get(ValueAxis.PURITY, 0) >= LEANING:
        return TouchNorm.FORBIDDEN
    if values.get(ValueAxis.KINSHIP, 0) >= LEANING:
        return TouchNorm.KIN_ONLY
    if values.get(ValueAxis.XENOPHILIA, 0) >= LEANING:
        return TouchNorm.OPEN
    return TouchNorm.SPARING


async def seed_space(ctx: TickContext, tally: SeedTally) -> None:
    owned = set(await ctx.session.scalars(select(SpaceNormRow.people_entity_id)))
    for folk in await peoples_lacking(ctx, owned):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        posture = SeededRandom.for_epoch(folk.id, 0, "posture").pick(list(PostureForm))
        ctx.session.add(SpaceNormRow(people_entity_id=folk.id, distance=distance_for(values), touch=touch_for(values), posture=posture, locked=[]))
        tally.space += 1


async def seed_leisure(ctx: TickContext, tally: SeedTally) -> None:
    owned = set(
        await ctx.session.scalars(
            select(LeisurePursuitRow.holder_node_id)
            .join(EntityRow, EntityRow.id == LeisurePursuitRow.holder_node_id)
            .where(EntityRow.entity_type == EntityType.PEOPLE)
        )
    )
    for folk in await peoples_lacking(ctx, owned):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        ranked = sorted(LEISURE_AXES, key=lambda pair: (-values.get(pair[0], 0), list(LeisureKind).index(pair[1])))
        for (_, kind), share in zip(ranked, LEISURE_SHARES, strict=False):
            ctx.session.add(LeisurePursuitRow(holder_node_id=folk.id, kind=kind, share=share, locked=[]))
        tally.leisure += 1


async def fill_stages(ctx: TickContext, tally: SeedTally) -> None:
    rows = await ctx.session.execute(select(TimeBudgetRow.people_entity_id, TimeBudgetRow.social_class, TimeBudgetRow.life_stage))
    present: dict[int, set[tuple[SocialClass, LifeStage]]] = {}
    for people_id, social_class, stage in rows:
        present.setdefault(people_id, set()).add((social_class, stage))
    for people_id in sorted(present):
        missing = [(social_class, stage) for stage in SEEDED_STAGES for social_class in SocialClass if (social_class, stage) not in present[people_id]]
        if not missing or held(people_id):
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people_id)
        sleeps = await sleeps_of(ctx.session, people_id)
        for social_class, stage in missing:
            ctx.session.add(
                TimeBudgetRow(
                    people_entity_id=people_id,
                    social_class=social_class,
                    life_stage=stage,
                    **shares_for(values, ctx.rules, sleeps=sleeps, stage=stage),
                    locked=[],
                )
            )
        tally.budgets += 1


def doer_for(duty: HouseDuty, members: list[HouseholdMemberRow], turn: int) -> HouseholdMemberRow | None:
    servants = [member for member in members if member.role is HouseholdRole.SERVANT]
    carers = [member for member in members if member.role is HouseholdRole.CARER]
    keepers = [member for member in members if member.role in KEEPERS]
    if duty in SERVED_DUTIES and servants:
        return servants[turn % len(servants)]
    if duty in CARE_DUTIES and carers:
        return carers[turn % len(carers)]
    return keepers[turn % len(keepers)] if keepers else None


async def seed_houses(ctx: TickContext, tally: SeedTally) -> None:
    kept = set(await ctx.session.scalars(select(HouseworkRow.household_id).distinct()))
    load = PERCENT // len(HouseDuty)
    for household in list(await ctx.session.scalars(select(HouseholdRow).where(HouseholdRow.head_node_id.is_not(None)).order_by(HouseholdRow.id))):
        if household.id in kept or held(household.head_node_id):
            continue
        members = list(
            await ctx.session.scalars(
                select(HouseholdMemberRow).where(HouseholdMemberRow.household_id == household.id).order_by(HouseholdMemberRow.member_node_id)
            )
        )
        placed = False
        for turn, duty in enumerate(HouseDuty):
            doer = doer_for(duty, members, turn)
            if doer is None:
                continue
            ctx.session.add(HouseworkRow(household_id=household.id, duty=duty, doer_node_id=doer.member_node_id, doer_role=doer.role, load=load, locked=[]))
            placed = True
        tally.houses += int(placed)


async def seed_daily(ctx: TickContext) -> SeedTally:
    tally = SeedTally()
    await fill_stages(ctx, tally)
    await seed_care(ctx, tally)
    await seed_space(ctx, tally)
    await seed_leisure(ctx, tally)
    await seed_houses(ctx, tally)
    await ctx.session.flush()
    return tally
