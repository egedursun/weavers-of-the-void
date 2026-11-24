from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.folkways import SIGN_WEIGHTS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import LuckBeliefRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.folkways import LuckReach, LuckSign
from aerona.domain.enums.kind_crafts import ColourFocus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import ConstructionState
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in, towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record


@dataclass(frozen=True)
class Reading:
    ctx: TickContext
    town: EntityRow
    belief: LuckBeliefRow

    @property
    def sign(self) -> int:
        return 1 if self.belief.lucky else -1


async def trade(reading: Reading) -> None:
    town = reading.town
    set_stats(town, prosperity=clamp_int(stat_or(town, "prosperity", 0) + reading.sign * reading.ctx.rules.luck.trade_pct, 0, PERCENT))


async def union(reading: Reading) -> None:
    ctx = reading.ctx
    wed = select(BondRow.source_node_id).where(BondRow.kind == BondKind.SPOUSE_OF, BondRow.epoch == ctx.epoch)
    here = await present_in(ctx.session, reading.town)
    newly_wed = await ctx.session.scalars(
        select(MortalProfileRow)
        .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
        .where(here, EntityRow.id.in_(wed), EntityRow.status == EntityStatus.CANON)
        .order_by(MortalProfileRow.entity_id)
    )
    for profile in list(newly_wed):
        if not held(profile.entity_id) and "stress" not in profile.locked:
            profile.stress = clamp_int(profile.stress - reading.sign * ctx.rules.luck.union_stress, 0, PERCENT)


async def building(reading: Reading) -> None:
    ctx = reading.ctx
    if reading.belief.lucky:
        return
    works = await ctx.session.scalars(
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(EntityRow.location_id == reading.town.id, StructureProfileRow.construction_state == ConstructionState.BUILDING)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    for work in list(works):
        if not held(work.structure_entity_id) and "progress" not in work.locked:
            work.progress = clamp_int(round_half_up(work.progress * (PERCENT - ctx.rules.luck.building_pct) / PERCENT), 0, PERCENT)


async def learning(reading: Reading) -> None:
    ctx = reading.ctx
    people = await people_of(ctx.session, reading.town)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is not None and not held(culture.people_entity_id) and "literacy" not in culture.locked:
        culture.literacy = clamp_int(culture.literacy + reading.sign * ctx.rules.luck.learning_pct, 0, PERCENT)


async def contest(reading: Reading) -> None:
    profile = await reading.ctx.session.get(SettlementProfileRow, reading.town.id)
    if profile is not None and "prestige" not in profile.locked:
        profile.prestige = clamp_int(profile.prestige + reading.sign * reading.ctx.rules.luck.contest_prestige, 0, PERCENT)


async def believed(_reading: Reading) -> None:
    return None


REACHES: Mapping[LuckReach, Callable[[Reading], Awaitable[None]]] = total(
    LuckReach,
    {
        LuckReach.HARVEST: believed,
        LuckReach.HEALTH: believed,
        LuckReach.BIRTH: believed,
        LuckReach.JOURNEY: believed,
        LuckReach.BATTLE: believed,
        LuckReach.TRADE: trade,
        LuckReach.UNION: union,
        LuckReach.BUILDING: building,
        LuckReach.LEARNING: learning,
        LuckReach.CONTEST: contest,
    },
)


def weighted_signs(ctx: TickContext, rng: SeededRandom, count: int) -> list[LuckSign]:
    pool = list(LuckSign)
    chosen: list[LuckSign] = []
    while pool and len(chosen) < count:
        weights = [float(SIGN_WEIGHTS[sign](ctx.rules)) for sign in pool]
        if not any(weights):
            break
        sign = rng.weighted(pool, weights)
        chosen.append(sign)
        pool.remove(sign)
    return chosen


async def creature_of(ctx: TickContext, people: EntityRow, rng: SeededRandom) -> int | None:
    atlas = await RegionAtlas.load(ctx.session)
    regions = sorted({region for town in await towns_of_people(ctx.session, people.id) if (region := atlas.top_region(town)) is not None})
    species = sorted(set(await ctx.session.scalars(select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id.in_(regions)))))
    return rng.pick(species) if species else None


async def mark_of(ctx: TickContext, people: EntityRow, sign: LuckSign, rng: SeededRandom) -> tuple[int | None, ColourFocus | None]:
    if sign is LuckSign.ANIMAL:
        return await creature_of(ctx, people, rng), None
    if sign is LuckSign.COLOUR:
        return None, rng.pick(list(ColourFocus))
    return None, None


async def read_luck(ctx: TickContext, town: EntityRow, people: EntityRow | None) -> bool:
    if people is None or held(town.id):
        return False
    beliefs = list(await ctx.session.scalars(select(LuckBeliefRow).where(LuckBeliefRow.people_entity_id == people.id).order_by(LuckBeliefRow.id)))
    rng = ctx.rng(f"luck.read.{town.id}.{ctx.epoch}")
    if not beliefs or not rng.chance(ctx.rules.luck.read_chance):
        return False
    belief = rng.weighted(beliefs, [float(SIGN_WEIGHTS[row.sign](ctx.rules)) + 1 for row in beliefs])
    await REACHES[belief.reach](Reading(ctx, town, belief))
    await record(
        ctx,
        "luck.read",
        roles={IncidentRole.PLACE: town.id, IncidentRole.SUBJECT: belief.species_entity_id},
        facts={"sign": belief.sign, "reach": belief.reach, "lucky": int(belief.lucky)},
        place=town.id,
    )
    return True
