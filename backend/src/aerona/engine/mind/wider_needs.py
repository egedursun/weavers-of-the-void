from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.mind import BODILESS_NEEDS
from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.catalog.needs_sources import ACTIVITY_COLUMNS, ACTIVITY_NEEDS, NEED_SOURCES
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.domain.enums.activities import ActivityKind, SatisfactionSource
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mind import NeedKind, PressureKind, ValueAxis
from aerona.domain.enums.minds import MindOrigin, MindSeat
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.customs.time_budgets import budget_of as time_budget_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

FULL = PERCENT
OLD = having(LIFE_STAGE_TRAITS, LifeStageTrait.OLD)


async def budget_of(session: AsyncSession, mortal: EntityRow) -> dict[ActivityKind, int]:
    row = await time_budget_of(session, mortal)
    return {kind: int(getattr(row, column)) for kind, column in ACTIVITY_COLUMNS.items()} if row is not None else {}


def pct(value: float) -> int:
    return clamp_int(value, 0, FULL)


async def recent_gatherings(session: AsyncSession, mortal_id: int, since: int) -> int:
    joined = select(func.count()).select_from(GatheringGuestRow).join(GatheringRow, GatheringRow.id == GatheringGuestRow.gathering_id)
    return int(
        await session.scalar(joined.where(GatheringGuestRow.node_id == mortal_id, GatheringGuestRow.attended.is_(True), GatheringRow.epoch >= since)) or 0
    )


async def wider_needs(
    session: AsyncSession, rules: Rules, mortal: EntityRow, *, values: dict[ValueAxis, int], pressures: dict[PressureKind, int], epoch: int
) -> dict[NeedKind, int]:
    table = rules.needs_wider
    profile = await session.get(MortalProfileRow, mortal.id)
    mind = await session.get(MindProfileRow, mortal.id)
    made = mind is not None and mind.origin is not MindOrigin.BORN
    people = await people_of(session, mortal)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    captive = bool(await active_bonds(session, [BondKind.HOLDS_CAPTIVE], targets=[mortal.id]))
    autonomy = FULL - (table.captive_autonomy if captive else 0) - (table.serf_autonomy if mortal.social_class is SocialClass.SERF_OR_SLAVE else 0)
    autonomy -= pressures.get(PressureKind.OPPRESSION, 0) * table.oppression_autonomy_pct // PERCENT
    networked = await session.scalar(select(NetworkNodeRow.id).where(NetworkNodeRow.member_node_id == mortal.id).limit(1)) is not None
    knowledge = (culture.literacy if culture is not None else 0) * table.literacy_knowledge_pct // PERCENT + (table.network_knowledge if networked else 0)
    gathered = await recent_gatherings(session, mortal.id, epoch - table.stimulation_epochs)
    stimulation = table.stimulation_base + gathered * table.stimulation_per_gathering
    if made:
        continuity = mind.stability if mind is not None else FULL
        upkeep = (profile.wealth if profile is not None else 0) * table.upkeep_wealth_pct // PERCENT + max(0, mind.maker_bond if mind is not None else 0)
    else:
        afraid = values.get(ValueAxis.DEATH, 0) <= -table.fear_of_ending_at and profile is not None and profile.life_stage in OLD
        continuity = FULL - (table.fear_of_ending if afraid else 0)
        upkeep = FULL
    return {
        NeedKind.AUTONOMY: pct(autonomy),
        NeedKind.KNOWLEDGE: pct(knowledge),
        NeedKind.STIMULATION: pct(stimulation),
        NeedKind.CONTINUITY: pct(continuity),
        NeedKind.UPKEEP: pct(upkeep),
    }


async def by_activity_and_make(session: AsyncSession, rules: Rules, mortal: EntityRow, needs: dict[NeedKind, int]) -> None:
    budget = await budget_of(session, mortal)
    step = rules.needs_wider.activity_need_pct
    for activity, share in budget.items():
        for need in ACTIVITY_NEEDS[activity]:
            if SatisfactionSource.ACTIVITY in NEED_SOURCES[need]:
                needs[need] = pct(needs.get(need, 0) + share * step // PERCENT)
    mind = await session.get(MindProfileRow, mortal.id)
    if mind is not None and mind.origin is not MindOrigin.BORN and mind.seat is not MindSeat.BODY:
        for need in BODILESS_NEEDS:
            needs[need] = FULL
    if stat_or(mortal, "renown", 0) >= rules.needs_wider.renown_status_at and SatisfactionSource.ACHIEVEMENT in NEED_SOURCES[NeedKind.STATUS]:
        needs[NeedKind.STATUS] = pct(needs.get(NeedKind.STATUS, 0) + rules.needs_wider.renown_status)
