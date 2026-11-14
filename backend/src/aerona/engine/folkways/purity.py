from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.divine import CreatorTabooRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import ImpuritySourceRow, PurificationRow, PurityRankRow, PurityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import SentenceRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import OPEN_INJURY_STATES
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.folkways import ImpuritySource, Purification, PurityState
from aerona.domain.enums.mind import Profession, ValueAxis
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.mind.book import values_for
from aerona.engine.mortal.kin import close_kin_of, parents_of
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import has_flag

BEAST_WORK = frozenset({Profession.HUNTER, Profession.RIDER})
DEFILED_PLACES = (EntityFlag.RUIN, EntityFlag.EMPTY_TOMB)


@dataclass
class PurityTally:
    seeded: int = 0
    defiled: int = 0
    purified: int = 0
    ranked: int = 0
    reformed: int = 0


async def sources_of(ctx: TickContext, people_id: int) -> dict[ImpuritySource, ImpuritySourceRow]:
    rows = await ctx.session.scalars(select(ImpuritySourceRow).where(ImpuritySourceRow.people_entity_id == people_id))
    return {row.source: row for row in rows}


async def methods_of(ctx: TickContext, people_id: int) -> list[PurificationRow]:
    return list(await ctx.session.scalars(select(PurificationRow).where(PurificationRow.people_entity_id == people_id).order_by(PurificationRow.method)))


async def ranks_of(ctx: TickContext, people_id: int) -> list[PurityRankRow]:
    return list(
        await ctx.session.scalars(
            select(PurityRankRow).where(PurityRankRow.people_entity_id == people_id).order_by(PurityRankRow.standing.desc(), PurityRankRow.id)
        )
    )


