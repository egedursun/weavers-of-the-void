from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarCause, WarEnding, WarStatus
from aerona.domain.models.entity_stats import DiseaseStats, EventStats
from aerona.engine.lore.art_forms import shaken
from tests.engine.society.factories import Realm, context, make, settlement


async def test_a_quiet_home_is_not_shaken(realm: Realm) -> None:
    town = await settlement(realm, "Quietmere")
    assert not await shaken(context(realm.session), town)


async def test_a_plague_just_ended_in_the_region_shakes_a_home(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Ashby")
    pox = await make(realm.session, "Grey Pox", EntityType.DISEASE, DiseaseStats(), world_id=realm.world.id)
    outbreak = OutbreakRow(
        disease_entity_id=pox.id, region_entity_id=realm.region.id, path=SpreadPath.ORIGIN, status=OutbreakStatus.ACTIVE, severity=40, started_epoch=1
    )
    realm.session.add(outbreak)
    await realm.session.flush()
    assert not await shaken(ctx, town)
    outbreak.status, outbreak.ended_epoch = OutbreakStatus.ENDED, ctx.epoch - 1
    await realm.session.flush()
    assert await shaken(ctx, town)
    outbreak.ended_epoch = ctx.epoch - 3
    await realm.session.flush()
    assert not await shaken(ctx, town)


async def test_a_war_just_lost_shakes_a_home(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Brack")
    victor = await settlement(realm, "Victor")
    event = await make(realm.session, "War of Brack", EntityType.EVENT, EventStats(), world_id=realm.world.id)
    realm.session.add(
        WarRow(
            event_entity_id=event.id,
            world_id=realm.world.id,
            status=WarStatus.ENDED,
            cause=WarCause.HOSTILITY,
            started_epoch=1,
            ended_epoch=ctx.epoch,
            ending=next(iter(WarEnding)),
            victor_entity_id=victor.id,
            loser_entity_id=town.id,
            battles=1,
        )
    )
    await realm.session.flush()
    assert await shaken(ctx, town)
    assert not await shaken(ctx, victor)
