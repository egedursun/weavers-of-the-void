from sqlalchemy import select

from aerona.catalog.genetics import DWELLINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import community_of
from aerona.engine.households.homes import district_for, dwelling_kind_for, household_of, starting_quality
from aerona.engine.mortal.kin import fosterers_of, parents_of, spouses_of
from aerona.engine.primitives.numbers import round_half_up

YOUNG = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH})
OLD = frozenset({LifeStage.ELDER, LifeStage.ANCIENT})


async def stage_of(ctx: TickContext, mortal_id: int) -> LifeStage | None:
    profile = await ctx.session.get(MortalProfileRow, mortal_id)
    return profile.life_stage if profile is not None else None


async def found_household(ctx: TickContext, head: EntityRow) -> HouseholdRow:
    community = await community_of(ctx.session, head)
    profile = await ctx.session.get(MortalProfileRow, head.id)
    household = HouseholdRow(
        name=f"Household of {head.name}",
        head_node_id=head.id,
        settlement_node_id=community.id if community is not None else None,
        social_class=head.social_class,
        wealth=round_half_up((profile.wealth if profile is not None else 0) * ctx.rules.households.starting_wealth_pct / PERCENT),
        income=0,
        expenses=0,
        servants=0,
        dependents=0,
        burden=0,
        formed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(household)
    await ctx.session.flush()
    kind = await dwelling_kind_for(ctx.session, head)
    ctx.session.add(
        DwellingRow(
            household_id=household.id,
            kind=kind,
            quality=starting_quality(kind, head.social_class),
            rooms=DWELLINGS[kind].rooms,
            settlement_node_id=household.settlement_node_id,
            district_id=await district_for(ctx.session, household.settlement_node_id, head.social_class),
            built_epoch=ctx.epoch,
            locked=[],
        )
    )
    ctx.session.add(HouseholdMemberRow(member_node_id=head.id, household_id=household.id, role=HouseholdRole.HEAD, joined_epoch=ctx.epoch))
    await ctx.session.flush()
    return household


async def join_household(ctx: TickContext, household: HouseholdRow, mortal: EntityRow, role: HouseholdRole) -> HouseholdMemberRow:
    found = await ctx.session.get(HouseholdMemberRow, mortal.id)
    if found is None:
        found = HouseholdMemberRow(member_node_id=mortal.id, household_id=household.id, role=role, joined_epoch=ctx.epoch)
        ctx.session.add(found)
    elif not found.locked:
        found.household_id, found.role, found.joined_epoch = household.id, role, ctx.epoch
    await ctx.session.flush()
    return found


async def kin_household(ctx: TickContext, mortal: EntityRow) -> tuple[HouseholdRow, HouseholdRole] | None:
    stage = await stage_of(ctx, mortal.id)
    for spouse in await spouses_of(ctx.session, mortal.id):
        household = await household_of(ctx.session, spouse)
        if household is not None:
            return household, HouseholdRole.SPOUSE
    if stage in YOUNG:
        for parent in await parents_of(ctx.session, mortal.id):
            household = await household_of(ctx.session, parent)
            if household is not None:
                return household, HouseholdRole.DEPENDENT
        for fosterer in await fosterers_of(ctx.session, mortal.id):
            household = await household_of(ctx.session, fosterer)
            if household is not None:
                return household, HouseholdRole.WARD
    return None


async def house_everyone(ctx: TickContext) -> int:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    housed = 0
    for mortal in await ctx.session.scalars(statement):
        if held(mortal.id) or await ctx.session.get(HouseholdMemberRow, mortal.id) is not None:
            continue
        found = await kin_household(ctx, mortal)
        if found is not None and not held_household(found[0]):
            await join_household(ctx, found[0], mortal, found[1])
        else:
            await found_household(ctx, mortal)
        housed += 1
    return housed


def held_household(household: HouseholdRow) -> bool:
    return "members" in (household.locked or [])
