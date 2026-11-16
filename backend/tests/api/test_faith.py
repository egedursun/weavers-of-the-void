from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, PossessionRow, SpiritProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import AfterlifeState, JudgementDoctrine, StratumKind
from aerona.domain.models.entity_stats import CultStats, MortalStats, SpiritStats
from aerona.engine.faith.judgement import new_stratum
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity
from tests.engine.gods.factories import bond


async def test_the_faith_views_show_every_lever_field(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        cult = await entity(session, "Order of Salt", EntityType.CULT, CultStats(followers=500, zeal=40, devotion=12), world_id=core.world.id)
        await bond(session, cult.id, core.son.id, BondKind.WORSHIPS)
        await bond(session, core.people.id, core.son.id, BondKind.WORSHIPS)
        session.add(
            CultDoctrineRow(
                cult_entity_id=cult.id, judgement=JudgementDoctrine.FAITH, orthodoxy=60, tithe_rate=10, treasury=5, clergy_count=3, clergy_quality=40, locked=[]
            )
        )
        stratum = new_stratum(api.services.rules.current, core.regions[0], StratumKind.REWARD)
        session.add(stratum)
        await session.flush()
        host = await entity(session, "Vessel", EntityType.MORTAL, MortalStats(age=30), world_id=core.world.id, location_id=core.regions[0].id)
        soul = await entity(session, "Shade", EntityType.SPIRIT, SpiritStats(unrest=70), world_id=core.world.id, location_id=core.regions[0].id)
        session.add(
            SpiritProfileRow(
                spirit_entity_id=soul.id,
                imprint={"mercy": -50},
                traits=[],
                deeds={"renown": 10},
                patron_son_id=core.son.id,
                state=AfterlifeState.IN_REALM,
                stratum_id=stratum.id,
                sealed=True,
                seal_strength=40,
                locked=[],
            )
        )
        session.add(PossessionRow(host_entity_id=host.id, spirit_entity_id=soul.id, since_epoch=1, stress=30, host_values={"mercy": 20}, locked=[]))
        stratum.population = 1
        ids = (cult.id, soul.id, host.id, core.regions[0].id)
    cult_id, soul_id, host_id, region_id = ids
    doctrine = (await api.http.get(f"/api/entities/{cult_id}/doctrine")).json()
    assert doctrine["devotion"] == 12 and doctrine["rebirth_path"] == "people" and doctrine["realm_population"] == 1
    card = (await api.http.get(f"/api/entities/{soul_id}/soul")).json()
    assert card["seal_strength"] == 40 and card["possession"]["stress"] == 30 and card["possession"]["host_values"] == {"mercy": 20}
    assert card["patron_name"] == core.son.name and card["unrest"] == 70
    realm = (await api.http.get(f"/api/entities/{region_id}/afterlife")).json()
    assert realm["gods"][0]["souls"] == 1 and realm["strata"][0]["criteria"]["score_at_least"] is not None
    possession = (await api.http.get(f"/api/entities/{host_id}/possession")).json()
    assert possession["spirit"]["id"] == soul_id
    assert (await api.http.get(f"/api/entities/{soul_id}/possession")).json() is None
    assert AfterlifeStratumRow.__tablename__ == "afterlife_strata"
