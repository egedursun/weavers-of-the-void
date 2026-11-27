import gzip
import hashlib
import io
import json
import tarfile
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, text

from aerona.core.errors import ConflictError, NotFoundError, ReadOnlyError, ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.meta import ImageRow
from aerona.db.tables.node import NameRegistryRow, NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.meta import ImageMime
from aerona.events.bus import EventBus
from aerona.events.change_feed import ChangeFeed, ChangeOperation
from aerona.events.kinds import EventKind
from aerona.media.file_store import FileMediaStore
from aerona.media.store import list_keys, read_all
from aerona.rules.registry import Rules
from aerona.services.backups import BackupService, backup_file_name, is_safe_image_name, label_of
from aerona.services.discovery import DiscoveryService
from aerona.services.exchange import ExchangeService, ImportMode, WorldChangedHook, package_file_name
from aerona.services.images.collection import MediaCollector
from aerona.services.world_merge import WorldMerger
from aerona.services.world_package import read_package
from aerona.settings import Settings
from tests.conftest import OpenDatabase
from tests.services.app.factories import bond, seed_cosmos


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    configured = Settings(data_dir=tmp_path / "data", llm_enabled=False)
    configured.ensure_directories()
    return configured


FOLK_BYTES = b"\x89PNG folk"
FOLK_KEY = "originals/folk.png"


@pytest.fixture
def store(settings: Settings) -> FileMediaStore:
    return FileMediaStore(settings.media_dir)


