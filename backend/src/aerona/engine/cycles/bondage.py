from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.tables.collective import DiasporaRow
from aerona.db.tables.cycles import IndentureRow, ManumissionRow, SlaveMarketRow
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, LabourReasonRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import AccountKind, AccountStance
from aerona.domain.enums.cycles import LabourRegime, ManumissionPath
from aerona.domain.enums.demography import AgeBand, Job
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ActKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import DebtRemedy, LawKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import LabourReason
from aerona.domain.enums.structure import BuildScale, ConstructionStatus
from aerona.engine.body.customs import people_of
from aerona.engine.collective.accounts import record
from aerona.engine.collective.book import population_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import polities, realm_towns
from aerona.engine.cycles.indenture import record_manumission
from aerona.engine.demography.bound import BOUND, move_people, sync_bound_share
from aerona.engine.demography.cohorts import cohorts_of, row_for
from aerona.engine.demography.events import captive_origins
from aerona.engine.economy.purse import coin_of, receive_coin, take_coin
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.mind.hooks import judged
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.regard import value_distance
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.structures.construction import finish
from aerona.engine.structures.spec import resolve

MARKET_TIERS = frozenset({SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS})
GREAT_SCALES = frozenset({BuildScale.GRAND, BuildScale.WONDER})
HALF = PERCENT // 2


@dataclass
class BondageTally:
    corvee_laid: int = 0
    corvee_work: int = 0
    suffering: int = 0
    indentured: int = 0
    released: int = 0
    inflated: int = 0
    markets: int = 0
    sold: int = 0
    revolts: int = 0
    refused: int = 0
    contracted: int = 0
    equal: int = 0


async def active_work(ctx: TickContext, work_id: int) -> ConstructionRow | None:
    found: ConstructionRow | None = await ctx.session.scalar(
        select(ConstructionRow).where(ConstructionRow.structure_entity_id == work_id, ConstructionRow.status == ConstructionStatus.ACTIVE).limit(1)
    )
    return found


async def remember_suffering(ctx: TickContext, town: EntityRow, row: CorveeRow, work: EntityRow, tally: BondageTally) -> None:
    stances = {town.id: AccountStance.NEUTRAL}
    if row.polity_entity_id is not None:
        stances[row.polity_entity_id] = AccountStance.VILIFY
    await record(ctx, town, AccountKind.FOLK_MEMORY, fidelity=ctx.rules.historiography.folk_fidelity, stances=stances, subject_id=work.id, structure_id=work.id)
    tally.suffering += 1
    await note(
        ctx,
        f"{town.name} remembers the {row.laboured_epochs} epochs of forced labour that raised {work.name}.",
        key="corvee.suffering",
        ids=[town.id, work.id, *([row.polity_entity_id] if row.polity_entity_id else [])],
    )


async def forced_labour_reading(ctx: TickContext, polity: EntityRow, seat: EntityRow) -> int:
    people = await people_of(ctx.session, seat)
    if people is None:
        return await ethic_reading(ctx.session, ctx.rules, polity.id, ActKind.FORCED_LABOUR, {})
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    return await ethic_reading(ctx.session, ctx.rules, people.id, ActKind.FORCED_LABOUR, values)


