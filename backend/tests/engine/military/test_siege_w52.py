from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import DEFENCES, FALL_CHOICES, FALLEN_STATES, SIEGE_ACTION_SPECS, SIEGE_STATES, SIEGE_WORKS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.military import CaptiveFate, DefenderAction, SackChoice, SiegeAction, SiegeWork, UnitKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.military.siege_w52 import capable, deport, fall_choice, flood, pace, progress, ransom_city, sapped
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.military.w52_war_setup import army_of, siege_of
from tests.engine.warfare.factories import make_ctx, tune


class Host:
    def __init__(self, army: EntityRow, owner: EntityRow, profile: object) -> None:
        self.army, self.owner, self.profile = army, owner, profile


def test_every_siege_value_has_its_catalogue_entry() -> None:
    assert set(SIEGE_ACTION_SPECS) == set(SiegeAction) and set(SIEGE_WORKS) == set(SiegeWork)
    assert set(DEFENCES) == set(DefenderAction) and set(FALL_CHOICES) == set(SackChoice) and set(SIEGE_STATES) == set(SiegeStatus)
    assert SiegeStatus.SURRENDERED in FALLEN_STATES and DEFENCES[DefenderAction.FLOOD_APPROACHES].needs_water


async def test_a_ramp_rises_slowly_and_only_fliers_assault_from_the_air(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker_id, _, siege = await siege_of(ctx, world_id)
    assert pace(ctx, SiegeWork.RAMP) < pace(ctx, SiegeWork.LADDERS)
    progress(ctx, siege, [SiegeWork.RAMP])
    assert int(siege.works[SiegeWork.RAMP.value]) == pace(ctx, SiegeWork.RAMP)
    owner = await session.get(EntityRow, attacker_id)
    army_id, profile = await army_of(ctx, attacker_id, world_id)
    army = await session.get(EntityRow, army_id)
    assert owner is not None and army is not None
    assert SiegeWork.AIR_ASSAULT not in await capable(ctx, siege, Host(army, owner, profile), 1.0)
    flier_id, flier_profile = await army_of(ctx, attacker_id, world_id, kind=UnitKind.SKY_RIDERS)
    flier = await session.get(EntityRow, flier_id)
    assert flier is not None and SiegeWork.AIR_ASSAULT in await capable(ctx, siege, Host(flier, owner, flier_profile), 1.0)
    siege.works = {**siege.works, SiegeWork.SAPPING.value: 100}
    assert sapped(ctx, siege, 100) == 100 - ctx.rules.siege.sapping_effect


async def test_flooding_undoes_works_and_a_fallen_city_is_ransomed_or_its_people_taken(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), sack={"ransom_from": 0, "ransom_pick_pct": 100})
    ctx = make_ctx(session, rules)
    attacker_id, city_id, siege = await siege_of(ctx, world_id)
    siege.works = {SiegeWork.RAMP.value: 50}
    assert await flood(ctx, siege) == 50 * ctx.rules.siege.flood_halt_pct // 100
    session.add(SettlementProfileRow(settlement_entity_id=city_id, size_tier=SizeTier.TOWN, treasury=100, locked=[]))
    await session.flush()
    attacker = await session.get(EntityRow, attacker_id)
    city = await session.get(EntityRow, city_id)
    assert attacker is not None and city is not None
    assert await fall_choice(ctx, siege, attacker, SackChoice.SACK, bondage=False) is SackChoice.RANSOM_CITY
    assert await ransom_city(ctx, city, attacker) == 100 * ctx.rules.sack.ransom_share_pct // 100
    before = stat(city, "population") or 0
    moved = await deport(ctx, city, attacker, siege.war_id)
    assert moved == round(before * ctx.rules.sack.deport_share_pct / 100) and stat(city, "population") == before - moved
    cohort = await session.scalar(select(CaptiveCohortRow).where(CaptiveCohortRow.origin_entity_id == city_id))
    assert cohort is not None and cohort.fate is CaptiveFate.LABOUR
