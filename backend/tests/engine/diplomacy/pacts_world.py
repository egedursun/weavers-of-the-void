from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.models.entity_stats import PolityStats
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement


async def crown(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, f"{name} Hold", world, world.regions[0])
    ruler = await mortal(session, f"{name} Ruler", world, town.id)
    polity = await entity(session, f"Crown of {name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            core_entity_id=polity.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity, town