async def seed_culture(ctx: TickContext, people: EntityRow, tally: PurityTally) -> None:
    table = ctx.rules.purity
    values = await values_for(ctx.session, people.id)
    if values.get(ValueAxis.PURITY, 0) < table.culture_from or await sources_of(ctx, people.id):
        return
    rng = ctx.rng(seed_of("purity.seed", people.id))
    for source in rng.sample(list(ImpuritySource), min(len(ImpuritySource), table.sources_per_culture)):
        ctx.session.add(
            ImpuritySourceRow(
                people_entity_id=people.id,
                source=source,
                weight=rng.integer(table.weight_low, table.weight_high),
                lasts=rng.integer(1, table.longest_lasts),
                locked=[],
            )
        )
    for method in rng.sample(list(Purification), min(len(Purification), table.methods_per_culture)):
        ctx.session.add(
            PurificationRow(
                people_entity_id=people.id,
                method=method,
                epochs=rng.integer(0, table.longest_lasts),
                cost=rng.integer(0, table.highest_cost),
                success=rng.integer(table.success_low, PERCENT),
                locked=[],
            )
        )
    tally.seeded += 1
    if values.get(ValueAxis.HIERARCHY, 0) >= table.castes_from and not await ranks_of(ctx, people.id):
        professions = [item.value for item in rng.sample(list(Profession), len(Profession))]
        count = max(2, table.ranks)
        size = max(1, len(professions) // count)
        for index in range(count):
            share = professions[index * size : (index + 1) * size] if index < count - 1 else professions[index * size :]
            ctx.session.add(
                PurityRankRow(
                    people_entity_id=people.id,
                    name=f"{people.name} rank {index + 1}",
                    standing=clamp_int(PERCENT - index * PERCENT // count, 0, PERCENT),
                    professions=share,
                    endogamous=True,
                    commensal=True,
                    locked=[],
                )
            )
    await ctx.session.flush()


async def cursed_bearer(session: AsyncSession, mortal_id: int) -> bool:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == mortal_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await session.scalar(
        select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.curse != CurseKind.NONE).limit(1)
    )
    return found is not None


async def impure_professions(ctx: TickContext, people_id: int) -> set[str]:
    ranks = await ranks_of(ctx, people_id)
    if ranks:
        return set(ranks[-1].professions)
    rng = ctx.rng(seed_of("purity.professions", people_id))
    return {item.value for item in rng.sample(list(Profession), min(len(Profession), ctx.rules.purity.impure_professions))}


@dataclass
class Touch:
    ctx: TickContext
    mortal: EntityRow
    profile: MortalProfileRow
    people_id: int


async def by_the_dead(touch: Touch) -> bool:
    kin = await close_kin_of(touch.ctx.session, touch.mortal.id)
    query = select(EntityRow.id).where(EntityRow.id.in_(kin), EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == touch.ctx.epoch)
    return bool(kin) and await touch.ctx.session.scalar(query.limit(1)) is not None


async def by_birth(touch: Touch) -> bool:
    query = select(BondRow.id).where(BondRow.source_node_id == touch.mortal.id, BondRow.kind == BondKind.PARENT_OF, BondRow.epoch == touch.ctx.epoch)
    return await touch.ctx.session.scalar(query.limit(1)) is not None


async def by_fluids(touch: Touch) -> bool:
    query = select(InjuryRow.id).where(InjuryRow.bearer_node_id == touch.mortal.id, InjuryRow.epoch == touch.ctx.epoch)
    return await touch.ctx.session.scalar(query.limit(1)) is not None


async def by_wound(touch: Touch) -> bool:
    query = select(InjuryRow.id).where(InjuryRow.bearer_node_id == touch.mortal.id, InjuryRow.state.in_(list(OPEN_INJURY_STATES)))
    return await touch.ctx.session.scalar(query.limit(1)) is not None


async def by_food(touch: Touch) -> bool:
    return touch.ctx.rng(seed_of("purity.food", touch.mortal.id, touch.ctx.epoch)).chance(touch.ctx.rules.purity.food_chance)


async def by_species(touch: Touch) -> bool:
    return touch.profile.profession in BEAST_WORK


async def by_profession(touch: Touch) -> bool:
    job = touch.profile.profession
    return job is not None and job.value in await impure_professions(touch.ctx, touch.people_id)


async def by_outsiders(touch: Touch) -> bool:
    session = touch.ctx.session
    town = await session.get(EntityRow, touch.mortal.location_id) if touch.mortal.location_id is not None else None
    here = await people_of(session, town) if town is not None else None
    return here is not None and here.id != touch.people_id


async def by_place(touch: Touch) -> bool:
    place = touch.mortal.location_id
    return place is not None and any([await has_flag(touch.ctx.session, place, flag) for flag in DEFILED_PLACES])


async def by_object(touch: Touch) -> bool:
    return await cursed_bearer(touch.ctx.session, touch.mortal.id)


async def by_act(touch: Touch) -> bool:
    query = select(SentenceRow.id).where(SentenceRow.mortal_entity_id == touch.mortal.id, SentenceRow.epoch == touch.ctx.epoch)
    return await touch.ctx.session.scalar(query.limit(1)) is not None


async def by_made_thing(touch: Touch) -> bool:
    return await touch.ctx.session.scalar(select(ConstructRow.entity_id).where(ConstructRow.maker_entity_id == touch.mortal.id).limit(1)) is not None


async def by_taboo(touch: Touch) -> bool:
    query = select(CreatorTabooRow.act).where(CreatorTabooRow.last_breaker_node_id == touch.mortal.id, CreatorTabooRow.last_broken_epoch == touch.ctx.epoch)
    return await touch.ctx.session.scalar(query.limit(1)) is not None


TOUCHES: dict[ImpuritySource, Callable[[Touch], Awaitable[bool]]] = {
    ImpuritySource.THE_DEAD: by_the_dead,
    ImpuritySource.BIRTH: by_birth,
    ImpuritySource.BODILY_FLUIDS: by_fluids,
    ImpuritySource.FOOD: by_food,
    ImpuritySource.SPECIES: by_species,
    ImpuritySource.PROFESSION: by_profession,
    ImpuritySource.OUTSIDERS: by_outsiders,
    ImpuritySource.PLACE: by_place,
    ImpuritySource.OBJECT: by_object,
    ImpuritySource.ACT: by_act,
    ImpuritySource.MADE_THING: by_made_thing,
    ImpuritySource.TABOO: by_taboo,
    ImpuritySource.WOUND: by_wound,
}


async def purity_of(ctx: TickContext, mortal_id: int) -> PurityRow:
    row = await ctx.session.get(PurityRow, mortal_id)
    if row is None:
        row = PurityRow(holder_node_id=mortal_id, state=PurityState.PURE, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def place_in_rank(
    ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow, row: PurityRow, ranks: list[PurityRankRow], *, tally: PurityTally
) -> None:
    if not ranks or "rank_id" in row.locked:
        return
    known = {rank.id for rank in ranks}
    if row.rank_id in known:
        rank = next(item for item in ranks if item.id == row.rank_id)
        rise = ctx.rules.purity
        if profile.wealth >= rise.rise_wealth and rank is not ranks[0] and ctx.rng(seed_of("purity.rise", mortal.id, ctx.epoch)).chance(rise.rise_chance):
            row.rank_id = ranks[ranks.index(rank) - 1].id
            tally.ranked += 1
        return
    for parent in await parents_of(ctx.session, mortal.id):
        inherited = await ctx.session.get(PurityRow, parent)
        if inherited is not None and inherited.rank_id in known:
            row.rank_id = inherited.rank_id
            tally.ranked += 1
            return
    job = profile.profession.value if profile.profession is not None else None
    row.rank_id = next((rank.id for rank in ranks if job in rank.professions), ranks[len(ranks) // 2].id)
    tally.ranked += 1


async def purify(ctx: TickContext, mortal: EntityRow, row: PurityRow, methods: list[PurificationRow], tally: PurityTally) -> None:
    if row.state is PurityState.PURE or "state" in row.locked:
        return
    if row.until_epoch is not None and ctx.epoch < row.until_epoch:
        return
    usable = [method for method in methods if row.state is not PurityState.DEFILED or method.method is not Purification.TIME]
    method = min(usable, key=lambda item: (item.cost, item.epochs, item.method.value), default=None)
    if method is None:
        if row.state is PurityState.DEFILED:
            return
    elif (method.cost and not await take_coin(ctx.session, ctx.rules, mortal, method.cost)) or not ctx.rng(
        seed_of("purity.cleanse", mortal.id, ctx.epoch)
    ).chance(method.success):
        return
    row.state, row.source, row.until_epoch, row.since_epoch = PurityState.PURE, None, None, ctx.epoch
    tally.purified += 1


async def defile(ctx: TickContext, row: PurityRow, source: ImpuritySourceRow, methods: list[PurificationRow], tally: PurityTally) -> None:
    if "state" in row.locked:
        return
    worst = source.weight >= ctx.rules.purity.defiled_from
    state = PurityState.DEFILED if worst else PurityState.IMPURE
    if row.state is PurityState.DEFILED and not worst:
        return
    wait = min((method.epochs for method in methods if method.method is Purification.TIME), default=source.lasts)
    row.state, row.source, row.since_epoch = state, source.source, ctx.epoch
    row.until_epoch = ctx.epoch + max(source.lasts, wait)
    tally.defiled += 1


async def reform(ctx: TickContext, people: EntityRow, sources: dict[ImpuritySource, ImpuritySourceRow], tally: PurityTally) -> None:
    table = ctx.rules.purity
    value = (await values_for(ctx.session, people.id)).get(ValueAxis.PURITY, 0)
    span = max(1, PERCENT - table.culture_from)
    target = 0 if value < table.culture_from else table.weight_low + (value - table.culture_from) * (table.weight_high - table.weight_low) // span
    for source, row in list(sources.items()):
        if "weight" in row.locked:
            continue
        step = round_half_up((target - row.weight) * table.reform_pct / PERCENT) or (target > row.weight) - (target < row.weight)
        row.weight = clamp_int(row.weight + step, 0, PERCENT)
        if row.weight <= 0 and target <= 0:
            await ctx.session.delete(row)
            del sources[source]
            tally.reformed += 1


async def keep_purity(ctx: TickContext, tally: PurityTally) -> None:
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for people in peoples:
        if not held(people.id):
            await seed_culture(ctx, people, tally)
    for people in peoples:
        sources = await sources_of(ctx, people.id)
        if not held(people.id):
            await reform(ctx, people, sources, tally)
        if not sources:
            continue
        methods = await methods_of(ctx, people.id)
        ranks = await ranks_of(ctx, people.id)
        for mortal in await ctx.session.scalars(
            select(EntityRow)
            .where(await folk_among(ctx.session, [people.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        ):
            profile = await ctx.session.get(MortalProfileRow, mortal.id)
            if profile is None or held(mortal.id):
                continue
            row = await purity_of(ctx, mortal.id)
            await place_in_rank(ctx, mortal, profile, row, ranks, tally=tally)
            await purify(ctx, mortal, row, methods, tally)
            rng = ctx.rng(seed_of("purity.touch", mortal.id, ctx.epoch))
            touch = Touch(ctx, mortal, profile, people.id)
            for source in sorted(sources.values(), key=lambda item: item.source.value):
                if await TOUCHES[source.source](touch) and rng.chance(source.weight):
                    await defile(ctx, row, source, methods, tally)
                    break
    await ctx.session.flush()


async def unclean(session: AsyncSession, node_id: int) -> bool:
    row = await session.get(PurityRow, node_id)
    return row is not None and row.state is not PurityState.PURE


async def caste_bars(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    one = await session.get(PurityRow, first.id)
    two = await session.get(PurityRow, second.id)
    if one is None or two is None:
        return False
    if (one.state is PurityState.PURE) != (two.state is PurityState.PURE):
        return True
    if one.rank_id is None or two.rank_id is None or one.rank_id == two.rank_id:
        return False
    rank = await session.get(PurityRankRow, one.rank_id)
    return rank is not None and rank.endogamous


async def apart_at_table(session: AsyncSession, first_id: int, second_id: int) -> bool:
    one = await session.get(PurityRow, first_id)
    two = await session.get(PurityRow, second_id)
    if one is None or two is None or one.rank_id is None or two.rank_id is None or one.rank_id == two.rank_id:
        return False
    ranks = [await session.get(PurityRankRow, one.rank_id), await session.get(PurityRankRow, two.rank_id)]
    return any(rank is not None and rank.commensal for rank in ranks)


async def barred_professions(session: AsyncSession, mortal_id: int) -> frozenset[str]:
    row = await session.get(PurityRow, mortal_id)
    rank = await session.get(PurityRankRow, row.rank_id) if row is not None and row.rank_id is not None else None
    if rank is None:
        return frozenset()
    others = await session.scalars(select(PurityRankRow).where(PurityRankRow.people_entity_id == rank.people_entity_id, PurityRankRow.id != rank.id))
    return frozenset(job for other in others for job in other.professions) - frozenset(rank.professions)
