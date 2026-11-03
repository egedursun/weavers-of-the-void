from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import SOCIETY_TYPES
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
    return HomeLine(
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
