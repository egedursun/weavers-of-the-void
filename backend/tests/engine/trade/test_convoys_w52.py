from sqlalchemy import select

from aerona.catalog.life.economy import CONVOY_WORDS, OPEN, SHUTTING_RESPONSES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import PlagueResponseRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.means import ContainerStockRow, NavigationKitRow
from aerona.db.tables.records import IncidentFactRow
from aerona.db.tables.urban import ConvoyRow
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.means import ContainerKind, NavigationAid
from aerona.domain.enums.urban import CargoClass, ConvoyStatus
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.economy.convoys import ConvoyTally, held_back_by, wait_out
from aerona.engine.means.containers import suited_relief
from aerona.engine.means.navigation import aid_open
from aerona.services.integrity.w52_agent_b import drop_positioning, unlinked_positioning
from tests.engine.society.factories import Realm, context, make, tuned
from tests.engine.trade.helpers import lay_route, market, seasons_of


def test_every_convoy_state_is_worded_and_waiting_states_stay_open() -> None:
    assert set(CONVOY_WORDS) == set(ConvoyStatus)
    assert ConvoyStatus.STRANDED in OPEN and ConvoyStatus.QUARANTINED in OPEN
    assert PlagueResponse.QUARANTINE in SHUTTING_RESPONSES


async def convoy_on(realm: Realm, route_id: int, *, departed: int = 3) -> ConvoyRow:
    convoy = ConvoyRow(route_entity_id=route_id, cargo={"grain": 100}, status=ConvoyStatus.TRAVELLING, departed_epoch=departed, locked=[])
    realm.session.add(convoy)
    await realm.session.flush()
    return convoy


async def test_a_convoy_into_a_quarantined_port_waits_there(realm: Realm) -> None:
    ctx = context(realm.session)
    route = await lay_route(realm)
    sickness = await make(realm.session, "Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=realm.world.id)
    realm.session.add(PlagueResponseRow(community_entity_id=route.ends[1], disease_entity_id=sickness.id, response=PlagueResponse.QUARANTINE))
    convoy = await convoy_on(realm, route.entity.id)
    state = await held_back_by(ctx, convoy, route.profile)
    assert state is ConvoyStatus.QUARANTINED
    await wait_out(ctx, convoy, route.profile, state, ConvoyTally())
    assert await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "convoy.quarantined")) is not None
    old = await convoy_on(realm, route.entity.id, departed=0)
    assert await held_back_by(ctx, old, route.profile) is None


async def test_a_convoy_caught_by_the_closed_season_eats_its_cargo(realm: Realm) -> None:
    ctx = context(realm.session, tuned(convoys={"stranded_pct": 100}))
    route = await lay_route(realm, status=TradeRouteStatus.SEASONAL)
    await seasons_of(realm, "Thaw", "Deep Cold")
    route.profile.closed_season = 1
    convoy = await convoy_on(realm, route.entity.id)
    state = await held_back_by(ctx, convoy, route.profile)
    assert state is ConvoyStatus.STRANDED
    await wait_out(ctx, convoy, route.profile, state, ConvoyTally())
    assert convoy.cargo["grain"] == 100 - 100 * ctx.rules.convoys.stranded_upkeep // 100
    told = await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "convoy.stranded"))
    season = await realm.session.scalar(select(IncidentFactRow.name).where(IncidentFactRow.incident_id == told, IncidentFactRow.key == "season"))
    assert season == "Deep Cold"


async def test_suited_containers_spare_their_cargo(realm: Realm) -> None:
    ctx = context(realm.session)
    route = await lay_route(realm)
    town = route.ends[0]
    assert await suited_relief(ctx, town, CargoClass.LIQUID, 10) == 1
    realm.session.add(ContainerStockRow(community_entity_id=town, kind=ContainerKind.SKIN, count=100, locked=[]))
    await realm.session.flush()
    assert await suited_relief(ctx, town, CargoClass.LIQUID, 10) < 1
    assert await suited_relief(ctx, town, CargoClass.BULK, 10) == 1


async def test_wayfinding_beacons_and_positioning_need_their_own_grounds(realm: Realm) -> None:
    ctx = context(realm.session)
    route = await lay_route(realm)
    town = await market(realm, route, 0)
    assert not await aid_open(ctx, town, NavigationAid.WAYFINDING, set())
    assert not await aid_open(ctx, town, NavigationAid.BEACONS, set())
    assert not await aid_open(ctx, town, NavigationAid.POSITIONING, set())
    realm.session.add(NavigationKitRow(holder_entity_id=town.id, aid=NavigationAid.POSITIONING, quality=50, since_epoch=1, locked=[]))
    await realm.session.flush()
    assert await unlinked_positioning(realm.session) == [town.id]
    await drop_positioning(realm.session, town.id)
    await realm.session.flush()
    assert await realm.session.get(NavigationKitRow, (town.id, NavigationAid.POSITIONING)) is None
    assert isinstance(town, EntityRow)