async def lay_corvees(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.corvee
    for polity, _ in await polities(ctx.session):
        if held(polity.id) or not ctx.rng(f"corvee.lay.{polity.id}.{ctx.epoch}").chance(table.lay_pct):
            continue
        towns = await realm_towns(ctx.session, polity.id)
        great = None
        for town in towns:
            for construction in await ctx.session.scalars(
                select(ConstructionRow).where(ConstructionRow.site_entity_id == town.id, ConstructionRow.status == ConstructionStatus.ACTIVE)
            ):
                if resolve(construction.kind).scale in GREAT_SCALES:
                    great = construction
                    break
            if great is not None:
                break
        if great is None:
            continue
        work = await ctx.session.get(EntityRow, great.structure_entity_id)
        if await forced_labour_reading(ctx, polity, towns[0]) < table.unthinkable_at:
            tally.refused += 1
            await note(
                ctx,
                f"{polity.name} would not force its folk to labour on {work.name if work else 'a great work'}; its people hold forced labour unthinkable.",
                key="corvee.refused",
                ids=[polity.id],
            )
            continue
        laid = 0
        summoned: list[int] = []
        for town in towns:
            if held(town.id) or await ctx.session.get(CorveeRow, town.id) is not None:
                continue
            ctx.session.add(
                CorveeRow(
                    community_entity_id=town.id,
                    share_pct=table.share_pct,
                    polity_entity_id=polity.id,
                    work_entity_id=great.structure_entity_id,
                    laboured_epochs=0,
                    since_epoch=ctx.epoch,
                    by_hand=False,
                )
            )
            laid += 1
            summoned.append(town.id)
        if laid:
            tally.corvee_laid += laid
            await note(
                ctx, f"{polity.name} summoned {laid} towns to forced labour on {work.name if work else 'a great work'}.", key="corvee.laid", ids=[polity.id]
            )
            await judged(ctx, polity.id, summoned[0], ActKind.FORCED_LABOUR, note=f"forced labour on {work.name if work else 'a great work'}")


async def work_corvees(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.corvee
    for row in list(await ctx.session.scalars(select(CorveeRow).where(CorveeRow.work_entity_id.is_not(None)).order_by(CorveeRow.community_entity_id))):
        town = await living_entity(ctx.session, row.community_entity_id)
        if town is None or held(town.id) or row.work_entity_id is None:
            continue
        work = await ctx.session.get(EntityRow, row.work_entity_id)
        construction = await active_work(ctx, row.work_entity_id)
        if work is None or construction is None:
            if work is not None:
                await remember_suffering(ctx, town, row, work, tally)
            if row.by_hand:
                row.work_entity_id = None
            else:
                await ctx.session.delete(row)
            continue
        hands = await ctx.session.get(LabourReasonRow, (town.id, Job.BUILDING, LabourReason.CORVEE))
        added = round_half_up((hands.workers if hands is not None else 0) * table.work_output / PERCENT)
        row.laboured_epochs += 1
        if added <= 0 or "progress" in construction.locked:
            continue
        construction.progress = min(construction.cost, construction.progress + added)
        profile = await ctx.session.get(StructureProfileRow, construction.structure_entity_id)
        if profile is not None:
            profile.progress = clamp_int(construction.progress * PERCENT / max(1, construction.cost), 0, PERCENT)
        tally.corvee_work += added
        if construction.progress >= construction.cost:
            await finish(ctx, construction)


async def employer_in(ctx: TickContext, town: EntityRow) -> int:
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(
            EntityRow.status == EntityStatus.CANON,
            FactionProfileRow.home_entity_id == town.id,
            FactionProfileRow.kind.in_([FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD]),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    return int(found) if found is not None else town.id


async def bind_debtors(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.indenture
    towns = await ctx.session.execute(
        select(EntityRow, CommunitySocietyRow)
        .join(CommunitySocietyRow, CommunitySocietyRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for town, society in towns.all():
        if held(town.id):
            continue
        poor = society.satisfaction(SocialClass.FARMER) + society.satisfaction(SocialClass.OUTCAST)
        if poor / 2 >= table.misery_at or not ctx.rng(f"indenture.{town.id}.{ctx.epoch}").chance(table.form_pct):
            continue
        remedy = await law_param(ctx.session, town.id, LawKind.DEBT_LAW, "remedy")
        if remedy == DebtRemedy.JUBILEE.value:
            continue
        regime = LabourRegime.PEONAGE if remedy == DebtRemedy.BONDAGE.value else LabourRegime.INDENTURE
        count = round_half_up(population_of(town) * table.bound_pct / PERCENT)
        if count <= 0:
            continue
        people = await people_of(ctx.session, town)
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id) if people is not None else {}
        spread = ctx.rng(f"indenture.greed.{town.id}.{ctx.epoch}").integer(-table.exploitation_spread, table.exploitation_spread)
        exploitation = clamp_int(table.exploitation_base + values.get(ValueAxis.WEALTH, 0) * table.greed_weight / PERCENT + spread, 0, PERCENT)
        ctx.session.add(
            IndentureRow(
                community_entity_id=town.id,
                employer_node_id=await employer_in(ctx, town),
                regime=regime,
                count=count,
                term_epochs=table.term_epochs,
                debt=count * table.debt_per_head,
                exploitation=exploitation,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.indentured += count
        word = "debt peonage" if regime is LabourRegime.PEONAGE else "indenture"
        await note(ctx, f"{count} of the poor of {town.name} were bound into {word}.", key="indenture.bound", ids=[town.id])


async def contract_exploitation(ctx: TickContext, town: EntityRow, newcomers: EntityRow) -> int:
    table = ctx.rules.indenture
    hosts = await people_of(ctx.session, town)
    mine = await stored_values(ctx.session, ValueHolder.CULTURE, hosts.id) if hosts is not None else {}
    theirs = await stored_values(ctx.session, ValueHolder.CULTURE, newcomers.id)
    greed = mine.get(ValueAxis.WEALTH, 0) * table.greed_weight / PERCENT
    return clamp_int(table.exploitation_base + greed + value_distance(mine, theirs) * table.foreign_weight / PERCENT, 0, PERCENT)


async def bind_migrants(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.indenture
    statement = select(DiasporaRow).where(DiasporaRow.population > 0).order_by(DiasporaRow.host_entity_id, DiasporaRow.people_entity_id)
    for row in list(await ctx.session.scalars(statement)):
        town = await living_entity(ctx.session, row.host_entity_id)
        newcomers = await living_entity(ctx.session, row.people_entity_id)
        if town is None or newcomers is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id, newcomers.id):
            continue
        bound = await ctx.session.scalar(
            select(IndentureRow.id).where(IndentureRow.community_entity_id == town.id, IndentureRow.origin_entity_id == newcomers.id).limit(1)
        )
        if bound is not None or not ctx.rng(f"indenture.migrants.{town.id}.{newcomers.id}.{ctx.epoch}").chance(table.migrant_pct):
            continue
        count = round_half_up(row.population * table.migrant_share_pct / PERCENT)
        if count <= 0:
            continue
        ctx.session.add(
            IndentureRow(
                community_entity_id=town.id,
                employer_node_id=await employer_in(ctx, town),
                regime=LabourRegime.INDENTURE,
                count=count,
                term_epochs=table.term_epochs,
                debt=count * table.debt_per_head,
                exploitation=await contract_exploitation(ctx, town, newcomers),
                origin_entity_id=newcomers.id,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.contracted += count
        await note(
            ctx,
            f"{several(count, 'newcomer', 'newcomers')} of {newcomers.name} in {town.name} signed contracts of labour for their keep.",
            key="indenture.contracted",
            ids=[town.id, newcomers.id],
        )


async def serve_terms(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.indenture
    for row in list(await ctx.session.scalars(select(IndentureRow).order_by(IndentureRow.id))):
        if held(row.community_entity_id) or (row.employer_node_id is not None and held(row.employer_node_id)):
            continue
        town = await ctx.session.get(EntityRow, row.community_entity_id)
        if "debt" not in row.locked:
            repaid = round_half_up(row.count * table.repay_per_head * (PERCENT - row.exploitation) / PERCENT)
            row.debt = max(0, row.debt - repaid)
            if ctx.rng(f"indenture.inflate.{row.id}.{ctx.epoch}").chance(row.exploitation * table.inflate_share / PERCENT):
                row.debt += round_half_up(row.debt * table.inflate_pct / PERCENT)
                tally.inflated += 1
        if row.regime is LabourRegime.INDENTURE and "term_epochs" not in row.locked:
            row.term_epochs = max(0, row.term_epochs - 1)
        done = row.term_epochs <= 0 if row.regime is LabourRegime.INDENTURE else row.debt <= 0
        if not done:
            continue
        tally.released += row.count
        await ctx.session.delete(row)
        if town is not None:
            await note(ctx, f"{row.count} bound labourers of {town.name} served out their bond and went free.", key="indenture.released", ids=[town.id])


async def slavery_lawful(ctx: TickContext, town: EntityRow) -> bool:
    people = await people_of(ctx.session, town)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture is not None and culture.slavery_lawful


async def skill_factor(ctx: TickContext, town_id: int) -> float:
    rows = list(await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == town_id)))
    total = sum(row.workers for row in rows)
    crafted = sum(row.workers for row in rows if row.job is Job.CRAFTING)
    share = crafted * PERCENT / total if total else 0
    return 1 + share * ctx.rules.slave_markets.skill_weight / PERCENT / PERCENT


def age_factor(ctx: TickContext, rows: list[CohortRow]) -> float:
    bound = [row for row in rows if row.social_class is BOUND]
    whole = sum(row.count for row in bound)
    adults = sum(row.count for row in bound if row.age_band is AgeBand.ADULT)
    share = adults * PERCENT / whole if whole else HALF
    return 1 + (share - HALF) * ctx.rules.slave_markets.age_weight / PERCENT / HALF


async def origin_factors(ctx: TickContext, town: EntityRow) -> tuple[float, float]:
    table = ctx.rules.slave_markets
    host = await people_of(ctx.session, town)
    origins = await captive_origins(ctx, town.id)
    if host is None or not origins:
        return 1.0, 1.0
    mine = await stored_values(ctx.session, ValueHolder.CULTURE, host.id)
    distance = 0
    beauty = 0
    seen = 0
    for origin in origins:
        distance += value_distance(mine, await stored_values(ctx.session, ValueHolder.CULTURE, origin.id))
        folk = await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.affiliated_entity_id == origin.id).limit(table.appearance_sample)
        )
        for mortal in folk:
            beauty += stat_or(mortal, "beauty", HALF)
            seen += 1
    foreign = 1 - distance / len(origins) * table.origin_weight / PERCENT / PERCENT
    looks = 1 + ((beauty / seen if seen else HALF) - HALF) * table.appearance_weight / PERCENT / HALF
    return max(0.1, foreign), max(0.1, looks)


async def price_market(ctx: TickContext, town: EntityRow, row: SlaveMarketRow) -> None:
    table = ctx.rules.slave_markets
    rows = list((await cohorts_of(ctx.session, town.id)).values())
    stock = sum(cohort.count for cohort in rows if cohort.social_class is BOUND and cohort.age_band is AgeBand.ADULT)
    if "stock" not in row.locked:
        row.stock = round_half_up(stock * table.sale_pct / PERCENT)
    if "price" in row.locked:
        return
    origin, looks = await origin_factors(ctx, town)
    scarcity = 1 + table.scarcity_weight / PERCENT * (1 - row.stock / max(1, row.stock + table.demand))
    row.price = clamp_int(table.base_price * await skill_factor(ctx, town.id) * age_factor(ctx, rows) * origin * looks * scarcity, 0, 10**6)


async def buyer_for(ctx: TickContext, town: EntityRow, markets: set[int]) -> EntityRow | None:
    best: tuple[int, EntityRow] | None = None
    towns = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == town.world_id, EntityRow.id != town.id
        )
    )
    for other in towns:
        if other.id in markets or held(other.id) or not await slavery_lawful(ctx, other):
            continue
        purse = await coin_of(ctx.session, ctx.rules, other)
        if best is None or (purse, -other.id) > (best[0], -best[1].id):
            best = (purse, other)
    return best[1] if best is not None else None


async def sell(ctx: TickContext, town: EntityRow, row: SlaveMarketRow, markets: set[int], tally: BondageTally) -> None:
    if row.stock <= 0 or row.price <= 0:
        return
    buyer = await buyer_for(ctx, town, markets)
    if buyer is None:
        return
    affordable = min(row.stock, await coin_of(ctx.session, ctx.rules, buyer) // row.price)
    if affordable <= 0 or not await take_coin(ctx.session, ctx.rules, buyer, affordable * row.price):
        return
    await receive_coin(ctx.session, ctx.rules, town, affordable * row.price)
    source = await cohorts_of(ctx.session, town.id)
    target = await cohorts_of(ctx.session, buyer.id)
    moved = 0
    for key in sorted(source, key=lambda item: tuple(part.value for part in item)):
        band, _, social_class, _ = key
        if social_class is not BOUND or band is not AgeBand.ADULT or moved >= affordable:
            continue
        step = min(source[key].count, affordable - moved)
        if move_amount(source[key], row_for(ctx.session, target, buyer.id, key, ctx.epoch), "count", step):
            moved += step
    with flowing(FlowCategory.MIGRATION):
        set_stats(town, population=max(0, population_of(town) - moved))
        set_stats(buyer, population=population_of(buyer) + moved)
    sync_bound_share(await ctx.session.get(CommunitySocietyRow, town.id), source)
    sync_bound_share(await ctx.session.get(CommunitySocietyRow, buyer.id), target)
    if "sold" not in row.locked:
        row.sold += moved
    tally.sold += moved
    await note(
        ctx, f"The market of {town.name} sold {moved} bound folk to {buyer.name} at {row.price} each.", key="slave_markets.sold", ids=[town.id, buyer.id]
    )


async def keep_markets(ctx: TickContext, tally: BondageTally) -> None:
    towns = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found = [(town, profile) for town, profile in towns.all() if not held(town.id)]
    markets = {town.id for town, profile in found if profile.size_tier in MARKET_TIERS}
    for town, profile in found:
        lawful = await slavery_lawful(ctx, town)
        row = await ctx.session.get(SlaveMarketRow, town.id)
        if row is None:
            if not lawful or profile.size_tier not in MARKET_TIERS:
                continue
            row = SlaveMarketRow(
                settlement_entity_id=town.id, price=ctx.rules.slave_markets.base_price, stock=0, sold=0, open=True, updated_epoch=ctx.epoch, locked=[]
            )
            ctx.session.add(row)
            tally.markets += 1
            await note(ctx, f"A market in bound folk opened in {town.name}.", key="slave_markets.opened", ids=[town.id])
        if "open" not in row.locked:
            row.open = lawful
        row.updated_epoch = ctx.epoch
        if not row.open:
            continue
        await price_market(ctx, town, row)
        await sell(ctx, town, row, markets, tally)


async def slave_risings(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.manumission
    rebels = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, FactionProfileRow.kind == FactionKind.REBELS, EntityRow.social_class == SocialClass.SERF_OR_SLAVE)
        .order_by(EntityRow.id)
    )
    for faction, profile in rebels.all():
        town = await living_entity(ctx.session, profile.home_entity_id) if profile.home_entity_id is not None else None
        settled = await ctx.session.get(SettlementProfileRow, town.id) if town is not None else None
        if town is None or settled is None or held(town.id, faction.id):
            continue
        if stat_or(faction, "strength", 0) * table.revolt_strength < settled.militia:
            continue
        rows = await cohorts_of(ctx.session, town.id)
        freed = await move_people(ctx, town, rows, source=BOUND, target=SocialClass.FARMER, share=table.revolt_share_pct / PERCENT)
        if freed <= 0:
            continue
        await record_manumission(ctx, town, freed, ManumissionPath.REVOLT)
        sync_bound_share(await ctx.session.get(CommunitySocietyRow, town.id), rows)
        tally.revolts += freed
        await note(ctx, f"The rising of {faction.name} broke the chains of {freed} in {town.name}.", key="manumission.revolt", ids=[faction.id, town.id])


async def raise_freed(ctx: TickContext, tally: BondageTally) -> None:
    table = ctx.rules.manumission
    for row in list(await ctx.session.scalars(select(ManumissionRow).where(ManumissionRow.standing < PERCENT).order_by(ManumissionRow.id))):
        town = await living_entity(ctx.session, row.community_entity_id)
        if town is None or held(town.id) or "standing" in row.locked:
            continue
        people = await people_of(ctx.session, town)
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id) if people is not None else {}
        drag = max(0, values.get(ValueAxis.HIERARCHY, 0)) * table.hierarchy_drag / PERCENT
        row.standing = min(PERCENT, row.standing + max(1, round_half_up(table.standing_rise * (PERCENT - drag) / PERCENT)))
        if row.standing < PERCENT:
            continue
        tally.equal += row.count
        await note(ctx, f"The {row.count} freed of {town.name} now stand as equals among the freeborn.", key="manumission.equal", ids=[town.id])


async def keep_bondage(ctx: TickContext, tally: BondageTally) -> None:
    await lay_corvees(ctx, tally)
    await work_corvees(ctx, tally)
    await bind_debtors(ctx, tally)
    await bind_migrants(ctx, tally)
    await serve_terms(ctx, tally)
    await keep_markets(ctx, tally)
    await slave_risings(ctx, tally)
    await raise_freed(ctx, tally)
    await ctx.session.flush()
