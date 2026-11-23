from sqlalchemy import select

from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.dominion import GodDesignRow, GodImageRow, MiracleRecordRow, RegionDominionRow
from aerona.db.tables.sons import SonRelationRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import Manifestation, PerceivedAlignment
from aerona.domain.enums.intervention import Miracle
from aerona.engine.dominion.image import manifestation_of, shown_of
from aerona.engine.dominion.miracles import impress
from tests.engine.divine.pantheon import god
from tests.engine.society.factories import Realm, context, settlement, tuned


async def test_a_god_that_shows_little_of_itself_is_seen_veiled(realm: Realm) -> None:
    faint = await god(realm, "Ilsa", Domain.DREAM, Domain.MOON)
    realm.session.add(GodDesignRow(god_node_id=faint.id, manifestation_strength=5))
    await realm.session.flush()
    ctx = context(realm.session)
    shown = await shown_of(ctx, faint.id)
    assert manifestation_of(ctx, PerceivedAlignment.BENEVOLENT, wrath=10, mercy=90, shown=shown) is Manifestation.VEILED
    assert manifestation_of(ctx, PerceivedAlignment.BENEVOLENT, wrath=10, mercy=90) is Manifestation.RADIANT


async def test_a_veiled_miracle_is_seen_by_fewer_and_stirs_less_awe_and_less_offence(realm: Realm) -> None:
    open_god = await god(realm, "Orun", Domain.SUN, Domain.LIFE)
    veiled_god = await god(realm, "Ilsa", Domain.DREAM, Domain.LIFE)
    ruler = await god(realm, "Vorn", Domain.WAR, Domain.STONE)
    town = await settlement(realm, "Lamplow")
    realm.session.add(RegionDominionRow(region_entity_id=realm.region.id, world_id=realm.world.id, god_node_id=ruler.id, share=100))
    realm.session.add(GodImageRow(god_node_id=veiled_god.id, manifestation=Manifestation.VEILED))
    await realm.session.flush()
    ctx = context(realm.session, tuned(dominion={"veiled_witness_pct": 50, "rival_miracle_offence": 10}))
    seen = await impress(ctx, open_god.id, town, kind=Miracle.HEALING.value, magnitude=60, witnesses=40)
    hidden = await impress(ctx, veiled_god.id, town, kind=Miracle.HEALING.value, magnitude=60, witnesses=40)
    assert hidden.witnesses == 20 and seen.witnesses == 40 and hidden.belief < seen.belief
    open_awe = await realm.session.get(DivineStandingRow, (town.id, open_god.id))
    veiled_awe = await realm.session.get(DivineStandingRow, (town.id, veiled_god.id))
    assert open_awe is not None and veiled_awe is not None and veiled_awe.awe < open_awe.awe
    relations = {frozenset((row.son_a_id, row.son_b_id)): row.value for row in await realm.session.scalars(select(SonRelationRow))}
    assert relations[frozenset((open_god.id, ruler.id))] == -10 and relations[frozenset((veiled_god.id, ruler.id))] == -5
    assert len(list(await realm.session.scalars(select(MiracleRecordRow)))) == 2
