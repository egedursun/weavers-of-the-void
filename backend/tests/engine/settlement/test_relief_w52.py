from aerona.catalog.relief import RELIEF_KINDS
from aerona.db.tables.customs import PoorReliefRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.customs import ReliefKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.customs.civics import relieve_kind
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, make, settlement

RULES = Rules()


def test_seven_kinds_of_relief() -> None:
    assert len(ReliefKind) == 9 and set(RELIEF_KINDS) == set(ReliefKind)
    assert RELIEF_KINDS[ReliefKind.FOSTER_CARE].takes_in is CohortCondition.ORPHANED and RELIEF_KINDS[ReliefKind.PENSION].pays_loyalty


async def test_foster_care_takes_in_orphans(realm: Realm) -> None:
    town = await settlement(realm, "Hearth", population=1000)
    polity = await make(realm.session, "Vale Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    realm.session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.CHILD,
            sex_kind=SexKind.BEARER,
            social_class=SocialClass.FARMER,
            condition=CohortCondition.ORPHANED,
            count=100,
            generation_epoch=0,
        )
    )
    row = PoorReliefRow(polity_entity_id=polity.id, kind=ReliefKind.FOSTER_CARE, budget=100, reach=100, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    helped = await relieve_kind(context(realm.session, RULES), row)
    assert helped == RULES.relief.foster_care_effect
    assert "relief.given" in await chronicle_keys(realm.session)
