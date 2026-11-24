from sqlalchemy import select

from aerona.catalog.biology import BIOLOGY_VARIANTS, SKYLESS_VARIANTS
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.body.variants import derived_effects
from aerona.engine.body.w52_variants import VariantTally, bud, live_with_partner
from aerona.engine.primitives.stats import stat_or
from tests.engine.society.factories import Realm, context, people, tuned

V = BiologyVariant


def test_sixteen_variants_and_skyless_read_from_the_catalogue() -> None:
    assert len(BIOLOGY_VARIANTS) == len(BiologyVariant) == 19
    assert {V.AQUATIC, V.SUBTERRANEAN, V.FUNGAL} == SKYLESS_VARIANTS
    assert derived_effects([V.ENERGY])["fire_harm_pct"] == 0
    assert BIOLOGY_VARIANTS[V.COLONIAL].buds and BIOLOGY_VARIANTS[V.SYMBIOTIC].needs_partner and BIOLOGY_VARIANTS[V.FUNGAL].burns


async def test_a_colonial_people_grows_by_budding(realm: Realm) -> None:
    folk = await people(realm, "Many", population=1000)
    tally = VariantTally()
    await bud(context(realm.session, tuned(biology={"colonial_bud_rate": 10})), folk, tally)
    assert stat_or(folk, "population", 0) > 1000 and tally.budded == 1


async def test_a_symbiotic_people_suffers_when_its_partner_kind_is_gone(realm: Realm) -> None:
    folk, partner = await people(realm, "Joined", population=1000), await people(realm, "Partner")
    row = BiologyRow(holder_entity_id=folk.id, variants=[V.SYMBIOTIC.value], partner_species_id=partner.id, locked=[])
    realm.session.add(row)
    partner.status, partner.end_epoch = EntityStatus.DESTROYED, 2
    await realm.session.flush()
    tally = VariantTally()
    await live_with_partner(context(realm.session), folk, row, [], tally)
    await realm.session.flush()
    assert tally.partners_lost == 1 and stat_or(folk, "population", 0) < 1000 and row.partner_species_id is None
    assert "people.partner_lost" in set(await realm.session.scalars(select(IncidentRow.kind)))
