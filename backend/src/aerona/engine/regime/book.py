from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.regime import TYPE_LABELS
from aerona.catalog.structures import RESEARCH_HOUSES
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.regime import (
    AcademicFreedomRow,
    CoalitionMemberRow,
    CredentialRow,
    ExaminationRow,
    ExamSittingRow,
    LineageSegmentRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolMemberRow,
    VenalOfficeRow,
)
from aerona.domain.enums.regime import LegitimacyType, PowerStance
from aerona.engine.primitives.folk import present_among
from aerona.engine.structures.readers import working
from aerona.rules.registry import Rules

HALF = PERCENT // 2
PROOFING = ("rotation", "parallel_guard", "loyalty_promotion", "hostages")


async def realm_seat(session: AsyncSession, entity_id: int | None) -> int | None:
    if entity_id is None:
        return None
    if await session.get(RegimeRow, entity_id) is not None:
        return entity_id
    found: int | None = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == entity_id).limit(1))
    return found


def kinds_of(regime: RegimeRow) -> dict[LegitimacyType, int]:
    return {LegitimacyType.TRADITIONAL: regime.traditional, LegitimacyType.CHARISMATIC: regime.charismatic, LegitimacyType.RATIONAL: regime.rational}


def dominant(regime: RegimeRow) -> LegitimacyType:
    found = kinds_of(regime)
    return max(found, key=lambda kind: (found[kind], -list(LegitimacyType).index(kind)))


async def legitimacy_kinds(session: AsyncSession, rules: Rules, polity_id: int) -> dict[str, int]:
    regime = await session.get(RegimeRow, polity_id)
    if regime is None:
        return {}
    weight = rules.legitimacy_types.legitimacy_weight
    parts: dict[str, int] = {}
    for kind, value in kinds_of(regime).items():
        moved = round((value - HALF) * weight / PERCENT)
        if moved:
            raised, lowered = TYPE_LABELS[kind]
            parts[raised if moved > 0 else lowered] = moved
    return parts


async def extraction_of(session: AsyncSession, polity_id: int) -> float:
    regime = await session.get(RegimeRow, polity_id)
    return regime.extraction / PERCENT if regime is not None else 1.0


async def bought_offices(session: AsyncSession, polity_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(VenalOfficeRow)
            .join(OfficeRow, OfficeRow.id == VenalOfficeRow.office_id)
            .where(OfficeRow.polity_entity_id == polity_id, VenalOfficeRow.sinecure.is_(False))
        )
        or 0
    )


async def corruption_pull(session: AsyncSession, rules: Rules, polity_id: int) -> float:
    regime = await session.get(RegimeRow, polity_id)
    private = (PERCENT - regime.public_share) * rules.selectorate.private_corruption / PERCENT if regime is not None else 0.0
    return private + await bought_offices(session, polity_id) * rules.venality.corruption


def measures(regime: RegimeRow) -> int:
    return sum(1 for field in PROOFING if getattr(regime, field))


async def coup_factor(session: AsyncSession, rules: Rules, polity_id: int) -> float:
    regime = await session.get(RegimeRow, polity_id)
    if regime is None:
        return 1.0
    disloyal = max(0, HALF - regime.coalition_loyalty) / HALF * rules.selectorate.coup_weight / PERCENT
    shield = max(0.0, 1 - measures(regime) * rules.coup_proofing.coup_cut / PERCENT)
    return (1 + disloyal) * shield


async def morale_factor(session: AsyncSession, rules: Rules, owner_id: int | None) -> float:
    regime = await session.get(RegimeRow, await realm_seat(session, owner_id)) if owner_id is not None else None
    if regime is None or not regime.rotation:
        return 1.0
    return 1 - rules.coup_proofing.morale_cut / PERCENT


async def plotter(session: AsyncSession, polity_id: int) -> int | None:
    found: int | None = await session.scalar(
        select(PowerBaseRow.mortal_entity_id)
        .where(PowerBaseRow.polity_entity_id == polity_id, PowerBaseRow.stance == PowerStance.PLOTTING)
        .order_by(PowerBaseRow.threat.desc(), PowerBaseRow.mortal_entity_id)
        .limit(1)
    )
    return found


@memoized(PowerBaseRow)
async def strongest_threat(session: AsyncSession, polity_id: int) -> int:
    found = await session.scalar(select(func.max(PowerBaseRow.threat)).where(PowerBaseRow.polity_entity_id == polity_id))
    return int(found or 0)


async def clients_of(session: AsyncSession, patron_id: int | None) -> set[int]:
    if patron_id is None:
        return set()
    return set(await session.scalars(select(PatronageTieRow.client_entity_id).where(PatronageTieRow.patron_node_id == patron_id)))


