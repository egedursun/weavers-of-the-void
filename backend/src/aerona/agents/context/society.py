from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, OathRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.polity import OathStatus
from aerona.engine.body.customs import people_of
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.prompts.contexts.mortal import HomeLine


def words(value: str) -> str:
    return value.replace("_", " ")


async def home_for(session: AsyncSession, me: EntityRow) -> HomeLine | None:
    home = me if me.entity_type in SOCIETY_TYPES else await community_of(session, me)
    if home is None or home.entity_type not in SOCIETY_TYPES:
        return None
    town = await session.get(SettlementProfileRow, home.id)
    society = await session.get(CommunitySocietyRow, home.id)
    people = await people_of(session, home)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    customs: list[str] = []
    if culture is not None:
        customs = [
            f"fights as {words(culture.martial_style.value)}",
            f"{words(culture.marriage.value)}",
            f"inheritance by {words(culture.inheritance.value)}",
            f"{words(culture.aesthetic.value)} art",
        ]
        if culture.slavery_lawful:
            customs.append("keeps slaves")
    region = (await RegionAtlas.load(session)).top_region(home.id)
    sickness: list[str] = []
    if region is not None:
        raging = await session.scalars(select(OutbreakRow).where(OutbreakRow.region_entity_id == region, OutbreakRow.status != OutbreakStatus.ENDED))
        endemic = await session.scalars(select(EndemicDiseaseRow).where(EndemicDiseaseRow.region_entity_id == region))
        for disease_id, label in [*((row.disease_entity_id, "raging") for row in raging), *((row.disease_entity_id, "endemic") for row in endemic)]:
            disease = await session.get(EntityRow, disease_id)
            if disease is not None:
                sickness.append(f"{disease.name} ({label})")
    social = me.social_class
    realm_id = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home.id).limit(1))
    realm = await session.get(EntityRow, realm_id) if realm_id is not None else None
    profile = await session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    office = await session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == me.id).limit(1))
    house_id = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == me.id).limit(1))
    house = await session.get(EntityRow, house_id) if house_id is not None else None
    oaths = [
        f"{row.kind.value.replace('_', ' ')} oath{' before a god' if row.witness_son_id else ''}"
        for row in await session.scalars(select(OathRow).where(OathRow.swearer_entity_id == me.id, OathRow.status == OathStatus.SWORN))
    ]
    return HomeLine(
        realm=f"{realm.name} ({words(profile.government.value)}, legitimacy {profile.legitimacy})" if realm is not None and profile is not None else "",
        office=words(office.kind.value) if office is not None else "",
        house=house.name if house is not None else "",
        oaths=oaths,
        community=home.name,
        tier=town.size_tier.value if town is not None else "",
        order=town.public_order if town is not None else None,
        crime=town.crime if town is not None else None,
        unrest=town.unrest if town is not None else None,
        social_class=words(social.value) if social is not None else "",
        satisfaction=society.satisfaction(social) if society is not None and social is not None else None,
        customs=customs,
        sickness=sickness,
    )