@pytest.fixture
async def live(settings: Settings, store: FileMediaStore, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(settings.database_path)
    async with database.write() as session:
        world = await seed_cosmos(session)
        session.add(
            ImageRow(
                target_node_id=world.people.id,
                file_name="folk.png",
                object_key=FOLK_KEY,
                sha256=hashlib.sha256(FOLK_BYTES).hexdigest(),
                mime=ImageMime.PNG,
                size_bytes=len(FOLK_BYTES),
            )
        )
    await store.put(FOLK_KEY, FOLK_BYTES)
    yield database
    await database.dispose()


def package_members(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            handle = archive.extractfile(member)
            assert handle is not None
            members[member.name] = handle.read()
    return members


def exchange_for(settings: Settings, live: Database, store: FileMediaStore, hook: WorldChangedHook) -> tuple[ExchangeService, BackupService, DiscoveryService]:
    discovery = DiscoveryService(settings)
    backups = BackupService(settings, live, Rules, store=store, pinned=discovery.pinned_objects)
    return ExchangeService(settings, backups, discovery, hook, WorldMerger(live), store=store), backups, discovery


def test_names_and_labels() -> None:
    name = backup_file_name("epoch 12!", datetime(2026, 1, 2, 3, 4, 5, 6000))
    assert name.startswith("aerona-epoch12-2026-01-02T03-04-05-006-")
    assert label_of(name) == "epoch12"
    assert label_of("random.db") == "manual"
    assert package_file_name("The Salt World", 4) == "The-Salt-World-epoch4.aerona"
    assert is_safe_image_name("a-b.png")
    assert not is_safe_image_name("../x.png")
    assert not is_safe_image_name("x.svg")


async def test_backup_validate_rotate_restore(settings: Settings, live: Database, store: FileMediaStore) -> None:
    bus = EventBus()
    rules = Rules()
    tight = replace(rules, backup=replace(rules.backup, recent_epoch_backups=1, milestone_epoch_multiple=10, manual_backups=1))
    service = BackupService(settings, live, lambda: tight, bus, store=store)
    first = await service.take("manual")
    manifest = json.loads((settings.backups_dir / first.file).with_suffix(".json").read_text(encoding="utf-8"))
    assert manifest["objects"] == [FOLK_KEY]
    assert bus.replay_after(0)[-1].kind is EventKind.BACKUP_TAKEN
    await service.validate(first.file)
    await service.take("epoch10")
    await service.take("epoch11")
    await service.take("epoch12")
    second_manual = await service.take("manual")
    labels = sorted(info.label for info in service.backups())
    assert labels == ["epoch10", "epoch12", "manual"]
    assert service.backups()[0].file == second_manual.file
    async with live.write() as session:
        cosmos = await session.get(CosmosRow, 1)
        assert cosmos is not None
        cosmos.name = "Changed"
        await session.execute(delete(ImageRow))
    assert await service.collector.collect([FOLK_KEY]) == 0
    assert await store.exists(FOLK_KEY)
    with pytest.raises(ValidationFailedError):
        await service.restore(second_manual.file, "nope")
    result = await service.restore(second_manual.file, "RESTORE")
    assert result.safety.startswith("aerona-before-restore-")
    async with live.read() as session:
        restored = await session.get(CosmosRow, 1)
        assert restored is not None
        assert restored.name == "Aerona"
        assert await session.scalar(select(ImageRow.object_key)) == FOLK_KEY
    assert await store.exists(FOLK_KEY)
    with pytest.raises(NotFoundError):
        await service.validate("missing.db")
    broken = settings.backups_dir / "aerona-manual-2020-01-01T00-00-00-000-zzzz.db"
    broken.write_bytes(b"not a database")
    with pytest.raises(ValidationFailedError):
        await service.validate(broken.name)


async def test_reset_keeps_objects_for_the_safety_backup(settings: Settings, live: Database, store: FileMediaStore) -> None:
    service = BackupService(settings, live, Rules, store=store)
    safety = await service.reset("RESET")
    assert safety.startswith("aerona-before-reset-")
    async with live.read() as session:
        assert await session.scalar(select(EntityRow.id)) is None
        assert await session.scalar(select(ImageRow.id)) is None
    assert await store.exists(FOLK_KEY)
    assert await service.collector.collect([FOLK_KEY]) == 0
    for info in service.backups():
        (settings.backups_dir / info.file).unlink()
        (settings.backups_dir / info.file).with_suffix(".json").unlink()
    assert await service.collector.collect([FOLK_KEY]) == 1
    assert not await store.exists(FOLK_KEY)


async def test_prune_media_keeps_referenced_and_young_objects(settings: Settings, live: Database, store: FileMediaStore) -> None:
    service = BackupService(settings, live, Rules, store=store)
    await store.put("originals/orphan.png", b"orphan")
    assert await service.prune_media() == 0
    sweeper = MediaCollector(store, service.referenced_objects, grace_seconds=0)
    assert await sweeper.sweep() == 1
    assert await store.exists(FOLK_KEY)
    assert not await store.exists("originals/orphan.png")


async def test_export_import_and_discovery(settings: Settings, live: Database, store: FileMediaStore) -> None:
    feed = ChangeFeed(period="p")
    bus = EventBus()
    hook = WorldChangedHook(feed, bus)
    fired: list[str] = []
    hook.register(lambda: fired.append("reset"))
    exchange, _backups, discovery = exchange_for(settings, live, store, hook)
    package = await exchange.export()
    members = package_members(package.path)
    assert list(members) == ["manifest.json", "world.db", f"media/{FOLK_KEY}"]
    payload = json.loads(members["manifest.json"])
    assert payload["format"] == "aerona-world"
    assert payload["version"] == 2
    assert payload["name"] == "Aerona"
    assert payload["objects"] == [{"key": FOLK_KEY, "sha256": hashlib.sha256(FOLK_BYTES).hexdigest(), "size": len(FOLK_BYTES)}]
    assert members[f"media/{FOLK_KEY}"] == FOLK_BYTES
    data = package.path.read_bytes()
    without_images = package_members((await exchange.export(images=False)).path)
    assert list(without_images) == ["manifest.json", "world.db"]
    with pytest.raises(ValidationFailedError):
        await exchange.import_package(data, ImportMode.REPLACE, "nope")
    with pytest.raises(ValidationFailedError):
        await exchange.import_package(gzip.compress(b'{"format": "other"}'), ImportMode.REPLACE, "REPLACE")
    feed.record("entities", "1", ChangeOperation.INSERT)
    token = feed.version
    result = await exchange.import_package(data, ImportMode.REPLACE, "REPLACE")
    assert result.safety_backup is not None
    assert fired == ["reset"]
    assert feed.changes_since(token, 100).full
    result = await exchange.import_package(data, ImportMode.DISCOVERY)
    assert discovery.active
    with pytest.raises(ReadOnlyError):
        discovery.ensure_writable()
    with pytest.raises(ConflictError):
        await exchange.import_package(data, ImportMode.DISCOVERY)
    async with discovery.guest_session() as session:
        guest = await session.get(CosmosRow, 1)
        assert guest is not None
        assert guest.name == "Aerona"
    restarted = DiscoveryService(settings)
    assert restarted.guest() is not None
    ended = await exchange.end_discovery()
    assert ended is not None
    assert not discovery.active
    assert await store.exists(FOLK_KEY)


async def test_import_into_a_fresh_store_restores_images(
    settings: Settings, live: Database, store: FileMediaStore, tmp_path: Path, open_database: OpenDatabase
) -> None:
    exchange, _backups, _discovery = exchange_for(settings, live, store, WorldChangedHook(ChangeFeed(period="p")))
    data = (await exchange.export()).path.read_bytes()
    other_settings = Settings(data_dir=tmp_path / "other", llm_enabled=False)
    other_settings.ensure_directories()
    other_store = FileMediaStore(other_settings.media_dir)
    other = open_database(other_settings.database_path)
    async with other.write() as session:
        await seed_cosmos(session)
    try:
        importer, _, _ = exchange_for(other_settings, other, other_store, WorldChangedHook(ChangeFeed(period="p")))
        await importer.import_package(data, ImportMode.REPLACE, "REPLACE")
        assert await read_all(other_store, FOLK_KEY) == FOLK_BYTES
        async with other.read() as session:
            image = await session.scalar(select(ImageRow))
            assert image is not None
            assert image.object_key == FOLK_KEY
            assert image.sha256 == hashlib.sha256(FOLK_BYTES).hexdigest()
        async with other.write() as session:
            await session.execute(delete(ImageRow))
        await other_store.put(FOLK_KEY, b"someone else")
        await importer.import_package(data, ImportMode.REPLACE, "REPLACE")
        assert await read_all(other_store, FOLK_KEY) == b"someone else"
        async with other.read() as session:
            relinked = await session.scalar(select(ImageRow))
            assert relinked is not None
            assert relinked.object_key != FOLK_KEY
            assert relinked.object_key.startswith("originals/imported-")
        assert await read_all(other_store, relinked.object_key) == FOLK_BYTES
        bare = (await exchange.export(images=False)).path.read_bytes()
        empty_store = FileMediaStore(tmp_path / "empty-media")
        stripped, _, _ = exchange_for(other_settings, other, empty_store, WorldChangedHook(ChangeFeed(period="p")))
        await stripped.import_package(bare, ImportMode.REPLACE, "REPLACE")
        async with other.read() as session:
            assert await session.scalar(select(ImageRow.id)) is None
    finally:
        await other.dispose()


async def test_import_dedupes_objects_by_checksum(settings: Settings, live: Database, store: FileMediaStore) -> None:
    exchange, _backups, _discovery = exchange_for(settings, live, store, WorldChangedHook(ChangeFeed(period="p")))
    data = (await exchange.export()).path.read_bytes()
    await store.delete(FOLK_KEY)
    await store.put("originals/renamed.png", FOLK_BYTES)
    async with live.write() as session:
        image = await session.scalar(select(ImageRow))
        assert image is not None
        image.object_key = "originals/renamed.png"
    await exchange.import_package(data, ImportMode.REPLACE, "REPLACE")
    async with live.read() as session:
        assert await session.scalar(select(ImageRow.object_key)) == "originals/renamed.png"
    assert not await store.exists(FOLK_KEY)


def test_package_reader_refuses_garbage_and_bombs(tmp_path: Path) -> None:
    def received(key: str, data: bytes, digest: str) -> None:
        raise AssertionError(key)

    with pytest.raises(ValidationFailedError):
        read_package(io.BytesIO(b"not gzip"), tmp_path / "x.db", received)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("world.db")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"abcd"))
    with pytest.raises(ValidationFailedError):
        read_package(io.BytesIO(buffer.getvalue()), tmp_path / "x.db", received)
    newer = io.BytesIO()
    with tarfile.open(fileobj=newer, mode="w:gz") as archive:
        manifest = json.dumps({"format": "aerona-world", "version": 99}).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        archive.addfile(info, io.BytesIO(manifest))
    with pytest.raises(ValidationFailedError, match="newer"):
        read_package(io.BytesIO(newer.getvalue()), tmp_path / "x.db", received)


