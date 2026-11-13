from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import DWELLINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.genetics import DwellingKind
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.genetics.life import disease_factor
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

CLASS_QUALITY: dict[SocialClass, int] = {
    SocialClass.NOBLE: 15,
    SocialClass.MERCHANT: 8,
    SocialClass.PRIEST: 5,
    SocialClass.SCRIBE: 4,
    SocialClass.ARTISAN: 2,
    SocialClass.WARRIOR: 0,
    SocialClass.FARMER: -2,
    SocialClass.MONASTIC: -5,
    SocialClass.WORKER: -3,
    SocialClass.PROFESSIONAL: 6,
    SocialClass.OFFICIAL: 5,
    SocialClass.CITIZEN: 1,
    SocialClass.UNEMPLOYED: -12,
    SocialClass.SERF_OR_SLAVE: -15,
    SocialClass.OUTCAST: -20,
}
CLASS_EXPECTATION: dict[SocialClass, int] = {
    SocialClass.NOBLE: 70,
    SocialClass.MERCHANT: 55,
    SocialClass.PRIEST: 45,
    SocialClass.SCRIBE: 45,
    SocialClass.ARTISAN: 40,
    SocialClass.WARRIOR: 35,
    SocialClass.FARMER: 30,
    SocialClass.MONASTIC: 25,
    SocialClass.WORKER: 35,
    SocialClass.PROFESSIONAL: 55,
    SocialClass.OFFICIAL: 50,
    SocialClass.CITIZEN: 40,
    SocialClass.UNEMPLOYED: 15,
    SocialClass.SERF_OR_SLAVE: 15,
    SocialClass.OUTCAST: 10,
}
COMMON_EXPECTATION = 30
WAGE_CLASSES = frozenset({SocialClass.WORKER, SocialClass.PROFESSIONAL, SocialClass.OFFICIAL, SocialClass.CITIZEN, SocialClass.UNEMPLOYED})
TOWN_POPULATION = 1500
SEA_ROLES = frozenset({MortalRole.CAPTAIN, MortalRole.EXPLORER})
TOWER_ROLES = frozenset({MortalRole.SEER, MortalRole.SAGE})


async def household_of(session: AsyncSession, member_id: int) -> HouseholdRow | None:
    member = await session.get(HouseholdMemberRow, member_id)
    return await session.get(HouseholdRow, member.household_id) if member is not None else None


async def dwelling_of(session: AsyncSession, household_id: int) -> DwellingRow | None:
    found: DwellingRow | None = await session.scalar(select(DwellingRow).where(DwellingRow.household_id == household_id))
    return found


async def furnishings(session: AsyncSession, dwelling_id: int) -> int:
    return int(await session.scalar(select(func.count()).select_from(DwellingFurnishingRow).where(DwellingFurnishingRow.dwelling_id == dwelling_id)) or 0)


async def home_quality(session: AsyncSession, rules: Rules, dwelling: DwellingRow | None) -> int:
    if dwelling is None:
        return 0
    return clamp_int(dwelling.quality + await furnishings(session, dwelling.id) * rules.households.furnishing_quality, 0, PERCENT)


async def home_of(session: AsyncSession, rules: Rules, mortal_id: int) -> tuple[HouseholdRow | None, DwellingRow | None, int, int]:
    household = await household_of(session, mortal_id)
    dwelling = await dwelling_of(session, household.id) if household is not None else None
    members = (
        int(await session.scalar(select(func.count()).select_from(HouseholdMemberRow).where(HouseholdMemberRow.household_id == household.id)) or 0)
        if household is not None
        else 0
    )
    return household, dwelling, await home_quality(session, rules, dwelling), members


def expectation(social_class: SocialClass | None) -> int:
    return CLASS_EXPECTATION.get(social_class, COMMON_EXPECTATION) if social_class is not None else COMMON_EXPECTATION


async def rules_realm(session: AsyncSession, mortal_id: int) -> bool:
    found = await session.scalar(
        select(OfficeRow.id).where(OfficeRow.holder_entity_id == mortal_id, OfficeRow.kind.in_([OfficeKind.RULER, OfficeKind.REGENT])).limit(1)
    )
    return found is not None


async def in_cave(session: AsyncSession, mortal: EntityRow) -> bool:
    place = await session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    if place is None or place.entity_type is not EntityType.PLACE:
        return False
    profile = await session.get(PlaceProfileRow, place.id)
    return profile is not None and profile.kind is PlaceKind.CAVE


