import asyncio

import pytest

from aerona.media.bridge import blocking_opener
from aerona.media.errors import InvalidMediaKeyError
from aerona.media.store import MediaStore, list_keys, read_all

PAYLOAD = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 3


async def test_put_head_get_round_trip(media_store: MediaStore) -> None:
    stored = await media_store.put("originals/one.png", PAYLOAD)
    assert stored.size == len(PAYLOAD)
    assert stored.content_type == "image/png"
    head = await media_store.head("originals/one.png")
    assert head is not None
    assert head.size == len(PAYLOAD)
    assert head.content_type == "image/png"
    opened = await media_store.get("originals/one.png")
    assert opened is not None
    assert opened.info.size == len(PAYLOAD)
    chunks = [chunk async for chunk in opened.chunks]
    await opened.aclose()
    assert len(chunks) > 1
    assert b"".join(chunks) == PAYLOAD
    assert await read_all(media_store, "originals/one.png") == PAYLOAD


async def test_missing_objects_and_idempotent_delete(media_store: MediaStore) -> None:
    assert await media_store.head("originals/absent.png") is None
    assert await media_store.get("originals/absent.png") is None
    assert not await media_store.exists("originals/absent.png")
    await media_store.delete("originals/absent.png")
    await media_store.put("originals/gone.webp", b"RIFF0000WEBP")
    assert await media_store.exists("originals/gone.webp")
    await media_store.delete("originals/gone.webp")
    assert not await media_store.exists("originals/gone.webp")


async def test_overwrite_replaces_content(media_store: MediaStore) -> None:
    await media_store.put("thumbnails/64/a.webp", b"first")
    await media_store.put("thumbnails/64/a.webp", b"second!")
    assert await read_all(media_store, "thumbnails/64/a.webp") == b"second!"
    head = await media_store.head("thumbnails/64/a.webp")
    assert head is not None
    assert head.content_type == "image/webp"


async def test_list_by_prefix(media_store: MediaStore) -> None:
    for key in ("originals/b.png", "originals/a.jpg", "thumbnails/64/a.webp", "thumbnails/160/a.webp", "originals-like/x.png"):
        await media_store.put(key, key.encode())
    originals = sorted(info.key for info in await list_keys(media_store, "originals/"))
    assert originals == ["originals/a.jpg", "originals/b.png"]
    thumbnails = sorted(info.key for info in await list_keys(media_store, "thumbnails/"))
    assert thumbnails == ["thumbnails/160/a.webp", "thumbnails/64/a.webp"]
    narrow = [info.key for info in await list_keys(media_store, "thumbnails/64/")]
    assert narrow == ["thumbnails/64/a.webp"]
    sizes = {info.key: info.size for info in await list_keys(media_store, "originals/")}
    assert sizes["originals/b.png"] == len(b"originals/b.png")
    assert await list_keys(media_store, "nothing/") == []


async def test_rejects_unsafe_keys(media_store: MediaStore) -> None:
    for key in ("../escape.png", "originals/../x.png", "/absolute.png", "", "originals//x.png", ".hidden/x.png"):
        with pytest.raises(InvalidMediaKeyError):
            await media_store.put(key, b"x")
    with pytest.raises(InvalidMediaKeyError):
        await media_store.head("originals/../../etc")
    with pytest.raises(InvalidMediaKeyError):
        await list_keys(media_store, "../")


async def test_blocking_reader_streams_into_threads(media_store: MediaStore) -> None:
    await media_store.put("originals/big.png", PAYLOAD)
    opener = blocking_opener(media_store, asyncio.get_running_loop())

    def read_in_thread() -> bytes | None:
        reader = opener("originals/big.png")
        if reader is None:
            return None
        with reader:
            parts = []
            while chunk := reader.read(5):
                parts.append(chunk)
            return b"".join(parts)

    assert await asyncio.to_thread(read_in_thread) == PAYLOAD
    assert await asyncio.to_thread(opener, "originals/none.png") is None
