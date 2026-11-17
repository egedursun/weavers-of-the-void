from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import DemographicTransitionRow, DiasporaRow, RoleNormRow, SexRatioRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.unions import PluralSide, UnionForm
from aerona.engine.body.customs import people_id_of, people_of
from aerona.engine.collective.book import population_of, shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import asabiyya_factor
from aerona.engine.cycles.breeding import breeding_factor, fixed_sexes_at
from aerona.engine.cycles.sides import first_sex, system_of_people
from aerona.engine.demography.cohorts import cohort_rows
from aerona.engine.mind.book import stored_values
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

THIRD = PERCENT // 3
URBAN_OF = total(
    SizeTier,
    {
        SizeTier.HAMLET: 5,
        SizeTier.VILLAGE: 15,
        SizeTier.TOWN: 50,
        SizeTier.CITY: 80,
        SizeTier.METROPOLIS: 95,
        SizeTier.MEGALOPOLIS: 98,
        SizeTier.WORLD_CITY: 99,
    },
)
FERTILITY_SPAN = 200
WEALTH_PER_HEAD = 100


@dataclass
class DemographyTally:
    diasporas: int = 0
    remitted: int = 0
    quarters: int = 0
    assimilated: int = 0
    transitions: int = 0
    skewed: int = 0


async def cohort_counts(session: AsyncSession, community_id: int) -> dict[tuple[AgeBand, Sex], int]:
    found: dict[tuple[AgeBand, Sex], int] = {}
    for row in await cohort_rows(session, community_id):
        found[(row.age_band, row.sex)] = found.get((row.age_band, row.sex), 0) + row.count
    return found


