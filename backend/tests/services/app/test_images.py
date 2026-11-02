import asyncio
import hashlib
from collections.abc import AsyncIterator, Callable
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from aerona.constants.imaging import PNG_SIGNATURE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.meta import ImageRow
from aerona.domain.enums.meta import ImageMime
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import StarType
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.contract import ImageProgress, ImageStage
from aerona.media.file_store import FileMediaStore
from aerona.media.store import list_keys, read_all
from aerona.rules.registry import Rules
from aerona.services.images import records
from aerona.services.images.collection import MediaCollector
from aerona.services.images.media import StoredImage, Thumbnailer, render_thumbnail
from aerona.services.images.queue import ImageClass, ImageQueue, percent, stage_units
from aerona.services.images.records import ImageRecords
from tests.conftest import OpenDatabase
from tests.imaging.fake_worker import WORKER_URL, FakeWorker
from tests.services.app.factories import Cosmos, seed_cosmos


def png_bytes(width: int = 100, height: int = 50) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "navy").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
async def file_database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "images.db")
    yield database
    await database.dispose()


@pytest.fixture
async def cosmos(file_database: Database) -> Cosmos:
    async with file_database.write() as session:
        return await seed_cosmos(session)


def make_records(tmp_path: Path, references: Callable[[], set[str] | None] = set) -> ImageRecords:
    return ImageRecords(MediaCollector(FileMediaStore(tmp_path / "media"), references))


async def test_upload_cover_delete_and_captions(tmp_path: Path, file_database: Database, cosmos: Cosmos) -> None:
    store = make_records(tmp_path)
    async with file_database.write() as session:
        with pytest.raises(ValidationFailedError):
            await store.upload(session, cosmos.people.id, b"GIF89a", ImageMime.PNG)
        first = await store.upload(session, cosmos.people.id, png_bytes(), ImageMime.PNG, caption="folk.png")
        second = await store.upload(session, cosmos.people.id, png_bytes(60, 30), ImageMime.PNG, caption="The folk at dawn")
        assert first.is_cover
        assert not second.is_cover
        assert first.caption is None
        assert first.width == 100
        assert first.object_key == f"originals/{first.file_name}"
        assert first.sha256 == hashlib.sha256(png_bytes()).hexdigest()
        assert await read_all(store.store, first.object_key) == png_bytes()
        await store.set_cover(session, second.id)
        assert await records.cover_of(session, cosmos.people.id) == second.file_name
        released = await store.delete(session, second.id)
        assert released == second.object_key
        assert await records.cover_of(session, cosmos.people.id) == first.file_name
        refreshed = await session.get(ImageRow, first.id)
        assert refreshed is not None
        assert refreshed.is_cover
        first.caption = "x.png"
        assert await records.clear_file_name_captions(session) == 1
        listed = await records.list_images(session)
        assert listed[0].target_name == "Velari Folk"
        missing = await records.missing_targets(session)
        assert [target.kind.value for target in missing][:2] == ["creator", "son"]


async def test_missing_targets_cover_every_painted_kind(file_database: Database, cosmos: Cosmos) -> None:
    async with file_database.write() as session:
        star = StarRow(name="Ember Eye", star_type=StarType.RED_GIANT, brightness=60, x=2.0, y=2.0, created_epoch=1)
        session.add(star)
        await session.flush()
        star_id = star.id
    async with file_database.read() as session:
        missing = await records.missing_targets(session)
    kinds = {target.kind for target in missing}
    assert {NodeKind.CREATOR, NodeKind.SON, NodeKind.WORLD, NodeKind.STAR, NodeKind.ENTITY} <= kinds
    assert star_id in {target.node_id for target in missing}