async def patron_pull(session: AsyncSession, rules: Rules, polity_id: int, patron_id: int | None, client_id: int | None) -> float:
    regime = await session.get(RegimeRow, polity_id)
    if regime is None or client_id is None or client_id not in await clients_of(session, patron_id):
        return 0.0
    return max(0, rules.clientelism.patronage_at - regime.institutions) / PERCENT


async def credentialed(session: AsyncSession, mortal_id: int) -> bool:
    return await session.scalar(select(CredentialRow.id).where(CredentialRow.mortal_entity_id == mortal_id).limit(1)) is not None


async def appointment_weights(session: AsyncSession, rules: Rules, polity_id: int, appointer_id: int | None, candidate_ids: Iterable[int]) -> dict[int, float]:
    wanted = set(candidate_ids)
    regime = await session.get(RegimeRow, polity_id)
    if regime is None or not wanted:
        return dict.fromkeys(wanted, 0.0)
    short = max(0, rules.clientelism.patronage_at - regime.institutions)
    clients = await clients_of(session, appointer_id)
    circle = set(await session.scalars(select(CoalitionMemberRow.mortal_entity_id).where(CoalitionMemberRow.polity_entity_id == polity_id)))
    examining = await session.scalar(select(ExamSittingRow.id).where(ExamSittingRow.polity_entity_id == polity_id).limit(1)) is not None
    learned = set(await session.scalars(select(CredentialRow.mortal_entity_id).where(CredentialRow.mortal_entity_id.in_(wanted)))) if examining else set()
    found: dict[int, float] = {}
    for candidate in wanted:
        weight = short * rules.clientelism.client_bonus / PERCENT if short and candidate in clients else 0.0
        if regime.loyalty_promotion and (candidate in clients or candidate in circle):
            weight += rules.clientelism.client_bonus
        if candidate in learned:
            weight += rules.examinations.credential_bonus
        found[candidate] = weight
    return found


async def credential_rank(session: AsyncSession, mortal_id: int, rank: int | None, preferred: int) -> int | None:
    if rank is None or rank <= preferred:
        return rank
    return preferred if await credentialed(session, mortal_id) else rank


async def graduates(session: AsyncSession, rules: Rules, polity_id: int, epoch: int) -> int:
    since = epoch - rules.examinations.credential_epochs
    found = await session.scalar(
        select(func.coalesce(func.sum(ExamSittingRow.passed), 0)).where(ExamSittingRow.polity_entity_id == polity_id, ExamSittingRow.epoch > since)
    )
    return round(int(found or 0) * rules.examinations.graduate_weight / PERCENT)


async def freedom_of(session: AsyncSession, community_id: int) -> int | None:
    levels = []
    for house in await working(session, RESEARCH_HOUSES, host_id=community_id):
        row = await session.get(AcademicFreedomRow, house.structure.id)
        if row is not None:
            levels.append(row.level)
    return round(sum(levels) / len(levels)) if levels else None


async def freedom_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    level = await freedom_of(session, community_id)
    if level is None:
        return 1.0
    return max(0.1, 1 + (level - HALF) * rules.academic_freedom.research_weight / PERCENT / HALF)


async def inquiry_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    level = await freedom_of(session, community_id)
    if level is None:
        return 1.0
    return max(0.1, 1 + (level - HALF) * rules.academic_freedom.theory_weight / PERCENT / HALF)


async def schooled(session: AsyncSession, community_id: int) -> bool:
    found = await session.scalar(
        select(SchoolMemberRow.school_id)
        .join(EntityRow, EntityRow.id == SchoolMemberRow.mortal_entity_id)
        .where(await present_among(session, [community_id]))
        .limit(1)
    )
    return found is not None


async def school_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return 1 + rules.school_lineages.research_pct / PERCENT if await schooled(session, community_id) else 1.0


async def backers(session: AsyncSession, house_id: int) -> int:
    return int(await session.scalar(select(func.count()).select_from(LineageSegmentRow).where(LineageSegmentRow.backs_entity_id == house_id)) or 0)


async def feud_swell(session: AsyncSession, rules: Rules, row: FeudRow) -> float:
    table = rules.segmentary_lineages
    backing = await backers(session, row.first_entity_id) + await backers(session, row.second_entity_id)
    first, second = await session.get(LineageSegmentRow, row.first_entity_id), await session.get(LineageSegmentRow, row.second_entity_id)
    foreign = first is not None and second is not None and first.tribe_entity_id != second.tribe_entity_id
    return (1 + backing * table.fusion_weight / PERCENT) * (1 + table.foreign_weight / PERCENT * foreign)


async def examined(session: AsyncSession, mortal: EntityRow) -> bool:
    realm = await realm_seat(session, mortal.location_id)
    return realm is not None and await session.get(ExaminationRow, realm) is not None
