from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import DWELLINGS, dwelling_spec
from aerona.catalog.life.households import CLASS_DISTRICTS, RULES_REALM_OFFICE_KINDS
from aerona.catalog.movement import breathes_under_water
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.write_guard import held
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.genetics import DwellingKind
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.body.variants import people_variants
from aerona.engine.context import TickContext
from aerona.engine.genetics.life import disease_factor
from aerona.engine.gods.queries import community_of
from aerona.engine.households.dwelling_kinds import dwelling_of_people
from aerona.engine.primitives.distance import RegionAtlas
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
SEA_ROLES = frozenset({MortalRole.CAPTAIN, MortalRole.EXPLORER, MortalRole.PILOT})
TOWER_ROLES = frozenset({MortalRole.SEER, MortalRole.SAGE, MortalRole.SCIENTIST})
WET_GROUND = 60


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
    found = await session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == mortal_id, OfficeRow.kind.in_(RULES_REALM_OFFICE_KINDS)).limit(1))
    return found is not None


async def in_cave(session: AsyncSession, mortal: EntityRow) -> bool:
    place = await session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    if place is None or place.entity_type is not EntityType.PLACE:
        return False
    profile = await session.get(PlaceProfileRow, place.id)
    return profile is not None and profile.kind is PlaceKind.CAVE


async def settled_kind(session: AsyncSession, rules: Rules, mortal: EntityRow) -> str:
    community = await community_of(session, mortal)
    if community is None or community.entity_type is not EntityType.SETTLEMENT:
        return "tent"
    if (stat(community, "population") or 0) >= rules.urban.town_population:
        return "apartment" if mortal.social_class in WAGE_CLASSES else "townhouse"
    if mortal.social_class is SocialClass.FARMER:
        return DwellingKind.FARMSTEAD
    return "longhouse" if mortal.social_class is SocialClass.WARRIOR else "hut"


async def born_dwelling(session: AsyncSession, mortal: EntityRow) -> DwellingKind | None:
    people = await people_of(session, mortal)
    biology = await session.get(PeopleBiologyRow, people.id) if people is not None else None
    if biology is None:
        return None
    variants = set(people_variants(biology))
    if BiologyVariant.AQUATIC in variants or breathes_under_water(biology.body_plan):
        return DwellingKind.SUBMERGED
    if BiologyVariant.AERIAL in variants:
        return DwellingKind.NEST
    if BiologyVariant.SUBTERRANEAN in variants:
        return DwellingKind.BURROW
    return None


async def wet_ground(session: AsyncSession, mortal: EntityRow) -> bool:
    community = await community_of(session, mortal)
    if community is None or community.entity_type is not EntityType.SETTLEMENT:
        return False
    region = (await RegionAtlas.load(session)).top_region(community.id)
    ground = await session.get(RegionEnvironmentRow, region) if region is not None else None
    return ground is not None and ground.wetland >= WET_GROUND


async def shelter(session: AsyncSession, rules: Rules, mortal_id: int, disaster: Disaster) -> float:
    _household, dwelling, _quality, _members = await home_of(session, rules, mortal_id)
    kind = await session.get(DwellingKindRow, dwelling.dwelling_kind_id) if dwelling is not None and dwelling.dwelling_kind_id is not None else None
    spec = dwelling_spec(kind.built_in_key) if kind is not None else None
    if spec is None:
        return 1.0
    guard = spec.floods if disaster is Disaster.FLOOD else spec.cold if disaster is Disaster.STORM else None
    return 1 - guard(rules) / PERCENT if guard is not None else 1.0


async def dwelling_key_for(session: AsyncSession, rules: Rules, mortal: EntityRow) -> str:
    choices = (
        (mortal.mortal_role is MortalRole.RULER or await rules_realm(session, mortal.id), "palace"),
        (await in_cave(session, mortal), "cave"),
        (mortal.mortal_role in SEA_ROLES, "ship"),
        (mortal.mortal_role in TOWER_ROLES, "tower"),
        (mortal.social_class is SocialClass.NOBLE, "manor"),
    )
    chosen = next((key for chosen, key in choices if chosen), None)
    if chosen is not None:
        return chosen
    born = await born_dwelling(session, mortal)
    if born is not None:
        return born
    return DwellingKind.STILT_HOUSE if await wet_ground(session, mortal) else await settled_kind(session, rules, mortal)


async def dwelling_kind_for(session: AsyncSession, rules: Rules, mortal: EntityRow) -> DwellingKindRow:
    people = await people_of(session, mortal)
    return await dwelling_of_people(session, people.id if people is not None else None, await dwelling_key_for(session, rules, mortal))


async def district_for(session: AsyncSession, settlement_id: int | None, social_class: SocialClass | None) -> int | None:
    if settlement_id is None:
        return None
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement_id).order_by(DistrictRow.id)))
    if not districts:
        return None
    wanted = CLASS_DISTRICTS.get(social_class, ()) if social_class is not None else ()
    chosen = next((district for kind in wanted for district in districts if district.kind is kind), None)
    return (chosen or districts[0]).id


def starting_quality(kind: DwellingKindRow, social_class: SocialClass | None) -> int:
    return clamp_int(kind.quality + (CLASS_QUALITY.get(social_class, 0) if social_class is not None else 0), 0, PERCENT)


async def sickness_factor(session: AsyncSession, rules: Rules, mortal_id: int) -> float:
    genome = await session.get(GenomeRow, mortal_id)
    _household, dwelling, quality, _members = await home_of(session, rules, mortal_id)
    squalor = dwelling is not None and quality < rules.households.squalor_at
    return disease_factor(rules, genome) * (1 + rules.households.squalor_disease_pct / PERCENT if squalor else 1.0)


DWELLINGS_FIXUP = "dwellings.w52"
W52_DWELLINGS = frozenset(kind for kind, spec in DWELLINGS.items() if spec.since_w52)


async def legacy_dwelling(ctx: TickContext, dwelling: DwellingRow) -> bool:
    current = await ctx.session.get(DwellingKindRow, dwelling.dwelling_kind_id) if dwelling.dwelling_kind_id is not None else None
    if current is None:
        return True
    source = (
        await ctx.session.get(DwellingKindRow, current.derived_from_id) if current.built_in_key is None and current.derived_from_id is not None else current
    )
    key = source.built_in_key if source is not None else None
    return key is not None and key not in W52_DWELLINGS


async def backfill_dwellings(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, DWELLINGS_FIXUP):
        return 0
    moved = 0
    rows = await ctx.session.execute(select(DwellingRow, HouseholdRow).join(HouseholdRow, HouseholdRow.id == DwellingRow.household_id).order_by(DwellingRow.id))
    for dwelling, household in list(rows):
        head = await ctx.session.get(EntityRow, household.head_node_id) if household.head_node_id is not None else None
        if head is None or held(head.id) or "dwelling_kind_id" in (dwelling.locked or []):
            continue
        wanted = await dwelling_key_for(ctx.session, ctx.rules, head)
        if wanted not in W52_DWELLINGS or not await legacy_dwelling(ctx, dwelling):
            continue
        people = await people_of(ctx.session, head)
        kind = await dwelling_of_people(ctx.session, people.id if people is not None else None, wanted)
        if dwelling.dwelling_kind_id != kind.id:
            dwelling.dwelling_kind_id = kind.id
            moved += 1
    ctx.session.add(AppliedFixupRow(key=DWELLINGS_FIXUP, result={"dwellings": moved}))
    await ctx.session.flush()
    return moved