async def test_upload_dedupes_by_checksum(tmp_path: Path, file_database: Database, cosmos: Cosmos) -> None:
    store = make_records(tmp_path)
    data = png_bytes(80, 40)
    async with file_database.write() as session:
        first = await store.upload(session, cosmos.people.id, data, ImageMime.PNG)
        again = await store.upload(session, cosmos.people.id, data, ImageMime.PNG)
        assert again.id == first.id
        shared = await store.upload(session, cosmos.son.id, data, ImageMime.PNG)
        assert shared.id != first.id
        assert shared.object_key == first.object_key
        assert shared.file_name != first.file_name
        released = await store.delete(session, first.id)
    assert [info.key for info in await list_keys(store.store, "originals/")] == [first.object_key]
    async with file_database.read() as session:
        keys = set((await session.scalars(select(ImageRow.object_key))).all())
    kept = make_records(tmp_path, lambda: keys)
    assert await kept.release([released]) == 0
    assert await store.store.exists(released)
    assert await make_records(tmp_path).release([released]) == 1
    assert not await store.store.exists(released)


async def test_thumbnails_render_once_and_are_cached(tmp_path: Path) -> None:
    media = FileMediaStore(tmp_path / "media")
    await media.put("originals/big.png", png_bytes(800, 400))
    await media.put("originals/small.png", png_bytes(50, 50))
    thumbnailer = Thumbnailer(media, 2, 5)
    big = StoredImage("originals/big.png", "image/png", "a" * 64, 800)
    variants = await asyncio.gather(*(thumbnailer.variant(big, 160) for _ in range(4)))
    assert {variant.key for variant in variants} == {"thumbnails/160/big.webp"}
    assert variants[0].content_type == "image/webp"
    assert variants[0].etag == f'"{"a" * 64}-w160"'
    rendered = await read_all(media, "thumbnails/160/big.webp")
    assert rendered is not None
    with Image.open(BytesIO(rendered)) as opened:
        assert opened.size == (160, 80)
        assert opened.format == "WEBP"
    modified = await media.head("thumbnails/160/big.webp")
    assert modified is not None
    again = await thumbnailer.variant(big, 160)
    assert again.key == "thumbnails/160/big.webp"
    assert (await media.head("thumbnails/160/big.webp")) == modified
    original = await thumbnailer.variant(big, None)
    assert original.key == "originals/big.png"
    assert original.etag == f'"{"a" * 64}"'
    small = StoredImage("originals/small.png", "image/png", "b" * 64, None)
    assert (await thumbnailer.variant(small, 160)).key == "originals/small.png"
    assert not await media.exists("thumbnails/160/small.webp")
    with pytest.raises(ValidationFailedError):
        await thumbnailer.variant(big, 77)
    with pytest.raises(NotFoundError):
        await thumbnailer.variant(StoredImage("originals/gone.png", "image/png", "c" * 64, 900), 64)


def test_render_thumbnail_handles_palette_images() -> None:
    buffer = BytesIO()
    Image.new("P", (300, 300)).save(buffer, format="PNG")
    rendered = render_thumbnail(buffer.getvalue(), 64)
    assert rendered is not None
    with Image.open(BytesIO(rendered)) as opened:
        assert opened.size == (64, 64)
    assert render_thumbnail(buffer.getvalue(), 640) is None


async def test_collector_sweeps_unreferenced_objects(tmp_path: Path) -> None:
    media = FileMediaStore(tmp_path / "media")
    for key in ("originals/kept.png", "originals/stale.png", "thumbnails/64/kept.webp", "thumbnails/64/stale.webp"):
        await media.put(key, b"x")
    unreadable = MediaCollector(media, lambda: None, grace_seconds=0)
    assert await unreadable.sweep() == 0
    assert await unreadable.collect(["originals/stale.png"]) == 0
    patient = MediaCollector(media, lambda: {"originals/kept.png"})
    assert await patient.sweep() == 0
    collector = MediaCollector(media, lambda: {"originals/kept.png"}, grace_seconds=0)
    assert await collector.sweep() == 1
    keys = sorted([info.key for info in await list_keys(media, "")])
    assert keys == ["originals/kept.png", "thumbnails/64/kept.webp"]


