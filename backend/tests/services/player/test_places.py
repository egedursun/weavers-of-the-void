import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.environment import PlaceCover, TerrainKind
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.engine.environment.places import mystery_held
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import stat
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import environment, places
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld

LEVERS = ("place:create", "place:edit", "place:release", "place:secret", "place:secret_edit", "place:reveal", "place:secret_delete", "pilgrimage:clear")


async def created(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, kind: PlaceKind = PlaceKind.CAVE) -> EntityRow:
    outcome = await places.create_place(scope, places.CreatePlace(region_id=world.region.id, name="Hollow Deep", kind=kind, mystery=60))
    place = await session.scalar(select(EntityRow).where(EntityRow.name == "Hollow Deep"))
    assert outcome.ledger_entry_id is not None and place is not None
    return place


def test_every_place_lever_is_catalogued() -> None:
    assert [lever for lever in LEVERS if lever not in ACTIONS_BY_ID] == []


async def test_a_created_place_carries_its_kind_profile_and_ground(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    profile = await session.get(PlaceProfileRow, place.id)
    ground = await session.get(PlaceEnvironmentRow, place.id)
    assert place.entity_type is EntityType.PLACE and stat(place, "mystery") == 60
    assert profile is not None and profile.kind is PlaceKind.CAVE
    assert ground is not None and ground.terrain is TerrainKind.UNDERGROUND and ground.cover is PlaceCover.HEAVY and ground.chokepoint


async def test_kind_sacredness_and_mystery_are_set_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    await places.edit_place(scope, places.EditPlace(place_id=place.id, kind=PlaceKind.SHRINE_SITE, sacredness=80, mystery=20))
    profile = await session.get(PlaceProfileRow, place.id)
    ground = await session.get(PlaceEnvironmentRow, place.id)
    assert profile.kind is PlaceKind.SHRINE_SITE and profile.sacredness == 80 and sorted(profile.locked) == ["kind", "sacredness"]
    assert ground.terrain is None and ground.cover is PlaceCover.LIGHT
    assert stat(place, "mystery") == 20 and await mystery_held(session, place.id)
    for field in ("kind", "sacredness", "mystery"):
        await places.release_place(scope, places.ReleasePlace(place_id=place.id, field=field))
    assert profile.locked == [] and not await mystery_held(session, place.id)
    with pytest.raises(ValidationFailedError):
        await places.release_place(scope, places.ReleasePlace(place_id=place.id, field="kind"))


async def test_held_ground_survives_a_change_of_kind_and_the_nexus_can_be_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    await environment.set_place_environment(scope, environment.SetPlaceEnvironment(place_id=place.id, field="cover", value="open"))
    await environment.set_place_environment(scope, environment.SetPlaceEnvironment(place_id=place.id, field="nexus", value=True))
    ground = await session.get(PlaceEnvironmentRow, place.id)
    assert sorted(ground.locked) == ["cover", "nexus"]
    await places.edit_place(scope, places.EditPlace(place_id=place.id, kind=PlaceKind.FOREST, hold=False))
    assert ground.cover is PlaceCover.OPEN and ground.terrain is TerrainKind.FOREST
    for field in ("cover", "nexus"):
        await places.release_place(scope, places.ReleasePlace(place_id=place.id, field=field))
    assert ground.locked == []


async def test_a_secret_is_hidden_edited_revealed_and_erased(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    outcome = await places.hide_secret(scope, places.HideSecret(place_id=place.id, kind=SecretKind.BURIED_RELIC, strength=40))
    secret = await session.scalar(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == place.id))
    assert secret is not None and secret.origin is SecretOrigin.PLAYER and outcome.ledger_entry_id is not None
    await places.edit_secret(scope, places.EditSecret(secret_id=secret.id, kind=SecretKind.SEALED_SPIRIT, strength=70, held=True))
    assert secret.kind is SecretKind.SEALED_SPIRIT and secret.sealed and secret.held and secret.strength == 70
    await places.reveal_secret(scope, places.RevealSecret(secret_id=secret.id))
    assert secret.revealed_by is DiscoveryMode.PLAYER and secret.sealed
    await places.reveal_secret(scope, places.RevealSecret(secret_id=secret.id, release=True))
    assert not secret.sealed and secret.result_entity_id is not None
    await places.delete_secret(scope, places.SecretTarget(secret_id=secret.id))
    assert await session.scalar(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == place.id)) is None


async def test_hiding_a_secret_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    outcome = await places.hide_secret(scope, places.HideSecret(place_id=place.id, kind=SecretKind.LOST_KNOWLEDGE))
    changes = await changes_of(session, outcome.ledger_entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []
    assert await session.scalar(select(PlaceSecretRow.id).where(PlaceSecretRow.place_entity_id == place.id)) is None


async def test_a_pilgrimage_site_can_be_cleared(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    place = await created(scope, session, world)
    await add_flag(session, place.id, EntityFlag.PILGRIMAGE_SITE, 1)
    await places.clear_pilgrimage_site(scope, places.SiteTarget(entity_id=place.id))
    with pytest.raises(ValidationFailedError):
        await places.clear_pilgrimage_site(scope, places.SiteTarget(entity_id=place.id))
    assert not list(await session.scalars(select(ModifierRow).where(ModifierRow.source_kind == ModifierSource.PIN)))
