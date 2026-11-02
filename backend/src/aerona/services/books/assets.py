import asyncio
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from anyio import to_thread
from PIL import Image
from sqlalchemy import select

from aerona.constants.books import PDF_IMAGE_CONCURRENCY, PRINT_JPEG_BACKGROUND, PRINT_JPEG_QUALITY, TERRAIN_WIDTH
from aerona.db.tables.meta import ImageRow
from aerona.services.books.mapsvg import load_map
from aerona.services.books.terrain import render_terrain
from aerona.services.container import Services
from aerona.services.images.media import StoredImage


def _flatten(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        flat = Image.new("RGB", rgba.size, PRINT_JPEG_BACKGROUND)
        flat.paste(rgba, mask=rgba.getchannel("A"))
        return flat
    return image if image.mode == "RGB" else image.convert("RGB")


def print_jpeg(data: bytes, pixels: int) -> bytes:
    with Image.open(BytesIO(data)) as source:
        source.load()
        sized = source.resize((pixels, max(1, round(source.height * pixels / source.width))), Image.Resampling.LANCZOS) if source.width > pixels else source
        output = BytesIO()
        _flatten(sized).save(output, format="JPEG", quality=PRINT_JPEG_QUALITY, optimize=True)
        return output.getvalue()


async def write_images(services: Services, images: dict[tuple[str, int, int], Path], on_step: Callable[[float], None] | None = None) -> None:
    names = sorted({file_name for file_name, _width, _pixels in images})
    async with services.database.read() as session:
        rows = {row.file_name: row for row in await session.scalars(select(ImageRow).where(ImageRow.file_name.in_(names)))}
    thumbnails = services.application.thumbnails
    store = services.application.media
    gate = asyncio.Semaphore(PDF_IMAGE_CONCURRENCY)
    total = max(1, len(images))
    done = 0

    async def fetch(file_name: str, width: int, pixels: int, target: Path) -> None:
        nonlocal done
        row = rows.get(file_name)
        async with gate:
            if row is not None:
                stored = StoredImage(object_key=row.object_key, content_type=row.mime.value, sha256=row.sha256, width=row.width)
                variant = await thumbnails.variant(stored, width)
                opened = await store.get(variant.key)
                if opened is not None:
                    data = b"".join([chunk async for chunk in opened.chunks])
                    if pixels:
                        data = await to_thread.run_sync(print_jpeg, data, pixels)
                    await to_thread.run_sync(target.write_bytes, data)
        done += 1
        if on_step is not None:
            on_step(done / total)

    await asyncio.gather(*(fetch(file_name, width, pixels, target) for (file_name, width, pixels), target in images.items()))


async def write_maps(services: Services, maps: dict[int, Path]) -> None:
    for world_id, target in maps.items():
        async with services.database.read() as session:
            loaded = await load_map(session, world_id)
        if loaded is None:
            continue
        data = await to_thread.run_sync(render_terrain, loaded[0], TERRAIN_WIDTH)
        await to_thread.run_sync(target.write_bytes, data)