def test_corrupt_discovery_state_still_counts(settings: Settings) -> None:
    service = DiscoveryService(settings)
    service.state_path.write_text("{broken", encoding="utf-8")
    assert service.active
    state = service.state()
    assert state is not None
    assert state.corrupt
    guest = service.guest()
    assert guest is not None
    assert guest.name == "unknown guest world"


async def test_merge_import_remaps_ids_and_resolves_names(settings: Settings, live: Database, store: FileMediaStore) -> None:
    feed = ChangeFeed(period="p")
    hook = WorldChangedHook(feed, EventBus())
    fired: list[str] = []
    hook.register(lambda: fired.append("changed"))
    exchange, _backups, _discovery = exchange_for(settings, live, store, hook)
    async with live.write() as session:
        people = await session.scalar(select(EntityRow).where(EntityRow.name == "Velari Folk"))
        region = await session.scalar(select(EntityRow).where(EntityRow.name == "Amberreach"))
        assert people is not None and region is not None
        await bond(session, people.id, region.id, BondKind.LIVES_IN)
    async with live.read() as session:
        before_nodes = await session.scalar(select(func.count()).select_from(NodeRow))
        before_bonds = await session.scalar(select(func.count()).select_from(BondRow))
        before_sons = await session.scalar(select(func.count()).select_from(SonRow))
    data = (await exchange.export()).path.read_bytes()
    with pytest.raises(ValidationFailedError):
        await exchange.import_package(data, ImportMode.MERGE, "merge")
    result = await exchange.import_package(data, ImportMode.MERGE, "MERGE")
    assert result.safety_backup is not None
    assert result.merge is not None
    assert fired == ["changed"]
    assert {item.old_name for item in result.merge.renamed} == {"Velar", "Velar Star", "Amberreach", "Velari Folk"}
    assert result.merge.images == {"folk.png": "merged1-folk.png"}
    assert [info.key for info in await list_keys(store, "originals/")] == [FOLK_KEY]
    assert result.merge.skipped["nodes"] == 2
    async with live.read() as session:
        assert await session.scalar(select(func.count()).select_from(SonRow)) == before_sons
        assert await session.scalar(select(func.count()).select_from(NodeRow)) == (before_nodes or 0) + 4
        assert await session.scalar(select(func.count()).select_from(BondRow)) == (before_bonds or 0) * 2
        assert await session.scalar(select(func.count()).select_from(WorldRow)) == 2
        duplicate = await session.scalar(select(EntityRow).where(EntityRow.name == "Velari Folk II"))
        assert duplicate is not None
        registry = await session.scalar(select(NameRegistryRow).where(NameRegistryRow.node_id == duplicate.id))
        assert registry is not None and registry.display == "Velari Folk II"
        assert duplicate.location_id is not None
        assert duplicate.location_id != region.id
        assert (await session.execute(text("PRAGMA foreign_key_check"))).fetchall() == []
        images = (await session.scalars(select(ImageRow.file_name))).all()
        assert sorted(images) == ["folk.png", "merged1-folk.png"]
        assert set((await session.scalars(select(ImageRow.object_key))).all()) == {FOLK_KEY}


