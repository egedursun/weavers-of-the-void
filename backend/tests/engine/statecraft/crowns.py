from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from tests.engine.society.factories import Realm, make, people


async def crown(realm: Realm, name: str, *, treasury: int = 0, debt: int = 0) -> tuple[EntityRow, EntityRow]:
    core = await people(realm, f"Folk of {name}")
    found = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=found.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            core_entity_id=core.id,
            treasury=treasury,
            debt=debt,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(PolityMemberRow(polity_entity_id=found.id, member_entity_id=core.id))
    await realm.session.flush()
    return found, core