async def communities(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.SETTLEMENT, EntityType.PEOPLE]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def transition_of(ctx: TickContext, community_id: int) -> DemographicTransitionRow:
    row = await ctx.session.get(DemographicTransitionRow, community_id)
    if row is None:
        row = DemographicTransitionRow(community_entity_id=community_id, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def ratio_of(ctx: TickContext, community_id: int) -> SexRatioRow:
    row = await ctx.session.get(SexRatioRow, community_id)
    if row is None:
        row = SexRatioRow(community_entity_id=community_id, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def women_study(session: AsyncSession, people_id: int | None) -> bool:
    row = await session.get(RoleNormRow, (people_id, RoleKind.PROFESSION)) if people_id is not None else None
    return row is None or row.eligibility not in {RoleEligibility.MALE_ONLY}


async def measure(ctx: TickContext, community: EntityRow, tally: DemographyTally) -> None:
    table = ctx.rules.demographic_transition
    counts = await cohort_counts(ctx.session, community.id)
    everyone = sum(counts.values())
    if everyone <= 0:
        return
    people = await people_of(ctx.session, community)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    transition = await transition_of(ctx, community.id)
    elders = sum(counts.get((AgeBand.ELDER, sex), 0) for sex in Sex)
    if "elder_share" not in transition.locked:
        transition.elder_share = clamp_int(elders * PERCENT / everyone, 0, PERCENT)
    if "urban_share" not in transition.locked:
        transition.urban_share = URBAN_OF[profile.size_tier] if profile is not None else (culture.urbanisation if culture is not None else 0)
    if "literacy" not in transition.locked:
        transition.literacy = culture.literacy if culture is not None else 0
    study = table.education_cut if await women_study(ctx.session, people.id if people is not None else None) else 0
    target = PERCENT - (table.urban_cut * transition.urban_share + table.literacy_cut * transition.literacy + study * transition.literacy) / PERCENT
    shift(transition, "fertility_pct", (target - transition.fertility_pct) * table.lag_pct / PERCENT, high=FERTILITY_SPAN)
    tally.transitions += 1
    ratio = await ratio_of(ctx, community.id)
    men, women = counts.get((AgeBand.ADULT, Sex.MALE), 0), counts.get((AgeBand.ADULT, Sex.FEMALE), 0)
    if "males_per_hundred" not in ratio.locked:
        ratio.males_per_hundred = clamp_int(men * PERCENT / max(1, women), 0, PERCENT * 10)
    if "widows" not in ratio.locked:
        ratio.widows = max(0, women - men)
    if ratio.males_per_hundred < ctx.rules.sex_ratio.skew_at:
        tally.skewed += 1
    if profile is not None and transition.elder_share > THIRD and people is not None:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
        if values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.FAMILY, 0) > 0:
            shift(profile, "public_order", table.elder_stability / 5)


async def scarce_side_plural(ctx: TickContext, community_id: int) -> bool:
    form = await law_param(ctx.session, community_id, LawKind.MARRIAGE_LAW, "form")
    if form == UnionForm.GROUP.value:
        return True
    if form != UnionForm.PLURAL.value:
        return False
    side = str(await law_param(ctx.session, community_id, LawKind.MARRIAGE_LAW, "plural_side") or PluralSide.EITHER.value)
    if side == PluralSide.EITHER.value:
        return True
    town = await ctx.session.get(EntityRow, community_id)
    system = await system_of_people(ctx.session, await people_id_of(ctx.session, town)) if town is not None else None
    scarce = PluralSide.FIRST if system is None or first_sex(system) == Sex.MALE.value else PluralSide.SECOND
    return side == scarce.value


async def fertility_factor(ctx: TickContext, community_id: int) -> float:
    table = ctx.rules.sex_ratio
    transition = await ctx.session.get(DemographicTransitionRow, community_id)
    factor = (transition.fertility_pct if transition is not None else PERCENT) / PERCENT
    factor *= await breeding_factor(ctx.session, ctx.rules, community_id)
    ratio = await ctx.session.get(SexRatioRow, community_id) if await fixed_sexes_at(ctx.session, community_id) else None
    if ratio is not None and ratio.males_per_hundred < table.skew_at:
        several = await scarce_side_plural(ctx, community_id)
        lack = (table.skew_at - ratio.males_per_hundred) / PERCENT
        factor *= 1 - lack * (PERCENT - (table.polygamy_pct if several else 0)) / PERCENT
        factor *= 1 - table.late_marriage_pct / PERCENT * lack
    return max(0.0, factor)


async def levy_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    transition = await session.get(DemographicTransitionRow, community_id)
    if transition is None or transition.elder_share <= THIRD:
        return 1.0
    return max(0.0, 1 - (transition.elder_share - THIRD) * rules.demographic_transition.elder_levy_cut / (PERCENT * PERCENT))


async def homeland_of(ctx: TickContext, people_id: int) -> int | None:
    return await ctx.session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.kind == BondKind.LIVES_IN, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == people_id, BondRow.role == BondRole.HOMELAND)
        .order_by(BondRow.id)
        .limit(1)
    )


