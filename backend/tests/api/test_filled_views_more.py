from aerona.db.tables.military import OccupationRow, SpyNetworkRow
from aerona.db.tables.polity import ClaimRow, PolityProfileRow, VassalageRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.happenings.control import EventDraft, create_event
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import open_war
from aerona.engine.structures.construction import Commission, begin, finish
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity, mortal, settlement


async def test_war_realm_structure_and_event_views_read_filled_records(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        ctx = await manual_context(session, "views", api.services.rules.current)
        town = await settlement(session, "Wardholt", core, core.regions[0], population=9000)
        rival = await settlement(session, "Reedmoor", core, core.regions[1], population=6000)
        war = await open_war(ctx, town, rival)
        session.add(SiegeRow(war_id=war.id, besieged_entity_id=rival.id, besieger_entity_id=town.id, started_epoch=ctx.epoch))
        session.add(OccupationRow(region_entity_id=core.regions[1].id, occupier_entity_id=town.id, war_id=war.id, since_epoch=ctx.epoch))
        session.add(SpyNetworkRow(owner_entity_id=town.id, target_entity_id=rival.id, intel=30, since_epoch=ctx.epoch, locked=[]))
        crown = await entity(session, "Ward Crown", EntityType.POLITY, PolityStats(), world_id=core.world.id)
        vassal = await entity(session, "Reed Crown", EntityType.POLITY, PolityStats(), world_id=core.world.id)
        for polity, seat in ((crown, town), (vassal, rival)):
            session.add(
                PolityProfileRow(
                    polity_entity_id=polity.id,
                    government=GovernmentKind.CHIEFDOM,
                    decision_rule=DecisionRule.AUTOCRATIC,
                    capital_entity_id=seat.id,
                    core_entity_id=seat.id,
                    emblem={},
                    legitimacy_parts={},
                    locked=[],
                )
            )
        await session.flush()
        session.add(VassalageRow(vassal_entity_id=vassal.id, overlord_entity_id=crown.id, since_epoch=ctx.epoch))
        pretender = await mortal(session, "Pretender", core, town.id)
        session.add(ClaimRow(claimant_entity_id=pretender.id, polity_entity_id=crown.id, basis=ClaimBasis.FABRICATED, since_epoch=1, locked=[]))
        work, row = await begin(ctx, Commission(site=town, kind=StructureKind.SHRINE))
        raised, _ = await begin(ctx, Commission(site=town, kind=StructureKind.MARKET))
        await finish(ctx, row)
        event, _ = await create_event(ctx, EventDraft(kind=EngineKind.FESTIVAL_OF_NOTE, name="Feast of Wardholt", where_id=town.id, severity=30))
        ids = {"town": town.id, "war": war.id, "crown": crown.id, "work": work.id, "raised": raised.id, "event": event.id, "pretender": pretender.id}
    for path in (
        f"/api/entities/{ids['town']}/military",
        f"/api/wars/{ids['war']}/room",
        f"/api/polities/{ids['crown']}",
        f"/api/entities/{ids['town']}/structures",
        f"/api/entities/{ids['work']}/structure",
        f"/api/entities/{ids['raised']}/structure",
        f"/api/works/{ids['town']}",
        f"/api/lineage/{ids['pretender']}",
        f"/api/home/{ids['pretender']}",
        f"/api/entities/{ids['event']}/event",
        f"/api/entities/{ids['town']}/happenings",
        f"/api/titles/{ids['crown']}",
    ):
        response = await api.http.get(path)
        assert response.status_code == 200, f"{path}: {response.text}"