async def test_discovery_pins_guest_objects_until_it_ends(
    settings: Settings, live: Database, store: FileMediaStore, tmp_path: Path, open_database: OpenDatabase
) -> None:
    exchange, _backups, _discovery = exchange_for(settings, live, store, WorldChangedHook(ChangeFeed(period="p")))
    data = (await exchange.export()).path.read_bytes()
    guest_settings = Settings(data_dir=tmp_path / "guest", llm_enabled=False)
    guest_settings.ensure_directories()
    guest_store = FileMediaStore(guest_settings.media_dir)
    host = open_database(guest_settings.database_path)
    async with host.write() as session:
        await seed_cosmos(session)
    try:
        visitor, backups, discovery = exchange_for(guest_settings, host, guest_store, WorldChangedHook(ChangeFeed(period="p")))
        await visitor.import_package(data, ImportMode.DISCOVERY)
        assert discovery.pinned_objects() == {FOLK_KEY}
        sweeper = MediaCollector(guest_store, backups.referenced_objects, grace_seconds=0)
        assert await sweeper.sweep() == 0
        assert await read_all(guest_store, FOLK_KEY) == FOLK_BYTES
        await visitor.end_discovery()
        assert not await guest_store.exists(FOLK_KEY)
    finally:
        await host.dispose()