async def tend_diasporas(ctx: TickContext, tally: DemographyTally) -> None:
    table = ctx.rules.diaspora
    seen: set[tuple[int, int]] = set()
    for town, profile in [
        (town, profile)
        for town, profile in await ctx.session.execute(
            select(EntityRow, SettlementProfileRow)
            .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
            .where(EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
    ]:
        if held(town.id):
            continue
        for key, share in sorted(profile.foreigners.items()):
            people_id = int(key)
            if held(people_id) or await ctx.session.get(EntityRow, people_id) is None:
                continue
            seen.add((people_id, town.id))
            row = await ctx.session.get(DiasporaRow, (people_id, town.id))
            if row is None:
                row = DiasporaRow(
                    people_entity_id=people_id, host_entity_id=town.id, home_entity_id=await homeland_of(ctx, people_id), since_epoch=ctx.epoch, locked=[]
                )
                ctx.session.add(row)
                await ctx.session.flush()
                tally.diasporas += 1
            size = round_half_up(population_of(town) * share / PERCENT)
            grew = size > row.population
            if "population" not in row.locked:
                row.population = size
            shift(row, "ties", table.chain_ties if grew else -table.ties_decay)
            await remit(ctx, row, profile, tally)
            await raise_quarter(ctx, row, town, tally)
            if row.ties < table.assimilate_at / max(0.1, await asabiyya_factor(ctx.session, [people_id], ctx.rules.asabiyya.assimilation_weight)):
                await assimilate(ctx, row, town, tally)
    for row in list(await ctx.session.scalars(select(DiasporaRow).order_by(DiasporaRow.people_entity_id, DiasporaRow.host_entity_id))):
        if (row.people_entity_id, row.host_entity_id) not in seen and not row.locked and not held(row.host_entity_id):
            await ctx.session.delete(row)
    await ctx.session.flush()


async def remit(ctx: TickContext, row: DiasporaRow, host: SettlementProfileRow, tally: DemographyTally) -> None:
    home = await ctx.session.get(SettlementProfileRow, row.home_entity_id) if row.home_entity_id is not None else None
    if home is None or held(home.settlement_entity_id):
        return
    sent = min(host.treasury, round_half_up(row.population * WEALTH_PER_HEAD / PERCENT * ctx.rules.diaspora.remittance_pct / PERCENT * row.ties / PERCENT))
    if sent > 0 and move_amount(host, home, "treasury", sent):
        if "remittance" not in row.locked:
            row.remittance = sent
        tally.remitted += sent


async def raise_quarter(ctx: TickContext, row: DiasporaRow, town: EntityRow, tally: DemographyTally) -> None:
    if row.population < ctx.rules.diaspora.quarter_at:
        return
    found = await ctx.session.scalar(
        select(DistrictRow.id).where(DistrictRow.settlement_entity_id == town.id, DistrictRow.kind == DistrictKind.FOREIGN_QUARTER).limit(1)
    )
    if found is not None:
        return
    ctx.session.add(
        DistrictRow(
            settlement_entity_id=town.id, kind=DistrictKind.FOREIGN_QUARTER, level=1, built_epoch=ctx.epoch, built_by_entity_id=row.people_entity_id, locked=[]
        )
    )
    await ctx.session.flush()
    tally.quarters += 1
    people = await ctx.session.get(EntityRow, row.people_entity_id)
    if people is not None:
        await record(
            ctx,
            "diaspora.quarter",
            roles={IncidentRole.MAKER: people.id, IncidentRole.PLACE: town.id},
            facts={"count": row.population},
            steps=(
                StepDraft(
                    StepAction.LAY_FOUNDATION, actor=people.id, target=town.id, locus_kind=StepLocus.DISTRICT, locus_key=DistrictKind.FOREIGN_QUARTER.value
                ),
            ),
            place=town.id,
        )


async def assimilate(ctx: TickContext, row: DiasporaRow, town: EntityRow, tally: DemographyTally) -> None:
    if row.locked:
        return
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is not None and "foreigners" not in profile.locked:
        profile.foreigners = {key: value for key, value in profile.foreigners.items() if key != str(row.people_entity_id)}
    for bond in await ctx.session.scalars(
        select(BondRow).where(
            BondRow.kind == BondKind.LIVES_IN,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id == row.people_entity_id,
            BondRow.target_node_id == town.id,
        )
    ):
        if bond.role is not BondRole.HOMELAND:
            await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "assimilated")
    await ctx.session.delete(row)
    tally.assimilated += 1
    people = await ctx.session.get(EntityRow, row.people_entity_id)
    if people is not None:
        await record(
            ctx,
            "diaspora.assimilated",
            roles={IncidentRole.SUBJECT: people.id, IncidentRole.PLACE: town.id},
            facts={"count": row.population, "generations": max(0, ctx.epoch - row.since_epoch)},
            place=town.id,
        )


async def diaspora_pull(session: AsyncSession, pull_pct: int, people_id: int, town_id: int) -> float:
    row = await session.get(DiasporaRow, (people_id, town_id))
    return 1 + pull_pct / PERCENT * row.ties / PERCENT if row is not None else 1.0


async def keep_demography(ctx: TickContext, tally: DemographyTally) -> None:
    for community in await communities(ctx):
        await measure(ctx, community, tally)
    await tend_diasporas(ctx, tally)
    await ctx.session.flush()