def test_progress_units() -> None:
    event = ImageProgress(job_id="j", sequence=1, kind=ImageStage.STEP, step=2, total=4, percent=0, at="2026-01-01T00:00:00Z")
    stage, units = stage_units(event, 4)
    assert stage.value == "steps"
    assert percent(units, 4) == 50


async def test_queue_generates_and_bulk(tmp_path: Path, file_database: Database, cosmos: Cosmos) -> None:
    worker = FakeWorker()
    client = ImageWorkerClient(WORKER_URL, transport=worker.transport())
    bus = EventBus()
    image_records = make_records(tmp_path)
    queue = ImageQueue(file_database, client, image_records, Rules, bus=bus)
    with pytest.raises(ValidationFailedError):
        await queue.enqueue(cosmos.son.id)
    async with file_database.write() as session:
        people = await session.get(EntityRow, cosmos.people.id)
        assert people is not None
        people.image_prompt = "A folk of salt."
    await queue.enqueue(cosmos.people.id, ImageClass.MANUAL)
    await queue.wait_idle()
    kinds = [event.kind for event in bus.replay_after(0)]
    assert EventKind.IMAGE_QUEUED in kinds
    assert EventKind.IMAGE_DONE in kinds
    async with file_database.read() as session:
        image = await session.scalar(select(ImageRow).where(ImageRow.target_node_id == cosmos.people.id))
        assert image is not None
        assert image.is_cover
        assert image.file_name.startswith("entity")
        assert image.object_key == f"originals/{image.file_name}"
    assert await image_records.store.exists(image.object_key)
    run = await queue.start_bulk()
    await queue.wait_bulk()
    assert run.skipped >= 1
    assert not queue.bulk.running
    with pytest.raises(ConflictError):
        queue.stop_bulk()
    status = queue.status()
    assert status.available
    assert status.width == Rules().image_gen.width


async def test_queue_disabled() -> None:
    queue = ImageQueue(Database("sqlite+aiosqlite:///:memory:"), ImageWorkerClient(""), make_records(Path(".")), Rules)
    assert not queue.available
    with pytest.raises(ConflictError):
        await queue.enqueue(1)


def test_generated_png_signature() -> None:
    assert png_bytes().startswith(PNG_SIGNATURE)


async def test_the_epoch_end_auto_run_generates_every_missing_image_and_rechecks_after(tmp_path: Path, file_database: Database, cosmos: Cosmos) -> None:
    worker = FakeWorker()
    queue = ImageQueue(file_database, ImageWorkerClient(WORKER_URL, transport=worker.transport()), make_records(tmp_path), Rules, bus=EventBus())
    async with file_database.write() as session:
        for entity in await session.scalars(select(EntityRow)):
            entity.image_prompt = f"A painting of {entity.name}."
    async with file_database.read() as session:
        missing_before = len(await records.missing_targets(session))
    run = await queue.start_bulk(auto=True)
    assert run.auto and run.total == missing_before
    again = await queue.start_bulk(auto=True)
    assert again is run and run.rerun_requested
    async with file_database.write() as session:
        late = EntityRow(
            name="Late Folk",
            entity_type=cosmos.people.entity_type,
            description="Born while the images were being drawn.",
            stats=cosmos.people.stats,
            power_level=1,
            origin=cosmos.people.origin,
            birth_epoch=1,
            world_id=cosmos.world.id,
            image_prompt="A painting of latecomers.",
        )
        session.add(late)
        await session.flush()
        late_id = late.id
    await queue.wait_bulk()
    await queue.wait_bulk()
    assert run.done >= 2 and run.failed == 0 and not queue.bulk.running
    async with file_database.read() as session:
        covered = set(await session.scalars(select(ImageRow.target_node_id)))
        left = await records.missing_targets(session)
    assert late_id in covered and cosmos.people.id in covered
    assert all(target.node_id not in covered for target in left)