async def settled_kind(session: AsyncSession, mortal: EntityRow) -> DwellingKind:
    community = await community_of(session, mortal)
    if community is None or community.entity_type is not EntityType.SETTLEMENT:
        return DwellingKind.TENT
    if (stat(community, "population") or 0) >= TOWN_POPULATION:
        return DwellingKind.APARTMENT if mortal.social_class in WAGE_CLASSES else DwellingKind.TOWNHOUSE
    return DwellingKind.LONGHOUSE if mortal.social_class in (SocialClass.WARRIOR, SocialClass.FARMER) else DwellingKind.HUT


async def dwelling_kind_for(session: AsyncSession, mortal: EntityRow) -> DwellingKind:
    choices = (
        (mortal.mortal_role is MortalRole.RULER or await rules_realm(session, mortal.id), DwellingKind.PALACE),
        (await in_cave(session, mortal), DwellingKind.CAVE),
        (mortal.mortal_role in SEA_ROLES, DwellingKind.SHIP),
        (mortal.mortal_role in TOWER_ROLES, DwellingKind.TOWER),
        (mortal.social_class is SocialClass.NOBLE, DwellingKind.MANOR),
    )
    return next((kind for chosen, kind in choices if chosen), None) or await settled_kind(session, mortal)


CLASS_DISTRICTS: dict[SocialClass, tuple[DistrictKind, ...]] = {
    SocialClass.NOBLE: (DistrictKind.PALACE, DistrictKind.CITADEL, DistrictKind.MARKET),
    SocialClass.MERCHANT: (DistrictKind.MARKET, DistrictKind.HARBOUR, DistrictKind.FOREIGN_QUARTER),
    SocialClass.PRIEST: (DistrictKind.TEMPLE_QUARTER,),
    SocialClass.MONASTIC: (DistrictKind.TEMPLE_QUARTER,),
    SocialClass.SCRIBE: (DistrictKind.TEMPLE_QUARTER, DistrictKind.MARKET),
    SocialClass.ARTISAN: (DistrictKind.CRAFT_QUARTER, DistrictKind.MARKET),
    SocialClass.WARRIOR: (DistrictKind.CITADEL,),
    SocialClass.FARMER: (DistrictKind.FARMLAND,),
    SocialClass.SERF_OR_SLAVE: (DistrictKind.SLUMS, DistrictKind.FARMLAND),
    SocialClass.OUTCAST: (DistrictKind.SLUMS,),
    SocialClass.WORKER: (DistrictKind.INDUSTRIAL, DistrictKind.RESIDENTIAL, DistrictKind.SLUMS),
    SocialClass.PROFESSIONAL: (DistrictKind.BUSINESS, DistrictKind.RESEARCH, DistrictKind.SUBURB),
    SocialClass.OFFICIAL: (DistrictKind.CIVIC_QUARTER, DistrictKind.BUSINESS),
    SocialClass.CITIZEN: (DistrictKind.RESIDENTIAL, DistrictKind.SUBURB, DistrictKind.MARKET),
    SocialClass.UNEMPLOYED: (DistrictKind.SLUMS, DistrictKind.RESIDENTIAL),
}


async def district_for(session: AsyncSession, settlement_id: int | None, social_class: SocialClass | None) -> int | None:
    if settlement_id is None:
        return None
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement_id).order_by(DistrictRow.id)))
    if not districts:
        return None
    wanted = CLASS_DISTRICTS.get(social_class, ()) if social_class is not None else ()
    chosen = next((district for kind in wanted for district in districts if district.kind is kind), None)
    return (chosen or districts[0]).id


def starting_quality(kind: DwellingKind, social_class: SocialClass | None) -> int:
    return clamp_int(DWELLINGS[kind].quality + (CLASS_QUALITY.get(social_class, 0) if social_class is not None else 0), 0, PERCENT)


async def sickness_factor(session: AsyncSession, rules: Rules, mortal_id: int) -> float:
    genome = await session.get(GenomeRow, mortal_id)
    _household, dwelling, quality, _members = await home_of(session, rules, mortal_id)
    squalor = dwelling is not None and quality < rules.households.squalor_at
    return disease_factor(rules, genome) * (1 + rules.households.squalor_disease_pct / PERCENT if squalor else 1.0)
